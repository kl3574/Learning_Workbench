"""Actual protected review HTTP, real SQLite/Jobs/worker; decisions are synthetic intent."""
from dataclasses import dataclass

import pytest

from tests.integration.test_authoring_http import session, command


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
        assert connection.execute('SELECT state FROM drafts WHERE id=?', (case.candidate['draft_id'],)).fetchone()[0] == 'draft'
