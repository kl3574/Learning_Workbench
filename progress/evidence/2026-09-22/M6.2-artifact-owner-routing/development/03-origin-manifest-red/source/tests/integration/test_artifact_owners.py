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
