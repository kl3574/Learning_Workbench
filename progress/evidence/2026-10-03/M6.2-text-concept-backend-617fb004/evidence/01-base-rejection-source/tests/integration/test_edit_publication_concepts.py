"""Synthetic root concept pins through actual Edit/Review/publication HTTP owners."""
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_edit_publication_dependencies import draft, reviewed
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def source(case):
    content = ContentService(case.database)
    concepts = [dm.Concept(id='edit_root_concept_' + name, revision=1, title='Original ' + name)
        for name in ('first', 'second')]
    refs = content.publish(case.identity.workspace_id, concepts, {})
    ordered = [refs[1], refs[0]]
    raw = b'Original synthetic text with concept bindings.\n'
    block = dm.ContentBlock(id='edit_concept_text', revision=1, kind='text', title='Original synthetic text',
        body_path='content/edit-concept.md', body_sha256=sha256_bytes(raw), concepts=[ref.id for ref in ordered])
    base = content.publish(case.identity.workspace_id, [block], {block.body_path: raw})[0]
    return content, block, base, concepts, ordered, raw


def test_original_concept_order_and_pins_survive_http_edit_after_concept_current_advances(prepared_review_http):
    case = prepared_review_http
    content, block, base, concepts, ordered, raw = source(case)
    identifier, create, created, patch, patched, snapshot = draft(case, base)
    content.publish(case.identity.workspace_id,
        [value.model_copy(update={'revision': 2, 'title': 'Later concept'}) for value in concepts], {})
    publication = reviewed(case, identifier, snapshot)
    path = f'/api/v1/drafts/{identifier}/publish'
    result = case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish'))
    assert result.status_code == 201, result.text
    published = dm.ContentRef.model_validate(result.json())
    assert published.id == base.id and published.revision == 2
    metadata = case.client.get(f'/api/v1/blocks/{base.id}?revision=2')
    assert metadata.status_code == 200
    assert metadata.json()['concepts'] == [ref.id for ref in ordered]
    assert metadata.json()['depends_on'] == []
    assert metadata.json()['title'] == create['title']
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision=2').text == patch['patches'][0]['value']
    assert case.client.get(f'/api/v1/blocks/{base.id}?revision=1').json() == block.model_dump(mode='json')
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision=1').content == raw
    with case.database.connect() as connection:
        connection.execute('PRAGMA query_only=ON')
        witness = content.verify_retained_dependencies_in_transaction(connection, case.identity.workspace_id, published)
    assert {(edge.target_ref.id, edge.target_ref.revision, edge.target_ref.sha256)
        for edge in witness.edges if edge.owner_ref == published and edge.relation == 'concept'} == {
            (ref.id, ref.revision, ref.sha256) for ref in ordered}
    before = table_hashes(case.database)
    current = case.client.get('/api/v1/draft-edits/' + identifier)
    assert current.status_code == 200 and current.json()['state'] == 'published'
    assert current.json()['candidate'] == snapshot['candidate']
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).content == patched.content
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).content == result.content
    assert table_hashes(case.database) == before
