"""Closed M6.1 application contracts from the sole PRODUCT_DESIGN 3.0.6.

Local shape and byte relationships do not establish authorization, source
ownership, immutable history, runtime safety, or approval. Owners check those
facts in their current transaction. Academic payloads are excluded from repr.
"""
from datetime import datetime, timedelta
import math

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from .provider_dto import TrueOnly, _omit_schema_default
from .import_dto import JobSnapshot
from .retrieval_dto import RetrievalProvenance
from .application.provider_models import UsageSnapshot
from pydantic.json_schema import SkipJsonSchema


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError('nonblank text is required')
    return value


def _unicode(value: object) -> None:
    if isinstance(value, str):
        try:
            value.encode('utf-8')
        except UnicodeError:
            raise ValueError('valid Unicode scalar values are required') from None
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


NonBlank = Annotated[str, Field(min_length=1), AfterValidator(_nonblank)]


class AuthoringModel(dm.StrictModel):
    model_config = ConfigDict(hide_input_in_errors=True, serialize_by_alias=True)

    def __repr_args__(self):
        return []

    @model_validator(mode='before')
    @classmethod
    def valid_unicode(cls, value: object) -> object:
        _unicode(value)
        return value


class AuthoringBlockRef(dm.ContentRef):
    entity: Literal['block']

    @model_validator(mode='before')
    @classmethod
    def core_value(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.ContentRef) else value


class AuthoringCandidate(dm.DraftCandidate):
    entity: Literal['block']

    @model_validator(mode='before')
    @classmethod
    def core_value(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.DraftCandidate) else value


def _distinct_refs(refs: list[AuthoringBlockRef]) -> list[AuthoringBlockRef]:
    identities = [(ref.entity, ref.id, ref.revision) for ref in refs]
    if len(set(identities)) != len(identities):
        raise ValueError('duplicate or conflicting exact source revisions are forbidden')
    return refs


BlockRefs = Annotated[list[AuthoringBlockRef], Field(max_length=8), AfterValidator(_distinct_refs)]


class AuthoringPrepareWrite(AuthoringModel):
    topic: Annotated[NonBlank, Field(max_length=4000)]
    prerequisites: Annotated[list[Annotated[NonBlank, Field(max_length=2000)]], Field(max_length=32)]
    objectives: Annotated[list[Annotated[NonBlank, Field(max_length=2000)]], Field(min_length=1, max_length=32)]
    proof_policy: Literal['full', 'declared_dependencies']
    output_kind: Literal['worked_example']
    source_refs: BlockRefs
    provider_id: dm.Id


FiniteNumber = Annotated[float, Field(allow_inf_nan=False)]
NonNegativeNumber = Annotated[FiniteNumber, Field(ge=0)]


class NumericVariable(AuthoringModel):
    name: Annotated[str, Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,31}$')]
    value: FiniteNumber
    unit: Annotated[NonBlank, Field(max_length=64)]


class NumericAssertion(AuthoringModel):
    id: dm.Id
    expression: Annotated[NonBlank, Field(max_length=512)]
    expected: FiniteNumber
    atol: NonNegativeNumber
    rtol: NonNegativeNumber
    unit: Annotated[NonBlank, Field(max_length=64)]


class NumericPlan(AuthoringModel):
    version: Literal['finite-arithmetic-v1']
    variables: Annotated[list[NumericVariable], Field(max_length=32)]
    assertions: Annotated[list[NumericAssertion], Field(min_length=1, max_length=32)]
    seed: None

    @model_validator(mode='after')
    def unique_names(self) -> Self:
        if (len({item.name for item in self.variables}) != len(self.variables)
                or len({item.id for item in self.assertions}) != len(self.assertions)):
            raise ValueError('variable names and assertion identities must each be unique')
        return self


class WorkedExampleSymbol(AuthoringModel):
    name: NonBlank
    tex: NonBlank
    domain: NonBlank
    dimension: NonBlank


class WorkedExamplePayload(AuthoringModel):
    version: Literal['worked-example-candidate-v1']
    kind: Literal['worked_example']
    title: Annotated[NonBlank, Field(max_length=300)]
    body_markdown: Annotated[NonBlank, Field(max_length=400000)]
    symbols: Annotated[list[WorkedExampleSymbol], Field(min_length=1, max_length=64)]
    declared_source_refs: BlockRefs
    numeric_plan: NumericPlan

    @model_validator(mode='after')
    def declared_symbols(self) -> Self:
        names = {symbol.name for symbol in self.symbols}
        if len(names) != len(self.symbols):
            raise ValueError('symbol names must be unique')
        if any(variable.name not in names for variable in self.numeric_plan.variables):
            raise ValueError('each numeric variable must be a declared symbol')
        return self


def parse_worked_example(raw: str | bytes) -> WorkedExamplePayload:
    """Parse the complete received object without repairs or ignored duplicate keys."""
    return WorkedExamplePayload.model_validate(strict_json(raw))


ApprovalDecision = dm.ApprovalDecision


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class NumericCheckPreviewWrite(AuthoringModel):
    candidate: AuthoringCandidate


class NumericRuntimeProfile(AuthoringModel):
    evaluator_version: Literal['finite-arithmetic-v1']
    evaluator_sha256: dm.Sha256
    runtime_manifest_sha256: dm.Sha256
    python_version: NonBlank
    sandbox_version: NonBlank
    wall_seconds: Literal[5]
    cpu_seconds: Literal[2]
    memory_bytes: Literal[268435456]
    output_bytes: Literal[65536]
    evaluator_process_limit: Literal[1]

    @field_validator('wall_seconds', 'cpu_seconds', 'memory_bytes', 'output_bytes', 'evaluator_process_limit', mode='before')
    @classmethod
    def integer_limits(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError('resource limits require integer literals, not booleans or floats')
        return value


class NumericAssertionResult(AuthoringModel):
    id: dm.Id
    actual: FiniteNumber | None
    passed: bool
    error_code: Literal['NUMERIC_DOMAIN_ERROR', 'NUMERIC_NONFINITE'] | None

    @model_validator(mode='after')
    def actual_or_error(self) -> Self:
        if self.error_code is not None:
            if self.actual is not None or self.passed:
                raise ValueError('an arithmetic error has no finite actual value and cannot pass')
        elif self.actual is None:
            raise ValueError('an evaluated assertion needs its finite actual value')
        return self


class NumericCheckResult(AuthoringModel):
    job_id: dm.Id
    input_sha256: dm.Sha256
    operation_sha256: dm.Sha256
    outcome: Literal['passed', 'mismatch', 'evaluation_error', 'timeout', 'resource_limit',
                     'cancelled', 'environment_unavailable', 'outcome_unknown']
    verdict: Literal['PASS', 'FAIL', 'BLOCKED']
    started_at: dm.UTC | None
    finished_at: dm.UTC
    exit_code: int | None
    assertions: Annotated[list[NumericAssertionResult], Field(max_length=32)]
    output_sha256: dm.Sha256 | None
    result_sha256: dm.Sha256

    @model_validator(mode='after')
    def result_facts(self) -> Self:
        verdict = 'PASS' if self.outcome == 'passed' else (
            'FAIL' if self.outcome in {'mismatch', 'evaluation_error'} else 'BLOCKED')
        if self.verdict != verdict:
            raise ValueError('numeric outcome and verdict disagree')
        if self.started_at is not None and _time(self.started_at) > _time(self.finished_at):
            raise ValueError('a result cannot finish before its actual start')
        if len({item.id for item in self.assertions}) != len(self.assertions):
            raise ValueError('an assertion may appear only once')
        if self.outcome in {'passed', 'mismatch', 'evaluation_error'}:
            if not self.assertions or self.started_at is None:
                raise ValueError('complete evaluation needs actual start and evaluated assertions')
            errors = any(item.error_code is not None for item in self.assertions)
            passing = all(item.passed for item in self.assertions)
            if ((self.outcome == 'passed' and not passing)
                    or (self.outcome == 'mismatch' and (passing or errors))
                    or (self.outcome == 'evaluation_error' and not errors)):
                raise ValueError('the outcome must preserve actual assertion results')
        if numeric_result_sha256(self) != self.result_sha256:
            raise ValueError('the result must match its complete canonical hash')
        return self


def numeric_result_sha256(result: NumericCheckResult | dict) -> str:
    value = result.model_dump(mode='json') if isinstance(result, NumericCheckResult) else dict(result)
    value.pop('result_sha256', None)
    return sha256_bytes(canonical_bytes(value))


def _check_assertions(plan: NumericPlan, result: NumericCheckResult) -> None:
    expected = {item.id: item for item in plan.assertions}
    actual_ids = [item.id for item in result.assertions]
    plan_ids = [item.id for item in plan.assertions]
    if result.outcome in {'passed', 'mismatch', 'evaluation_error'}:
        if actual_ids != plan_ids:
            raise ValueError('a complete evaluation must contain each original assertion in order')
    elif any(name not in expected for name in actual_ids):
        raise ValueError('partial results cannot invent assertions')
    for item in result.assertions:
        if item.error_code is not None:
            continue
        assertion = expected[item.id]
        assert item.actual is not None
        difference = abs(item.actual - assertion.expected)
        product = assertion.rtol * abs(assertion.expected)
        tolerance = assertion.atol + product
        if not all(math.isfinite(value) for value in (difference, product, tolerance)):
            raise ValueError('nonfinite comparison must be an actual numeric error, never a pass')
        if item.passed != (difference <= tolerance):
            raise ValueError('passed must match the fixed finite tolerance comparison')


class NumericCheckView(AuthoringModel):
    id: dm.Id
    revision: dm.Revision
    candidate: AuthoringCandidate
    plan: NumericPlan
    runtime: NumericRuntimeProfile
    operation_sha256: dm.Sha256
    decision: Literal['pending', 'approve_once', 'decline']
    created_at: dm.UTC
    expires_at: dm.UTC
    expired: bool
    job: dm.JobRef | None
    job_revision: dm.Revision | None
    result: NumericCheckResult | None
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def approval_and_execution(self) -> Self:
        if _time(self.expires_at) != _time(self.created_at) + timedelta(minutes=10):
            raise ValueError('a preview expires exactly ten minutes after creation')
        if self.revision != (1 if self.decision == 'pending' else 2):
            raise ValueError('the sole decision advances only the approval revision')
        approved = self.decision == 'approve_once'
        if (self.job is not None) != approved or (self.job_revision is not None) != approved:
            raise ValueError('only explicit approval has its separate actual job and revision')
        if self.result is not None:
            if self.job is None or self.job.status not in {'completed', 'failed', 'cancelled'}:
                raise ValueError('a result requires an actual terminal execution job')
            expected_status = ('completed' if self.result.outcome in {'passed', 'mismatch', 'evaluation_error'}
                               else 'cancelled' if self.result.outcome == 'cancelled' else 'failed')
            if (self.result.job_id != self.job.id or self.result.operation_sha256 != self.operation_sha256
                    or self.job.status != expected_status):
                raise ValueError('result must belong to this operation and actual terminal job')
            _check_assertions(self.plan, self.result)
        elif self.job is not None and self.job.status in {'completed', 'failed', 'cancelled'}:
            raise ValueError('the terminal job requires its same-transaction checked result')
        return self


class NumericCheckDecisionAck(AuthoringModel):
    id: dm.Id
    revision: dm.Revision
    operation_sha256: dm.Sha256
    decision: Literal['approve_once', 'decline']
    applied: TrueOnly
    job: dm.JobRef | None

    @model_validator(mode='after')
    def original_decision(self) -> Self:
        if self.revision != 2 or (self.job is not None) != (self.decision == 'approve_once'):
            raise ValueError('the original decision must bind revision two and its actual job')
        if self.job is not None and self.job.status != 'queued':
            raise ValueError('original approval ACK names the newly queued job, not its later status')
        return self


class AuthoringInputMaterial(AuthoringModel):
    ref: AuthoringBlockRef
    title: NonBlank
    body_sha256: dm.Sha256
    body_bytes: Annotated[int, Field(ge=1)]
    material_review: Literal['unreviewed']
    provenance: RetrievalProvenance


def _unique_materials(materials: list[AuthoringInputMaterial]) -> None:
    _distinct_refs([item.ref for item in materials])


class AuthoringPreparationSummary(AuthoringModel):
    context_snapshot_id: dm.Id
    snapshot_sha256: dm.Sha256
    job_input_sha256: dm.Sha256
    prepared_input_sha256: dm.Sha256
    character_count: Annotated[int, Field(ge=1, le=12000)]
    materials: Annotated[list[AuthoringInputMaterial], Field(max_length=8)]
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def exact_materials(self) -> Self:
        _unique_materials(self.materials)
        return self


class AuthoringValidation(AuthoringModel):
    # Keep the wire name exactly 'schema' without shadowing BaseModel.schema().
    schema_check: Literal['PASS', 'FAIL', 'NOT_RUN'] = Field(alias='schema')
    references: Literal['PASS', 'FAIL', 'NOT_RUN']
    symbol_declarations: Literal['PASS', 'FAIL', 'NOT_RUN']
    issues: list[dm.Warning]
    mathematical: Literal['NOT_RUN']
    sources: Literal['NOT_RUN']
    independent_pedagogy: Literal['NOT_RUN']

    def structure_passed(self) -> bool:
        return self.schema_check == self.references == self.symbol_declarations == 'PASS'


class AuthoringJobSummary(AuthoringModel):
    id: dm.Id
    kind: Literal['authoring']
    job_revision: dm.Revision
    status: Literal['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled']
    title: NonBlank
    candidate: AuthoringCandidate | None
    created_at: dm.UTC
    updated_at: dm.UTC

    @model_validator(mode='after')
    def persisted_candidate(self) -> Self:
        if (self.status == 'completed') != (self.candidate is not None):
            raise ValueError('only completed generation has its actual immutable candidate')
        if _time(self.updated_at) < _time(self.created_at):
            raise ValueError('job update cannot precede its creation')
        return self


class AuthoringPageQuery(AuthoringModel):
    cursor: NonBlank | SkipJsonSchema[None] = Field(
        default=None, exclude_if=lambda value: value is None, json_schema_extra=_omit_schema_default,
    )
    limit: Annotated[int, Field(ge=1, le=100)] = 20

    @model_validator(mode='before')
    @classmethod
    def omitted_cursor(cls, value: object) -> object:
        if isinstance(value, dict) and 'cursor' in value and value['cursor'] is None:
            raise ValueError('cursor may be omitted, not explicitly null')
        return value


class AuthoringJobPage(AuthoringModel):
    items: Annotated[list[JobSnapshot], Field(max_length=100)]
    next_cursor: NonBlank | None
    total_hint: Annotated[int, Field(ge=0)] | SkipJsonSchema[None] = Field(
        default=None, exclude_if=lambda value: value is None, json_schema_extra=_omit_schema_default,
    )

    @model_validator(mode='before')
    @classmethod
    def omitted_hint(cls, value: object) -> object:
        if isinstance(value, dict) and 'total_hint' in value and value['total_hint'] is None:
            raise ValueError('total_hint may be omitted, not explicitly null')
        return value

    @model_validator(mode='after')
    def safe_control_projection(self) -> Self:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('a control page cannot duplicate jobs')
        for item in self.items:
            if (item.kind not in {'authoring', 'authoring_numeric_check'}
                    or item.result_refs or item.warnings or item.error is not None
                    or item.progress.label != item.status):
                raise ValueError('control jobs must contain only fixed safe state fields')
        return self


class AuthoringJobView(AuthoringModel):
    summary: AuthoringJobSummary
    request: AuthoringPrepareWrite
    preparation: AuthoringPreparationSummary
    proposal_id: dm.Id | None
    consent_id: dm.Id | None
    provider_receipt_id: dm.Id | None
    provider_outcome: Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown'] | None
    usage: UsageSnapshot
    raw_answer: str | None
    raw_refusal: str | None
    validation: AuthoringValidation
    error_code: NonBlank | None

    @model_validator(mode='after')
    def original_generation_facts(self) -> Self:
        if self.request.source_refs != [item.ref for item in self.preparation.materials]:
            raise ValueError('every selected exact source must be prepared in original order')
        if self.consent_id is not None and self.proposal_id is None:
            raise ValueError('consent must be linked to its actual proposal')
        has_receipt = self.provider_receipt_id is not None
        if has_receipt and self.consent_id is None:
            raise ValueError('a provider receipt requires its original consent and proposal')
        if has_receipt != (self.provider_outcome is not None):
            raise ValueError('provider outcome requires its actual checked receipt')
        if not has_receipt and (self.raw_answer is not None or self.raw_refusal is not None):
            raise ValueError('raw output may only come from a checked provider receipt')
        completed = self.summary.status == 'completed'
        if completed != self.validation.structure_passed():
            raise ValueError('completed generation and all three structural passes must agree')
        if completed and (self.provider_outcome != 'completed' or self.raw_refusal
                          or not self.raw_answer or self.error_code is not None):
            raise ValueError('a candidate requires complete non-refusal output without a terminal error')
        if self.summary.status == 'failed' and self.error_code is None:
            raise ValueError('failed generation needs its safe error code')
        if self.summary.status not in {'failed', 'cancelled'} and self.error_code is not None:
            raise ValueError('a live or completed job cannot carry a terminal error')
        return self


def candidate_sha256(payload: WorkedExamplePayload) -> str:
    return sha256_bytes(canonical_bytes(payload))


def validate_candidate(candidate: AuthoringCandidate, payload: WorkedExamplePayload,
                       body_sha256: str, validation: AuthoringValidation) -> None:
    if (candidate.entity != 'block' or candidate.candidate_sha256 != candidate_sha256(payload)
            or body_sha256 != sha256_bytes(payload.body_markdown.encode('utf-8'))):
        raise ValueError('candidate payload and original body must match their distinct hashes')
    if not validation.structure_passed():
        raise ValueError('a valid candidate requires its actual structural checks')


def validate_declared_sources(payload: WorkedExamplePayload, materials: list[AuthoringInputMaterial]) -> None:
    allowed = {canonical_bytes(item.ref) for item in materials}
    if any(canonical_bytes(ref) not in allowed for ref in payload.declared_source_refs):
        raise ValueError('declared references must come from the actual prepared exact materials')


class AuthoringDraftView(AuthoringModel):
    owner: Literal['authoring']
    candidate: AuthoringCandidate
    source_job_id: dm.Id
    state: Literal['draft']
    base_ref: None
    body_sha256: dm.Sha256
    payload: WorkedExamplePayload
    validation: AuthoringValidation
    numeric_check_ids: Annotated[list[dm.Id], Field(max_length=100)]
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def immutable_candidate(self) -> Self:
        validate_candidate(self.candidate, self.payload, self.body_sha256, self.validation)
        if len(set(self.numeric_check_ids)) != len(self.numeric_check_ids):
            raise ValueError('each numerical preview identity is independent and unique')
        return self
