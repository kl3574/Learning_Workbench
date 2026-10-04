"""Single owned memory-operation consumption; no HTTP execution entry point."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from .codex_operation_profile import CodexOperationRegistry
if TYPE_CHECKING:
    from .codex_turn import CodexTurnService
    from ..infrastructure.database import Database

from ..infrastructure.consent_repository import instant
from ..infrastructure.database import utc_now
from ..serialization import content_sha256
from .codex_operation_models import SupportedOperation, OperationStarted, OperationFinished
from .codex_operation_profile import LiteralOperationResult
from .errors import ApiError


class CodexOperationExecution(ABC):
    turns: "CodexTurnService"
    database: "Database"
    operations: CodexOperationRegistry

    @abstractmethod
    def verify_history(self, conn, workspace, history): ...

    @abstractmethod
    def _append(self, conn, workspace, history, state, event, now): ...

    def admit_operation(self, conn, workspace, state, states, history):
        operation = state.operation
        if not isinstance(operation, SupportedOperation):
            raise ApiError(409, 'CODEX_OPERATION_UNSUPPORTED', '原操作没有受检执行闭包。')
        session, turn = self.turns._find(history, operation.turn_id)
        if state.closed or state.started or state.status == 'declined':
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原操作已经关闭或消费。')
        if (session.active_turn_id != operation.turn_id or turn.control.execution != 'active'
                or turn.control.cancel_requested):
            raise ApiError(409, 'CODEX_CANCELLED', '原任务已不再允许工具执行。')
        if instant(utc_now()) >= instant(operation.expires_at):
            raise ApiError(409, 'CODEX_TIMEOUT', '原工具期限已过。')
        if not self.operations.available(operation.closure.profile):
            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '原内存操作解释器不可用。')
        if self.turns.outbound_owner is None:
            raise ApiError(409, 'CODEX_HISTORY_DAMAGED', '原外发 owner 不可用。')
        provider, _, _ = self.turns.outbound_owner.admit_execution(conn, workspace, operation.turn_id, already_started=True)
        if provider.started is None or provider.started.execution_owner_id != operation.execution_owner_id or provider.started.lease != operation.lease:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原操作执行实例不匹配。')
        self.turns.verify_dispatch_lease(conn, workspace, operation.job_id, operation.lease)
        used = sum(item.started is not None for item in states.values() if item.operation.turn_id == operation.turn_id)
        if used >= operation.tools.max_tool_calls:
            raise ApiError(409, 'CODEX_BUDGET_EXCEEDED', '原任务工具额度已消费。')
        return used + 1

    def execute_owned_operation(self, workspace, turn_id, owner, identifier):
        # Private live-worker callback context is checked by the caller. Claim
        # commits before the interpreter. A crash here can never justify replay.
        with self.database.transaction() as conn:
            _, _, history = self.turns._owned_state(conn, workspace)
            states = self.verify_history(conn, workspace, history)
            state = states.get(identifier)
            if state is None or state.operation.turn_id != turn_id or state.operation.execution_owner_id != owner:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '操作不属于原回调实例。')
            if state.finished is not None:
                if state.finished.result is not None:
                    return state.finished.result
                raise ApiError(409, 'CODEX_OUTCOME_UNKNOWN', '原操作没有可重放的完成结果。')
            if state.started is not None:
                raise ApiError(409, 'CODEX_OUTCOME_UNKNOWN', '原操作已有开始事实，不能再执行。')
            if state.decided is None or state.status != 'approved':
                raise ApiError(409, 'CODEX_BINDING_INVALID', '原操作尚未批准。')
            ordinal = self.admit_operation(conn, workspace, state, states, history)
            operation = state.operation
            now = utc_now()
            if instant(now) >= instant(operation.expires_at):
                raise ApiError(409, 'CODEX_TIMEOUT', '原工具期限已过。')
            self._append(conn, workspace, history, state, OperationStarted(kind='started',
                execution_owner_id=owner, lease=operation.lease,
                operation_sha256=content_sha256(operation), budget_ordinal=ordinal), now)
            _, _, checked = self.turns._owned_state(conn, workspace)
            self.verify_history(conn, workspace, checked)
        try:
            result = self.operations.execute(operation.closure, content_sha256(operation))
            result = LiteralOperationResult.model_validate(result.model_dump(mode='json'))
            if result.operation_sha256 != content_sha256(operation) or result.text != operation.closure.command.text:
                raise ValueError('Invalid interpreter receipt')
            event = OperationFinished(kind='finished', outcome='completed', result=result, error_code=None)
        except Exception:
            # No checked receipt, including crash-adjacent adapter errors. The
            # debit remains and the original operation is never re-executed.
            event = OperationFinished(kind='finished', outcome='unknown', result=None, error_code='CODEX_OUTCOME_UNKNOWN')
        self.record_operation_outcome(workspace, turn_id, owner, identifier, event)
        if event.result is None:
            raise ApiError(409, 'CODEX_OUTCOME_UNKNOWN', '原操作结果未知。')
        return event.result

    def record_operation_outcome(self, workspace, turn_id, owner, identifier, event):
        # Integrity-only original-owner receipt port, not a new permission. Late
        # true facts survive logout, revocation and Policy changes.
        with self.database.transaction() as conn:
            _, _, history = self.turns._owned_state(conn, workspace)
            state = self.verify_history(conn, workspace, history).get(identifier)
            if state is None or state.operation.turn_id != turn_id or state.operation.execution_owner_id != owner or state.started is None:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '结果没有原开始许可。')
            if state.finished is not None:
                if state.finished != event:
                    raise ApiError(409, 'CODEX_BINDING_INVALID', '原结果不可更换。')
                return
            self._append(conn, workspace, history, state, event, utc_now())
            _, _, checked = self.turns._owned_state(conn, workspace)
            self.verify_history(conn, workspace, checked)
