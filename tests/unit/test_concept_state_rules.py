"""Counterexamples for an uncalibrated rule, not empirical mastery evidence."""

import pytest
from pydantic import ValidationError

from packages.contracts import domain_models as dm
from services.api.app.application.concept_state_rules import derive_concept_state
from services.api.app.concept_state_dto import ConceptStateSource


def source(number=1, *, attempt=None, group=None, score=1.0, eligible=True,
           independence='independent', freshness='novel', applicability='usable', day=None, grade=1):
    concept = dm.ContentRef(entity='concept', id='concept_rule', revision=1, sha256='c' * 64)
    return ConceptStateSource(evidence=dm.Evidence(id=f'evidence_{number}', event_id=f'event_{number}',
        concept_id=concept.id, skill='compute', eligible=eligible, reason='synthetic rule input', score=score,
        independence=independence, freshness=freshness), question_ref=dm.ContentRef(entity='question',
        id=f'question_{number}', revision=1, sha256='a' * 64), concept_ref=concept,
        assessment_ref=dm.ContentRef(entity='assessment', id='assessment_rule', revision=1, sha256='b' * 64),
        attempt_id=f'attempt_{attempt or number}', grading_revision=grade,
        submitted_at=f'2026-09-{day or number:02d}T00:00:00Z', exposure_group=f'group_{group or number}',
        qualification_basis='submission_frozen', reason_codes=[],
        applicability={'status': applicability, 'reason_codes': [], 'checked_refs': [concept.model_dump()]})


def test_no_observations_is_none_and_zero_not_confidence():
    result = derive_concept_state([])
    assert result.evidence_state == 'none' and result.independent_count == 0
    assert result.state_input_evidence_ids == []


@pytest.mark.parametrize('count,attempts,expected', [(1, [1], 'preliminary'), (2, [1, 2], 'preliminary'),
    (3, [1, 1, 1], 'preliminary'), (3, [1, 1, 2], 'consistent')])
def test_three_groups_alone_or_two_attempts_alone_do_not_imply_consistent(count, attempts, expected):
    values = [source(i + 1, attempt=attempts[i]) for i in range(count)]
    assert derive_concept_state(values).evidence_state == expected


@pytest.mark.parametrize('score', [0.0, 0.999999])
def test_any_non_full_current_representative_requires_support(score):
    assert derive_concept_state([source(1), source(2, score=score), source(3)]).evidence_state == 'needs_support'


def test_group_representatives_deduplicate_only_thresholds_not_question_attempt_counts():
    values = [source(1, group=1, score=0.0), source(2, group=1), source(3, group=1), source(4, group=2)]
    result = derive_concept_state(values)
    assert result.independent_count == 4 and result.evidence_state == 'preliminary'
    assert result.state_input_evidence_ids == ['evidence_4', 'evidence_3']


def test_latest_three_groups_ignore_older_wrong_sample_but_keep_it_in_count():
    result = derive_concept_state([source(1, score=0.0), source(2), source(3), source(4)])
    assert result.evidence_state == 'consistent' and result.independent_count == 4
    assert result.state_input_evidence_ids == ['evidence_4', 'evidence_3', 'evidence_2']


def test_regrade_number_and_new_evidence_id_cannot_promote_an_old_submission_into_window():
    result = derive_concept_state([source(99, day=1, grade=9, score=0.0), source(2), source(3), source(4)])
    assert result.evidence_state == 'consistent'
    assert result.state_input_evidence_ids == ['evidence_4', 'evidence_3', 'evidence_2']


def test_repeated_assisted_unknown_null_pending_and_stale_are_overlapping_not_a_score_pool():
    values = [source(1, eligible=False, independence='assisted', freshness='repeated'),
        source(2, eligible=False, independence='unknown', freshness='unknown', score=None),
        source(3, applicability='pending_review'), source(4, applicability='confirmed_stale')]
    result = derive_concept_state(values)
    assert result.evidence_state == 'none' and result.independent_count == 0
    assert (result.assisted_count, result.repeated_count, result.unknown_count, result.null_count,
            result.pending_review_count, result.stale_count) == (1, 1, 1, 1, 1, 1)


def test_stale_and_pending_inputs_do_not_mask_a_current_wrong_answer():
    result = derive_concept_state([source(1, score=0.0), source(2, applicability='pending_review'),
                                  source(3, applicability='confirmed_stale')])
    assert result.evidence_state == 'needs_support' and result.state_input_evidence_ids == ['evidence_1']


@pytest.mark.parametrize('change', ['revision', 'skill', 'duplicate', 'invalid_copy', 'contradiction'])
def test_invalid_or_mixed_exact_identity_cannot_silently_aggregate(change):
    first, second = source(1), source(2)
    if change == 'revision':
        second = second.model_copy(update={'concept_ref': second.concept_ref.model_copy(update={'revision': 2})})
    elif change == 'skill':
        second = second.model_copy(update={'evidence': second.evidence.model_copy(update={'skill': 'recall'})})
    elif change == 'duplicate':
        second = first
    elif change == 'invalid_copy':
        second = second.model_copy(update={'grading_revision': 0})
    else:
        second = second.model_copy(update={'evidence': second.evidence.model_copy(update={'freshness': 'repeated'})})
    with pytest.raises((ValueError, ValidationError)):
        derive_concept_state([first, second])


def test_equal_times_have_stable_order_independent_of_input_order():
    values = [source(1, day=1), source(2, day=1), source(3, day=1), source(4, day=1)]
    assert derive_concept_state(values) == derive_concept_state(list(reversed(values)))
