"""Pinned zero-model control bootstrap. Inspection never starts a child.

Only initialize/initialized/thread-start bytes fixed in the preparation can be
sent. The existing external fence remains mandatory; no account/login/turn/tool
method is available here, and failure cannot select a weaker profile.
"""
import ctypes
from importlib.metadata import distribution
import os
from pathlib import Path
import platform
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import sysconfig
import time
from typing import Literal

from jsonschema import Draft7Validator  # type: ignore[import-untyped]

from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.codex_bootstrap_models import BootstrapFreeze, BootstrapOutcome, uncertain_outcome
from ..application.errors import ApiError
from ..codex_bootstrap_dto import CodexBootstrapScope
from ..serialization import canonical_json, content_sha256
from .codex_probe import ADAPTER_VERSION, CONFIG, PINNED_BYTES, PINNED_SHA256, sealed_binary, _private_directory

PROFILE_VERSION = 'codex-local-control-profile-v2'
MODEL = 'gpt-5.4'
WALL_SECONDS, OUTPUT_BYTES, REAP_SECONDS = 8, 65536, 2
RESOURCES = {'wall_seconds': WALL_SECONDS, 'cpu_seconds': 5, 'address_space_bytes': 2 * 1024**3,
             'file_size_bytes': 16 * 1024**2, 'descriptors': 128, 'core_bytes': 0,
             'combined_output_bytes': OUTPUT_BYTES, 'cleanup': 'SIGKILL-owned-group-wait-close-pipes', 'reap_seconds': REAP_SECONDS,
             'parent_death': 'SIGKILL-before-fence-and-exec'}
# Historical decoders are deliberately independent from current admission
# settings. A future profile adds a decoder; it must not reinterpret old ACKs.
HISTORICAL_RESOURCES = {'wall_seconds': 8, 'cpu_seconds': 5, 'address_space_bytes': 2147483648,
    'file_size_bytes': 16777216, 'descriptors': 128, 'core_bytes': 0, 'combined_output_bytes': 65536,
    'cleanup': 'SIGKILL-owned-group-wait-close-pipes', 'reap_seconds': 2}
PROFILE_DEFINITIONS = {
    'codex-local-control-profile-v1': HISTORICAL_RESOURCES,
    'codex-local-control-profile-v2': {**HISTORICAL_RESOURCES, 'parent_death': 'SIGKILL-before-fence-and-exec'},
}
HISTORICAL_CONFIG_SHA256 = 'bff46532b53a7592511dbe2a39bdcf39eae764cd7b12b6f66f2ca8c3bcb621e3'
HISTORICAL_SCHEMAS = {'ThreadStartParams.json': 'e9c6d3cc18d049bfbc0249add3808fb8e5a27e1a0b5a423767aafbc3859a9428',
                 'ThreadStartResponse.json': '70d9c9a3a064edb76662ec7cd066d142ed9252b768272bc3a7d00788386755c0'}
SCHEMA_HASHES = dict(HISTORICAL_SCHEMAS)
LAUNCHER_PREFIX = ('import ctypes, os, signal\n'
    'control_parent = os.getppid()\n'
    'if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0) != 0:\n'
    '    raise SystemExit(126)\n'
    'if os.getppid() != control_parent:\n'
    '    raise SystemExit(126)\n')


def unavailable() -> ApiError:
    return ApiError(503, 'CODEX_BOOTSTRAP_UNAVAILABLE', '当前受限本地控制环境不可用；没有降低隔离设置。')


def _read_regular(path: Path, maximum: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise unavailable()
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise unavailable()
        return raw


def _member(path: Path, maximum: int = 32 * 1024**2) -> dict:
    raw = _read_regular(path, maximum)
    return {'path': str(path), 'size': len(raw), 'sha256': sha256_bytes(raw)}


def _frames(broker: Path, model: str = 'gpt-5.4') -> list[str]:
    messages = [
        {'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'learning_workbench_bootstrap', 'version': '0.1.0'},
            'capabilities': {'experimentalApi': False, 'explicitGatewayOauth': True,
                             'optOutNotificationMethods': ['remoteControl/status/changed']}}},
        {'method': 'initialized', 'params': {}},
        {'id': 2, 'method': 'thread/start', 'params': {'approvalPolicy': 'never', 'approvalsReviewer': 'user',
            'baseInstructions': '', 'developerInstructions': '', 'config': {}, 'cwd': str(broker / 'workspace'),
            'ephemeral': False, 'model': model, 'modelProvider': 'openai', 'personality': 'none',
            'sandbox': 'read-only', 'serviceName': None, 'serviceTier': None, 'sessionStartSource': None, 'threadSource': None}},
    ]
    return [(canonical_bytes(message) + b'\n').decode() for message in messages]


def _environment(broker: Path) -> dict[str, str]:
    return {'PATH': '/bin:/usr/bin', 'HOME': str(broker / 'os-home'), 'CODEX_HOME': str(broker / 'home'),
            'XDG_CONFIG_HOME': str(broker / 'os-home'), 'XDG_CACHE_HOME': str(broker / 'os-home'),
            'XDG_DATA_HOME': str(broker / 'os-home'), 'TMPDIR': str(broker / 'tmp'),
            'LANG': 'C.UTF-8', 'TOKIO_WORKER_THREADS': '2'}


def _launcher_source() -> str:
    # Execute these exact frozen source bytes with -c. Replacing a launcher file
    # after approval cannot redirect the pre-exec fence. Parent loss terminates
    # the one child; restart recovery never treats a missing process as unused.
    return LAUNCHER_PREFIX + _read_regular(Path(__file__).with_name('codex_probe_isolation.py'), 64 * 1024).decode()


def _directory_binding(path: Path) -> dict:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise unavailable()
    return {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid, 'mode': stat.S_IMODE(info.st_mode)}


def _deployment() -> list[dict]:
    """Hash the Python/fence startup closure without executing ldd or a CLI.

    This is the installed trusted supervisor closure, not permission to expose
    these files to the CLI: Landlock is applied before the sealed CLI exec.
    """
    standard = Path(sysconfig.get_path('stdlib')).resolve(strict=True)
    paths = {Path(sys.executable).resolve(strict=True), Path(__file__),
             Path(__file__).with_name('codex_probe.py'), Path(__file__).with_name('codex_probe_isolation.py')}
    application = Path(__file__).parents[1]
    repository = application.parents[2]
    paths.update(application / relative for relative in (
        'codex_bootstrap_dto.py', 'serialization.py', 'application/codex_bootstrap_models.py',
        'application/codex_bootstrap_ports.py', 'application/errors.py', 'infrastructure/authoring_numeric_runtime.py'))
    paths.update(repository / relative for relative in ('packages/contracts/canonical.py', 'packages/contracts/domain_models.py',
                                                        'pyproject.toml', 'uv.lock'))
    # Validation libraries are part of the approved observer, including their
    # installed schema resources/native modules. No user configuration is read.
    for name in ('jsonschema', 'jsonschema-specifications', 'referencing', 'rpds-py', 'attrs',
                 'pydantic', 'pydantic-core', 'annotated-types', 'typing-extensions', 'typing-inspection'):
        installed = distribution(name)
        if installed.files is None:
            raise unavailable()
        paths.update(Path(str(installed.locate_file(item))).resolve(strict=True) for item in installed.files
                     if item.suffix in {'.py', '.so', '.json'} or item.name in {'METADATA', 'RECORD'})
    paths.update(standard.glob('*.py'))
    for package in ('encodings', 'collections', 're', 'ctypes', 'importlib', 'json', 'urllib'):
        paths.update((standard / package).rglob('*.py'))
    for name in ('_ctypes', '_struct', 'resource', 'fcntl', 'math'):
        paths.update((standard / 'lib-dynload').glob(name + '.*.so'))
    # Resolve ELF declarations as file bytes, never ldd, process memory or accounts.
    from .authoring_numeric_runtime import _elf
    search = (Path(sys.executable).resolve().parent.parent / 'lib', Path('/usr/lib/x86_64-linux-gnu'), Path('/usr/lib64'))
    visited = set()
    def dependencies(path: Path) -> None:
        if path in visited:
            return
        visited.add(path)
        raw = _read_regular(path, 64 * 1024**2)
        if not raw.startswith(b'\x7fELF'):
            return
        needed, interpreter = _elf(raw)
        if interpreter:
            loader = Path(interpreter).resolve(strict=True)
            paths.add(loader)
            dependencies(loader)
        for name in needed:
            target = next((folder / name for folder in search if (folder / name).exists()), None)
            if target is None:
                raise unavailable()
            target = target.resolve(strict=True)
            paths.add(target)
            dependencies(target)
    for path in tuple(paths):
        dependencies(path)
    return [_member(path, 64 * 1024**2) for path in sorted(paths)]


class LocalCodexBootstrapRuntime:
    def __init__(self, data_directory: Path, executable: Path | None = None):
        self.data_directory, self.executable = data_directory.resolve(), executable

    def _description(self, *, create: bool) -> tuple[dict, bool]:
        broker = self.data_directory / 'codex-broker'
        directories = (self.data_directory, broker, broker / 'home', broker / 'os-home', broker / 'workspace', broker / 'tmp')
        if create:
            for directory in directories:
                _private_directory(directory)
            configuration = broker / 'home' / 'config.toml'
            if not configuration.exists():
                descriptor = os.open(configuration, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(CONFIG)
        bindings = [_directory_binding(path) for path in directories]
        config_path = broker / 'home' / 'config.toml'
        config_info = config_path.lstat()
        config = _read_regular(config_path, len(CONFIG) + 1)
        if config_info.st_uid != os.getuid() or config_info.st_mode & 0o077 or config != CONFIG:
            raise unavailable()
        located = str(self.executable) if self.executable is not None else shutil.which('codex')
        binary = None
        if located is not None:
            try:
                path = Path(located).resolve(strict=True)
                binary = _member(path, PINNED_BYTES)
            except (OSError, ApiError):
                binary = None
        schemas = {}
        for name, digest in SCHEMA_HASHES.items():
            raw = _read_regular(Path(__file__).with_name('codex_protocol') / name, 256 * 1024)
            if sha256_bytes(raw) != digest:
                raise unavailable()
            schemas[name] = digest
        abi = ctypes.CDLL(None, use_errno=True).syscall(444, 0, 0, 1) if sys.platform == 'linux' and platform.machine() == 'x86_64' else -1
        description = {'version': PROFILE_VERSION, 'binary': binary,
            'expected_binary': {'sha256': PINNED_SHA256, 'size': PINNED_BYTES},
            'broker_root': str(broker), 'directories': bindings, 'config_utf8': config.decode(),
            'config_mode': stat.S_IMODE(config_info.st_mode), 'config_uid': config_info.st_uid,
            'environment': _environment(broker), 'request_frames_utf8': _frames(broker, MODEL), 'resources': RESOURCES,
            'schemas': schemas, 'deployment': _deployment(), 'platform': {'system': sys.platform, 'machine': platform.machine(),
            'kernel': platform.release(), 'landlock_abi': abi}, 'python_executable': str(Path(sys.executable).resolve()),
            'launcher_source_utf8': _launcher_source()}
        available = (binary is not None and binary['sha256'] == PINNED_SHA256 and binary['size'] == PINNED_BYTES
                     and abi >= 3 and sys.platform == 'linux' and platform.machine() == 'x86_64')
        return description, available

    def freeze(self, sandbox_root_id: str) -> BootstrapFreeze:
        if sandbox_root_id != 'workspace_default':
            raise ApiError(409, 'CODEX_BOOTSTRAP_BINDING', '未声明的本地控制根不能被批准。')
        try:
            description, available = self._description(create=True)
        except (OSError, ValueError, ApiError):
            raise unavailable() from None
        scope = CodexBootstrapScope(version='codex-local-session-bootstrap-v1', sandbox_root_id=sandbox_root_id,
            sandbox_label='此工作区的隔离 Broker 目录', allowed_actions=[], adapter_version=ADAPTER_VERSION,
            bootstrap_profile_sha256=content_sha256(description))
        frozen = BootstrapFreeze(version='codex-bootstrap-freeze-v1', scope=scope,
                                 description_json=canonical_json(description), available=available)
        self.validate_frozen(frozen)
        return frozen

    def validate_frozen(self, frozen: BootstrapFreeze) -> None:
        BootstrapFreeze.model_validate(frozen.model_dump())
        value = strict_json(frozen.description_json)
        expected = {'version', 'binary', 'expected_binary', 'broker_root', 'directories', 'config_utf8', 'config_mode',
                    'config_uid', 'environment', 'request_frames_utf8', 'resources', 'schemas', 'deployment', 'platform',
                    'python_executable', 'launcher_source_utf8'}
        legacy = value['version'] == 'codex-local-control-profile-v1'
        required = expected - {'launcher_source_utf8'} | {'launcher'} if legacy else expected
        if (set(value) != required or value['version'] not in PROFILE_DEFINITIONS
                or value['resources'] != PROFILE_DEFINITIONS[value['version']]
                or not isinstance(value['config_utf8'], str)
                or sha256_bytes(value['config_utf8'].encode()) != HISTORICAL_CONFIG_SHA256 or value['schemas'] != HISTORICAL_SCHEMAS
                or value['expected_binary'] != {'sha256': '12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad', 'size': 289101384}
                or frozen.scope.sandbox_root_id != 'workspace_default' or frozen.scope.adapter_version != 'codex-cli/0.160.0'
                or frozen.scope.sandbox_label != '此工作区的隔离 Broker 目录'
                or value['environment'] != _environment(Path(value['broker_root']))
                or value['request_frames_utf8'] != _frames(Path(value['broker_root']))):
            raise ValueError('Frozen control profile is invalid')
        # v1 remains a readable historical record. It is never silently upgraded
        # or used with v2's changed launcher: current eligibility compares the
        # complete description and therefore requires a new preparation.
        members = value['deployment']
        if (not isinstance(members, list) or not members or any(not isinstance(member, dict)
                or set(member) != {'path', 'size', 'sha256'} or not isinstance(member['path'], str)
                or not Path(member['path']).is_absolute() or type(member['size']) is not int or member['size'] < 0
                or not isinstance(member['sha256'], str) or len(member['sha256']) != 64
                or any(character not in '0123456789abcdef' for character in member['sha256']) for member in members)
                or len({member['path'] for member in members}) != len(members)):
            raise ValueError('Invalid frozen deployment members')
        if not legacy:
            source = value['launcher_source_utf8']
            fences = [member for member in members if Path(member['path']).name == 'codex_probe_isolation.py']
            if (not isinstance(source, str) or not source.startswith(LAUNCHER_PREFIX) or len(fences) != 1
                    or fences[0]['sha256'] != sha256_bytes(source[len(LAUNCHER_PREFIX):].encode())
                    or fences[0]['size'] != len(source[len(LAUNCHER_PREFIX):].encode())):
                raise ValueError('Missing exact frozen launcher source binding')
        schema = strict_json(_read_regular(Path(__file__).with_name('codex_protocol') / 'ThreadStartParams.json', 256 * 1024))
        Draft7Validator(schema).validate(strict_json(value['request_frames_utf8'][2])['params'])
        if frozen.available and (value['binary'] is None or value['binary']['sha256'] != value['expected_binary']['sha256']
                                 or value['binary']['size'] != value['expected_binary']['size'] or value['platform']['landlock_abi'] < 3):
            raise ValueError('Unverified deployment cannot be current')

    def validity(self, frozen: BootstrapFreeze) -> Literal['current', 'changed', 'unavailable']:
        self.validate_frozen(frozen)
        try:
            old = strict_json(frozen.description_json)
            if (old['broker_root'] != str(self.data_directory / 'codex-broker')
                    or old['version'] != PROFILE_VERSION or old['resources'] != RESOURCES
                    or old['config_utf8'].encode() != CONFIG or frozen.scope.adapter_version != ADAPTER_VERSION
                    or old['request_frames_utf8'] != _frames(self.data_directory / 'codex-broker', MODEL)):
                return 'changed'
            for directory in old['directories']:
                info = Path(directory['path']).lstat()
                observed = {'path': directory['path'], 'device': info.st_dev, 'inode': info.st_ino,
                            'uid': info.st_uid, 'mode': stat.S_IMODE(info.st_mode)}
                if not stat.S_ISDIR(info.st_mode) or observed != directory:
                    return 'changed'
            config = Path(old['broker_root']) / 'home' / 'config.toml'
            info = config.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != old['config_uid']
                    or stat.S_IMODE(info.st_mode) != old['config_mode']
                    or _read_regular(config, len(old['config_utf8'].encode()) + 1) != old['config_utf8'].encode()):
                return 'changed'
            current, available = self._description(create=False)
        except (OSError, ValueError, ApiError):
            return 'unavailable'
        if canonical_json(current) != frozen.description_json:
            return 'changed'
        return 'current' if available and frozen.available else 'unavailable'

    def execute(self, frozen: BootstrapFreeze, permit_id: str) -> BootstrapOutcome:
        observing = False
        try:
            if self.validity(frozen) != 'current':
                return BootstrapOutcome(status='failed', thread_id=None, receipt_json=None,
                                        error_code='CODEX_BOOTSTRAP_UNAVAILABLE', thread_start_attempted=False)
            profile = strict_json(frozen.description_json)
            with sealed_binary(Path(profile['binary']['path'])) as executable:
                observing = True
                return self._observe(executable, frozen, permit_id)
        except Exception:
            if observing:
                return uncertain_outcome()
            return BootstrapOutcome(status='failed', thread_id=None, receipt_json=None,
                                    error_code='CODEX_BOOTSTRAP_UNAVAILABLE', thread_start_attempted=False)

    def _observe(self, executable: int, frozen: BootstrapFreeze, permit_id: str) -> BootstrapOutcome:
        profile = strict_json(frozen.description_json)
        deadline = time.monotonic() + WALL_SECONDS
        # The total envelope includes process launch and cleanup. Reserve the
        # bounded reap budget; never use an extra eight seconds after Popen.
        protocol_deadline = deadline - min(REAP_SECONDS, WALL_SECONDS / 4)
        process = subprocess.Popen([profile['python_executable'], '-I', '-S', '-B', '-c', profile['launcher_source_utf8'],
            str(executable), profile['broker_root']], cwd=str(Path(profile['broker_root']) / 'workspace'),
            env=profile['environment'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, close_fds=True, pass_fds=(executable,))
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        started, budget, pending = False, 0, b''
        outcome = None
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
                selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
                def receive(identifier: int) -> object:
                    nonlocal budget, pending
                    while True:
                        if time.monotonic() >= protocol_deadline:
                            raise ValueError('Control deadline exceeded')
                        if b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            value = strict_json(line)
                            if (not isinstance(value, dict) or set(value) != {'id', 'result'}
                                    or type(value['id']) is not int or value['id'] != identifier):
                                raise ValueError('Unexpected control response')
                            return value['result']
                        remaining = protocol_deadline - time.monotonic()
                        if remaining <= 0:
                            raise ValueError('Control deadline exceeded')
                        events = selector.select(remaining)
                        if not events:
                            raise ValueError('Control deadline exceeded')
                        for selected, _ in events:
                            chunk = os.read(selected.fd, 8192)
                            if not chunk:
                                selector.unregister(selected.fileobj)
                                if selected.data == 'stdout':
                                    raise ValueError('Control response missing')
                                continue
                            budget += len(chunk)
                            if budget > OUTPUT_BYTES:
                                raise ValueError('Control output budget exceeded')
                            if selected.data == 'stdout':
                                pending += chunk
                if time.monotonic() >= protocol_deadline:
                    raise ValueError('Control launch exhausted the deadline')
                process.stdin.write(profile['request_frames_utf8'][0].encode())
                process.stdin.flush()
                initialized = receive(1)
                self._initialized(profile, initialized)
                process.stdin.write(profile['request_frames_utf8'][1].encode())
                process.stdin.flush()
                if time.monotonic() >= protocol_deadline:
                    raise ValueError('Control deadline exceeded')
                started = True  # uncertainty begins before the first start byte
                process.stdin.write(profile['request_frames_utf8'][2].encode())
                process.stdin.flush()
                result = receive(2)
                self._result(profile, result)
                assert isinstance(result, dict)
                if pending:
                    raise ValueError('Unexpected trailing control output')
                receipt = canonical_json({'version': 'codex-bootstrap-receipt-v1', 'permit_id': permit_id,
                    'profile_sha256': frozen.scope.bootstrap_profile_sha256,
                    'frames_sha256': sha256_bytes(''.join(profile['request_frames_utf8']).encode()),
                    'initialized': initialized, 'result': result})
                outcome = BootstrapOutcome(status='ready', thread_id=result['thread']['id'], receipt_json=receipt,
                                           error_code=None, thread_start_attempted=True)
        except Exception:
            outcome = uncertain_outcome() if started else BootstrapOutcome(status='failed', thread_id=None, receipt_json=None,
                error_code='CODEX_BOOTSTRAP_UNAVAILABLE', thread_start_attempted=False)
        finally:
            clean = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                clean = False
            try:
                process.wait(timeout=max(0.001, min(REAP_SECONDS, deadline - time.monotonic())))
            except (OSError, subprocess.TimeoutExpired):
                clean = False
            try:
                # Account for bytes already in both pipes at termination,
                # including split duplicate responses. Never save raw text.
                for pipe in (process.stdout, process.stderr):
                    os.set_blocking(pipe.fileno(), False)
                    while True:
                        try:
                            chunk = os.read(pipe.fileno(), 8192)
                        except BlockingIOError:
                            clean = False
                            break
                        if not chunk:
                            break
                        budget += len(chunk)
                        if pipe is process.stdout or budget > OUTPUT_BYTES:
                            clean = False
                        if budget > OUTPUT_BYTES or time.monotonic() > deadline:
                            clean = False
                            break
            except OSError:
                clean = False
            finally:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    try:
                        pipe.close()
                    except OSError:
                        clean = False
            if not clean or time.monotonic() > deadline:
                outcome = uncertain_outcome() if started else BootstrapOutcome(status='failed', thread_id=None,
                    receipt_json=None, error_code='CODEX_BOOTSTRAP_UNAVAILABLE', thread_start_attempted=False)
        assert outcome is not None
        return outcome

    @staticmethod
    def _initialized(profile: dict, value: object) -> None:
        if (not isinstance(value, dict) or set(value) != {'codexHome', 'platformFamily', 'platformOs', 'userAgent'}
                or value['codexHome'] != str(Path(profile['broker_root']) / 'home')
                or value['platformFamily'] != 'unix' or value['platformOs'] != 'linux'
                or not isinstance(value['userAgent'], str) or '0.160.0' not in value['userAgent']):
            raise ValueError('The initialized identity is not the fixed broker')

    @staticmethod
    def _result(profile: dict, value: object) -> None:
        schema = strict_json(_read_regular(Path(__file__).with_name('codex_protocol') / 'ThreadStartResponse.json', 256 * 1024))
        Draft7Validator(schema).validate(value)
        if not isinstance(value, dict):
            raise ValueError('The result must be an object')
        thread = value['thread']
        if (set(value) - set(schema['properties']) or set(thread) - set(schema['definitions']['Thread']['properties'])
                or value['approvalPolicy'] != 'never' or value['approvalsReviewer'] != 'user'
                or value['cwd'] != str(Path(profile['broker_root']) / 'workspace')
                or value['model'] != strict_json(profile['request_frames_utf8'][2])['params']['model']
                or value['modelProvider'] != 'openai'
                or value['sandbox'] != {'type': 'readOnly', 'networkAccess': False}
                or value.get('instructionSources', []) != [] or value.get('disabledPluginIds', []) != []
                or thread['cwd'] != value['cwd'] or thread['cliVersion'] != '0.160.0'
                or thread['ephemeral'] is not False or thread['modelProvider'] != 'openai'
                or thread['turns'] != [] or thread['preview'] != '' or thread['status'] != {'type': 'idle'}
                or not thread['id'] or len(thread['id']) > 240):
            raise ValueError('The result does not match the exact approved control profile')

    def validate_outcome(self, frozen: BootstrapFreeze, permit_id: str, outcome: BootstrapOutcome) -> None:
        BootstrapOutcome.model_validate(outcome.model_dump())
        if outcome.status != 'ready':
            return
        assert outcome.receipt_json is not None
        receipt = strict_json(outcome.receipt_json)
        profile = strict_json(frozen.description_json)
        if (set(receipt) != {'version', 'permit_id', 'profile_sha256', 'frames_sha256', 'initialized', 'result'}
                or receipt['version'] != 'codex-bootstrap-receipt-v1' or receipt['permit_id'] != permit_id
                or receipt['profile_sha256'] != frozen.scope.bootstrap_profile_sha256
                or receipt['frames_sha256'] != sha256_bytes(''.join(profile['request_frames_utf8']).encode())):
            raise ValueError('The receipt is not bound to the original control instance')
        self._initialized(profile, receipt['initialized'])
        self._result(profile, receipt['result'])
        if outcome.thread_id != receipt['result']['thread']['id']:
            raise ValueError('The saved external mapping does not match its receipt')
