"""Private independent synthetic probes against fixed 676; no production mutation."""
import copy
import json
import pytest
from pydantic import TypeAdapter, ValidationError
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.content_draft_source import ContentDraftSource
from services.api.app.application.draft_edit_models import StoredDraftBase
from services.api.app.application.errors import ApiError
from tests.integration.test_review_http import prepared_review_http as prepared_review_http
from tests.integration.test_edit_publication_dependencies import source, draft, reviewed
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def dependent(case):
    content, block, base, children, ordered, bodies = source(case)
    identifier, create, created, patch, patched, snapshot = draft(case, base)
    with case.database.connect() as conn:
        raw = conn.execute('SELECT record_json FROM draft_edit_versions WHERE draft_id=? AND revision=2', (identifier,)).fetchone()[0]
    base_value = json.loads(raw)['base']
    assert base_value['version'] == 'draft-base-material-dependencies-v2'
    assert len(base_value['dependency_witness']['edges']) == 2
    return content, base, identifier, create, created, patch, patched, snapshot, base_value


@pytest.mark.parametrize('damage', ['missing_witness', 'legacy_downgrade', 'unknown_version', 'wrong_root', 'duplicate_edge', 'reverse_edges', 'extra_field'])
def test_invalid_dependency_base_never_defaults_or_downgrades(prepared_review_http, damage):
    case = prepared_review_http
    *_, value = dependent(case)
    if damage == 'missing_witness':
        del value['dependency_witness']
    elif damage == 'legacy_downgrade':
        value['version'] = 'draft-base-material-v1'; del value['dependency_witness']
    elif damage == 'unknown_version':
        value['version'] = 'draft-base-material-dependencies-v3'
    elif damage == 'wrong_root':
        value['dependency_witness']['root_ref']['revision'] += 1
    elif damage == 'duplicate_edge':
        value['dependency_witness']['edges'].append(copy.deepcopy(value['dependency_witness']['edges'][0]))
    elif damage == 'reverse_edges':
        value['dependency_witness']['edges'].reverse()
    else:
        value['dependency_witness']['trusted'] = True
    with pytest.raises(ValidationError):
        TypeAdapter(StoredDraftBase).validate_python(value)


def test_structurally_valid_but_incomplete_witness_fails_actual_owner_verification(prepared_review_http):
    case = prepared_review_http
    *_, value = dependent(case)
    value['dependency_witness']['edges'] = []
    narrowed = TypeAdapter(StoredDraftBase).validate_python(value)
    before = table_hashes(case.database)
    with case.database.transaction() as conn:
        with pytest.raises(ApiError) as caught:
            ContentDraftSource(case.database).verify_exact(conn, case.identity, narrowed)
        assert caught.value.code == 'DRAFT_EDIT_INTEGRITY'
    assert table_hashes(case.database) == before


def test_result_only_corruption_preserves_exact_original_revision_review_and_command_acks(prepared_review_http):
    case = prepared_review_http
    _, base, identifier, create, created, patch, patched, snapshot, _ = dependent(case)
    original_revision = case.client.get(f'/api/v1/draft-edits/{identifier}?revision=1')
    publication = reviewed(case, identifier, snapshot)
    review_path = '/api/v1/reviews/' + publication['review_receipt_id']
    review = case.client.get(review_path)
    path = f'/api/v1/drafts/{identifier}/publish'
    published = case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish'))
    assert published.status_code == 201
    with case.database.transaction() as conn:
        assert conn.execute('DELETE FROM object_dependencies WHERE owner_id=? AND owner_revision=2', (base.id,)).rowcount == 2
    before = table_hashes(case.database)
    current = case.client.get('/api/v1/draft-edits/' + identifier)
    replay = case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish'))
    assert (current.status_code, replay.status_code) == (409, 409)
    assert current.json()['error']['code'] == replay.json()['error']['code'] == 'CONTENT_HASH_MISMATCH'
    old_read = case.client.get(f'/api/v1/draft-edits/{identifier}?revision=1')
    assert old_read.status_code == 200 and old_read.content == original_revision.content
    assert case.client.get(review_path).content == review.content
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).content == patched.content
    assert table_hashes(case.database) == before


def test_corrupt_result_edge_before_return_rolls_back_every_publication_fact(prepared_review_http, monkeypatch):
    case = prepared_review_http
    content, base, identifier, _, _, _, _, snapshot, _ = dependent(case)
    publication = reviewed(case, identifier, snapshot)
    before = table_hashes(case.database)
    original_publish = ContentService.publish_in_transaction
    def corrupt(self, conn, workspace_id, blocks, bodies, **kwargs):
        result = original_publish(self, conn, workspace_id, blocks, bodies, **kwargs)
        assert len(result) == 1 and result[0].id == base.id and result[0].revision == 2
        assert conn.execute('DELETE FROM object_dependencies WHERE owner_id=? AND owner_revision=2', (base.id,)).rowcount == 2
        return result
    monkeypatch.setattr(ContentService, 'publish_in_transaction', corrupt)
    response = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication, headers=command(case.headers, 'dependency-publish'))
    assert response.status_code == 409 and response.json()['error']['code'] == 'CONTENT_HASH_MISMATCH'
    assert table_hashes(case.database) == before
    assert content.current(case.identity.workspace_id, base.id) == base
    monkeypatch.setattr(ContentService, 'publish_in_transaction', original_publish)
    retried = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication, headers=command(case.headers, 'dependency-publish'))
    assert retried.status_code == 201
