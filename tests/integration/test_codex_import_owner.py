"""Import-owned staging/preview; Artifact-source port is an explicit synthetic peer."""
from dataclasses import replace
from hashlib import sha256

from services.api.app.application.import_codex_models import CheckedCodexArtifactSource
from services.api.app.application.imports import ImportService
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
