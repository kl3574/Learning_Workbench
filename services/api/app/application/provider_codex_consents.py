"""Provider-owned Codex proposals/grants; no ordinary text-adapter fallback."""
from datetime import timedelta
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
from ..infrastructure.security import SessionIdentity
from ..serialization import content_sha256
from .codex_bootstrap_access import current_control_access
from .codex_turn_context import damaged
from .codex_turn_models import TurnProviderBound
from .codex_turn_execution_models import RunnableTurnInput
from .errors import ApiError
from .provider_budget import ProofRegistry
from .provider_codex_models import CodexProposed, CodexGranted, CodexRevoked, CodexPreviewCommand, CodexGrantCommand, CodexRevokeCommand
from .provider_codex_ports import CodexOutboundSourcePort
from .provider_codex_profile import PreparedCodexRequest, unavailable
from .providers import checked_provider_configuration, validate_key


def missing() -> ApiError:
    return ApiError(404, 'REFERENCE_MISSING', '本工作区没有此 Codex 外发记录。')


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

    def verify_links(self, conn, identity, sources):
        states = CodexProviderRepository(conn, identity.workspace_id).checked()
        self._verify_links(states, sources)
        return {turn: state.consent_control(utc_now()) for turn, state in states.items()}

    @staticmethod
    def _verify_links(states, sources):
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

    def _bind(self, conn, identity, state, envelope):
        # The Provider fact and the consumer's independent witness commit together.
        if isinstance(envelope.event, CodexProposed):
            proposal, grant, revoked = envelope.event.command.ack.id, None, False
        else:
            proposal = state.proposed.command.ack.id
            grant = (envelope.event.command.ack if isinstance(envelope.event, CodexGranted)
                     else state.granted.command.ack if state.granted else None)
            revoked = isinstance(envelope.event, CodexRevoked) or state.revoked_at is not None
        event = TurnProviderBound(kind='provider_bound', turn_id=envelope.turn_id,
            provider_seq=envelope.seq, provider_sha256=content_sha256(envelope), proposal_id=proposal,
            consent_id=grant.id if grant else None, consent_revision=(2 if revoked else 1) if grant else None,
            consent_status=('revoked' if revoked else 'active') if grant else None)
        self.source.bind_outbound_event(conn, identity, event, envelope.occurred_at)

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
