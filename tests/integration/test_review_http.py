"""Actual protected review HTTP, real SQLite/Jobs/worker; decisions are synthetic intent."""
from dataclasses import dataclass

import pytest

from tests.integration.test_authoring_http import session, command
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@dataclass(repr=False)
class ReviewHttpCase:
    database: object
    identity: object
    app: object
    client: object
    headers: dict
    candidate: dict


@pytest.fixture
def prepared_review_http(tmp_path):
    database, identity, app, client, headers = session(tmp_path)
    try:
        uploaded = client.post('/api/v1/imports', files={'file': ('review-source.md', b'# Synthetic review input\n\nUnreviewed body.\n', 'text/markdown')},
            data={'kind': 'markdown'}, headers=command(headers, 'review-import'))
        assert uploaded.status_code == 202, uploaded.text
        assert app.state.import_worker.run_once()
        preview = client.get('/api/v1/imports/' + uploaded.json()['import_id'])
        assert preview.status_code == 200, preview.text
        drafts = [client.get('/api/v1/drafts/' + value).json() for value in preview.json()['preview_refs']]
        draft = next(item for item in drafts if item['kind'] == 'block')
        candidate = {'draft_id': draft['id'], 'draft_revision': draft['revision'], 'entity': 'block',
                     'candidate_sha256': draft['candidate_sha256']}
        yield ReviewHttpCase(database, identity, app, client, headers, candidate)
    finally:
        client.close()


def test_real_http_review_worker_receipt_and_explicit_rejected_decision(prepared_review_http):
    case = prepared_review_http
    path = '/api/v1/drafts/' + case.candidate['draft_id'] + '/review'
    body = {'expected_revision': 1, 'checks': ['structure', 'numerical_examples', 'sources', 'mathematics'],
            'reviewer_note': 'Synthetic HTTP intent; no real content approval.'}
    created = case.client.post(path, json=body, headers=command(case.headers, 'review-create'))
    assert created.status_code == 202, created.text
    original = created.json()
    assert original['status'] == 'queued'
    receipt_path = '/api/v1/reviews/' + original['id']
    pending = case.client.get(receipt_path)
    assert pending.status_code == 409 and pending.json()['error']['code'] == 'REVIEW_NOT_READY'
    assert case.app.state.review_worker.run_once()
    ready = case.client.get(receipt_path)
    assert ready.status_code == 200, ready.text
    machine = ready.json()
    assert machine['candidate'] == case.candidate and machine['revision'] == 1
    assert machine['structural'] == 'PASS'
    assert machine['mathematical'] == machine['sources'] == machine['independent_pedagogy'] == 'NOT_RUN'
    assert ready.headers['cache-control'] == 'no-store'
    assert len(machine['evidence_paths']) == 1
    report = case.client.get(machine['evidence_paths'][0])
    assert report.status_code == 200, report.text
    assert report.headers['cache-control'] == 'no-store'
    assert report.headers['etag'].startswith('"') and report.headers['content-disposition'].startswith('attachment;')
    control = case.client.get('/api/v1/jobs/' + original['id'])
    assert control.status_code == 200 and control.json()['status'] == 'completed'
    assert control.json()['result_refs'] == [] and body['reviewer_note'] not in control.text
    request = {'expected_revision': 1, 'candidate_sha256': case.candidate['candidate_sha256'],
               'mathematical': 'REJECTED', 'sources': 'REJECTED',
               'reason': 'Synthetic rejection fixture, not actual human content review.', 'evidence_artifact_ids': []}
    decision = case.client.post(receipt_path + '/decision', json=request, headers=command(case.headers, 'decision'))
    assert decision.status_code == 200, decision.text
    human = decision.json()
    assert human['revision'] == 2 and human['reviewer'] == case.identity.id
    assert human['structural'] == machine['structural'] and human['independent_pedagogy'] == 'NOT_RUN'
    assert human['mathematical'] == human['sources'] == 'REJECTED'
    assert case.client.get(receipt_path).json() == human
    assert case.client.post(receipt_path + '/decision', json=request, headers=command(case.headers, 'decision')).json() == human
    replay = case.client.post(path, json=body, headers=command(case.headers, 'review-create'))
    assert replay.status_code == 202 and replay.json() == original
    stale = case.client.post(receipt_path + '/decision', json=request, headers=command(case.headers, 'other-decision'))
    assert stale.status_code == 412
    with case.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM review_revisions').fetchone()[0] == 2
        assert connection.execute('SELECT status FROM drafts WHERE id=?', (case.candidate['draft_id'],)).fetchone()[0] == 'draft'


def review_create(case):
    path = '/api/v1/drafts/' + case.candidate['draft_id'] + '/review'
    body = {'expected_revision': 1, 'checks': ['structure'], 'reviewer_note': 'Synthetic private review note'}
    response = case.client.post(path, json=body, headers=command(case.headers, 'create'))
    assert response.status_code == 202, response.text
    return path, body, '/api/v1/reviews/' + response.json()['id']


def rejected_decision(case):
    return {'expected_revision': 1, 'candidate_sha256': case.candidate['candidate_sha256'],
            'mathematical': 'REJECTED', 'sources': 'REJECTED', 'reason': 'Synthetic explicit rejection',
            'evidence_artifact_ids': []}


@pytest.mark.parametrize('endpoint', ['create', 'decision', 'read'])
@pytest.mark.parametrize('fault', ['unknown_query', 'duplicate_query', 'duplicate_identity_header'])
def test_review_http_rejects_ambiguous_transport_without_mutation(prepared_review_http, endpoint, fault):
    case = prepared_review_http
    create_path, create_body, read_path = review_create(case)
    assert case.app.state.review_worker.run_once()
    path = create_path if endpoint == 'create' else read_path + ('/decision' if endpoint == 'decision' else '')
    headers = list(command(case.headers, 'bad-transport').items())
    expected = 422
    if fault == 'unknown_query':
        path += '?unused=1'
    elif fault == 'duplicate_query':
        path += '?revision=1&revision=1'
    else:
        headers.append(('Idempotency-Key', 'another-command'))
        expected = 400
    before = table_hashes(case.database)
    result = (case.client.get(path, headers=headers) if endpoint == 'read' else
              case.client.post(path, json=create_body if endpoint == 'create' else rejected_decision(case), headers=headers))
    assert result.status_code == expected, result.text
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('endpoint', ['create', 'decision'])
@pytest.mark.parametrize('fault', ['missing_key', 'bad_key', 'csrf', 'origin', 'extra_body', 'bool_revision'])
def test_review_http_write_guards_and_strict_request(prepared_review_http, endpoint, fault):
    case = prepared_review_http
    path, body, read_path = review_create(case)
    assert case.app.state.review_worker.run_once()
    if endpoint == 'decision':
        path, body = read_path + '/decision', rejected_decision(case)
    headers = command(case.headers, 'invalid-write')
    expected = 400
    if fault == 'missing_key':
        headers.pop('Idempotency-Key')
    elif fault == 'bad_key':
        headers['Idempotency-Key'] = 'invalid key'
    elif fault in {'csrf', 'origin'}:
        headers['X-CSRF-Token' if fault == 'csrf' else 'Origin'] = 'synthetic-invalid' if fault == 'csrf' else 'https://invalid.example'
        expected = 403
    else:
        body['reviewer' if fault == 'extra_body' else 'expected_revision'] = 'client-claimed-actor' if fault == 'extra_body' else True
        expected = 422
    before = table_hashes(case.database)
    result = case.client.post(path, json=body, headers=headers)
    assert result.status_code == expected, result.text
    assert 'client-claimed-actor' not in result.text and 'synthetic-invalid' not in result.text
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('change', ['role', 'logout'])
def test_current_session_controls_private_receipt_ack_and_report(prepared_review_http, change):
    case = prepared_review_http
    path, body, read_path = review_create(case)
    assert case.app.state.review_worker.run_once()
    receipt = case.client.get(read_path).json()
    decision = rejected_decision(case)
    assert case.client.post(read_path + '/decision', json=decision, headers=command(case.headers, 'decision')).status_code == 200
    route = '/api/v1/session/role' if change == 'role' else '/api/v1/session/logout'
    result = case.client.post(route, json={'role': 'learner'} if change == 'role' else {}, headers=command(case.headers, 'change'))
    assert result.status_code == 200
    before = table_hashes(case.database)
    denied = [case.client.get(read_path), case.client.get(receipt['evidence_paths'][0]),
              case.client.post(path, json=body, headers=command(case.headers, 'create')),
              case.client.post(read_path + '/decision', json=decision, headers=command(case.headers, 'decision'))]
    assert [item.status_code for item in denied] == [403 if change == 'role' else 401] * 4
    assert all(body['reviewer_note'] not in item.text for item in denied)
    assert table_hashes(case.database) == before


def test_review_safe_job_control_and_cancel_after_role_change(prepared_review_http):
    case = prepared_review_http
    _, body, read_path = review_create(case)
    identifier = read_path.rsplit('/', 1)[1]
    changed = case.client.post('/api/v1/session/role', json={'role': 'learner'}, headers=command(case.headers, 'learner'))
    assert changed.status_code == 200
    path = '/api/v1/jobs/' + identifier
    current = case.client.get(path)
    assert current.status_code == 200 and current.json()['result_refs'] == []
    assert body['reviewer_note'] not in current.text
    request = {'expected_revision': current.json()['revision']}
    cancelled = case.client.post(path + '/cancel', json=request, headers=command(case.headers, 'cancel'))
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
    assert case.client.post(path + '/cancel', json=request, headers=command(case.headers, 'cancel')).json() == cancelled.json()
    assert not case.app.state.review_worker.run_once()
    with case.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM review_revisions').fetchone()[0] == 0


@pytest.mark.parametrize('mode', ['independent', 'assisted', 'open_book'])
def test_real_active_assessment_policy_blocks_review_subject_http(prepared_review_http, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    case = prepared_review_http
    path, body, read_path = review_create(case)
    assert case.app.state.review_worker.run_once()
    receipt = case.client.get(read_path).json()
    fixture = assessment_fixture('reviewhttp')
    import_fixture(case.database, case.identity, fixture, 'assessment-material')
    AssessmentService(case.database).create_attempt(case.identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    before = table_hashes(case.database)
    results = [case.client.get(read_path), case.client.get(receipt['evidence_paths'][0]),
               case.client.post(path, json=body, headers=command(case.headers, 'create')),
               case.client.post(read_path + '/decision', json=rejected_decision(case), headers=command(case.headers, 'decision'))]
    assert [item.status_code for item in results] == [403] * 4
    assert case.client.get('/api/v1/jobs/' + read_path.rsplit('/', 1)[1]).status_code == 200
    assert table_hashes(case.database) == before
