"""Actual HTTP publication of synthetic reviewed input; no real academic approval."""
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def approve_for_publication(case):
    candidate = case.candidate
    created = case.client.post('/api/v1/drafts/' + candidate['draft_id'] + '/review',
        json={'expected_revision': candidate['draft_revision'],
              'checks': ['structure', 'numerical_examples', 'mathematics', 'sources'],
              'reviewer_note': 'Synthetic HTTP publication protocol only; no actual content approval.'},
        headers=command(case.headers, 'publish-review'))
    assert created.status_code == 202, created.text
    assert case.app.state.review_worker.run_once()
    path = '/api/v1/reviews/' + created.json()['id']
    machine = case.client.get(path)
    assert machine.status_code == 200, machine.text
    assert machine.json()['structural'] == 'PASS'
    decided = case.client.post(path + '/decision', json={
        'expected_revision': machine.json()['revision'],
        'candidate_sha256': candidate['candidate_sha256'],
        'mathematical': 'NOT_APPLICABLE', 'sources': 'APPROVED',
        'reason': 'Synthetic plain text fixture; explicit protocol choice, not real source certification.',
        'evidence_artifact_ids': []}, headers=command(case.headers, 'publish-human'))
    assert decided.status_code == 200, decided.text
    draft = case.client.get('/api/v1/drafts/' + candidate['draft_id'])
    assert draft.status_code == 200, draft.text
    body = {'expected_revision': candidate['draft_revision'],
        'expected_content_sha256': candidate['candidate_sha256'],
        'review_receipt_id': created.json()['id'],
        'acknowledged_warning_codes': sorted({warning['code'] for warning in draft.json()['warnings']
                                            if warning['severity'] == 'warning'})}
    return body, draft.json(), decided.json()


def test_actual_http_publish_returns_persisted_ref_and_original_201_on_replay(prepared_review_http):
    case = prepared_review_http
    body, original_draft, original_human = approve_for_publication(case)
    path = '/api/v1/drafts/' + case.candidate['draft_id'] + '/publish'
    response = case.client.post(path, json=body, headers=command(case.headers, 'publish-once'))
    assert response.status_code == 201, response.text
    ref = dm.ContentRef.model_validate_json(response.content)
    assert ref.entity == 'block' and ref.revision == 1
    assert response.headers['cache-control'] == 'no-store'
    metadata = case.client.get(f'/api/v1/blocks/{ref.id}?revision={ref.revision}')
    assert metadata.status_code == 200, metadata.text
    assert metadata_sha256(dm.ContentBlock.model_validate_json(metadata.content)) == ref.sha256
    text = case.client.get(f'/api/v1/blocks/{ref.id}/body?revision={ref.revision}')
    assert text.status_code == 200
    assert text.content == original_draft['payload']['body_markdown'].encode('utf-8')
    replay = case.client.post(path, json=body, headers=command(case.headers, 'publish-once'))
    assert replay.status_code == 201 and replay.json() == response.json()
    assert case.client.get('/api/v1/drafts/' + case.candidate['draft_id']).json() == original_draft
    assert case.client.get('/api/v1/reviews/' + body['review_receipt_id']).json() == original_human
    assert case.client.get('/api/v1/courses').json()['items'] == []
    with case.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM objects').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM revisions').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM review_revisions').fetchone()[0] == 2


def test_new_publication_requires_current_human_approval_and_keeps_machine_history(prepared_review_http):
    case = prepared_review_http
    body, _, human = approve_for_publication(case)
    rejected = case.client.post('/api/v1/reviews/' + body['review_receipt_id'] + '/decision', json={
        'expected_revision': human['revision'], 'candidate_sha256': case.candidate['candidate_sha256'],
        'mathematical': 'REJECTED', 'sources': 'REJECTED',
        'reason': 'Synthetic later rejection before publication.', 'evidence_artifact_ids': []},
        headers=command(case.headers, 'reject-before-publish'))
    assert rejected.status_code == 200, rejected.text
    response = case.client.post('/api/v1/drafts/' + case.candidate['draft_id'] + '/publish',
        json=body, headers=command(case.headers, 'publish-rejected'))
    assert response.status_code == 409, response.text
    assert case.client.get('/api/v1/reviews/' + body['review_receipt_id']).json() == rejected.json()
    with case.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM objects').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM review_revisions').fetchone()[0] == 3


def test_committed_publication_ack_is_historical_after_later_review_rejection(prepared_review_http):
    case = prepared_review_http
    body, _, human = approve_for_publication(case)
    path = '/api/v1/drafts/' + case.candidate['draft_id'] + '/publish'
    first = case.client.post(path, json=body, headers=command(case.headers, 'historical-publish'))
    assert first.status_code == 201, first.text
    rejected = case.client.post('/api/v1/reviews/' + body['review_receipt_id'] + '/decision', json={
        'expected_revision': human['revision'], 'candidate_sha256': case.candidate['candidate_sha256'],
        'mathematical': 'REJECTED', 'sources': 'REJECTED',
        'reason': 'Synthetic later decision; original publication is a historical fact.',
        'evidence_artifact_ids': []}, headers=command(case.headers, 'reject-after-publish'))
    assert rejected.status_code == 200, rejected.text
    replay = case.client.post(path, json=body, headers=command(case.headers, 'historical-publish'))
    assert replay.status_code == 201 and replay.json() == first.json()
    other = case.client.post(path, json=body, headers=command(case.headers, 'new-publish-after-reject'))
    assert other.status_code == 409, other.text
    assert case.client.get('/api/v1/reviews/' + body['review_receipt_id']).json() == rejected.json()
    with case.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM revisions').fetchone()[0] == 1


@pytest.mark.parametrize('fault', ['missing_key', 'invalid_key', 'csrf', 'origin', 'extra_body',
                                  'bool_revision', 'unknown_query', 'duplicate_key', 'duplicate_csrf'])
def test_publication_transport_rejects_ambiguous_or_unauthorized_writes_before_mutation(prepared_review_http, fault):
    case = prepared_review_http
    body, _, _ = approve_for_publication(case)
    path = '/api/v1/drafts/' + case.candidate['draft_id'] + '/publish'
    headers = command(case.headers, 'guarded-publication')
    expected = 400
    if fault == 'missing_key':
        headers.pop('Idempotency-Key')
    elif fault == 'invalid_key':
        headers['Idempotency-Key'] = 'invalid key'
    elif fault in {'csrf', 'origin'}:
        headers['X-CSRF-Token' if fault == 'csrf' else 'Origin'] = (
            'synthetic-invalid' if fault == 'csrf' else 'https://invalid.example')
        expected = 403
    elif fault == 'extra_body':
        body['reviewer'] = 'client-claimed-actor'
        expected = 422
    elif fault == 'bool_revision':
        body['expected_revision'] = True
        expected = 422
    elif fault == 'unknown_query':
        path += '?reuse=true'
        expected = 422
    actual_headers = list(headers.items())
    if fault.startswith('duplicate_'):
        actual_headers.append(('Idempotency-Key', 'second-command') if fault == 'duplicate_key'
                              else ('X-CSRF-Token', headers['X-CSRF-Token']))
    before = table_hashes(case.database)
    response = case.client.post(path, json=body, headers=actual_headers)
    assert response.status_code == expected, response.text
    assert 'client-claimed-actor' not in response.text and 'synthetic-invalid' not in response.text
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('change', ['role', 'logout'])
def test_original_publication_ack_requires_current_session_authority(prepared_review_http, change):
    case = prepared_review_http
    body, _, _ = approve_for_publication(case)
    path = '/api/v1/drafts/' + case.candidate['draft_id'] + '/publish'
    original = case.client.post(path, json=body, headers=command(case.headers, 'access-publish'))
    assert original.status_code == 201, original.text
    if change == 'role':
        switched = case.client.post('/api/v1/session/role', json={'role': 'learner'},
                                    headers=command(case.headers, 'switch-learner'))
        assert switched.status_code == 200
    else:
        case.client.cookies.clear()
    before = table_hashes(case.database)
    replay = case.client.post(path, json=body, headers=command(case.headers, 'access-publish'))
    assert replay.status_code == (403 if change == 'role' else 401), replay.text
    assert table_hashes(case.database) == before
