"""Fixed sandbox entry: only an approved JSON plan; no arbitrary code or paths."""
import ctypes
from dataclasses import asdict
import errno
import json
import os
import resource
import socket
import sys

sys.path.insert(0, '/evaluator')
from authoring_numeric import evaluate_plan  # noqa: E402


def _deny_execution() -> None:
    class Instruction(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte), ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ushort), ('filter', ctypes.POINTER(Instruction))]

    with open('/post-exec.bpf', 'rb') as stream:
        data = stream.read(4096)
    if not data or len(data) % 8:
        raise RuntimeError('BLOCKED_ENVIRONMENT')
    instructions = (Instruction * (len(data) // 8)).from_buffer_copy(data)
    program = Program(len(instructions), instructions)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(22, 2, ctypes.byref(program), 0, 0) != 0:
        raise RuntimeError('BLOCKED_ENVIRONMENT')


def _isolation() -> dict[str, object]:
    if os.getuid() == 0 or os.getgid() == 0 or set(os.environ) - {'LANG', 'LC_CTYPE'}:
        raise RuntimeError('BLOCKED_ENVIRONMENT')
    limits = {'cpu_limit': (resource.RLIMIT_CPU, 2), 'memory_limit': (resource.RLIMIT_AS, 268435456),
              'output_limit': (resource.RLIMIT_FSIZE, 65536)}
    result: dict[str, object] = {'uid': os.getuid(), 'gid': os.getgid()}
    for name, (kind, limit) in limits.items():
        if resource.getrlimit(kind) != (limit, limit):
            raise RuntimeError('BLOCKED_ENVIRONMENT')
        result[name] = limit
    for name, action in [('network_denied', lambda: socket.socket()), ('fork_denied', os.fork),
                         ('exec_denied', lambda: os.execve('/runtime/bin/python3.12', ['python3.12'], {}))]:
        try:
            action()
        except OSError as error:
            if error.errno != errno.EPERM:
                raise RuntimeError('BLOCKED_ENVIRONMENT') from None
            result[name] = True
        else:
            raise RuntimeError('BLOCKED_ENVIRONMENT')
    if any(os.path.exists(path) for path in ('/home', '/workspace', '/etc', '/run', '/root')):
        raise RuntimeError('BLOCKED_ENVIRONMENT')
    result['host_paths_absent'] = True
    return result


def _pairs(values: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values:
        if key in result:
            raise ValueError('NUMERIC_INPUT_INVALID')
        result[key] = value
    return result


def main() -> None:
    _deny_execution()
    isolation = _isolation()
    with open('/input.json', 'rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError('NUMERIC_INPUT_INVALID')
    job = json.loads(data, object_pairs_hook=_pairs)
    assertions = evaluate_plan(job['plan'])
    result = {'version': 'numeric-output-v1', 'isolation': isolation, 'assertions': [asdict(item) for item in assertions]}
    output = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(output) > 65536:
        raise ValueError('NUMERIC_OUTPUT_LIMIT')
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
