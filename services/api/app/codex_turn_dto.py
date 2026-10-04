"""Closed application contracts from sole PRODUCT_DESIGN §20.17.

These models validate public shape and self-contained relationships, not access,
private freeze hashes, history membership, protocol truth, or execution rights.
The named owners must check those facts in their current transaction. Bootstrap
acknowledgements and ordinary Provider contracts keep their original decoders.
"""
from datetime import datetime, timedelta
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self, TypeVar
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from .application.provider_models import UsageSnapshot
from .codex_bootstrap_dto import SafeLabel
from . import provider_dto as provider


def _unicode(value: object) -> None:
    if isinstance(value, str):
        try:
            value.encode('utf-8')
        except UnicodeError:
            raise ValueError('Unicode scalar text is required') from None
    elif isinstance(value, BaseModel):
        for name in type(value).model_fields:
            _unicode(getattr(value, name))
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode(key)
            _unicode(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _unicode(item)


class CodexTurnModel(dm.StrictModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    def __repr_args__(self):
        return []

    @model_validator(mode='before')
    @classmethod
    def unicode_scalars(cls, value: object) -> object:
        _unicode(value)
        return value


Model = TypeVar('Model', bound=CodexTurnModel)


def parse_codex_turn(model: type[Model], raw: bytes | str) -> Model:
    """Strict raw JSON seam: never let a decoder discard duplicate keys."""
    return model.model_validate(strict_json(raw))


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _distinct(values: Sequence[object]) -> None:
    if len(set(values)) != len(values):
        raise ValueError('Duplicate or conflicting members are forbidden')


def _integer(value: object) -> object:
    if type(value) is not int:
        raise ValueError('An integer literal is required')
    return value


def _path(value: str) -> str:
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '\\' in value or ':' in value
            or any(part in {'', '.', '..'} for part in value.split('/')) or str(path) != value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('A canonical relative sandbox path is required')
    return value


def _endpoint(value: str) -> str:
    # Syntax only. Provider owns endpoint policy, normalization and DNS proofs;
    # this validation performs no lookup and cannot authorize a destination.
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError('A safe model endpoint is required') from None
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or (port is not None and not 1 <= port <= 65535)
            or any(ord(char) <= 32 or ord(char) == 127 for char in value) or '\\' in value):
        raise ValueError('A safe model endpoint is required')
    return value


SandboxPath = Annotated[str, Field(min_length=1), AfterValidator(_path)]
Endpoint = Annotated[str, Field(min_length=1), AfterValidator(_endpoint)]
NonBlank = provider.NonEmpty
NonNegativeInt = provider.NonNegativeInt
FileSize = Annotated[int, Field(ge=0, le=16777216)]
Outcome = Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown']
ApprovalValidity = Literal['current', 'expired', 'changed', 'unavailable', 'closed']
ApprovalChoice = Literal['pending', 'approve_once', 'decline']
CodexFailureCode = Literal[
    'CODEX_PROTOCOL_INVALID', 'CODEX_PROFILE_CHANGED', 'CODEX_RUNTIME_UNAVAILABLE',
    'CODEX_BINDING_INVALID', 'CODEX_HISTORY_DAMAGED', 'CODEX_INPUT_PROOF_UNAVAILABLE',
    'CODEX_OPERATION_UNSUPPORTED', 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED', 'CODEX_TIMEOUT',
    'CODEX_RESOURCE_LIMIT', 'CODEX_CANCELLED', 'CODEX_OUTCOME_UNKNOWN', 'CODEX_OPERATION_FAILED',
    'CODEX_ARTIFACT_REJECTED', 'CODEX_ARTIFACT_MISSING', 'CODEX_SOURCE_CHANGED',
    'CODEX_SOURCE_UNAVAILABLE', 'CODEX_APPROVAL_EXPIRED', 'CODEX_CONSENT_EXPIRED',
    'CODEX_CONSENT_REVOKED', 'CODEX_BUDGET_EXCEEDED', 'POLICY_DENIED', 'ASSESSMENT_ACTIVE',
]
SafeCode = CodexFailureCode | provider.ProviderFailureCode


class CodexBlockRef(dm.ContentRef):
    entity: Literal['block']

    @model_validator(mode='before')
    @classmethod
    def core_ref(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.ContentRef) else value


def _refs(refs: list[CodexBlockRef]) -> list[CodexBlockRef]:
    _distinct([(ref.entity, ref.id, ref.revision) for ref in refs])
    return refs


BlockRefs = Annotated[list[CodexBlockRef], Field(max_length=8), AfterValidator(_refs)]


class CodexTurnWarning(CodexTurnModel):
    # Same Warning fields; this new wire requires the nullable locator explicitly.
    code: str
    message: str
    locator: str | None
    severity: Literal['info', 'warning', 'error']


class CodexLocalToolBudget(CodexTurnModel):
    max_tool_calls: Annotated[int, Field(ge=0, le=16)]
    wall_seconds: Annotated[int, Field(ge=1, le=300)]


class CodexTurnRuntimeSummary(CodexTurnModel):
    profile_sha256: dm.Sha256
    cpu_seconds: Annotated[Literal[60], BeforeValidator(_integer)]
    memory_bytes: Annotated[Literal[2147483648], BeforeValidator(_integer)]
    file_bytes: Annotated[Literal[16777216], BeforeValidator(_integer)]
    protocol_output_bytes: Annotated[Literal[16777216], BeforeValidator(_integer)]
    file_descriptors: Annotated[Literal[128], BeforeValidator(_integer)]
    processes: Annotated[Literal[16], BeforeValidator(_integer)]
    core_bytes: provider.Zero
    command_network: Literal['denied']
    writable_area: Literal['turn_outputs']


class CodexTurnPrepareWrite(CodexTurnModel):
    message: Annotated[NonBlank, Field(max_length=8000)]
    context_refs: BlockRefs
    expected_session_revision: dm.Revision
    provider_id: dm.Id
    tools: CodexLocalToolBudget


class CodexTurnPreparationSummary(CodexTurnModel):
    context_snapshot_id: dm.Id
    snapshot_sha256: dm.Sha256
    job_input_sha256: dm.Sha256
    prepared_input_sha256: dm.Sha256
    runtime: CodexTurnRuntimeSummary
    character_count: Annotated[int, Field(ge=1, le=12000)]
    materials: Annotated[list[provider.ReferenceSummary], Field(max_length=8)]
    history_turn_ids: Annotated[list[dm.Id], Field(max_length=2)]
    tools: CodexLocalToolBudget
    warnings: Annotated[list[CodexTurnWarning], Field(max_length=32)]

    @model_validator(mode='after')
    def unique_members(self) -> Self:
        _refs([CodexBlockRef.model_validate(item.ref) for item in self.materials])
        _distinct(list(self.history_turn_ids))
        _distinct([(item.code, item.message, item.locator, item.severity) for item in self.warnings])
        return self


class CodexTurnPreparationView(CodexTurnModel):
    id: dm.Id
    preparation_sha256: dm.Sha256
    actor_session_id: dm.Id
    session_id: dm.Id
    session_revision: dm.Revision
    turn_id: dm.Id
    job: dm.JobRef
    request: CodexTurnPrepareWrite
    summary: CodexTurnPreparationSummary
    created_at: dm.UTC
    proposal_id: dm.Id | None
    consent_id: dm.Id | None
    validity: Literal['current', 'changed', 'unavailable', 'closed']

    @model_validator(mode='after')
    def frozen_relationships(self) -> Self:
        if self.session_revision <= self.request.expected_session_revision:
            raise ValueError('Preparation must reserve a newer session revision')
        if self.summary.tools != self.request.tools:
            raise ValueError('The prepared tool budget must retain the request')
        if self.consent_id is not None and self.proposal_id is None:
            raise ValueError('A consent requires its proposal binding')
        if self.turn_id in self.summary.history_turn_ids:
            raise ValueError('The new turn cannot be its own history')
        # Whole references may be omitted, but never reordered, substituted, or
        # resolved through a later current revision.
        remaining = iter(self.request.context_refs)
        for material in self.summary.materials:
            if not any(ref == CodexBlockRef.model_validate(material.ref) for ref in remaining):
                raise ValueError('Prepared materials must preserve exact requested reference order')
        if self.summary.character_count < len(self.request.message):
            raise ValueError('The required message cannot be truncated')
        return self


class CodexOutboundBudgetWrite(CodexTurnModel):
    max_input_tokens: provider.PositiveInt
    max_output_tokens: provider.PositiveInt
    max_provider_calls: provider.One
    max_search_calls: provider.Zero
    max_cost_usd: provider.NonNegativeAmount | None


class CodexOutboundPreviewWrite(CodexTurnModel):
    preparation_id: dm.Id
    preparation_sha256: dm.Sha256
    expected_job_revision: dm.Revision
    expected_provider_revision: dm.Revision
    budget: CodexOutboundBudgetWrite
    expires_at: dm.UTC


class CodexFrozenOutboundSummary(CodexTurnModel):
    version: Literal['codex-outbound-summary-v1']
    preparation_id: dm.Id
    preparation_sha256: dm.Sha256
    session_id: dm.Id
    turn_id: dm.Id
    job_id: dm.Id
    source_job_revision: dm.Revision
    source_input_sha256: dm.Sha256
    provider_id: dm.Id
    provider_revision: dm.Revision
    config_sha256: dm.Sha256
    adapter: Literal['codex_app_server']
    adapter_version: SafeLabel
    endpoint: Endpoint
    endpoint_policy: provider.EndpointPolicy
    model: SafeLabel
    context_snapshot_id: dm.Id
    context_snapshot_sha256: dm.Sha256
    input_sha256: dm.Sha256
    request_body_sha256: dm.Sha256
    messages: Annotated[list[provider.MessageSummary], Field(min_length=2, max_length=6)]
    references: Annotated[list[provider.ReferenceSummary], Field(max_length=8)]
    input_character_count: Annotated[int, Field(ge=1, le=12000)]
    input_token_assurance: provider.InputTokenAssurance
    budget: CodexOutboundBudgetWrite
    tools: CodexLocalToolBudget
    runtime: CodexTurnRuntimeSummary
    cost_estimate: provider.CostEstimate
    created_at: dm.UTC
    expires_at: dm.UTC

    @model_validator(mode='after')
    def frozen_limits(self) -> Self:
        lifetime = _time(self.expires_at) - _time(self.created_at)
        if not timedelta(0) < lifetime <= timedelta(minutes=10):
            raise ValueError('The proposal lifetime must be positive and at most ten minutes')
        assurance = self.input_token_assurance
        bound = (assurance.input_tokens if isinstance(assurance, provider.LocalExactInputTokens)
                 else assurance.input_tokens_upper_bound)
        if (assurance.request_body_sha256 != self.request_body_sha256
                or bound > self.budget.max_input_tokens):
            raise ValueError('The proof must bind this request within its input budget')
        if (isinstance(self.cost_estimate, provider.EstimatedCostEstimate)
                and self.budget.max_cost_usd is not None
                and self.cost_estimate.maximum_estimated_cost > self.budget.max_cost_usd):
            raise ValueError('Estimated cost exceeds the budget')
        _refs([CodexBlockRef.model_validate(item.ref) for item in self.references])
        if self.endpoint_policy == 'public_https' and urlsplit(self.endpoint).scheme != 'https':
            raise ValueError('Public endpoints require HTTPS')
        if (self.endpoint_policy == 'explicit_loopback'
                and urlsplit(self.endpoint).hostname not in {'localhost', '127.0.0.1', '::1'}):
            raise ValueError('Explicit loopback policy must retain a loopback endpoint')
        return self


class CodexConsentProposalView(CodexTurnModel):
    id: dm.Id
    proposal_sha256: dm.Sha256
    summary: CodexFrozenOutboundSummary
    validity: Literal['current', 'stale', 'expired', 'unavailable']
    consent_id: dm.Id | None
    warnings: Annotated[list[provider.ProposalWarning], Field(max_length=8)]

    @model_validator(mode='after')
    def unique_warnings(self) -> Self:
        _distinct([warning.code for warning in self.warnings])
        return self


class CodexConsentCreateWrite(CodexTurnModel):
    proposal_id: dm.Id
    proposal_sha256: dm.Sha256


class CodexConsentCreateAck(CodexTurnModel):
    id: dm.Id
    revision: provider.One
    status: Literal['active']
    actor_session_id: dm.Id
    proposal_id: dm.Id
    proposal_sha256: dm.Sha256
    summary: CodexFrozenOutboundSummary


class CodexDispatchView(CodexTurnModel):
    id: dm.Id
    job: dm.JobRef
    started_at: dm.UTC | None
    finished_at: dm.UTC | None
    consumed_provider_calls: Annotated[int, Field(ge=0, le=1)]
    input_tokens: NonNegativeInt | None
    output_tokens: NonNegativeInt | None
    elapsed_ms: NonNegativeInt | None
    cost: provider.UsageCost
    outcome: Outcome | None
    error_code: SafeCode | None

    @model_validator(mode='after')
    def actual_facts(self) -> Self:
        if (self.finished_at is None) != (self.outcome is None):
            raise ValueError('Terminal dispatch outcome and finish must be present together')
        if (self.started_at is not None and self.finished_at is not None
                and _time(self.finished_at) < _time(self.started_at)):
            raise ValueError('Dispatch finish precedes start')
        if self.outcome == 'completed' and self.error_code is not None:
            raise ValueError('Completed dispatch cannot contain an error')
        return self


class CodexConsentView(CodexTurnModel):
    id: dm.Id
    revision: dm.Revision
    status: Literal['active', 'revoked', 'expired']
    actor_session_id: dm.Id
    proposal_id: dm.Id
    proposal_sha256: dm.Sha256
    summary: CodexFrozenOutboundSummary
    created_at: dm.UTC
    expires_at: dm.UTC
    revoked_at: dm.UTC | None
    dispatch: CodexDispatchView | None

    @model_validator(mode='after')
    def grant_facts(self) -> Self:
        if self.expires_at != self.summary.expires_at:
            raise ValueError('Grant expiry must retain its proposal expiry')
        if not _time(self.summary.created_at) <= _time(self.created_at) < _time(self.expires_at):
            raise ValueError('Grant must be created within the proposal lifetime')
        if (self.status == 'revoked') != (self.revoked_at is not None):
            raise ValueError('Only revocation has a revocation time')
        if self.revoked_at is not None and _time(self.revoked_at) < _time(self.created_at):
            raise ValueError('Revocation precedes creation')
        if self.revision != (2 if self.status == 'revoked' else 1):
            raise ValueError('Expiry and dispatch cannot revise the original grant')
        if self.dispatch is not None and self.dispatch.job.id != self.summary.job_id:
            raise ValueError('Dispatch must belong to the original turn job')
        return self


class CodexTurnStartWrite(CodexTurnModel):
    preparation_id: dm.Id
    preparation_sha256: dm.Sha256
    consent_id: dm.Id
    expected_session_revision: dm.Revision


class CodexTurnStartAck(CodexTurnModel):
    turn_id: dm.Id
    session_revision: dm.Revision
    job: dm.JobRef

    @model_validator(mode='after')
    def original_queued_fact(self) -> Self:
        if self.job.status != 'queued':
            raise ValueError('The original start ACK records queue admission, not execution')
        return self


class CodexCurrentFeatures(CodexTurnModel):
    approvals: bool
    interrupt: bool
    artifacts: bool


class CodexCurrentSessionView(CodexTurnModel):
    """Current projection only; never use this decoder for an old create ACK."""
    id: dm.Id
    revision: dm.Revision
    status: Literal['initializing', 'ready', 'failed', 'unknown']
    active_turn_id: dm.Id | None
    adapter_version: SafeLabel
    capabilities: CodexCurrentFeatures

    @model_validator(mode='after')
    def bootstrap_or_control_history(self) -> Self:
        if self.status != 'ready':
            if (self.revision != (1 if self.status == 'initializing' else 2)
                    or self.active_turn_id is not None or any(self.capabilities.model_dump().values())):
                raise ValueError('Only a ready bootstrap can have subsequent control history')
        elif self.revision < 2:
            raise ValueError('Ready bootstrap begins at revision two')
        elif self.revision == 2 and (self.active_turn_id is not None or any(self.capabilities.model_dump().values())):
            raise ValueError('An original session without turn history retains empty/false fields')
        return self


class CodexApprovalControl(CodexTurnModel):
    id: dm.Id
    revision: dm.Revision
    operation_sha256: dm.Sha256
    decision: ApprovalChoice
    validity: ApprovalValidity

    @model_validator(mode='after')
    def decided_revision(self) -> Self:
        if self.decision != 'pending' and self.revision < 2:
            raise ValueError('A decision must advance the original pending revision')
        return self


class CodexConsentControl(CodexTurnModel):
    id: dm.Id
    revision: dm.Revision
    status: Literal['active', 'revoked', 'expired']

    @model_validator(mode='after')
    def consent_revision(self) -> Self:
        if self.revision != (2 if self.status == 'revoked' else 1):
            raise ValueError('Derived expiry and dispatch do not revise authorization')
        return self


class CodexTurnControlView(CodexTurnModel):
    id: dm.Id
    session_id: dm.Id
    actor_session_id: dm.Id
    job: dm.JobRef
    job_revision: dm.Revision
    run_revision: dm.Revision
    last_seq: NonNegativeInt
    cancel_requested: bool
    execution: Literal['not_started', 'active', 'terminal']
    outcome: Outcome | None
    approval_ids: Annotated[list[dm.Id], Field(max_length=64)]
    approval_controls: Annotated[list[CodexApprovalControl], Field(max_length=64)]
    consent_control: CodexConsentControl | None
    manifest_id: dm.Id | None
    created_at: dm.UTC
    started_at: dm.UTC | None
    finished_at: dm.UTC | None
    error_code: SafeCode | None

    @model_validator(mode='after')
    def control_relationships(self) -> Self:
        _distinct(list(self.approval_ids))
        if self.approval_ids != [item.id for item in self.approval_controls]:
            raise ValueError('Approval controls must retain the complete ordered membership')
        terminal = self.execution == 'terminal'
        if terminal != (self.outcome is not None) or terminal != (self.finished_at is not None):
            raise ValueError('Execution, terminal outcome and finish must agree')
        if self.execution == 'active' and self.started_at is None:
            raise ValueError('Active execution requires the actual start')
        if self.execution == 'not_started' and self.started_at is not None:
            raise ValueError('Actual start cannot be rewritten as not started')
        for when in (self.started_at, self.finished_at):
            if when is not None and _time(when) < _time(self.created_at):
                raise ValueError('Execution cannot precede creation')
        if (self.started_at is not None and self.finished_at is not None
                and _time(self.finished_at) < _time(self.started_at)):
            raise ValueError('Finish cannot precede start')
        if terminal:
            expected = self.outcome if self.outcome in {'completed', 'cancelled'} else 'failed'
            if self.job.status != expected:
                raise ValueError('The Job must retain the actual mapped terminal outcome')
        elif self.job.status in {'completed', 'failed', 'cancelled'}:
            raise ValueError('A terminal Job cannot have active control state')
        if self.outcome == 'completed' and (self.started_at is None or self.error_code is not None):
            raise ValueError('Completion requires actual execution without an error')
        if self.manifest_id is not None and not terminal:
            raise ValueError('A manifest is registered with the unique terminal fact')
        return self


class CodexTurnPage(CodexTurnModel):
    items: Annotated[list[CodexTurnControlView], Field(max_length=100)]
    next_cursor: NonBlank | None

    @model_validator(mode='after')
    def unique_turns(self) -> Self:
        _distinct([item.id for item in self.items])
        if len({item.session_id for item in self.items}) > 1:
            raise ValueError('A page belongs to one session')
        return self


class CodexTurnResultView(CodexTurnModel):
    control: CodexTurnControlView
    preparation_id: dm.Id
    answer_markdown: Annotated[str, Field(max_length=400000)]
    output_sha256: dm.Sha256 | None
    output_state: Literal['none', 'partial', 'complete']
    usage: UsageSnapshot
    mathematical: Literal['NOT_RUN']
    sources: Literal['NOT_RUN']
    independent_pedagogy: Literal['NOT_RUN']

    @model_validator(mode='after')
    def exact_answer(self) -> Self:
        expected = sha256_bytes(self.answer_markdown.encode()) if self.answer_markdown else None
        if self.output_sha256 != expected or (self.output_state == 'none') != (expected is None):
            raise ValueError('Output state and SHA must describe the exact preserved UTF-8 answer')
        return self


class CodexTurnStatusEvent(CodexTurnModel):
    type: Literal['status']
    job: dm.JobRef
    run_revision: dm.Revision


class CodexTurnAnswerEvent(CodexTurnModel):
    type: Literal['answer_delta']
    text: Annotated[str, Field(min_length=1)]


class CodexTurnApprovalEvent(CodexTurnModel):
    type: Literal['approval_required']
    approval_id: dm.Id


class CodexTurnUsageEvent(CodexTurnModel):
    type: Literal['usage']
    usage: UsageSnapshot


class CodexTurnManifestEvent(CodexTurnModel):
    type: Literal['manifest_ready']
    manifest_id: dm.Id
    manifest_sha256: dm.Sha256


class CodexTurnTerminalEvent(CodexTurnModel):
    type: Literal['terminal']
    outcome: Outcome
    error_code: SafeCode | None

    @model_validator(mode='after')
    def completed_without_error(self) -> Self:
        if self.outcome == 'completed' and self.error_code is not None:
            raise ValueError('Completed terminal cannot contain an error')
        return self


CodexTurnEventPayload = Annotated[
    CodexTurnStatusEvent | CodexTurnAnswerEvent | CodexTurnApprovalEvent | CodexTurnUsageEvent
    | CodexTurnManifestEvent | CodexTurnTerminalEvent, Field(discriminator='type'),
]


class CodexTurnEvent(CodexTurnModel):
    turn_id: dm.Id
    run_id: dm.Id
    seq: dm.Revision
    occurred_at: dm.UTC
    payload: CodexTurnEventPayload

    @model_validator(mode='after')
    def status_run_binding(self) -> Self:
        if isinstance(self.payload, CodexTurnStatusEvent) and self.payload.job.id != self.run_id:
            raise ValueError('The status event Run is the actual Job ID')
        return self


class CodexOperationFile(CodexTurnModel):
    path: SandboxPath
    size: FileSize
    sha256: dm.Sha256


class CodexCommandOperation(CodexTurnModel):
    kind: Literal['command']
    command_text: Annotated[NonBlank, Field(max_length=20000)]
    cwd: SandboxPath
    executable_sha256: dm.Sha256
    environment_sha256: dm.Sha256
    read_files: Annotated[list[CodexOperationFile], Field(max_length=64)]
    writable_area: Literal['turn_outputs']
    filesystem_scope_sha256: dm.Sha256
    network: Literal['denied']
    operation_profile_sha256: dm.Sha256

    @model_validator(mode='after')
    def unique_files(self) -> Self:
        _distinct([item.path for item in self.read_files])
        return self


class CodexFileChange(CodexTurnModel):
    path: SandboxPath
    action: Literal['add', 'update', 'delete']
    before_sha256: dm.Sha256 | None
    after_sha256: dm.Sha256 | None
    before_size: FileSize | None
    after_size: FileSize | None
    diff: Annotated[str, Field(max_length=400000)]

    @model_validator(mode='after')
    def actual_before_after(self) -> Self:
        for prefix, exists in (('before', self.action != 'add'), ('after', self.action != 'delete')):
            if ((getattr(self, prefix + '_sha256') is not None) != exists
                    or (getattr(self, prefix + '_size') is not None) != exists):
                raise ValueError('File action must retain complete actual before/after facts')
        return self


class CodexFileOperation(CodexTurnModel):
    kind: Literal['file_change']
    files: Annotated[list[CodexFileChange], Field(min_length=1, max_length=32)]
    operation_profile_sha256: dm.Sha256

    @model_validator(mode='after')
    def unique_paths(self) -> Self:
        _distinct([item.path for item in self.files])
        return self


class CodexDeniedOperation(CodexTurnModel):
    kind: Literal['unsupported']
    category: Literal['network', 'permission_expansion', 'unbound_operation', 'unsupported_tool']
    reason: SafeCode


CodexOperation = Annotated[
    CodexCommandOperation | CodexFileOperation | CodexDeniedOperation, Field(discriminator='kind'),
]


class GenericApprovalView(CodexTurnModel):
    id: dm.Id
    revision: dm.Revision
    actor_session_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    run_id: dm.Id
    job: dm.JobRef
    job_revision: dm.Revision
    operation: CodexOperation
    operation_sha256: dm.Sha256
    created_at: dm.UTC
    expires_at: dm.UTC
    decision: ApprovalChoice
    validity: ApprovalValidity
    execution: Literal['not_started', 'started', 'completed', 'failed', 'unknown']
    decided_at: dm.UTC | None
    started_at: dm.UTC | None
    finished_at: dm.UTC | None
    result_sha256: dm.Sha256 | None
    error_code: SafeCode | None

    @model_validator(mode='after')
    def operation_facts(self) -> Self:
        if self.run_id != self.job.id:
            raise ValueError('The approval Run must be its actual Job')
        if _time(self.expires_at) <= _time(self.created_at):
            raise ValueError('Approval expiry must follow creation')
        if (self.decision == 'pending') != (self.decided_at is None):
            raise ValueError('Only actual decisions have a decision time')
        if self.decision != 'pending' and self.revision < 2:
            raise ValueError('A decision advances the approval revision')
        if self.execution == 'started' and self.revision < 3:
            raise ValueError('Actual start must advance the original decision revision')
        if self.execution in {'completed', 'failed', 'unknown'} and self.revision < 4:
            raise ValueError('Actual finish must advance the actual start revision')
        if isinstance(self.operation, CodexDeniedOperation) and self.decision == 'approve_once':
            raise ValueError('An unsupported operation can never be approved')
        if self.execution != 'not_started' and self.decision != 'approve_once':
            raise ValueError('Only an approved operation may have execution facts')
        if (self.execution == 'not_started') != (self.started_at is None):
            raise ValueError('Execution state and actual start must agree')
        if (self.execution in {'completed', 'failed', 'unknown'}) != (self.finished_at is not None):
            raise ValueError('Terminal execution and finish must agree')
        previous = self.created_at
        for when in (self.decided_at, self.started_at, self.finished_at):
            if when is not None:
                if _time(when) < _time(previous):
                    raise ValueError('Operation facts cannot precede their prerequisites')
                previous = when
        if self.execution in {'not_started', 'started'} and self.result_sha256 is not None:
            raise ValueError('A result cannot precede terminal execution')
        if self.execution == 'completed' and (self.result_sha256 is None or self.error_code is not None):
            raise ValueError('Completed operation needs an intact result without an error')
        return self


class GenericApprovalDecisionAck(CodexTurnModel):
    id: dm.Id
    revision: Annotated[Literal[2], BeforeValidator(_integer)]
    actor_session_id: dm.Id
    operation_sha256: dm.Sha256
    decision: Literal['approve_once', 'decline']
    applied: provider.TrueOnly
    session_id: dm.Id
    turn_id: dm.Id
    run_id: dm.Id
    job: dm.JobRef

    @model_validator(mode='after')
    def original_binding(self) -> Self:
        if self.run_id != self.job.id:
            raise ValueError('The original decision Run must be its actual Job')
        return self


class CodexInterruptWrite(CodexTurnModel):
    turn_id: dm.Id
    expected_session_revision: dm.Revision


class CodexInterruptAck(CodexTurnModel):
    id: dm.Id
    turn_id: dm.Id
    status: Literal['interrupt_requested', 'already_terminal']


class CodexArtifactEntry(CodexTurnModel):
    artifact_id: dm.Id
    logical_path: SandboxPath
    size: FileSize
    sha256: dm.Sha256
    media_type: SafeLabel
    scan: Literal['PASS']
    import_kind: Literal['markdown', 'html', 'learnpack'] | None


class CodexArtifactExcluded(CodexTurnModel):
    entry_id: dm.Id
    reason: SafeCode


class CodexArtifactManifest(CodexTurnModel):
    version: Literal['codex-artifact-manifest-v1']
    id: dm.Id
    revision: provider.One
    session_id: dm.Id
    turn_id: dm.Id
    run_id: dm.Id
    source_job_id: dm.Id
    source_outcome: Outcome
    runtime_profile_sha256: dm.Sha256
    terminal_receipt_sha256: dm.Sha256
    scan_profile_sha256: dm.Sha256
    created_at: dm.UTC
    entries: Annotated[list[CodexArtifactEntry], Field(max_length=32)]
    excluded: Annotated[list[CodexArtifactExcluded], Field(max_length=32)]
    total_bytes: FileSize
    mathematical: Literal['NOT_RUN']
    sources: Literal['NOT_RUN']
    independent_pedagogy: Literal['NOT_RUN']

    @model_validator(mode='after')
    def manifest_membership(self) -> Self:
        if self.run_id != self.source_job_id:
            raise ValueError('The manifest Run must be its actual source Job')
        _distinct([item.artifact_id for item in self.entries] + [item.entry_id for item in self.excluded])
        _distinct([item.logical_path for item in self.entries])
        if len(self.entries) + len(self.excluded) > 32:
            raise ValueError('The complete candidate file set is bounded to 32')
        if self.total_bytes != sum(item.size for item in self.entries):
            raise ValueError('Total bytes must equal the complete ordered accepted file set')
        return self


class CodexArtifactManifestView(CodexTurnModel):
    manifest: CodexArtifactManifest
    manifest_sha256: dm.Sha256

    @model_validator(mode='after')
    def canonical_manifest(self) -> Self:
        if self.manifest_sha256 != sha256_bytes(canonical_bytes(self.manifest)):
            raise ValueError('Manifest SHA must bind the complete immutable manifest')
        return self


class CodexArtifactImportWrite(CodexTurnModel):
    turn_id: dm.Id
    artifact_ids: Annotated[list[dm.Id], Field(min_length=1, max_length=32)]
    expected_manifest_sha256: dm.Sha256

    @model_validator(mode='after')
    def unique_selection(self) -> Self:
        _distinct(list(self.artifact_ids))
        return self


class CodexArtifactImportItem(CodexTurnModel):
    artifact_id: dm.Id
    source_sha256: dm.Sha256
    import_id: dm.Id
    job: dm.JobRef


class CodexArtifactImportView(CodexTurnModel):
    job: dm.JobRef
    session_id: dm.Id
    turn_id: dm.Id
    manifest_sha256: dm.Sha256
    actor_session_id: dm.Id
    items: Annotated[list[CodexArtifactImportItem], Field(min_length=1, max_length=32)]

    @model_validator(mode='after')
    def distinct_children(self) -> Self:
        _distinct([item.artifact_id for item in self.items])
        _distinct([item.import_id for item in self.items])
        _distinct([self.job.id] + [item.job.id for item in self.items])
        return self
