"""Real unsupported-operation owner. There is no production execution registry.

This intake preserves strictly bound synthetic protocol callbacks and permits
only decline. A request description is never an executable operation proof.
"""
from datetime import timedelta, timezone
from uuid import uuid4
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json, sha256_bytes
from ..codex_turn_dto import CodexDeniedOperation, GenericApprovalView, GenericApprovalDecisionAck
from ..import_dto import JobCancelRequest
from ..infrastructure.codex_approval_repository import CodexApprovalRepository, CheckedApproval
from ..infrastructure.consent_repository import instant
from ..infrastructure.database import utc_now
from ..serialization import content_sha256, canonical_json
from .codex_approval_models import (
    ApprovalOperation, ApprovalCreated, ApprovalClosed, ApprovalDecided, ApprovalCommand, SyntheticOperationCallback,
)
from .codex_bootstrap_access import current_control_access
from .codex_turn import missing
from .codex_turn_context import damaged
from .errors import ApiError
from .providers import validate_key


class CodexApprovalsService:
    def __init__(self, turns):
        self.turns, self.database = turns, turns.database

    def verify_history(self, conn, workspace, history):
        if self.turns.outbound_owner is None:
            raise damaged()
        provider, _ = self.turns.outbound_owner.owned_states(conn, workspace)
        bootstrap = self.turns.bootstrap.checked_owned_sessions(conn, workspace)
        return CodexApprovalRepository(conn, workspace).checked(history, provider, bootstrap)

    @staticmethod
    def control(state: CheckedApproval, turn):
        value = state.control
        validity = value.validity
        if validity != 'closed':
            if turn.control.execution == 'terminal' or turn.control.cancel_requested:
                validity = 'closed'
            elif instant(utc_now()) >= instant(state.operation.expires_at):
                validity = 'expired'
        return value.model_copy(update={'validity': validity})

    def read_pending_operation(self, conn, identity, identifier):
        current, _, _, history = self.turns._state(conn, identity, subject=True)
        states = self.verify_history(conn, current.workspace_id, history)
        state = states.get(identifier)
        if state is None:
            raise missing()
        _, turn = self.turns._find(history, state.operation.turn_id)
        operation = state.operation
        return GenericApprovalView(id=identifier, revision=state.revision, actor_session_id=operation.actor_session_id,
            session_id=operation.session_id, turn_id=operation.turn_id, run_id=operation.job_id,
            job=turn.control.job, job_revision=turn.control.job_revision, operation=operation.operation,
            operation_sha256=content_sha256(operation), created_at=operation.created_at, expires_at=operation.expires_at,
            decision=state.control.decision, validity=self.control(state, turn).validity, execution='not_started',
            decided_at=state.events[1].occurred_at if state.decided else None,
            started_at=None, finished_at=None, result_sha256=None,
            error_code=state.closed.reason if state.closed else None)

    def read(self, identity, identifier):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            value = self.read_pending_operation(conn, identity, identifier)
        return self.turns._deliver(identity, value, subject=True)

    def decide(self, identity, identifier, body, key):
        key = validate_key(key)
        body = dm.ApprovalDecision.model_validate(body.model_dump())
        with self.database.transaction() as conn:
            value = self.decide_once(conn, identity, identifier, body, key)
        return self.turns._deliver(identity, value, subject=body.decision == 'approve_once')

    def decide_once(self, conn, identity, identifier, body, key):
        current, _, _, history = self.turns._state(conn, identity, subject=body.decision == 'approve_once')
        states = self.verify_history(conn, current.workspace_id, history)
        state = states.get(identifier)
        if state is None:
            raise missing()
        command = state.decided.command if state.decided else None
        if command is not None and (command.actor_session_id, command.key) == (current.id, key):
            if canonical_json(command.body) != canonical_json(body):
                raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原决定命令不能更换完整输入。')
            return command.ack
        if body.expected_revision != state.revision:
            raise ApiError(412, 'REVISION_MISMATCH', '审批修订已改变。')
        if body.operation_sha256 != content_sha256(state.operation):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '决定必须绑定原完整操作。')
        if body.decision == 'approve_once':
            if current.id != state.operation.actor_session_id:
                raise ApiError(403, 'POLICY_DENIED', '新操作者不能接管原操作批准。')
            raise ApiError(409, 'CODEX_OPERATION_UNSUPPORTED', '该回调缺少可核的完整执行闭包，只能拒绝。')
        if state.decided is not None or state.closed is not None:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原操作已经决定或关闭。')
        session, turn = self.turns._find(history, state.operation.turn_id)
        if turn.control.execution != 'active' or session.active_turn_id != turn.control.id:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原操作已不在活跃任务中。')
        ack = GenericApprovalDecisionAck(id=identifier, revision=2, actor_session_id=current.id,
            operation_sha256=body.operation_sha256, decision='decline', applied=True,
            session_id=state.operation.session_id, turn_id=state.operation.turn_id,
            run_id=state.operation.job_id, job=turn.control.job)
        event = ApprovalDecided(kind='decided', command=ApprovalCommand(actor_session_id=current.id,
            key=key, body=body, ack=ack))
        self._append(conn, current.workspace_id, history, state, event, utc_now())
        # The ordinary Jobs owner records a request; this does not claim a
        # remote cancellation or tool completion. The worker owns convergence.
        self.turns.request_stop(conn, current, turn.control.job.id,
            JobCancelRequest(expected_revision=turn.control.job_revision), 'approval-stop-'+identifier)
        self.turns._state(conn, current)
        current_control_access(conn, current, write=False)
        return ack

    def receive(self, workspace, turn_id, owner, raw):
        """Only the live worker's registered synthetic callback adapter calls this.

        No HTTP caller can create an operation or supply a profile/operation hash.
        The current version creates denied operations only.
        """
        if not isinstance(raw, bytes) or len(raw) > 131072:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '回调格式不符合固定协议。')
        try:
            text = raw.decode('utf-8')
            callback = SyntheticOperationCallback.model_validate(strict_json(text))
        except (ValueError, TypeError, RecursionError):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '回调格式不符合固定协议。') from None
        with self.database.transaction() as conn:
            bootstrap, _, history = self.turns._owned_state(conn, workspace)
            states = self.verify_history(conn, workspace, history)
            session, turn = self.turns._find(history, turn_id)
            if self.turns.outbound_owner is None:
                raise damaged()
            # A received original callback is a private historical read, not a
            # new dispatch. Decline, actor loss or expiry cannot erase it. The
            # worker still requires this exact live owner and calling thread.
            for state in states.values():
                if (state.operation.execution_owner_id, state.operation.callback.rpc_id) == (owner, callback.rpc_id):
                    if state.operation.turn_id != turn_id or state.operation.callback_json != text:
                        raise ApiError(409, 'CODEX_BINDING_INVALID', '原回调不能替换。')
                    return state.operation.approval_id
            provider, _, _ = self.turns.outbound_owner.admit_execution(conn, workspace, turn_id, already_started=True)
            original = bootstrap[session.anchor.session_id]
            if (provider.started is None or provider.started.execution_owner_id != owner or provider.queued is None
                    or original.finished is None or callback.thread_id != original.finished.outcome.thread_id
                    or callback.turn_id != turn_id or turn.control.cancel_requested
                    or turn.control.execution != 'active' or session.active_turn_id != turn_id):
                raise ApiError(409, 'CODEX_BINDING_INVALID', '回调不属于当前受检执行实例。')
            self.turns.verify_dispatch_lease(conn, workspace, turn.control.job.id, provider.started.lease)
            if len(turn.control.approval_ids) >= 64:
                raise ApiError(409, 'CODEX_OPERATION_UNSUPPORTED', '当前任务审批对象已达到上限。')
            now = utc_now()
            expiry = min(instant(provider.proposed.command.ack.summary.expires_at),
                instant(provider.started_at) + timedelta(seconds=turn.prepared.input.request.tools.wall_seconds))
            if instant(now) >= expiry:
                raise ApiError(409, 'CODEX_TIMEOUT', '原任务期限已过。')
            category: Literal['network', 'unbound_operation'] = 'network' if callback.method == 'network/requestApproval' else 'unbound_operation'
            operation = ApprovalOperation(version='codex-unsupported-operation-v1', workspace_id=workspace,
                approval_id='approval_'+uuid4().hex, actor_session_id=session.anchor.actor_session_id,
                session_id=session.anchor.session_id, turn_id=turn_id, job_id=turn.control.job.id,
                job_input_sha256=turn.prepared.command.ack.summary.job_input_sha256,
                dispatch_id=provider.queued.dispatch_id, execution_owner_id=owner, lease=provider.started.lease,
                profile_sha256=turn.prepared.command.ack.summary.runtime.profile_sha256,
                input_proof_sha256=provider.proposed.command.ack.summary.input_token_assurance.proof_sha256,
                request_sha256=provider.started.request_body_sha256,
                callback_json=text, callback_sha256=sha256_bytes(raw), callback=callback,
                tools=turn.prepared.input.request.tools,
                operation=CodexDeniedOperation(kind='unsupported', category=category, reason='CODEX_OPERATION_UNSUPPORTED'),
                created_at=now, expires_at=expiry.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'))
            if conn.execute('SELECT 1 FROM approvals WHERE id=?', (operation.approval_id,)).fetchone() is not None:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '新审批标识与既有事实冲突。')
            self._append(conn, workspace, history, None, ApprovalCreated(kind='created', operation=operation), now)
            _, _, latest = self.turns._owned_state(conn, workspace)
            self.verify_history(conn, workspace, latest)
            return operation.approval_id

    def _append(self, conn, workspace, history, state, event, now):
        bound = CodexApprovalRepository(conn, workspace).append(state, event, now)
        _, repo, actual = self.turns._owned_state(conn, workspace)
        # The new approval event is not yet witnessed. _owned_state checks the
        # Codex graph only; full cross-owner checks follow the same-TX append.
        session, _ = self.turns._find(actual, bound.turn_id)
        repo.append(session, bound, now)

    def close_pending(self, conn, workspace, history, turn_id, reason):
        states = self.verify_history(conn, workspace, history)
        for state in states.values():
            _, turn = self.turns._find(history, state.operation.turn_id)
            if state.operation.turn_id == turn_id and turn.control.execution == 'active' and state.decided is None and state.closed is None:
                self._append(conn, workspace, history, state, ApprovalClosed(kind='closed', reason=reason), utc_now())
