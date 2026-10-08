"""Complete-input admission for an explicitly registered synthetic protocol peer.

This is not a production CLI profile. No process, socket, filesystem discovery,
real model tokenizer, credential, or HTTP registration is used here. The closed
peer language defines one input token per complete request octet, including its
entire private runtime envelope. Its upper-bound proof rounds that exact count
up to a multiple of eight. Neither rule applies to an actual model.

Only trusted application construction can install a registration. The Provider
owner must still check current source/secret/consent/dispatch history. Preparing
or verifying bytes does not authorize execution or enforce a dispatch ledger.
"""
from __future__ import annotations

import base64
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Final, Literal, Self

from pydantic import AfterValidator, BeforeValidator, ConfigDict, Field, TypeAdapter, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..codex_turn_dto import (
    CodexLocalToolBudget, CodexOutboundBudgetWrite, CodexTurnModel,
)
from ..provider_dto import (
    CostEstimate, FrozenOutboundBudget, LocalExactInputTokens, LocalUpperBoundInputTokens,
    NonEmpty, One, PositiveInt, ProviderConfigView, TrueOnly, Zero,
)
from ..infrastructure.database import utc_now
from ..infrastructure.provider_network import validate_endpoint
from .errors import ApiError

ADAPTER_VERSION: Final = 'codex-synthetic-request-v1'
CHECKER_VERSION: Final = 'codex-synthetic-byte-token-checker-v1'


def unavailable() -> ApiError:
    return ApiError(503, 'CODEX_INPUT_PROOF_UNAVAILABLE', '没有可核验的完整 Codex 输入证明。')


def changed() -> ApiError:
    return ApiError(409, 'CODEX_PROFILE_CHANGED', '冻结的 Codex 运行配置已改变。')


def exceeded() -> ApiError:
    return ApiError(409, 'CODEX_BUDGET_EXCEEDED', '完整 Codex 请求超过已冻结预算。')


class PrivateModel(CodexTurnModel):
    model_config = ConfigDict(frozen=True, revalidate_instances='always')


def _base64(value: str) -> str:
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError:
        raise ValueError('Canonical complete private bytes are required') from None
    if not raw or base64.b64encode(raw).decode('ascii') != value:
        raise ValueError('Canonical complete private bytes are required')
    return value


PrivateBytes = Annotated[str, Field(min_length=4, max_length=400000), AfterValidator(_base64)]


def _integer(value: object) -> object:
    if type(value) is not int:
        raise ValueError('An integer literal is required')
    return value


class CodexSyntheticClosure(PrivateModel):
    """Full bytes, not unverifiable SHA placeholders; never part of public DTOs."""
    version: Literal['codex-synthetic-private-closure-v1']
    peer_definition: PrivateBytes
    deployment: PrivateBytes
    protocol_schema: PrivateBytes
    configuration: PrivateBytes
    environment: PrivateBytes
    initialization: PrivateBytes
    resume: PrivateBytes
    turn: PrivateBytes
    network: PrivateBytes
    resources: PrivateBytes
    proof_evidence: PrivateBytes


class CodexRuntimeProfile(PrivateModel):
    version: Literal['codex-synthetic-runtime-profile-v1']
    implemented: TrueOnly
    bootstrap_sha256: dm.Sha256
    template_version: Literal['codex-local-task-v1']
    tools: CodexLocalToolBudget
    registration_id: dm.Id
    proof_sha256: dm.Sha256
    closure: CodexSyntheticClosure
    cpu_seconds: Annotated[Literal[60], BeforeValidator(_integer)]
    memory_bytes: Annotated[Literal[2147483648], BeforeValidator(_integer)]
    file_bytes: Annotated[Literal[16777216], BeforeValidator(_integer)]
    protocol_output_bytes: Annotated[Literal[16777216], BeforeValidator(_integer)]
    file_descriptors: Annotated[Literal[128], BeforeValidator(_integer)]
    processes: Annotated[Literal[16], BeforeValidator(_integer)]
    core_bytes: Zero
    command_network: Literal['denied']
    writable_area: Literal['turn_outputs']


class SyntheticInitialization(PrivateModel):
    method: Literal['synthetic/initialize']
    protocol: Literal['codex-synthetic-peer-v1']
    process: Literal['none']


class SyntheticResume(PrivateModel):
    method: Literal['synthetic/resume']
    bootstrap_sha256: dm.Sha256
    history_source: Literal['complete_turn_messages_only']
    directory_inputs: Literal['none']
    unknown_execution: Literal['forbidden']


class SyntheticToolDefinition(PrivateModel):
    name: Literal['command', 'file_change']
    approval: Literal['exact_operation_once']
    execution: Literal['protocol_data_only']
    network: Literal['denied']


class SyntheticTurn(PrivateModel):
    method: Literal['synthetic/turn']
    messages: Annotated[list[dm.GenerationMessage], Field(min_length=2, max_length=6)]
    evidence: Annotated[list[dm.EvidenceChunk], Field(max_length=8)]
    tools: CodexLocalToolBudget
    tool_definitions: Annotated[list[SyntheticToolDefinition], Field(max_length=2)]
    max_output_tokens: PositiveInt
    truncation: Literal['disabled']

    @model_validator(mode='after')
    def complete_input_shape(self) -> Self:
        # A system template, zero to two whole user/answer pairs, current user.
        expected = ['system'] + ['user', 'assistant'] * ((len(self.messages) - 2) // 2) + ['user']
        if [item.role for item in self.messages] != expected:
            raise ValueError('Only whole selected history pairs are supported')
        if len({canonical_bytes(item.ref) for item in self.evidence}) != len(self.evidence):
            raise ValueError('Evidence references must be distinct')
        definitions = ['command', 'file_change'] if self.tools.max_tool_calls else []
        if [item.name for item in self.tool_definitions] != definitions:
            raise ValueError('Tool definitions must match the complete tool budget')
        return self


class SyntheticCompleteRequest(PrivateModel):
    version: Literal['codex-synthetic-model-request-v1']
    adapter: Literal['codex_app_server']
    adapter_version: Literal['codex-synthetic-request-v1']
    endpoint: NonEmpty
    provider: ProviderConfigView
    runtime: CodexRuntimeProfile
    initialization: SyntheticInitialization
    resume: SyntheticResume
    turn: SyntheticTurn
    max_provider_calls: One
    max_search_calls: Zero
    retries: Zero
    redirects: Zero
    auxiliary_requests: Zero


class SyntheticCodexProof(PrivateModel):
    version: Literal['codex-synthetic-proof-v1']
    registration_id: dm.Id
    config: ProviderConfigView
    bootstrap_sha256: dm.Sha256
    model_versions: Annotated[list[NonEmpty], Field(min_length=1, max_length=16)]
    kind: Literal['local_exact', 'local_upper_bound']
    max_input_tokens: PositiveInt
    max_output_tokens: PositiveInt
    shared_context_tokens: PositiveInt | None
    valid_until: dm.UTC | None
    checker_version: Literal['codex-synthetic-byte-token-checker-v1']
    closure: CodexSyntheticClosure

    @model_validator(mode='after')
    def reviewed_synthetic_scope(self) -> Self:
        if (self.config.endpoint_policy != 'explicit_loopback'
                or self.config.adapter != 'official_responses'
                or not self.config.secret_present
                or self.config.model not in self.model_versions
                or any(not value.startswith('synthetic-') or '*' in value for value in self.model_versions)
                or len(set(self.model_versions)) != len(self.model_versions)):
            raise ValueError('Only explicit synthetic model and peer registrations are supported')
        _endpoint(self.config)
        if self.closure != _closure(self.model_dump(mode='json', exclude={'closure'})):
            raise ValueError('Complete synthetic closure differs from the reviewed protocol')
        return self

    @property
    def sha256(self) -> str:
        return sha256_bytes(canonical_bytes(self))

    @classmethod
    def create(cls, *, registration_id: str, config: ProviderConfigView, bootstrap_sha256: str,
               model_versions: list[str], kind: Literal['local_exact', 'local_upper_bound'],
               max_input_tokens: int, max_output_tokens: int, shared_context_tokens: int | None,
               valid_until: str | None) -> SyntheticCodexProof:
        """Trusted test composition only; does not admit HTTP supplied material."""
        values = dict(version='codex-synthetic-proof-v1', registration_id=registration_id,
            config=config.model_dump(mode='json'), bootstrap_sha256=bootstrap_sha256,
            model_versions=model_versions, kind=kind, max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens, shared_context_tokens=shared_context_tokens,
            valid_until=valid_until, checker_version=CHECKER_VERSION)
        return cls.model_validate(values | {'closure': _closure(values)})


def _endpoint(config: ProviderConfigView) -> str:
    endpoint = validate_endpoint(config.base_url, config.endpoint_policy)
    host = f'[{endpoint.host}]' if ':' in endpoint.host else endpoint.host
    return f'{endpoint.scheme}://{host}:{endpoint.port}{endpoint.base_path}/codex-peer/model'


def _initialization() -> SyntheticInitialization:
    return SyntheticInitialization(method='synthetic/initialize', protocol='codex-synthetic-peer-v1', process='none')


def _resume(bootstrap: str) -> SyntheticResume:
    return SyntheticResume(method='synthetic/resume', bootstrap_sha256=bootstrap,
        history_source='complete_turn_messages_only', directory_inputs='none', unknown_execution='forbidden')


RESOURCE_VALUES = dict(cpu_seconds=60, memory_bytes=2147483648, file_bytes=16777216,
    protocol_output_bytes=16777216, file_descriptors=128, processes=16, core_bytes=0,
    command_network='denied', writable_area='turn_outputs')


def _blob(value: object) -> str:
    return base64.b64encode(canonical_bytes(value)).decode('ascii')


def _closure(values: dict) -> CodexSyntheticClosure:
    # These are a full, versioned protocol-peer equivalent, not host deployment
    # claims. No runtime library, environment, directory, or implicit history is
    # allowed to add input. An actual CLI would require a different registration.
    return CodexSyntheticClosure(version='codex-synthetic-private-closure-v1',
        peer_definition=_blob({'version': 'synthetic-peer-language-v1', 'binary': None,
            'input': 'canonical SyntheticCompleteRequest bytes', 'token': 'one raw request octet',
            'output_limit': 'turn.max_output_tokens', 'hidden_input': [], 'execution': 'protocol_data_only'}),
        deployment=_blob({'version': 'synthetic-deployment-v1', 'mode': 'in_memory_protocol_peer',
            'binary': None, 'libraries': [], 'processes_started': 0, 'files_read': [], 'files_written': []}),
        protocol_schema=_blob(SyntheticCompleteRequest.model_json_schema()),
        configuration=_blob(values),
        environment=_blob({'version': 'synthetic-environment-v1', 'variables': [], 'inherit': False,
            'working_directory': None, 'read_directories': [], 'external_configuration': []}),
        initialization=_blob(_initialization()), resume=_blob(_resume(values['bootstrap_sha256'])),
        turn=_blob({'version': 'synthetic-turn-shape-v1', 'schema': SyntheticTurn.model_json_schema(),
            'template_version': 'codex-local-task-v1', 'history': 'all_and_only_turn_messages',
            'files': 'all_and_only_turn_evidence', 'append_after_freeze': False}),
        network=_blob({'version': 'synthetic-network-v1', 'transport': 'in_memory_peer_only',
            'socket_creation': False, 'requests': 1, 'search': 0, 'retry': 0, 'redirect': 0,
            'auxiliary': 0, 'commands': 'denied', 'tools': 'denied'}),
        resources=_blob({'version': 'synthetic-resource-policy-v1', **RESOURCE_VALUES,
            'wall_seconds': 'exact_runtime_tools_wall_seconds', 'max_wall_seconds': 300,
            'enforcement': 'no_external_process_files_or_network',
            'host_execution_authorized': False, 'artifact_total_bytes': 16777216}),
        proof_evidence=_blob({'version': 'synthetic-complete-byte-proof-v1',
            'domain': 'only_complete_canonical_SyntheticCompleteRequest',
            'exact': 'Every raw request octet is one token by the synthetic peer language definition.',
            'upper_bound': '8*ceil(N/8)>=N for every nonnegative complete byte count N.',
            'capacity': 'N<=max_input; requested_output<=max_output; N+requested_output<=shared_if_present.',
            'invalidity': 'registry_absent_or_withdrawn_or_expired_or_any_binding_or_closure_changed',
            'production_model_claim': False}))


@dataclass(frozen=True)
class PreparedCodexRequest:
    body: bytes = field(repr=False)
    adapter_version: str
    input_character_count: int
    input_token_assurance: LocalExactInputTokens | LocalUpperBoundInputTokens
    cost_estimate: CostEstimate
    endpoint: str


class CodexProofRegistry:
    """Provider-owned, explicit construction seam; production defaults empty."""
    def __init__(self, proofs: Iterable[SyntheticCodexProof] = (), *, withdrawn_proofs: Iterable[str] = ()):
        self._withdrawn = frozenset(TypeAdapter(dm.Sha256).validate_python(value) for value in withdrawn_proofs)
        # Keep immutable canonical original bytes, not externally mutable models.
        self._proofs: dict[str, bytes] = {}
        names: set[str] = set()
        for value in proofs:
            if not isinstance(value, SyntheticCodexProof):
                raise ValueError('A named synthetic Codex proof is required')
            proof = SyntheticCodexProof.model_validate(strict_json(canonical_bytes(value)))
            if proof.bootstrap_sha256 in self._proofs or proof.registration_id in names:
                raise ValueError('Duplicate synthetic Codex proof registration')
            names.add(proof.registration_id)
            self._proofs[proof.bootstrap_sha256] = canonical_bytes(proof)

    def _resolve(self, bootstrap_sha256: str) -> SyntheticCodexProof | None:
        raw = self._proofs.get(bootstrap_sha256)
        if raw is None:
            return None
        proof = SyntheticCodexProof.model_validate(strict_json(raw))
        if (proof.sha256 in self._withdrawn or proof.valid_until is not None
                and datetime.fromisoformat(utc_now().replace('Z', '+00:00'))
                    >= datetime.fromisoformat(proof.valid_until.replace('Z', '+00:00'))):
            return None
        return proof

    def freeze(self, bootstrap_sha256: str, tools: CodexLocalToolBudget, *,
               config: ProviderConfigView | None = None) -> CodexRuntimeProfile | None:
        TypeAdapter(dm.Sha256).validate_python(bootstrap_sha256)
        tools = CodexLocalToolBudget.model_validate(strict_json(canonical_bytes(tools)))
        proof = self._resolve(bootstrap_sha256)
        if proof is None or config is not None and canonical_bytes(config) != canonical_bytes(proof.config):
            return None
        return CodexRuntimeProfile.model_validate(dict(version='codex-synthetic-runtime-profile-v1', implemented=True,
            bootstrap_sha256=bootstrap_sha256, template_version='codex-local-task-v1', tools=tools,
            registration_id=proof.registration_id, proof_sha256=proof.sha256, closure=proof.closure,
            **RESOURCE_VALUES))

    def current(self, profile: CodexRuntimeProfile) -> Literal['current', 'changed', 'unavailable']:
        if not isinstance(profile, CodexRuntimeProfile):
            return 'unavailable'
        try:
            profile = CodexRuntimeProfile.model_validate(strict_json(canonical_bytes(profile)))
            frozen = self.freeze(profile.bootstrap_sha256, profile.tools)
        except (ValueError, TypeError, KeyError):
            return 'unavailable'
        if frozen is None:
            return 'unavailable'
        return 'current' if canonical_bytes(frozen) == canonical_bytes(profile) else 'changed'

    def prepare(self, config: ProviderConfigView, profile: CodexRuntimeProfile,
                messages: list[dm.GenerationMessage], evidence: list[dm.EvidenceChunk],
                budget: CodexOutboundBudgetWrite) -> PreparedCodexRequest:
        state = self.current(profile)
        if state == 'unavailable':
            raise unavailable()
        if state == 'changed':
            raise changed()
        proof = self._resolve(profile.bootstrap_sha256)
        if proof is None or canonical_bytes(config) != canonical_bytes(proof.config):
            raise unavailable()
        try:
            budget = CodexOutboundBudgetWrite.model_validate(strict_json(canonical_bytes(budget)))
            definitions = [SyntheticToolDefinition(name=name, approval='exact_operation_once',
                execution='protocol_data_only', network='denied') for name in ('command', 'file_change')
                if profile.tools.max_tool_calls]
            turn = SyntheticTurn(method='synthetic/turn',
                messages=[dm.GenerationMessage.model_validate(item.model_dump()) for item in messages],
                evidence=[dm.EvidenceChunk.model_validate(item.model_dump()) for item in evidence],
                tools=profile.tools, tool_definitions=definitions, max_output_tokens=budget.max_output_tokens,
                truncation='disabled')
            request = SyntheticCompleteRequest(version='codex-synthetic-model-request-v1', adapter='codex_app_server',
                adapter_version=ADAPTER_VERSION, endpoint=_endpoint(config), provider=config, runtime=profile,
                initialization=_initialization(), resume=_resume(profile.bootstrap_sha256), turn=turn,
                max_provider_calls=1, max_search_calls=0, retries=0, redirects=0, auxiliary_requests=0)
            body = canonical_bytes(request)
            # Schema/decoder closure is itself frozen and strict, including all
            # referenced definitions; no hidden fields or reserialization later.
            if canonical_bytes(SyntheticCompleteRequest.model_validate(strict_json(body))) != body:
                raise ValueError('Noncanonical synthetic request')
        except (ValueError, TypeError, KeyError, AttributeError):
            raise unavailable() from None
        characters = sum(len(item.content) for item in turn.messages) + sum(
            len('<reference>\n' + canonical_bytes(item).decode() + '\n</reference>') for item in turn.evidence)
        bound = len(body) if proof.kind == 'local_exact' else ((len(body) + 7) // 8) * 8
        if (not 1 <= characters <= 12000 or bound > min(budget.max_input_tokens, proof.max_input_tokens)
                or budget.max_output_tokens > proof.max_output_tokens
                or proof.shared_context_tokens is not None
                    and bound + budget.max_output_tokens > proof.shared_context_tokens):
            raise exceeded()
        identity = dict(checker_version=proof.checker_version, proof_sha256=proof.sha256,
            request_body_sha256=sha256_bytes(body))
        assurance = (LocalExactInputTokens(kind='local_exact', input_tokens=bound, **identity)
            if proof.kind == 'local_exact' else LocalUpperBoundInputTokens(kind='local_upper_bound',
                input_tokens_upper_bound=bound, **identity))
        from .provider_budget import cost_estimate
        cost_budget = FrozenOutboundBudget(max_input_tokens=budget.max_input_tokens,
            max_output_tokens=budget.max_output_tokens, max_provider_calls=1, max_search_calls=0,
            max_tool_calls=0, timeout_seconds=profile.tools.wall_seconds, max_cost_usd=budget.max_cost_usd)
        try:
            cost = cost_estimate(config, bound, cost_budget)
        except ApiError:
            raise exceeded() from None
        return PreparedCodexRequest(body=body, adapter_version=ADAPTER_VERSION,
            input_character_count=characters, input_token_assurance=assurance, cost_estimate=cost,
            endpoint=request.endpoint)

    def verify(self, config: ProviderConfigView, profile: CodexRuntimeProfile,
               messages: list[dm.GenerationMessage], evidence: list[dm.EvidenceChunk],
               budget: CodexOutboundBudgetWrite, prepared: PreparedCodexRequest) -> None:
        current = self.prepare(config, profile, messages, evidence, budget)
        if current != prepared:
            raise ApiError(409, 'CODEX_SOURCE_CHANGED', '实际完整请求与冻结的 Codex 请求不一致。')
