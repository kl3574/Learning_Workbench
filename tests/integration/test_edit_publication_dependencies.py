"""Synthetic exact dependencies through the real Edit/Review/publication HTTP owners."""
from contextlib import contextmanager
import pytest
import sqlite3
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def source(case):
    content = ContentService(case.database)
    bodies = {name: f'Synthetic original {name}.\n'.encode() for name in ('first', 'second', 'base')}
    dependencies = [dm.ContentBlock(id='edit_dependency_' + name, revision=1, kind='text', title=name,
        body_path=f'content/edit-{name}.md', body_sha256=sha256_bytes(bodies[name])) for name in ('first', 'second')]
    refs = content.publish(case.identity.workspace_id, dependencies,
        {value.body_path: bodies[name] for value, name in zip(dependencies, ('first', 'second'))})
    ordered = [refs[1], refs[0]]
    block = dm.ContentBlock(id='edit_dependent_text', revision=1, kind='text', title='Original synthetic text',
        body_path='content/edit-dependent.md', body_sha256=sha256_bytes(bodies['base']), depends_on=ordered)
    base = content.publish(case.identity.workspace_id, [block], {block.body_path: bodies['base']})[0]
    return content, block, base, dependencies, ordered, bodies


def draft(case, base):
    create = {'kind': 'block', 'base_ref': base.model_dump(mode='json'), 'title': 'Synthetic corrected title'}
    created = case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create'))
    assert created.status_code == 201, created.text
    identifier = created.json()['draft_id']
    patch = {'expected_revision': 1, 'patches': [{'field': 'body_markdown', 'value': 'Corrected synthetic prose.\n'}]}
    patched = case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch'))
    assert patched.status_code == 200, patched.text
    read = case.client.get('/api/v1/draft-edits/' + identifier)
    assert read.status_code == 200, read.text
    snapshot = read.json()
    assert snapshot['state'] == 'draft' and snapshot['candidate']['draft_revision'] == 2
    assert snapshot['payload']['body_markdown'] == patch['patches'][0]['value']
    assert 'depends_on' not in snapshot['payload'] and 'concepts' not in snapshot['payload']
    return identifier, create, created, patch, patched, snapshot


def reviewed(case, identifier, snapshot):
    response = case.client.post(f'/api/v1/drafts/{identifier}/review', json={
        'expected_revision': 2, 'checks': ['structure', 'mathematics', 'sources'],
        'reviewer_note': 'Synthetic HTTP dependency preservation; no academic approval.'},
        headers=command(case.headers, 'dependency-review'))
    assert response.status_code == 202, response.text
    assert case.app.state.review_worker.run_once()
    path = '/api/v1/reviews/' + response.json()['id']
    machine = case.client.get(path)
    assert machine.status_code == 200, machine.text
    assert machine.json()['candidate'] == snapshot['candidate']
    assert machine.json()['structural'] == 'PASS'
    human = case.client.post(path + '/decision', json={'expected_revision': 1,
        'candidate_sha256': snapshot['candidate']['candidate_sha256'], 'mathematical': 'NOT_APPLICABLE',
        'sources': 'APPROVED', 'reason': 'Synthetic protocol intent only.', 'evidence_artifact_ids': []},
        headers=command(case.headers, 'dependency-human'))
    assert human.status_code == 200, human.text
    return {'expected_revision': 2, 'expected_content_sha256': snapshot['candidate']['candidate_sha256'],
        'review_receipt_id': response.json()['id'],
        'acknowledged_warning_codes': sorted({w['code'] for w in snapshot['warnings'] if w['severity'] == 'warning'})}


def test_exact_dependency_order_survives_http_edit_review_publication_and_later_source_current(prepared_review_http):
    case = prepared_review_http
    content, original, base, dependencies, ordered, bodies = source(case)
    identifier, create, created, patch, patched, snapshot = draft(case, base)
    # Both source current pointers advance after the exact edit has been frozen.
    content.publish(case.identity.workspace_id, [value.model_copy(update={'revision': 2, 'title': 'Later source'})
        for value in dependencies], {value.body_path: bodies[name] for value, name in zip(dependencies, ('first', 'second'))})
    publication = reviewed(case, identifier, snapshot)
    result = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication,
        headers=command(case.headers, 'dependency-publish'))
    assert result.status_code == 201, result.text
    ref = result.json()
    assert ref['id'] == base.id and ref['revision'] == 2
    metadata = case.client.get(f'/api/v1/blocks/{base.id}?revision=2')
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()['depends_on'] == [value.model_dump(mode='json') for value in ordered]
    assert metadata.json()['concepts'] == [] and metadata.json()['title'] == create['title']
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision=2').text == patch['patches'][0]['value']
    assert case.client.get(f'/api/v1/blocks/{base.id}?revision=1').json() == original.model_dump(mode='json')
    assert case.client.get(f'/api/v1/blocks/{base.id}/body?revision=1').content == bodies['base']
    current = case.client.get('/api/v1/draft-edits/' + identifier)
    assert current.status_code == 200 and current.json()['state'] == 'published'
    assert current.json()['candidate'] == snapshot['candidate']
    before = table_hashes(case.database)
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).content == patched.content
    assert case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication,
        headers=command(case.headers, 'dependency-publish')).content == result.content
    assert table_hashes(case.database) == before


def test_historical_dependencies_with_original_concept_pins_are_readonly_even_after_current_moves_or_archives(prepared_review_http, monkeypatch):
    case = prepared_review_http
    content = ContentService(case.database)
    concept = dm.Concept(id='dependency_original_concept', revision=1, title='Original concept')
    content.publish(case.identity.workspace_id, [concept], {})
    raw = b'Synthetic nested original source.'
    leaf = dm.ContentBlock(id='dependency_leaf', revision=1, kind='definition', title='Historical source',
        body_path='content/dependency-leaf.md', body_sha256=sha256_bytes(raw), concepts=[concept.id])
    leaf_ref = content.publish(case.identity.workspace_id, [leaf], {leaf.body_path: raw})[0]
    middle = dm.ContentBlock(id='dependency_middle', revision=1, kind='text', title='Middle source',
        body_path='content/dependency-middle.md', body_sha256=sha256_bytes(raw), depends_on=[leaf_ref])
    middle_ref = content.publish(case.identity.workspace_id, [middle], {middle.body_path: raw})[0]
    block = middle.model_copy(update={'id': 'dependency_nested_edit', 'depends_on': [middle_ref]})
    base = content.publish(case.identity.workspace_id, [block], {block.body_path: raw})[0]
    identifier, _, _, _, _, snapshot = draft(case, base)
    content.publish(case.identity.workspace_id, [concept.model_copy(update={'revision': 2, 'title': 'Later concept'})], {})
    publication = reviewed(case, identifier, snapshot)
    path = f'/api/v1/drafts/{identifier}/publish'
    result = case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish'))
    assert result.status_code == 201, result.text
    with case.database.transaction() as connection:
        connection.execute("UPDATE objects SET lifecycle='archived' WHERE id IN (?,?)", (concept.id, leaf.id))
    before = table_hashes(case.database)
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).content == result.content
    assert table_hashes(case.database) == before
    application_database = case.app.state.draft_edit_service.database
    original_connect, attempted_writes = application_database.connect, []
    @contextmanager
    def connect():
        with original_connect() as connection:
            def authorize(operation, *_):
                if operation in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
                    attempted_writes.append(operation)
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            connection.set_authorizer(authorize)
            yield connection
    monkeypatch.setattr(application_database, 'connect', connect)
    current = case.client.get('/api/v1/draft-edits/' + identifier)
    assert current.status_code == 200, current.text
    assert current.json()['state'] == 'published'
    assert case.client.get('/api/v1/draft-edits/' + identifier + '?unknown=1').status_code == 422
    assert case.client.get('/api/v1/draft-edits/' + case.candidate['draft_id']).status_code == 404
    assert attempted_writes == []
    assert table_hashes(case.database) == before


def test_corrupt_dependency_before_creation_and_attempted_dependency_edit_create_no_facts(prepared_review_http):
    case = prepared_review_http
    _, _, base, dependencies, _, _ = source(case)
    identifier, _, _, _, _, _ = draft(case, base)
    before = table_hashes(case.database)
    response = case.client.patch('/api/v1/drafts/' + identifier, json={'expected_revision': 2,
        'patches': [{'field': 'depends_on', 'value': []}]}, headers=command(case.headers, 'dependency-field'))
    assert response.status_code == 422
    assert table_hashes(case.database) == before
    digest = dependencies[0].body_sha256
    (case.database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic damaged before new create')
    before = table_hashes(case.database)
    response = case.client.post('/api/v1/drafts', json={'kind': 'block', 'base_ref': base.model_dump(mode='json'),
        'title': 'New command with damaged original source'}, headers=command(case.headers, 'corrupt-dependency-create'))
    assert response.status_code == 409
    assert table_hashes(case.database) == before


def test_dependency_body_damage_refuses_frozen_draft_read_and_original_command_without_writes(prepared_review_http):
    case = prepared_review_http
    _, _, base, dependencies, _, _ = source(case)
    identifier, create, _, _, _, _ = draft(case, base)
    digest = dependencies[0].body_sha256
    (case.database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic corrupt dependency')
    before = table_hashes(case.database)
    read = case.client.get('/api/v1/draft-edits/' + identifier)
    assert read.status_code == 409
    replay = case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create'))
    assert replay.status_code == 409
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['base_body', 'dependency_metadata', 'missing_edge', 'extra_edge'])
@pytest.mark.parametrize('published', [False, True])
def test_bad_original_base_or_dependency_evidence_is_never_repaired_by_read_review_publish_or_ack(prepared_review_http, damage, published):
    case = prepared_review_http
    _, block, base, dependencies, _, _ = source(case)
    identifier, create, _, patch, _, snapshot = draft(case, base)
    publication = reviewed(case, identifier, snapshot)
    path = f'/api/v1/drafts/{identifier}/publish'
    if published:
        assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 201
    if damage == 'base_body':
        digest = block.body_sha256
        (case.database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic corrupt base')
    else:
        with case.database.transaction() as connection:
            if damage == 'dependency_metadata':
                connection.execute('DROP TRIGGER revisions_no_update')
                connection.execute('UPDATE revisions SET sha256=? WHERE object_id=? AND revision=1', ('0' * 64, dependencies[0].id))
            elif damage == 'missing_edge':
                connection.execute('DELETE FROM object_dependencies WHERE owner_id=? AND owner_revision=1 AND target_id=?', (base.id, dependencies[0].id))
            else:
                connection.execute("INSERT INTO object_dependencies VALUES(?,1,?,1,'reference')", (dependencies[0].id, dependencies[1].id))
    before = table_hashes(case.database)
    read = case.client.get('/api/v1/draft-edits/' + identifier)
    assert read.status_code == 409, read.text
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).status_code == 409
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).status_code == 409
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 409
    review = case.client.post(f'/api/v1/drafts/{identifier}/review', json={'expected_revision': 2,
        'checks': ['structure'], 'reviewer_note': 'Synthetic recheck of damaged dependencies.'},
        headers=command(case.headers, 'damage-review'))
    assert review.status_code == 409
    assert table_hashes(case.database) == before


def test_current_base_cas_still_blocks_publish_while_original_draft_ack_remains_readable(prepared_review_http):
    case = prepared_review_http
    content, block, base, _, _, bodies = source(case)
    identifier, create, created, _, _, snapshot = draft(case, base)
    publication = reviewed(case, identifier, snapshot)
    later = content.publish(case.identity.workspace_id, [block.model_copy(update={'revision': 2, 'title': 'Competing revision'})],
        {block.body_path: bodies['base']})[0]
    before = table_hashes(case.database)
    result = case.client.post(f'/api/v1/drafts/{identifier}/publish', json=publication,
        headers=command(case.headers, 'dependency-publish'))
    assert result.status_code == 412
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).content == created.content
    assert case.client.get('/api/v1/draft-edits/' + identifier).json() == snapshot
    assert content.current(case.identity.workspace_id, base.id) == later
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('mode', ['learner', 'independent', 'open_book', 'assisted'])
def test_current_role_and_policy_guard_original_dependency_edit_and_publication_acks(prepared_review_http, mode):
    case = prepared_review_http
    _, _, base, _, _, _ = source(case)
    identifier, create, _, patch, _, snapshot = draft(case, base)
    publication = reviewed(case, identifier, snapshot)
    path = f'/api/v1/drafts/{identifier}/publish'
    assert case.client.post(path, json=publication, headers=command(case.headers, 'dependency-publish')).status_code == 201
    if mode == 'learner':
        role = case.client.post('/api/v1/session/role', json={'role': 'learner'}, headers=command(case.headers, 'dependency-role'))
        assert role.status_code == 200
    else:
        from services.api.app.application.assessment import AssessmentService
        from services.api.app.assessment_dto import AssessmentAttemptCreate
        from services.api.app.infrastructure.content_repository import reference
        from tests.assessment_fixtures import assessment_fixture
        from tests.integration.test_assessment_attempts import import_fixture
        fixture = assessment_fixture('dependencyeditpolicy')
        import_fixture(case.database, case.identity, fixture, 'dependency-assessment-material')
        AssessmentService(case.database).create_attempt(case.identity, fixture.assessment.id,
            AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'dependency-attempt')
    before = table_hashes(case.database)
    expected = 403 if mode == 'learner' else 409
    assert case.client.get('/api/v1/draft-edits/' + identifier).status_code == expected
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'dependency-create')).status_code == expected
    assert case.client.patch('/api/v1/drafts/' + identifier, json=patch, headers=command(case.headers, 'dependency-patch')).status_code == expected
    for key in ['dependency-publish', 'another-publish']:
        assert case.client.post(path, json=publication, headers=command(case.headers, key)).status_code == expected
    assert table_hashes(case.database) == before
