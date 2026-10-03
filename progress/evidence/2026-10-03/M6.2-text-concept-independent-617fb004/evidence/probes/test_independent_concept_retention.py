"""Private independent synthetic HTTP probes; no original user databases."""
import pytest

from packages.contracts import domain_models as dm
from tests.integration.test_review_http import prepared_review_http as prepared_review_http
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_edit_publication_concepts import source
from tests.integration.test_edit_publication_dependencies import draft, reviewed


@pytest.mark.parametrize('with_dependencies', [False, True])
def test_current_was_already_new_before_candidate_freeze(prepared_review_http, with_dependencies):
    case = prepared_review_http
    content, _, base, concepts, ordered, _ = source(case, with_dependencies=with_dependencies)
    content.publish(case.identity.workspace_id,
        [c.model_copy(update={'revision': 2, 'title': 'Current changed before candidate freeze'}) for c in concepts], {})
    identifier, _, _, _, _, snapshot = draft(case, base)
    publication = reviewed(case, identifier, snapshot)
    result = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication,
        headers=command(case.headers, 'independent-concept-publish'))
    assert result.status_code == 201, result.text
    published = dm.ContentRef.model_validate(result.json())
    with case.database.connect() as conn:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        witness = content.verify_retained_dependencies_in_transaction(conn, case.identity.workspace_id, published)
    assert [ref.id for ref in ordered] == case.client.get(f'/api/v1/blocks/{base.id}?revision=2').json()['concepts']
    assert all(edge.target_ref.revision == 1 for edge in witness.edges)
    before = table_hashes(case.database)
    assert case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication,
        headers=command(case.headers, 'independent-concept-publish')).content == result.content
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['missing', 'undeclared_extra'])
def test_original_root_edge_set_damage_refuses_without_writes(prepared_review_http, damage):
    case = prepared_review_http
    _, _, base, concepts, _, _ = source(case, with_dependencies=True)
    identifier, create, _, patch, _, snapshot = draft(case, base)
    request = reviewed(case, identifier, snapshot)
    with case.database.transaction() as conn:
        if damage == 'missing':
            changed = conn.execute("DELETE FROM object_dependencies WHERE owner_id=? AND owner_revision=1 AND target_id=? AND relation='concept'",
                (base.id, concepts[0].id))
        else:
            changed = conn.execute("INSERT INTO object_dependencies(owner_id,owner_revision,target_id,target_revision,relation) VALUES(?,1,?,1,'concept')",
                (base.id, concepts[2].id))
        assert changed.rowcount == 1
    before = table_hashes(case.database)
    responses = [case.client.get('/api/v1/draft-edits/' + identifier),
        case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')),
        case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')),
        case.client.get('/api/v1/reviews/' + request['review_receipt_id']),
        case.client.post(f'/api/v1/drafts/{identifier}/publish', json=request,
            headers=command(case.headers, 'independent-damaged-publish'))]
    assert [(r.status_code, r.json()['error']['code']) for r in responses] == [(409, 'CONTENT_HASH_MISMATCH')] * 5
    assert table_hashes(case.database) == before


def test_missing_result_edge_does_not_reinterpret_original_candidate_acks(prepared_review_http):
    case = prepared_review_http
    _, _, base, concepts, _, _ = source(case)
    identifier, create, created, patch, patched, snapshot = draft(case, base)
    original_r1 = case.client.get('/api/v1/draft-edits/' + identifier + '?revision=1')
    request = reviewed(case, identifier, snapshot)
    review_path = '/api/v1/reviews/' + request['review_receipt_id']
    review = case.client.get(review_path)
    path = f'/api/v1/drafts/{identifier}/publish'
    assert case.client.post(path, json=request, headers=command(case.headers, 'independent-result')).status_code == 201
    with case.database.transaction() as conn:
        assert conn.execute("DELETE FROM object_dependencies WHERE owner_id=? AND owner_revision=2 AND target_id=? AND relation='concept'",
            (base.id, concepts[0].id)).rowcount == 1
    before = table_hashes(case.database)
    for response in [case.client.get('/api/v1/draft-edits/' + identifier),
            case.client.post(path, json=request, headers=command(case.headers, 'independent-result'))]:
        assert (response.status_code, response.json()['error']['code']) == (409, 'CONTENT_HASH_MISMATCH')
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).content == patched.content
    assert case.client.get(review_path).content == review.content
    assert case.client.get('/api/v1/draft-edits/' + identifier + '?revision=1').content == original_r1.content
    assert table_hashes(case.database) == before
