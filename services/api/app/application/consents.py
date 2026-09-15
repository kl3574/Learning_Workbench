"""Server-frozen approval, current projections and safe control revocation."""

import base64
import hashlib
import hmac
import math
import secrets
import sqlite3
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..infrastructure.consent_repository import ConsentRepository, instant, prepared_digest
from ..infrastructure.database import Database, utc_now
from ..infrastructure.provider_repository import ProviderRepository, command_id, digest, integrity_error
from ..infrastructure.provider_secret_store import SecretStore
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..provider_dto import (
    ConsentCreate, ConsentCreateAck, ConsentDispatchView, ConsentPage, ConsentPreviewWrite,
    ConsentProposalView, ConsentRevoke, ConsentView, FrozenOutboundBudget, FrozenOutboundSummary,
    EstimatedUsageCost, MessageSummary, ProposalWarning, ProviderUsageView, UnknownUsageCost, UsageCost,
)
from .errors import ApiError
from .provider_ports import OutboundSourceRegistry, ProviderRequestPreparer, SourcePreparationChanged
from .providers import ProviderService, identifier, validate_key


class ConsentsService:
    def __init__(self, database: Database, secret_store: SecretStore,
                 source_registry: OutboundSourceRegistry, preparer: ProviderRequestPreparer):
        self.database = database
        self.secret_store = secret_store
        self.source_registry = source_registry
        self.preparer = preparer
        self._providers = ProviderService(database, secret_store, preparer)
        self._cursor_key = secrets.token_bytes(32)

    def _fingerprint(self, identity: SessionIdentity, route: str, key: str, request: object) -> str:
        return self._providers._fingerprint(identity, route, key, request)

    @staticmethod
    def _warnings(summary: FrozenOutboundSummary) -> list[ProposalWarning]:
        return [ProposalWarning(code='price_unknown' if summary.cost_estimate.kind == 'unknown' else 'estimate_not_guaranteed',
            message='费用未知，金额没有硬保证；仍执行输入、输出和调用次数限制。' if summary.cost_estimate.kind == 'unknown'
                    else '按本机价格估算费用，不表示提供商账单或金额硬保证。')]

    def preview(self, identity: SessionIdentity, request: ConsentPreviewWrite, key: str | None) -> ConsentProposalView:
        key = validate_key(key)
        request = ConsentPreviewWrite.model_validate(request.model_dump(mode='json'))
        route = 'POST /consents/preview'
        fingerprint = self._fingerprint(identity, route, key, request)
        with self.database.transaction() as connection:
            guard_subject_access(connection, identity.workspace_id)
            providers = ProviderRepository(connection, identity.workspace_id)
            repo = ConsentRepository(connection, identity.workspace_id)
            providers.require_workspace()
            previous = providers.replay(route, key, fingerprint, ConsentProposalView)
            if previous is not None:
                repo.proposal(previous.id)
                return previous
            now = utc_now()
            if instant(request.expires_at) <= instant(now):
                raise ApiError(422, 'CONSENT_EXPIRY_INVALID', '新提案的到期时间必须晚于当前服务端时间。')
            config = providers.config(request.provider_id)
            if config.revision != request.expected_provider_revision:
                raise ApiError(412, 'PROVIDER_VERSION_CONFLICT', '提供商预览基准已改变。')
            source = self.source_registry.resolve(connection, identity, request.job_id)
            material = source.read_prepared(connection, identity, request.job_id, request.expected_job_revision)
            if material.purpose not in {'tutor', 'authoring'}:
                raise ApiError(409, 'CAPABILITY_UNSUPPORTED', '本阶段不支持该外发目的。')
            if prepared_digest(identity.workspace_id, material) != material.prepared_input_sha256:
                raise integrity_error()
            locator = providers.secret_locator(config.id, config.revision)
            if locator is None or not self.secret_store.available(locator):
                raise ApiError(409, 'PROVIDER_SECRET_UNAVAILABLE', '提供商秘密不可用。')
            budget = FrozenOutboundBudget.model_validate(request.budget.model_dump(mode='json'))
            prepared = self.preparer.prepare(config, material, budget)
            if sha256_bytes(prepared.body) != prepared.input_token_assurance.request_body_sha256:
                raise integrity_error()
            summary = FrozenOutboundSummary(job_id=material.job_id, source_job_revision=material.job_revision,
                source_input_sha256=material.job_input_sha256, purpose=material.purpose,
                provider_id=config.id, provider_revision=config.revision, config_sha256=config.config_sha256,
                adapter=config.adapter, adapter_version=prepared.adapter_version, base_url=config.base_url,
                endpoint_policy=config.endpoint_policy, model=config.model,
                context_snapshot_id=material.context_snapshot.id, context_snapshot_sha256=material.context_snapshot.snapshot_sha256,
                input_sha256=material.prepared_input_sha256,
                messages=[MessageSummary(role=x.role, character_count=len(x.content), content_sha256=sha256_bytes(x.content.encode()))
                          for x in material.messages], references=source.reference_summaries(connection, identity, material),
                input_character_count=prepared.input_character_count, input_token_assurance=prepared.input_token_assurance,
                allow_web=False, budget=budget, cost_estimate=prepared.cost_estimate, created_at=now, expires_at=request.expires_at)
            self.preparer.verify(config, material, summary, prepared.body)
            proposal_id = 'proposal_' + uuid4().hex
            view = ConsentProposalView(id=proposal_id, proposal_sha256=digest({'version': 'outbound-proposal-v1',
                'workspace_id': identity.workspace_id, 'id': proposal_id, 'summary': summary.model_dump(mode='json')}),
                summary=summary, validity='current', consent_id=None, warnings=self._warnings(summary))
            cid = command_id()
            repo.add_proposal(view, material, prepared.body, cid)
            providers.record_command(cid, route, key, request, fingerprint, view)
            return view

    def _current(self, connection: sqlite3.Connection, identity: SessionIdentity, proposal_id: str) -> ConsentProposalView:
        repo = ConsentRepository(connection, identity.workspace_id)
        view, material, body = repo.proposal_material(proposal_id)
        providers = ProviderRepository(connection, identity.workspace_id)
        config = providers.config(view.summary.provider_id)
        warnings = self._warnings(view.summary)
        changed = config.revision != view.summary.provider_revision or config.config_sha256 != view.summary.config_sha256
        source_changed = False
        unavailable = False
        try:
            source = self.source_registry.resolve(connection, identity, material.job_id)
        except ApiError as error:
            if error.code != 'OUTBOUND_SOURCE_UNAVAILABLE' or error.status != 409:
                raise
            source = None
            unavailable = True
            warnings.append(ProposalWarning(code='source_unavailable', message='原任务当前没有已注册的外发准备来源，不能批准或派发。'))
        try:
            if source is not None:
                source.verify_prepared(connection, identity, material)
        except SourcePreparationChanged:
            source_changed = True
            warnings.append(ProposalWarning(code='source_changed', message='来源已确认发布新的准备版本，需要重新预览。'))
        except ApiError as error:
            if error.code != 'OUTBOUND_SOURCE_UNAVAILABLE':
                raise  # Unknown integrity is not an apparently valid stale projection.
            unavailable = True
            warnings.append(ProposalWarning(code='job_unavailable', message='原任务当前不在可授权或运行阶段。'))
        if changed:
            warnings.append(ProposalWarning(code='provider_changed', message='提供商配置已变化，需要重新预览。'))
        else:
            locator = providers.secret_locator(config.id, config.revision)
            try:
                if locator is None or not self.secret_store.available(locator) or providers.backup_disabled():
                    raise ApiError(409, 'CAPABILITY_UNSUPPORTED', '配置不可调度。')
                self.preparer.verify(config, material, view.summary, body)
            except ApiError as error:
                if error.code not in {'CAPABILITY_UNSUPPORTED', 'PROVIDER_SECRET_UNAVAILABLE'}:
                    raise
                unavailable = True
                warnings.append(ProposalWarning(code='capability_unavailable', message='当前秘密或完整输入证明不可用于派发。'))
        validity = 'current'
        if instant(view.summary.expires_at) <= instant(utc_now()):
            validity = 'expired'
            warnings.append(ProposalWarning(code='proposal_expired', message='原提案已到期。'))
        elif changed or source_changed:
            validity = 'stale'
        elif unavailable:
            validity = 'unavailable'
        return view.model_copy(update={'validity': validity, 'warnings': warnings})

    def proposal(self, identity: SessionIdentity, proposal_id: str) -> ConsentProposalView:
        identifier(proposal_id)
        with self.database.transaction() as connection:
            guard_subject_access(connection, identity.workspace_id)
            return self._current(connection, identity, proposal_id)

    def grant(self, identity: SessionIdentity, request: ConsentCreate, key: str | None) -> ConsentCreateAck:
        key = validate_key(key)
        request = ConsentCreate.model_validate(request.model_dump(mode='json'))
        route = 'POST /consents'
        fingerprint = self._fingerprint(identity, route, key, request)
        with self.database.transaction() as connection:
            guard_subject_access(connection, identity.workspace_id)
            providers = ProviderRepository(connection, identity.workspace_id)
            repo = ConsentRepository(connection, identity.workspace_id)
            providers.require_workspace()
            previous = providers.replay(route, key, fingerprint, ConsentCreateAck)
            if previous is not None:
                repo.consent(previous.id, previous.revision)
                return previous
            original = repo.proposal(request.proposal_id)
            if original.proposal_sha256 != request.proposal_sha256:
                raise ApiError(412, 'PROPOSAL_VERSION_CONFLICT', '批准必须对应原提案的确切摘要。')
            if original.consent_id is not None:
                raise ApiError(409, 'CONSENT_ALREADY_GRANTED', '此提案已批准，重新授权需要新预览。')
            view = self._current(connection, identity, request.proposal_id)
            if view.validity != 'current':
                raise ApiError(409, 'CONSENT_EXPIRED' if view.validity == 'expired' else
                    ('PROVIDER_CONFIGURATION_CHANGED' if any(w.code == 'provider_changed' for w in view.warnings)
                     else 'OUTBOUND_SOURCE_CHANGED') if view.validity == 'stale' else
                    ('OUTBOUND_SOURCE_UNAVAILABLE' if any(w.code == 'source_unavailable' for w in view.warnings)
                     else 'CAPABILITY_UNSUPPORTED'),
                    '当前提案已不可批准，请查看诊断并重新预览。')
            _, material, _ = repo.proposal_material(view.id)
            source = self.source_registry.resolve(connection, identity, material.job_id)
            source.verify_prepared(connection, identity, material)
            consent_id = 'consent_' + uuid4().hex
            cid = command_id()
            repo.append_consent(consent_id, view.id, cid, utc_now())
            source.bind_authorization(connection, identity, material.job_id, material.prepared_input_sha256, consent_id)
            ack = ConsentCreateAck(id=consent_id, revision=1, status='active', proposal_id=view.id,
                                   proposal_sha256=view.proposal_sha256, summary=view.summary)
            providers.record_command(cid, route, key, request, fingerprint, ack)
            return ack

    def revoke(self, identity: SessionIdentity, consent_id: str, request: ConsentRevoke, key: str | None) -> dm.MutationAck:
        identifier(consent_id)
        key = validate_key(key)
        request = ConsentRevoke.model_validate(request.model_dump(mode='json'))
        route = f'POST /consents/{consent_id}/revoke'
        fingerprint = self._fingerprint(identity, route, key, request)
        with self.database.transaction() as connection:
            providers = ProviderRepository(connection, identity.workspace_id)
            repo = ConsentRepository(connection, identity.workspace_id)
            providers.require_workspace()
            previous = providers.replay(route, key, fingerprint, dm.MutationAck)
            if previous is not None:
                repo.consent(consent_id, previous.revision)
                return previous
            current = repo.consent(consent_id)
            cid = command_id()
            revision = repo.append_consent(consent_id, current['proposal_id'], cid, utc_now(), expected_revision=request.expected_revision)
            ack = dm.MutationAck(id=consent_id, revision=revision, applied=revision != current['revision'])
            providers.record_command(cid, route, key, request, fingerprint, ack)
            return ack

    def _view(self, connection: sqlite3.Connection, identity: SessionIdentity, consent_id: str) -> ConsentView:
        repo = ConsentRepository(connection, identity.workspace_id)
        row = repo.consent(consent_id)
        proposal = self._current(connection, identity, row['proposal_id'])
        dispatch = repo.dispatch_for_consent(consent_id)
        dispatch_view = None
        if dispatch is not None:
            source = self.source_registry.resolve(connection, identity, proposal.summary.job_id)
            job = source.read_job(connection, identity, proposal.summary.job_id)
            usage = repo.usage(dispatch.id)
            receipt = dispatch.terminal
            error_code = None
            if receipt is not None:
                term = receipt.terminal
                if term.type == 'error':
                    error_code = term.error_code
                elif term.outcome != 'complete':
                    error_code = 'PROVIDER_REFUSAL' if term.outcome == 'refused' else 'PROVIDER_INCOMPLETE'
            elapsed = int((instant(receipt.recorded_at) - instant(dispatch.started_at)).total_seconds() * 1000) if receipt else None
            dispatch_view = ConsentDispatchView(id=dispatch.id, job=job, started_at=dispatch.started_at,
                finished_at=receipt.recorded_at if receipt else None, error_code=error_code,
                usage=ProviderUsageView(consumed_provider_calls=1, search_calls=0, tool_calls=0,
                    input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                    elapsed_ms=elapsed, cost=self._usage_cost(connection, identity, proposal.summary,
                                                             usage.input_tokens, usage.output_tokens)))
        status: Literal['active', 'revoked', 'expired'] = 'revoked' if row['status'] == 'revoked' else ('expired' if instant(proposal.summary.expires_at) <= instant(utc_now()) else 'active')
        return ConsentView(id=consent_id, revision=row['revision'], status=status,
            proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256, summary=proposal.summary,
            created_at=row['created_at'], expires_at=proposal.summary.expires_at, revoked_at=row['revoked_at'], dispatch=dispatch_view)

    @staticmethod
    def _usage_cost(connection: sqlite3.Connection, identity: SessionIdentity, summary: FrozenOutboundSummary,
                    input_tokens: int | None, output_tokens: int | None) -> UsageCost:
        config = ProviderRepository(connection, identity.workspace_id).config(summary.provider_id, summary.provider_revision)
        pricing = config.pricing
        if pricing is None or input_tokens is None or output_tokens is None:
            return UnknownUsageCost(kind='unknown', currency='USD')
        amount = (Decimal(str(pricing.input_usd_per_million)) * input_tokens
                  + Decimal(str(pricing.output_usd_per_million)) * output_tokens) / Decimal(1000000)
        value = float(amount)
        if Decimal.from_float(value) < amount:
            value = math.nextafter(value, math.inf)
        if not math.isfinite(value):
            return UnknownUsageCost(kind='unknown', currency='USD')
        return EstimatedUsageCost(kind='estimated', currency='USD', amount=value, pricing_sha256=digest({
            'version': 'provider-pricing-v1', 'provider_id': config.id, 'provider_revision': config.revision,
            'pricing': pricing.model_dump(mode='json')}))

    def page(self, identity: SessionIdentity, *, consent_id: str | None = None, cursor: str | None = None,
             limit: int = 20) -> ConsentPage:
        if type(limit) is not int or not 1 <= limit <= 100 or consent_id is not None and cursor is not None:
            raise ApiError(422, 'SCHEMA_INVALID', '授权查询范围或分页字段无效。')
        if consent_id is not None:
            identifier(consent_id)
        with self.database.transaction() as connection:
            guard_subject_access(connection, identity.workspace_id)
            repo = ConsentRepository(connection, identity.workspace_id)
            repo.providers.require_workspace()
            if consent_id is not None:
                return ConsentPage(items=[self._view(connection, identity, consent_id)], next_cursor=None, total_hint=1)
            items = [self._view(connection, identity, item) for item in repo.consent_ids()]
            items.sort(key=lambda item: (item.created_at, item.id), reverse=True)
            context = {'workspace_id': identity.workspace_id, 'limit': limit}
            if cursor is not None:
                try:
                    decoded = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
                    if not hmac.compare_digest(decoded[:32], hmac.new(self._cursor_key, decoded[32:], hashlib.sha256).digest()):
                        raise ValueError('signature')
                    value = strict_json(decoded[32:])
                    if not isinstance(value, dict) or set(value) != {'workspace_id', 'limit', 'created_at', 'id'} or any(value[k] != v for k, v in context.items()):
                        raise ValueError('context')
                    boundary = (value['created_at'], value['id'])
                    items = [item for item in items if (item.created_at, item.id) < boundary]
                except (ValueError, TypeError, KeyError):
                    raise ApiError(422, 'CURSOR_INVALID', '授权分页游标无效或不属于本次查询。') from None
            selected = items[:limit]
            next_cursor = None
            if len(items) > limit:
                last = selected[-1]
                data = canonical_bytes({**context, 'created_at': last.created_at, 'id': last.id})
                next_cursor = base64.urlsafe_b64encode(hmac.new(self._cursor_key, data, hashlib.sha256).digest() + data).decode().rstrip('=')
            return ConsentPage(items=selected, next_cursor=next_cursor, total_hint=len(items))
