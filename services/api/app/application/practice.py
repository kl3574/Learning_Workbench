"""Guarded practice commands with frozen deterministic grades and private audit."""

import base64
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import hmac
import secrets
import sqlite3
import time

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..infrastructure.content_repository import damaged, reference
from ..infrastructure.database import Database, utc_now
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.practice_repository import PracticeRecord, PracticeRepository, StoredHelp, StoredSubmission, invalid_snapshot
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..practice_dto import (
    PagePracticeSet, PracticeHint, PracticeHintRequest, PracticeResponsesSaved, PracticeSession,
    PracticeSessionCreate, PracticeSetSummary, PracticeSolution, PracticeSolutionRequest,
    PracticeSubmitted, PracticeSubmitRequest,
)
from .errors import ApiError
from .policy import Policy
from .learning import record_practice_event
from .practice_content import PracticeContent
from .practice_grading import build_audit, grade_practice, persist_audit, validate_audit

HINT_RULE_VERSION = "public-input-guidance-1.0.0"


class PageCursor(dm.StrictModel):
    context: dm.Sha256
    position: dm.Id
    revision: dm.Revision
    expires: int


def invalid() -> ApiError:
    return ApiError(422, "SCHEMA_INVALID", "练习请求、分配题目或分页参数无效。")


def rule_hint(question: dm.QuestionPublic, level: int) -> str:
    """Only public metadata enters these fixed rules; no answer lookup or model call."""
    directions = {
        "single_choice": "逐一检查选项是否满足题干条件；记录排除每个选项的理由，不凭选项位置判断。",
        "text_blank": "先确定空缺处需要的概念或关系，再按题面要求组织简短文本；检查术语与上下文是否一致。",
        "numeric": "先写出所用关系，再代入题目给出的数值；检查单位、符号与所需精度。",
        "expression": "先列出变量、条件域与表达式结构，再逐步变形；避免在未声明的条件下约分或开方。",
        "calculation": "将计算拆成有顺序的小步骤，保留中间量，并检查最后结果是否满足原题条件。",
    }
    if level == 1:
        instructions = question.input_instructions[:2000]
        if len(question.input_instructions) > 2000:
            instructions += "\n（其余输入说明请查看题面原文。）"
        return "规则提示 1：先用自己的话写出已知条件、待求量与计划。\n\n题面输入说明：\n" + instructions
    if level == 2:
        return "规则提示 2：" + directions[question.kind]
    return "规则提示 3：回到原题逐项复核条件、单位和边界，再用代回或独立计算检查自己的结果。\n\n这是基于公开题型的检查清单，不含标准答案，也没有执行自动评分。"


class PracticeService:
    def __init__(self, database: Database):
        self.database = database
        self._cursor_key = secrets.token_bytes(32)

    @contextmanager
    def _access(self, identity: SessionIdentity) -> Iterator[tuple[PracticeContent, PracticeRepository]]:
        try:
            with self.database.transaction() as connection:
                content = PracticeContent(connection, identity.workspace_id)
                content.public.require_workspace()
                guard_subject_access(connection, identity.workspace_id)
                yield content, PracticeRepository(connection, identity.workspace_id)
        except sqlite3.Error:
            raise ApiError(503, "PRACTICE_STORAGE_UNAVAILABLE", "练习存储暂不可用，未确认的本机草稿请保留。", True) from None

    def _cursor(self, context: str, position: str, revision: int) -> str:
        value = canonical_bytes(PageCursor(context=context, position=position, revision=revision, expires=int(time.time()) + 3600))
        return base64.urlsafe_b64encode(value + hmac.new(self._cursor_key, value, hashlib.sha256).digest()).decode().rstrip("=")

    def _position(self, context: str, cursor: str | None) -> tuple[str, int]:
        if cursor is None:
            return "", 0
        try:
            if type(cursor) is not str or not 1 <= len(cursor) <= 1024:
                raise invalid()
            decoded = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
            raw, signature = decoded[:-32], decoded[-32:]
            if not hmac.compare_digest(signature, hmac.new(self._cursor_key, raw, hashlib.sha256).digest()):
                raise invalid()
            value = PageCursor.model_validate(strict_json(raw))
            if value.context != context or value.expires < time.time():
                raise invalid()
            return value.position, value.revision
        except (ValueError, TypeError):
            raise invalid() from None

    def list_sets(self, identity: SessionIdentity, course_id: str | None = None, lesson_id: str | None = None,
                  limit: int = 20, cursor: str | None = None) -> PagePracticeSet:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise invalid()
        try:
            for identifier in (course_id, lesson_id):
                if identifier is not None:
                    TypeAdapter(dm.Id).validate_python(identifier)
        except (ValueError, TypeError):
            raise invalid() from None
        with self._access(identity) as (content, repository):
            lessons = None
            if lesson_id is not None and not isinstance(content.public.current(lesson_id).value, dm.Lesson):
                raise invalid()
            if course_id is not None:
                if not isinstance(content.public.current(course_id).value, dm.Course):
                    raise invalid()
                membership: dict[tuple[str, int, str], dm.ContentRef] = {}
                for row in repository.connection.execute("SELECT revision FROM revisions WHERE object_id=? ORDER BY revision", (course_id,)):
                    course = content.public.load("course", course_id, row["revision"]).value
                    if not isinstance(course, dm.Course):
                        raise damaged()
                    for lesson in course.lesson_refs:
                        if not isinstance(content.exact(lesson), dm.Lesson):
                            raise damaged()
                        membership[(lesson.id, lesson.revision, lesson.sha256)] = lesson
                lessons = canonical_bytes([ref.model_dump(mode="json") for ref in membership.values()]).decode()
            context = sha256_bytes(canonical_bytes([identity.workspace_id, course_id, lesson_id, limit, lessons]))
            position, revision = self._position(context, cursor)
            rows = repository.connection.execute(
                "SELECT r.*,o.kind,o.lifecycle FROM objects o JOIN revisions r ON r.object_id=o.id "
                "WHERE o.workspace_id=? AND o.kind='practice_set' AND o.lifecycle='active' "
                "AND (o.id>? OR (o.id=? AND r.revision>?)) "
                "AND (? IS NULL OR json_extract(r.metadata_json,'$.lesson_ref.id')=?) "
                "AND (? IS NULL OR EXISTS(SELECT 1 FROM json_each(?) member "
                "WHERE json_extract(member.value,'$.id')=json_extract(r.metadata_json,'$.lesson_ref.id') "
                "AND json_extract(member.value,'$.revision')=json_extract(r.metadata_json,'$.lesson_ref.revision') "
                "AND json_extract(member.value,'$.sha256')=json_extract(r.metadata_json,'$.lesson_ref.sha256'))) "
                "ORDER BY o.id,r.revision LIMIT ?", (identity.workspace_id, position, position, revision, lesson_id, lesson_id, lessons, lessons, limit + 1),
            ).fetchall()
            items = []
            for row in rows[:limit]:
                value = content.public.decode(row).value
                practice = content.practice(reference(value))
                questions = content.questions(practice)
                items.append(PracticeSetSummary(ref=reference(practice), title=practice.title, lesson_ref=practice.lesson_ref, question_count=len(questions)))
            return PagePracticeSet(items=items, next_cursor=self._cursor(context, items[-1].ref.id, items[-1].ref.revision) if len(rows) > limit else None)

    @staticmethod
    def _load(content: PracticeContent, repository: PracticeRepository, identifier: str) -> tuple[PracticeRecord, list[dm.QuestionPublic]]:
        record = repository.load(identifier)
        practice = content.practice(record.practice_ref)
        if practice.question_refs != record.question_refs:
            raise invalid_snapshot()
        questions = content.questions(practice)
        repository.exposure_facts(record, questions)
        validate_audit(repository, record, questions)
        return record, questions

    @staticmethod
    def _view(content: PracticeContent, repository: PracticeRepository, record: PracticeRecord, questions: list[dm.QuestionPublic]) -> PracticeSession:
        events, assistance = repository.exposure_facts(record, questions)
        return PracticeSession(id=record.id, revision=record.revision, practice_ref=record.practice_ref,
            lesson_ref=content.practice(record.practice_ref).lesson_ref,
            questions=questions, responses=record.responses, status=record.status, exposure_event_ids=events,
            assisted=bool(events), assistance=assistance, results=record.submission.results if record.submission else None)

    @staticmethod
    def _question(record: PracticeRecord, questions: list[dm.QuestionPublic], question_id: str) -> tuple[dm.ContentRef, dm.QuestionPublic]:
        for ref, question in zip(record.question_refs, questions, strict=True):
            if ref.id == question_id:
                return ref, question
        raise ApiError(422, "QUESTION_NOT_ASSIGNED", "该题目不属于本次练习会话。")

    def create_session(self, identity: SessionIdentity, request: PracticeSessionCreate, key: str | None) -> PracticeSession:
        with self._access(identity) as (content, repository):
            practice = content.practice(request.practice_ref)
            questions = content.questions(practice)

            def operation():
                private_refs = content.freeze_solutions(practice.question_refs)
                identifier = repository.create(request.practice_ref, practice.question_refs, private_refs)
                from .recommendations import inputs_changed
                inputs_changed(repository.connection, identity.workspace_id, 'practice.allocated')
                return self._view(content, repository, repository.load(identifier), questions).model_dump(mode="json")

            result = execute_idempotent(repository.connection, actor=identity.workspace_id, route="POST /practice/sessions",
                key=key, payload=request.model_dump(mode="json"), operation=operation)
            return PracticeSession.model_validate(result)

    def get_session(self, identity: SessionIdentity, id: str) -> PracticeSession:
        with self._access(identity) as (content, repository):
            record, questions = self._load(content, repository, id)
            return self._view(content, repository, record, questions)

    def save_responses(self, identity: SessionIdentity, id: str, request: dm.ResponsesWrite, key: str | None) -> PracticeResponsesSaved:
        with self._access(identity) as (content, repository):
            record, questions = self._load(content, repository, id)
            identifiers = [item.question_id for item in request.responses]
            if len(identifiers) != len(set(identifiers)):
                raise invalid()
            for identifier in identifiers:
                self._question(record, questions, identifier)

            def operation():
                repository.expect(record, request.expected_revision, active=True)
                revision, saved_at = repository.save_responses(record, request.responses)
                return PracticeResponsesSaved(id=id, revision=revision, saved_at=saved_at).model_dump(mode="json")

            result = execute_idempotent(repository.connection, actor=identity.workspace_id, route=f"PUT /practice/sessions/{id}/responses",
                key=key, payload=request.model_dump(mode="json"), operation=operation)
            return PracticeResponsesSaved.model_validate(result)

    def submit(self, identity: SessionIdentity, id: str, request: PracticeSubmitRequest, key: str | None) -> PracticeSubmitted:
        with self._access(identity) as (content, repository):
            record, questions = self._load(content, repository, id)

            def operation():
                repository.expect(record, request.expected_revision, active=True)
                events, assistance = repository.exposure_facts(record, questions)
                entries = grade_practice(content, record, questions)
                results = [entry.result for entry in entries]
                snapshot = StoredSubmission(revision=record.revision + 1, submitted_at=utc_now(), responses=record.responses,
                    results=results, exposure_event_ids=events, assisted=bool(events), assistance=assistance)
                audit = build_audit(identity.workspace_id, record, snapshot, entries)
                record_practice_event(repository.connection, identity.workspace_id, "practice_submitted", record.practice_ref, id)
                outbox_id = repository.submit(record, snapshot, grading_rules_version=audit.grading_rules_version,
                                              grading_audit_sha256=metadata_sha256(audit))
                persist_audit(repository, audit, outbox_id, snapshot.submitted_at)
                return PracticeSubmitted(id=id, revision=snapshot.revision, results=results, evidence_label="practice",
                    exposure_event_ids=events, assisted=bool(events), assistance=assistance).model_dump(mode="json")

            result = execute_idempotent(repository.connection, actor=identity.workspace_id, route=f"POST /practice/sessions/{id}/submit",
                key=key, payload=request.model_dump(mode="json"), operation=operation)
            current, current_questions = self._load(content, repository, id)
            snapshot = current.submission
            if snapshot is None:
                raise invalid_snapshot()
            expected = PracticeSubmitted(id=id, revision=snapshot.revision, results=snapshot.results, evidence_label="practice",
                exposure_event_ids=snapshot.exposure_event_ids, assisted=snapshot.assisted, assistance=snapshot.assistance)
            try:
                if PracticeSubmitted.model_validate(result) != expected:
                    raise invalid_snapshot()
            except (ValueError, TypeError):
                raise invalid_snapshot() from None
            return expected

    def hint(self, identity: SessionIdentity, id: str, request: PracticeHintRequest, key: str | None) -> PracticeHint:
        with self._access(identity) as (content, repository):
            record, questions = self._load(content, repository, id)
            ref, question = self._question(record, questions, request.question_id)
            Policy(repository.connection, identity.workspace_id).check("practice_hint", question_ref=ref)

            def operation():
                repository.expect(record, request.expected_revision)
                previous = repository.help(record, question.id, "hint", request.level)
                if previous:
                    event, help = previous
                    revision = record.revision
                else:
                    help = StoredHelp(markdown=rule_hint(question, request.level), rule_version=HINT_RULE_VERSION, review_status=None)
                    event = record_practice_event(repository.connection, identity.workspace_id, "hint_revealed", ref, id)
                    revision = repository.expose(record, question, ref, "hint", request.level, event, help)
                return PracticeHint(markdown=help.markdown, exposure_event_id=event, revision=revision,
                    level=request.level, rule_version=help.rule_version or HINT_RULE_VERSION, source="rules").model_dump(mode="json")

            result = execute_idempotent(repository.connection, actor=identity.workspace_id, route=f"POST /practice/sessions/{id}/hints",
                key=key, payload=request.model_dump(mode="json"), operation=operation)
            return PracticeHint.model_validate(result)

    def solution(self, identity: SessionIdentity, id: str, request: PracticeSolutionRequest, key: str | None) -> PracticeSolution:
        with self._access(identity) as (content, repository):
            record, questions = self._load(content, repository, id)
            ref, question = self._question(record, questions, request.question_id)
            Policy(repository.connection, identity.workspace_id).check("solution_read", question_ref=ref)
            frozen = next(item for item in record.solution_refs if item.question_ref == ref)

            def operation():
                repository.expect(record, request.expected_revision)
                private = content.solution(frozen)
                previous = repository.help(record, question.id, "solution", 0)
                if previous:
                    event, help = previous
                    if help.markdown != private.solution_markdown or help.review_status != private.review_status:
                        raise invalid_snapshot()
                    revision = record.revision
                else:
                    help = StoredHelp(markdown=private.solution_markdown, rule_version=None, review_status=private.review_status)
                    event = record_practice_event(repository.connection, identity.workspace_id, "solution_revealed", ref, id)
                    revision = repository.expose(record, question, ref, "solution", 0, event, help)
                return PracticeSolution(solution_markdown=help.markdown, exposure_event_id=event,
                    revision=revision, review_status=private.review_status).model_dump(mode="json")

            result = execute_idempotent(repository.connection, actor=identity.workspace_id, route=f"POST /practice/sessions/{id}/solutions",
                key=key, payload=request.model_dump(mode="json"), operation=operation)
            return PracticeSolution.model_validate(result)
