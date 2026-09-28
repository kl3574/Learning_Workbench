"""Actual HTTP publication of synthetic reviewed input; no real academic approval."""
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from tests.integration.test_authoring_http import command
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
    assert text.status_code == 200 and b'Unreviewed body.' in text.content
    replay = case.client.post(path, json=body, headers=command(case.headers, 'publish-once'))
    assert replay.status_code == 201 and replay.json() == response.json()
    assert case.client.get('/api/v1/drafts/' + case.candidate['draft_id']).json() == original_draft
    assert case.client.get('/api/v1/reviews/' + body['review_receipt_id']).json() == original_human
    assert case.client.get('/api/v1/courses').json()['items'] == []
    with case.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM objects').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM revisions').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM review_revisions').fetchone()[0] == 2
