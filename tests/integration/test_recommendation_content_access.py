"""Real Content publication and SQLite reads, not material-review approval.

Catalog availability validates registrations/metadata and parent navigation.
Physical body integrity remains Content.body's check at actual navigation time.
Approved answers below are controlled software qualification preconditions only.
"""

from dataclasses import replace
import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.content import ContentService
from services.api.app.application.content_recommendation_access import recommendation_catalog
from services.api.app.application.errors import ApiError
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import SessionIdentity
from tests.assessment_fixtures import assessment_fixture


def put_answer(database, solution):
    """Controlled private fixture insertion, not a product review action."""
    with database.transaction() as connection:
        connection.execute('INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) '
            'VALUES(?,?,?,?,?,?)', (solution.question_ref.id, solution.question_ref.revision, solution.revision,
            canonical_bytes(solution).decode(), metadata_sha256(solution), solution.review_status))


@pytest.fixture
def catalog_storage(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    fixture = assessment_fixture('catalog')
    ContentService(database).publish(workspace, fixture.public_objects, fixture.bodies)
    for solution in fixture.solutions:
        put_answer(database, solution)
    identity = SessionIdentity('session_catalog', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    return database, identity, fixture


def read(storage, course_id=None):
    database, identity, _ = storage
    with database.transaction() as connection:
        before = connection.total_changes
        result = recommendation_catalog(connection, identity.workspace_id, course_id)
        assert connection.total_changes == before
    return result


def target(result, value):
    return next(item for item in result.candidates if item.target_ref == reference(value))


def assert_error(code, callback):
    with pytest.raises(ApiError) as caught:
        callback()
    assert caught.value.code == code


def logical_state(database):
    with database.connect() as connection:
        return tuple(connection.iterdump())


def test_exact_catalog_is_repeatable_zero_write_and_unreviewed(catalog_storage):
    database, _, fixture = catalog_storage
    before = logical_state(database)
    first = read(catalog_storage)
    assert first == read(catalog_storage)
    assert logical_state(database) == before
    assert len(first.candidates) == 4
    assert first.course_refs == [reference(fixture.course)]
    assert first.courses[0].language == fixture.course.language
    assert first.courses[0].difficulty == fixture.course.difficulty
    for item in first.candidates:
        assert item.available and item.material_review == 'unreviewed'
        assert item.estimated_minutes is None and item.mapping_state == 'complete'
        assert not item.test_ready
    assert target(first, fixture.assessment).test_warning_codes
    assert target(first, fixture.practice).concept_skills
    assert target(first, fixture.block).concept_skills == []
    for private in ('accepted_answers', 'solution_markdown', 'private_pins', 'absolute_tolerance', 'rubric_markdown'):
        assert private not in first.model_dump_json()


def test_all_historical_revisions_and_every_exact_parent_chain(catalog_storage):
    database, identity, fixture = catalog_storage
    content = ContentService(database)
    sibling = fixture.lesson.model_copy(update={'id': 'lesson_catalog_sibling'})
    second = fixture.course.model_copy(update={'id': 'course_catalog_second', 'sections': [],
        'lesson_refs': [reference(fixture.lesson), reference(sibling)]})
    content.publish(identity.workspace_id, [sibling, second], {})
    updated_course = fixture.course.model_copy(update={'revision': 2, 'title': '第二修订'})
    content.publish(identity.workspace_id, [updated_course], {})
    result = read(catalog_storage)
    block = target(result, fixture.block)
    assert len(block.navigation_options) == 4
    assert set((option.course_ref.id, option.course_ref.revision, option.lesson_ref.id)
               for option in block.navigation_options) == {
        (fixture.course.id, 1, fixture.lesson.id), (fixture.course.id, 2, fixture.lesson.id),
        (second.id, 1, fixture.lesson.id), (second.id, 1, sibling.id)}
    assert len(target(result, fixture.practice).navigation_options) == 3
    assert len(target(result, fixture.assessment).navigation_options) == 3
    assert len(read(catalog_storage, second.id).course_refs) == 1


def test_entire_historical_candidate_tree_keeps_original_references(catalog_storage):
    database, identity, fixture = catalog_storage
    updated = assessment_fixture('catalog', revision=2)
    ContentService(database).publish(identity.workspace_id, updated.public_objects, updated.bodies)
    for solution in updated.solutions:
        put_answer(database, solution)
    result = read(catalog_storage)
    assert len(result.candidates) == 8 and len(result.concepts) == 2
    for source in (fixture, updated):
        for value in (source.lesson, source.block, source.practice, source.assessment):
            item = target(result, value)
            assert item.target_ref == reference(value)
            assert item.concept_refs == [reference(source.concept)]
            assert item.course_refs == [reference(source.course)]
            assert all(option.course_ref == reference(source.course) for option in item.navigation_options)
    assert 'SEMANTIC_DEPENDENCY_REVISION_CHANGED' in target(result, fixture.assessment).test_warning_codes


@pytest.mark.parametrize('kind', ['course', 'lesson', 'block', 'practice', 'assessment'])
def test_archived_target_or_required_parent_is_unavailable(catalog_storage, kind):
    database, _, fixture = catalog_storage
    value = getattr(fixture, kind)
    before = read(catalog_storage)
    with database.transaction() as connection:
        connection.execute("UPDATE objects SET lifecycle='archived' WHERE id=?", (value.id,))
    result = read(catalog_storage)
    assert result.content_basis_sha256 != before.content_basis_sha256
    selected = target(result, fixture.block if kind == 'course' else value)
    assert not selected.available and selected.unavailable_reason_codes and not selected.navigation_options
    if kind == 'course':
        assert not target(result, fixture.assessment).available


def test_archived_one_parent_keeps_other_real_active_chain(catalog_storage):
    database, identity, fixture = catalog_storage
    second = fixture.course.model_copy(update={'id': 'course_catalog_active', 'sections': []})
    ContentService(database).publish(identity.workspace_id, [second], {})
    with database.transaction() as connection:
        connection.execute("UPDATE objects SET lifecycle='archived' WHERE id=?", (fixture.course.id,))
    for item in read(catalog_storage).candidates:
        assert item.available and item.unavailable_reason_codes == []
        assert item.course_refs == sorted([reference(second), reference(fixture.course)], key=lambda ref: ref.id)
        assert all(option.course_ref == reference(second) for option in item.navigation_options)


def test_frozen_prerequisite_never_substitutes_new_current(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    fixture = assessment_fixture('frozen')
    prerequisite = dm.Concept(id='concept_prerequisite', revision=1, title='先修条件', skill_dimensions=['recall'])
    concept = fixture.concept.model_copy(update={'prerequisite_ids': [prerequisite.id]})
    fixture = replace(fixture, concept=concept, course=fixture.course.model_copy(update={'concept_refs': [reference(concept)]}))
    content = ContentService(database)
    content.publish(workspace, [prerequisite, *fixture.public_objects], fixture.bodies)
    content.publish(workspace, [prerequisite.model_copy(update={'revision': 2, 'title': '变更先修'})], {})
    identity = SessionIdentity('session_frozen', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    result = read((database, identity, fixture))
    for item in result.candidates:
        assert item.prerequisite_refs == [reference(prerequisite)]
    assert next(item for item in result.concepts if item.ref == reference(concept)).prerequisite_refs == [reference(prerequisite)]
    assert 'SEMANTIC_DEPENDENCY_REVISION_CHANGED' in target(result, fixture.assessment).test_warning_codes
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM outbox WHERE event_type='content.dependencies_invalidated' "
                                  'AND delivered_at IS NULL').fetchone()[0] > 0


def test_practice_concepts_come_from_questions_not_sibling_material(catalog_storage):
    database, identity, fixture = catalog_storage
    other = dm.Concept(id='concept_material_only', revision=1, title='教材额外概念', skill_dimensions=['transfer'])
    block = fixture.block.model_copy(update={'id': 'block_material_only', 'concepts': [other.id]})
    lesson = fixture.lesson.model_copy(update={'id': 'lesson_material_only', 'block_refs': [reference(block)]})
    practice = fixture.practice.model_copy(update={'id': 'practice_material_only', 'lesson_ref': reference(lesson)})
    course = fixture.course.model_copy(update={'id': 'course_material_only', 'sections': [],
        'lesson_refs': [reference(lesson)], 'concept_refs': [reference(fixture.concept), reference(other)]})
    ContentService(database).publish(identity.workspace_id, [other, block, lesson, practice, course], fixture.bodies)
    result = read(catalog_storage)
    assert target(result, practice).concept_refs == [reference(fixture.concept)]
    assert target(result, practice).block_refs == [reference(block)]
    assert all(item.concept_ref == reference(fixture.concept) for item in target(result, practice).concept_skills)
    assert target(result, block).concept_refs == [reference(other)]


def test_empty_declared_mapping_remains_available_only_as_unmapped_reading(catalog_storage):
    database, identity, fixture = catalog_storage
    block = fixture.block.model_copy(update={'id': 'block_no_concepts', 'concepts': []})
    lesson = fixture.lesson.model_copy(update={'id': 'lesson_no_concepts', 'block_refs': [reference(block)]})
    course = fixture.course.model_copy(update={'id': 'course_no_concepts', 'sections': [],
        'lesson_refs': [reference(lesson)], 'concept_refs': []})
    ContentService(database).publish(identity.workspace_id, [block, lesson, course], fixture.bodies)
    for value in (block, lesson):
        item = target(read(catalog_storage), value)
        assert item.available and item.mapping_state == 'unresolved'
        assert item.concept_refs == item.concept_skills == []


@pytest.mark.parametrize('owner', ['block', 'question', 'concept'])
def test_missing_frozen_mapping_is_unresolved_without_current_fallback(catalog_storage, owner):
    database, identity, fixture = catalog_storage
    value = fixture.block if owner == 'block' else fixture.questions[0]
    if owner == 'concept':
        prerequisite = dm.Concept(id='concept_missing_prerequisite', revision=1, title='条件')
        concept = fixture.concept.model_copy(update={'revision': 2, 'prerequisite_ids': [prerequisite.id]})
        ContentService(database).publish(identity.workspace_id, [prerequisite, concept], {})
        value = concept
    with database.transaction() as connection:
        connection.execute("DELETE FROM object_dependencies WHERE owner_id=? AND owner_revision=? AND relation='concept'",
                           (value.id, value.revision))
    result = read(catalog_storage)
    if owner == 'concept':
        item = next(item for item in result.concepts if item.ref == reference(value))
        assert item.mapping_state == 'unresolved' and item.prerequisite_refs == []
    elif owner == 'block':
        assert target(result, fixture.block).mapping_state == 'unresolved'
        assert target(result, fixture.block).concept_refs == []
        assert target(result, fixture.block).available
    else:
        assessment = target(result, fixture.assessment)
        assert assessment.mapping_state == 'unresolved' and not assessment.test_ready
        assert assessment.test_warning_codes == ['CONCEPT_MAPPING_UNRESOLVED']
        assert assessment.course_refs == []


def test_ambiguous_mapping_and_cross_workspace_dependency_do_not_guess(catalog_storage):
    database, identity, fixture = catalog_storage
    concept2 = fixture.concept.model_copy(update={'revision': 2, 'title': '变化'})
    ContentService(database).publish(identity.workspace_id, [concept2], {})
    with database.transaction() as connection:
        connection.execute("INSERT INTO object_dependencies(owner_id,owner_revision,target_id,target_revision,relation) VALUES(?,?,?,?,?)",
            (fixture.block.id, 1, concept2.id, 2, 'concept'))
    assert target(read(catalog_storage), fixture.block).mapping_state == 'unresolved'
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) SELECT 'workspace_other','other',created_at FROM workspace LIMIT 1")
        connection.execute("UPDATE objects SET workspace_id='workspace_other' WHERE id=?", (concept2.id,))
    assert_error('CONTENT_HASH_MISMATCH', lambda: read(catalog_storage))


@pytest.mark.parametrize('corruption', ['metadata', 'reference', 'body_registration'])
def test_integrity_damage_fails_closed(catalog_storage, corruption):
    database, _, fixture = catalog_storage
    with database.transaction() as connection:
        if corruption in {'metadata', 'reference'}:
            # Deliberately bypass immutability only in this damaged-storage fixture.
            connection.execute('DROP TRIGGER revisions_no_update')
        if corruption == 'metadata':
            connection.execute("UPDATE revisions SET sha256=? WHERE object_id=?", ('f' * 64, fixture.block.id))
        elif corruption == 'reference':
            lesson = fixture.lesson.model_copy(update={'block_refs': [reference(fixture.block).model_copy(update={'sha256': 'f' * 64})]})
            connection.execute('UPDATE revisions SET metadata_json=?,sha256=? WHERE object_id=?',
                (canonical_bytes(lesson).decode(), metadata_sha256(lesson), lesson.id))
        else:
            connection.execute('DELETE FROM block_bodies WHERE block_id=?', (fixture.block.id,))
    assert_error('CONTENT_HASH_MISMATCH', lambda: read(catalog_storage))


def test_body_bytes_are_checked_by_content_body_not_catalog(catalog_storage):
    database, identity, fixture = catalog_storage
    content = ContentService(database)
    body, digest = content.body(identity.workspace_id, fixture.block.id, 1)
    assert body == fixture.bodies[fixture.block.body_path] and digest == fixture.block.body_sha256
    blob = database.settings.data_dir / 'blobs' / digest[:2] / digest
    blob.unlink()
    assert target(read(catalog_storage), fixture.block).available
    with pytest.raises(ApiError):
        content.body(identity.workspace_id, fixture.block.id, 1)


def test_real_independent_readiness_changes_with_review_and_seen_history(catalog_storage):
    database, identity, fixture = catalog_storage
    safe = fixture.assessment.model_copy(update={'id': 'assessment_catalog_safe', 'question_refs': [reference(fixture.questions[0])]})
    ContentService(database).publish(identity.workspace_id, [safe], {})
    before = read(catalog_storage)
    assert not target(before, safe).test_ready
    approved = fixture.solutions[0].model_copy(update={'revision': 2, 'review_status': 'approved'})
    put_answer(database, approved)
    reviewed = read(catalog_storage)
    assert target(reviewed, safe).test_ready
    assert target(reviewed, safe).material_review == 'unreviewed'
    assert reviewed.content_basis_sha256 != before.content_basis_sha256
    service = AssessmentService(database)
    attempt = service.create_attempt(identity, safe.id, AssessmentAttemptCreate(assessment_ref=reference(safe), mode='independent'), 'start')
    assert_error('ASSESSMENT_ACTIVE', lambda: read(catalog_storage))
    assert_error('ASSESSMENT_ACTIVE', lambda: read(catalog_storage, 'course_unknown'))
    service.abandon(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'abandon')
    seen = read(catalog_storage)
    assert not target(seen, safe).test_ready
    assert 'INDEPENDENT_NOVELTY_UNAVAILABLE' in target(seen, safe).test_warning_codes
    assert seen.content_basis_sha256 != reviewed.content_basis_sha256


def test_global_orphan_and_course_scopes_and_routes(catalog_storage):
    database, identity, fixture = catalog_storage
    orphan = assessment_fixture('orphan')
    ContentService(database).publish(identity.workspace_id, [orphan.concept, *orphan.questions, orphan.assessment], {})
    route = dm.Route(id='route_catalog', revision=1, title='实际路线', goal='阅读', steps=[dm.RouteStep(id='step_catalog',
        title='阅读原修订', target=reference(fixture.block), completion_rule='read')])
    ContentService(database).publish(identity.workspace_id, [route], {})
    result = read(catalog_storage)
    assert result.routes == [route]
    item = target(result, orphan.assessment)
    assert item.available and item.course_refs == [] and item.navigation_options[0].course_ref is None
    assert all(item.target_ref != reference(orphan.assessment) for item in read(catalog_storage, fixture.course.id).candidates)
    assert_error('REFERENCE_MISSING', lambda: read(catalog_storage, 'course_unknown'))
    with database.connect() as connection:
        assert_error('TRANSACTION_REQUIRED', lambda: recommendation_catalog(connection, identity.workspace_id))
    with database.transaction() as connection:
        assert_error('REFERENCE_MISSING', lambda: recommendation_catalog(connection, 'workspace_unknown'))


def test_sqlite_query_only_enforces_no_write(catalog_storage):
    database, identity, _ = catalog_storage
    with database.connect() as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        result = recommendation_catalog(connection, identity.workspace_id)
        assert result.candidates and connection.total_changes == 0
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            connection.execute("UPDATE outbox SET delivered_at='2099-01-01T00:00:00Z'")
