"""Linux/x86_64 control-probe fence, not a model/tool execution sandbox.

Only the pinned static executable and the dedicated broker hierarchy are readable.
No addressable sockets (including UNIX/keyring), network syscalls or io_uring.
Anonymous socketpair is needed by Tokio signal handling and cannot name a peer.
Unsupported kernels fail before exec; there is no ordinary-process fallback.
"""
import ctypes
import os
from pathlib import Path
import platform
import resource
import sys


class _Instruction(ctypes.Structure):
    _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte), ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]


class _Program(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ushort), ('filter', ctypes.POINTER(_Instruction))]


class _Ruleset(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


class _PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def restrict_probe(executable: Path | None, broker: Path) -> None:
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Unsupported control-probe platform')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        raise RuntimeError('No-new-privileges unavailable')
    if libc.syscall(444, 0, 0, 1) < 3:
        raise RuntimeError('Landlock ABI3 unavailable')
    handled = (1 << 15) - 1
    ruleset = _Ruleset(handled)
    descriptor = libc.syscall(444, ctypes.byref(ruleset), ctypes.sizeof(ruleset), 0)
    if descriptor < 0:
        raise RuntimeError('Filesystem fence unavailable')
    try:
        # Read/write the broker only; never execute files placed in its home.
        broker_rights = handled & ~((1 << 0) | (1 << 6) | (1 << 9) | (1 << 10) | (1 << 11))
        paths = [(broker, broker_rights), (Path('/dev/null'), (1 << 1) | (1 << 2))]
        if executable is not None:
            paths.append((executable, (1 << 0) | (1 << 2)))
        for path, rights in paths:
            file_descriptor = os.open(path, os.O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                rule = _PathRule(rights, file_descriptor)
                if libc.syscall(445, descriptor, 1, ctypes.byref(rule), 0) != 0:
                    raise RuntimeError('Filesystem rule unavailable')
            finally:
                os.close(file_descriptor)
        if libc.syscall(446, descriptor, 0) != 0:
            raise RuntimeError('Filesystem restriction unavailable')
    finally:
        os.close(descriptor)
    # Check architecture first; reject x32 and every socket/async-I/O bypass.
    instructions = [_Instruction(0x20, 0, 0, 4), _Instruction(0x15, 1, 0, 0xC000003E),
                    _Instruction(0x06, 0, 0, 0x80000000), _Instruction(0x20, 0, 0, 0),
                    _Instruction(0x45, 0, 1, 0x40000000), _Instruction(0x06, 0, 0, 0x00050001)]
    for syscall in (41, 42, 43, 49, 50, 288, 425, 426, 427):
        instructions.extend([_Instruction(0x15, 0, 1, syscall), _Instruction(0x06, 0, 0, 0x00050001)])
    instructions.append(_Instruction(0x06, 0, 0, 0x7FFF0000))
    array = (_Instruction * len(instructions))(*instructions)
    program = _Program(len(array), array)
    if libc.prctl(22, 2, ctypes.byref(program), 0, 0) != 0:
        raise RuntimeError('Network restriction unavailable')


def main() -> None:
    # This script is called with Python -I -S, never via shell/preexec_fn.
    try:
        executable, broker = int(sys.argv[1]), Path(sys.argv[2])
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024**2, 16 * 1024**2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
        restrict_probe(None, broker)
        # Only this verified sealed memfd is inherited, alongside three pipes.
        # execve(fd) cannot be redirected by replacing or writing the CLI path.
        os.execve(executable, ['codex', 'app-server', '--listen', 'stdio://'], dict(os.environ))
    except Exception:
        # Neither exception text nor account/config/process stderr is diagnostic output.
        os.write(2, b'CODEX_PROBE_ISOLATION_UNAVAILABLE\n')
        raise SystemExit(126) from None


if __name__ == '__main__':
    main()
