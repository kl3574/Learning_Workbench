"""Workspace assessment policy checked before access and idempotent replay."""

import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm

from .assessment_access import AssessmentAccess, AttemptAccess
from .assessment_content import question_exposure_group
from .errors import ApiError
from .jobs import active_subject_work

Action = Literal['subject_read', 'attempt_read', 'attempt_write', 'practice_hint', 'solution_read', 'private_artifact']


def active_error() -> ApiError:
    return ApiError(409, 'ASSESSMENT_ACTIVE', '独立测试进行中，此操作暂不可用。')


def protected_error() -> ApiError:
    return ApiError(409, 'ASSESSMENT_ANSWER_PROTECTED', '相关测验的帮助或解答仍受策略保护；提交及必要评分完成前暂不可读取。')


class Policy:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id
        self.assessments = AssessmentAccess(connection, workspace_id)

    def check(self, action: Action, attempt_id: str | None = None, question_ref: dm.ContentRef | None = None) -> None:
        active = self.assessments.active_independent()
        if active is not None:
            if action not in {'attempt_read', 'attempt_write'} or active != attempt_id:
                raise active_error()
        if action in {'attempt_read', 'attempt_write'}:
            if attempt_id is None:
                raise ApiError(422, 'ATTEMPT_REFERENCE_REQUIRED', '此操作需要明确的测验作答。')
            self.assessments.load(attempt_id)
            return
        if action == 'subject_read':
            return
        if action not in {'practice_hint', 'solution_read', 'private_artifact'}:
            raise ApiError(403, 'POLICY_DENIED', '未声明的操作不能越过测验策略。')
        candidates = self.assessments.protected()
        if action == 'practice_hint':
            candidates = tuple(item for item in candidates if item.policy.mode != 'assisted')
        if not candidates:
            return
        # An opaque private original cannot establish that its hidden bytes do
        # not disclose a protected answer. Its safe public derivative stays readable.
        if action == 'private_artifact' or question_ref is None:
            raise protected_error()
        group = question_exposure_group(self.connection, self.workspace_id, question_ref)
        for item in candidates:
            for assigned in item.question_refs:
                if assigned == question_ref or question_exposure_group(self.connection, self.workspace_id, assigned) == group:
                    raise protected_error()

    def start_exclusion(self, mode: Literal['independent', 'assisted', 'open_book']) -> None:
        if not self.connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '测验开始排他检查需要有效事务。')
        if self.assessments.active_independent() is not None:
            raise active_error()
        if mode == 'independent' and active_subject_work(self.connection, self.workspace_id):
            raise ApiError(409, 'SUBJECT_WORK_ACTIVE', '仍有进行中、排队中或待批准的学科任务，请先结束或取消任务。')


def guard_attempt_access(connection: sqlite3.Connection, workspace_id: str, attempt_id: str, *,
                         assessment_ref: dm.ContentRef | None = None) -> AttemptAccess:
    policy = Policy(connection, workspace_id)
    policy.check('attempt_read', attempt_id=attempt_id)
    access = policy.assessments.load(attempt_id)
    if assessment_ref is not None and access.assessment_ref != assessment_ref:
        raise ApiError(409, 'ASSESSMENT_REFERENCE_MISMATCH', '事件必须绑定本次作答冻结的测验修订。')
    return access
