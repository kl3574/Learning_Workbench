"""Real graded observations and practice actions; no learned state is seeded."""

from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.concept_states import ConceptStateService
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.grading import GradingWorker
from services.api.app.application.practice import PracticeService
from services.api.app.application.profile import ProfileService
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.security import issue_bootstrap_code
from services.api.app.main import create_app
from services.api.app.practice_dto import PracticeHintRequest, PracticeSessionCreate, PracticeSolutionRequest, PracticeSubmitRequest
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_assessment_attempts import insert_answer, start
from tests.integration.test_learning_evidence import counts, manual, raw_history, storage, submit
from tests.integration.test_learner_profile import profile_rows, request

__all__ = ['storage']


def test_empty_declared_skill_rows_and_standalone_no_skill_catalog_are_not_fake_knowledge(storage):
    database, identity, fixture, _ = storage
    standalone = dm.Concept(id='concept_standalone', revision=1, title=fixture.concept.title)
    ContentService(database).publish(identity.workspace_id, [standalone], {})
    state = ConceptStateService(database).read(identity.workspace_id)
    assert {item.ref.id for item in state.concepts} == {fixture.concept.id, standalone.id}
    assert {item.skill for item in state.items} == set(fixture.concept.skill_dimensions)
    assert all(item.evidence_state == 'none' and item.independent_count == 0 and not item.sources for item in state.items)
    assert all(item.concept_id == fixture.concept.id for item in state.items)
    filtered = ConceptStateService(database).read(identity.workspace_id, fixture.course.id)
    assert [item.ref.id for item in filtered.concepts] == [fixture.concept.id]


def test_self_report_cannot_create_or_raise_independent_evidence(storage):
    database, identity, fixture, _ = storage
    state = ConceptStateService(database)
    before = state.read(identity.workspace_id)
    ProfileService(database).save(identity, request(self_assessments=[{'concept_id': fixture.concept.id, 'level': 'independent_use'}]), 'self')
    after = state.read(identity.workspace_id)
    for old, new in zip(before.items, after.items, strict=True):
        assert new.self_report is not None and new.self_report.level == 'independent_use'
        assert new.self_report.origin == 'self_report'
        assert new.evidence_state == old.evidence_state == 'none'
        assert new.sources == old.sources == [] and new.independent_count == 0


def test_real_unreviewed_and_manual_regrade_keep_latest_sources_and_original_submission_time(storage):
    database, identity, fixture, _ = storage
    attempt = submit(storage)
    assert GradingWorker(database).run_once()
    service = ConceptStateService(database)
    first = service.read(identity.workspace_id)
    first_sources = [source for row in first.items for source in row.sources]
    assert len(first_sources) == len(fixture.questions)
    assert sum(row.null_count for row in first.items) == 5
    manual(storage, attempt.id)
    before, original, profiles = counts(database), raw_history(database), profile_rows(database)
    current = service.read(identity.workspace_id, fixture.course.id)
    sources = [source for row in current.items for source in row.sources]
    assert len(sources) == 5 and {source.grading_revision for source in sources} == {2}
    assert {source.submitted_at for source in sources} == {source.submitted_at for source in first_sources}
    assert sum(row.null_count for row in current.items) == 0
    assert all(row.evidence_state == 'none' and row.independent_count == 0 for row in current.items)
    assert all(source.evidence.score == .5 and 'ANSWER_UNREVIEWED' in source.reason_codes for source in sources)
    assert counts(database) == before and raw_history(database) == original and profile_rows(database) == profiles
    for private in ('solution_markdown', 'feedback_markdown', 'private_pins', 'accepted_answers', 'responses'):
        assert private not in current.model_dump_json()


def test_actual_controlled_approved_wrong_responses_are_support_evidence_not_absent_evidence(storage):
    database, identity, fixture, _ = storage
    # Controlled software-rule preconditions only, not a human review claim.
    for answer in fixture.solutions:
        insert_answer(database, answer.model_copy(update={'revision': 2, 'review_status': 'approved'}))
    submit(storage)
    assert GradingWorker(database).run_once()
    rows = ConceptStateService(database).read(identity.workspace_id).items
    contributing = [row for row in rows if row.independent_count]
    assert contributing and all(row.evidence_state == 'needs_support' for row in contributing)
    assert all(source.evidence.score == 0 for row in contributing for source in row.sources if source.evidence.eligible)
    assert sum(row.independent_count for row in rows) == 4


def test_exact_concept_revision_change_marks_applicability_pending_retains_historical_sources(storage):
    database, identity, fixture, _ = storage
    for answer in fixture.solutions:
        insert_answer(database, answer.model_copy(update={'revision': 2, 'review_status': 'approved'}))
    submit(storage)
    assert GradingWorker(database).run_once()
    original = raw_history(database)
    changed = fixture.concept.model_copy(update={'revision': 2, 'title': 'Explicitly changed concept revision'})
    ContentService(database).publish(identity.workspace_id, [changed], {})
    result = ConceptStateService(database).read(identity.workspace_id)
    assert {value.ref.revision for value in result.concepts} == {1, 2}
    old = [row for row in result.items if row.concept_ref.revision == 1]
    assert sum(row.pending_review_count for row in old) == 5
    assert all(row.stale_count == 0 and row.evidence_state == 'none' for row in old)
    assert all(source.applicability.status == 'pending_review' for row in old for source in row.sources)
    assert all(not row.sources for row in result.items if row.concept_ref.revision == 2)
    assert raw_history(database) == original


def test_practice_counts_real_submitted_sessions_and_help_events_separately_from_question_attempts(storage):
    database, identity, fixture, _ = storage
    practice = PracticeService(database)
    active = practice.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), 'practice')
    service = ConceptStateService(database)
    assert all(row.practice_submission_count == 0 for row in service.read(identity.workspace_id).items)
    hint = practice.hint(identity, active.id, PracticeHintRequest(question_id=fixture.questions[0].id,
        expected_revision=1, level=1), 'hint')
    solution = practice.solution(identity, active.id, PracticeSolutionRequest(question_id=fixture.questions[0].id,
        expected_revision=hint.revision), 'solution')
    practice.submit(identity, active.id, PracticeSubmitRequest(expected_revision=solution.revision), 'submit')
    result = service.read(identity.workspace_id, fixture.course.id)
    assert all(row.practice_submission_count == 1 for row in result.items)  # Two recall questions are one session.
    recall = next(row for row in result.items if row.skill == 'recall')
    assert recall.hint_count == recall.solution_count == 1
    assert recall.hint_sources[0].event_id == hint.exposure_event_id
    assert recall.solution_sources[0].event_id == solution.exposure_event_id
    assert all(row.independent_count == 0 and not row.sources for row in result.items)
    # Another real course shares the concept, but not this practice's exact lesson.
    other_lesson = fixture.lesson.model_copy(update={'id': 'lesson_other'})
    other = dm.Course(id='course_other', revision=1, title='Same concept, distinct course', audience='Synthetic',
                      concept_refs=[reference(fixture.concept)], lesson_refs=[reference(other_lesson)])
    ContentService(database).publish(identity.workspace_id, [other_lesson, other], {})
    unrelated = service.read(identity.workspace_id, other.id)
    assert all(row.practice_submission_count == row.hint_count == row.solution_count == 0 for row in unrelated.items)


def test_real_evidence_skill_is_retained_even_if_concept_declares_no_skill(storage):
    database, identity, _, _ = storage
    original = assessment_fixture('undeclared')
    concept = original.concept.model_copy(update={'skill_dimensions': []})
    course = original.course.model_copy(update={'concept_refs': [reference(concept)]})
    fixture = replace(original, concept=concept, course=course)
    ContentService(database).publish(identity.workspace_id, fixture.public_objects, fixture.bodies)
    for answer in fixture.solutions:
        insert_answer(database, answer)
    attempt = start(storage, key='undeclared', fixture=fixture)
    storage[3].submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'undeclared-submit')
    assert GradingWorker(database).run_once()
    result = ConceptStateService(database).read(identity.workspace_id, course.id)
    assert result.concepts[0].skill_dimensions == []
    assert {row.skill for row in result.items} == {'recall', 'compute', 'derive'}
    assert sum(len(row.sources) for row in result.items) == 5


def test_guard_and_damaged_history_cannot_be_hidden_by_a_different_course_filter(storage):
    database, identity, fixture, _ = storage
    service = ConceptStateService(database)
    attempt = start(storage)
    with pytest.raises(ApiError) as denied:
        service.read(identity.workspace_id, fixture.course.id)
    assert denied.value.status == 409
    storage[3].submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), 'guard-submit')
    assert GradingWorker(database).run_once()
    other = assessment_fixture('other')
    ContentService(database).publish(identity.workspace_id, other.public_objects, other.bodies)
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER evidence_binding_no_update')
        connection.execute('UPDATE learning_grade_bindings SET binding_sha256=?', ('0' * 64,))
    with pytest.raises(ApiError) as rejected:
        service.read(identity.workspace_id, other.course.id)
    assert rejected.value.code == 'EVIDENCE_HISTORY_INVALID'


def test_http_full_catalog_projection_and_repeated_scope_are_strict(storage):
    database, _, fixture, _ = storage
    with TestClient(create_app(database.settings), base_url=database.settings.origin) as client:
        boot = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
                           headers={'Origin': database.settings.origin})
        assert boot.status_code == 200
        result = client.get('/api/v1/learning/concept-states', params={'course_id': fixture.course.id})
        assert result.status_code == 200 and result.headers['Cache-Control'] == 'no-store'
        assert result.json()['calibration'] == 'uncalibrated'
        assert result.json()['concepts'][0]['ref'] == reference(fixture.concept).model_dump()
        assert client.get(f'/api/v1/learning/concept-states?course_id={fixture.course.id}&course_id={fixture.course.id}').status_code == 422
        assert client.get('/api/v1/learning/concept-states?skill=recall').status_code == 422
