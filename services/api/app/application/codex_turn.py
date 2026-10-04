"""Codex preparation, immutable dispatch control and current safe projections."""
import base64
import hashlib
import hmac
import secrets
from uuid import uuid4
from typing import TYPE_CHECKING, TypeVar, Literal
from collections.abc import Callable

from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json, sha256_bytes
from ..codex_turn_dto import (
    CodexCurrentSessionView, CodexTurnPrepareWrite, CodexTurnPreparationView, CodexTurnControlView, CodexTurnPage,
    CodexTurnStartWrite, CodexTurnStartAck, CodexTurnResultView,
)
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.codex_turn_repository import CodexTurnRepository, CheckedSession, CheckedTurn
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import SessionIdentity
from ..serialization import canonical_json, content_sha256
from .codex_bootstrap import CodexBootstrapService
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import CodexTurnContext, damaged
from .codex_turn_models import (
    SessionAnchor, TurnRuntimeBinding, TurnInput, TurnPrepared, TurnCancelled, PrepareCommand, CancelCommand,
    preparation_digest, StartCommand, TurnStarted, TurnCancelRequested,
)
from .errors import ApiError
from .providers import checked_provider_configuration, validate_key
from .provider_codex_ports import CodexOutboundMaterial
from .provider_codex_ports import CodexOutboundSourceState
from .provider_budget import ProofRegistry
from .codex_turn_execution_models import RunnableTurnInput, RunnableTurnPrepared
from .provider_codex_profile import CodexRuntimeProfile
from .provider_models import UsageSnapshot, DispatchLease

if TYPE_CHECKING:
    from .provider_codex_consents import CodexConsentsService


Delivery = TypeVar("Delivery")


def missing() -> ApiError:
    return ApiError(404, 'REFERENCE_MISSING', '本工作区没有此本地任务记录。')


class CodexTurnService:
    def __init__(self, database: Database, bootstrap: CodexBootstrapService, proofs: ProofRegistry | None = None):
        self.database, self.bootstrap = database, bootstrap
        self.context = CodexTurnContext(database)
        self._cursor_key = secrets.token_bytes(32)
        self.proofs = (proofs or ProofRegistry()).codex
        self.outbound_owner: CodexConsentsService | None = None
        self.execution_available: Callable[[CodexRuntimeProfile], bool] = lambda profile: False

    def _deliver(self, identity: SessionIdentity, value: Delivery, *, subject: bool) -> Delivery:
        # A prior WAL read snapshot cannot observe a concurrently committed
        # logout/role/Policy change. Check delivery in a new read transaction.
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current_control_access(conn, identity, write=subject)
        return value

    def prepare_turn(self, identity: SessionIdentity, session_id: str,
                     body: CodexTurnPrepareWrite, key: str) -> CodexTurnPreparationView:
        return self._deliver(identity, self._prepare_turn(identity, session_id, body, key), subject=True)

    def read_preparation(self, identity: SessionIdentity, identifier: str) -> CodexTurnPreparationView:
        return self._deliver(identity, self._read_preparation(identity, identifier), subject=True)

    def read_control(self, identity: SessionIdentity, identifier: str) -> CodexTurnControlView:
        return self._deliver(identity, self._read_control(identity, identifier), subject=False)

    def read_session(self, identity: SessionIdentity, identifier: str) -> CodexCurrentSessionView:
        return self._deliver(identity, self._read_session(identity, identifier), subject=False)

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        return self._deliver(identity, self._job(identity, identifier), subject=False)

    def cancel_job(self, identity: SessionIdentity, identifier: str, body: JobCancelRequest, key: str) -> JobSnapshot:
        return self._deliver(identity, self._cancel_job(identity, identifier, body, key), subject=False)

    def turns(self, identity: SessionIdentity, session_id: str, cursor: str | None = None, limit: int = 20) -> CodexTurnPage:
        return self._deliver(identity, self._turns(identity, session_id, cursor, limit), subject=False)

    def _state(self, conn, identity, *, subject=False):
        current, original, repository, history = self._base_state(conn, identity, subject=subject)
        if self.outbound_owner is not None:
            self.outbound_owner.verify_links(conn, current, self._source_views(conn, current, history))
        return current, original, repository, history

    def _control_views(self, conn, identity, history):
        # Derived expiry belongs only to a response. Mutation reducers must keep
        # the original grant/revocation facts in the immutable Run projection.
        controls = self.outbound_owner.verify_links(conn, identity, self._source_views(conn, identity, history)) if self.outbound_owner else {}
        result = {}
        for state in history.values():
            for turn in state.turns.values():
                consent = controls.get(turn.control.id, turn.control.consent_control)
                result[turn.control.id] = CodexTurnControlView.model_validate({**turn.control.model_dump(),
                    'consent_control':consent.model_dump() if consent else None})
        return result

    def _base_state(self, conn, identity, *, subject=False):
        current = current_control_access(conn, identity, write=subject)
        original = self.bootstrap.checked_sessions(conn, current)
        repository = CodexTurnRepository(conn, current, self.context)
        return current, original, repository, repository.checked(original)

    def _source_views(self, transaction, identity, history):
        return self._owned_source_views(transaction, identity.workspace_id, history)

    def _owned_state(self, conn, workspace_id):
        """Private persistence facts; deliberately not an access identity."""
        original = self.bootstrap.checked_owned_sessions(conn, workspace_id)
        repository = CodexTurnRepository(conn, workspace_id, self.context)
        return original, repository, repository.checked(original)

    def _owned_source_views(self, transaction, workspace_id, history):
        result = {}
        for state in history.values():
            for turn in state.turns.values():
                context = self.context.verify_owned_turn(transaction, workspace_id, turn.prepared.input, turn.prepared.command.ack.summary)
                material = CodexOutboundMaterial(version='codex-outbound-material-v1', workspace_id=workspace_id,
                    actor_session_id=turn.prepared.input.actor_session_id, preparation=turn.prepared.command.ack,
                    job_revision=turn.control.job_revision, input=turn.prepared.input, context=context)
                result[turn.control.id] = CodexOutboundSourceState(material=material, control=turn.control,
                    provider_bindings=turn.provider_bindings, start=turn.start, lifecycle=turn.lifecycle,
                    active_lease=self.dispatch_lease(transaction,workspace_id,turn.control.job.id))
        return result

    @staticmethod
    def dispatch_lease(transaction, workspace_id, job_id):
        from ..infrastructure.codex_turn_jobs import CodexTurnJobs
        row=CodexTurnJobs(transaction,workspace_id).load(job_id)
        return DispatchLease(owner_id=row['lease_owner'],job_revision=row['revision'],expires_at=row['lease_until']) if row['status']=='running' else None

    def verify_dispatch_lease(self, transaction, workspace_id, job_id, lease):
        if self.dispatch_lease(transaction,workspace_id,job_id) != lease:
            raise damaged()

    def owned_outbound_sources(self, transaction, workspace_id):
        _, _, history = self._owned_state(transaction, workspace_id)
        return self._owned_source_views(transaction, workspace_id, history)

    def outbound_sources(self, transaction, identity):
        current, _, _, history = self._base_state(transaction, identity)
        return self._source_views(transaction, current, history)

    def current_outbound_material(self, transaction, identity, material):
        current_control_access(transaction, identity, write=True)
        actual = self.outbound_sources(transaction, identity).get(material.preparation.turn_id)
        if actual is None or actual.material.model_dump(exclude={'job_revision'}) != material.model_dump(exclude={'job_revision'}):
            raise damaged()
        return self.context.current(transaction, identity, material.context)

    def bind_outbound_event(self, transaction, identity, event, occurred_at):
        current, original, repository, history = self._base_state(transaction, identity)
        state, turn = self._find(history, event.turn_id)
        repository.append(state, event, occurred_at)
        repository.checked(original)

    def read_outbound_preparation(self, transaction, identity: SessionIdentity,
                                 preparation_id: str, expected_job_revision: int) -> CodexOutboundMaterial:
        """Trusted Provider source, retaining the actual caller transaction."""
        if not transaction.in_transaction:
            raise damaged()
        current, _, _, history = self._state(transaction, identity, subject=True)
        state, turn = self._find(history, preparation_id, preparation=True)
        if turn.prepared.input.actor_session_id != current.id:
            raise ApiError(403, 'POLICY_DENIED', '新操作者不能接管原本地任务。')
        if expected_job_revision != turn.control.job_revision:
            raise ApiError(412, 'REVISION_MISMATCH', '任务修订已改变，请读取当前事实。')
        if state.active_turn_id != turn.control.id or turn.control.execution == 'terminal':
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '原任务已不可建立新的外发许可。')
        context = self.context.verify_turn(transaction, current, turn.prepared.input, turn.prepared.command.ack.summary)
        if not self.context.current(transaction, current, context):
            raise ApiError(409, 'CODEX_SOURCE_CHANGED', '原冻结来源已改变，不能继续授权。')
        return CodexOutboundMaterial(version='codex-outbound-material-v1', workspace_id=current.workspace_id,
            actor_session_id=current.id, preparation=turn.prepared.command.ack,
            job_revision=turn.control.job_revision, input=turn.prepared.input, context=context)

    def start_turn(self, identity: SessionIdentity, session_id: str, body: CodexTurnStartWrite, key: str) -> CodexTurnStartAck:
        return self._deliver(identity, self._start_turn(identity, session_id, body, key), subject=True)

    def _start_turn(self, identity, session_id, body, key):
        key = validate_key(key)
        body = CodexTurnStartWrite.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current, original, repo, history = self._state(conn, identity, subject=True)
            replay = repo.replay(history, current, 'start', session_id, key, body)
            if replay is not None:
                return CodexTurnStartAck.model_validate(replay.model_dump())
            state, turn = self._find(history, body.preparation_id, preparation=True)
            preparation = turn.prepared.command.ack
            if current.id != state.anchor.actor_session_id:
                raise ApiError(403, 'POLICY_DENIED', '新操作者不能消费原任务许可。')
            if state.anchor.session_id != session_id or preparation.preparation_sha256 != body.preparation_sha256:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '开始命令须绑定原会话和准备。')
            if body.expected_session_revision != state.revision:
                raise ApiError(412, 'REVISION_MISMATCH', '会话控制修订已改变。')
            if state.active_turn_id != turn.control.id or turn.start is not None or turn.control.job.status != 'awaiting_approval':
                raise ApiError(409, 'CODEX_BINDING_INVALID', '原任务已消费许可或不能开始。')
            if not isinstance(turn.prepared.input, RunnableTurnInput):
                raise ApiError(503, 'CODEX_INPUT_PROOF_UNAVAILABLE', '没有完整请求证明。')
            if self.outbound_owner is None:
                raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '当前部署没有对应的受检执行适配器。')
            ack = CodexTurnStartAck(turn_id=turn.control.id, session_revision=state.revision+1,
                job=dm.JobRef(id=turn.control.job.id, status='queued'))
            command = StartCommand(workspace_id=current.workspace_id, actor_session_id=current.id, route='start',
                target_id=session_id, key=key, body=body, ack=ack)
            dispatch, binding = self.outbound_owner.consume(conn, current, turn.control.id, body.consent_id, content_sha256(command))
            if not self.execution_available(turn.prepared.input.runtime):
                # Provider proof/current eligibility is checked first. This same
                # transaction rolls back the tentative consume when no adapter
                # is registered; no permission or queued Job escapes it.
                raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '当前部署没有对应的受检执行适配器。')
            bound = repo.append(state, binding, dispatch.occurred_at)
            state.envelopes.append(bound)
            repo.jobs.transition(repo.jobs.load(turn.control.job.id), 'queued')
            repo.append(state, TurnStarted(kind='start_queued', turn_id=turn.control.id,
                dispatch_id=dispatch.event.dispatch_id, command=command), utc_now())
            self._state(conn, current, subject=True)
            return ack

    @staticmethod
    def _find(history, identifier, *, job=False, preparation=False) -> tuple[CheckedSession, CheckedTurn]:
        for state in history.values():
            for turn in state.turns.values():
                value = turn.prepared.command.ack
                key = value.job.id if job else value.id if preparation else value.turn_id
                if key == identifier:
                    return state, turn
        raise missing()

    def _prepare_turn(self, identity: SessionIdentity, session_id: str,
                     body: CodexTurnPrepareWrite, key: str) -> CodexTurnPreparationView:
        key = validate_key(key)
        body = CodexTurnPrepareWrite.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current, originals, repo, history = self._state(conn, identity, subject=True)
            replay = repo.replay(history, current, 'prepare', session_id, key, body)
            if replay is not None:
                return CodexTurnPreparationView.model_validate(replay.model_dump())
            original = originals.get(session_id)
            if original is None or original.session is None:
                raise missing()
            if original.session.status != 'ready' or original.finished is None:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '原本地会话尚无受检的 ready 映射。')
            if original.operation.actor_session_id != current.id:
                raise ApiError(403, 'POLICY_DENIED', '新操作者不能接管原本地会话的准备权限。')
            state = history.get(session_id)
            revision = state.revision if state else original.session.revision
            if body.expected_session_revision != revision:
                raise ApiError(412, 'REVISION_MISMATCH', '会话控制修订已改变，请读取当前事实。')
            if state and state.active_turn_id is not None:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '此会话已有未结束任务。')
            provider = checked_provider_configuration(conn, current, body.provider_id)
            previous=[]
            if self.outbound_owner is not None:
                provider_states,sources=self.outbound_owner.owned_states(conn,current.workspace_id)
                previous=self.outbound_owner.completed_history(provider_states,sources,session_id,revision)
            now = utc_now()
            if state is None:
                state = repo.establish(SessionAnchor(version='codex-turn-session-v1', workspace_id=current.workspace_id,
                    session_id=session_id, actor_session_id=current.id, bootstrap_sha256=content_sha256(original),
                    thread_id='thread_' + uuid4().hex, created_at=now))
            runtime = TurnRuntimeBinding(version='codex-turn-unavailable-profile-v1', implemented=False,
                bootstrap_sha256=state.anchor.bootstrap_sha256, template_version='codex-local-task-v1', tools=body.tools,
                cpu_seconds=60, memory_bytes=2147483648, file_bytes=16777216, protocol_output_bytes=16777216,
                file_descriptors=128, processes=16, core_bytes=0, command_network='denied', writable_area='turn_outputs')
            available = self.proofs.freeze(state.anchor.bootstrap_sha256, body.tools, config=provider)
            value = (RunnableTurnInput if available is not None else TurnInput).model_validate(dict(
                version='codex-turn-input-v2' if available is not None else 'codex-turn-input-v1', workspace_id=current.workspace_id,
                actor_session_id=current.id, session_id=session_id, turn_id='turn_' + uuid4().hex,
                job_id='job_' + uuid4().hex, request=body, provider=provider, runtime=available if available is not None else runtime))
            repo.jobs.create(value.job_id, 'codex_turn', value)
            context = self.context.prepare_turn(conn, current, value, now, previous)
            summary = self.context.summary(context)
            ack = CodexTurnPreparationView(id='turnprep_' + uuid4().hex, preparation_sha256='0' * 64,
                actor_session_id=current.id, session_id=session_id, session_revision=revision + 1,
                turn_id=value.turn_id, job=dm.JobRef(id=value.job_id, status='awaiting_approval'), request=body,
                summary=summary, created_at=now, proposal_id=None, consent_id=None, validity='current' if available is not None else 'unavailable')
            ack.preparation_sha256 = preparation_digest(current.workspace_id, ack)
            event = (RunnableTurnPrepared if available is not None else TurnPrepared).model_validate(dict(kind='prepared', creation_sequence=repo.next_creation_sequence(), input=value, command=PrepareCommand(workspace_id=current.workspace_id,
                actor_session_id=current.id, route='prepare', target_id=session_id, key=key, body=body, ack=ack)))
            repo.append(state, event, now)
            # Verify the actual graph before committing: Job/Run/context and
            # immutable command must either all survive or all roll back.
            self._state(conn,current,subject=True)
            current_control_access(conn, current, write=True)
            return ack

    def _read_preparation(self, identity: SessionIdentity, identifier: str) -> CodexTurnPreparationView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current, _, _, history = self._state(conn, identity, subject=True)
            _, turn = self._find(history, identifier, preparation=True)
            ack, value = turn.prepared.command.ack, turn.prepared.input
            validity = 'closed' if turn.control.execution == 'terminal' else 'unavailable'
            if validity != 'closed':
                if isinstance(value, RunnableTurnInput):
                    validity = self.proofs.current(value.runtime)
                context = self.context.verify_turn(conn, current, value, ack.summary)
                provider = checked_provider_configuration(conn, current, value.provider.id)
                if provider != value.provider or not self.context.current(conn, current, context):
                    validity = 'changed'
            binding = turn.provider_bindings[-1] if turn.provider_bindings else None
            return CodexTurnPreparationView.model_validate({**ack.model_dump(), 'job': turn.control.job.model_dump(),
                'validity': validity, 'proposal_id':binding.proposal_id if binding else None,
                'consent_id':binding.consent_id if binding else None})

    def _read_control(self, identity: SessionIdentity, identifier: str) -> CodexTurnControlView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current, _, _, history = self._state(conn, identity)
            turn = self._find(history, identifier)[1]
            return self._control_views(conn, current, history)[turn.control.id]

    def read_result(self, identity: SessionIdentity, identifier: str) -> CodexTurnResultView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current,_,_,history=self._state(conn,identity,subject=True)
            _,turn=self._find(history,identifier)
            terminal=None
            if self.outbound_owner is not None:
                states,_=self.outbound_owner.owned_states(conn,current.workspace_id)
                provider=states.get(identifier)
                terminal=provider.finished if provider else None
            answer=terminal.answer if terminal else ''
            output: Literal['none','partial','complete']='none'
            if answer and terminal and terminal.execution_result:
                output=terminal.execution_result.output_state
            value=CodexTurnResultView(control=self._control_views(conn,current,history)[identifier],
                preparation_id=turn.prepared.command.ack.id,answer_markdown=answer,
                output_sha256=sha256_bytes(answer.encode()) if answer else None,output_state=output,
                usage=terminal.usage if terminal else UsageSnapshot(input_tokens=None,output_tokens=None),
                mathematical='NOT_RUN',sources='NOT_RUN',independent_pedagogy='NOT_RUN')
        return self._deliver(identity,value,subject=True)

    def _read_session(self, identity: SessionIdentity, identifier: str) -> CodexCurrentSessionView:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            _, original, _, history = self._state(conn, identity)
            snapshot = original.get(identifier)
            if snapshot is None or snapshot.session is None:
                raise missing()
            value = snapshot.session.model_dump()
            state = history.get(identifier)
            if state:
                value.update(revision=state.revision, active_turn_id=state.active_turn_id)
            return CodexCurrentSessionView.model_validate(value)

    def _job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            _, _, repo, history = self._state(conn, identity)
            self._find(history, identifier, job=True)
            return repo.jobs.snapshot(identifier)

    def _cancel_job(self, identity: SessionIdentity, identifier: str, body: JobCancelRequest, key: str) -> JobSnapshot:
        key = validate_key(key)
        body = JobCancelRequest.model_validate(body.model_dump())
        with self.database.transaction() as conn:
            current, original, repo, history = self._state(conn, identity)
            replay = repo.replay(history, current, 'cancel', identifier, key, body)
            if replay is not None:
                return JobSnapshot.model_validate(replay.model_dump())
            state, turn = self._find(history, identifier, job=True)
            if body.expected_revision != turn.control.job_revision:
                raise ApiError(412, 'REVISION_MISMATCH', '任务修订已改变，请读取当前事实。')
            terminal = turn.control.execution == 'terminal'
            active = turn.control.execution == 'active'
            already_requested = turn.control.cancel_requested
            provider_state = None
            if not terminal and turn.start is not None and self.outbound_owner is not None:
                provider_state = self.outbound_owner.owned_states(conn,current.workspace_id)[0][turn.control.id]
            if not terminal:
                if state.active_turn_id != turn.control.id:
                    raise damaged()
                repo.jobs.cancel(identifier, body.expected_revision)
            ack = repo.jobs.snapshot(identifier)
            command=CancelCommand(workspace_id=current.workspace_id, actor_session_id=current.id, route='cancel',
                target_id=identifier,key=key,body=body,ack=ack)
            if provider_state is not None and not active and self.outbound_owner is not None:
                _, binding = self.outbound_owner.record_terminal(conn,current.workspace_id,turn.control.id,provider_state,
                    ack.updated_at,outcome='cancelled',error_code='CODEX_CANCELLED')
                bound = repo.append(state,binding,ack.updated_at)
                state.envelopes.append(bound)
            event: TurnCancelled | TurnCancelRequested
            if active:
                event = TurnCancelRequested(kind='cancel_request_observed' if already_requested else 'cancel_requested',
                    turn_id=turn.control.id,session_revision=None if already_requested else state.revision+1,command=command)
            else:
                event = TurnCancelled(kind='cancel_observed' if terminal else 'cancelled', turn_id=turn.control.id,
                    requested_session_revision=None if terminal else state.revision + 1,
                    terminal_session_revision=None if terminal else state.revision + 2,command=command)
            repo.append(state, event, ack.updated_at if not terminal and not already_requested else utc_now())
            self._state(conn,current)
            current_control_access(conn, current, write=False)
            return ack

    def _turns(self, identity: SessionIdentity, session_id: str, cursor: str | None = None, limit: int = 20) -> CodexTurnPage:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(422, 'SCHEMA_INVALID', '分页数量须为1至100。')
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current, original, _, history = self._state(conn, identity)
            if session_id not in original:
                raise missing()
            state = history.get(session_id)
            turns = sorted(state.turns.values(), key=lambda item: item.sequence, reverse=True) if state else []
            high = turns[0].sequence if turns else 0
            position = high + 1
            if cursor is not None:
                try:
                    if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048:
                        raise ValueError('length')
                    raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
                    if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                        raise ValueError('signature')
                    value = strict_json(raw[32:])
                    if (set(value) != {'workspace', 'session', 'limit', 'high', 'position'}
                            or value['workspace'] != current.workspace_id or value['session'] != session_id
                            or type(value['limit']) is not int or value['limit'] != limit
                            or type(value['high']) is not int or type(value['position']) is not int
                            or not 0 < value['position'] <= value['high'] <= high):
                        raise ValueError('binding')
                    high, position = value['high'], value['position']
                except (ValueError, TypeError, KeyError):
                    raise ApiError(400, 'CURSOR_INVALID', '分页游标无效，请重新读取第一页。') from None
            selected = [item for item in turns if item.sequence <= high and item.sequence < position]
            next_cursor = None
            if len(selected) > limit:
                raw = canonical_json({'workspace': current.workspace_id, 'session': session_id,
                    'limit': limit, 'high': high, 'position': selected[limit - 1].sequence}).encode()
                next_cursor = base64.urlsafe_b64encode(hmac.new(self._cursor_key, raw, hashlib.sha256).digest() + raw).decode().rstrip('=')
            controls = self._control_views(conn, current, history)
            return CodexTurnPage(items=[controls[item.control.id] for item in selected[:limit]], next_cursor=next_cursor)
