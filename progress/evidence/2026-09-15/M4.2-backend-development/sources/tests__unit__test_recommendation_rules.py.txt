"""Worked synthetic input examples at the pure recommendation-rule boundary."""

from packages.contracts import domain_models as dm
import pytest
from services.api.app.application.recommendation_content_models import (
    CandidateConcept, CandidateConceptSkill, CandidateCourse, RecommendationCandidate, RecommendationCatalog,
)
from services.api.app.concept_state_dto import ConceptStateResponse
from services.api.app.infrastructure.content_repository import reference
from services.api.app.learning_dto import RouteStepState
from services.api.app.recommendation_dto import RecommendationActivityRef, RecommendationEvidenceRef, RecommendationRuleParameters
from services.api.app.route_dto import RouteAssessmentOption, RoutePracticeOption, RouteReaderOption
from tests.assessment_fixtures import assessment_fixture

NOW = '2026-09-15T10:00:00Z'
READ_AT = '2026-09-14T10:00:00Z'


def rule_inputs():
    from services.api.app.application.recommendation_rules import RecommendationInputs

    fixture = assessment_fixture('rules')
    course_ref, concept_ref, lesson_ref = map(reference, (fixture.course, fixture.concept, fixture.lesson))
    lesson = RecommendationCandidate(target_ref=lesson_ref, title=fixture.lesson.title,
        navigation_options=[RouteReaderOption(kind='reader', course_ref=course_ref, lesson_ref=lesson_ref, block_ref=None)],
        concept_refs=[concept_ref], concept_skills=[], prerequisite_refs=[], course_refs=[course_ref],
        lesson_refs=[lesson_ref], block_refs=[reference(fixture.block)], mapping_state='complete',
        material_review='unreviewed', available=True, unavailable_reason_codes=[], test_ready=False,
        test_warning_codes=[], estimated_minutes=None)
    practice = RecommendationCandidate(target_ref=reference(fixture.practice), title=fixture.practice.title,
        navigation_options=[RoutePracticeOption(kind='practice', course_ref=course_ref, lesson_ref=lesson_ref,
            practice_ref=reference(fixture.practice))], concept_refs=[concept_ref], concept_skills=[],
        prerequisite_refs=[], course_refs=[course_ref], lesson_refs=[lesson_ref], block_refs=[], mapping_state='complete',
        material_review='unreviewed', available=True, unavailable_reason_codes=[], test_ready=False,
        test_warning_codes=[], estimated_minutes=None)
    catalog = RecommendationCatalog(course_refs=[course_ref], courses=[CandidateCourse(ref=course_ref,
        title=fixture.course.title, language=fixture.course.language, difficulty=fixture.course.difficulty, lifecycle='active')],
        concepts=[CandidateConcept(ref=concept_ref, title=fixture.concept.title, skill_dimensions=fixture.concept.skill_dimensions,
            prerequisite_refs=[], mapping_state='complete', available=True)], candidates=[lesson, practice], routes=[],
        content_basis_sha256='a' * 64)
    return RecommendationInputs(catalog=catalog, profile=dm.LearnerProfile(workspace_id='workspace_rules', revision=1),
        concept_states=ConceptStateResponse(items=[], course_refs=[course_ref], concepts=[]), observations=[],
        activities=[RecommendationActivityRef(kind='read_marked', event_id='read_actual', target_ref=lesson_ref,
            source_id=None, occurred_at=READ_AT)], route_states=[]), fixture


def test_real_reading_without_practice_has_its_own_reason_and_original_activity_time():
    from services.api.app.application.recommendation_rules import derive_recommendations

    inputs, fixture = rule_inputs()
    result = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    assert len(result.items) == 1
    item = result.items[0]
    assert item.target_ref == reference(fixture.practice) and item.action == 'practice'
    assert item.reason_codes == ['read_without_practice']
    assert item.evidence_refs == [] and item.profile_basis is None and item.route_basis is None
    assert item.activity_refs[0].occurred_at == READ_AT and item.generated_at == NOW
    assert item.estimated_minutes is None and '未审' in item.explanation
    assert [warning.code for warning in result.warnings] == ['UNREVIEWED_MATERIAL_ONLY']


def test_goals_consider_two_exact_course_parents_without_turning_self_report_into_evidence():
    from services.api.app.application.recommendation_rules import derive_recommendations

    inputs, fixture = rule_inputs()
    other_course = fixture.course.model_copy(update={'id': 'course_second'})
    other_lesson = fixture.lesson.model_copy(update={'id': 'lesson_second'})
    other_ref = reference(other_course)
    candidate = inputs.catalog.candidates[0].model_copy(update={'target_ref': reference(other_lesson),
        'course_refs': [other_ref], 'lesson_refs': [reference(other_lesson)],
        'navigation_options': [RouteReaderOption(kind='reader', course_ref=other_ref,
            lesson_ref=reference(other_lesson), block_ref=None)]})
    inputs.catalog.course_refs.append(other_ref)
    inputs.catalog.courses.append(CandidateCourse(ref=other_ref, title=other_course.title,
        language=other_course.language, difficulty=other_course.difficulty, lifecycle='active'))
    inputs.catalog.candidates.append(candidate)
    inputs.profile.goal_concept_ids = [fixture.concept.id]
    inputs.profile.self_assessments = [dm.SelfAssessment(concept_id=fixture.concept.id,
        level='independent_use', updated_at=READ_AT)]
    inputs.activities = []
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    lessons = [item for item in plan.items if item.action == 'read']
    assert {item.target_ref.id for item in lessons} == {fixture.lesson.id, other_lesson.id}
    assert all(item.reason_codes == ['user_goal'] and item.evidence_refs == [] for item in lessons)
    assert all(item.profile_basis.self_assessments[0].updated_at == READ_AT for item in lessons)


def observation(fixture, *, origin='deterministic', outcome='incorrect', submitted_at=READ_AT,
                applicability='usable', eligible=True):
    from services.api.app.application.recommendation_rules import RecommendationRuleObservation
    return RecommendationRuleObservation(source=RecommendationEvidenceRef(
        evidence=dm.Evidence(id='evidence_actual', event_id='grade_actual', concept_id=fixture.concept.id,
            skill='recall', eligible=eligible, reason='synthetic checked rule input', score=0.0,
            independence='independent', freshness='novel'), question_ref=reference(fixture.questions[0]),
        concept_ref=reference(fixture.concept), assessment_ref=reference(fixture.assessment), attempt_id='attempt_actual',
        grading_revision=1, submitted_at=submitted_at, applicability=applicability, grading_origin=origin), outcome=outcome)


@pytest.mark.parametrize(('origin', 'outcome', 'applicability', 'expected'), [
    ('deterministic', 'incorrect', 'usable', True), ('human_review', 'incorrect', 'usable', False),
    ('deterministic', 'unanswered', 'usable', False), ('deterministic', 'invalid_input', 'usable', False),
    ('deterministic', 'incorrect', 'pending_review', False), ('unknown', None, 'usable', False),
])
def test_only_checked_current_deterministic_incorrect_is_an_assessment_error(origin, outcome, applicability, expected):
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    inputs.activities = []
    inputs.observations = [observation(fixture, origin=origin, outcome=outcome, applicability=applicability)]
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    errors = [item for item in plan.items if item.reason_codes == ['assessment_error']]
    assert bool(errors) is expected
    if expected:
        assert errors[0].target_ref == reference(fixture.lesson)
        assert errors[0].evidence_refs[0].submitted_at == READ_AT


def test_prerequisite_gap_uses_original_exact_dependency_and_self_report_does_not_fill_it():
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    dependent = fixture.concept.model_copy(update={'id': 'concept_advanced', 'prerequisite_ids': [fixture.concept.id]})
    inputs.catalog.concepts.append(CandidateConcept(ref=reference(dependent), title=dependent.title,
        skill_dimensions=['recall'], prerequisite_refs=[reference(fixture.concept)], mapping_state='complete', available=True))
    inputs.catalog.candidates[1].concept_refs = [reference(dependent)]
    inputs.catalog.candidates[1].prerequisite_refs = [reference(fixture.concept)]
    inputs.profile.goal_concept_ids = [dependent.id]
    inputs.profile.self_assessments = [dm.SelfAssessment(concept_id=fixture.concept.id,
        level='independent_use', updated_at=READ_AT)]
    inputs.activities = []
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    gaps = [item for item in plan.items if item.reason_codes == ['prerequisite_gap']]
    assert len(gaps) == 1 and gaps[0].target_ref == reference(fixture.lesson)
    assert gaps[0].prerequisite_gaps == [reference(fixture.concept)]
    assert plan.items[0].reason_codes == ['prerequisite_gap']


@pytest.mark.parametrize('ready', [False, True])
def test_submitted_practice_requires_actual_qualified_independent_test_or_explicit_gap(ready):
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    skill = CandidateConceptSkill(concept_ref=reference(fixture.concept), skill='recall')
    inputs.catalog.candidates[1].concept_skills = [skill]
    assessment = inputs.catalog.candidates[1].model_copy(update={'target_ref': reference(fixture.assessment),
        'navigation_options': [RouteAssessmentOption(kind='assessment', assessment_ref=reference(fixture.assessment),
            course_ref=reference(fixture.course))], 'lesson_refs': [], 'test_ready': ready,
        'test_warning_codes': [] if ready else ['ANSWER_UNREVIEWED']})
    inputs.catalog.candidates.append(assessment)
    inputs.activities.append(RecommendationActivityRef(kind='practice_submitted', event_id='submitted_actual',
        target_ref=reference(fixture.practice), source_id='practice_session_actual', occurred_at=READ_AT))
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    tests = [item for item in plan.items if item.reason_codes == ['practice_without_independent']]
    assert bool(tests) is ready
    if ready:
        assert tests[0].target_ref == reference(fixture.assessment) and tests[0].action == 'test'
        assert tests[0].activity_refs[0].event_id == 'submitted_actual' and tests[0].evidence_refs == []
    else:
        assert 'NO_REVIEWED_ASSESSMENT' in {warning.code for warning in plan.warnings}


@pytest.mark.parametrize(('days', 'due'), [(3, True), (4, False)])
def test_review_uses_original_submission_and_actual_configurable_uncalibrated_days(days, due):
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    inputs.activities = []
    inputs.observations = [observation(fixture, origin='human_review', outcome=None, submitted_at='2026-09-12T10:00:00Z')]
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=days, calibration='uncalibrated'))
    reviews = [item for item in plan.items if item.reason_codes == ['review_due']]
    assert bool(reviews) is due
    if due:
        assert reviews[0].evidence_refs[0].submitted_at == '2026-09-12T10:00:00Z'
        assert plan.valid_until is None
    else:
        assert plan.valid_until == '2026-09-16T10:00:00.000000Z'


def test_next_route_step_uses_exact_route_and_real_completed_dependency_events():
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    inputs.activities = []
    route = dm.Route(id='route_actual', revision=1, title='Actual ordered route', goal='Synthetic goal', steps=[
        dm.RouteStep(id='first', title='Read', target=reference(fixture.lesson), completion_rule='manual'),
        dm.RouteStep(id='second', title='Practice', target=reference(fixture.practice),
            completion_rule='practice_submitted', requires_steps=['first'])])
    inputs.catalog.routes = [route]
    inputs.route_states = [RouteStepState(route_ref=reference(route), step_id='first', completed=True,
        completion_origin='manual', manual_override=True, completed_at=READ_AT, updated_at=READ_AT, source_event_ids=['route_completed']),
        RouteStepState(route_ref=reference(route), step_id='second', completed=False)]
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    assert len(plan.items) == 1
    assert plan.items[0].target_ref == reference(fixture.practice)
    assert plan.items[0].reason_codes == ['next_route_step']
    assert plan.items[0].route_basis.route_ref == reference(route)
    assert plan.items[0].route_basis.source_event_ids == ['route_completed']


def test_cold_imported_prerequisite_relation_does_not_invent_a_learning_need():
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    inputs.activities = []
    inputs.catalog.candidates[1].prerequisite_refs = [reference(fixture.concept)]
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    assert plan.items == [] and plan.warnings == []


def test_text_only_goal_reports_unresolved_mapping_without_guessing_concepts():
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, _ = rule_inputs()
    inputs.activities = []
    inputs.profile.goals = ['Understand estimation from first principles']
    inputs.catalog.candidates = []
    inputs.catalog.course_refs = []
    inputs.catalog.courses = []
    inputs.catalog.concepts = []
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    assert plan.items == []
    assert [warning.code for warning in plan.warnings] == ['EXACT_MAPPING_UNRESOLVED']


def test_same_clock_timestamp_cannot_reuse_an_id_for_changed_frozen_inputs():
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    parameters = RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated')
    first = derive_recommendations(inputs, generated_at=NOW, parameters=parameters)
    inputs.profile.goal_concept_ids = [fixture.concept.id]
    second = derive_recommendations(inputs, generated_at=NOW, parameters=parameters)
    original = next(item for item in first.items if item.reason_codes == ['read_without_practice'])
    changed = next(item for item in second.items if item.reason_codes == ['read_without_practice'])
    assert original.id != changed.id


def test_default_reason_classes_then_goal_coverage_order_distinct_materials():
    from services.api.app.application.recommendation_rules import derive_recommendations
    inputs, fixture = rule_inputs()
    second_concept = fixture.concept.model_copy(update={'id': 'concept_second'})
    second_lesson = fixture.lesson.model_copy(update={'id': 'lesson_z_more_coverage'})
    wider = inputs.catalog.candidates[0].model_copy(update={'target_ref': reference(second_lesson),
        'concept_refs': [reference(fixture.concept), reference(second_concept)], 'lesson_refs': [reference(second_lesson)],
        'navigation_options': [RouteReaderOption(kind='reader', course_ref=reference(fixture.course),
            lesson_ref=reference(second_lesson), block_ref=None)]})
    inputs.catalog.candidates.append(wider)
    inputs.profile.goal_concept_ids = [fixture.concept.id, second_concept.id]
    inputs.activities = []
    inputs.observations = [observation(fixture)]
    plan = derive_recommendations(inputs, generated_at=NOW,
        parameters=RecommendationRuleParameters(review_after_days=3, calibration='uncalibrated'))
    assert [item.reason_codes[0] for item in plan.items[:2]] == ['assessment_error', 'assessment_error']
    assert plan.items[0].target_ref == reference(second_lesson)
    goals = [item for item in plan.items if item.reason_codes == ['user_goal']]
    assert goals[0].target_ref == reference(second_lesson)
