"""Finite Codex dispatch coordination; production has no execution registration.

Provider consumption, Jobs lease, immutable start and independent Run witness
commit before the trusted adapter boundary. Recovery only closes old facts.
"""
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
import sqlite3
import threading
import time
from typing import Protocol, TYPE_CHECKING
from uuid import uuid4

from pydantic import TypeAdapter

from ..codex_turn_dto import CodexFrozenOutboundSummary, SafeCode
from ..infrastructure.codex_bootstrap_execution import CodexExecutionOwners
from ..infrastructure.database import utc_now
from ..infrastructure.codex_turn_jobs import CodexTurnJobs
from ..infrastructure.codex_answer_materializer import artifact_error
from ..serialization import content_sha256
from .codex_turn import CodexTurnService
from .codex_broker_control import CodexBrokerControls
from .codex_turn_models import TurnLifecycle
from .errors import ApiError
from .provider_codex_consents import CodexConsentsService, _CodexAuthSnapshot
from .provider_codex_execution import CodexExecutionResult, CodexRequestGate, SyntheticCodexExecution, SyntheticTransport
from .provider_codex_profile import CodexRuntimeProfile, PreparedCodexRequest

if TYPE_CHECKING:
    from .codex_artifact_imports import CodexArtifactImports


class CodexTurnExecutor(Protocol):
    def available(self, profile: CodexRuntimeProfile) -> bool: ...

    def execute(self, prepared: PreparedCodexRequest, summary: CodexFrozenOutboundSummary,
                profile: CodexRuntimeProfile, before_request: Callable[[], None]) -> CodexExecutionResult: ...


@dataclass
class SyntheticCodexExecutor:
    """Explicit pure protocol test composition, never a host/CLI sandbox."""
    transport: SyntheticTransport
    peer: Callable[[CodexRequestGate], None] | None = None

    def available(self, profile: CodexRuntimeProfile) -> bool:
        return profile.version == 'codex-synthetic-runtime-profile-v1'

    def execute(self, prepared, summary, profile, before_request):
        return SyntheticCodexExecution(prepared,summary,profile,transport=self.transport).run(
            self.peer,before_request=before_request)


class CodexTurnWorker:
    def __init__(self, turns: CodexTurnService, provider: CodexConsentsService,
                 executor: CodexTurnExecutor | None = None):
        self.turns,self.provider,self.executor = turns,provider,executor
        self.database = turns.database
        self.owners = CodexExecutionOwners(self.database.settings.data_dir)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.last_error_code: str | None = None
        self._callback_context: tuple[str, str, str, int] | None = None
        self.imports: CodexArtifactImports | None = None
        self.controls = CodexBrokerControls(turns, provider, lambda: self._callback_context
            if type(self.executor) is SyntheticCodexExecutor else None)
        turns.broker_controls = self.controls

    def available(self, profile: CodexRuntimeProfile) -> bool:
        return self.executor is not None and self.executor.available(profile)

    @staticmethod
    def safe_failure(error: ApiError) -> SafeCode:
        # Unknown integrity/programming errors must not be recast as normal
        # admission failure or allow a partial damaged graph to be rewritten.
        if error.code == 'CODEX_HISTORY_DAMAGED':
            raise error
        try:
            return TypeAdapter(SafeCode).validate_python(error.code)
        except ValueError:
            raise error from None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread=threading.Thread(target=self._loop,name='learning-codex-turn-worker',daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _loop(self):
        next_recovery=0.0
        while not self._stop.is_set():
            try:
                if time.monotonic()>=next_recovery:
                    self.recover()
                    next_recovery=time.monotonic()+1
                worked=self.run_once()
                if self.imports is not None:
                    worked = self.imports.run_once() or worked
                self.last_error_code=None
            except (ApiError,sqlite3.Error) as error:
                self.last_error_code=error.code if isinstance(error,ApiError) else 'CODEX_HISTORY_DAMAGED'
                worked=False
            if not worked:
                self._stop.wait(0.25)

    def _terminal(self, conn, workspace, repo, state, turn, provider_state, *,
                  outcome, code, execution_result=None, elapsed_ms=None, collection=None):
        if self.turns.approvals is not None:
            _, _, full_history = self.turns._owned_state(conn, workspace)
            approvals = self.turns.approvals.verify_history(conn, workspace, full_history)
            pending = [value for value in approvals.values() if value.operation.turn_id == turn.control.id
                and value.closed is None and value.finished is None
                and (value.decided is None or value.status == 'approved')]
            owned = [value for value in approvals.values() if value.operation.turn_id == turn.control.id]
            uncertain = any(value.started is not None and (value.finished is None or value.finished.outcome == 'unknown') for value in owned)
            failed = next((value.finished for value in owned if value.finished and value.finished.outcome == 'failed'), None)
            if uncertain:
                outcome, code = 'unknown', 'CODEX_OUTCOME_UNKNOWN'
            elif failed is not None:
                outcome, code = 'failed', failed.error_code
            elif pending and outcome == 'completed':
                outcome, code = 'failed', 'CODEX_OPERATION_UNSUPPORTED'
            _, _, full_history = self.turns._owned_state(conn, workspace)
            self.turns.approvals.close_pending(conn, workspace, full_history, turn.control.id,
                code or 'CODEX_OPERATION_UNSUPPORTED')
            _, repo, full_history = self.turns._owned_state(conn, workspace)
            state, turn = self.turns._find(full_history, turn.control.id)
        result={'version':'codex-turn-job-result-v1' ,'turn_id':turn.control.id,
            'outcome':outcome,'dispatch_id':provider_state.queued.dispatch_id}
        if collection is not None:
            if self.turns.artifacts is None:
                raise ApiError(409, 'CODEX_HISTORY_DAMAGED', '原产物所有者缺失。')
            conn.execute('SAVEPOINT codex_artifact_terminal')
            try:
                _, _, history = self.turns._owned_state(conn, workspace)
                manifest, manifest_time = self.turns.artifacts.record_manifest(conn, workspace, history,
                    state, turn, provider_state, execution_result, collection, outcome, code)
                envelope = repo.append(state, manifest, manifest_time)
            except ApiError as error:
                conn.execute('ROLLBACK TO codex_artifact_terminal')
                conn.execute('RELEASE codex_artifact_terminal')
                outcome, code = 'failed', self.safe_failure(artifact_error(error))
                result['outcome'] = outcome
            else:
                conn.execute('RELEASE codex_artifact_terminal')
                state.envelopes.append(envelope)
                result = {**result, 'version': 'codex-turn-job-result-v2',
                    'manifest_sha256': manifest.manifest.manifest_sha256,
                    'terminal_receipt_sha256': manifest.receipt_sha256}
        status='completed' if outcome=='completed' else 'cancelled' if outcome=='cancelled' else 'failed'
        repo.jobs.transition(repo.jobs.load(turn.control.job.id),status,result=result)
        now=repo.jobs.snapshot(turn.control.job.id).updated_at
        event,binding=self.provider.record_terminal(conn,workspace,turn.control.id,provider_state,now,
            outcome=outcome,error_code=code,execution_result=execution_result,elapsed_ms=elapsed_ms)
        state.envelopes.append(repo.append(state,binding,now))
        control=repo.terminal_control(turn.control,now,outcome,code,
            turn.manifest.manifest.manifest.id if turn.manifest else None)
        repo.append(state,TurnLifecycle(kind='lifecycle',turn_id=turn.control.id,phase='terminal',control=control,
            provider_seq=event.seq,provider_sha256=content_sha256(event)),now)
        self.provider.owned_states(conn,workspace)

    def _claim(self, stack: ExitStack):
        workspace=self.database.workspace_id()
        with self.database.transaction() as conn:
            identifiers=CodexTurnJobs(conn,workspace).queued_ids()
            if not identifiers:
                return None
            _,repo,history=self.turns._owned_state(conn,workspace)
            if self.turns.approvals is not None:
                self.turns.approvals.verify_history(conn,workspace,history)
            states,_=self.provider.owned_states(conn,workspace)
            state,turn=self.turns._find(history,identifiers[0],job=True)
            provider_state=states.get(turn.control.id)
            if provider_state is None or provider_state.queued is None:
                raise ApiError(409,'CODEX_HISTORY_DAMAGED','任务缺少原消费事实。')
            try:
                provider_state,current,prepared=self.provider.admit_execution(conn,workspace,turn.control.id)
                profile=provider_state.proposed.material.input.runtime
                if not self.available(profile):
                    raise ApiError(503,'CODEX_RUNTIME_UNAVAILABLE','原执行适配器当前不可用。')
                auth = self.provider.auth_snapshot(conn, current, provider_state)
            except ApiError as error:
                code=self.safe_failure(error)
                self._terminal(conn,workspace,repo,state,turn,provider_state,outcome='failed',code=code)
                return False
            owner='codex_owner_'+uuid4().hex
            if not stack.enter_context(self.owners.hold(owner)):
                raise ApiError(503,'CODEX_RUNTIME_UNAVAILABLE','执行实例不可用。')
            conn.execute('SAVEPOINT codex_claim')
            lease=repo.jobs.claim(turn.control.job.id,profile.tools.wall_seconds+30)
            now=repo.jobs.snapshot(turn.control.job.id).updated_at
            try:
                self.provider.valid_at(provider_state,now)
            except ApiError:
                # Expiry can cross while the real Jobs owner stamps its claim.
                # Roll back that uncommitted claim, then close the still-queued
                # dispatch without inventing any possible-send consumption.
                conn.execute('ROLLBACK TO codex_claim')
                conn.execute('RELEASE codex_claim')
                self._terminal(conn,workspace,repo,state,turn,provider_state,
                    outcome='failed',code='CODEX_CONSENT_EXPIRED')
                return False
            event,binding=self.provider.record_start(conn,workspace,turn.control.id,provider_state,lease.dispatch(),owner,now)
            state.envelopes.append(repo.append(state,binding,now))
            control=repo.active_control(turn.control,now)
            repo.append(state,TurnLifecycle(kind='lifecycle',turn_id=turn.control.id,phase='claim',control=control,
                provider_seq=event.seq,provider_sha256=content_sha256(event)),now)
            self.provider.owned_states(conn,workspace)
            conn.execute('RELEASE codex_claim')
            return workspace,turn.control.id,owner,prepared,provider_state.proposed.command.ack.summary,profile,auth

    def _guard(self, workspace, turn_id, owner, started, auth: _CodexAuthSnapshot):
        if self._stop.is_set():
            raise ApiError(409,'CODEX_CANCELLED','本机执行正在停止。')
        with self.database.transaction() as conn:
            provider_state,current,_=self.provider.admit_execution(conn,workspace,turn_id,already_started=True)
            _,repo,history=self.turns._owned_state(conn,workspace)
            if self.turns.approvals is not None:
                self.turns.approvals.verify_history(conn,workspace,history)
            _,turn=self.turns._find(history,turn_id)
            row=repo.jobs.load(turn.control.job.id)
            permit=provider_state.started
            if (permit is None or permit.execution_owner_id!=owner or row['lease_owner']!=permit.lease.owner_id
                    or row['status']!='running' or row['lease_until']<=utc_now()):
                raise ApiError(409,'CODEX_OUTCOME_UNKNOWN','原开始许可不能继续派发。')
            self.provider.valid_at(provider_state,utc_now())
            if row['cancel_requested']:
                raise ApiError(409,'CODEX_CANCELLED','原任务已请求停止。')
            if time.monotonic()-started>=provider_state.proposed.command.ack.summary.tools.wall_seconds:
                raise ApiError(409,'CODEX_TIMEOUT','原任务已超过总期限。')
            self.provider.verify_auth_snapshot(conn, current, provider_state, auth)

    def _finish(self, workspace, turn_id, owner, execution_result, started, collection=None, scan_error=None):
        with self.database.transaction() as conn:
            _,repo,history=self.turns._owned_state(conn,workspace)
            states,_=self.provider.owned_states(conn,workspace)
            state,turn=self.turns._find(history,turn_id)
            provider_state=states[turn_id]
            if provider_state.finished is not None:
                return
            if provider_state.started is None or provider_state.started.execution_owner_id!=owner:
                raise ApiError(409,'CODEX_HISTORY_DAMAGED','原执行实例不一致。')
            outcome,code=(execution_result.outcome,execution_result.error_code) if execution_result is not None else ('unknown','CODEX_OUTCOME_UNKNOWN')
            # Receiving a real response survives actor loss; receiving it does
            # not renew permission or label an interrupted operation complete.
            if turn.control.cancel_requested:
                outcome,code='cancelled','CODEX_CANCELLED'
            elif outcome=='completed':
                try:
                    self.provider.admit_execution(conn,workspace,turn_id,already_started=True)
                except ApiError as error:
                    outcome,code='failed',self.safe_failure(error)
                if time.monotonic()-started>=provider_state.proposed.command.ack.summary.tools.wall_seconds:
                    outcome,code='failed','CODEX_TIMEOUT'
            if scan_error is not None:
                outcome, code = 'failed', scan_error
            self._terminal(conn,workspace,repo,state,turn,provider_state,outcome=outcome,code=code,
                execution_result=execution_result,elapsed_ms=max(0,int((time.monotonic()-started)*1000)), collection=collection)

    def run_once(self) -> bool:
        if not self._lock.acquire(blocking=False):
            return False
        try:
            with ExitStack() as stack:
                claimed=self._claim(stack)
                if claimed is None:
                    return False
                if claimed is False:
                    return True
                workspace,turn_id,owner,prepared,summary,profile,auth=claimed
                started=time.monotonic()
                self._callback_context=(workspace,turn_id,owner,threading.get_ident())
                try:
                    if self.executor is None:
                        raise ApiError(503,'CODEX_RUNTIME_UNAVAILABLE','执行适配器不可用。')
                    result=self.executor.execute(prepared,summary,profile,
                        lambda:self._guard(workspace,turn_id,owner,started,auth))
                    result=CodexExecutionResult.model_validate(result.model_dump(mode='json'))
                except Exception:
                    # The adapter did not yield a checked receipt. Preserve an
                    # unknown outcome; never invent a zero-call response fact.
                    result=None
                finally:
                    self._callback_context=None
                    self.controls.release(workspace, turn_id, owner)
                collection, scan_error = None, None
                if self.turns.artifacts is not None and self.turns.artifacts.producer is not None:
                    try:
                        # Only this exact trusted synchronous adapter has a
                        # closed process-free stop contract. Other adapters do
                        # not acquire file authority by returning a result DTO.
                        if type(self.executor) is not SyntheticCodexExecutor:
                            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '没有受检的原执行停止映射。')
                        collection = self.turns.artifacts.collect_stopped_answer(workspace, turn_id, owner, result)
                    except ApiError as error:
                        scan_error = self.safe_failure(error)
                self._finish(workspace,turn_id,owner,result,started,collection,scan_error)
                return True
        finally:
            self._lock.release()

    def bind_control_peer(self, upstream_turn_id: str, transport: Callable[[bytes], list[bytes]]):
        context = self._callback_context
        if (context is None or context[3] != threading.get_ident()
                or type(self.executor) is not SyntheticCodexExecutor):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '没有原执行实例控制映射。')
        return self.controls.bind_peer(context[0], context[1], context[2], context[3], upstream_turn_id, transport)

    def interrupt_once(self) -> bool:
        context = self._callback_context
        if (context is None or context[3] != threading.get_ident()
                or type(self.executor) is not SyntheticCodexExecutor):
            return False
        return self.controls.interrupt_once(context[0], context[1], context[2], context[3])

    def receive_operation(self, raw: bytes) -> str:
        """Internal synthetic adapter input; never an HTTP authority port.

        The original v1 model request profile is unchanged. This separate intake
        only retains denied callbacks and cannot start any host operation.
        """
        context = self._callback_context
        if (context is None or context[3] != threading.get_ident()
                or type(self.executor) is not SyntheticCodexExecutor or self.turns.approvals is None):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '没有受检的活跃回调实例。')
        return self.turns.approvals.receive(context[0], context[1], context[2], raw)

    def execute_operation(self, identifier: str):
        context = self._callback_context
        if (context is None or context[3] != threading.get_ident()
                or type(self.executor) is not SyntheticCodexExecutor or self.turns.approvals is None):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '没有受检的活跃回调实例。')
        return self.turns.approvals.execute_owned_operation(context[0], context[1], context[2], identifier)

    def recover(self) -> int:
        workspace=self.database.workspace_id()
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            states,_=self.provider.owned_states(conn,workspace)
            pending=[(turn,state.started.execution_owner_id) for turn,state in states.items()
                if state.started is not None and state.finished is None]
        count=0
        for turn_id,owner in pending:
            with self.owners.hold(owner) as inactive:
                if not inactive:
                    continue
                with self.database.transaction() as conn:
                    _,repo,history=self.turns._owned_state(conn,workspace)
                    states,_=self.provider.owned_states(conn,workspace)
                    state,turn=self.turns._find(history,turn_id)
                    provider_state=states[turn_id]
                    if provider_state.finished is not None:
                        continue
                    row=repo.jobs.load(turn.control.job.id)
                    if row['lease_until']>utc_now():
                        continue
                    self._terminal(conn,workspace,repo,state,turn,provider_state,
                        outcome='unknown',code='CODEX_OUTCOME_UNKNOWN')
                    self.controls.recover_owned(conn, workspace, turn_id)
                    count+=1
        return count
