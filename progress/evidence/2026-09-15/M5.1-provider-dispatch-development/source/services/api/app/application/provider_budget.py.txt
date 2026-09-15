"""Local complete-input admission. Registrations are code-reviewed trust inputs.

There are deliberately no production registrations. A proof is not an arbitrary
hash or a text tokenizer: registration includes the immutable evidence bytes,
its exact model/shape/capacity scope, and the reviewed complete-request checker.
No remote counting, fallback token estimate, or silent truncation occurs here.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
import math
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..provider_dto import (
    CostEstimate, EstimatedCostEstimate, FrozenOutboundBudget, FrozenOutboundSummary,
    LocalExactInputTokens, LocalUpperBoundInputTokens, ProviderAdapter, ProviderConfigView,
    UnknownCostEstimate,
)
from .errors import ApiError
from .provider_models import PreparedOutboundMaterial, UsageSnapshot
from .provider_ports import PreparedProviderRequest

ADAPTER_VERSION = 'text-request-v1'
INPUT_SHAPE = 'text-messages-with-delimited-evidence-v1'


def unsupported() -> ApiError:
    return ApiError(409, 'CAPABILITY_UNSUPPORTED', '此模型没有可用的完整输入计量依据。')


def budget_exceeded() -> ApiError:
    return ApiError(409, 'OUTBOUND_BUDGET_EXCEEDED', '此请求超过已冻结的调用预算。')


@dataclass(frozen=True)
class InputProof:
    """Explicit trusted registration, never accepted from HTTP/configuration.

    `evidence` contains the actual reviewed basis, including formatting rules and
    validity conditions. `check` must reject every shape outside that basis. The
    registry authenticates binding; it cannot invent mathematical validity for
    a caller-supplied checker. Only application construction can install one.
    """
    model: str
    adapter: ProviderAdapter
    checker_version: str
    kind: Literal['local_exact', 'local_upper_bound']
    max_input_tokens: int
    max_output_tokens: int
    shared_context_tokens: int | None
    evidence: bytes = field(repr=False)
    check: Callable[[bytes], int] = field(repr=False, compare=False)
    adapter_version: str = ADAPTER_VERSION
    input_shape: str = INPUT_SHAPE

    @property
    def sha256(self) -> str:
        return sha256_bytes(canonical_bytes({
            'model': self.model, 'adapter': self.adapter, 'adapter_version': self.adapter_version,
            'input_shape': self.input_shape, 'checker_version': self.checker_version,
            'kind': self.kind, 'max_input_tokens': self.max_input_tokens,
            'max_output_tokens': self.max_output_tokens, 'shared_context_tokens': self.shared_context_tokens,
            'evidence_sha256': sha256_bytes(self.evidence),
        }))


class ProofRegistry:
    def __init__(self, proofs: Iterable[InputProof] = ()):
        self._proofs: dict[tuple[str, str], InputProof] = {}
        for proof in proofs:
            key = (proof.adapter, proof.model)
            if (key in self._proofs or not proof.evidence or not proof.checker_version.strip()
                    or proof.adapter_version != ADAPTER_VERSION or proof.input_shape != INPUT_SHAPE
                    or proof.kind not in {'local_exact', 'local_upper_bound'}
                    or type(proof.max_input_tokens) is not int or proof.max_input_tokens <= 0
                    or type(proof.max_output_tokens) is not int or proof.max_output_tokens <= 0
                    or (proof.shared_context_tokens is not None and
                        (type(proof.shared_context_tokens) is not int or proof.shared_context_tokens <= 0))):
                raise ValueError('Invalid or duplicate complete-input proof registration.')
            self._proofs[key] = proof

    def resolve(self, config: ProviderConfigView) -> InputProof:
        proof = self._proofs.get((config.adapter, config.model))
        if proof is None:
            raise unsupported()
        return proof


def input_bound(assurance: LocalExactInputTokens | LocalUpperBoundInputTokens) -> int:
    return (assurance.input_tokens if isinstance(assurance, LocalExactInputTokens)
            else assurance.input_tokens_upper_bound)


def check_usage(usage: UsageSnapshot, assurance: LocalExactInputTokens | LocalUpperBoundInputTokens,
                budget: FrozenOutboundBudget) -> None:
    if ((usage.input_tokens is not None and usage.input_tokens > min(input_bound(assurance), budget.max_input_tokens))
            or (usage.output_tokens is not None and usage.output_tokens > budget.max_output_tokens)):
        raise budget_exceeded()


def cost_estimate(config: ProviderConfigView, bound: int, budget: FrozenOutboundBudget) -> CostEstimate:
    pricing = config.pricing
    if pricing is None:
        return UnknownCostEstimate(kind='unknown', currency='USD')
    amount = (Decimal(str(pricing.input_usd_per_million)) * bound
              + Decimal(str(pricing.output_usd_per_million)) * budget.max_output_tokens) / Decimal(1000000)
    if budget.max_cost_usd is not None and amount > Decimal(str(budget.max_cost_usd)):
        raise budget_exceeded()
    value = float(amount)
    # Public DTO uses JSON numbers; never round a computed upper estimate down.
    if Decimal.from_float(value) < amount:
        value = math.nextafter(value, math.inf)
    if not math.isfinite(value):
        raise budget_exceeded()
    return EstimatedCostEstimate(kind='estimated', currency='USD', maximum_estimated_cost=value,
        pricing_sha256=sha256_bytes(canonical_bytes({
            'version': 'provider-pricing-v1', 'provider_id': config.id,
            'provider_revision': config.revision, 'pricing': pricing.model_dump(mode='json')})))


class RequestPreparer:
    def __init__(self, registry: ProofRegistry | None = None):
        self.registry = registry if registry is not None else ProofRegistry()

    def capabilities(self, config: ProviderConfigView, secret_available: bool) -> dm.ProviderCapabilities:
        try:
            proof = self.registry.resolve(config)
        except ApiError:
            enabled, version = False, 'MODEL_NOT_REGISTERED'
        else:
            enabled = config.secret_present and secret_available
            version = proof.sha256 if enabled else 'PROVIDER_SECRET_UNAVAILABLE'
        return dm.ProviderCapabilities(provider_id=config.id, configured=config.configured,
            chat=enabled, streaming=enabled, structured_output=False, web_search=False,
            tool_calls=False, version_evidence=version)

    def prepare(self, config: ProviderConfigView, material: PreparedOutboundMaterial,
                budget: FrozenOutboundBudget) -> PreparedProviderRequest:
        proof = self.registry.resolve(config)
        if material.purpose not in {'tutor', 'authoring'}:
            raise unsupported()
        if len(material.messages) > 6 or len(material.evidence) > 8:
            raise budget_exceeded()
        messages = [item.model_dump(mode='json') for item in material.messages]
        # Evidence is data in an explicit user message, never an instruction role.
        # The entire delimiter/locator text is frozen and counted by the proof.
        for item in material.evidence:
            messages.append({'role': 'user', 'content': '<reference>\n' + canonical_bytes({
                'ref': item.ref.model_dump(mode='json'), 'locator': item.locator, 'text': item.text,
            }).decode() + '\n</reference>'})
        characters = sum(len(item['content']) for item in messages)
        if characters > 12000:
            raise budget_exceeded()
        body_object: dict[str, object] = {'model': config.model, 'stream': True}
        if config.adapter == 'official_responses':
            body_object.update(input=messages, max_output_tokens=budget.max_output_tokens,
                               truncation='disabled', store=False)
        else:
            body_object.update(messages=messages, max_completion_tokens=budget.max_output_tokens,
                               n=1, stream_options={'include_usage': True})
        body = canonical_bytes(body_object)
        try:
            bound = proof.check(body)
        except (ValueError, TypeError, KeyError):
            raise unsupported() from None
        if type(bound) is not int or bound < 0:
            raise unsupported()
        if (bound > budget.max_input_tokens or bound > proof.max_input_tokens
                or budget.max_output_tokens > proof.max_output_tokens
                or (proof.shared_context_tokens is not None
                    and bound + budget.max_output_tokens > proof.shared_context_tokens)):
            raise budget_exceeded()
        digest = sha256_bytes(body)
        assurance: LocalExactInputTokens | LocalUpperBoundInputTokens
        if proof.kind == 'local_exact':
            assurance = LocalExactInputTokens(kind='local_exact', input_tokens=bound,
                checker_version=proof.checker_version, proof_sha256=proof.sha256, request_body_sha256=digest)
        else:
            assurance = LocalUpperBoundInputTokens(kind='local_upper_bound', input_tokens_upper_bound=bound,
                checker_version=proof.checker_version, proof_sha256=proof.sha256, request_body_sha256=digest)
        return PreparedProviderRequest(body=body, adapter_version=ADAPTER_VERSION,
            input_character_count=characters, input_token_assurance=assurance,
            cost_estimate=cost_estimate(config, bound, budget))

    def verify(self, config: ProviderConfigView, material: PreparedOutboundMaterial,
               summary: FrozenOutboundSummary, body: bytes) -> None:
        prepared = self.prepare(config, material, summary.budget)
        if (summary.provider_id != config.id or summary.provider_revision != config.revision
                or summary.config_sha256 != config.config_sha256 or summary.adapter != config.adapter
                or summary.base_url != config.base_url or summary.endpoint_policy != config.endpoint_policy
                or summary.model != config.model or summary.job_id != material.job_id
                or summary.source_input_sha256 != material.job_input_sha256
                or summary.input_sha256 != material.prepared_input_sha256
                or summary.context_snapshot_id != material.context_snapshot.id
                or summary.context_snapshot_sha256 != material.context_snapshot.snapshot_sha256
                or summary.purpose != material.purpose
                or prepared.body != body or prepared.adapter_version != summary.adapter_version
                or prepared.input_character_count != summary.input_character_count
                or prepared.input_token_assurance != summary.input_token_assurance
                or prepared.cost_estimate != summary.cost_estimate):
            raise ApiError(409, 'OUTBOUND_SOURCE_CHANGED', '实际请求与冻结摘要不一致。')
        # Guard against a permissive parser or accidental late request extension.
        if canonical_bytes(strict_json(body)) != body:
            raise unsupported()
