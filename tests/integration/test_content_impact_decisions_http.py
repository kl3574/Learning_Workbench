"""Real Content publication/SQLite and HTTP impact decisions, synthetic intent only."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import sqlite3

import pytest
from fastapi.testclient import TestClient

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.content import ContentService
from services.api.app.infrastructure.content_repository import reference
from services.api.app.main import create_app
from tests.integration.test_authoring_http import session, command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_content_repository import tree
from tests.integration.test_content_impact_snapshot import invalidation_id


@dataclass
class Case:
    database: object
    identity: object
    app: object
    client: object
    headers: dict
    original: list
    service: object
    event_id: str

    @property
    def path(self):
        return f'/api/v1/content/impacts/{self.event_id}'

    def write(self, target='lesson', *, revision=0, decision='no_revision_needed'):
        view = self.client.get(self.path, params={'target_id': target})
        assert view.status_code == 200, view.text
        return dict(target_id=target, observed_ref=self.service.current(self.identity.workspace_id, target).model_dump(mode='json'),
                    expected_event_snapshot_sha256=view.json()['event_snapshot_sha256'],
                    expected_decision_revision=revision, decision=decision, reason='Synthetic explicit object review.',
                    evidence_artifact_ids=[])

    def decide(self, body, key='decide'):
        return self.client.post(self.path + '/decisions', json=body, headers=command(self.headers, key))


@pytest.fixture
def case(tmp_path):
    database, identity, app, client, headers = session(tmp_path)
    original, bodies = tree()
    service = ContentService(database)
    service.publish(identity.workspace_id, original, bodies)
    # A note retains its own owner state; its ID stays in the conservative event.
    note = dm.Note(id='note_impact', revision=1, workspace_id=identity.workspace_id, markdown='Synthetic note',
                   anchor=dm.Selection(ref=reference(original[1]), exact_quote='#', start_codepoint=0, end_codepoint=1))
    note_response = client.post('/api/v1/notes', json=note.model_dump(mode='json'), headers=command(headers, 'note'))
    assert note_response.status_code == 201, note_response.text
    route = dm.Route(id='route_impact', revision=1, title='Synthetic route', goal='Read exact old material',
        steps=[dm.RouteStep(id='step_read', title='Read', target=reference(original[1]), completion_rule='manual')])
    route_response = client.post('/api/v1/routes', json=route.model_dump(mode='json'), headers=command(headers, 'route'))
    assert route_response.status_code == 201, route_response.text
    changed = original[1].model_copy(update={'revision': 2, 'title': 'Synthetic changed conditions'})
    # This newly created explicit ref points at new, not old: ID-only candidate.
    candidate = dm.Lesson(id='lesson_candidate', revision=1, title='New revision child', objectives=[], block_refs=[reference(changed)])
    service.publish(identity.workspace_id, [changed, candidate], {})
    event = invalidation_id(database, changed.id)
    try:
        yield Case(database, identity, app, client, headers, original, service, event)
    finally:
        client.close()


def test_http_decisions_exact_id_only_correction_restart_and_owner_only_writes(case):
    before = table_hashes(case.database)
    view = case.client.get(case.path)
    assert view.status_code == 200, view.text
    assert view.headers['cache-control'] == 'no-store'
    value = view.json()
    assert value['target_decision_head'] is None
    assert value['pending_target_ids'] == ['course', 'lesson', 'lesson_candidate']
    assert 'note_impact' in value['affected_ids'] and 'block' in value['affected_ids']
    assert value['conservative_only_ids'] == ['lesson_candidate']
    assert table_hashes(case.database) == before
    first_body = case.write()
    first = case.decide(first_body)
    assert first.status_code == 200, first.text
    assert first.json()['classification'] == 'exact_ref'
    assert first.json()['target_body_sha256'] is None
    after = table_hashes(case.database)
    assert {name for name in before if before[name] != after[name]} == {'content_impact_decisions', 'content_impact_decision_heads'}
    assert case.decide(first_body).content == first.content
    assert table_hashes(case.database) == after
    assert case.decide({**first_body, 'reason': 'Changed same command.'}).status_code == 409
    assert case.decide(first_body, 'stale-key').status_code == 412
    corrected = case.decide(case.write(revision=1, decision='new_revision_required'), 'correct')
    assert corrected.status_code == 200 and corrected.json()['decision_revision'] == 2
    id_only = case.decide(case.write('lesson_candidate'), 'id-only')
    assert id_only.status_code == 200 and id_only.json()['classification'] == 'id_only_candidate'
    current = case.client.get(case.path, params={'target_id': 'lesson'}).json()
    assert current['pending_target_ids'] == ['course']
    assert current['action_required_target_ids'] == ['lesson']
    assert current['target_decision_head'] == 2
    assert [x['decision_revision'] for x in current['decisions']] == [1, 2]
    restarted = TestClient(create_app(case.database.settings), base_url=case.database.settings.origin)
    restarted.cookies.update(case.client.cookies)
    try:
        assert restarted.get(case.path, params={'target_id': 'lesson'}).json() == current
        replay = restarted.post(case.path + '/decisions', json=first_body, headers=command(case.headers, 'decide'))
        assert replay.content == first.content
    finally:
        restarted.close()


def test_target_revision_or_archive_invalidates_decision_without_erasing_history(case):
    body = case.write()
    receipt = case.decide(body)
    assert receipt.status_code == 200
    old_lesson = case.original[2]
    updated = old_lesson.model_copy(update={'revision': 2, 'title': 'Later unrelated title'})
    case.service.publish(case.identity.workspace_id, [updated], {})
    view = case.client.get(case.path, params={'target_id': 'lesson'})
    assert view.status_code == 200 and 'lesson' in view.json()['pending_target_ids']
    assert view.json()['decisions'] == [receipt.json()]
    assert case.decide(body).content == receipt.content
    next_receipt = case.decide(case.write(revision=1), 'current')
    assert next_receipt.status_code == 200 and next_receipt.json()['classification'] == 'id_only_candidate'
    with case.database.transaction() as conn:
        conn.execute("UPDATE objects SET lifecycle='archived' WHERE id='lesson'")
    assert 'lesson' in case.client.get(case.path).json()['pending_target_ids']
    assert case.decide(case.write(revision=2), 'archived').status_code == 412


def test_pagination_binds_event_target_limit_and_freezes_history_watermark(case):
    assert case.decide(case.write('course'), 'course').status_code == 200
    assert case.decide(case.write('lesson'), 'lesson').status_code == 200
    assert case.decide(case.write('lesson_candidate'), 'candidate').status_code == 200
    first = case.client.get(case.path, params={'limit': 1})
    assert first.status_code == 200 and first.json()['decisions'][0]['target_id'] == 'course'
    cursor = first.json()['next_cursor']
    assert cursor
    assert case.decide(case.write('course', revision=1), 'course-second').status_code == 200
    second = case.client.get(case.path, params={'limit': 1, 'cursor': cursor}).json()
    assert second['decisions'][0]['target_id'] == 'lesson'  # Later revision excluded from original page sequence.
    third = case.client.get(case.path, params={'limit': 1, 'cursor': second['next_cursor']}).json()
    assert third['decisions'][0]['target_id'] == 'lesson_candidate' and third['next_cursor'] is None
    before = table_hashes(case.database)
    for params in ({'limit': 2, 'cursor': cursor}, {'limit': 1, 'cursor': cursor, 'target_id': 'lesson'},
                   {'limit': 1, 'cursor': cursor + 'x'}):
        assert case.client.get(case.path, params=params).status_code == 422
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('query', ['unused=1', 'limit=1&limit=1', 'target_id=lesson&target_id=course',
    'limit=0', 'limit=101', 'limit=true', 'limit=1.0', 'limit=%2B1', 'cursor=', 'target_id=', 'target_id=note_impact', 'target_id=route_impact', 'target_id=block'])
def test_read_transport_and_wrong_owner_rejected_zero_write(case, query):
    before = table_hashes(case.database)
    response = case.client.get(case.path + '?' + query)
    assert response.status_code == (404 if query in {'target_id=note_impact', 'target_id=route_impact', 'target_id=block'} else 422), response.text
    assert table_hashes(case.database) == before


def test_read_body_rejected_and_missing_event_zero_write(case):
    before = table_hashes(case.database)
    assert case.client.request('GET', case.path, content=b'{}').status_code == 422
    assert case.client.get('/api/v1/content/impacts/event_missing').status_code == 404
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('fault,status', [('missing_key',400), ('csrf',403), ('origin',403), ('extra',422),
    ('bool_revision',422), ('extra_ref',422), ('blank_reason',422), ('long_reason',422), ('duplicate_artifacts',422),
    ('missing_nullable',422), ('wrong_sha',412), ('wrong_observed',412), ('note',404), ('changed_object',404),
    ('unknown_artifact',404), ('query',422), ('duplicate_key',400)])
def test_decision_transport_cas_membership_artifact_and_errors_are_zero_write(case, fault, status):
    body, headers, path = case.write(), command(case.headers, 'invalid'), case.path + '/decisions'
    if fault == 'missing_key':
        headers.pop('Idempotency-Key')
    elif fault == 'csrf':
        headers['X-CSRF-Token'] = 'invalid'
    elif fault == 'origin':
        headers['Origin'] = 'https://invalid.example'
    elif fault == 'extra':
        body['actor_session_id'] = 'forged'
    elif fault == 'bool_revision':
        body['expected_decision_revision'] = True
    elif fault == 'extra_ref':
        body['observed_ref']['secret'] = 'forged'
    elif fault == 'blank_reason':
        body['reason'] = ' \n'
    elif fault == 'long_reason':
        body['reason'] = 'x' * 2001
    elif fault == 'duplicate_artifacts':
        body['evidence_artifact_ids'] = ['same', 'same']
    elif fault == 'missing_nullable':
        body.pop('evidence_artifact_ids')
    elif fault == 'wrong_sha':
        body['expected_event_snapshot_sha256'] = '0' * 64
    elif fault == 'wrong_observed':
        body['observed_ref']['sha256'] = '0' * 64
    elif fault == 'note':
        body['target_id'] = 'note_impact'
    elif fault == 'changed_object':
        body['target_id'] = 'block'
    elif fault == 'unknown_artifact':
        body['evidence_artifact_ids'] = ['artifact_missing']
    elif fault == 'query':
        path += '?unused=1'
    elif fault == 'duplicate_key':
        headers = [*headers.items(), ('Idempotency-Key','other')]
    before = table_hashes(case.database)
    response = case.client.post(path, json=body, headers=headers)
    assert response.status_code == status, response.text
    assert table_hashes(case.database) == before


def test_two_http_sessions_compete_at_same_decision_head(case):
    body = case.write()
    def post(key):
        other = TestClient(case.app, base_url=case.database.settings.origin)
        other.cookies.update(case.client.cookies)
        try:
            return other.post(case.path + '/decisions', json=body, headers=command(case.headers,key))
        finally:
            other.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(post, ['tab-a', 'tab-b']))
    assert sorted(r.status_code for r in responses) == [200, 412]
    assert case.client.get(case.path, params={'target_id':'lesson'}).json()['target_decision_head'] == 1


@pytest.mark.parametrize('change', ['role', 'logout'])
def test_current_author_policy_precedes_original_ack(case, change):
    body = case.write()
    assert case.decide(body).status_code == 200
    endpoint = 'role' if change == 'role' else 'logout'
    response = case.client.post('/api/v1/session/' + endpoint, json={'role':'learner'} if change == 'role' else {},
                                headers=command(case.headers,'change'))
    assert response.status_code == 200
    before = table_hashes(case.database)
    assert case.client.get(case.path).status_code == (403 if change == 'role' else 401)
    assert case.decide(body).status_code == (403 if change == 'role' else 401)
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['event_missing', 'snapshot_sha', 'record_sha', 'record_command', 'head'])
def test_noncoordinated_tampering_fails_closed_read_and_replay(case, damage):
    body = case.write()
    assert case.decide(body).status_code == 200
    with case.database.transaction() as conn:
        if damage == 'event_missing':
            conn.execute('DROP TRIGGER content_impact_snapshot_no_update')
            conn.execute("UPDATE content_impact_snapshots SET snapshot_json='{}' WHERE event_id=?",(case.event_id,))
        elif damage == 'snapshot_sha':
            conn.execute('DROP TRIGGER content_impact_snapshot_no_update')
            conn.execute('UPDATE content_impact_snapshots SET snapshot_sha256=? WHERE event_id=?',('0'*64,case.event_id))
        elif damage == 'record_sha':
            conn.execute('DROP TRIGGER content_impact_decision_no_update')
            conn.execute('UPDATE content_impact_decisions SET record_sha256=?',('0'*64,))
        elif damage == 'record_command':
            conn.execute('DROP TRIGGER content_impact_decision_no_update')
            conn.execute("UPDATE content_impact_decisions SET command_key='forged'")
        else:
            conn.execute("UPDATE content_impact_decision_heads SET receipt_sha256=?",('0'*64,))
    before = table_hashes(case.database)
    assert case.client.get(case.path).status_code == 409
    assert case.decide(body).status_code == 409
    assert table_hashes(case.database) == before


def test_missing_new_snapshot_never_becomes_legacy(case):
    with case.database.transaction() as conn:
        conn.execute('DROP TRIGGER content_impact_snapshot_no_delete')
        conn.execute('DELETE FROM content_impact_snapshots WHERE event_id=?',(case.event_id,))
    before = table_hashes(case.database)
    assert case.client.get(case.path).status_code == 409
    assert table_hashes(case.database) == before


def test_explicit_legacy_event_readable_but_cannot_decide(case):
    # Controlled migration-era fixture keeps the original publication payload.
    with case.database.transaction() as conn:
        conn.execute('DROP TRIGGER content_impact_snapshot_no_delete')
        conn.execute('DELETE FROM content_impact_snapshots WHERE event_id=?',(case.event_id,))
        conn.execute('DROP TRIGGER content_impact_legacy_no_insert')
        conn.execute('INSERT INTO content_impact_legacy_events(event_id,payload_json) '
                     'SELECT id,payload_json FROM outbox WHERE id=?',(case.event_id,))
    view = case.client.get(case.path)
    assert view.status_code == 200, view.text
    assert view.json()['evidence_version'] == 'legacy_unverified'
    assert view.json()['event_snapshot_sha256'] is None and view.json()['exact_dependency_refs'] == []
    body = case.write()
    body['expected_event_snapshot_sha256'] = '0'*64
    before = table_hashes(case.database)
    result = case.decide(body)
    assert result.status_code == 409 and result.json()['error']['code'] == 'CONTENT_IMPACT_LEGACY_UNVERIFIED'
    assert table_hashes(case.database) == before


def test_failed_head_write_rolls_back_receipt_and_all_other_owners(case):
    body = case.write()
    with case.database.transaction() as conn:
        conn.execute("CREATE TRIGGER fail_impact_head BEFORE INSERT ON content_impact_decision_heads "
                     "BEGIN SELECT RAISE(ABORT,'synthetic head failure'); END")
    before = table_hashes(case.database)
    result = case.decide(body)
    assert result.status_code == 503
    assert table_hashes(case.database) == before


def test_database_append_only_constraints_and_receipt_sha(case):
    receipt = case.decide(case.write()).json()
    with case.database.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE content_impact_decisions SET command_key='new'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute('DELETE FROM content_impact_decisions')
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute('INSERT OR REPLACE INTO content_impact_decisions SELECT * FROM content_impact_decisions')
        row = conn.execute('SELECT record_json,record_sha256 FROM content_impact_decisions').fetchone()
        from services.api.app.application.content_impact_decisions import ImpactDecisionRecord
        record = ImpactDecisionRecord.model_validate_json(row['record_json'])
        assert canonical_bytes(record).decode() == row['record_json']
        assert metadata_sha256(record) == row['record_sha256']
    assert record.receipt.model_dump(mode='json') == receipt


def test_authorized_real_import_artifact_is_byte_bound_and_tamper_blocks_replay(case):
    upload = case.client.post('/api/v1/imports', files={'file': ('evidence.md', b'# Original synthetic review evidence\n', 'text/markdown')},
        data={'kind':'markdown'}, headers=command(case.headers,'artifact-upload'))
    assert upload.status_code == 202, upload.text
    assert case.app.state.import_worker.run_once()
    with case.database.connect() as conn:
        artifact = conn.execute('SELECT id,blob_sha256 FROM artifacts ORDER BY rowid LIMIT 1').fetchone()
    assert artifact is not None
    downloaded = case.client.get('/api/v1/artifacts/' + artifact['id'] + '/download')
    assert downloaded.status_code == 200, downloaded.text
    body = case.write()
    body['evidence_artifact_ids'] = [artifact['id']]
    receipt = case.decide(body)
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()['evidence_artifacts'] == [{'id':artifact['id'],'sha256':artifact['blob_sha256']}]
    assert case.client.get(case.path).status_code == 200
    digest = artifact['blob_sha256']
    path = case.database.settings.data_dir / 'blobs' / digest[:2] / digest
    path.write_bytes(b'corrupted original evidence bytes')
    before = table_hashes(case.database)
    assert case.client.get(case.path).status_code == 409
    assert case.decide(body).status_code == 409
    assert table_hashes(case.database) == before


def test_block_target_binds_actual_bytes_and_concept_id_stays_conservative(case):
    concept = case.original[0].model_copy(update={'revision':2, 'title':'Changed concept definition'})
    case.service.publish(case.identity.workspace_id, [concept], {})
    event_id = invalidation_id(case.database, concept.id)
    path = f'/api/v1/content/impacts/{event_id}'
    read = case.client.get(path, params={'target_id':'block'})
    assert read.status_code == 200
    block_ref = case.service.current(case.identity.workspace_id, 'block')
    body = dict(target_id='block', observed_ref=block_ref.model_dump(mode='json'),
        expected_event_snapshot_sha256=read.json()['event_snapshot_sha256'], expected_decision_revision=0,
        decision='no_revision_needed', reason='Synthetic explicit ID-only judgment.', evidence_artifact_ids=[])
    receipt = case.client.post(path+'/decisions', json=body, headers=command(case.headers,'block-decision'))
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()['classification'] == 'id_only_candidate'
    digest = case.original[1].body_sha256
    assert receipt.json()['target_body_sha256'] == digest
    (case.database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'corrupt body')
    before = table_hashes(case.database)
    assert case.client.get(path).status_code == 409
    assert case.client.post(path+'/decisions', json=body, headers=command(case.headers,'block-decision')).status_code == 409
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book', 'assisted'])
def test_active_attempt_policy_blocks_report_and_replay(case, mode):
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    fixture = assessment_fixture('impactpolicy')
    import_fixture(case.database, case.identity, fixture, 'assessment-import')
    body = case.write()
    assert case.decide(body).status_code == 200
    attempt = case.client.post(f'/api/v1/assessments/{fixture.assessment.id}/attempts',
        json={'assessment_ref':reference(fixture.assessment).model_dump(mode='json'),'mode':mode},
        headers=command(case.headers,'start-assessment'))
    assert attempt.status_code == 201, attempt.text
    before = table_hashes(case.database)
    assert case.client.get(case.path).status_code == 409
    assert case.decide(body).status_code == 409
    assert table_hashes(case.database) == before


def test_cross_workspace_event_and_target_cannot_be_read(case):
    with case.database.transaction() as conn:
        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','Synthetic','2026-09-28T00:00:00Z')")
        conn.execute("UPDATE local_sessions SET workspace_id='workspace_other' WHERE id=?",(case.identity.id,))
    before = table_hashes(case.database)
    assert case.client.get(case.path).status_code == 404
    assert table_hashes(case.database) == before


def test_read_is_sqlite_query_only_and_holds_the_policy_writer_gate(case, monkeypatch):
    from services.api.app.application import content_impact_decisions as module
    from threading import Event

    entered, release = Event(), Event()
    real = module.impact_snapshot
    def checked(conn, workspace_id, event_id):
        assert conn.execute('PRAGMA query_only').fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            conn.execute("UPDATE workspace SET title='forbidden read mutation'")
        entered.set()
        assert release.wait(5)
        return real(conn, workspace_id, event_id)
    monkeypatch.setattr(module, 'impact_snapshot', checked)
    before = table_hashes(case.database)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(case.client.get, case.path)
        assert entered.wait(5)
        try:
            with case.database.connect(busy_timeout_ms=1) as conn:
                with pytest.raises(sqlite3.OperationalError, match='locked'):
                    conn.execute('BEGIN IMMEDIATE')
        finally:
            release.set()
        assert pending.result(5).status_code == 200
    assert table_hashes(case.database) == before


def test_real_loopback_http_server_decision_and_restart_receipt(case, record_property):
    """Actual TCP/HTTP serving, separate from TestClient's in-process transport."""
    from dataclasses import replace
    import socket
    from threading import Thread
    import time
    import httpx
    import uvicorn

    original = None
    for restart in range(2):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        settings = replace(case.database.settings, port=listener.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(create_app(settings), host='127.0.0.1', port=settings.port,
            lifespan='off', log_level='error', access_log=False, ws='none'))
        thread = Thread(target=server.run, kwargs={'sockets':[listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with httpx.Client(base_url=settings.origin, cookies=dict(case.client.cookies), trust_env=False, timeout=5) as client:
                read = client.get(case.path, params={'target_id':'lesson'})
                assert read.status_code == 200 and read.headers['cache-control'] == 'no-store'
                body = dict(target_id='lesson', observed_ref=reference(case.original[2]).model_dump(mode='json'),
                    expected_event_snapshot_sha256=read.json()['event_snapshot_sha256'], expected_decision_revision=0,
                    decision='no_revision_needed', reason='Synthetic loopback decision.', evidence_artifact_ids=[])
                result = client.post(case.path+'/decisions', json=body,
                    headers=command({'Origin':settings.origin,'X-CSRF-Token':case.identity.csrf_token},'loopback-original'))
                assert result.status_code == 200, result.text
                if restart == 0:
                    original = result.content
                    record_property('event_snapshot_sha256', result.json()['event_snapshot_sha256'])
                    record_property('request_sha256', result.json()['request_sha256'])
                    record_property('receipt_sha256', result.json()['receipt_sha256'])
                else:
                    assert result.content == original
                    assert read.json()['decisions'] == [result.json()]
                    assert read.json()['target_decision_head'] == 1
        finally:
            server.should_exit = True
            thread.join(5)
            listener.close()
            assert not thread.is_alive()
