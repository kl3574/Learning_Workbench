"""Immutable, bounded raw-byte storage (PRODUCT_DESIGN sections 9.3, 10.1, 14, 20.1).

The Linux runtime publishes with renameat2(RENAME_NOREPLACE): a competing writer,
symlink or corrupt existing file must never be overwritten. A failure after the
rename can leave an unreferenced blob; callers must only commit a database
reference after write() returns successfully.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import io
import os
import re
import stat
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from ..application.errors import ApiError

_HASH = re.compile(r"[0-9a-f]{64}")
_CHUNK_BYTES = 64 * 1024
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _invalid() -> ApiError:
    return ApiError(422, "SCHEMA_INVALID", "Blob input is invalid.")


def _unavailable() -> ApiError:
    return ApiError(503, "BLOB_STORAGE_UNAVAILABLE", "Blob storage is unavailable.", retryable=True)


def _mismatch() -> ApiError:
    return ApiError(409, "CONTENT_HASH_MISMATCH", "Blob integrity verification failed.")


def _too_large() -> ApiError:
    return ApiError(413, "BLOB_TOO_LARGE", "Blob exceeds the configured byte limit.")


def _validate_hash(value: str) -> None:
    if not isinstance(value, str) or _HASH.fullmatch(value) is None:
        raise _invalid()


def _rename_noreplace(source_dir: int, source: str, target_dir: int, target: str) -> None:
    """Linux-only atomic rename, deliberately without an overwriting fallback."""
    library = ctypes.CDLL(None, use_errno=True)
    try:
        rename = library.renameat2
    except AttributeError:
        raise OSError(errno.ENOSYS, "Atomic blob publication is unavailable.") from None
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(source_dir, source.encode("ascii"), target_dir, target.encode("ascii"), 1) != 0:
        raise OSError(ctypes.get_errno(), "Atomic blob publication failed.")


@dataclass(frozen=True)
class BlobInfo:
    sha256: str
    relative_path: str
    size: int


class BlobStore:
    def __init__(self, data_dir: Path, max_bytes: int = 50 * 1024 * 1024):
        # Database initialization owns data_dir creation. Construction does no I/O.
        if not isinstance(data_dir, Path) or type(max_bytes) is not int or max_bytes < 0:
            raise _invalid()
        self.data_dir = data_dir
        self.max_bytes = max_bytes

    def _data_directory(self, descriptors: ExitStack) -> int:
        # Do not resolve(): traversing every component with O_NOFOLLOW also
        # rejects a symlink in an ancestor of the configured data directory.
        directory = os.open(self.data_dir.anchor or ".", _DIRECTORY_FLAGS)
        descriptors.callback(os.close, directory)
        for component in self.data_dir.parts:
            if component in {self.data_dir.anchor, "."}:
                continue
            if component == "..":
                raise _unavailable()
            directory = os.open(component, _DIRECTORY_FLAGS, dir_fd=directory)
            descriptors.callback(os.close, directory)
        return directory

    @staticmethod
    def _child_directory(descriptors: ExitStack, parent: int, name: str, *, create: bool) -> int:
        created = False
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent)
                created = True
            except FileExistsError:
                pass
        directory = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
        descriptors.callback(os.close, directory)
        if create:
            os.fchmod(directory, 0o700)
        elif stat.S_IMODE(os.fstat(directory).st_mode) != 0o700:
            raise _unavailable()
        if created:
            os.fsync(directory)
            os.fsync(parent)
        return directory

    def _copy(self, source: BinaryIO, destination: BinaryIO) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        while True:
            requested = min(_CHUNK_BYTES, self.max_bytes - size + 1)
            try:
                chunk = source.read(requested)
            except (TypeError, ValueError):
                raise _invalid() from None
            if not isinstance(chunk, bytes):
                raise _invalid()
            if size + len(chunk) > self.max_bytes:
                raise _too_large()
            if len(chunk) > requested:
                raise _invalid()
            if not chunk:
                break
            destination.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        return digest.hexdigest(), size

    def _read_file(self, directory: int, sha256: str, expected_size: int | None) -> bytes:
        # O_NONBLOCK prevents a malicious FIFO from blocking before fstat.
        with ExitStack() as descriptors:
            descriptor = os.open(sha256, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                 dir_fd=directory)
            descriptors.callback(os.close, descriptor)
            details = os.fstat(descriptor)
            if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1
                    or stat.S_IMODE(details.st_mode) != 0o600):
                raise _unavailable()
            if details.st_size > self.max_bytes:
                raise _too_large()
            if expected_size is not None and details.st_size != expected_size:
                raise _mismatch()
            destination = io.BytesIO()
            with os.fdopen(descriptor, "rb", closefd=False) as source:
                actual_hash, size = self._copy(source, destination)
            if actual_hash != sha256 or size != details.st_size or (expected_size is not None and size != expected_size):
                raise _mismatch()
            return destination.getvalue()

    def write(self, source: bytes | BinaryIO, expected_sha256: str | None = None) -> BlobInfo:
        if expected_sha256 is not None:
            _validate_hash(expected_sha256)
        if isinstance(source, bytes):
            if len(source) > self.max_bytes:
                raise _too_large()
            source = io.BytesIO(source)
        try:
            if not callable(getattr(source, "read", None)):
                raise _invalid()
            with ExitStack() as descriptors:
                data_directory = self._data_directory(descriptors)
                blob_directory = self._child_directory(descriptors, data_directory, "blobs", create=True)
                temporary: str | None = None
                try:
                    name = f".blob-{uuid4().hex}.tmp"
                    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                         0o600, dir_fd=blob_directory)
                    descriptors.callback(os.close, descriptor)
                    temporary = name
                    with os.fdopen(descriptor, "wb", closefd=False) as destination:
                        os.fchmod(destination.fileno(), 0o600)
                        sha256, size = self._copy(source, destination)
                        if expected_sha256 is not None and sha256 != expected_sha256:
                            raise _mismatch()
                        destination.flush()
                        os.fsync(destination.fileno())
                    shard_directory = self._child_directory(descriptors, blob_directory, sha256[:2], create=True)
                    try:
                        _rename_noreplace(blob_directory, temporary, shard_directory, sha256)
                        temporary = None
                    except FileExistsError:
                        # Verify even when the name matches: never repair a
                        # corrupt or unsafe object by silently overwriting it.
                        self._read_file(shard_directory, sha256, size)
                    os.fsync(shard_directory)
                finally:
                    if temporary is not None:
                        try:
                            os.unlink(temporary, dir_fd=blob_directory)
                        except FileNotFoundError:
                            pass
                os.fsync(blob_directory)
                return BlobInfo(sha256, f"blobs/{sha256[:2]}/{sha256}", size)
        except OSError:
            raise _unavailable() from None

    def read(self, sha256: str, expected_size: int | None = None) -> bytes:
        _validate_hash(sha256)
        if expected_size is not None and (type(expected_size) is not int or expected_size < 0):
            raise _invalid()
        try:
            with ExitStack() as descriptors:
                data_directory = self._data_directory(descriptors)
                blob_directory = self._child_directory(descriptors, data_directory, "blobs", create=False)
                shard_directory = self._child_directory(descriptors, blob_directory, sha256[:2], create=False)
                return self._read_file(shard_directory, sha256, expected_size)
        except OSError:
            raise _unavailable() from None
