"""Import-owned staging/preview; Artifact-source port is an explicit synthetic peer."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from services.api.app.application.import_codex_models import CheckedCodexArtifactSource
from services.api.app.application.imports import ImportService
from services.api.app.application.errors import ApiError
from services.api.app.codex_turn_dto import CodexArtifactImportWrite
from services.api.app.infrastructure.database import utc_now
from services.api.app.infrastructure.security import author_execution_identity
from tests.integration.test_codex_bootstrap_http import make_case


class SourcePeer:
    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def read_selected_artifacts(self, conn, identity, session_id, body):
        assert conn.in_transaction
        self.calls.append((identity.id, session_id, body.model_dump()))
        return self.selected


def source(identity, data=b'# Synthetic model output\n\nUnreviewed material.\n', artifact_id='artifact_selected'):
    return CheckedCodexArtifactSource(identity.workspace_id, identity.id, 'session_synthetic',
        'turn_synthetic', 'job_original', '1' * 64, 'manifest_synthetic', '2' * 64,
        artifact_id, sha256(data).hexdigest(), len(data), 'markdown', 'selected.md', 'text/markdown', data)


def fixture(tmp_path):
    case = make_case(tmp_path)
    database = case.app.state.database
    with database.transaction() as conn:
        identity = author_execution_identity(conn, database.workspace_id(), case.actor_id)
        now = utc_now()
        # The Artifact aggregate owner is outside this Import-port slice.
        conn.execute("INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) "
            "VALUES(?,?,'codex_artifact_import','queued',1,?,'{}',?,?)",
            ('job_aggregate', identity.workspace_id, '3' * 64, now, now))
    return case, ImportService(database), identity


def stage(case, service, identity, selected):
    body = CodexArtifactImportWrite(turn_id='turn_synthetic', artifact_ids=[item.artifact_id for item in selected],
        expected_manifest_sha256='2' * 64)
    port = SourcePeer(tuple(selected))
    with case.app.state.database.transaction() as conn:
        bindings = service.stage_codex_artifacts(conn, identity, session_id='session_synthetic', body=body,
            aggregate_job_id='job_aggregate', source=port)
    assert len(port.calls) == 1
    return bindings


def test_real_import_preview_and_source_keep_exact_selected_bytes_and_unreviewed_origin(tmp_path):
    case, service, identity = fixture(tmp_path)
    selected = source(identity, '# 模型材料 α\n\n原件保留 UTF-8。\n'.encode())
    bindings = stage(case, service, identity, [selected])
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.artifact_sha256 == sha256(selected.data).hexdigest()
    assert binding.actor_session_id == case.actor_id
    assert case.app.state.import_worker.run_once() is True
    preview = case.client.get('/api/v1/imports/' + binding.import_id)
    assert preview.status_code == 200
    assert preview.json()['status'] == 'preview_ready'
    assert 'CODEX_IMPORTED_MATERIAL_UNREVIEWED' in {item['code'] for item in preview.json()['warnings']}
    response = case.client.get('/api/v1/sources/' + binding.source_id)
    assert response.status_code == 200
    view = response.json()
    assert view['sha256'] == selected.artifact_sha256 and view['size'] == len(selected.data)
    assert view['rights'] == 'user_selected_model_output; unreviewed; rights_not_verified'
    assert case.client.get(view['artifact']['download_path']).content == selected.data
    with case.app.state.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        checked = service.check_codex_bindings(conn, identity.workspace_id, bindings)
    assert checked[0].status == 'preview_ready' and checked[0].job.status == 'awaiting_approval'
    assert case.client.get('/api/v1/courses').json()['items'] == []
    # Later mutable peer input cannot change the frozen Import original.
    selected = replace(selected, data=b'Changed later')
    assert case.client.get(view['artifact']['download_path']).content != selected.data


@pytest.mark.parametrize('parsed', [False, True])
def test_safe_aggregate_cancel_keeps_own_preview_facts_and_is_idempotent(tmp_path, parsed):
    case, service, identity = fixture(tmp_path)
    bindings = stage(case, service, identity, [source(identity)])
    if parsed:
        assert case.app.state.import_worker.run_once() is True
    with case.app.state.database.transaction() as conn:
        before = service.check_codex_bindings(conn, identity.workspace_id, bindings)
        stopped = service.cancel_codex_imports(conn, identity.workspace_id, bindings)
    assert stopped[0].status == 'cancelled' and stopped[0].job.status == 'cancelled'
    assert stopped[0].preview_receipt_sha256 == before[0].preview_receipt_sha256
    assert stopped[0].preview_reached is parsed
    dump = case.dump()
    with case.app.state.database.transaction() as conn:
        assert service.cancel_codex_imports(conn, identity.workspace_id, bindings) == stopped
    assert case.dump() == dump


def test_later_ordinary_commit_does_not_change_prior_preview_receipt_or_original_ack(tmp_path):
    case, service, identity = fixture(tmp_path)
    binding, = bindings = stage(case, service, identity, [source(identity)])
    assert case.app.state.import_worker.run_once() is True
    preview = case.client.get('/api/v1/imports/' + binding.import_id).json()
    with case.app.state.database.transaction(immediate=False) as conn:
        original = service.check_codex_bindings(conn, identity.workspace_id, bindings)[0]
    body = {'expected_input_sha256': binding.artifact_sha256,
        'accepted_warning_codes': [item['code'] for item in preview['warnings']], 'id_mapping': []}
    path = '/api/v1/imports/' + binding.import_id + '/commit'
    headers = {**case.headers, 'Idempotency-Key': 'ordinary-explicit-commit'}
    ack = case.client.post(path, json=body, headers=headers)
    assert ack.status_code == 200
    before = case.dump()
    with case.app.state.database.transaction(immediate=False) as conn:
        current = service.check_codex_bindings(conn, identity.workspace_id, bindings)[0]
    assert current.status == 'committed' and current.job.status == 'completed'
    assert current.preview_reached and current.preview_receipt_sha256 == original.preview_receipt_sha256
    assert case.client.post(path, json=body, headers=headers).content == ack.content
    assert case.dump() == before


@pytest.mark.parametrize('bad', ['actor', 'workspace', 'session', 'turn', 'digest', 'size', 'kind', 'filename', 'order'])
def test_invalid_checked_selection_leaves_no_stages(tmp_path, bad):
    case, service, identity = fixture(tmp_path)
    item = source(identity)
    values = {'actor': {'actor_session_id': 'wrong_actor'}, 'workspace': {'workspace_id': 'wrong_workspace'},
        'session': {'session_id': 'wrong_session'}, 'turn': {'turn_id': 'wrong_turn'},
        'digest': {'artifact_sha256': '0' * 64}, 'size': {'artifact_size': 1},
        'kind': {'import_kind': 'text'}, 'filename': {'filename': '../wrong.md'}}
    body = CodexArtifactImportWrite(turn_id=item.turn_id, artifact_ids=[item.artifact_id], expected_manifest_sha256='2' * 64)
    peer = SourcePeer((replace(item, **values[bad]),) if bad != 'order' else ())
    before = case.dump()
    with pytest.raises(ApiError):
        with case.app.state.database.transaction() as conn:
            service.stage_codex_artifacts(conn, identity, session_id=item.session_id, body=body,
                aggregate_job_id='job_aggregate', source=peer)
    assert case.dump() == before


def test_second_blob_failure_rolls_back_even_if_caller_handles_exception(tmp_path, monkeypatch):
    case, service, identity = fixture(tmp_path)
    items = (source(identity), source(identity, b'# Second material\n', 'artifact_second'))
    body = CodexArtifactImportWrite(turn_id='turn_synthetic', artifact_ids=[item.artifact_id for item in items],
        expected_manifest_sha256='2' * 64)
    write, calls = service.blobs.write, []
    def failing(data, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise ApiError(503, 'BLOB_STORAGE_UNAVAILABLE', 'Synthetic storage refusal')
        return write(data, **kwargs)
    monkeypatch.setattr(service.blobs, 'write', failing)
    before = case.dump()
    with case.app.state.database.transaction() as conn:
        with pytest.raises(ApiError):
            service.stage_codex_artifacts(conn, identity, session_id='session_synthetic', body=body,
                aggregate_job_id='job_aggregate', source=SourcePeer(items))
    assert len(calls) == 2 and case.dump() == before


@pytest.mark.parametrize('damage', ['binding_tail', 'bindings_all', 'batch', 'ordinal', 'job_input', 'source_sha',
    'original_artifact', 'preview_receipt', 'preview_tail', 'extra_warning'])
def test_new_binding_damage_fails_closed_on_ordinary_get_and_owner_read_without_repairs(tmp_path, damage):
    case, service, identity = fixture(tmp_path)
    bindings = stage(case, service, identity, [source(identity), source(identity, b'# Second\n', 'artifact_second')])
    for _ in bindings:
        assert case.app.state.import_worker.run_once() is True
    first, last = bindings
    with case.app.state.database.transaction() as conn:
        if damage in {'binding_tail', 'bindings_all', 'batch'}:
            # Deliberate synthetic integrity damage, not a normal deletion API.
            conn.execute('DELETE FROM codex_import_previews WHERE import_id=?', (last.import_id,))
            conn.execute('DELETE FROM codex_import_bindings WHERE import_id=?', (last.import_id,))
            if damage != 'binding_tail':
                conn.execute('DELETE FROM codex_import_previews')
                conn.execute('DELETE FROM codex_import_bindings')
            if damage == 'batch':
                conn.execute('DELETE FROM codex_import_batches')
        elif damage == 'ordinal':
            conn.execute('UPDATE codex_import_bindings SET ordinal=7 WHERE import_id=?', (first.import_id,))
        elif damage == 'job_input':
            conn.execute("UPDATE jobs SET input_json='{}' WHERE id=?", (first.import_job_id,))
        elif damage == 'source_sha':
            conn.execute('UPDATE sources SET blob_sha256=? WHERE id=?', (last.artifact_sha256, first.source_id))
        elif damage == 'original_artifact':
            conn.execute("UPDATE artifacts SET profile='import_asset' WHERE job_id=?", (first.import_job_id,))
        elif damage == 'preview_receipt':
            conn.execute('DELETE FROM codex_import_previews WHERE import_id=?', (first.import_id,))
        elif damage == 'preview_tail':
            conn.execute("DELETE FROM job_events WHERE job_id=? AND type='awaiting_approval'", (first.import_job_id,))
        else:
            row = conn.execute('SELECT metadata_json FROM sources WHERE id=?', (first.source_id,)).fetchone()
            metadata = json.loads(row[0])
            metadata['warnings'].append({'code': 'FORGED_APPROVAL', 'message': 'Synthetic false claim',
                'severity': 'warning', 'locator': None})
            conn.execute('UPDATE sources SET metadata_json=? WHERE id=?', (json.dumps(metadata), first.source_id))
    before = case.dump()
    for path in ['/api/v1/imports/' + first.import_id, '/api/v1/sources/' + first.source_id]:
        response = case.client.get(path)
        assert response.status_code == 409
    with pytest.raises(ApiError):
        with case.app.state.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            service.check_codex_bindings(conn, identity.workspace_id, bindings)
    assert case.dump() == before


def test_current_role_is_checked_before_artifact_port_or_new_stage(tmp_path):
    case, service, identity = fixture(tmp_path)
    response = case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'become-learner'})
    assert response.status_code == 200
    item, before = source(identity), case.dump()
    peer = SourcePeer((item,))
    with pytest.raises(ApiError) as denied:
        with case.app.state.database.transaction() as conn:
            service.stage_codex_artifacts(conn, identity, session_id=item.session_id,
                body=CodexArtifactImportWrite(turn_id=item.turn_id, artifact_ids=[item.artifact_id],
                    expected_manifest_sha256=item.manifest_sha256), aggregate_job_id='job_aggregate', source=peer)
    assert denied.value.status == 403 and peer.calls == [] and case.dump() == before


@pytest.mark.parametrize('damage', ['all_binding_family', 'status_pair'])
def test_complete_member_discovery_and_child_status_cannot_hide_damage(tmp_path, damage):
    case, service, identity = fixture(tmp_path)
    binding, = bindings = stage(case, service, identity, [source(identity)])
    with case.app.state.database.transaction() as conn:
        if damage == 'all_binding_family':
            conn.execute('DELETE FROM codex_import_bindings')
            conn.execute('DELETE FROM codex_import_batches')
        else:
            conn.execute("UPDATE ingestion_imports SET status='cancelled' WHERE id=?", (binding.import_id,))
    before = case.dump()
    with pytest.raises(ApiError):
        with case.app.state.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            service.codex_aggregate_members(conn, identity.workspace_id)
    assert case.dump() == before


@pytest.mark.parametrize('field', ['filename', 'media_type', 'import_kind'])
def test_malformed_artifact_owner_descriptor_is_safe_error_not_unhandled_type(tmp_path, field):
    case, service, identity = fixture(tmp_path)
    item = replace(source(identity), **{field: 8})
    before = case.dump()
    with pytest.raises(ApiError):
        stage(case, service, identity, [item])
    assert case.dump() == before


@pytest.mark.parametrize('missing', ['codex_import_batches', 'codex_import_bindings', 'codex_import_previews', 'all'])
def test_applied_codex_migration_missing_tables_is_damage_even_for_legacy_source(tmp_path, missing):
    case, service, identity = fixture(tmp_path)
    staged = service.stage(identity, data=b'Original legacy material.\n', filename='legacy.md',
        kind='markdown', key='ordinary-before-damage')
    with case.app.state.database.transaction() as conn:
        tables = ['codex_import_previews', 'codex_import_bindings', 'codex_import_batches'] if missing == 'all' else [missing]
        for table in tables:
            conn.execute('DROP TABLE ' + table)
    before = case.dump()
    with pytest.raises(ApiError) as caught:
        with case.app.state.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            service.check_codex_source(conn, identity.workspace_id, staged.import_id)
    assert caught.value.code == 'CODEX_IMPORT_HISTORY_DAMAGED'
    assert case.dump() == before


def test_actual_old_stage_raw_json_hash_and_http_ack_oracle_remain_exact(tmp_path, monkeypatch):
    from services.api.app.application import imports
    oracle = json.loads((Path(__file__).parents[1] / 'fixtures/codex_import_legacy/stage-80d18a93.json').read_text())
    case = make_case(tmp_path)
    monkeypatch.setattr(imports, 'identifier', lambda prefix: prefix + '_legacy_oracle')
    data = oracle['data_utf8'].encode()
    headers = {**case.headers, 'Idempotency-Key': 'legacy-import'}
    response = case.client.post('/api/v1/imports', data={'kind': 'markdown'}, files={'file': ('legacy.md', data)}, headers=headers)
    assert response.status_code == 202 and response.content == oracle['http_ack_utf8'].encode()
    assert sha256(response.content).hexdigest() == oracle['http_ack_sha256']
    with case.app.state.database.transaction(immediate=False) as conn:
        source_row = conn.execute('SELECT metadata_json,rights FROM sources WHERE id=?', ('source_legacy_oracle',)).fetchone()
        job = conn.execute('SELECT input_json,input_sha256 FROM jobs WHERE id=?', ('job_legacy_oracle',)).fetchone()
        assert source_row['metadata_json'] == oracle['source_metadata_json'] and source_row['rights'] == oracle['rights']
        assert job['input_json'] == oracle['job_input_json'] and job['input_sha256'] == oracle['data_sha256']
        assert conn.execute('SELECT COUNT(*) FROM codex_import_bindings').fetchone()[0] == 0
    before = case.dump()
    assert case.client.post('/api/v1/imports', data={'kind': 'markdown'},
        files={'file': ('legacy.md', data)}, headers=headers).content == response.content
    assert case.dump() == before


def test_selected_author_package_keeps_original_and_preview_private_and_claims_unreviewed(tmp_path):
    case, service, identity = fixture(tmp_path)
    data = (Path(__file__).parents[2] / 'fixtures/synthetic/course-author.learnpack.zip').read_bytes()
    item = replace(source(identity, data), import_kind='learnpack', filename='selected.learnpack.zip',
        media_type='application/zip')
    binding, = stage(case, service, identity, [item])
    assert case.app.state.import_worker.run_once() is True
    preview = case.client.get('/api/v1/imports/' + binding.import_id)
    assert preview.status_code == 200 and preview.json()['status'] == 'preview_ready'
    codes = {warning['code'] for warning in preview.json()['warnings']}
    assert {'CODEX_IMPORTED_MATERIAL_UNREVIEWED', 'IMPORT_PRIVATE_ANSWERS', 'IMPORT_REVIEW_UNVERIFIED'} <= codes
    source_view = case.client.get('/api/v1/sources/' + binding.source_id).json()
    assert case.client.get(source_view['artifact']['download_path']).content == data
    assert case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'learner'}).status_code == 200
    for path in ['/api/v1/imports/' + binding.import_id, '/api/v1/sources/' + binding.source_id,
            source_view['artifact']['download_path'], '/api/v1/drafts/' + preview.json()['preview_refs'][0]]:
        assert case.client.get(path).status_code == 403


def test_parser_failure_remains_real_failure_with_model_origin_and_zero_publication(tmp_path):
    case, service, identity = fixture(tmp_path)
    binding, = bindings = stage(case, service, identity, [source(identity, b'\x00 malformed synthetic markdown')])
    assert case.app.state.import_worker.run_once() is True
    view = case.client.get('/api/v1/imports/' + binding.import_id)
    assert view.status_code == 200 and view.json()['status'] == 'failed'
    assert 'CODEX_IMPORTED_MATERIAL_UNREVIEWED' in {item['code'] for item in view.json()['warnings']}
    with case.app.state.database.transaction(immediate=False) as conn:
        checked = service.check_codex_bindings(conn, identity.workspace_id, bindings)[0]
    assert checked.status == 'failed' and checked.job.status == 'failed' and not checked.preview_reached
    assert case.client.get('/api/v1/courses').json()['items'] == []


@pytest.mark.parametrize('damage', ['input', 'blob'])
def test_damaged_queued_source_does_not_claim_successful_work_or_repair_it(tmp_path, damage):
    case, service, identity = fixture(tmp_path)
    binding, = stage(case, service, identity, [source(identity)])
    with case.app.state.database.transaction() as conn:
        if damage == 'input':
            conn.execute("UPDATE jobs SET input_json='{}' WHERE id=?", (binding.import_job_id,))
        else:
            path = conn.execute('SELECT relative_path FROM content_blobs WHERE sha256=?', (binding.artifact_sha256,)).fetchone()[0]
            blob = case.app.state.settings.data_dir / path
            raw = blob.read_bytes()
            assert sha256(raw).hexdigest() == binding.artifact_sha256
            blob.write_bytes(b'x' * len(raw))
    worked = case.app.state.import_worker.run_once()
    assert worked is False
    with case.app.state.database.transaction(immediate=False) as conn:
        row = conn.execute('SELECT status,revision,input_json FROM jobs WHERE id=?', (binding.import_job_id,)).fetchone()
    assert tuple(row)[:2] == ('queued', 1)
    if damage == 'input':
        assert row['input_json'] == '{}'
