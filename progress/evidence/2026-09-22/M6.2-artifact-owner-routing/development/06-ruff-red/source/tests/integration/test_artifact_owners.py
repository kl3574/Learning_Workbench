"""Existing download HTTP with actual Import production and closed owner routing."""

from dataclasses import replace
import json

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.infrastructure.security import SessionIdentity
from tests.integration.test_import_http import headers

from tests.integration.test_import_http import block_preview, importing as importing, preview, upload


def imported_original(importing):
    app, client, settings = importing
    raw = b'# Synthetic artifact source\n\nExact original bytes.\n'
    staged = upload(client, settings, raw)
    candidate = preview(client, staged['import_id'])
    assert candidate['status'] == 'preview_ready'
    draft = block_preview(client, candidate)
    source = client.get('/api/v1/sources/' + draft['payload']['source_id'])
    assert source.status_code == 200
    return app, client, settings, staged, candidate, source.json()['artifact'], raw


def test_unregistered_artifact_profile_never_defaults_to_import(importing):
    app, client, _, _, _, artifact, raw = imported_original(importing)
    assert client.get(artifact['download_path']).content == raw
    with app.state.database.transaction() as connection:
        connection.execute("UPDATE artifacts SET profile='quality_report' WHERE id=?", (artifact['artifact_id'],))
    response = client.get(artifact['download_path'])
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'ARTIFACT_OWNER_UNAVAILABLE'
    assert raw not in response.content


def current_test_identity(app):
    with app.state.database.connect() as connection:
        row = connection.execute('SELECT id,workspace_id,role,expires_at FROM local_sessions').fetchone()
    return SessionIdentity(row['id'], row['workspace_id'], row['role'], '', row['expires_at'])


@pytest.mark.parametrize('corruption', ['source_membership', 'job_kind', 'other_import_job', 'manifest_size',
                                       'manifest_hash', 'manifest_filename', 'manifest_missing_field',
                                       'manifest_extra_field', 'manifest_bool_version', 'bytes', 'file'])
def test_registered_import_reader_rejects_corrupt_origin_and_bytes(importing, corruption):
    app, client, settings, staged, _, artifact, _ = imported_original(importing)
    with app.state.database.transaction() as connection:
        row = connection.execute('SELECT * FROM artifacts WHERE id=?', (artifact['artifact_id'],)).fetchone()
        if corruption == 'source_membership':
            source = connection.execute('SELECT source_id FROM ingestion_imports WHERE id=?', (staged['import_id'],)).fetchone()[0]
            metadata = json.loads(connection.execute('SELECT metadata_json FROM sources WHERE id=?', (source,)).fetchone()[0])
            metadata['artifact_id'] = 'artifact_not_the_original'
            connection.execute('UPDATE sources SET metadata_json=? WHERE id=?', (json.dumps(metadata), source))
        elif corruption == 'job_kind':
            connection.execute("UPDATE jobs SET kind='quality_gate' WHERE id=?", (staged['job']['id'],))
        elif corruption == 'other_import_job':
            pass
        elif corruption.startswith('manifest_'):
            manifest = json.loads(row['manifest_json'])
            if corruption == 'manifest_size': manifest['size'] += 1
            if corruption == 'manifest_hash': manifest['sha256'] = '0' * 64
            if corruption == 'manifest_filename': manifest['filename'] = '../PRIVATE_SENTINEL'
            if corruption == 'manifest_missing_field': del manifest['filename']
            if corruption == 'manifest_extra_field': manifest['unexpected'] = 'PRIVATE_SENTINEL'
            if corruption == 'manifest_bool_version': manifest['version'] = True
            connection.execute('UPDATE artifacts SET manifest_json=? WHERE id=?', (json.dumps(manifest), artifact['artifact_id']))
        else:
            path = settings.data_dir / connection.execute('SELECT relative_path FROM content_blobs WHERE sha256=?',
                                                         (row['blob_sha256'],)).fetchone()[0]
            if corruption == 'bytes': path.write_bytes(b'PRIVATE_SENTINEL')
            else: path.unlink()
    if corruption == 'other_import_job':
        other = upload(client, settings, b'# Another real source\n', key='another')
        assert preview(client, other['import_id'])['status'] == 'preview_ready'
        with app.state.database.transaction() as connection:
            connection.execute('UPDATE artifacts SET job_id=? WHERE id=?', (other['job']['id'], artifact['artifact_id']))
    response = client.get(artifact['download_path'])
    expected = 'ARTIFACT_OWNER_UNAVAILABLE' if corruption == 'job_kind' else 'BLOB_STORAGE_UNAVAILABLE' if corruption == 'file' else 'CONTENT_HASH_MISMATCH'
    assert response.status_code == (503 if corruption == 'file' else 409)
    assert response.json()['error']['code'] == expected
    assert 'PRIVATE_SENTINEL' not in response.text


@pytest.mark.parametrize('change', ['revoked', 'expired', 'missing', 'different_workspace'])
def test_owner_reloads_real_session_inside_the_callers_transaction(importing, change):
    app, _, _, _, _, artifact, _ = imported_original(importing)
    identity = current_test_identity(app)
    with app.state.database.transaction() as connection:
        if change == 'revoked': connection.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z'")
        if change == 'expired': connection.execute("UPDATE local_sessions SET expires_at='2000-01-01T00:00:00Z'")
        if change == 'missing': connection.execute('DELETE FROM local_sessions')
        if change == 'different_workspace': identity = replace(identity, workspace_id='workspace_unrelated')
        with pytest.raises(ApiError) as rejected:
            ImportService(app.state.database).read_artifact(connection, identity, artifact['artifact_id'])
        assert rejected.value.code == 'SESSION_REQUIRED'


def test_owner_read_uses_same_readonly_transaction_and_never_writes(importing, monkeypatch):
    app, _, _, _, _, artifact, raw = imported_original(importing)
    database = app.state.database
    identity = current_test_identity(app)
    owner = ImportService(database)
    with database.transaction(immediate=False) as connection:
        connection.execute('PRAGMA query_only=ON')
        before = list(connection.iterdump())
        def another_connection(*args, **kwargs):
            raise AssertionError('Artifact owner must retain the caller transaction')
        monkeypatch.setattr(database, 'connect', another_connection)
        data, descriptor = owner.read_artifact(connection, identity, artifact['artifact_id'])
        assert data == raw and descriptor.model_dump(mode='json') == artifact
        assert list(connection.iterdump()) == before


def test_empty_registry_and_quality_job_are_explicitly_unavailable(importing):
    from services.api.app.application.artifacts import ArtifactsService
    app, client, _, staged, _, artifact, _ = imported_original(importing)
    identity = current_test_identity(app)
    with pytest.raises(ApiError) as unavailable:
        ArtifactsService(app.state.database, {}).download(identity, artifact['artifact_id'])
    assert unavailable.value.code == 'ARTIFACT_OWNER_UNAVAILABLE'
    # Corrupt only a real produced artifact/job; this is not a Quality producer.
    with app.state.database.transaction() as connection:
        connection.execute("UPDATE artifacts SET profile='quality_report' WHERE id=?", (artifact['artifact_id'],))
        connection.execute("UPDATE jobs SET kind='quality_gate' WHERE id=?", (staged['job']['id'],))
    response = client.get(artifact['download_path'])
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'ARTIFACT_OWNER_UNAVAILABLE'


@pytest.mark.parametrize('table,code', [('artifacts', 'REFERENCE_MISSING'), ('sources', 'CONTENT_HASH_MISMATCH'),
                                      ('jobs', 'JOB_MISSING')])
def test_foreign_workspace_binding_never_reads_the_known_blob(importing, table, code):
    app, client, _, staged, _, artifact, raw = imported_original(importing)
    with app.state.database.transaction() as connection:
        workspace = dict(connection.execute('SELECT * FROM workspace').fetchone())
        workspace['id'] = 'workspace_unrelated'
        connection.execute('INSERT INTO workspace(' + ','.join(workspace) + ') VALUES(' +
                           ','.join('?' for _ in workspace) + ')', tuple(workspace.values()))
        if table == 'artifacts': identifier = artifact['artifact_id']
        elif table == 'jobs': identifier = staged['job']['id']
        else: identifier = connection.execute('SELECT source_id FROM ingestion_imports WHERE id=?',
                                              (staged['import_id'],)).fetchone()[0]
        connection.execute(f"UPDATE {table} SET workspace_id='workspace_unrelated' WHERE id=?", (identifier,))
    response = client.get(artifact['download_path'])
    assert response.status_code == (409 if table == 'sources' else 404)
    assert response.json()['error']['code'] == code
    assert raw not in response.content


def test_all_four_real_import_profiles_keep_http_bytes_and_headers(importing):
    import hashlib
    from tests.integration.test_import_http import confirm
    from tests.integration.test_import_repository import package_bytes, synthetic_tree
    app, client, settings = importing
    values, bodies = synthetic_tree()
    raw = package_bytes(values, bodies, asset=b'synthetic passive resource')
    staged = upload(client, settings, raw, filename='assets.learnpack.zip', kind='learnpack')
    candidate = preview(client, staged['import_id'])
    assert candidate['status'] == 'preview_ready'
    committed = confirm(client, settings, candidate)
    assert committed.status_code == 200
    with app.state.database.connect() as connection:
        rows = connection.execute('SELECT id,profile FROM artifacts WHERE job_id=?', (staged['job']['id'],)).fetchall()
    assert {row['profile'] for row in rows} == {'import_original', 'import_asset', 'untrusted_quality_receipt', 'import_receipt'}
    identity = current_test_identity(app)
    owner = ImportService(app.state.database)
    for row in rows:
        with app.state.database.transaction(immediate=False) as connection:
            data, descriptor = owner.read_artifact(connection, identity, row['id'])
        response = client.get(descriptor.download_path)
        assert response.status_code == 200 and response.content == data
        assert response.headers['content-type'] == 'application/octet-stream'
        assert response.headers['content-disposition'].startswith('attachment;')
        assert response.headers['etag'] == '"' + hashlib.sha256(data).hexdigest() + '"'
        if row['profile'] == 'import_original': assert data == raw
        if row['profile'] == 'import_asset': assert data == b'synthetic passive resource'
        if row['profile'] == 'untrusted_quality_receipt':
            assert data == b'{"mathematical":"APPROVED","fixture_only":true}'
        if row['profile'] == 'import_receipt':
            assert json.loads(data)['kind'] == 'import_migration_receipt'
            assert json.loads(data)['mathematical'] == 'NOT_RUN'


def test_private_original_reloads_downgraded_role_and_http_never_uses_legacy_port(importing, monkeypatch):
    from tests.integration.test_import_repository import FIXTURES
    app, client, settings = importing
    assert client.post('/api/v1/session/role', json={'role': 'author'}, headers=headers(client, settings)).status_code == 200
    raw = (FIXTURES / 'course-author.learnpack.zip').read_bytes()
    staged = upload(client, settings, raw, filename='author.learnpack.zip', kind='learnpack')
    candidate = preview(client, staged['import_id'])
    draft = block_preview(client, candidate)
    artifact = client.get('/api/v1/sources/' + draft['payload']['source_id']).json()['artifact']
    old_identity = current_test_identity(app)
    def legacy(*args, **kwargs):
        raise AssertionError('HTTP must not call trusted legacy Import.download')
    monkeypatch.setattr(ImportService, 'download', legacy)
    assert client.get(artifact['download_path']).content == raw
    assert client.post('/api/v1/session/role', json={'role': 'learner'}, headers=headers(client, settings)).status_code == 200
    response = client.get(artifact['download_path'])
    assert response.status_code == 403 and response.json()['error']['code'] == 'POLICY_DENIED'
    with app.state.database.transaction(immediate=False) as connection:
        with pytest.raises(ApiError) as rejected:
            ImportService(app.state.database).read_artifact(connection, old_identity, artifact['artifact_id'])
        assert rejected.value.code == 'POLICY_DENIED'


def test_owner_requires_a_real_transaction(importing):
    app, _, _, _, _, artifact, _ = imported_original(importing)
    identity = current_test_identity(app)
    with app.state.database.connect() as connection:
        assert not connection.in_transaction
        with pytest.raises(ApiError) as rejected:
            ImportService(app.state.database).read_artifact(connection, identity, artifact['artifact_id'])
        assert rejected.value.code == 'TRANSACTION_REQUIRED'


@pytest.mark.parametrize('change,status,code', [('revoked', 401, 'SESSION_REQUIRED'),
                                               ('expired', 401, 'SESSION_REQUIRED'),
                                               ('downgraded', 403, 'POLICY_DENIED')])
def test_http_rechecks_identity_changed_after_cookie_authentication(importing, monkeypatch, change, status, code):
    from services.api.app.interfaces import http
    from tests.integration.test_import_repository import FIXTURES
    app, client, settings = importing
    assert client.post('/api/v1/session/role', json={'role': 'author'}, headers=headers(client, settings)).status_code == 200
    staged = upload(client, settings, (FIXTURES / 'course-author.learnpack.zip').read_bytes(),
                    filename='private.learnpack.zip', kind='learnpack')
    candidate = preview(client, staged['import_id'])
    draft = block_preview(client, candidate)
    artifact = client.get('/api/v1/sources/' + draft['payload']['source_id']).json()['artifact']
    authenticate = http.authenticate
    def changed_after_authentication(database, request):
        actual = authenticate(database, request)
        with database.transaction() as connection:
            if change == 'revoked':
                connection.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (actual.id,))
            elif change == 'expired':
                connection.execute("UPDATE local_sessions SET expires_at='2000-01-01T00:00:00Z' WHERE id=?", (actual.id,))
            else:
                connection.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (actual.id,))
        return actual
    monkeypatch.setattr(http, 'authenticate', changed_after_authentication)
    response = client.get(artifact['download_path'])
    assert response.status_code == status
    assert response.json()['error']['code'] == code
    assert 'etag' not in response.headers and 'content-disposition' not in response.headers
