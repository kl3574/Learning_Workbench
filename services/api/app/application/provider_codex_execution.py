"""Single-request gate for a trusted, pure synthetic protocol peer only.

There is no default transport, production adapter, process, command, file access
or networking here. Injected Python callables are trusted test composition, NOT
a host sandbox. Wall checks bracket calls; they cannot forcibly interrupt a
blocking callable or prove CPU/memory/process limits. The outer Provider owner
must persist its real start permit first and recheck source/proof/secret/lease/
consent/actor/policy/deadline through before_request. This gate's call count is
actual transport entries, not the outer durable conservative reservation.
"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import math
from threading import Lock
from time import monotonic
from typing import Annotated, Literal, NoReturn, Protocol, Self

from pydantic import ConfigDict, Field, TypeAdapter, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..codex_turn_dto import CodexFrozenOutboundSummary, CodexTurnModel, SafeCode
from ..provider_dto import LocalExactInputTokens
from .errors import ApiError
from .provider_codex_profile import (
    ADAPTER_VERSION, CHECKER_VERSION, RESOURCE_VALUES, CodexRuntimeProfile,
    PreparedCodexRequest, SyntheticCompleteRequest,
)
from .provider_models import UsageSnapshot


class SyntheticCodexResponse(CodexTurnModel):
    """A complete synthetic response; token means one raw input/output octet."""
    model_config = ConfigDict(frozen=True, revalidate_instances='always')
    version: Literal['codex-synthetic-response-v1']
    outcome: Literal['completed', 'failed']
    answer: Annotated[str, Field(max_length=400000)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    error_code: Literal['CODEX_OPERATION_FAILED'] | None

    @model_validator(mode='after')
    def terminal_error(self) -> Self:
        if (self.outcome == 'completed') != (self.error_code is None):
            raise ValueError('A completed response has no error; failure requires its closed error')
        return self


class CodexExecutionResult(CodexTurnModel):
    model_config = ConfigDict(frozen=True)
    version: Literal['codex-synthetic-execution-result-v1']
    outcome: Literal['completed', 'failed', 'unknown']
    answer: Annotated[str, Field(max_length=400000)]
    output_state: Literal['none', 'partial', 'complete']
    usage: UsageSnapshot
    error_code: SafeCode | None
    consumed_provider_calls: Annotated[int, Field(ge=0, le=1)]
    first_response: SyntheticCodexResponse | None
    first_response_sha256: dm.Sha256 | None

    @model_validator(mode='after')
    def terminal_facts(self) -> Self:
        if (self.outcome == 'completed') != (self.error_code is None):
            raise ValueError('Only completed execution has no error')
        if self.outcome == 'completed' and (self.consumed_provider_calls != 1 or self.first_response_sha256 is None):
            raise ValueError('Completion requires a real checked response')
        if self.first_response is not None and self.consumed_provider_calls != 1:
            raise ValueError('A retained response requires one consumed provider call')
        if self.first_response is None:
            if self.first_response_sha256 is not None or self.answer or self.usage != UsageSnapshot(input_tokens=None, output_tokens=None):
                raise ValueError('Response facts require their complete original response')
        elif (self.first_response_sha256 != sha256_bytes(canonical_bytes(self.first_response))
                or self.answer != self.first_response.answer or self.usage != UsageSnapshot(
                    input_tokens=self.first_response.input_tokens, output_tokens=self.first_response.output_tokens)):
            raise ValueError('Retained response facts must agree with their original bytes')
        expected = 'none' if not self.answer else ('complete' if self.outcome == 'completed' else 'partial')
        if self.output_state != expected:
            raise ValueError('Failed execution cannot label retained output complete')
        return self


SyntheticTransport = Callable[[bytes, str, int], bytes]


class CodexRequestGate(Protocol):
    def request(self, body: bytes, *, endpoint: str, max_output_tokens: int) -> SyntheticCodexResponse: ...


def _checked_binding(prepared: PreparedCodexRequest, summary: CodexFrozenOutboundSummary,
                     profile: CodexRuntimeProfile) -> None:
    if type(prepared.body) is not bytes:
        raise ValueError('The complete raw request must be immutable bytes')
    request = SyntheticCompleteRequest.model_validate(strict_json(prepared.body))
    assurance = prepared.input_token_assurance
    actual_bound = len(prepared.body)
    if isinstance(assurance, LocalExactInputTokens):
        claimed_bound = assurance.input_tokens
    else:
        claimed_bound = assurance.input_tokens_upper_bound
        actual_bound = ((actual_bound + 7) // 8) * 8
    if (canonical_bytes(request) != prepared.body or canonical_bytes(request.runtime) != canonical_bytes(profile)
            or summary.runtime.profile_sha256 != sha256_bytes(canonical_bytes(profile))
            or summary.runtime.model_dump(exclude={'profile_sha256'}) != RESOURCE_VALUES
            or summary.tools != profile.tools or request.turn.tools != profile.tools
            or prepared.adapter_version != ADAPTER_VERSION or summary.adapter_version != ADAPTER_VERSION
            or prepared.endpoint != summary.endpoint or request.endpoint != prepared.endpoint
            or request.provider.id != summary.provider_id or request.provider.revision != summary.provider_revision
            or request.provider.config_sha256 != summary.config_sha256 or request.provider.model != summary.model
            or request.provider.endpoint_policy != summary.endpoint_policy
            or request.resume.bootstrap_sha256 != profile.bootstrap_sha256
            or request.turn.max_output_tokens != summary.budget.max_output_tokens
            or prepared.input_token_assurance != summary.input_token_assurance
            or assurance.request_body_sha256 != sha256_bytes(prepared.body)
            or summary.request_body_sha256 != assurance.request_body_sha256
            or assurance.proof_sha256 != profile.proof_sha256 or assurance.checker_version != CHECKER_VERSION
            or claimed_bound != actual_bound or claimed_bound > summary.budget.max_input_tokens
            or prepared.cost_estimate != summary.cost_estimate
            or prepared.input_character_count != summary.input_character_count
            or len(request.turn.messages) != len(summary.messages)
            or len(request.turn.evidence) != len(summary.references)):
        raise ValueError('The actual request must match its complete frozen bindings')
    for actual, frozen in zip(request.turn.messages, summary.messages, strict=True):
        if (actual.role != frozen.role or len(actual.content) != frozen.character_count
                or sha256_bytes(actual.content.encode()) != frozen.content_sha256):
            raise ValueError('The complete frozen messages differ')
    for material, reference in zip(request.turn.evidence, summary.references, strict=True):
        if (material.ref != reference.ref or material.locator != reference.locator
                or len(material.text) != reference.character_count
                or sha256_bytes(material.text.encode()) != reference.excerpt_sha256):
            raise ValueError('The complete frozen evidence differs')
    characters = sum(len(item.content) for item in request.turn.messages) + sum(
        len('<reference>\n' + canonical_bytes(item).decode() + '\n</reference>') for item in request.turn.evidence)
    if characters != prepared.input_character_count:
        raise ValueError('The complete frozen character count differs')


class _Gate:
    def __init__(self, prepared: PreparedCodexRequest, summary: CodexFrozenOutboundSummary,
                 transport: SyntheticTransport, clock: Callable[[], float],
                 before_request: Callable[[], None] | None):
        self.prepared, self.summary, self.transport = prepared, summary, transport
        self.clock, self.before_request = clock, before_request
        self.lock = Lock()
        self.requested = False
        self.closed = False
        self.calls = 0
        self.response: SyntheticCodexResponse | None = None
        self.response_sha: str | None = None
        self.error: SafeCode | None = None
        self.outcome: Literal['failed', 'unknown'] = 'failed'
        self.started = self.last_clock = clock()

    def fail(self, code: SafeCode, *, unknown: bool = False, replace: bool = False) -> None:
        with self.lock:
            if self.error is None or replace:
                self.error = code
                self.outcome = 'unknown' if unknown else 'failed'

    def reject(self, code: SafeCode, *, unknown: bool = False, replace: bool = False) -> NoReturn:
        self.fail(code, unknown=unknown, replace=replace)
        raise ApiError(409, code, '受控 Codex 请求已被安全阻止。')

    def wall(self, *, unknown: bool = False) -> None:
        now = self.clock()
        if (type(now) not in {int, float} or not math.isfinite(now)
                or type(self.started) not in {int, float} or not math.isfinite(self.started)
                or now < self.last_clock):
            self.reject('CODEX_RUNTIME_UNAVAILABLE')
        self.last_clock = now
        if now - self.started >= self.summary.tools.wall_seconds:
            self.reject('CODEX_TIMEOUT', unknown=unknown)

    def request(self, body: bytes, *, endpoint: str, max_output_tokens: int) -> SyntheticCodexResponse:
        with self.lock:
            duplicate = self.requested or self.closed
            self.requested = True
        if duplicate:
            self.reject('CODEX_NEW_OUTBOUND_CONSENT_REQUIRED', replace=True)
        if (type(body) is not bytes or body != self.prepared.body or endpoint != self.prepared.endpoint
                or type(max_output_tokens) is not int or max_output_tokens != self.summary.budget.max_output_tokens):
            self.reject('CODEX_BINDING_INVALID')
        self.wall()
        if self.before_request is not None:
            try:
                self.before_request()
            except ApiError as error:
                try:
                    code: SafeCode = TypeAdapter(SafeCode).validate_python(error.code)
                except ValueError:
                    self.reject('CODEX_OUTCOME_UNKNOWN', unknown=True)
                self.reject(code)
            except Exception:
                self.reject('CODEX_OUTCOME_UNKNOWN', unknown=True)
        self.wall()
        with self.lock:
            # A reentrant/concurrent rejected request latches a failure even if
            # the trusted peer swallows its exception before this boundary.
            if self.error is not None:
                raise ApiError(409, self.error, '受控 Codex 请求已被安全阻止。')
            self.calls = 1
        try:
            raw = self.transport(body, endpoint, max_output_tokens)
        except Exception:
            self.wall(unknown=True)
            self.reject('CODEX_OUTCOME_UNKNOWN', unknown=True)
        try:
            if type(raw) is not bytes or len(raw) > self.summary.runtime.protocol_output_bytes:
                raise ValueError('A bounded raw synthetic response is required')
            response = SyntheticCodexResponse.model_validate(strict_json(raw))
            if canonical_bytes(response) != raw:
                raise ValueError('A canonical closed response is required')
        except (ValueError, TypeError, KeyError, RecursionError):
            self.reject('CODEX_PROTOCOL_INVALID')
        # Keep the first typed response, including reported usage, even when a
        # subsequent budget/consistency/deadline or extra-call check fails.
        with self.lock:
            self.response, self.response_sha = response, sha256_bytes(raw)
        self.wall()
        actual_output = len(response.answer.encode())
        assurance = self.prepared.input_token_assurance
        bound = assurance.input_tokens if isinstance(assurance, LocalExactInputTokens) else assurance.input_tokens_upper_bound
        if (response.input_tokens > min(bound, self.summary.budget.max_input_tokens)
                or response.output_tokens > max_output_tokens or actual_output > max_output_tokens):
            self.reject('CODEX_BUDGET_EXCEEDED')
        if response.input_tokens != len(body) or response.output_tokens != actual_output:
            self.reject('PROVIDER_USAGE_INCONSISTENT')
        if response.outcome == 'failed':
            self.reject('CODEX_OPERATION_FAILED')
        return response

    def result(self) -> CodexExecutionResult:
        with self.lock:
            self.closed = True
            if self.error is None and self.response is None:
                self.error = 'CODEX_PROTOCOL_INVALID'
            answer = self.response.answer if self.response is not None else ''
            outcome = self.outcome if self.error is not None else 'completed'
            return CodexExecutionResult(version='codex-synthetic-execution-result-v1', outcome=outcome,
                answer=answer, output_state='none' if not answer else ('complete' if outcome == 'completed' else 'partial'),
                usage=UsageSnapshot(input_tokens=self.response.input_tokens if self.response else None,
                    output_tokens=self.response.output_tokens if self.response else None),
                error_code=self.error, consumed_provider_calls=self.calls,
                first_response=self.response, first_response_sha256=self.response_sha)


class SyntheticCodexExecution:
    """One in-memory execution instance; durable uniqueness belongs to Provider."""
    def __init__(self, prepared: PreparedCodexRequest, summary: CodexFrozenOutboundSummary,
                 profile: CodexRuntimeProfile, *, transport: SyntheticTransport | None = None,
                 clock: Callable[[], float] = monotonic):
        self._prepared = deepcopy(prepared)
        self._summary = deepcopy(summary)
        self._profile = deepcopy(profile)
        self._transport, self._clock = transport, clock
        self._lock = Lock()
        self._started = False
        self._gate: _Gate | None = None

    @staticmethod
    def _unstarted(code: SafeCode, *, unknown: bool = False) -> CodexExecutionResult:
        return CodexExecutionResult(version='codex-synthetic-execution-result-v1',
            outcome='unknown' if unknown else 'failed', answer='', output_state='none',
            usage=UsageSnapshot(input_tokens=None, output_tokens=None), error_code=code,
            consumed_provider_calls=0, first_response=None, first_response_sha256=None)

    def run(self, peer: Callable[[CodexRequestGate], None] | None = None, *,
            before_request: Callable[[], None] | None = None) -> CodexExecutionResult:
        with self._lock:
            if self._started:
                if self._gate is None:
                    return self._unstarted('CODEX_NEW_OUTBOUND_CONSENT_REQUIRED')
                self._gate.fail('CODEX_NEW_OUTBOUND_CONSENT_REQUIRED', replace=True)
                return self._gate.result()
            self._started = True
        try:
            summary = CodexFrozenOutboundSummary.model_validate(strict_json(canonical_bytes(self._summary)))
            profile = CodexRuntimeProfile.model_validate(strict_json(canonical_bytes(self._profile)))
            _checked_binding(self._prepared, summary, profile)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            return self._unstarted('CODEX_BINDING_INVALID')
        if self._transport is None:
            return self._unstarted('CODEX_RUNTIME_UNAVAILABLE')
        try:
            gate = _Gate(self._prepared, summary, self._transport, self._clock, before_request)
            self._gate = gate
            gate.wall()
            if peer is None:
                gate.request(self._prepared.body, endpoint=self._prepared.endpoint,
                    max_output_tokens=summary.budget.max_output_tokens)
            else:
                peer(gate)
            gate.wall()
        except ApiError as error:
            if self._gate is None:
                return self._unstarted('CODEX_OUTCOME_UNKNOWN', unknown=True)
            try:
                safe: SafeCode = TypeAdapter(SafeCode).validate_python(error.code)
            except ValueError:
                safe = 'CODEX_OUTCOME_UNKNOWN'
            self._gate.fail(safe, unknown=safe == 'CODEX_OUTCOME_UNKNOWN')
        except Exception:
            if self._gate is None:
                return self._unstarted('CODEX_OUTCOME_UNKNOWN', unknown=True)
            self._gate.fail('CODEX_OUTCOME_UNKNOWN', unknown=True)
        return self._gate.result()
