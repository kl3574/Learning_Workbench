"""Restore numeric protocol against actual composition, HTTP and SQLite.

Source text and author intent are synthetic. Runtime preview inspects the real
closure; these cases do not execute arithmetic or claim mathematical approval.
"""
from copy import deepcopy
from dataclasses import dataclass

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.main import create_app
from tests.integration.test_authoring_http import command, session
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@dataclass(repr=False)
class NumericHTTP:
    database: object
    identity: object
    app: object
    client: object
    headers: dict
    snapshot: dict
    block: object
    raw: bytes
    body: dict

    @property
    def draft_path(self):
        return '/api/v1/content/restore-drafts/' + self.snapshot['candidate']['draft_id']

    @property
    def preview_path(self):
        return self.draft_path + '/numeric-checks'


def bound_material(text):
    def span(quote):
        start = text.index(quote)
        return {'start_codepoint': start, 'end_codepoint': start + len(quote), 'quote': quote}
    return {
        'version': 'restore-numeric-material-v1',
        'symbols': [{'name': 'x', 'tex': 'x', 'domain': 'finite real', 'dimension': 'unitless'}],
        'plan': {'version': 'finite-arithmetic-v1', 'variables': [{'name': 'x', 'value': 2.0, 'unit': '1'}],
                 'assertions': [{'id': 'assert_sum', 'expression': 'x+1', 'expected': 3.0,
                                 'atol': 0.0, 'rtol': 0.0, 'unit': '1'}], 'seed': None},
        'variable_bindings': [{'variable_name': 'x', 'value_source': span('2')}],
        'assertion_bindings': [{'assertion_id': 'assert_sum', 'expression_source': span('x+1'),
                               'expected_source': span('3')}],
        'reason': 'Synthetic mapping only; no academic validation.',
    }


@pytest.fixture
def numeric_http(tmp_path):
    database, identity, app, client, headers = session(tmp_path)
    try:
        text = '🧮 原文 e\u0301\nGiven x=2, formula x+1 has expected 3. Symbol-only π is not a decimal.\n'
        raw = text.encode('utf-8')
        block = dm.ContentBlock(id='numeric_original', revision=1, kind='worked_example',
            title='Synthetic historical example', body_path='content/numeric-original.md',
            body_sha256=sha256_bytes(raw), concepts=[], citations=[], depends_on=[])
        content = ContentService(database)
        old = content.publish(identity.workspace_id, [block], {block.body_path: raw})[0]
        current = content.publish(identity.workspace_id,
            [block.model_copy(update={'revision': 2, 'title': 'Distinct current revision'})],
            {block.body_path: raw})[0]
        created = client.post('/api/v1/content/restore-drafts', json={
            'source_ref': old.model_dump(mode='json'), 'expected_current_ref': current.model_dump(mode='json'),
            'reason': 'Synthetic explicit restoration.'}, headers=command(headers, 'restore'))
        assert created.status_code == 201, created.text
        path = '/api/v1/content/restore-drafts/' + created.json()['candidate']['draft_id']
        snapshot = client.get(path)
        assert snapshot.status_code == 200, snapshot.text
        yield NumericHTTP(database, identity, app, client, headers, snapshot.json(), block, raw,
                          {'candidate': snapshot.json()['candidate'], 'material': bound_material(text)})
    finally:
        client.close()


def preview(case, key='preview'):
    response = case.client.post(case.preview_path, json=case.body, headers=command(case.headers, key))
    assert response.status_code == 201, response.text
    value = response.json()
    assert value['owner'] == 'authoring_restore' and value['decision'] == 'pending'
    assert value['job'] is value['result'] is value['job_revision'] is None
    return value, '/api/v1/content/restore-numeric-checks/' + value['id']


def decision(view, action='decline'):
    return {'expected_revision': view['revision'], 'operation_sha256': view['operation_sha256'], 'decision': action}


def no_write_response(case, method, path, *, status, client=None, **kwargs):
    before = table_hashes(case.database)
    response = (client or case.client).request(method, path, **kwargs)
    assert response.status_code == status, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert table_hashes(case.database) == before
    return response


def test_actual_preview_decline_original_ack_and_restart_are_distinct_zero_write_reads(numeric_http):
    case = numeric_http
    assert case.snapshot['numeric_material'] is None and case.snapshot['numeric_check_ids'] == []
    no_write_response(case, 'GET', case.draft_path, status=200)
    view, path = preview(case)
    snapshot = no_write_response(case, 'GET', case.draft_path, status=200).json()
    assert snapshot['candidate'] == case.snapshot['candidate']
    assert snapshot['body_markdown'].encode('utf-8') == case.raw
    assert snapshot['numeric_material']['material'] == case.body['material']
    assert snapshot['numeric_material']['numeric_material_sha256'] == view['numeric_material_sha256']
    assert snapshot['numeric_check_ids'] == [view['id']]
    with case.database.connect() as conn:
        assert conn.execute("SELECT count(*) FROM jobs WHERE kind='authoring_numeric_check'").fetchone()[0] == 0
    declined = case.client.post(path + '/decision', json=decision(view), headers=command(case.headers, 'decline'))
    assert declined.status_code == 200 and declined.json()['job'] is None
    current = no_write_response(case, 'GET', path, status=200).json()
    assert current['revision'] == 2 and current['decision'] == 'decline'
    assert no_write_response(case, 'POST', case.preview_path, status=201, json=case.body,
        headers=command(case.headers, 'preview')).json() == view
    assert no_write_response(case, 'POST', path + '/decision', status=200, json=decision(view),
        headers=command(case.headers, 'decline')).json() == declined.json()
    # A fresh application composition reopens the same database. Workers are
    # intentionally not started during the all-table zero-write measurement;
    # their unrelated pending outbox consumption is not a write by this GET.
    restarted = TestClient(create_app(case.database.settings), base_url=case.database.settings.origin)
    try:
        restarted.cookies.update(case.client.cookies)
        restored = no_write_response(case, 'GET', path, status=200, client=restarted).json()
        assert restored == current
        assert no_write_response(case, 'GET', case.draft_path, status=200, client=restarted).json() == snapshot
    finally:
        restarted.close()


@pytest.mark.parametrize('change', ['role', 'logout', 'independent', 'assisted', 'open_book'])
def test_actual_current_permissions_guard_read_and_both_original_ack_replays(numeric_http, change):
    case = numeric_http
    view, path = preview(case)
    request = decision(view)
    assert case.client.post(path + '/decision', json=request, headers=command(case.headers, 'decline')).status_code == 200
    if change in {'role', 'logout'}:
        response = case.client.post('/api/v1/session/' + ('role' if change == 'role' else 'logout'),
            json={'role': 'learner'} if change == 'role' else {}, headers=command(case.headers, 'permission-change'))
        assert response.status_code == 200
        expected = 403 if change == 'role' else 401
    else:
        from services.api.app.application.assessment import AssessmentService
        from services.api.app.assessment_dto import AssessmentAttemptCreate
        from services.api.app.infrastructure.content_repository import reference
        from tests.assessment_fixtures import assessment_fixture
        from tests.integration.test_assessment_attempts import import_fixture
        fixture = assessment_fixture('restorenumericpolicy')
        import_fixture(case.database, case.identity, fixture, 'assessment-material')
        AssessmentService(case.database).create_attempt(case.identity, fixture.assessment.id,
            AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=change), 'attempt')
        expected = 409
    results = [no_write_response(case, 'GET', path, status=expected),
        no_write_response(case, 'GET', case.draft_path, status=expected),
        no_write_response(case, 'POST', case.preview_path, status=expected, json=case.body,
                          headers=command(case.headers, 'preview')),
        no_write_response(case, 'POST', path + '/decision', status=expected, json=request,
                          headers=command(case.headers, 'decline'))]
    assert all(case.body['material']['reason'] not in response.text and 'numeric_material' not in response.text
               for response in results)


@pytest.mark.parametrize('fault', ['quote', 'number', 'nondecimal', 'past_body', 'utf16_offset',
                                   'unknown_runtime', 'unknown_actor', 'bool_position', 'revision', 'hash'])
def test_actual_source_numeric_binding_rejects_invalid_material_without_writes(numeric_http, fault):
    case = numeric_http
    body = deepcopy(case.body)
    span = body['material']['variable_bindings'][0]['value_source']
    expected = 409
    if fault == 'quote':
        span['quote'] = '9'
    elif fault == 'number':
        body['material']['plan']['variables'][0]['value'] = 9.0
    elif fault == 'nondecimal':
        at = case.raw.decode('utf-8').index('π')
        span.update(start_codepoint=at, end_codepoint=at + 1, quote='π')
    elif fault == 'past_body':
        span.update(start_codepoint=len(case.raw), end_codepoint=len(case.raw) + 1)
        expected = 422
    elif fault == 'utf16_offset':
        span['start_codepoint'] += 1
        span['end_codepoint'] += 1
    elif fault in {'unknown_runtime', 'unknown_actor'}:
        body['runtime' if fault == 'unknown_runtime' else 'actor_session_id'] = 'caller-controlled'
        expected = 422
    elif fault == 'bool_position':
        span['start_codepoint'] = False
        expected = 422
    elif fault == 'revision':
        body['candidate']['draft_revision'] = 2
        expected = 412
    else:
        body['candidate']['candidate_sha256'] = '0' * 64
    no_write_response(case, 'POST', case.preview_path, status=expected, json=body,
                      headers=command(case.headers, 'invalid'))
    assert case.client.get(case.draft_path).json()['numeric_material'] is None


def test_actual_material_is_immutable_and_foreign_owner_cannot_reuse_preview(numeric_http):
    case = numeric_http
    original, path = preview(case)
    changed = deepcopy(case.body)
    changed['material']['reason'] += ' Changed intent.'
    for key in ['preview', 'different-key']:
        no_write_response(case, 'POST', case.preview_path, status=409, json=changed,
                          headers=command(case.headers, key))
    no_write_response(case, 'GET', '/api/v1/authoring/numeric-checks/' + original['id'], status=404)
    no_write_response(case, 'POST', '/api/v1/authoring/numeric-checks/' + original['id'] + '/decision',
                      status=404, json=decision(original), headers=command(case.headers, 'foreign-owner'))
    assert no_write_response(case, 'GET', path, status=200).json() == original


def test_actual_current_race_preserves_original_ack_but_refuses_new_authorization(numeric_http):
    case = numeric_http
    original, path = preview(case)
    ContentService(case.database).publish(case.identity.workspace_id,
        [case.block.model_copy(update={'revision': 3, 'title': 'Concurrent current'})],
        {case.block.body_path: case.raw})
    assert no_write_response(case, 'POST', case.preview_path, status=201, json=case.body,
        headers=command(case.headers, 'preview')).json() == original
    no_write_response(case, 'POST', case.preview_path, status=412, json=case.body,
                      headers=command(case.headers, 'new-preview'))
    no_write_response(case, 'POST', path + '/decision', status=412, json=decision(original, 'approve_once'),
                      headers=command(case.headers, 'approve'))
    assert no_write_response(case, 'GET', path, status=200).json()['job'] is None


def test_actual_corrupt_source_cannot_be_read_or_replayed_and_is_never_repaired(numeric_http):
    case = numeric_http
    original, path = preview(case)
    digest = case.block.body_sha256
    source = case.database.settings.data_dir / 'blobs' / digest[:2] / digest
    source.write_bytes(b'Synthetic corrupted immutable body')
    for request_path in [path, case.draft_path]:
        no_write_response(case, 'GET', request_path, status=409)
    no_write_response(case, 'POST', case.preview_path, status=409, json=case.body,
                      headers=command(case.headers, 'preview'))
    no_write_response(case, 'POST', path + '/decision', status=409, json=decision(original),
                      headers=command(case.headers, 'decline'))
    assert source.read_bytes() == b'Synthetic corrupted immutable body'


def test_actual_foreign_workspace_cannot_discover_or_replay_original_numeric_material(numeric_http):
    case = numeric_http
    original, path = preview(case)
    with case.database.transaction() as conn:
        workspace = dict(conn.execute('SELECT * FROM workspace WHERE id=?', (case.identity.workspace_id,)).fetchone())
        workspace['id'] = 'workspace_foreign_numeric'
        conn.execute('INSERT INTO workspace(' + ','.join(workspace) + ') VALUES(' +
                     ','.join('?' for _ in workspace) + ')', tuple(workspace.values()))
        conn.execute('UPDATE local_sessions SET workspace_id=? WHERE id=?', (workspace['id'], case.identity.id))
    for request_path in [case.draft_path, path]:
        no_write_response(case, 'GET', request_path, status=404)
    no_write_response(case, 'POST', case.preview_path, status=404, json=case.body,
                      headers=command(case.headers, 'preview'))
    no_write_response(case, 'POST', path + '/decision', status=404, json=decision(original),
                      headers=command(case.headers, 'foreign-decision'))


def test_actual_other_kind_stays_explicitly_unbound_and_cannot_borrow_numeric_owner(numeric_http):
    case = numeric_http
    content = ContentService(case.database)
    block = case.block.model_copy(update={'id': 'numeric_other_kind', 'body_path': 'content/non-numeric.md', 'kind': 'theorem'})
    old = content.publish(case.identity.workspace_id, [block], {block.body_path: case.raw})[0]
    current = content.publish(case.identity.workspace_id, [block.model_copy(update={'revision': 2})], {block.body_path: case.raw})[0]
    created = case.client.post('/api/v1/content/restore-drafts', json={
        'source_ref': old.model_dump(mode='json'), 'expected_current_ref': current.model_dump(mode='json'),
        'reason': 'Synthetic nonnumeric restore.'}, headers=command(case.headers, 'other-kind'))
    assert created.status_code == 201, created.text
    candidate = created.json()['candidate']
    path = '/api/v1/content/restore-drafts/' + candidate['draft_id']
    snapshot = no_write_response(case, 'GET', path, status=200).json()
    assert snapshot['numeric_material'] is None and snapshot['numeric_check_ids'] == []
    response = no_write_response(case, 'POST', path + '/numeric-checks', status=409,
        json={'candidate': candidate, 'material': case.body['material']}, headers=command(case.headers, 'other-numeric'))
    assert response.json()['error']['code'] == 'RESTORE_NUMERIC_KIND_UNSUPPORTED'
