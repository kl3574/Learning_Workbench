"""Exact public question reads and private, frozen solution lookup for Practice."""

import sqlite3

from pydantic import model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256, strict_json

from ..infrastructure.content_repository import ContentRepository, damaged, reference
from ..infrastructure.security import guard_subject_access
from .errors import ApiError


class FrozenSolution(dm.StrictModel):
    question_ref: dm.ContentRef
    solution_revision: dm.Revision | None
    sha256: dm.Sha256 | None

    @model_validator(mode="after")
    def consistent(self):
        if self.question_ref.entity != "question" or (self.solution_revision is None) != (self.sha256 is None):
            raise ValueError("invalid frozen solution reference")
        return self


class PracticeContent:
    """This internal port never returns a private model to generic content routes."""

    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id
        self.public = ContentRepository(connection, workspace_id)

    def exact(self, ref: dm.ContentRef):
        guard_subject_access(self.connection, self.workspace_id)
        value = self.public.load(ref.entity, ref.id, ref.revision).value
        if reference(value) != ref:
            raise ApiError(422, "REFERENCE_HASH_MISMATCH", "引用哈希与指定修订不一致。")
        return value

    def practice(self, ref: dm.ContentRef) -> dm.PracticeSet:
        value = self.exact(ref)
        if not isinstance(value, dm.PracticeSet):
            raise ApiError(422, "PRACTICE_REFERENCE_INVALID", "练习会话必须引用准确的题集修订。")
        if value.lesson_ref.entity != "lesson" or not isinstance(self.exact(value.lesson_ref), dm.Lesson):
            raise damaged()
        return value

    def questions(self, practice: dm.PracticeSet) -> list[dm.QuestionPublic]:
        questions = []
        ids: set[str] = set()
        for ref in practice.question_refs:
            value = self.exact(ref)
            if not isinstance(value, dm.QuestionPublic) or value.id in ids:
                raise damaged()
            ids.add(value.id)
            questions.append(value)
        return questions

    def _decode_solution(self, row: sqlite3.Row, question: dm.ContentRef) -> dm.SolutionPrivate:
        try:
            solution = dm.SolutionPrivate.model_validate(strict_json(row["private_json"]))
            if (solution.question_ref != question or solution.revision != row["solution_revision"]
                    or metadata_sha256(solution) != row["sha256"] or solution.review_status != row["review_status"]):
                raise damaged()
            return solution
        except (ValueError, TypeError, KeyError):
            raise damaged() from None

    def freeze_solutions(self, questions: list[dm.ContentRef]) -> list[FrozenSolution]:
        result = []
        for question in questions:
            if not isinstance(self.exact(question), dm.QuestionPublic):
                raise damaged()
            row = self.connection.execute(
                "SELECT s.* FROM solutions s JOIN objects o ON o.id=s.question_id "
                "WHERE o.workspace_id=? AND o.kind='question' AND s.question_id=? AND s.question_revision=? "
                "ORDER BY s.solution_revision DESC LIMIT 1", (self.workspace_id, question.id, question.revision),
            ).fetchone()
            if row is None:
                result.append(FrozenSolution(question_ref=question, solution_revision=None, sha256=None))
            else:
                self._decode_solution(row, question)
                result.append(FrozenSolution(question_ref=question, solution_revision=row["solution_revision"], sha256=row["sha256"]))
        return result

    def solution(self, frozen: FrozenSolution) -> dm.SolutionPrivate:
        if not isinstance(self.exact(frozen.question_ref), dm.QuestionPublic):
            raise damaged()
        if frozen.solution_revision is None:
            raise ApiError(409, "SOLUTION_UNAVAILABLE", "创建本次练习时没有可用解答；此会话不会改用后来发布的答案。")
        row = self.connection.execute(
            "SELECT s.* FROM solutions s JOIN objects o ON o.id=s.question_id "
            "WHERE o.workspace_id=? AND o.kind='question' AND s.question_id=? AND s.question_revision=? AND s.solution_revision=?",
            (self.workspace_id, frozen.question_ref.id, frozen.question_ref.revision, frozen.solution_revision),
        ).fetchone()
        if row is None or row["sha256"] != frozen.sha256:
            raise damaged()
        return self._decode_solution(row, frozen.question_ref)
