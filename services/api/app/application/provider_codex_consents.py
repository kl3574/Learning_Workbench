"""Provider-owned Codex proposals/grants; no ordinary text-adapter fallback."""
from dataclasses import dataclass
from datetime import timedelta
import hmac
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from ..codex_turn_dto import (
    CodexOutboundPreviewWrite, CodexConsentProposalView, CodexFrozenOutboundSummary,
    CodexConsentCreateWrite, CodexConsentCreateAck,
)
from ..provider_dto import ConsentRevoke, ProposalWarning, MessageSummary
from ..infrastructure.database import Database, utc_now
from ..infrastructure.consent_repository import instant
from ..infrastructure.provider_repository import ProviderRepository
from ..infrastructure.provider_codex_repository import CodexProviderRepository
from ..infrastructure.provider_secret_store import SecretStore
from ..infrastructure.security import SessionIdentity, author_execution_identity
from ..serialization import content_sha256
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import damaged
from .codex_turn_models import TurnProviderBound
from .codex_turn_execution_models import RunnableTurnInput, RunnableTurnContext, UnavailableHistoryContext, CodexCompletedHistory
from .codex_turn_preparation_models import UnavailablePreparationContext
from .codex_turn_context import select_history, wrapped
from .errors import ApiError
from .provider_budget import ProofRegistry
from .provider_codex_models import CodexProposed, CodexGranted, CodexRevoked, CodexPreviewCommand, CodexGrantCommand, CodexRevokeCommand, CodexDispatchQueued, CodexDispatchStarted, CodexDispatchFinished
from .provider_models import UsageSnapshot
from .provider_codex_ports import CodexOutboundSourcePort
from .provider_codex_profile import PreparedCodexRequest, unavailable
from .providers import checked_provider_configuration, validate_key


def missing() -> ApiError:
    return ApiError(404, 'REFERENCE_MISSING', '本工作区没有此 Codex 外发记录。')


@dataclass(frozen=True, slots=True, repr=False)
class _CodexAuthSnapshot:
    """Private retained owner material, not a request handle or send authority.

    No serializer/public DTO consumes this object. An explicit private local
    memory owner may retain it; qualified production request/auth facts and
    durable-start-to-send integration remain unavailable.
    """
    workspace_id: str
    turn_id: str
    dispatch_id: str
    provider_id: str
    provider_revision: int
    config_sha256: str
    locator: str
    secret: str


class CodexConsentsService:
    def __init__(self, database: Database, source: CodexOutboundSourcePort,
                 secrets: SecretStore, proofs: ProofRegistry):
        self.database, self.source, self.secrets, self.proofs = database, source, secrets, proofs.codex

    def _deliver(self, identity, value, *, subject=True):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current_control_access(conn, identity, write=subject)
        return value

    def _states(self, conn, identity):
        states = CodexProviderRepository(conn, identity.workspace_id).checked()
        sources = self.source.outbound_sources(conn, identity)
        self._verify_links(states, sources)
        return states, sources

    def owned_states(self, conn, workspace_id):
        """Integrity-only history for finishing an already-owned execution.

        No caller identity is synthesized and no new request is authorized.
        """
        states = CodexProviderRepository(conn, workspace_id).checked()
        sources = self.source.owned_outbound_sources(conn, workspace_id)
        self._verify_links(states, sources)
        return states, sources

    def verify_links(self, conn, identity, sources):
        states = CodexProviderRepository(conn, identity.workspace_id).checked()
        self._verify_links(states, sources)
        return {turn: state.consent_control(utc_now()) for turn, state in states.items()}

    @staticmethod
    def _verify_links(states, sources):
        for source in sources.values():
            context=source.material.context
            prior=CodexConsentsService.completed_history(states,sources,source.material.preparation.session_id,
                source.material.preparation.request.expected_session_revision)
            size=len(context.messages[0].content)+len(source.material.preparation.request.message)+sum(len(wrapped(item)) for item in context.evidence)
            kept,omitted=select_history(prior,size)
            if isinstance(context,(RunnableTurnContext,UnavailableHistoryContext,UnavailablePreparationContext)):
                if context.history != kept or context.omitted_history != omitted:
                    raise damaged()
                if ('CODEX_CONTEXT_HISTORY_OMITTED' in [warning.code for warning in context.warnings]) != bool(omitted):
                    raise damaged()
            elif prior:
                raise damaged()
        if set(states) != {turn for turn, source in sources.items() if source.provider_bindings}:
            raise damaged()
        for turn, state in states.items():
            source = sources[turn]
            if (state.proposed.material.model_dump(exclude={'job_revision'}) != source.material.model_dump(exclude={'job_revision'})
                    or len(source.provider_bindings) != len(state.envelopes)):
                raise damaged()
            consent, revision, status = None, None, None
            for envelope, binding in zip(state.envelopes, source.provider_bindings, strict=True):
                event = envelope.event
                if isinstance(event, CodexGranted):
                    consent, revision, status = event.command.ack.id, 1, 'active'
                elif isinstance(event, CodexRevoked):
                    revision, status = 2, 'revoked'
                if (binding.turn_id != turn or binding.provider_seq != envelope.seq
                        or binding.provider_sha256 != content_sha256(envelope)
                        or binding.proposal_id != state.proposed.command.ack.id
                        or (binding.consent_id,binding.consent_revision,binding.consent_status) != (consent,revision,status)):
                    raise damaged()
            raw_control = source.control.consent_control
            if ((raw_control is None) != (consent is None) or raw_control is not None
                    and (raw_control.id,raw_control.revision,raw_control.status) != (consent,revision,status)):
                raise damaged()
            if (state.queued is None) != (source.start is None):
                raise damaged()
            if state.queued is not None:
                start = source.start
                if (start.dispatch_id != state.queued.dispatch_id
                        or start.command.body.consent_id != state.queued.consent_id
                        or content_sha256(start.command) != state.queued.start_command_sha256):
                    raise damaged()
                claims = [item for item in source.lifecycle if item.phase == 'claim']
                if (state.started is None) != (not claims) or len(claims) > 1:
                    raise damaged()
                if state.started is not None:
                    if source.control.execution == 'active' and (source.active_lease is None
                            or source.active_lease.owner_id != state.started.lease.owner_id
                            or source.active_lease.expires_at != state.started.lease.expires_at):
                        raise damaged()
                    original = next(item for item in state.envelopes if item.event == state.started)
                    claim = claims[0]
                    if ((claim.provider_seq,claim.provider_sha256) != (original.seq,content_sha256(original))
                            or claim.control.started_at != original.occurred_at
                            or claim.control.job_revision != state.started.lease.job_revision):
                        raise damaged()
                if (state.finished is not None) != (source.control.execution == 'terminal'):
                    raise damaged()
                if state.finished is not None and (source.control.outcome != state.finished.outcome
                        or source.control.error_code != state.finished.error_code
                        or source.control.finished_at != state.finished_at):
                    raise damaged()

    @staticmethod
    def completed_history(states, sources, session_id, before_revision):
        eligible = sorted((source for source in sources.values()
            if source.material.preparation.session_id == session_id
            and source.material.preparation.session_revision < before_revision
            and source.control.outcome == 'completed'), key=lambda item:item.material.preparation.session_revision)[-2:]
        result=[]
        for source in eligible:
            state=states.get(source.control.id)
            if state is None or state.finished is None or state.finished.outcome != 'completed':
                raise damaged()
            receipt=next(item for item in state.envelopes if item.event == state.finished)
            answer=state.finished.answer
            result.append(CodexCompletedHistory(turn_id=source.control.id,user=source.material.preparation.request.message,
                answer=answer,receipt_sha256=content_sha256(receipt),output_sha256=sha256_bytes(answer.encode()) if answer else None))
        return result

    def _bind(self, conn, identity, state, envelope):
        # The Provider fact and the consumer's independent witness commit together.
        event = self.binding(state, envelope)
        self.source.bind_outbound_event(conn, identity, event, envelope.occurred_at)

    @staticmethod
    def binding(state, envelope):
        if isinstance(envelope.event, CodexProposed):
            proposal, grant, revoked = envelope.event.command.ack.id, None, False
        else:
            proposal = state.proposed.command.ack.id
            grant = (envelope.event.command.ack if isinstance(envelope.event, CodexGranted)
                     else state.granted.command.ack if state.granted else None)
            revoked = isinstance(envelope.event, CodexRevoked) or state.revoked_at is not None
        return TurnProviderBound(kind='provider_bound', turn_id=envelope.turn_id,
            provider_seq=envelope.seq, provider_sha256=content_sha256(envelope), proposal_id=proposal,
            consent_id=grant.id if grant else None, consent_revision=(2 if revoked else 1) if grant else None,
            consent_status=('revoked' if revoked else 'active') if grant else None)

    def consume(self, conn, identity, turn_id, consent_id, command_sha256):
        """Provider-owned consume in the caller's active coordinated transaction.

        The caller must atomically bind the returned witness, original start
        ACK and queued Job before checking the completed owner graph.
        """
        if not conn.in_transaction:
            raise damaged()
        current = current_control_access(conn, identity, write=True)
        states, sources = self._states(conn, current)
        state = self._find(states, consent_id, consent=True)
        if state.proposed.material.preparation.turn_id != turn_id:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '许可不属于此准备和任务。')
        if state.granted.command.actor_session_id != current.id:
            raise ApiError(403, 'POLICY_DENIED', '新操作者不能消费原许可。')
        if state.queued is not None:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原许可已消费，不能重新排队。')
        if state.revoked_at is not None:
            raise ApiError(409, 'CODEX_CONSENT_REVOKED', '原许可已撤销。')
        self.require_current(conn, current, state, sources[turn_id])
        event = CodexDispatchQueued(kind='queued', dispatch_id='codexdispatch_'+uuid4().hex,
            consent_id=consent_id, start_command_sha256=command_sha256)
        now=utc_now()
        self.valid_at(state,now)
        envelope = CodexProviderRepository(conn, current.workspace_id).append(turn_id,event,now,state)
        return envelope, self.binding(state,envelope)

    @staticmethod
    def valid_at(state, now):
        if instant(now) >= instant(state.proposed.command.ack.summary.expires_at):
            raise ApiError(409,'CODEX_CONSENT_EXPIRED','原许可已到期，不能开始新的执行。')

    def require_current(self, conn, identity, state, source):
        view = self._current(conn,identity,state,source)
        if view.validity != 'current':
            raise ApiError(503 if view.validity == 'unavailable' else 409,
                'CODEX_INPUT_PROOF_UNAVAILABLE' if view.validity == 'unavailable' else
                'CODEX_CONSENT_EXPIRED' if view.validity == 'expired' else 'CODEX_SOURCE_CHANGED',
                '原外发许可当前不可开始。')

    @staticmethod
    def prepared_request(state):
        summary = state.proposed.command.ack.summary
        return PreparedCodexRequest(body=state.proposed.request_body.encode(),adapter_version=summary.adapter_version,
            input_character_count=summary.input_character_count,input_token_assurance=summary.input_token_assurance,
            cost_estimate=summary.cost_estimate,endpoint=summary.endpoint)

    def admit_execution(self, conn, workspace_id, turn_id, *, already_started=False):
        """Current authorization is distinct from owned historical fact reads."""
        states,sources = self.owned_states(conn,workspace_id)
        state = states.get(turn_id)
        if state is None or state.queued is None or state.granted is None:
            raise damaged()
        if state.finished is not None or (state.started is not None) != already_started:
            raise ApiError(409,'CODEX_OUTCOME_UNKNOWN','原派发不能重新开始。')
        current = author_execution_identity(conn,workspace_id,state.granted.command.actor_session_id)
        current_control_access(conn,current,write=True)
        if state.revoked_at is not None:
            raise ApiError(409,'CODEX_CONSENT_REVOKED','原外发许可已撤销。')
        self.require_current(conn,current,state,sources[turn_id])
        return state,current,self.prepared_request(state)

    def auth_snapshot(self, conn, identity, state) -> _CodexAuthSnapshot:
        """Read the named private secret port in the caller's start transaction.

        Admission still owns source/actor/proof/consent checks. This capture
        does not finalize a Rust request or register production capability.
        """
        if not conn.in_transaction or state.queued is None or state.started is not None:
            raise damaged()
        summary = state.proposed.command.ack.summary
        config = checked_provider_configuration(conn, identity, summary.provider_id)
        if config != state.proposed.material.input.provider:
            raise ApiError(409, 'PROVIDER_CONFIGURATION_CHANGED', '原提供商配置已改变。')
        providers = ProviderRepository(conn, identity.workspace_id)
        locator = providers.secret_locator(config.id, config.revision)
        if providers.backup_disabled() or locator is None:
            raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '原配置的秘密当前不可用。')
        secret = self.secrets.read(locator)
        return _CodexAuthSnapshot(identity.workspace_id, state.proposed.material.preparation.turn_id,
            state.queued.dispatch_id, config.id, config.revision, config.config_sha256, locator, secret)

    def verify_auth_snapshot(self, conn, identity, state, snapshot: _CodexAuthSnapshot) -> None:
        """Reduce a committed execution on rotation; never refresh frozen auth."""
        if not conn.in_transaction or state.queued is None or state.started is None:
            raise damaged()
        self._verify_auth_snapshot(conn, identity, state, snapshot)

    def verify_prepared_auth_snapshot(self, conn, identity, state, snapshot: _CodexAuthSnapshot) -> None:
        """Recheck a private memory capture before freeze, without recording start.

        This is not genuine InputProof or send admission. Existing committed
        execution callers keep the distinct post-start precondition above.
        """
        if not conn.in_transaction or state.queued is None or state.started is not None:
            raise damaged()
        self._verify_auth_snapshot(conn, identity, state, snapshot)

    def _verify_auth_snapshot(self, conn, identity, state, snapshot: _CodexAuthSnapshot) -> None:
        if type(snapshot) is not _CodexAuthSnapshot:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原执行的私有凭据绑定不一致。')
        summary = state.proposed.command.ack.summary
        binding = (identity.workspace_id, state.proposed.material.preparation.turn_id,
            state.queued.dispatch_id, summary.provider_id, summary.provider_revision, summary.config_sha256)
        if binding != (snapshot.workspace_id, snapshot.turn_id, snapshot.dispatch_id,
                snapshot.provider_id, snapshot.provider_revision, snapshot.config_sha256):
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原执行的私有凭据绑定不一致。')
        config = checked_provider_configuration(conn, identity, summary.provider_id)
        if config != state.proposed.material.input.provider:
            raise ApiError(409, 'PROVIDER_CONFIGURATION_CHANGED', '原提供商配置已改变。')
        providers = ProviderRepository(conn, identity.workspace_id)
        locator = providers.secret_locator(config.id, config.revision)
        if providers.backup_disabled() or locator is None or locator != snapshot.locator:
            raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '原冻结的提供商秘密不可用。')
        if not hmac.compare_digest(self.secrets.read(locator).encode('utf-8'), snapshot.secret.encode('utf-8')):
            raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '原冻结的提供商秘密不可用。')

    def record_start(self, conn, workspace_id, turn_id, state, lease, owner_id, now):
        """Persist possible-send consumption before any external boundary.

        The Codex coordinator adds its independent witness and claim control in
        this same transaction. No transport is performed by this record port.
        """
        self.valid_at(state,now)
        self.source.verify_dispatch_lease(conn,workspace_id,state.proposed.material.input.job_id,lease)
        event=CodexDispatchStarted(kind='started',dispatch_id=state.queued.dispatch_id,
            request_body_sha256=state.proposed.command.ack.summary.request_body_sha256,
            lease=lease,execution_owner_id=owner_id)
        envelope=CodexProviderRepository(conn,workspace_id).append(turn_id,event,now,state)
        return envelope,self.binding(state,envelope)

    def record_terminal(self, conn, workspace_id, turn_id, state, now, *, outcome, error_code,
                        execution_result=None, elapsed_ms=None):
        event=CodexDispatchFinished(kind='terminal',dispatch_id=state.queued.dispatch_id,
            outcome=outcome,error_code=error_code,answer=execution_result.answer if execution_result else '',
            usage=execution_result.usage if execution_result else UsageSnapshot(input_tokens=None,output_tokens=None),
            elapsed_ms=elapsed_ms,execution_result=execution_result)
        envelope=CodexProviderRepository(conn,workspace_id).append(turn_id,event,now,state)
        return envelope,self.binding(state,envelope)

    @staticmethod
    def _find(states, identifier, *, consent=False):
        for state in states.values():
            candidate = (state.granted.command.ack.id if state.granted else None) if consent else state.proposed.command.ack.id
            if candidate == identifier:
                return state
        raise missing()

    @staticmethod
    def _warnings(summary):
        return [ProposalWarning(code='price_unknown' if summary.cost_estimate.kind == 'unknown' else 'estimate_not_guaranteed',
            message='费用未知或仅为估算；不表示账单硬保证，输入、输出和单次请求限制仍有效。')]

    def preview(self, identity: SessionIdentity, body: CodexOutboundPreviewWrite, key: str) -> CodexConsentProposalView:
        return self._deliver(identity, self._preview(identity, body, key))

    def _preview(self, identity, body, key):
        key = validate_key(key)
        body = CodexOutboundPreviewWrite.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current = current_control_access(conn, identity, write=True)
            states, _ = self._states(conn, current)
            repo = CodexProviderRepository(conn, current.workspace_id)
            replay = repo.replay(states, current.id, 'preview', key, body)
            if replay is not None:
                return CodexConsentProposalView.model_validate(replay.model_dump())
            material = self.source.read_outbound_preparation(conn, current, body.preparation_id, body.expected_job_revision)
            if material.preparation.preparation_sha256 != body.preparation_sha256:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '外发预览必须对应原准备的确切摘要。')
            if material.preparation.turn_id in states:
                raise ApiError(409, 'CODEX_BINDING_INVALID', '原准备已存在唯一提案；不能换 key 重建。')
            config = checked_provider_configuration(conn, current, material.input.provider.id)
            if config.revision != body.expected_provider_revision:
                raise ApiError(412, 'PROVIDER_VERSION_CONFLICT', '提供商预览基准已改变。')
            if config != material.input.provider:
                raise ApiError(409, 'PROVIDER_CONFIGURATION_CHANGED', '原任务的提供商配置已改变。')
            now = utc_now()
            if not instant(now) < instant(body.expires_at) <= instant(now) + timedelta(minutes=10):
                raise ApiError(422, 'CONSENT_EXPIRY_INVALID', '新提案须在当前时间后十分钟内到期。')
            if not isinstance(material.input, RunnableTurnInput):
                raise unavailable()
            prepared = self.proofs.prepare(config, material.input.runtime, material.context.messages, material.context.evidence, body.budget)
            providers = ProviderRepository(conn, current.workspace_id)
            locator = providers.secret_locator(config.id, config.revision)
            if providers.backup_disabled() or locator is None or not self.secrets.available(locator):
                raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '原配置的秘密当前不可用。')
            source = material.preparation
            summary = CodexFrozenOutboundSummary(version='codex-outbound-summary-v1', preparation_id=source.id,
                preparation_sha256=source.preparation_sha256, session_id=source.session_id, turn_id=source.turn_id,
                job_id=source.job.id, source_job_revision=material.job_revision, source_input_sha256=source.summary.job_input_sha256,
                provider_id=config.id, provider_revision=config.revision, config_sha256=config.config_sha256,
                adapter='codex_app_server', adapter_version=prepared.adapter_version, endpoint=prepared.endpoint,
                endpoint_policy=config.endpoint_policy, model=config.model,
                context_snapshot_id=source.summary.context_snapshot_id, context_snapshot_sha256=source.summary.snapshot_sha256,
                input_sha256=source.summary.prepared_input_sha256, request_body_sha256=sha256_bytes(prepared.body),
                messages=[MessageSummary(role=x.role,character_count=len(x.content),content_sha256=sha256_bytes(x.content.encode())) for x in material.context.messages],
                references=source.summary.materials, input_character_count=prepared.input_character_count,
                input_token_assurance=prepared.input_token_assurance, budget=body.budget, tools=source.request.tools,
                runtime=source.summary.runtime,cost_estimate=prepared.cost_estimate,created_at=now,expires_at=body.expires_at)
            view = CodexConsentProposalView(id='codexproposal_'+uuid4().hex,
                proposal_sha256=content_sha256({'version':'codex-consent-proposal-v1','workspace_id':current.workspace_id,
                    'actor_session_id':current.id,'summary':summary.model_dump(mode='json')}),
                summary=summary,validity='current',consent_id=None,warnings=self._warnings(summary))
            event = CodexProposed(kind='proposed',material=material,request_body=prepared.body.decode('utf-8'),
                command=CodexPreviewCommand(route='preview',actor_session_id=current.id,key=key,body=body,ack=view))
            envelope = repo.append(source.turn_id,event,now,None)
            self._bind(conn,current,None,envelope)
            self._states(conn,current)
            current_control_access(conn,current,write=True)
            return view

    def _current(self, conn, identity, state, source):
        original, material = state.proposed.command.ack, state.proposed.material
        summary = original.summary
        config = checked_provider_configuration(conn,identity,summary.provider_id)
        validity = 'current'
        if config != material.input.provider or source.control.execution == 'terminal' or not self.source.current_outbound_material(conn,identity,material):
            validity = 'stale'
        else:
            try:
                if not isinstance(material.input,RunnableTurnInput):
                    raise unavailable()
                frozen = PreparedCodexRequest(body=state.proposed.request_body.encode(),adapter_version=summary.adapter_version,
                    input_character_count=summary.input_character_count,input_token_assurance=summary.input_token_assurance,
                    cost_estimate=summary.cost_estimate,endpoint=summary.endpoint)
                self.proofs.verify(config,material.input.runtime,material.context.messages,material.context.evidence,summary.budget,frozen)
                providers = ProviderRepository(conn,identity.workspace_id)
                locator = providers.secret_locator(config.id,config.revision)
                if providers.backup_disabled() or locator is None or not self.secrets.available(locator):
                    validity = 'unavailable'
            except ApiError as error:
                if error.code not in {'CODEX_INPUT_PROOF_UNAVAILABLE','CODEX_PROFILE_CHANGED'}:
                    raise
                validity = 'unavailable' if error.code=='CODEX_INPUT_PROOF_UNAVAILABLE' else 'stale'
        if instant(utc_now()) >= instant(summary.expires_at):
            validity = 'expired'
        return CodexConsentProposalView.model_validate({**original.model_dump(),'validity':validity,
            'consent_id':state.granted.command.ack.id if state.granted else None})

    def proposal(self, identity, identifier):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current = current_control_access(conn,identity,write=True)
            states,sources = self._states(conn,current)
            state = self._find(states,identifier)
            result = self._current(conn,current,state,sources[state.proposed.material.preparation.turn_id])
        return self._deliver(identity,result)

    def grant(self, identity, body, key):
        return self._deliver(identity,self._grant(identity,body,key))

    def _grant(self, identity, body, key):
        key=validate_key(key)
        body=CodexConsentCreateWrite.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current=current_control_access(conn,identity,write=True)
            states,sources=self._states(conn,current)
            repo=CodexProviderRepository(conn,current.workspace_id)
            replay=repo.replay(states,current.id,'grant',key,body)
            if replay is not None:
                return CodexConsentCreateAck.model_validate(replay.model_dump())
            state=self._find(states,body.proposal_id)
            original=state.proposed.command.ack
            if state.proposed.command.actor_session_id!=current.id:
                raise ApiError(403,'POLICY_DENIED','新操作者不能接管原外发批准。')
            if body.proposal_sha256!=original.proposal_sha256:
                raise ApiError(412,'PROPOSAL_VERSION_CONFLICT','批准须对应原提案摘要。')
            if state.granted is not None:
                raise ApiError(409,'CODEX_BINDING_INVALID','原提案已有唯一许可。')
            source=sources[original.summary.turn_id]
            view=self._current(conn,current,state,source)
            if view.validity!='current':
                raise ApiError(503 if view.validity=='unavailable' else 409,
                    'CODEX_INPUT_PROOF_UNAVAILABLE' if view.validity=='unavailable' else
                    'CODEX_CONSENT_EXPIRED' if view.validity=='expired' else 'CODEX_SOURCE_CHANGED',
                    '原外发提案当前不可批准。')
            ack=CodexConsentCreateAck(id='codexconsent_'+uuid4().hex,revision=1,status='active',actor_session_id=current.id,
                proposal_id=original.id,proposal_sha256=original.proposal_sha256,summary=original.summary)
            now=utc_now()
            if instant(now) >= instant(original.summary.expires_at):
                raise ApiError(409,'CODEX_CONSENT_EXPIRED','原外发提案已到期，不能批准。')
            event=CodexGranted(kind='granted',command=CodexGrantCommand(route='grant',actor_session_id=current.id,key=key,body=body,ack=ack))
            envelope=repo.append(original.summary.turn_id,event,now,state)
            self._bind(conn,current,state,envelope)
            self._states(conn,current)
            current_control_access(conn,current,write=True)
            return ack

    def consent(self, identity, identifier):
        with self.database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            current=current_control_access(conn,identity,write=True)
            states,sources=self._states(conn,current)
            state=self._find(states,identifier,consent=True)
            result=state.consent_view(utc_now(),sources[state.proposed.material.preparation.turn_id].control.job)
        return self._deliver(identity,result)

    def revoke(self, identity, identifier, body, key):
        return self._deliver(identity,self._revoke(identity,identifier,body,key),subject=False)

    def _revoke(self, identity, identifier, body, key):
        key=validate_key(key)
        body=ConsentRevoke.model_validate(body.model_dump(mode='json'))
        with self.database.transaction() as conn:
            current=current_control_access(conn,identity,write=False)
            states,_=self._states(conn,current)
            repo=CodexProviderRepository(conn,current.workspace_id)
            # The target is part of the complete replay comparison too.
            replay=repo.replay(states,current.id,'revoke',key,body)
            if replay is not None:
                if replay.id!=identifier:
                    raise ApiError(409,'IDEMPOTENCY_CONFLICT','原 key 不属于本许可。')
                return dm.MutationAck.model_validate(replay.model_dump())
            state=self._find(states,identifier,consent=True)
            if body.expected_revision!=state.revision:
                raise ApiError(412,'REVISION_MISMATCH','许可修订已改变。')
            applied=state.revoked_at is None
            ack=dm.MutationAck(id=identifier,revision=2,applied=applied)
            event=CodexRevoked(kind='revoked' if applied else 'revoke_observed',
                command=CodexRevokeCommand(route='revoke',actor_session_id=current.id,key=key,body=body,ack=ack))
            envelope=repo.append(state.proposed.material.preparation.turn_id,event,utc_now(),state)
            self._bind(conn,current,state,envelope)
            self._states(conn,current)
            current_control_access(conn,current,write=False)
            return ack
