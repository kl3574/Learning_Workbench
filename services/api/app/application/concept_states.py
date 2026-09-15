"""Read-only learning projection composed through the modules' checked ports."""

from collections import defaultdict
import sqlite3
from typing import TypeAlias

from pydantic import ValidationError

from packages.contracts import domain_models as dm

from ..concept_state_dto import ConceptState, ConceptStateResponse, ConceptStateSource
from ..infrastructure.content_repository import ContentRepository
from ..infrastructure.database import Database
from ..infrastructure.security import guard_subject_access
from .concept_state_rules import derive_concept_state, observation_order
from .content_learning_access import evidence_applicability, learning_scope, participation_in_scope
from .eligibility_models import Skill
from .errors import ApiError
from .evidence import latest_checked_observations
from .learning_state_models import EvidenceApplicability, PracticeHelpActivity, SubmissionActivity
from .practice_activity_access import practice_participation
from .profile import read_profile
from .question_qualification import QuestionQualificationFacts, question_qualification_facts

RefKey: TypeAlias = tuple[str, str, int, str]
RowKey: TypeAlias = tuple[RefKey, Skill]
SKILLS: tuple[Skill, ...] = ('recall', 'explain', 'compute', 'derive', 'transfer')


def ref_key(ref: dm.ContentRef) -> RefKey:
    return ref.entity, ref.id, ref.revision, ref.sha256


def read_concept_states(connection: sqlite3.Connection, workspace_id: str,
                        course_id: str | None = None) -> ConceptStateResponse:
    """Public Learning query inside the caller's transaction, with no default writes."""
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '学习状态读取需要同一事务的来源快照。')
    guard_subject_access(connection, workspace_id)
    ContentRepository(connection, workspace_id).require_workspace()
    try:
        return ConceptStateService._read(connection, workspace_id, course_id)
    except (ValidationError, ValueError, TypeError):
        raise ApiError(409, 'LEARNING_STATE_INVALID', '学习状态来源或计数完整性校验失败。') from None


class ConceptStateService:
    def __init__(self, database: Database):
        self.database = database

    def read(self, workspace_id: str, course_id: str | None = None) -> ConceptStateResponse:
        try:
            with self.database.transaction() as connection:
                guard_subject_access(connection, workspace_id)
                ContentRepository(connection, workspace_id).require_workspace()
                return self._read(connection, workspace_id, course_id)
        except sqlite3.Error:
            raise ApiError(503, 'LEARNING_STATE_UNAVAILABLE', '学习状态暂时无法读取。', True) from None
        except (ValidationError, ValueError, TypeError):
            raise ApiError(409, 'LEARNING_STATE_INVALID', '学习状态来源或计数完整性校验失败。') from None

    @staticmethod
    def _read(connection: sqlite3.Connection, workspace_id: str, course_id: str | None) -> ConceptStateResponse:
        scope = learning_scope(connection, workspace_id, course_id)
        profile = read_profile(connection, workspace_id)
        concepts = {ref_key(item.ref): item for item in scope.concepts}
        skills = {key: set(item.skill_dimensions) for key, item in concepts.items()}
        membership: dict[RefKey, bool] = {}

        def included(target: dm.ContentRef) -> bool:
            key = ref_key(target)
            if course_id is None:
                return True
            if key not in membership:
                membership[key] = participation_in_scope(connection, workspace_id, target, scope.course_refs)
            return membership[key]

        # Validate the full successful history before the user's course/skill filters.
        observations = latest_checked_observations(connection, workspace_id)
        evidence: dict[RowKey, list[ConceptStateSource]] = defaultdict(list)
        applicability: dict[tuple[RefKey, RefKey], EvidenceApplicability] = {}
        for observation in observations:
            concept_key = ref_key(observation.concept_ref)
            if concept_key not in concepts or not included(observation.assessment_ref):
                continue
            key = (ref_key(observation.question_ref), concept_key)
            if key not in applicability:
                applicability[key] = evidence_applicability(connection, workspace_id,
                    observation.question_ref, observation.concept_ref)
            source = ConceptStateSource(**observation.model_dump(mode='json'), applicability=applicability[key])
            evidence[concept_key, source.evidence.skill].append(source)
            skills[concept_key].add(source.evidence.skill)

        participation = practice_participation(connection, workspace_id)
        facts: dict[RefKey, QuestionQualificationFacts] = {}

        def rows_for(question: dm.ContentRef) -> list[RowKey]:
            key = ref_key(question)
            if key not in facts:
                facts[key] = question_qualification_facts(connection, workspace_id, question)
            value = facts[key]
            if not value.mapping_valid:
                return []  # No partial or guessed per-concept participation.
            return [(ref_key(ref), value.skill) for ref in value.concept_refs if ref_key(ref) in concepts]

        submissions: dict[RowKey, dict[str, SubmissionActivity]] = defaultdict(dict)
        hints: dict[RowKey, dict[str, PracticeHelpActivity]] = defaultdict(dict)
        solutions: dict[RowKey, dict[str, PracticeHelpActivity]] = defaultdict(dict)
        for submission in participation.submissions:
            if not included(submission.target_ref):
                continue
            for question in submission.question_refs:
                for row_key in rows_for(question):
                    submissions[row_key][submission.source_id] = submission
                    skills[row_key[0]].add(row_key[1])
        for help_event in participation.help:
            if not included(help_event.practice_set_ref):
                continue
            for row_key in rows_for(help_event.question_ref):
                target = hints if help_event.kind == 'hint_revealed' else solutions
                target[row_key][help_event.event_id] = help_event
                skills[row_key[0]].add(row_key[1])

        self_reports = {item.concept_id: item for item in profile.self_assessments}
        items = []
        for concept_key, concept in concepts.items():
            for skill in SKILLS:
                if skill not in skills[concept_key]:
                    continue
                row_key = concept_key, skill
                sources = sorted(evidence[row_key], key=observation_order, reverse=True)
                decision = derive_concept_state(sources)
                submitted = sorted(submissions[row_key].values(), key=lambda value: (value.submitted_at, value.source_id), reverse=True)
                revealed_hints = sorted(hints[row_key].values(), key=lambda value: (value.occurred_at, value.event_id), reverse=True)
                revealed_solutions = sorted(solutions[row_key].values(), key=lambda value: (value.occurred_at, value.event_id), reverse=True)
                items.append(ConceptState(concept_id=concept.ref.id, concept_ref=concept.ref, title=concept.title, skill=skill,
                    **decision.model_dump(mode='json'), self_report=self_reports.get(concept.ref.id),
                    evidence_ids=[source.evidence.id for source in sources], sources=sources,
                    practice_submission_count=len(submitted), hint_count=len(revealed_hints), solution_count=len(revealed_solutions),
                    practice_submission_sources=submitted, hint_sources=revealed_hints, solution_sources=revealed_solutions))
        return ConceptStateResponse(items=items, course_refs=scope.course_refs, concepts=scope.concepts)
