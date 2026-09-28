"""Declared Draft HTTP uses real Import/Content history and the editing owner."""
import pytest

from packages.contracts import domain_models as dm
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_draft_publication_http import approve_for_publication
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def published_base(case):
    publication, _, _ = approve_for_publication(case)
    response = case.client.post('/api/v1/drafts/' + case.candidate['draft_id'] + '/publish',
                                json=publication, headers=command(case.headers, 'editing-base-publication'))
    assert response.status_code == 201, response.text
    return dm.ContentRef.model_validate_json(response.content)


def test_create_patch_review_and_historical_ack_use_actual_http_owners(prepared_review_http):
    case = prepared_review_http
    base = published_base(case)
    original = case.client.get(f'/api/v1/blocks/{base.id}/body?revision={base.revision}')
    assert original.status_code == 200
    create_body = {'kind': 'block', 'base_ref': base.model_dump(mode='json'), 'title': 'Synthetic edited title'}
    created = case.client.post('/api/v1/drafts', json=create_body, headers=command(case.headers, 'edit-create'))
    assert created.status_code == 201, created.text
    assert created.json() == {'draft_id': created.json()['draft_id'], 'revision': 1,
                              'base_ref': create_body['base_ref'], 'state': 'draft'}
    assert created.headers['cache-control'] == 'no-store' and created.headers['vary'] == 'Cookie'
    identifier = created.json()['draft_id']
    edit = case.app.state.draft_edit_service
    first = edit.read(case.identity, identifier, 1)
    assert first.payload.body_markdown.encode() == original.content
    assert case.client.get(f'/api/v1/drafts/{identifier}').status_code == 404  # Import GET stays Import-shaped.
    patch_body = {'expected_revision': 1, 'patches': [
        {'field': 'title', 'value': 'Second synthetic title'},
        {'field': 'body_markdown', 'value': '逐字正文 🌏\nSecond line.\n'}]}
    patched = case.client.patch(f'/api/v1/drafts/{identifier}', json=patch_body,
                                headers=command(case.headers, 'edit-patch'))
    assert patched.status_code == 200, patched.text
    assert set(patched.json()) == {'draft_id', 'revision', 'validation_warnings'}
    assert patched.json()['draft_id'] == identifier and patched.json()['revision'] == 2
    assert edit.read(case.identity, identifier, 2).payload.body_markdown == patch_body['patches'][1]['value']
    assert edit.read(case.identity, identifier, 1) == first
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision={base.revision}').content == original.content
    assert case.client.post('/api/v1/drafts', json=create_body,
                            headers=command(case.headers, 'edit-create')).json() == created.json()
    assert case.client.patch(f'/api/v1/drafts/{identifier}', json=patch_body,
                             headers=command(case.headers, 'edit-patch')).json() == patched.json()
    review = case.client.post(f'/api/v1/drafts/{identifier}/review', json={
        'expected_revision': 2, 'checks': ['structure', 'sources', 'mathematics'],
        'reviewer_note': 'Synthetic editing protocol; no real academic approval.'},
        headers=command(case.headers, 'edit-review'))
    assert review.status_code == 202, review.text
    assert case.app.state.review_worker.run_once()
    receipt = case.client.get(f"/api/v1/reviews/{review.json()['id']}")
    assert receipt.status_code == 200 and receipt.json()['candidate'] == edit.read(case.identity, identifier, 2).candidate.model_dump(mode='json')
    assert receipt.json()['structural'] == 'PASS'
    assert receipt.json()['mathematical'] == receipt.json()['sources'] == 'NOT_RUN'


@pytest.mark.parametrize('fault,status', [
    ('missing_key', 400), ('duplicate_key', 400), ('bad_origin', 403), ('bad_csrf', 403),
    ('unknown_query', 400), ('extra_field', 422), ('nontext_kind', 409),
])
def test_create_http_rejects_ambiguous_or_unsupported_writes_without_mutation(prepared_review_http, fault, status):
    case = prepared_review_http
    base = published_base(case)
    body = {'kind': 'block', 'base_ref': base.model_dump(mode='json'), 'title': 'Synthetic title'}
    headers = command(case.headers, 'edit-guard')
    path = '/api/v1/drafts'
    if fault == 'missing_key':
        headers.pop('Idempotency-Key')
    elif fault == 'bad_origin':
        headers['Origin'] = 'https://invalid.example'
    elif fault == 'bad_csrf':
        headers['X-CSRF-Token'] = 'invalid-synthetic'
    elif fault == 'unknown_query':
        path += '?revision=1'
    elif fault == 'extra_field':
        body['claimed_review'] = 'approved'
    elif fault == 'nontext_kind':
        body['kind'] = 'question'
    values = list(headers.items())
    if fault == 'duplicate_key':
        values.append(('Idempotency-Key', 'other-key'))
    before = table_hashes(case.database)
    response = case.client.post(path, json=body, headers=values)
    assert response.status_code == status, response.text
    assert table_hashes(case.database) == before


def test_patch_http_cas_optional_key_strict_json_and_key_conflict(prepared_review_http):
    case = prepared_review_http
    base = published_base(case)
    created = case.client.post('/api/v1/drafts', json={'kind': 'block', 'base_ref': base.model_dump(mode='json'),
        'title': 'Synthetic title'}, headers=command(case.headers, 'edit-create-patch'))
    assert created.status_code == 201, created.text
    path = f"/api/v1/drafts/{created.json()['draft_id']}"
    original = {'expected_revision': 1, 'patches': [{'field': 'title', 'value': 'Changed title'}]}
    no_key = {name: value for name, value in case.headers.items() if name.lower() != 'idempotency-key'}
    first = case.client.patch(path, json=original, headers=no_key)
    assert first.status_code == 200 and first.json()['revision'] == 2
    assert case.client.patch(path, json=original, headers=no_key).status_code == 412
    keyed = {'expected_revision': 2, 'patches': [{'field': 'body_markdown', 'value': '真实编辑候选文本。\n'}]}
    second = case.client.patch(path, json=keyed, headers=command(case.headers, 'edit-patch-key'))
    assert second.status_code == 200 and second.json()['revision'] == 3
    assert case.client.patch(path, json=keyed, headers=command(case.headers, 'edit-patch-key')).json() == second.json()
    changed = {'expected_revision': 2, 'patches': [{'field': 'body_markdown', 'value': 'Different command.\n'}]}
    assert case.client.patch(path, json=changed, headers=command(case.headers, 'edit-patch-key')).status_code == 409
    before = table_hashes(case.database)
    for bad in [True, 1, None, {'nested': ['valid', 1]}, ['valid']]:
        response = case.client.patch(path, json={'expected_revision': 3,
            'patches': [{'field': 'title', 'value': bad}]}, headers=no_key)
        assert response.status_code == 422, (bad, response.text)
    assert table_hashes(case.database) == before
