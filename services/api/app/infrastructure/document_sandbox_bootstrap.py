"""Install the post-exec filter before opening untrusted document bytes."""

import ctypes
from pathlib import Path


def lock_execution() -> None:
    class Instruction(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Instruction))]

    data = Path("/post-exec.bpf").read_bytes()
    if not data or len(data) % ctypes.sizeof(Instruction):
        raise RuntimeError("Invalid sandbox policy")
    instructions = (Instruction * (len(data) // ctypes.sizeof(Instruction))).from_buffer_copy(data)
    program = Program(len(instructions), instructions)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(22, 2, ctypes.byref(program), 0, 0) != 0:
        raise RuntimeError("Sandbox policy unavailable")
