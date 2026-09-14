"""Uncalibrated, inspectable latest-three-group rule from ADR 0013.

Counts describe latest successful question-attempt records, not mutually
exclusive buckets. Only usable eligible scored records inform the state.
Group de-duplication limits the rule's representatives, never source retention.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from pydantic import Field

from packages.contracts import domain_models as dm

from ..concept_state_dto import ConceptStateSource

RULE_VERSION = 'learning-state-v1'


class ConceptRuleDecision(dm.StrictModel):
    evidence_state: Literal['none', 'preliminary', 'needs_support', 'consistent']
    state_input_evidence_ids: list[dm.Id] = Field(max_length=3)
    independent_count: int = Field(ge=0)
    assisted_count: int = Field(ge=0)
    stale_count: int = Field(ge=0)
    repeated_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    null_count: int = Field(ge=0)
    pending_review_count: int = Field(ge=0)


def observation_order(source: ConceptStateSource) -> tuple[datetime, str, str, str]:
    """Original submission time; stable IDs break simultaneous-submission ties."""
    return (datetime.fromisoformat(source.submitted_at.replace('Z', '+00:00')),
            source.attempt_id, source.question_ref.id, source.evidence.id)


def derive_concept_state(sources: Sequence[ConceptStateSource]) -> ConceptRuleDecision:
    values = [ConceptStateSource.model_validate(item.model_dump(mode='json')) for item in sources]
    identities = {(v.concept_ref.id, v.concept_ref.revision, v.concept_ref.sha256, v.evidence.skill) for v in values}
    if len(identities) > 1 or len({v.evidence.id for v in values}) != len(values):
        raise ValueError('one exact concept/skill and unique evidence identities are required')
    for value in values:
        evidence = value.evidence
        if evidence.eligible and (evidence.score is None or evidence.independence != 'independent'
                                  or evidence.freshness != 'novel' or value.qualification_basis != 'submission_frozen'):
            raise ValueError('eligible source conflicts with its frozen qualification metadata')
    candidates = [v for v in values if v.applicability.status == 'usable' and v.evidence.eligible
                  and v.evidence.score is not None]
    representatives: list[ConceptStateSource] = []
    groups: set[str] = set()
    for candidate in sorted(candidates, key=observation_order, reverse=True):
        if candidate.exposure_group in groups:
            continue
        representatives.append(candidate)
        groups.add(candidate.exposure_group)
        if len(representatives) == 3:
            break
    state: Literal['none', 'preliminary', 'needs_support', 'consistent'] = 'none'
    if representatives:
        if any(v.evidence.score is not None and v.evidence.score < 1 for v in representatives):
            state = 'needs_support'
        elif len(representatives) == 3 and len({v.attempt_id for v in representatives}) >= 2:
            state = 'consistent'
        else:
            state = 'preliminary'
    return ConceptRuleDecision(evidence_state=state,
        state_input_evidence_ids=[v.evidence.id for v in representatives], independent_count=len(candidates),
        assisted_count=sum(v.evidence.independence == 'assisted' and v.evidence.score is not None for v in values),
        stale_count=sum(v.applicability.status == 'confirmed_stale' for v in values),
        repeated_count=sum(v.evidence.freshness == 'repeated' for v in values),
        unknown_count=sum(v.evidence.independence == 'unknown' or v.evidence.freshness == 'unknown' for v in values),
        null_count=sum(v.evidence.score is None for v in values),
        pending_review_count=sum(v.applicability.status == 'pending_review' for v in values))
