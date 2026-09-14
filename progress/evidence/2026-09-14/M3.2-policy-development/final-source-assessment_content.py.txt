"""Content-owned, exact assessment assignments; private pins stay inside the server."""

from collections.abc import Sequence
from dataclasses import dataclass
import sqlite3
from typing import Literal

from pydantic import model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256, strict_json
from packages.contracts.validation import PublishedModel

from ..infrastructure.content_repository import ContentRepository, damaged, reference
from .errors import ApiError

ReviewStatus = Literal["approved", "draft", "needs_review", "missing", "damaged"]


class FrozenAnswer(dm.StrictModel):
    question_ref: dm.ContentRef
    solution_revision: dm.Revision
    sha256: dm.Sha256
    review_status: Literal["approved", "draft", "needs_review"]

    @model_validator(mode="after")
    def question_entity(self):
        if self.question_ref.entity != "question":
            raise ValueError("private pin must bind an exact question")
        return self


@dataclass(frozen=True)
class Assignment:
    questions: tuple[dm.QuestionPublic, ...]
    private_pins: tuple[FrozenAnswer, ...]
    concept_refs: tuple[dm.ContentRef, ...]


@dataclass(frozen=True)
class ContentPreflight:
    startable: bool
    reason_codes: tuple[str, ...]
    review_statuses: tuple[ReviewStatus, ...]
    question_kinds: tuple[str, ...]
    concept_refs: tuple[dm.ContentRef, ...]


class AssessmentContent:
    """Trusted Content facts port. The caller checks Policy before invoking it.

    It deliberately does not invoke the global academic guard: an already active
    independent attempt must still read its own frozen public assignment.
    """

    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id
        self.public = ContentRepository(connection, workspace_id)

    def exact(self, ref: dm.ContentRef) -> PublishedModel:
        value = self.public.load(ref.entity, ref.id, ref.revision).value
        if reference(value) != ref:
            raise ApiError(422, "REFERENCE_HASH_MISMATCH", "引用哈希与指定修订不一致。")
        return value

    def blueprint(self, ref: dm.ContentRef) -> dm.AssessmentBlueprint:
        value = self.exact(ref)
        if not isinstance(value, dm.AssessmentBlueprint):
            raise ApiError(422, "ASSESSMENT_REFERENCE_INVALID", "测验必须引用准确的测验修订。")
        return value

    def catalog(self) -> tuple[dm.AssessmentBlueprint, ...]:
        rows = self.connection.execute(
            "SELECT r.*,o.kind,o.lifecycle FROM revisions r JOIN objects o ON o.id=r.object_id "
            "WHERE o.workspace_id=? AND o.kind='assessment' AND o.lifecycle='active' ORDER BY o.id,r.revision",
            (self.workspace_id,),
        )
        output = []
        for row in rows:
            value = self.public.decode(row).value
            if not isinstance(value, dm.AssessmentBlueprint):
                raise damaged()
            output.append(value)
        return tuple(output)

    def questions(self, blueprint: dm.AssessmentBlueprint) -> tuple[dm.QuestionPublic, ...]:
        output = []
        identifiers: set[str] = set()
        for ref in blueprint.question_refs:
            value = self.exact(ref)
            if not isinstance(value, dm.QuestionPublic) or value.id in identifiers:
                raise damaged()
            identifiers.add(value.id)
            output.append(value)
        return tuple(output)

    def concepts(self, questions: Sequence[dm.QuestionPublic]) -> tuple[dm.ContentRef, ...]:
        output: dict[tuple[str, int, str], dm.ContentRef] = {}
        for question in questions:
            for identifier in question.concept_ids:
                ref = reference(self.public.concept_dependency(question, identifier))
                output[(ref.id, ref.revision, ref.sha256)] = ref
        return tuple(output[key] for key in sorted(output))

    def course_witnesses(self, concept_refs: Sequence[dm.ContentRef], course_id: str | None = None) -> tuple[dm.ContentRef, ...]:
        required = {(ref.entity, ref.id, ref.revision, ref.sha256) for ref in concept_refs}
        if not required or any(ref.entity != "concept" for ref in concept_refs):
            raise damaged()
        for ref in concept_refs:
            if not isinstance(self.exact(ref), dm.Concept):
                raise damaged()
        rows = self.connection.execute(
            "SELECT r.*,o.kind,o.lifecycle FROM revisions r JOIN objects o ON o.id=r.object_id "
            "WHERE o.workspace_id=? AND o.kind='course' AND (? IS NULL OR o.id=?) ORDER BY o.id,r.revision",
            (self.workspace_id, course_id, course_id),
        )
        output = []
        for row in rows:
            course = self.public.decode(row).value
            if not isinstance(course, dm.Course):
                raise damaged()
            # One exact historical course must contain the entire dependency set.
            available = {(ref.entity, ref.id, ref.revision, ref.sha256) for ref in course.concept_refs}
            if required <= available:
                for ref in course.concept_refs:
                    if not isinstance(self.exact(ref), dm.Concept):
                        raise damaged()
                output.append(reference(course))
        return tuple(output)

    def _decode_answer(self, row: sqlite3.Row, ref: dm.ContentRef) -> dm.SolutionPrivate:
        try:
            answer = dm.SolutionPrivate.model_validate(strict_json(row["private_json"]))
            if (answer.question_ref != ref or answer.revision != row["solution_revision"]
                    or metadata_sha256(answer) != row["sha256"] or answer.review_status != row["review_status"]):
                raise damaged()
            question = self.exact(ref)
            if not isinstance(question, dm.QuestionPublic):
                raise damaged()
            # M3.2 freezes an answer, it does not declare a grading algorithm
            # compatible or reviewed. The strict shared model permits several
            # review paths; actual grading compatibility belongs to M3.3.
            return answer
        except (ValueError, TypeError, KeyError):
            raise damaged() from None

    def _latest(self, ref: dm.ContentRef) -> tuple[FrozenAnswer, dm.SolutionPrivate] | None:
        row = self.connection.execute(
            "SELECT s.* FROM solutions s JOIN objects o ON o.id=s.question_id "
            "WHERE o.workspace_id=? AND o.kind='question' AND s.question_id=? AND s.question_revision=? "
            "ORDER BY s.solution_revision DESC LIMIT 1", (self.workspace_id, ref.id, ref.revision),
        ).fetchone()
        if row is None:
            return None
        answer = self._decode_answer(row, ref)
        return FrozenAnswer(question_ref=ref, solution_revision=answer.revision, sha256=row["sha256"], review_status=answer.review_status), answer

    def preflight(self, blueprint: dm.AssessmentBlueprint) -> ContentPreflight:
        questions = self.questions(blueprint)
        concepts = self.concepts(questions)
        statuses: list[ReviewStatus] = []
        for question in questions:
            try:
                latest = self._latest(reference(question))
                statuses.append(latest[0].review_status if latest else "missing")
            except ApiError:
                statuses.append("damaged")
        reasons = tuple(code for state, code in (("missing", "answer_missing"), ("damaged", "answer_damaged")) if state in statuses)
        return ContentPreflight(not reasons, reasons, tuple(statuses), tuple(question.kind for question in questions), concepts)

    def question_bundle(self, blueprint: dm.AssessmentBlueprint) -> Assignment:
        questions = self.questions(blueprint)
        pins = []
        for question in questions:
            latest = self._latest(reference(question))
            if latest is None:
                raise ApiError(409, "ASSESSMENT_ANSWER_UNAVAILABLE", "测验缺少绑定此题目修订的私有解答，无法冻结作答。")
            pins.append(latest[0])
        return Assignment(questions, tuple(pins), self.concepts(questions))

    def solution(self, pin: FrozenAnswer) -> dm.SolutionPrivate:
        row = self.connection.execute(
            "SELECT s.* FROM solutions s JOIN objects o ON o.id=s.question_id "
            "WHERE o.workspace_id=? AND o.kind='question' AND s.question_id=? AND s.question_revision=? AND s.solution_revision=?",
            (self.workspace_id, pin.question_ref.id, pin.question_ref.revision, pin.solution_revision),
        ).fetchone()
        if row is None or row["sha256"] != pin.sha256 or row["review_status"] != pin.review_status:
            raise damaged()
        return self._decode_answer(row, pin.question_ref)


def validate_assessment_reference(connection: sqlite3.Connection, workspace_id: str, ref: dm.ContentRef) -> dm.AssessmentBlueprint:
    return AssessmentContent(connection, workspace_id).blueprint(ref)


def question_exposure_group(connection: sqlite3.Connection, workspace_id: str, ref: dm.ContentRef) -> str:
    question = AssessmentContent(connection, workspace_id).exact(ref)
    if not isinstance(question, dm.QuestionPublic):
        raise damaged()
    return question.exposure_group
