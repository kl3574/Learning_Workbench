"""Real local HTTP/SQLite turn control; synthetic bootstrap only, no CLI/model."""
import pytest

from tests.integration.test_codex_bootstrap_http import ControlledRuntime, approve, make_case
from tests.integration.test_assessment_learning_port import assessment_learning_state

assessment_state = assessment_learning_state


@pytest.fixture
def turn_case(tmp_path):
    runtime = ControlledRuntime()
    case = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    case.app.state.provider_service.secret_store.initialize()
    response = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 0, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'synthetic-model', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'synthetic-config'})
    assert response.status_code == 200, response.text
    _, _, body = approve(case)
    response = case.post('sessions', body, 'bootstrap-session')
    assert response.status_code == 201, response.text
    yield case, runtime, response.json()['id'], body, response.content
    case.client.close()


def turn_body(revision=2):
    return {'message': 'Synthetic original Unicode α\nDo not execute.', 'context_refs': [],
            'expected_session_revision': revision, 'provider_id': 'codex_local',
            'tools': {'max_tool_calls': 0, 'wall_seconds': 30}}


def test_prepare_current_control_cancel_and_original_acks(turn_case, monkeypatch):
    case, runtime, session_id, bootstrap_body, bootstrap_ack = turn_case
    def forbidden(*args, **kwargs):
        pytest.fail('turn preparation or control read attempted execution')
    monkeypatch.setattr(runtime, 'execute', forbidden)
    response = case.post(f'sessions/{session_id}/turn-preparations', turn_body(), 'turn-original')
    assert response.status_code == 202, response.text
    original, ack = response.json(), response.content
    assert original['validity'] == 'unavailable' and original['session_revision'] == 3
    assert original['job']['status'] == 'awaiting_approval'
    assert original['proposal_id'] is None and original['consent_id'] is None
    before = case.dump()
    control = case.get('turns/' + original['turn_id'])
    assert control.status_code == 200, control.text
    assert control.json()['execution'] == 'not_started'
    assert control.json()['approval_controls'] == [] and control.json()['consent_control'] is None
    assert turn_body()['message'] not in control.text and 'context_refs' not in control.text
    current = case.get('sessions/' + session_id).json()
    assert current['revision'] == 3 and current['active_turn_id'] == original['turn_id']
    assert not any(current['capabilities'].values())
    assert case.get('turn-preparations/' + original['id']).json() == original
    assert case.get(f'sessions/{session_id}/turns').json()['items'] == [control.json()]
    assert case.dump() == before
    cancel = case.client.post('/api/v1/jobs/' + original['job']['id'] + '/cancel',
        json={'expected_revision': 1}, headers={**case.headers, 'Idempotency-Key': 'cancel-original'})
    assert cancel.status_code == 200 and cancel.json()['status'] == 'cancelled', cancel.text
    current = case.get('sessions/' + session_id).json()
    assert current['revision'] == 5 and current['active_turn_id'] is None
    assert case.get('turns/' + original['turn_id']).json()['outcome'] == 'cancelled'
    assert case.get('turn-preparations/' + original['id']).json()['validity'] == 'closed'
    before = case.dump()
    assert case.post(f'sessions/{session_id}/turn-preparations', turn_body(), 'turn-original').content == ack
    assert case.post('sessions', bootstrap_body, 'bootstrap-session').content == bootstrap_ack
    assert case.dump() == before and len(runtime.calls) == 1


def prepared(turn_case, revision=2, key='turn'):
    case, _, session_id, _, _ = turn_case
    response = case.post(f'sessions/{session_id}/turn-preparations', turn_body(revision), key)
    assert response.status_code == 202, response.text
    return response


def cancel(case, job, revision=1, key='cancel'):
    return case.client.post('/api/v1/jobs/' + job + '/cancel', json={'expected_revision': revision},
        headers={**case.headers, 'Idempotency-Key': key})


@pytest.mark.parametrize('bad,expected', [('revision', 412), ('active', 409), ('changed_key', 409),
    ('extra', 422), ('bool_revision', 422), ('duplicate_refs', 422), ('unknown_provider', 404)])
def test_fresh_cas_active_slot_full_command_and_schema_zero_write(turn_case, bad, expected):
    case, _, sid, _, _ = turn_case
    prepared(turn_case)
    body, key = turn_body(3), 'other'
    if bad == 'revision':
        body['expected_session_revision'] = 2
    elif bad == 'changed_key':
        body, key = {**turn_body(), 'message': 'different'}, 'turn'
    elif bad == 'extra':
        body['trusted_proof'] = True
    elif bad == 'bool_revision':
        body['expected_session_revision'] = True
    elif bad == 'duplicate_refs':
        body['context_refs'] = [{'entity': 'block', 'id': 'same', 'revision': 1}] * 2
    elif bad == 'unknown_provider':
        assert cancel(case, case.get(f'sessions/{sid}/turns').json()['items'][0]['job']['id']).status_code == 200
        body['expected_session_revision'] = 5
        body['provider_id'] = 'missing'
    before = case.dump()
    result = case.post(f'sessions/{sid}/turn-preparations', body, key)
    assert result.status_code == expected, result.text
    assert case.dump() == before


def test_learner_control_cancel_no_subject_and_no_second_terminal(turn_case):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    role = case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'learner'})
    assert role.status_code == 200
    before = case.dump()
    for path in ['turns/' + value['turn_id'], f'sessions/{sid}/turns', 'sessions/' + sid]:
        response = case.get(path)
        assert response.status_code == 200 and 'message' not in response.text and 'context_refs' not in response.text
    assert case.get('turn-preparations/' + value['id']).status_code == 403
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(3), 'new').status_code == 403
    assert case.dump() == before
    first = cancel(case, value['job']['id'])
    assert first.status_code == 200
    assert cancel(case, value['job']['id'], 1, 'stale').status_code == 412
    second = cancel(case, value['job']['id'], 2, 'observe')
    assert second.content == first.content
    assert case.get('sessions/' + sid).json()['revision'] == 5
    assert case.get('turns/' + value['turn_id']).json()['last_seq'] == 2
    before = case.dump()
    assert cancel(case, value['job']['id']).content == first.content
    assert cancel(case, value['job']['id'], 2, 'observe').content == first.content
    assert case.dump() == before


def test_new_actor_reads_old_control_but_cannot_take_original_session(turn_case, tmp_path):
    case, runtime, sid, _, _ = turn_case
    original = prepared(turn_case).json()
    other = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    assert other.actor_id != case.actor_id
    try:
        assert other.get('turns/' + original['turn_id']).json()['actor_session_id'] == case.actor_id
        assert cancel(other, original['job']['id']).status_code == 200
        before = case.dump()
        assert other.post(f'sessions/{sid}/turn-preparations', turn_body(5), 'original-looking').status_code == 403
        assert case.dump() == before
        assert prepared(turn_case, revision=5, key='original-actor-new').status_code == 202
    finally:
        other.client.close()


@pytest.mark.parametrize('table', ['codex_turn_sessions', 'codex_turn_heads', 'codex_turn_events',
    'codex_turn_event_members', 'codex_turn_members', 'codex_turn_commands'])
def test_missing_complete_owner_table_fails_every_read_replay_and_cancel(turn_case, table):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    with case.app.state.database.transaction() as conn:
        triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall()
        for row in triggers:
            conn.execute('DROP TRIGGER ' + row[0])
        conn.execute('DELETE FROM ' + table)
    before = case.dump()
    for path in ['turn-preparations/' + value['id'], 'turns/' + value['turn_id'],
                 f'sessions/{sid}/turns', 'sessions/' + sid]:
        response = case.get(path)
        assert response.status_code == 409, (table, path, response.text)
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'turn').status_code == 409
    assert cancel(case, value['job']['id']).status_code == 409
    assert case.dump() == before


def test_tail_delete_cannot_revive_cancelled_turn_or_erase_original_ack(turn_case):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    assert cancel(case, value['job']['id']).status_code == 200
    with case.app.state.database.transaction() as conn:
        conn.execute('DROP TRIGGER codex_turn_events_delete')
        conn.execute('DELETE FROM codex_turn_events WHERE seq=2')
    before = case.dump()
    assert case.get('sessions/' + sid).status_code == 409
    assert case.get('turns/' + value['turn_id']).status_code == 409
    assert cancel(case, value['job']['id']).status_code == 409
    assert case.dump() == before


@pytest.mark.parametrize('damage', ['context', 'run', 'job', 'provider'])
def test_cross_owner_original_binding_damage_cannot_return_partial_success(turn_case, damage):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    with case.app.state.database.transaction() as conn:
        if damage == 'context':
            conn.execute("UPDATE context_snapshots SET envelope_json='{}' WHERE id=?", (value['summary']['context_snapshot_id'],))
        elif damage == 'run':
            conn.execute("UPDATE runs SET snapshot_json='{}' WHERE id=?", (value['job']['id'],))
        elif damage == 'job':
            conn.execute("DELETE FROM job_events WHERE job_id=?", (value['job']['id'],))
        else:
            conn.execute("DROP TRIGGER provider_config_history_no_update")
            conn.execute("UPDATE provider_config_history SET config_json='{}' WHERE provider_id='codex_local'")
    before = case.dump()
    assert case.get('sessions/' + sid).status_code == 409
    assert case.get('turns/' + value['turn_id']).status_code == 409
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'turn').status_code == 409
    assert case.dump() == before


def test_pagination_freezes_membership_but_reads_current_status(turn_case):
    case, _, sid, _, _ = turn_case
    first = prepared(turn_case).json()
    assert cancel(case, first['job']['id']).status_code == 200
    second = prepared(turn_case, 5, 'two').json()
    assert cancel(case, second['job']['id'], key='cancel-two').status_code == 200
    page = case.get(f'sessions/{sid}/turns?limit=1').json()
    assert page['items'][0]['id'] == second['turn_id'] and page['next_cursor']
    prepared(turn_case, 8, 'three')
    before = case.dump()
    older = case.get(f'sessions/{sid}/turns?limit=1&cursor=' + page['next_cursor'])
    assert older.status_code == 200 and [item['id'] for item in older.json()['items']] == [first['turn_id']]
    assert older.json()['next_cursor'] is None
    assert case.get(f'sessions/{sid}/turns?limit=2&cursor=' + page['next_cursor']).status_code == 400
    assert case.get(f'sessions/{sid}/turns?limit=1&limit=1').status_code == 422
    assert case.get(f'sessions/{sid}/turns?unknown=x').status_code == 422
    assert case.dump() == before


def test_prepare_atomic_rollback_keeps_session_revision_job_run_context_and_command(turn_case):
    case, _, sid, _, _ = turn_case
    with case.app.state.database.transaction() as conn:
        conn.execute("CREATE TRIGGER controlled_failure BEFORE INSERT ON codex_turn_event_members BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END;")
    before = case.dump()
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'rollback')
    assert response.status_code == 500 and response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert case.dump() == before
    assert case.get('sessions/' + sid).json()['revision'] == 2


def test_current_provider_revision_changes_eligibility_never_original_ack(turn_case):
    case, _, sid, _, _ = turn_case
    original = prepared(turn_case)
    response = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 1, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'synthetic-model-new', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'config-advance'})
    assert response.status_code == 200
    before = case.dump()
    assert case.get('turn-preparations/' + original.json()['id']).json()['validity'] == 'changed'
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'turn').content == original.content
    assert case.dump() == before


def test_first_cancel_persists_request_and_release_as_two_session_changes(turn_case):
    case, _, sid, _, _ = turn_case
    original = prepared(turn_case).json()
    assert original['session_revision'] == 3
    assert cancel(case, original['job']['id']).status_code == 200
    assert case.get('sessions/' + sid).json()['revision'] == 5
    assert case.get('turns/' + original['turn_id']).json()['last_seq'] == 2


def identity(case):
    from services.api.app.infrastructure.security import SessionIdentity
    return SessionIdentity(case.actor_id, case.app.state.database.workspace_id(), 'author', '', '2099-01-01T00:00:00Z')


def test_exact_public_source_order_original_pins_and_history_after_current_advance(turn_case):
    from tests.integration.test_retrieval import publish_small
    from services.api.app.infrastructure.content_repository import reference
    from services.api.app.application.content import ContentService
    case, _, sid, _, _ = turn_case
    blocks, _, _ = publish_small(case.app.state.database, identity(case), 'turn-source', ['Alpha original\n', 'Beta original\n'])
    body = {**turn_body(), 'context_refs': [reference(blocks[1]).model_dump(), reference(blocks[0]).model_dump()]}
    response = case.post(f'sessions/{sid}/turn-preparations', body, 'sources')
    assert response.status_code == 202, response.text
    value = response.json()
    assert [item['ref']['id'] for item in value['summary']['materials']] == [blocks[1].id, blocks[0].id]
    new = blocks[0].model_copy(update={'revision': 2, 'title': 'Later metadata'})
    ContentService(case.app.state.database).publish(identity(case).workspace_id, [new], {new.body_path: b'Alpha original\n'})
    before = case.dump()
    current = case.get('turn-preparations/' + value['id'])
    assert current.status_code == 200 and current.json()['validity'] == 'changed'
    assert current.json()['summary'] == value['summary']
    replay = case.post(f'sessions/{sid}/turn-preparations', body, 'sources')
    assert replay.content == response.content
    assert case.dump() == before


@pytest.mark.parametrize('large,damage', [(True, False), (True, True), (False, True)])
def test_omission_still_verifies_actual_selected_bytes_before_any_job_is_saved(turn_case, large, damage):
    from tests.integration.test_retrieval import publish_small
    from services.api.app.infrastructure.content_repository import reference
    case, _, sid, _, _ = turn_case
    text = 'Original source α\n' * (4000 if large else 2)
    blocks, _, _ = publish_small(case.app.state.database, identity(case), 'bounded', [text])
    block = blocks[0]
    if damage:
        path = case.app.state.settings.data_dir / 'blobs' / block.body_sha256[:2] / block.body_sha256
        path.write_bytes(b'corrupt actual synthetic source')
    before = case.dump()
    body = {**turn_body(), 'context_refs': [reference(block).model_dump()]}
    response = case.post(f'sessions/{sid}/turn-preparations', body, 'bounded-source')
    if damage:
        assert response.status_code == 409, response.text
        assert case.dump() == before
    else:
        assert response.status_code == 202, response.text
        value = response.json()
        assert value['summary']['materials'] == [] and value['summary']['character_count'] < 12000
        assert any(item['code'] == 'CODEX_CONTEXT_MATERIAL_OMITTED' for item in value['summary']['warnings'])
        before = case.dump()
        read = case.get('turn-preparations/' + value['id'])
        assert read.status_code == 200 and read.json() == value
        assert case.dump() == before


def test_changed_original_source_cannot_hide_behind_saved_context_for_safe_control(turn_case):
    from tests.integration.test_retrieval import publish_small
    from services.api.app.infrastructure.content_repository import reference
    case, _, sid, _, _ = turn_case
    blocks, _, _ = publish_small(case.app.state.database, identity(case), 'retained', ['Actual original\n'])
    body = {**turn_body(), 'context_refs': [reference(blocks[0]).model_dump()]}
    created = case.post(f'sessions/{sid}/turn-preparations', body, 'retained')
    assert created.status_code == 202, created.text
    value = created.json()
    digest = blocks[0].body_sha256
    (case.app.state.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'corrupt original')
    before = case.dump()
    control = case.get('turns/' + value['turn_id'])
    assert control.status_code == 409
    replay = case.post(f'sessions/{sid}/turn-preparations', body, 'retained')
    assert replay.status_code == 409
    assert cancel(case, value['job']['id']).status_code == 409
    assert case.dump() == before


def test_concurrent_real_writers_reserve_one_slot_and_original_key_one_job(turn_case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from services.api.app.codex_turn_dto import CodexTurnPrepareWrite
    from services.api.app.application.errors import ApiError
    case, _, sid, _, _ = turn_case
    service, actor = case.app.state.codex_turn_service, identity(case)
    barrier = Barrier(2)
    def run(key):
        barrier.wait()
        try:
            return service.prepare_turn(actor, sid, CodexTurnPrepareWrite.model_validate(turn_body()), key)
        except ApiError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ['same', 'same']))
    assert results[0] == results[1]
    assert len(case.get(f'sessions/{sid}/turns').json()['items']) == 1
    assert cancel(case, results[0].job.id).status_code == 200
    barrier = Barrier(2)
    def distinct(key):
        barrier.wait()
        try:
            return service.prepare_turn(actor, sid, CodexTurnPrepareWrite.model_validate(turn_body(5)), key)
        except ApiError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(distinct, ['one', 'two']))
    assert sum(not isinstance(item, int) for item in results) == 1
    assert 412 in results
    assert len(case.get(f'sessions/{sid}/turns').json()['items']) == 2


def test_cancel_transaction_failure_preserves_waiting_slot_and_no_terminal(turn_case):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    with case.app.state.database.transaction() as conn:
        conn.execute("CREATE TRIGGER cancel_failure BEFORE UPDATE ON codex_turn_heads BEGIN SELECT RAISE(ABORT,'synthetic cancel rollback'); END;")
    before = case.dump()
    result = cancel(case, value['job']['id'])
    assert result.status_code == 500
    assert case.dump() == before
    current = case.get('sessions/' + sid).json()
    assert current['revision'] == 3 and current['active_turn_id'] == value['turn_id']
    control = case.get('turns/' + value['turn_id']).json()
    assert control['execution'] == 'not_started' and control['last_seq'] == 1


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_real_policy_exclusion_and_control_access(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from services.api.app.application.errors import ApiError
    database, _, fixture, assessment = assessment_state
    runtime = ControlledRuntime()
    case = make_case(database.settings.data_dir, codex_bootstrap_runtime=runtime)
    case.app.state.provider_service.secret_store.initialize()
    config = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 0, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'synthetic-model', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'config'})
    assert config.status_code == 200
    _, _, body = approve(case)
    session = case.post('sessions', body, 'session').json()['id']
    turn = case.post(f'sessions/{session}/turn-preparations', turn_body(), 'prepared')
    assert turn.status_code == 202, turn.text
    owner_state = database, identity(case), fixture, assessment
    if mode == 'independent':
        before = case.dump()
        with pytest.raises(ApiError) as rejected:
            start(owner_state, mode=mode)
        assert rejected.value.code == 'SUBJECT_WORK_ACTIVE'
        assert case.dump() == before
        assert cancel(case, turn.json()['job']['id']).status_code == 200
    start(owner_state, mode=mode)
    before = case.dump()
    value = turn.json()
    assert case.get('turns/' + value['turn_id']).status_code == 200
    assert case.get(f'sessions/{session}/turns').status_code == 200
    assert case.get('turn-preparations/' + value['id']).status_code == 409
    assert case.post(f'sessions/{session}/turn-preparations', turn_body(), 'prepared').status_code == 409
    assert case.dump() == before
    assert cancel(case, value['job']['id'], 2 if mode == 'independent' else 1, 'safe-stop').status_code == 200
    assert len(runtime.calls) == 1
