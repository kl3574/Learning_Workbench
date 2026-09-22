"""Trusted, hash-bound finite arithmetic runtime; preview never executes a child.

Linux x86-64/CPython 3.12 is the initial verified deployment shape. Every permitted
source file is safely read, then execution uses sealed copies of those exact bytes.
The loader and both supervisors also execute sealed descriptors, with transitive
libraries preloaded by sealed descriptor. No host environment or filesystem fallback.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
import ctypes
import fcntl
from datetime import datetime, timezone
import hashlib
import io
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import time
from collections.abc import Callable
import stat
import struct
import sys
import sysconfig
import threading
import zipfile

from packages.contracts.canonical import canonical_bytes, strict_json
from ..authoring_dto import NumericRuntimeProfile, NumericAssertionResult, NumericCheckResult, numeric_result_sha256
from ..application.authoring_models import NumericJobInput
from ..application.authoring_group_models import AuthoringGroupNumericJobInput
from ..application.authoring_numeric import validate_plan
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from typing import Annotated, Literal


NumericExecutionInput = Annotated[
    NumericJobInput | AuthoringGroupNumericJobInput, Field(discriminator='version')
]
_NUMERIC_INPUT: TypeAdapter[NumericJobInput | AuthoringGroupNumericJobInput] = TypeAdapter(NumericExecutionInput)


class NumericRuntimeError(ValueError):
    def __init__(self, code: str = 'BLOCKED_ENVIRONMENT'):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class RuntimeMember:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True, repr=False)
class _File:
    logical: str
    source: Path | None
    data: bytes


@dataclass(frozen=True, repr=False)
class _Closure:
    files: tuple[_File, ...]
    libraries: tuple[str, ...]  # dependency-first SONAMEs
    loader: str
    profile: NumericRuntimeProfile
    manifest_json: bytes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path, maximum: int = 128 * 1024 * 1024) -> bytes:
    """Walk from / with O_NOFOLLOW on every component, not only the final file."""
    if not path.is_absolute() or '..' in path.parts:
        raise NumericRuntimeError()
    current = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            os.close(current)
            current = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
                raise NumericRuntimeError()
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            if (len(data) != before.st_size or before.st_size != after.st_size
                    or before.st_mtime_ns != after.st_mtime_ns or before.st_ctime_ns != after.st_ctime_ns):
                raise NumericRuntimeError()
            return data
    finally:
        os.close(current)


def _elf(data: bytes) -> tuple[tuple[str, ...], str | None]:
    """Read ELF headers only. No ldd/subprocess or execution during preview."""
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 62:
        raise NumericRuntimeError()
    phoff = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    if count > 256 or size < 56:
        raise NumericRuntimeError()
    loads: list[tuple[int, int, int]] = []
    dynamic: tuple[int, int] | None = None
    interpreter = None
    for index in range(count):
        kind, _, offset, address, _, length, _, _ = struct.unpack_from('<IIQQQQQQ', data, phoff + index * size)
        if offset + length > len(data):
            raise NumericRuntimeError()
        if kind == 1:
            loads.append((address, offset, length))
        elif kind == 2:
            dynamic = offset, length
        elif kind == 3:
            interpreter = data[offset:offset + length].rstrip(b'\0').decode('ascii')
    if dynamic is None:
        return (), interpreter
    needed: list[int] = []
    strings = None
    for offset in range(dynamic[0], sum(dynamic), 16):
        tag, value = struct.unpack_from('<QQ', data, offset)
        if tag == 0:
            break
        if tag == 1:
            needed.append(value)
        if tag == 5:
            strings = value
    if not needed:
        return (), interpreter
    if strings is None:
        raise NumericRuntimeError()
    table = next((offset + strings - address for address, offset, length in loads
                  if address <= strings < address + length), None)
    if table is None:
        raise NumericRuntimeError()
    names = []
    for offset in needed:
        end = data.find(b'\0', table + offset)
        if end < 0:
            raise NumericRuntimeError()
        name = data[table + offset:end].decode('ascii')
        if not name or '/' in name or name in {'.', '..'}:
            raise NumericRuntimeError()
        names.append(name)
    return tuple(names), interpreter


def _filter(*, post_exec: bool) -> bytes:
    # Fixed Linux x86-64 UAPI BPF. Deny x32 ABI, network, process creation and
    # cross-process/kernel namespace escapes. Post-exec additionally forbids exec.
    denied = [41, 42, 43, 49, 50, 53, 56, 57, 58, 101, 165, 166, 155, 272,
              288, 298, 303, 304, 308, 310, 311, 321, 425, 426, 427, 435, 438]
    if post_exec:
        denied += [59, 322]
    instructions = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xC000003E), (0x06, 0, 0, 0x80000000),
                    (0x20, 0, 0, 0), (0x45, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000)]
    for number in sorted(set(denied)):
        instructions.extend(((0x15, 0, 1, number), (0x06, 0, 0, 0x00050001)))
    instructions.append((0x06, 0, 0, 0x7FFF0000))
    return b''.join(struct.pack('<HBBI', *instruction) for instruction in instructions)


def _sealed(data: bytes) -> io.FileIO:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.memfd_create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    libc.memfd_create.restype = ctypes.c_int
    fd = libc.memfd_create(b'authoring-numeric', 3)
    if fd < 0:
        raise NumericRuntimeError()
    stream = io.FileIO(fd, 'w+b', closefd=True)
    try:
        stream.write(data)
        stream.seek(0)
        fcntl.fcntl(fd, 1033, 15)  # F_ADD_SEALS: SEAL|SHRINK|GROW|WRITE.
        if fcntl.fcntl(fd, 1034) & 15 != 15:
            raise NumericRuntimeError()
        return stream
    except BaseException:
        stream.close()
        raise


class NumericRuntime:
    def __init__(self, *, entry_path: Path | None = None):
        # Only trusted composition/test code can choose an entry. No HTTP input
        # or NumericJobInput contains a path; a changed entry changes approval.
        self.entry_path = entry_path or Path(__file__).absolute().parents[4] / 'scripts/authoring_numeric_entry.py'
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._cancelled = threading.Event()

    def _closure(self) -> _Closure:
        if sys.platform != 'linux' or platform.machine() != 'x86_64' or sys.version_info[:2] != (3, 12) or os.getuid() == 0:
            raise NumericRuntimeError()
        try:
            return self._read_closure()
        except (OSError, ValueError, UnicodeError, struct.error) as error:
            if isinstance(error, NumericRuntimeError):
                raise
            raise NumericRuntimeError() from None

    def _read_closure(self) -> _Closure:
        stdlib = Path(sysconfig.get_path('stdlib')).resolve(strict=True)
        executable = Path(sys.executable).resolve(strict=True)
        evaluator = Path(__file__).parents[1] / 'application/authoring_numeric.py'
        sources = [
            _File('runtime/bin/python3.12', executable, _read(executable)),
            _File('supervisor/bwrap', Path('/usr/bin/bwrap'), _read(Path('/usr/bin/bwrap'))),
            _File('supervisor/prlimit', Path('/usr/bin/prlimit'), _read(Path('/usr/bin/prlimit'))),
            _File('entry.py', self.entry_path, _read(self.entry_path)),
            _File('evaluator/authoring_numeric.py', evaluator, _read(evaluator)),
            _File('manifest/runner.py', Path(__file__), _read(Path(__file__))),
        ]
        packages = {'encodings', 'collections', 're', 'json', 'ctypes', 'importlib'}
        python_files = list(stdlib.glob('*.py'))
        for name in sorted(packages):
            python_files.extend((stdlib / name).rglob('*.py'))
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(python_files):
                relative = path.relative_to(stdlib).as_posix()
                data = _read(path)
                sources.append(_File('stdlib/' + relative, path, data))
                entry = zipfile.ZipInfo(relative, (1980, 1, 1, 0, 0, 0))
                entry.external_attr = 0o444 << 16
                archive.writestr(entry, data)
        sources.append(_File('runtime/lib/python312.zip', None, zip_buffer.getvalue()))
        for name in ('_struct', 'math', '_json', '_ctypes', 'resource', 'select', 'fcntl', '_socket', 'array'):
            if name not in sys.builtin_module_names:
                matches = list((stdlib / 'lib-dynload').glob(name + '.*.so'))
                if len(matches) != 1:
                    raise NumericRuntimeError()
                path = matches[0]
                sources.append(_File('runtime/lib/python3.12/lib-dynload/' + path.name, path, _read(path)))
        libraries: dict[str, _File] = {}
        order: list[str] = []
        loader_paths: set[str] = set()
        searching: set[str] = set()
        search = (executable.parent.parent / 'lib', Path('/usr/lib/x86_64-linux-gnu'), Path('/usr/lib64'))

        def dependencies(data: bytes) -> None:
            needed, interpreter = _elf(data)
            if interpreter is not None:
                loader_paths.add(interpreter)
            for name in needed:
                if name in libraries:
                    continue
                if name in searching:
                    continue  # libc/loader may refer to each other; already held bytes.
                searching.add(name)
                path = next((directory / name for directory in search if (directory / name).exists()), None)
                if path is None:
                    raise NumericRuntimeError()
                path = path.resolve(strict=True)  # resolve trusted SONAME once; safe-open its canonical path.
                value = _File('runtime/lib/' + name, path, _read(path))
                libraries[name] = value
                dependencies(value.data)
                order.append(name)
                searching.remove(name)

        for source in tuple(sources):
            if source.data.startswith(b'\x7fELF'):
                dependencies(source.data)
        if len(loader_paths) != 1:
            raise NumericRuntimeError()
        loader_path = Path(next(iter(loader_paths))).resolve(strict=True)
        loader = _File('runtime/loader', loader_path, _read(loader_path))
        dependencies(loader.data)
        sources.extend(libraries.values())
        sources.extend((loader, _File('pre-exec.bpf', None, _filter(post_exec=False)),
                        _File('post-exec.bpf', None, _filter(post_exec=True))))
        status = _read(Path('/var/lib/dpkg/status'), 32 * 1024 * 1024).decode('utf-8')
        stanza = next((part for part in status.split('\n\n') if part.startswith('Package: bubblewrap\n')), None)
        if stanza is None:
            raise NumericRuntimeError()
        sandbox_version = next((line[9:] for line in stanza.splitlines() if line.startswith('Version: ')), None)
        if not sandbox_version:
            raise NumericRuntimeError()
        config = {'format': 'numeric-runtime-manifest-v1', 'evaluator_version': 'finite-arithmetic-v1',
                  'python_version': sys.version, 'sandbox_version': sandbox_version,
                  'architecture': 'linux-x86_64', 'wall_seconds': 5, 'cpu_seconds': 2, 'memory_bytes': 268435456,
                  'output_bytes': 65536, 'evaluator_process_limit': 1,
                  'stdlib_packages': sorted(packages), 'entry': 'entry.py', 'evaluator': 'evaluator/authoring_numeric.py',
                  'libraries_dependency_first': order, 'loader': loader.logical}
        sources.append(_File('manifest/config.json', None, canonical_bytes(config)))
        files = tuple(sorted(sources, key=lambda item: item.logical))
        members = [{'path': item.logical, 'size': len(item.data), 'sha256': _sha(item.data)} for item in files]
        manifest = {'format': 'numeric-runtime-manifest-v1', 'config': config, 'members': members}
        profile = NumericRuntimeProfile(evaluator_version='finite-arithmetic-v1',
            evaluator_sha256=_sha(next(item.data for item in files if item.logical == 'evaluator/authoring_numeric.py')),
            runtime_manifest_sha256=_sha(canonical_bytes(manifest)), python_version=sys.version,
            sandbox_version=sandbox_version, wall_seconds=5, cpu_seconds=2, memory_bytes=268435456,
            output_bytes=65536, evaluator_process_limit=1)
        return _Closure(files, tuple(order), loader.logical, profile, canonical_bytes(manifest))

    def prepare(self) -> NumericRuntimeProfile:
        return self._closure().profile

    def manifest_sha256(self) -> str:
        return self._closure().profile.runtime_manifest_sha256

    def manifest(self) -> tuple[RuntimeMember, ...]:
        return tuple(RuntimeMember(item.logical, len(item.data), _sha(item.data)) for item in self._closure().files)

    def manifest_document(self) -> bytes:
        """Complete canonical manifest, with logical paths only; freshly checked."""
        return self._closure().manifest_json

    def check(self, profile: NumericRuntimeProfile) -> None:
        if self._closure().profile != profile:
            raise NumericRuntimeError('NUMERIC_RUNTIME_CHANGED')

    def cancel(self) -> bool:
        """Only this runtime's active process group. No job/policy state mutation."""
        process = self._process
        if process is None:
            return False
        self._cancelled.set()
        _kill(process)
        return True

    def run(self, job: NumericExecutionInput, cancellation: Callable[[], bool]) -> NumericCheckResult:
        return self.run_checked(job, cancellation).result

    def run_checked(self, job: NumericExecutionInput, cancellation: Callable[[], bool], *,
                    on_started: Callable[[str], None] | None = None) -> NumericExecution:
        if not self._lock.acquire(blocking=False):
            raise NumericRuntimeError('NUMERIC_RUNTIME_BUSY')
        self._cancelled.clear()
        try:
            return self._execute(job, cancellation, on_started)
        finally:
            self._process = None
            self._lock.release()

    def _execute(self, job: NumericExecutionInput, cancellation: Callable[[], bool],
                 on_started: Callable[[str], None] | None) -> NumericExecution:
        started: str | None = None
        exit_code: int | None = None
        stdout, stderr = b'', b''
        complete = True
        assertions: list[NumericAssertionResult] = []
        outcome: str = 'environment_unavailable'
        members: tuple[RuntimeMember, ...] = ()
        manifest_json = b''
        try:
            # Revalidate the complete versioned input before sealing any bytes.
            # Group member and root identities remain in the mounted input and
            # result input hash; they are never projected into the old schema.
            job = _NUMERIC_INPUT.validate_python(job.model_dump(mode='json'))
            validate_plan(job.plan.model_dump(mode='json'))
            closure = self._closure()
            manifest_json = closure.manifest_json
            members = tuple(RuntimeMember(item.logical, len(item.data), _sha(item.data)) for item in closure.files)
            if closure.profile != job.runtime:
                raise NumericRuntimeError('NUMERIC_RUNTIME_CHANGED')
            data = canonical_bytes(job)
            if len(data) > 65536:
                raise NumericRuntimeError('NUMERIC_INPUT_LIMIT')
            if cancellation():
                outcome = 'cancelled'
            else:
                with ExitStack() as stack:
                    descriptors: dict[str, int] = {}
                    # zip already contains every stdlib source member; mount the
                    # zip, not mutable source paths or undeclared site-packages.
                    for item in closure.files:
                        if not item.logical.startswith('stdlib/'):
                            descriptors[item.logical] = stack.enter_context(_sealed(item.data)).fileno()
                    descriptors['input.json'] = stack.enter_context(_sealed(data)).fileno()
                    command = self._command(closure, descriptors)
                    if cancellation() or self._cancelled.is_set():
                        outcome = 'cancelled'
                    else:
                        deadline = time.monotonic() + 5
                        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={'LANG': 'C.UTF-8'}, pass_fds=tuple(descriptors.values()),
                            close_fds=True, start_new_session=True)
                        self._process = process
                        started = _utc()
                        if on_started is not None:
                            try:
                                on_started(started)
                            except Exception:
                                raise NumericRuntimeError('NUMERIC_START_RECORD_FAILED') from None
                        stdout, stderr, outcome, complete = _collect(
                            process, deadline, lambda: cancellation() or self._cancelled.is_set())
                        exit_code = process.returncode
                        if cancellation() or self._cancelled.is_set():
                            outcome = 'cancelled'
                        if outcome == 'finished':
                            if exit_code == 0:
                                parsed = _Output.model_validate(strict_json(stdout))
                                if (parsed.isolation.uid == 0 or parsed.isolation.gid == 0
                                        or [item.id for item in parsed.assertions] != [item.id for item in job.plan.assertions]):
                                    raise NumericRuntimeError()
                                assertions = parsed.assertions
                                outcome = ('evaluation_error' if any(item.error_code for item in assertions)
                                           else 'passed' if all(item.passed for item in assertions) else 'mismatch')
                            else:
                                outcome = ('resource_limit' if exit_code in {-9, -24, -25, 137, 152, 153}
                                           else 'environment_unavailable')
        except (NumericRuntimeError, OSError, ValueError, subprocess.SubprocessError, ValidationError) as error:
            outcome = ('outcome_unknown' if started is not None and (exit_code == 0 or (
                isinstance(error, NumericRuntimeError) and error.code == 'NUMERIC_START_RECORD_FAILED'))
                else 'environment_unavailable')
        finally:
            if self._process is not None:
                _kill(self._process)
                if exit_code is None:
                    exit_code = self._process.returncode
        value: dict[str, object] = {
            'job_id': job.job_id, 'input_sha256': _sha(canonical_bytes(job)), 'operation_sha256': job.operation_sha256,
            'outcome': outcome, 'verdict': 'PASS' if outcome == 'passed' else (
                'FAIL' if outcome in {'mismatch', 'evaluation_error'} else 'BLOCKED'),
            'started_at': started, 'finished_at': _utc(), 'exit_code': exit_code,
            'assertions': [item.model_dump(mode='json') for item in assertions],
            'output_sha256': _sha(stdout) if stdout and complete else None,
        }
        value['result_sha256'] = numeric_result_sha256(value)
        return NumericExecution(NumericCheckResult.model_validate(value), stdout, stderr, complete, members, manifest_json)

    def _command(self, closure: _Closure, fds: dict[str, int]) -> list[str]:
        def descriptor(name: str) -> str:
            return f'/proc/self/fd/{fds[name]}'
        loader = descriptor(closure.loader)
        libraries = ':'.join(descriptor('runtime/lib/' + name) for name in closure.libraries
                             if name != 'ld-linux-x86-64.so.2')
        # Explicit sealed ELF loader + all dependency-first preloads: no ldd or
        # host path lookup for these trusted supervisor executables after hashing.
        load = [loader, '--inhibit-cache', '--library-path', '/nonexistent', '--preload', libraries]
        command = [*load, descriptor('supervisor/prlimit'), '--cpu=2:2', '--as=268435456', '--fsize=65536',
                   '--nofile=512:512', '--core=0:0', '--', *load, descriptor('supervisor/bwrap'),
                   '--unshare-user', '--unshare-ipc', '--unshare-pid', '--unshare-net', '--unshare-uts',
                   '--disable-userns', '--uid', str(os.getuid()), '--gid', str(os.getgid()), '--cap-drop', 'ALL',
                   '--die-with-parent', '--clearenv', '--setenv', 'LANG', 'C.UTF-8']
        for logical, fd in fds.items():
            if logical.startswith('supervisor/') or logical.startswith('manifest/') or logical == 'pre-exec.bpf':
                continue
            command += ['--perms', '0555' if logical.startswith('runtime/') and not logical.endswith('.zip') else '0444',
                        '--ro-bind-data', str(fd), '/' + logical]
        command += ['--dir', '/runtime/lib/python3.12', '--tmpfs', '/tmp', '--proc', '/proc',
                    '--remount-ro', '/proc', '--chdir', '/', '--remount-ro', '/', '--seccomp',
                    str(fds['pre-exec.bpf']), '--', '/runtime/loader', '--inhibit-cache', '--library-path',
                    '/runtime/lib', '/runtime/bin/python3.12', '-I', '-S', '-B', '/entry.py']
        return command


@dataclass(frozen=True, repr=False)
class NumericExecution:
    result: NumericCheckResult
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)
    output_complete: bool
    manifest: tuple[RuntimeMember, ...]
    manifest_json: bytes = field(repr=False)


class _Isolation(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    uid: int
    gid: int
    network_denied: Literal[True]
    fork_denied: Literal[True]
    exec_denied: Literal[True]
    host_paths_absent: Literal[True]
    cpu_limit: Literal[2]
    memory_limit: Literal[268435456]
    output_limit: Literal[65536]


class _Output(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    version: Literal['numeric-output-v1']
    isolation: _Isolation
    assertions: list[NumericAssertionResult]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _kill(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=1)


def _collect(process: subprocess.Popen[bytes], deadline: float,
             cancellation: Callable[[], bool]) -> tuple[bytes, bytes, str, bool]:
    assert process.stdout is not None and process.stderr is not None
    output, error = bytearray(), bytearray()
    outcome, complete = 'finished', True
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    selector.register(process.stderr, selectors.EVENT_READ)
    next_check = 0.0
    stop = False
    try:
        while selector.get_map():
            if time.monotonic() >= next_check:
                stop = cancellation()
                next_check = time.monotonic() + 0.25
            if stop:
                outcome = 'cancelled'
                _kill(process)
            elif time.monotonic() >= deadline:
                outcome = 'timeout'
                _kill(process)
            for key, _ in selector.select(0.02):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = output if key.fileobj is process.stdout else error
                remaining = 65536 - len(output) - len(error)
                target.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    complete = False
                    outcome = 'resource_limit'
                    _kill(process)
            if outcome != 'finished' and process.poll() is not None:
                # Dead process group: drain only already available bounded pipe bytes.
                for key, _ in selector.select(0):
                    chunk = os.read(key.fd, 8192)
                    if chunk:
                        target = output if key.fileobj is process.stdout else error
                        remaining = 65536 - len(output) - len(error)
                        target.extend(chunk[:remaining])
                        complete = False
                    else:
                        selector.unregister(key.fileobj)
                complete = complete and not selector.get_map()
                break
        process.wait(timeout=max(0.01, deadline - time.monotonic()))
        return bytes(output), bytes(error), outcome, complete
    finally:
        selector.close()
        _kill(process)
        process.stdout.close()
        process.stderr.close()
