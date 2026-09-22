"""Appendix-A request boundaries only; these DTOs do not register HTTP routes."""
import pytest
from pydantic import ValidationError
from services.api.app.review_dto import DraftReviewWrite, ReviewDecisionWrite


def review():
    return {'expected_revision': 1, 'checks': ['structure'], 'reviewer_note': ''}


def decision():
    return {'expected_revision': 1, 'candidate_sha256': 'a' * 64,
            'mathematical': 'APPROVED', 'sources': 'NOT_APPLICABLE',
            'reason': 'Explicit synthetic human statement, not a persisted approval', 'evidence_artifact_ids': []}


@pytest.mark.parametrize(('field', 'value'), [
    ('expected_revision', True), ('checks', []), ('checks', ['structure', 'structure']),
    ('checks', ['unknown']), ('reviewer_note', '\ud800'), ('candidate_sha256', 'a' * 64),
])
def test_review_rejects_noncontract_input(field, value):
    with pytest.raises(ValidationError):
        DraftReviewWrite.model_validate({**review(), field: value})


@pytest.mark.parametrize(('field', 'value'), [
    ('expected_revision', True), ('mathematical', 'NOT_RUN'), ('sources', 'PASS'),
    ('reason', '  '), ('evidence_artifact_ids', ['artifact_a', 'artifact_a']),
    ('structural', 'PASS'), ('reviewer', 'a_model'), ('independent_pedagogy', 'PASS'),
    ('evidence_paths', ['/a/local/path']), ('candidate_sha256', 'a' * 63),
])
def test_decision_cannot_supply_machine_status_reviewer_paths_or_invalid_claim(field, value):
    with pytest.raises(ValidationError):
        ReviewDecisionWrite.model_validate({**decision(), field: value})


@pytest.mark.parametrize(('cls', 'factory'), [(DraftReviewWrite, review), (ReviewDecisionWrite, decision)])
def test_valid_requests_preserve_original_bytes_without_exposing_repr(cls, factory):
    raw = factory()
    key = 'reviewer_note' if cls is DraftReviewWrite else 'reason'
    raw[key] = 'zz_review_private_sentinel 正文\n'
    value = cls.model_validate(raw)
    assert value.model_dump(mode='json') == raw
    assert repr(value) == cls.__name__ + '()' and str(value) == ''
    with pytest.raises(ValidationError) as caught:
        cls.model_validate({**raw, 'unexpected': 'zz_review_private_sentinel'})
    assert 'zz_review_private_sentinel' not in str(caught.value)
