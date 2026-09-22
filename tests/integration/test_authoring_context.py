"""Actual SQLite and public Content bytes; no provider or numeric execution."""
from dataclasses import replace

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.authoring_dto import AuthoringPrepareWrite
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.infrastructure.content_repository import reference
from tests.integration.test_retrieval import all_rows, publish_small


def request(refs=()):
    return AuthoringPrepareWrite(topic='原创合成算术例题', prerequisites=[], objectives=['检验显式求和'],
        proof_policy='full', output_kind='worked_example', source_refs=list(refs), provider_id='test_provider')


@pytest.fixture
def authoring(tmp_path):
    from services.api.app.application.authoring import AuthoringService
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    identity = SessionIdentity('session_author_test', workspace, 'author', 'unused', '2099-01-01T00:00:00Z')
    blocks, _, _ = publish_small(database, identity, 'authoring', ['完整合成材料甲。\n', '完整合成材料乙。\n'])
    return database, identity, blocks, AuthoringService(database)


def test_real_prepare_freezes_exact_order_and_replays_original_ack_after_cancel(authoring):
    database, identity, blocks, service = authoring
    body = request([reference(blocks[1]), reference(blocks[0])])
    ack = service.prepare(identity, body, 'original')
    assert ack.status == 'awaiting_approval'
    view = service.read(identity, ack.id)
    assert view.request == body and view.proposal_id is view.consent_id is view.raw_answer is None
    assert [item.ref.id for item in view.preparation.materials] == [blocks[1].id, blocks[0].id]
    assert all(item.material_review == 'unreviewed' for item in view.preparation.materials)
    with database.connect() as conn:
        row = conn.execute('SELECT * FROM jobs WHERE id=?', (ack.id,)).fetchone()
        assert row['kind'] == 'authoring' and row['revision'] == 1
        assert sha256_bytes(row['input_json'].encode()) == row['input_sha256']
        assert conn.execute('SELECT COUNT(*) FROM context_snapshots').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM consents').fetchone()[0] == 0
    before = all_rows(database)
    assert service.read(identity, ack.id) == view
    assert service.prepare(identity, body, 'original') == ack
    assert all_rows(database) == before
    from services.api.app.import_dto import JobCancelRequest
    service.cancel_job(identity, ack.id, JobCancelRequest(expected_revision=1), 'cancel')
    before = all_rows(database)
    assert service.prepare(identity, body, 'original') == ack
    assert service.job(identity, ack.id).status == 'cancelled'
    assert all_rows(database) == before


def test_empty_sources_stated_and_oversized_complete_selection_rolls_back(authoring):
    database, identity, _, service = authoring
    ack = service.prepare(identity, request(), 'empty')
    view = service.read(identity, ack.id)
    assert view.preparation.materials == []
    assert any(warning.code == 'AUTHORING_SOURCES_UNSELECTED' for warning in view.preparation.warnings)
    blocks, _, _ = publish_small(database, identity, 'oversize', ['甲' * 12000])
    before = all_rows(database)
    with pytest.raises(ApiError) as caught:
        service.prepare(identity, request([reference(blocks[0])]), 'too-large')
    assert caught.value.status == 413
    assert all_rows(database) == before


def test_current_role_precedes_old_ack_but_safe_job_control_remains(authoring):
    database, identity, _, service = authoring
    ack = service.prepare(identity, request(), 'original')
    learner = replace(identity, role='learner')
    before = all_rows(database)
    with pytest.raises(ApiError) as caught:
        service.prepare(learner, request(), 'original')
    assert caught.value.status == 403
    snapshot = service.job(learner, ack.id)
    assert snapshot.result_refs == snapshot.warnings == [] and snapshot.error is None
    assert snapshot.progress.label == snapshot.status
    assert request().topic not in canonical_bytes(snapshot).decode()
    assert all_rows(database) == before


@pytest.mark.parametrize('read_kind', ['job', 'page'])
def test_corrupt_owned_context_blocks_safe_control_without_disclosing_it(authoring, read_kind):
    database, identity, _, service = authoring
    ack = service.prepare(identity, request(), 'original')
    with database.transaction() as conn:
        conn.execute("UPDATE context_snapshots SET snapshot_sha256=?", ('f' * 64,))
    before = all_rows(database)
    learner = replace(identity, role='learner')
    with pytest.raises(ApiError) as caught:
        service.job(learner, ack.id) if read_kind == 'job' else service.jobs(learner)
    assert caught.value.code == 'AUTHORING_INTEGRITY_ERROR'
    assert all_rows(database) == before


def test_terminal_cancel_ack_cannot_rewrite_its_original_transition_basis(authoring):
    database, identity, _, service = authoring
    from services.api.app.import_dto import JobCancelRequest
    ack = service.prepare(identity, request(), 'original')
    service.cancel_job(identity, ack.id, JobCancelRequest(expected_revision=1), 'cancel')
    with database.transaction() as conn:
        raw = canonical_bytes({'expected_revision': 999}).decode()
        conn.execute('UPDATE authoring_commands SET request_json=?,request_sha256=? WHERE key=?',
                     (raw, sha256_bytes(raw.encode()), 'cancel'))
    before = all_rows(database)
    with pytest.raises(ApiError) as caught:
        service.job(identity, ack.id)
    assert caught.value.code == 'AUTHORING_INTEGRITY_ERROR'
    assert all_rows(database) == before
