"""An opt-in literal-only memory interpreter, never a host command sandbox.

Production construction registers nothing. This explicit synthetic language can
return at most 256 characters and has no file/process/network operation. Its
entire executable function has one argument and returns that argument unchanged.
The original model-request profile/bytes remain a separate immutable contract.
"""
from collections.abc import Iterable
from functools import partial
from typing import Annotated, Literal, Any
from types import CodeType, FunctionType, MethodType
import sys
import pydantic
from pydantic_core import SchemaValidator, SchemaSerializer

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
    version: Literal['codex-synthetic-literal-profile-v1', 'codex-synthetic-literal-profile-v2']
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
        return cls(version='codex-synthetic-literal-profile-v2', executable_sha256=content_sha256(runtime_executable_closure()),
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
        # An instance replacement is not the class code frozen by current().
        # Legacy v1 facts remain decodable but never regain an execution grant.
        if (type(self) is not CodexOperationRegistry or any(name in self.__dict__
                for name in ('prepare', 'projection', 'execute', 'available'))):
            return False
        try:
            return canonical_bytes(profile) in self._profiles and profile == LiteralOperationProfile.current()
        except (ApiError, TypeError, ValueError, RecursionError):
            return False

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
        return closure, self.projection(closure)

    @staticmethod
    def projection(closure: LiteralOperationClosure):
        operation = CodexCommandOperation(kind='command', command_text=canonical_bytes(closure.command).decode(), cwd='turn_outputs',
            executable_sha256=closure.profile.executable_sha256, environment_sha256=content_sha256({}), read_files=[],
            writable_area='turn_outputs', filesystem_scope_sha256=content_sha256({
                'version': 'codex-literal-namespace-v1', 'workspace_id': closure.workspace_id, 'turn_id': closure.turn_id,
                'namespace': 'turn_outputs', 'host_paths': [], 'files_read': [], 'files_written': []}),
            network='denied', operation_profile_sha256=content_sha256(closure.profile))
        return operation

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


def _code_value(value):
    """Path-independent identity of loaded owned code, not source on disk."""
    if isinstance(value, CodeType):
        return {'code': value.co_code.hex(), 'constants': [_code_value(item) for item in value.co_consts],
            'names': list(value.co_names), 'varnames': list(value.co_varnames),
            'freevars': list(value.co_freevars), 'cellvars': list(value.co_cellvars),
            'argcount': value.co_argcount, 'posonlyargcount': value.co_posonlyargcount,
            'kwonlyargcount': value.co_kwonlyargcount, 'flags': value.co_flags,
            'exceptiontable': value.co_exceptiontable.hex()}
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is bytes:
        return {'bytes': value.hex()}
    if type(value) is tuple:
        return {'tuple': [_code_value(item) for item in value]}
    if type(value) is frozenset and all(type(item) is str for item in value):
        return {'frozenset': sorted(value)}
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _code_value(item) for key, item in value.items()}
    raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '内存解释器代码闭包不可核验。')


def _function_binding(function):
    if isinstance(function, MethodType):
        function = function.__func__
    if type(function) is not FunctionType or function.__closure__:
        raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '内存解释器包装代码不可核验。')
    return {'code': _code_value(function.__code__), 'defaults': _code_value(function.__defaults__),
        'kwdefaults': _code_value(function.__kwdefaults__)}


def runtime_executable_closure() -> dict:
    """Freeze the actual interpreter and owned decoding/execution/receipt path.

    Python/Pydantic are fixed trusted runtime libraries, not a hostile process
    boundary. This profile grants no host action. Runtime code replacement is
    checked before a start/debit, rather than inferred from an earlier Git hash.
    """
    functions = {'literal': _literal, 'prepare': CodexOperationRegistry.prepare,
        'projection': CodexOperationRegistry.projection, 'execute': CodexOperationRegistry.execute,
        'canonical_bytes': canonical_bytes, 'strict_json': strict_json,
        'content_sha256': content_sha256, 'sha256_bytes': sha256_bytes, 'result_digest': result_digest}
    return {'version': 'codex-literal-runtime-closure-v2', 'interpreter': executable_closure(),
        'functions': {name: _function_binding(function) for name, function in functions.items()},
        'schemas': {model.__name__: model.model_json_schema() for model in
            (LiteralCommand, LiteralOperationClosure, LiteralOperationResult, CodexCommandOperation)},
        'project_dependencies': _project_dependencies(functions,
            (LiteralCommand, LiteralOperationClosure, LiteralOperationResult, CodexCommandOperation)),
        'model_validate': _function_binding(LiteralCommand.model_validate),
        'model_dump': _function_binding(LiteralOperationResult.model_dump),
        'python': list(sys.version_info[:3]), 'pydantic': pydantic.__version__}


def _project_dependencies(functions, models):
    """Traverse real loaded project globals and compiled model callables.

    A JSON schema alone omits Python validators. A function's globals belong to
    its defining module, not this module's same-named import. Compiler refs and
    file paths are not identity; actual validator/serializer code and config are.
    Standard-library and third-party internals remain explicit trusted runtime.
    """
    nodes: dict[str, Any] = {}
    identities: dict[str, Any] = {}
    def owned(value):
        return getattr(value, '__module__', '').startswith(('services.api.app.', 'packages.contracts.'))
    def label(value):
        return value.__module__+'.'+value.__qualname__
    def function(value):
        if isinstance(value, MethodType):
            value = value.__func__
        if not owned(value):
            return {'trusted_library': label(value)}
        key = 'function:'+label(value)
        if key in nodes:
            if identities[key] is not value:
                raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '项目代码标识冲突。')
            return {'ref': key}
        identities[key] = value
        nodes[key] = None
        bound = _function_binding(value)
        dependencies = {}
        for name in value.__code__.co_names:
            if name not in value.__globals__:
                continue
            dependency = value.__globals__[name]
            if isinstance(dependency, (FunctionType, MethodType)) and owned(dependency):
                dependencies[name] = function(dependency)
            elif isinstance(dependency, type) and issubclass(dependency, pydantic.BaseModel) and owned(dependency):
                dependencies[name] = model(dependency)
            elif type(dependency) in (str, int, bool, tuple, frozenset) or dependency is None:
                dependencies[name] = _code_value(dependency)
        nodes[key] = {'binding': bound, 'globals': dependencies}
        return {'ref': key}
    def core(value):
        if value is None or type(value) in (str, int, float, bool):
            return value
        if isinstance(value, dict):
            # Pydantic JSON-schema callbacks and pointer-address ref labels are
            # not validation. Actual referenced class/function nodes are below.
            return {key: (item.rsplit(':', 1)[0] if key in ('ref', 'schema_ref')
                and isinstance(item, str) and item.rsplit(':', 1)[-1].isdigit() else core(item))
                for key, item in value.items() if key != 'metadata'}
        if isinstance(value, (list, tuple)):
            return [core(item) for item in value]
        if type(value) is partial:
            return {'partial': core(value.func), 'args': core(value.args), 'keywords': core(value.keywords)}
        if isinstance(value, (FunctionType, MethodType)):
            return function(value)
        if isinstance(value, type):
            if issubclass(value, pydantic.BaseModel) and owned(value):
                return model(value)
            return {'trusted_type': label(value)}
        raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '模型执行闭包不可核验。')
    def model(value):
        key = 'model:'+label(value)
        if key in nodes:
            if identities[key] is not value:
                raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '模型代码标识冲突。')
            return {'ref': key}
        identities[key] = value
        nodes[key] = None
        validator, serializer = value.__pydantic_validator__, value.__pydantic_serializer__
        if type(validator) is not SchemaValidator or type(serializer) is not SchemaSerializer:
            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '模型执行器不可核验。')
        nodes[key] = {'validation': core(validator.__reduce__()[1]),
            'serialization': core(serializer.__reduce__()[1]),
            'constructor': _function_binding(value.__init__)}
        return {'ref': key}
    for value in functions.values():
        function(value)
    for value in models:
        model(value)
    return nodes
