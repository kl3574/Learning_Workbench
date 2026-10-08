"""Private ABI01 memory owner. No provider registry, transport or ledger integration.

Serialized input is explicit construction material, never a prepared request JSON.
The loaded pinned owned Rust library runs the actual core producer and bearer freeze.
Completeness facts here confer no SecretStore authority or InputProof qualification.
"""
from __future__ import annotations
import ctypes
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

class _HandleFault(RuntimeError):
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"RETAINED_REQUEST_STATUS_{code}")

class _Info(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        "body_bytes", "encoded_frozen_same", "cloned_body_same", "auth_sensitive")]

@dataclass(frozen=True, slots=True, repr=False)
class _BorrowedState:
    body_bytes: int
    encoded_frozen_same: bool
    cloned_body_same: bool
    auth_sensitive: bool

class _RetainedRequestOwner:
    """Concrete private memory owner; trusted production owner qualification is absent."""
    def __init__(self, library: Path, expected_sha256: str):
        library = Path(library)
        if library.is_symlink() or not library.is_file():
            raise ValueError("OWNED_LIBRARY_REQUIRED")
        # Owned sealed path only. This is not a qualified general trusted loader.
        with library.open("rb") as stream:
            identity = os.fstat(stream.fileno())
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1048576), b""):
                digest.update(chunk)
            if digest.hexdigest() != expected_sha256:
                raise ValueError("OWNED_LIBRARY_CHANGED")
            self._library = ctypes.CDLL(str(library.resolve()))
            after = library.stat()
            if (identity.st_dev, identity.st_ino, identity.st_size, identity.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
            ):
                raise ValueError("OWNED_LIBRARY_PATH_CHANGED")
            self._library_identity = (identity.st_dev, identity.st_ino, identity.st_size, expected_sha256)
        signatures = {
            "m63_request_create": [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint64)],
            "m63_request_info": [ctypes.c_uint64, ctypes.POINTER(_Info)],
            "m63_request_copy_body": [ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)],
            "m63_request_clone": [ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64)],
            "m63_request_release": [ctypes.c_uint64],
        }
        for name, arguments in signatures.items():
            function = getattr(self._library, name)
            function.argtypes = arguments
            function.restype = ctypes.c_int32

    @staticmethod
    def _checked(code: int) -> None:
        if code:
            raise _HandleFault(code)

    def create(self, resolved_materials: dict, static_bearer: bytes) -> _OpaqueRequest:
        # This is only a facts carrier. Rust performs the actual Responses encoding.
        carrier = json.dumps(resolved_materials, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
        return self._create_carrier_for_owned_test(carrier, static_bearer)

    def _create_carrier_for_owned_test(self, carrier: bytes, bearer: bytes) -> _OpaqueRequest:
        if not isinstance(carrier, bytes) or not isinstance(bearer, bytes):
            raise TypeError("OWNED_BYTE_BUFFERS_REQUIRED")
        source = ctypes.create_string_buffer(carrier)
        auth = ctypes.create_string_buffer(bearer)
        output = ctypes.c_uint64()
        self._checked(self._library.m63_request_create(source, len(carrier), auth, len(bearer), ctypes.byref(output)))
        return _OpaqueRequest(self, output.value)

class _OpaqueRequest:
    """Owns one checked foreign handle; cloning shares the genuine frozen Rust Arc."""
    __slots__ = ("_owner", "_handle")
    def __init__(self, owner: _RetainedRequestOwner, handle: int):
        self._owner = owner
        self._handle = handle

    def borrow_state(self) -> _BorrowedState:
        info = _Info()
        self._owner._checked(self._owner._library.m63_request_info(self._handle, ctypes.byref(info)))
        return _BorrowedState(info.body_bytes, bool(info.encoded_frozen_same),
                              bool(info.cloned_body_same), bool(info.auth_sensitive))

    def _copy_body_for_owned_verification(self, capacity: int = 1048576) -> bytes:
        if capacity < 1 or capacity > 1048576:
            raise ValueError("BOUNDED_OWNED_BUFFER_REQUIRED")
        buffer = (ctypes.c_uint8 * capacity)()
        size = ctypes.c_size_t()
        self._owner._checked(self._owner._library.m63_request_copy_body(self._handle, buffer, capacity, ctypes.byref(size)))
        return bytes(buffer[:size.value])

    def clone(self) -> _OpaqueRequest:
        output = ctypes.c_uint64()
        self._owner._checked(self._owner._library.m63_request_clone(self._handle, ctypes.byref(output)))
        return _OpaqueRequest(self._owner, output.value)

    def release(self) -> None:
        # Actual Rust map removal is checked on every call, including duplicate release.
        self._owner._checked(self._owner._library.m63_request_release(self._handle))
