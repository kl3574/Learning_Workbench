"""Closed M5.1 wire models from PRODUCT_DESIGN.md v3.0.2, appendix A.

These models check shape and local relationships. The Provider owner must also
verify source/receipt hashes, current time, Policy, safe summaries, endpoint
policy and immutable history. A valid model is not proof or authorization.
Secret input is write-only; handlers must never echo validation input or bodies.
"""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints, field_validator, model_validator
from pydantic.config import JsonDict
from pydantic.json_schema import SkipJsonSchema

from packages.contracts import domain_models as dm


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError('a nonblank string is required')
    return value


def _integer_literal(value: object) -> object:
    if type(value) is not int:
        raise ValueError('an integer literal is required')
    return value


def _boolean_literal(value: object) -> object:
    if type(value) is not bool:
        raise ValueError('a boolean literal is required')
    return value


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + '+00:00')


def _omit_schema_default(schema: JsonDict) -> None:
    schema.pop('default', None)


NonEmpty = Annotated[str, StringConstraints(min_length=1), AfterValidator(_nonblank)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(ge=1)]
NonNegativeAmount = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Zero = Annotated[Literal[0], BeforeValidator(_integer_literal)]
One = Annotated[Literal[1], BeforeValidator(_integer_literal)]
TrueOnly = Annotated[Literal[True], BeforeValidator(_boolean_literal)]
FalseOnly = Annotated[Literal[False], BeforeValidator(_boolean_literal)]
ProviderAdapter = Literal['official_responses', 'compatible_chat']
EndpointPolicy = Literal['public_https', 'explicit_loopback']
OutboundPurpose = Literal['tutor', 'search', 'authoring', 'codex']
ProviderFailureCode = Literal[
    'CAPABILITY_UNSUPPORTED', 'PROVIDER_CONFIGURATION_CHANGED',
    'PROVIDER_SECRET_UNAVAILABLE', 'OUTBOUND_SOURCE_CHANGED', 'OUTBOUND_SOURCE_UNAVAILABLE',
    'CONSENT_REQUIRED', 'CONSENT_REVOKED', 'CONSENT_EXPIRED', 'OUTBOUND_BUDGET_EXCEEDED',
    'PROVIDER_TIMEOUT', 'PROVIDER_CANCELLED', 'PROVIDER_TRANSPORT_ERROR',
    'PROVIDER_PROTOCOL_ERROR', 'PROVIDER_OUTCOME_UNKNOWN', 'PROVIDER_USAGE_INCONSISTENT',
    'PROVIDER_REFUSAL', 'PROVIDER_INCOMPLETE',
]


class ProviderPricing(dm.StrictModel):
    input_usd_per_million: NonNegativeAmount
    output_usd_per_million: NonNegativeAmount
    source_note: NonEmpty


class ProviderCapabilitiesResponse(dm.StrictModel):
    items: list[dm.ProviderCapabilities]


class ProviderConfigWrite(dm.StrictModel):
    expected_revision: NonNegativeInt
    adapter: ProviderAdapter
    base_url: NonEmpty
    model: NonEmpty
    embedding_model: NonEmpty | None
    endpoint_policy: EndpointPolicy
    pricing: ProviderPricing | None


class ProviderConfigView(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    config_sha256: dm.Sha256
    adapter: ProviderAdapter
    base_url: NonEmpty
    model: NonEmpty
    embedding_model: NonEmpty | None
    endpoint_policy: EndpointPolicy
    pricing: ProviderPricing | None
    configured: TrueOnly
    secret_present: bool


class ProviderConfigAck(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    config_sha256: dm.Sha256
    configured: TrueOnly
    secret_present: bool


class ProviderSecretWrite(dm.StrictModel):
    expected_revision: dm.Revision
    secret: NonEmpty = Field(repr=False)


class ProviderSecretAck(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    config_sha256: dm.Sha256
    secret_present: bool


class OutboundBudget(dm.StrictModel):
    max_input_tokens: PositiveInt
    max_output_tokens: PositiveInt
    max_provider_calls: One
    max_search_calls: Zero
    max_tool_calls: Zero
    timeout_seconds: PositiveInt = 180
    max_cost_usd: NonNegativeAmount | None


class FrozenOutboundBudget(dm.StrictModel):
    max_input_tokens: PositiveInt
    max_output_tokens: PositiveInt
    max_provider_calls: One
    max_search_calls: Zero
    max_tool_calls: Zero
    timeout_seconds: PositiveInt
    max_cost_usd: NonNegativeAmount | None


class ConsentPreviewWrite(dm.StrictModel):
    job_id: dm.Id
    expected_job_revision: dm.Revision
    provider_id: dm.Id
    expected_provider_revision: dm.Revision
    budget: OutboundBudget
    expires_at: dm.UTC


class ReferenceSummary(dm.StrictModel):
    ref: dm.ContentRef
    title: NonEmpty
    locator: NonEmpty
    character_count: NonNegativeInt
    excerpt_sha256: dm.Sha256


class MessageSummary(dm.StrictModel):
    role: Literal['system', 'user', 'assistant']
    character_count: NonNegativeInt
    content_sha256: dm.Sha256


class LocalExactInputTokens(dm.StrictModel):
    kind: Literal['local_exact']
    input_tokens: NonNegativeInt
    checker_version: NonEmpty
    proof_sha256: dm.Sha256
    request_body_sha256: dm.Sha256


class LocalUpperBoundInputTokens(dm.StrictModel):
    kind: Literal['local_upper_bound']
    input_tokens_upper_bound: NonNegativeInt
    checker_version: NonEmpty
    proof_sha256: dm.Sha256
    request_body_sha256: dm.Sha256


InputTokenAssurance = Annotated[
    LocalExactInputTokens | LocalUpperBoundInputTokens, Field(discriminator='kind'),
]


class UnknownCostEstimate(dm.StrictModel):
    kind: Literal['unknown']
    currency: Literal['USD']


class EstimatedCostEstimate(dm.StrictModel):
    kind: Literal['estimated']
    currency: Literal['USD']
    maximum_estimated_cost: NonNegativeAmount
    pricing_sha256: dm.Sha256


CostEstimate = Annotated[UnknownCostEstimate | EstimatedCostEstimate, Field(discriminator='kind')]


class FrozenOutboundSummary(dm.StrictModel):
    job_id: dm.Id
    source_job_revision: dm.Revision
    source_input_sha256: dm.Sha256
    purpose: OutboundPurpose
    provider_id: dm.Id
    provider_revision: dm.Revision
    config_sha256: dm.Sha256
    adapter: ProviderAdapter
    adapter_version: NonEmpty
    base_url: NonEmpty
    endpoint_policy: EndpointPolicy
    model: NonEmpty
    context_snapshot_id: dm.Id
    context_snapshot_sha256: dm.Sha256
    input_sha256: dm.Sha256
    messages: list[MessageSummary]
    references: list[ReferenceSummary]
    input_character_count: NonNegativeInt
    input_token_assurance: InputTokenAssurance
    allow_web: FalseOnly
    budget: FrozenOutboundBudget
    cost_estimate: CostEstimate
    created_at: dm.UTC
    expires_at: dm.UTC

    @model_validator(mode='after')
    def frozen_limits(self) -> Self:
        if _instant(self.expires_at) <= _instant(self.created_at):
            raise ValueError('frozen expiry must follow creation')
        assurance = self.input_token_assurance
        bound = (assurance.input_tokens if isinstance(assurance, LocalExactInputTokens)
                 else assurance.input_tokens_upper_bound)
        if bound > self.budget.max_input_tokens:
            raise ValueError('input assurance exceeds the frozen input budget')
        if (isinstance(self.cost_estimate, EstimatedCostEstimate)
                and self.budget.max_cost_usd is not None
                and self.cost_estimate.maximum_estimated_cost > self.budget.max_cost_usd):
            raise ValueError('known estimated cost exceeds the frozen cost budget')
        return self


ProposalWarningCode = Literal[
    'price_unknown', 'estimate_not_guaranteed', 'provider_changed', 'source_changed',
    'source_unavailable', 'job_unavailable', 'proposal_expired', 'capability_unavailable',
]


class ProposalWarning(dm.StrictModel):
    code: ProposalWarningCode
    message: NonEmpty


class ConsentProposalView(dm.StrictModel):
    id: dm.Id
    proposal_sha256: dm.Sha256
    summary: FrozenOutboundSummary
    validity: Literal['current', 'stale', 'expired', 'unavailable']
    consent_id: dm.Id | None
    warnings: list[ProposalWarning]


class ConsentCreate(dm.StrictModel):
    proposal_id: dm.Id
    proposal_sha256: dm.Sha256


class ConsentCreateAck(dm.StrictModel):
    id: dm.Id
    revision: One
    status: Literal['active']
    proposal_id: dm.Id
    proposal_sha256: dm.Sha256
    summary: FrozenOutboundSummary


class ConsentRevoke(dm.StrictModel):
    expected_revision: dm.Revision


class UnknownUsageCost(dm.StrictModel):
    kind: Literal['unknown']
    currency: Literal['USD']


class EstimatedUsageCost(dm.StrictModel):
    kind: Literal['estimated']
    currency: Literal['USD']
    amount: NonNegativeAmount
    pricing_sha256: dm.Sha256


class ActualUsageCost(dm.StrictModel):
    kind: Literal['actual']
    currency: Literal['USD']
    amount: NonNegativeAmount
    source: Literal['provider_reported']


UsageCost = Annotated[
    UnknownUsageCost | EstimatedUsageCost | ActualUsageCost, Field(discriminator='kind'),
]


class ProviderUsageView(dm.StrictModel):
    consumed_provider_calls: Annotated[int, Field(ge=0, le=1)]
    search_calls: Zero
    tool_calls: Zero
    input_tokens: NonNegativeInt | None
    output_tokens: NonNegativeInt | None
    elapsed_ms: NonNegativeInt | None
    cost: UsageCost


JobRef = dm.JobRef


class ConsentDispatchView(dm.StrictModel):
    id: dm.Id
    job: JobRef
    started_at: dm.UTC | None
    finished_at: dm.UTC | None
    usage: ProviderUsageView
    error_code: ProviderFailureCode | None

    @model_validator(mode='after')
    def dispatch_times(self) -> Self:
        if (self.started_at is not None and self.finished_at is not None
                and _instant(self.finished_at) < _instant(self.started_at)):
            raise ValueError('dispatch finish precedes its start')
        return self


class ConsentView(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    status: Literal['active', 'revoked', 'expired']
    proposal_id: dm.Id
    proposal_sha256: dm.Sha256
    summary: FrozenOutboundSummary
    created_at: dm.UTC
    expires_at: dm.UTC
    revoked_at: dm.UTC | None
    dispatch: ConsentDispatchView | None

    @model_validator(mode='after')
    def consent_times(self) -> Self:
        if _instant(self.expires_at) != _instant(self.summary.expires_at):
            raise ValueError('consent expiry must match the frozen summary')
        if not (_instant(self.summary.created_at) <= _instant(self.created_at) < _instant(self.expires_at)):
            raise ValueError('grant must be created within the proposal lifetime')
        if (self.status == 'revoked') != (self.revoked_at is not None):
            raise ValueError('only an actually revoked consent has a revocation time')
        if self.revoked_at is not None and _instant(self.revoked_at) < _instant(self.created_at):
            raise ValueError('revocation precedes grant creation')
        return self


class ConsentByIdQuery(dm.StrictModel):
    consent_id: dm.Id


class ConsentListQuery(dm.StrictModel):
    # None is an internal omitted marker, excluded from wire/schema. Explicit
    # null is rejected; this preserves optional-but-not-nullable URL semantics.
    cursor: NonEmpty | SkipJsonSchema[None] = Field(
        default=None, exclude_if=lambda value: value is None, json_schema_extra=_omit_schema_default,
    )
    limit: Annotated[int, Field(ge=1, le=100)] = 20

    @field_validator('cursor', mode='before')
    @classmethod
    def cursor_not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError('cursor may be omitted but cannot be null')
        return value


ConsentQuery = ConsentByIdQuery | ConsentListQuery


class ConsentPage(dm.StrictModel):
    items: list[ConsentView]
    next_cursor: NonEmpty | None
    total_hint: NonNegativeInt | SkipJsonSchema[None] = Field(
        default=None, exclude_if=lambda value: value is None, json_schema_extra=_omit_schema_default,
    )

    @field_validator('total_hint', mode='before')
    @classmethod
    def total_not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError('total_hint may be omitted but cannot be null')
        return value
