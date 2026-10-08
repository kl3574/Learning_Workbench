"""Pinned offline stdio observation; account state belongs only to this Broker.

Raw handshake/account/stderr is bounded in memory, never logged or persisted.
"""
from contextlib import contextmanager
import ctypes
import fcntl
import hashlib
import json
import os
import platform
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Iterator

from ..application.errors import ApiError

PINNED_SHA256 = '12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad'
PINNED_BYTES = 289101384
ADAPTER_VERSION = 'codex-cli/0.160.0'
PROBE_SECONDS = 8
# Linux UAPI fcntl.h: uv's Python omits these constant exports.
F_ADD_SEALS, F_GET_SEALS, IMMUTABLE_SEALS = 1033, 1034, 15
CONFIG = b'''cli_auth_credentials_store = "file"
mcp_oauth_credentials_store = "file"
check_for_update_on_startup = false
approval_policy = "never"
sandbox_mode = "read-only"
notify = []
[analytics]
enabled = false
[feedback]
enabled = false
[otel]
exporter = "none"
trace_exporter = "none"
metrics_exporter = "none"
[features]
hooks = false
plugins = false
remote_plugin = false
apps = false
'''


def unavailable() -> dict:
    return {'available': False, 'authorized': False, 'adapter_version': None,
            'sandbox_roots': [], 'capabilities': {'approvals': False, 'interrupt': False, 'artifacts': False}}


def failure(code: str = 'CODEX_PROBE_UNAVAILABLE') -> ApiError:
    messages = {
        'CODEX_ADAPTER_UNSUPPORTED': '本机 Codex 不是已固定的受检版本；未连接 Codex，未启动生成。',
        'CODEX_PROTOCOL_INVALID': '本机 Codex 控制协议响应无法核验；授权状态未知，未启动生成。',
        'CODEX_PROBE_TIMEOUT': '本机 Codex 状态探测超时；授权状态未知，未启动生成。',
        'CODEX_BROKER_CONFIG_CHANGED': '隔离 Broker 配置或目录不符合受检设置；未读取全局登录，未启动生成。',
        'CODEX_PROBE_UNAVAILABLE': '无法完成隔离 Codex 控制探测；授权状态未知，未启动生成。',
    }
    return ApiError(503, code, messages[code], True)


def project_capabilities(initialized: object, account: object) -> dict:
    if (not isinstance(initialized, dict)
            or set(initialized) != {'codexHome', 'platformFamily', 'platformOs', 'userAgent'}
            or any(not isinstance(value, str) or not value for value in initialized.values())
            or '0.160.0' not in initialized['userAgent']
            or initialized['platformOs'] != 'linux' or initialized['platformFamily'] != 'unix'):
        raise failure('CODEX_PROTOCOL_INVALID')
    if (not isinstance(account, dict) or set(account) - {'account', 'requiresOpenaiAuth', 'workspaceRouting'}
            or type(account.get('requiresOpenaiAuth')) is not bool or 'account' not in account
            or account.get('workspaceRouting') is not None):
        raise failure('CODEX_PROTOCOL_INVALID')
    identity = account['account']
    if identity is not None:
        if not isinstance(identity, dict):
            raise failure('CODEX_PROTOCOL_INVALID')
        if identity.get('type') == 'apiKey':
            if set(identity) != {'type'}:
                raise failure('CODEX_PROTOCOL_INVALID')
        elif identity.get('type') == 'chatgpt':
            if (set(identity) != {'type', 'email', 'planType'} or not isinstance(identity['planType'], str)
                    or not identity['planType'] or identity['email'] is not None and not isinstance(identity['email'], str)):
                raise failure('CODEX_PROTOCOL_INVALID')
        else:
            raise failure('CODEX_PROTOCOL_INVALID')
    if not account['requiresOpenaiAuth']:
        raise failure('CODEX_PROTOCOL_INVALID')
    return {'available': True, 'authorized': identity is not None, 'adapter_version': ADAPTER_VERSION,
            'sandbox_roots': [{'id': 'workspace_default', 'label': '此工作区的隔离 Broker 目录'}],
            'capabilities': {'approvals': False, 'interrupt': False, 'artifacts': False}}


def _private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise failure('CODEX_BROKER_CONFIG_CHANGED')


@contextmanager
def sealed_binary(binary: Path) -> Iterator[int]:
    """Hash and execute one sealed anonymous snapshot; never reopen the path."""
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise failure()
    # The locked uv Python does not expose os.memfd_create. Linux x86_64's
    # syscall is the same primitive, with CLOEXEC | ALLOW_SEALING.
    descriptor = ctypes.CDLL(None, use_errno=True).syscall(319, b'learning-codex-control', 3)
    if descriptor < 0:
        raise failure()
    try:
        source_descriptor = os.open(binary, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(source_descriptor, 'rb') as source, os.fdopen(os.dup(descriptor), 'wb') as target:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size != PINNED_BYTES:
                raise failure('CODEX_ADAPTER_UNSUPPORTED')
            remaining = PINNED_BYTES
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise failure('CODEX_ADAPTER_UNSUPPORTED')
                target.write(chunk)
                remaining -= len(chunk)
            if source.read(1):
                raise failure('CODEX_ADAPTER_UNSUPPORTED')
        fcntl.fcntl(descriptor, F_ADD_SEALS, IMMUTABLE_SEALS)
        os.lseek(descriptor, 0, os.SEEK_SET)
        with os.fdopen(os.dup(descriptor), 'rb') as snapshot:
            if hashlib.file_digest(snapshot, 'sha256').hexdigest() != PINNED_SHA256:
                raise failure('CODEX_ADAPTER_UNSUPPORTED')
        yield descriptor
    finally:
        os.close(descriptor)


class LocalCodexProbe:
    def __init__(self, data_directory: Path, executable: Path | None = None):
        self.data_directory, self.executable = data_directory, executable
        self._lock = threading.Lock()

    def read(self) -> object:
        # No lookup/process/directory creation in module/factory/OpenAPI.
        located = str(self.executable) if self.executable else shutil.which('codex')
        if located is None:
            return unavailable()
        if not self._lock.acquire(blocking=False):
            raise failure()
        try:
            binary = Path(located).resolve(strict=True)
            broker = self.data_directory / 'codex-broker'
            for directory in (self.data_directory, broker, broker / 'home', broker / 'os-home', broker / 'workspace', broker / 'tmp'):
                _private_directory(directory)
            config = broker / 'home' / 'config.toml'
            if not config.exists():
                descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(descriptor, 'wb') as output:
                    output.write(CONFIG)
            descriptor = os.open(config, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, 'rb') as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or source.read(len(CONFIG) + 1) != CONFIG:
                    raise failure('CODEX_BROKER_CONFIG_CHANGED')
            with sealed_binary(binary) as descriptor:
                return self._observe(descriptor, broker)
        except ApiError:
            raise
        except (OSError, ValueError, TypeError, subprocess.SubprocessError):
            raise failure() from None
        finally:
            self._lock.release()

    def _observe(self, executable: int, broker: Path) -> dict:
        # A child-only environment. The parent HOME/CODEX_HOME is neither read
        # nor changed, and no authentication is copied into this stable home.
        environment = {'PATH': os.defpath, 'HOME': str(broker / 'os-home'), 'CODEX_HOME': str(broker / 'home'),
                       'XDG_CONFIG_HOME': str(broker / 'os-home'), 'XDG_CACHE_HOME': str(broker / 'os-home'),
                       'XDG_DATA_HOME': str(broker / 'os-home'), 'TMPDIR': str(broker / 'tmp'),
                       'LANG': 'C.UTF-8', 'TOKIO_WORKER_THREADS': '2'}
        process = subprocess.Popen([sys.executable, '-I', '-S', '-B', str(Path(__file__).with_name('codex_probe_isolation.py')),
                                    str(executable), str(broker)], cwd=broker / 'workspace', env=environment,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True, close_fds=True, pass_fds=(executable,))
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        input_pipe = process.stdin
        deadline, budget, pending = time.monotonic() + PROBE_SECONDS, 0, b''
        def send(value: dict) -> None:
            input_pipe.write(json.dumps(value, separators=(',', ':')).encode() + b'\n')
            input_pipe.flush()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
                selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
                def receive(identifier: int) -> object:
                    nonlocal budget, pending
                    while True:
                        if b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            try:
                                value = json.loads(line, object_pairs_hook=_unique_object)
                            except (ValueError, UnicodeError):
                                raise failure('CODEX_PROTOCOL_INVALID') from None
                            if not isinstance(value, dict) or set(value) != {'id', 'result'} or type(value['id']) is not int or value['id'] != identifier:
                                raise failure('CODEX_PROTOCOL_INVALID')
                            return value['result']
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise failure('CODEX_PROBE_TIMEOUT')
                        events = selector.select(remaining)
                        if not events:
                            raise failure('CODEX_PROBE_TIMEOUT')
                        for key, _ in events:
                            chunk = os.read(key.fd, 8192)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                if key.data == 'stdout':
                                    raise failure()
                                continue
                            budget += len(chunk)
                            if budget > 64 * 1024:
                                raise failure('CODEX_PROTOCOL_INVALID')
                            if key.data == 'stdout':
                                pending += chunk
                            # stderr contributes only to the bounded byte count.
                send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'learning_workbench_probe', 'version': '0.1.0'},
                     'capabilities': {'experimentalApi': False, 'explicitGatewayOauth': True, 'optOutNotificationMethods': ['remoteControl/status/changed']}}})
                initialized = receive(1)
                send({'method': 'initialized', 'params': {}})
                send({'id': 2, 'method': 'account/read', 'params': {'refreshToken': False}})
                account = receive(2)
                return project_capabilities(initialized, account)
        finally:
            # Kill the entire owned group even if its leader already exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate protocol member')
        result[key] = value
    return result
