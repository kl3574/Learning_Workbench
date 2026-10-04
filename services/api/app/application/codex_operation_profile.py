"""An opt-in literal-only memory interpreter, never a host command sandbox.

Production construction registers nothing. This explicit synthetic language can
return at most 256 characters and has no file/process/network operation. Its
entire executable function has one argument and returns that argument unchanged.
The original model-request profile/bytes remain a separate immutable contract.
"""
from collections.abc import Iterable
from typing import Annotated, Literal

from pydantic import Field
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..codex_turn_dto import CodexCommandOperation
from ..serialization import content_sha256
from .errors import ApiError


class LiteralCommand(dm.StrictModel):
    version: Literal['codex-synthetic-literal-command-v1']
    text: Annotated[str, Field(max_length=256)]


def _literal(text: str) -> str:
    return text


def executable_closure() -> dict:
    """Actual checked code object; no source path, binary read or hidden input."""
    code = _literal.__code__
    if (code.co_argcount != 1 or code.co_kwonlyargcount != 0 or code.co_names
            or code.co_freevars or code.co_cellvars or code.co_consts != (None,)):
        raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '固定内存解释器不可用。')
    return {'version': 'codex-literal-code-closure-v1', 'bytecode_hex': code.co_code.hex(),
        'argument_count': code.co_argcount, 'constants': [None], 'names': [], 'freevars': [],
        'semantics': 'return the same exact str; no calls, imports, loops or effects'}


class LiteralOperationProfile(dm.StrictModel):
    version: Literal['codex-synthetic-literal-profile-v1']
    executable_sha256: dm.Sha256
    command_schema_sha256: dm.Sha256
    max_characters: Literal[256]
    shell: None
    environment: dict[Literal['no_environment_variables'], Literal[True]]
    filesystem: Literal['no_host_files; private in-memory turn_outputs namespace only']
    network: Literal['denied']
    subprocesses: Literal[0]
    actual_cli_claim: Literal[False]

    @classmethod
    def current(cls):
        return cls(version='codex-synthetic-literal-profile-v1', executable_sha256=content_sha256(executable_closure()),
            command_schema_sha256=content_sha256(LiteralCommand.model_json_schema()), max_characters=256,
            shell=None, environment={'no_environment_variables': True},
            filesystem='no_host_files; private in-memory turn_outputs namespace only', network='denied',
            subprocesses=0, actual_cli_claim=False)


class LiteralOperationClosure(dm.StrictModel):
    version: Literal['codex-synthetic-literal-operation-v1']
    profile: LiteralOperationProfile
    argv: Annotated[list[str], Field(min_length=2, max_length=2)]
    environment: dict[str, str]
    workspace_id: dm.Id
    turn_id: dm.Id
    output_namespace: Literal['turn_outputs']
    command: LiteralCommand


class LiteralOperationResult(dm.StrictModel):
    version: Literal['codex-synthetic-literal-result-v1']
    operation_sha256: dm.Sha256
    text: Annotated[str, Field(max_length=256)]
    host_actions: Literal[0]
    provider_requests: Literal[0]
    files_written: Literal[0]


class CodexOperationRegistry:
    """Trusted composition only. No HTTP registration or ambient default."""
    def __init__(self, registrations: Iterable[LiteralOperationProfile] = ()):
        self._profiles = tuple(canonical_bytes(item) for item in registrations)
        if len(self._profiles) != len(set(self._profiles)):
            raise ValueError('Duplicate fixed operation profile')

    def available(self, profile: LiteralOperationProfile) -> bool:
        return canonical_bytes(profile) in self._profiles and profile == LiteralOperationProfile.current()

    def prepare(self, workspace: str, turn: str, text: str):
        if not self._profiles:
            return None
        profile = LiteralOperationProfile.current()
        if not self.available(profile):
            return None
        try:
            command = LiteralCommand.model_validate(strict_json(text))
        except (ValueError, TypeError, RecursionError):
            return None
        if canonical_bytes(command).decode() != text:
            return None
        closure = LiteralOperationClosure(version='codex-synthetic-literal-operation-v1', profile=profile,
            argv=['synthetic-memory-literal-v1', command.text], environment={}, workspace_id=workspace,
            turn_id=turn, output_namespace='turn_outputs', command=command)
        operation = CodexCommandOperation(kind='command', command_text=text, cwd='turn_outputs',
            executable_sha256=profile.executable_sha256, environment_sha256=content_sha256({}), read_files=[],
            writable_area='turn_outputs', filesystem_scope_sha256=content_sha256({
                'version': 'codex-literal-namespace-v1', 'workspace_id': workspace, 'turn_id': turn,
                'namespace': 'turn_outputs', 'host_paths': [], 'files_read': [], 'files_written': []}),
            network='denied', operation_profile_sha256=content_sha256(profile))
        return closure, operation

    def execute(self, closure: LiteralOperationClosure, operation_sha256: str) -> LiteralOperationResult:
        if not self.available(closure.profile):
            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '原内存解释器已不可用。')
        original = self.prepare(closure.workspace_id, closure.turn_id, canonical_bytes(closure.command).decode())
        if original is None or original[0] != closure:
            raise ApiError(409, 'CODEX_BINDING_INVALID', '原完整内存操作绑定不一致。')
        # This is the whole interpreter. Never eval/exec/shell user input.
        text = _literal(closure.command.text)
        if type(text) is not str or text != closure.command.text:
            raise ApiError(409, 'CODEX_OUTCOME_UNKNOWN', '内存操作结果不符合固定解释语义。')
        return LiteralOperationResult(version='codex-synthetic-literal-result-v1',
            operation_sha256=operation_sha256, text=text, host_actions=0, provider_requests=0, files_written=0)


def result_digest(result: LiteralOperationResult) -> str:
    return sha256_bytes(canonical_bytes(result))
