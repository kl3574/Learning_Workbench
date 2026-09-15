"""Recommendation wire-shape checks; synthetic refs are not stored source evidence."""

from copy import deepcopy
from pathlib import Path
from typing import get_args

import jsonschema
from pydantic import ValidationError
import pytest

from packages.contracts import domain_models as dm
from services.api.app.recommendation_dto import (
    RecommendationActivityRef, RecommendationDecisionWrite, RecommendationEvidenceRef,
    RecommendationPage, RecommendationProfileBasis, RecommendationReason,
    RecommendationRouteBasis, RecommendationView,
)

NOW = '2026-09-14T00:00:00Z'


def ref(entity: str, suffix: str = 'one') -> dict:
    return {'entity': entity, 'id': f'{entity}_{suffix}', 'revision': 1, 'sha256': 'a' * 64}


def evidence() -> dict:
    return {
        'evidence': {'id': 'evidence_one', 'event_id': 'event_grade', 'concept_id': 'concept_one',
                     'skill': 'compute', 'eligible': True, 'reason': 'eligible', 'score': 0.0,
                     'independence': 'independent', 'freshness': 'novel'},
        'question_ref': ref('question'), 'concept_ref': ref('concept'), 'assessment_ref': ref('assessment'),
        'attempt_id': 'attempt_one', 'grading_revision': 1, 'submitted_at': NOW,
        'applicability': 'usable', 'grading_origin': 'deterministic',
    }


def view() -> dict:
    return {
        'id': 'recommendation_one', 'target_ref': ref('block'), 'target_title': '合成材料',
        'action': 'read', 'reason_codes': ['assessment_error'], 'explanation': '合成契约样例，非产品来源证明。',
        'evidence_refs': [evidence()], 'activity_refs': [], 'profile_basis': None, 'route_basis': None,
        'prerequisite_gaps': [ref('concept')],
        'navigation_options': [{'kind': 'reader', 'course_ref': ref('course'),
                                'lesson_ref': ref('lesson'), 'block_ref': ref('block')}],
        'estimated_minutes': None, 'rule_version': 'rules-1.0.0', 'generated_at': NOW,
        'staleness': 'current', 'decision': 'pending', 'decision_revision': 1,
        'decision_sha256': 'b' * 64, 'decision_reason': None,
    }


def page() -> dict:
    return {'items': [view()], 'next_cursor': None, 'projection_state': 'ready', 'warnings': [],
            'snapshot_id': 'recommendation_snapshot_one', 'generated_at': NOW, 'rule_version': 'rules-1.0.0',
            'rule_parameters': {'review_after_days': 3, 'calibration': 'uncalibrated'}}


def test_application_shapes_leave_all_fifty_four_core_contracts_intact():
    assert len(dm.CONTRACTS) == 54
    assert not issubclass(RecommendationView, dm.Recommendation)
    legacy = {'id': 'recommendation_old', 'target': ref('lesson'), 'reason_code': 'user_goal',
              'explanation': 'shape only', 'evidence_ids': [], 'generated_at': NOW}
    dm.Recommendation.model_validate(legacy)
    for reason in ['read_without_practice', 'practice_without_independent']:
        with pytest.raises(ValidationError):
            dm.Recommendation.model_validate({**legacy, 'reason_code': reason})
    source = (Path(__file__).resolve().parents[2] / 'PRODUCT_DESIGN.md').read_text()
    embedded = source.split('<!-- BEGIN FILE: packages/contracts/domain_models.py -->\n~~~python\n')[1].split('\n~~~\n<!-- END FILE -->')[0]
    assert embedded + '\n' == (Path(__file__).resolve().parents[2] / 'packages/contracts/domain_models.py').read_text()


@pytest.mark.parametrize('reason', get_args(RecommendationReason))
def test_each_required_reason_is_a_distinct_finite_value(reason):
    value = view()
    value['reason_codes'] = [reason]
    assert RecommendationView.model_validate(value).reason_codes == [reason]


@pytest.mark.parametrize('field', ['target', 'reason_code', 'evidence_ids', 'unresolved_needs', 'mastery_probability'])
def test_unstated_aliases_and_fake_mastery_fields_are_rejected(field):
    with pytest.raises(ValidationError):
        RecommendationView.model_validate({**view(), field: None})


@pytest.mark.parametrize('field', ['evidence_refs', 'activity_refs', 'profile_basis', 'route_basis',
                                  'estimated_minutes', 'decision_reason'])
def test_nullable_or_empty_fields_are_still_required(field):
    value = view()
    del value[field]
    with pytest.raises(ValidationError):
        RecommendationView.model_validate(value)


@pytest.mark.parametrize('field,bad', [('reason_codes', []), ('reason_codes', ['unknown']),
    ('target_title', ''), ('rule_version', ''), ('estimated_minutes', 0), ('estimated_minutes', True),
    ('decision_revision', 0), ('decision_sha256', 'W/"abc"'), ('generated_at', '2026-02-30T00:00:00Z')])
def test_invalid_scalar_boundaries_are_rejected(field, bad):
    with pytest.raises(ValidationError):
        RecommendationView.model_validate({**view(), field: bad})


@pytest.mark.parametrize('field', ['reason_codes', 'evidence_refs', 'prerequisite_gaps', 'navigation_options'])
def test_duplicate_frozen_source_identities_are_rejected(field):
    value = view()
    value[field] += deepcopy(value[field])
    with pytest.raises(ValidationError):
        RecommendationView.model_validate(value)


@pytest.mark.parametrize('field', ['revision', 'sha256', 'id', 'entity'])
def test_navigation_checks_the_complete_target_reference(field):
    value = view()
    value['navigation_options'][0]['block_ref'][field] = {
        'revision': 2, 'sha256': 'c' * 64, 'id': 'block_other', 'entity': 'lesson',
    }[field]
    with pytest.raises(ValidationError):
        RecommendationView.model_validate(value)


def test_practice_and_parentless_assessment_have_different_closed_navigation_shapes():
    value = view()
    value.update(action='practice', target_ref=ref('practice_set'), reason_codes=['read_without_practice'],
                 evidence_refs=[], activity_refs=[{'kind': 'read_marked', 'event_id': 'event_read',
                     'target_ref': ref('lesson'), 'source_id': None, 'occurred_at': NOW}],
                 navigation_options=[{'kind': 'practice', 'course_ref': ref('course'),
                     'lesson_ref': ref('lesson'), 'practice_ref': ref('practice_set')}])
    RecommendationView.model_validate(value)
    value.update(action='test', target_ref=ref('assessment'), reason_codes=['practice_without_independent'],
                 navigation_options=[{'kind': 'assessment', 'assessment_ref': ref('assessment'), 'course_ref': None}])
    RecommendationView.model_validate(value)
    with pytest.raises(ValidationError):
        RecommendationView.model_validate({**value, 'action': 'read'})


@pytest.mark.parametrize('field', ['question_ref', 'concept_ref', 'assessment_ref'])
def test_evidence_refs_are_not_fake_content_evidence_entities(field):
    value = evidence()
    value[field] = ref('evidence')
    with pytest.raises(ValidationError):
        RecommendationEvidenceRef.model_validate(value)


def test_evidence_mapping_and_private_payload_rejection():
    with pytest.raises(ValidationError):
        RecommendationEvidenceRef.model_validate({**evidence(), 'concept_ref': ref('concept', 'other')})
    for field in ['private_trace', 'solution_markdown', 'answer', 'private_pin']:
        with pytest.raises(ValidationError):
            RecommendationEvidenceRef.model_validate({**evidence(), field: 'private'})


@pytest.mark.parametrize('kind,entity,source', [('read_marked', 'lesson', None),
    ('practice_submitted', 'practice_set', 'practice_session_one'), ('test_submitted', 'assessment', 'attempt_one')])
def test_activity_identity_retains_actual_source_unit(kind, entity, source):
    value = {'kind': kind, 'event_id': 'event_one', 'target_ref': ref(entity), 'source_id': source, 'occurred_at': NOW}
    RecommendationActivityRef.model_validate(value)
    with pytest.raises(ValidationError):
        RecommendationActivityRef.model_validate({**value, 'source_id': 'attempt_other' if source is None else None})


def test_basis_types_reject_foreign_entity_and_duplicate_source_claims():
    with pytest.raises(ValidationError):
        RecommendationRouteBasis.model_validate({'route_ref': ref('lesson'), 'step_id': 'step_one', 'source_event_ids': []})
    with pytest.raises(ValidationError):
        RecommendationProfileBasis.model_validate({'revision': 1, 'goals': [],
            'goal_concept_ids': ['concept_one', 'concept_one'], 'self_assessments': []})
    value = view()
    value['prerequisite_gaps'] = [ref('lesson')]
    with pytest.raises(ValidationError):
        RecommendationView.model_validate(value)


def test_decision_write_requires_nullable_reason_and_rejects_pending_or_client_revision():
    assert RecommendationDecisionWrite.model_validate({'decision': 'dismissed', 'reason': None}).reason is None
    for body in [{'decision': 'accepted'}, {'decision': 'pending', 'reason': None},
                 {'decision': 'accepted', 'reason': None, 'expected_revision': 1},
                 {'decision': 'accepted', 'reason': False}]:
        with pytest.raises(ValidationError):
            RecommendationDecisionWrite.model_validate(body)


def test_decision_projection_preserves_pending_and_actual_history_revision_boundaries():
    RecommendationView.model_validate(view())
    for changes in [{'decision_revision': 2}, {'decision_reason': 'invented'}, {'decision': 'accepted'}]:
        with pytest.raises(ValidationError):
            RecommendationView.model_validate({**view(), **changes})
    RecommendationView.model_validate({**view(), 'decision': 'accepted', 'decision_revision': 2})
    RecommendationView.model_validate({**view(), 'decision': 'dismissed', 'decision_revision': 3, 'decision_reason': '更正理由'})


@pytest.mark.parametrize('state', ['pending_refresh', 'stale', 'failed'])
def test_old_snapshot_states_never_claim_current_items(state):
    value = page()
    value['projection_state'] = state
    with pytest.raises(ValidationError):
        RecommendationPage.model_validate(value)
    value['items'][0]['staleness'] = 'stale'
    assert RecommendationPage.model_validate(value).projection_state == state


def test_empty_workspace_does_not_require_fake_needs_or_snapshot():
    value = {**page(), 'items': [], 'snapshot_id': None, 'generated_at': None, 'projection_state': 'missing'}
    assert RecommendationPage.model_validate(value).warnings == []
    with pytest.raises(ValidationError):
        RecommendationPage.model_validate({**value, 'projection_state': 'ready'})
    with pytest.raises(ValidationError):
        RecommendationPage.model_validate({**value, 'items': [view()]})


def test_page_binds_batch_clock_rule_and_nullable_snapshot():
    for changes in [{'generated_at': None}, {'projection_state': 'missing'},
                    {'generated_at': '2026-09-15T00:00:00Z'}, {'rule_version': 'new-rules'}]:
        with pytest.raises(ValidationError):
            RecommendationPage.model_validate({**page(), **changes})


def test_optional_total_hint_is_not_nullable_or_smaller_than_page():
    value = page()
    assert 'total_hint' not in RecommendationPage.model_validate(value).model_dump(mode='json')
    assert RecommendationPage.model_validate({**value, 'total_hint': 1}).model_dump()['total_hint'] == 1
    schema = RecommendationPage.model_json_schema()
    assert 'total_hint' not in schema['required']
    assert schema['properties']['total_hint']['type'] == 'integer'
    for invalid in [None, -1, True, 0]:
        with pytest.raises(ValidationError):
            RecommendationPage.model_validate({**value, 'total_hint': invalid})


def test_every_nested_schema_is_closed_and_generated_schema_checks_real_samples():
    schema = RecommendationPage.model_json_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema['additionalProperties'] is False
    for definition in schema['$defs'].values():
        if definition.get('type') == 'object':
            assert definition['additionalProperties'] is False
    jsonschema.validate(page(), schema)
    value = page()
    value['items'][0]['evidence_refs'][0]['evidence']['answer'] = 'private'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, schema)
