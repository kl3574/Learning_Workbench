"""Assessment-owned safe provenance and current qualification for Recommendation.

Private answer pins and traces stay here. A compatibility probe produces no
persisted response, grade, activity or evidence; only its readiness boolean leaves.
"""

import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm

from ..assessment_dto import AssessmentPreflight
from ..infrastructure.assessment_repository import AssessmentRecord, AssessmentRepository, invalid_snapshot
from ..infrastructure.content_repository import ContentRepository, reference
from ..infrastructure.grading_repository import GradeAudit, GradingRepository
from ..infrastructure.security import guard_subject_access
from .assessment import AssessmentService
from .assessment_content import AssessmentContent
from .content_learning_access import evidence_applicability
from .errors import ApiError
from .evidence import latest_checked_observations
from .grading_rule_models import RULES_VERSION, Outcome
from .grading_rules import grade_item
from .learning_state_models import EvidenceApplicability, EvidenceObservation
from .question_qualification import question_qualification_facts


class RecommendationObservation(dm.StrictModel):
    source: EvidenceObservation
    applicability: EvidenceApplicability
    grading_origin: Literal['deterministic', 'human_review', 'unknown']
    outcome: Outcome | None


class RecommendationAssessmentReadiness(dm.StrictModel):
    preflight: AssessmentPreflight
    independent_ready: bool
    reason_codes: list[str]


def _access(connection: sqlite3.Connection, workspace_id: str) -> None:
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '推荐来源读取需要同一事务的测评快照。')
    guard_subject_access(connection, workspace_id)
    ContentRepository(connection, workspace_id).require_workspace()


def _checked_review_chain(repository: GradingRepository, record: AssessmentRecord,
                           revision: int) -> tuple[dm.GradingResult, GradeAudit]:
    """Bind the full review sequence to actual immutable grading job inputs."""
    expected: list[str] = []
    latest = None
    for current in range(1, revision + 1):
        loaded = repository.load_grade(record, current)
        if loaded is None:
            raise invalid_snapshot()
        result, audit = loaded
        if audit.input.base_grading_revision != current - 1:
            raise invalid_snapshot()
        identifier = audit.input.review_id
        if current == 1 and identifier is not None:
            raise invalid_snapshot()
        if identifier is not None:
            signed, _ = repository.review(identifier, record)
            if identifier in expected or signed.request.expected_grading_revision != current - 1:
                raise invalid_snapshot()
            expected.append(identifier)
        if (audit.review_ids != expected
                or audit.rules_version != RULES_VERSION + ('+human-v1' if expected else '')):
            raise invalid_snapshot()
        latest = result, audit
    if latest is None:
        raise invalid_snapshot()
    return latest


def assessment_recommendation_readiness(connection: sqlite3.Connection, workspace_id: str,
                                        assessment_ref: dm.ContentRef) -> RecommendationAssessmentReadiness:
    """Check actual current startability and independent qualification, without writes."""
    _access(connection, workspace_id)
    content = AssessmentContent(connection, workspace_id)
    blueprint = content.blueprint(assessment_ref)
    preflight = AssessmentService._preflight(content, AssessmentRepository(connection, workspace_id), blueprint)
    reasons = list(preflight.start_block_reason_codes)
    if 'independent' not in blueprint.allowed_modes:
        reasons.append('INDEPENDENT_MODE_UNAVAILABLE')
    if preflight.grading.status != 'reviewed':
        reasons.extend(preflight.grading.reason_codes)
    if preflight.prior_seen.status != 'known':
        reasons.append('PRIOR_SEEN_UNKNOWN')
    if any(item.state != 'unseen' for item in preflight.prior_seen.questions):
        reasons.append('INDEPENDENT_NOVELTY_UNAVAILABLE')
    for question in content.questions(blueprint):
        facts = question_qualification_facts(connection, workspace_id, reference(question))
        if not facts.mapping_valid or not facts.concept_refs:
            reasons.append('CONCEPT_MAPPING_UNRESOLVED')
    if preflight.startable and preflight.grading.status == 'reviewed':
        bundle = content.question_bundle(blueprint)
        for question, pin in zip(bundle.questions, bundle.private_pins, strict=True):
            probe = grade_item(question_ref=reference(question), question=question, pin=pin,
                               solution=content.solution(pin), response=None)
            if probe.item_grade.status != 'graded' or probe.private_trace.outcome != 'unanswered':
                reasons.append('DETERMINISTIC_GRADING_UNAVAILABLE')
    return RecommendationAssessmentReadiness(preflight=preflight,
        independent_ready=preflight.startable and not reasons, reason_codes=sorted(set(reasons)))


def checked_recommendation_observations(connection: sqlite3.Connection,
                                        workspace_id: str) -> list[RecommendationObservation]:
    """Validate all history, then expose the latest item's actual grading origin.

Human regrading retains old deterministic traces in its private audit. Coverage
of each signed item review therefore takes precedence over that historical trace.
No error is inferred from a score, a blank answer or a human-assigned score.
"""
    _access(connection, workspace_id)
    sources = latest_checked_observations(connection, workspace_id)
    repository = GradingRepository(connection, workspace_id)
    origins: dict[tuple[str, int, str], tuple[Literal['deterministic', 'human_review', 'unknown'], Outcome | None]] = {}
    for source in sources:
        key = (source.attempt_id, source.grading_revision, source.question_ref.model_dump_json())
        if key in origins:
            continue
        record = repository.attempts.load(source.attempt_id)
        result, audit = _checked_review_chain(repository, record, source.grading_revision)
        reviewed = {item.question_id: item for review_id in audit.review_ids
                    for item in repository.review(review_id, record)[0].request.item_reviews}
        content = AssessmentContent(connection, workspace_id)
        for item, trace in zip(result.items, audit.traces, strict=True):
            question = content.exact(trace.question_ref)
            if not isinstance(question, dm.QuestionPublic):
                raise invalid_snapshot()
            replay = grade_item(question_ref=trace.question_ref, question=question, pin=trace.private_pin,
                               solution=content.solution(trace.private_pin), response=trace.response)
            if replay.private_trace != trace:
                raise invalid_snapshot()
            item_key = (record.id, result.grading_revision, item.question_ref.model_dump_json())
            if item.question_ref.id in reviewed:
                review = reviewed[item.question_ref.id]
                expected = dm.ItemGrade(question_ref=item.question_ref, max_score=question.max_score,
                    score=review.score, status='graded', feedback_markdown=review.feedback_markdown, solution_markdown=None)
                if item != expected:
                    raise invalid_snapshot()
                origins[item_key] = ('human_review', None)
            elif item != replay.item_grade:
                raise invalid_snapshot()
            elif (item.status == 'graded' and trace.private_pin.review_status == 'approved'
                    and trace.outcome in {'correct', 'incorrect', 'unanswered'}):
                origins[item_key] = ('deterministic', trace.outcome)
            else:
                origins[item_key] = ('unknown', None)
    return [RecommendationObservation(source=source,
        applicability=evidence_applicability(connection, workspace_id, source.question_ref, source.concept_ref),
        grading_origin=origins[(source.attempt_id, source.grading_revision, source.question_ref.model_dump_json())][0],
        outcome=origins[(source.attempt_id, source.grading_revision, source.question_ref.model_dump_json())][1])
        for source in sources]
