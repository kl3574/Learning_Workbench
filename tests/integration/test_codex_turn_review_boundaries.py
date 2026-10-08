"""Independent owner-boundary counterexamples retained across fixed sources."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from tests.integration.test_codex_turn_preparation_http import turn_case as fixture, prepared, turn_body
from tests.integration.test_retrieval import publish_small
from services.api.app.infrastructure.content_repository import reference

turn_case = fixture


def identity(case):
    from services.api.app.infrastructure.security import SessionIdentity
    return SessionIdentity(case.actor_id, case.app.state.database.workspace_id(), 'author', '', '2099-01-01T00:00:00Z')


def test_member_creation_sequence_corruption_is_rejected_by_read_and_replay(turn_case):
    case, _, sid, _, _ = turn_case
    original = prepared(turn_case).json()
    with case.app.state.database.transaction() as conn:
        conn.execute('DROP TRIGGER codex_turn_members_update')
        conn.execute('UPDATE codex_turn_members SET sequence=sequence+100')
    before = case.dump()
    response = case.get(f'sessions/{sid}/turns?limit=1')
    assert response.status_code == 409
    replay = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'turn')
    assert replay.status_code == 409
    response = case.get('turns/' + original['turn_id'])
    assert response.status_code == 409
    assert case.dump() == before


def test_large_omitted_selection_must_verify_real_body(turn_case):
    case, _, sid, _, _ = turn_case
    blocks, _, _ = publish_small(case.app.state.database, identity(case), 'large-review', ['large synthetic α\n' * 4000])
    digest = blocks[0].body_sha256
    path = case.app.state.settings.data_dir / 'blobs' / digest[:2] / digest
    path.write_bytes(b'corrupt synthetic original')
    before = case.dump()
    body = {**turn_body(), 'context_refs': [reference(blocks[0]).model_dump()]}
    response = case.post(f'sessions/{sid}/turn-preparations', body, 'large-corrupt')
    assert response.status_code == 409
    assert case.dump() == before


def test_subject_get_rechecks_access_after_read_snapshot_closes(turn_case, monkeypatch):
    case, _, _, _, _ = turn_case
    value = prepared(turn_case).json()
    owner = case.app.state.codex_turn_service.context
    original = owner.current
    entered, release = Event(), Event()
    def held(*args):
        entered.set()
        assert release.wait(10), 'controlled role-change writer did not finish'
        return original(*args)
    monkeypatch.setattr(owner, 'current', held)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(case.get, 'turn-preparations/' + value['id'])
        try:
            assert entered.wait(10), 'subject GET did not reach its checked context read'
            role = case.client.post('/api/v1/session/role', json={'role': 'learner'},
                headers={**case.headers, 'Idempotency-Key': 'late-role'})
            assert role.status_code == 200
            before = case.dump()
        finally:
            release.set()
        response = future.result(timeout=10)
    assert response.status_code == 403
    assert turn_body()['message'] not in response.text
    assert case.dump() == before
