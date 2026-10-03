"""Synthetic root concept pins through actual Edit/Review/publication HTTP owners."""
import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_edit_publication_dependencies import draft, reviewed
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def source(case, *, with_dependencies=False):
    content = ContentService(case.database)
    prerequisite = dm.Concept(id='edit_root_prerequisite', revision=1, title='Original prerequisite')
    content.publish(case.identity.workspace_id, [prerequisite], {})
    concepts = [dm.Concept(id='edit_root_concept_' + name, revision=1, title='Original ' + name)
        for name in ('first', 'second')]
    concepts[0] = concepts[0].model_copy(update={'prerequisite_ids': [prerequisite.id]})
    refs = content.publish(case.identity.workspace_id, concepts, {})
    ordered = [refs[1], refs[0]]
    raw = b'Original synthetic text with concept bindings.\n'
    dependencies = []
    if with_dependencies:
        leaf = dm.ContentBlock(id='edit_concept_leaf', revision=1, kind='definition', title='Original leaf',
            body_path='content/edit-concept-leaf.md', body_sha256=sha256_bytes(raw), concepts=[concepts[0].id])
        leaf_ref = content.publish(case.identity.workspace_id, [leaf], {leaf.body_path: raw})[0]
        middle = dm.ContentBlock(id='edit_concept_middle', revision=1, kind='text', title='Original middle',
            body_path='content/edit-concept-middle.md', body_sha256=sha256_bytes(raw), depends_on=[leaf_ref])
        middle_ref = content.publish(case.identity.workspace_id, [middle], {middle.body_path: raw})[0]
        dependencies = [middle_ref, leaf_ref]
    block = dm.ContentBlock(id='edit_concept_text', revision=1, kind='text', title='Original synthetic text',
        body_path='content/edit-concept.md', body_sha256=sha256_bytes(raw), concepts=[ref.id for ref in ordered],
        depends_on=dependencies)
    base = content.publish(case.identity.workspace_id, [block], {block.body_path: raw})[0]
    return content, block, base, [*concepts, prerequisite], ordered, raw


@pytest.mark.parametrize('with_dependencies', [False, True])
def test_original_concept_order_and_pins_survive_http_edit_after_concept_current_advances(prepared_review_http, with_dependencies):
    case = prepared_review_http
    content, block, base, concepts, ordered, raw = source(case, with_dependencies=with_dependencies)
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
    assert metadata.json()['depends_on'] == [ref.model_dump(mode='json') for ref in block.depends_on]
    assert metadata.json()['title'] == create['title']
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision=2').text == patch['patches'][0]['value']
    assert case.client.get(f'/api/v1/blocks/{base.id}?revision=1').json() == block.model_dump(mode='json')
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision=1').content == raw
    with case.database.connect() as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        witness = content.verify_retained_dependencies_in_transaction(connection, case.identity.workspace_id, published)
    assert {(edge.target_ref.id, edge.target_ref.revision, edge.target_ref.sha256)
        for edge in witness.edges if edge.owner_ref == published and edge.relation == 'concept'} == {
            (ref.id, ref.revision, ref.sha256) for ref in ordered}
    assert all(edge.target_ref.revision == 1 for edge in witness.edges)
    before = table_hashes(case.database)
    current = case.client.get('/api/v1/draft-edits/' + identifier)
    assert current.status_code == 200 and current.json()['state'] == 'published'
    assert current.json()['candidate'] == snapshot['candidate']
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).content == patched.content
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).content == result.content
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['root_pin', 'concept_metadata', 'nested_pin', 'dependency_pin'])
@pytest.mark.parametrize('published', [False, True])
def test_frozen_root_and_descendant_concept_damage_refuses_candidate_paths_without_writes(prepared_review_http, damage, published):
    case = prepared_review_http
    content, _, base, concepts, _, _ = source(case, with_dependencies=True)
    identifier, create, _, patch, _, snapshot = draft(case, base)
    content.publish(case.identity.workspace_id,
        [value.model_copy(update={'revision': 2, 'title': 'Later concept'}) for value in concepts], {})
    publication = reviewed(case, identifier, snapshot)
    path = f'/api/v1/drafts/{identifier}/publish'
    if published:
        assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 201
    with case.database.transaction() as connection:
        if damage == 'concept_metadata':
            connection.execute('DROP TRIGGER revisions_no_update')
            connection.execute('UPDATE revisions SET sha256=? WHERE object_id=? AND revision=1', ('0' * 64, concepts[0].id))
        else:
            owner, target = {'root_pin': (base.id, concepts[0].id),
                'nested_pin': (concepts[0].id, concepts[2].id),
                'dependency_pin': ('edit_concept_leaf', concepts[0].id)}[damage]
            changed = connection.execute("UPDATE object_dependencies SET target_revision=2 WHERE owner_id=? AND owner_revision=1 AND target_id=? AND relation='concept'", (owner, target))
            assert changed.rowcount == 1
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/draft-edits/' + identifier).status_code == 409
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).status_code == 409
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).status_code == 409
    assert case.client.get('/api/v1/reviews/' + publication['review_receipt_id']).status_code == 409
    assert case.client.post(f'/api/v1/drafts/{identifier}/review', json={'expected_revision': 2, 'checks': ['structure'],
        'reviewer_note': 'Synthetic damaged concept recheck.'}, headers=command(case.headers, 'bad-concept-review')).status_code == 409
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 409
    assert table_hashes(case.database) == before


def test_only_published_root_concept_damage_preserves_original_candidate_facts(prepared_review_http):
    case = prepared_review_http
    content, _, base, concepts, _, _ = source(case)
    identifier, create, created, patch, patched, snapshot = draft(case, base)
    original_r1 = case.client.get('/api/v1/draft-edits/' + identifier + '?revision=1')
    content.publish(case.identity.workspace_id,
        [value.model_copy(update={'revision': 2, 'title': 'Later concept'}) for value in concepts], {})
    publication = reviewed(case, identifier, snapshot)
    review_path = '/api/v1/reviews/' + publication['review_receipt_id']
    original_review = case.client.get(review_path)
    path = f'/api/v1/drafts/{identifier}/publish'
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 201
    with case.database.transaction() as connection:
        changed = connection.execute("UPDATE object_dependencies SET target_revision=2 WHERE owner_id=? AND owner_revision=2 AND target_id=? AND relation='concept'", (base.id, concepts[0].id))
        assert changed.rowcount == 1
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/draft-edits/' + identifier).status_code == 409
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 409
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).content == patched.content
    assert case.client.get(review_path).content == original_review.content
    assert case.client.get('/api/v1/draft-edits/' + identifier + '?revision=1').content == original_r1.content
    assert table_hashes(case.database) == before


def test_missing_published_concept_pin_rolls_back_whole_publication_before_original_key_retry(prepared_review_http):
    case = prepared_review_http
    _, _, base, _, _, _ = source(case, with_dependencies=True)
    identifier, _, _, _, _, snapshot = draft(case, base)
    publication = reviewed(case, identifier, snapshot)
    path = f'/api/v1/drafts/{identifier}/publish'
    with case.database.transaction() as connection:
        connection.execute("""CREATE TRIGGER damage_new_concept AFTER INSERT ON object_dependencies
            WHEN NEW.owner_id='edit_concept_text' AND NEW.owner_revision=2 AND NEW.relation='concept'
            BEGIN DELETE FROM object_dependencies WHERE owner_id=NEW.owner_id AND owner_revision=NEW.owner_revision
              AND target_id=NEW.target_id AND relation='concept'; END""")
    before = table_hashes(case.database)
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 409
    assert table_hashes(case.database) == before
    assert case.client.get('/api/v1/objects/' + base.id + '/current').json() == base.model_dump(mode='json')
    with case.database.transaction() as connection:
        connection.execute('DROP TRIGGER damage_new_concept')
    result = case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish'))
    assert result.status_code == 201 and result.json()['revision'] == 2
