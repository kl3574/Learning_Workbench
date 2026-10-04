"""Broker-owned answer files, separate from the no-files model/tool runtime.

Only the worker supplies a checked original response after its trusted in-memory
adapter returned and all owned operations closed. This producer writes exactly
that answer, synchronously, into a new private directory. It owns the only writer
and closes it before a complete bounded scan. A schema or caller-supplied stop
flag cannot activate this producer, and HTTP never calls this port.
"""
from contextlib import ExitStack
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from packages.contracts.canonical import sha256_bytes
from ..application.codex_artifact_models import AnswerCollection, AnswerSource, OutputFile, SCAN_PROFILE_V1_SHA256
from ..application.errors import ApiError
from ..serialization import content_sha256
from .blobs import BlobStore

LIMIT = 16 * 1024 * 1024
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
SCAN_PROFILE = {
    'version': 'codex-answer-directory-scan-v1',
    'producer': 'codex-checked-answer-materializer-v1',
    'owned_writers': 'one-synchronous-writer-closed-before-scan',
    'inventory': ['answer.md'], 'max_files': 32, 'max_bytes': LIMIT,
    'links': 'deny', 'special_files': 'deny', 'extra_candidates': 'reject-whole-batch',
    'classifier': 'exact-original-unicode-answer-as-utf8-markdown-v1',
    'content_checks': 'nul-private-key-known-token-config-assignment-v1',
    'quality': 'NOT_RUN',
}
SUSPECT = (rb'-----BEGIN [A-Z ]*PRIVATE KEY-----', rb'gh[pousr]_[A-Za-z0-9]{30,}',
    rb'github_pat_[A-Za-z0-9_]{40,}', rb'sk-[A-Za-z0-9_-]{24,}', rb'AKIA[A-Z0-9]{16}',
    rb'(?im)^\s*(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*\S+')


def rejected() -> ApiError:
    return ApiError(409, 'CODEX_ARTIFACT_REJECTED', '产物目录未通过完整安全核验。')


def unavailable() -> ApiError:
    return ApiError(503, 'CODEX_SOURCE_UNAVAILABLE', '原产物受控副本暂不可用。')


def artifact_error(error: ApiError) -> ApiError:
    """Translate only known file-copy failures, never swallow owner corruption."""
    if error.code == 'BLOB_STORAGE_UNAVAILABLE':
        return unavailable()
    if error.code in {'CONTENT_HASH_MISMATCH', 'BLOB_TOO_LARGE'}:
        return rejected()
    return error


def _directory(stack: ExitStack, path: Path) -> int:
    current = os.open(path.anchor or '.', DIRECTORY_FLAGS)
    stack.callback(os.close, current)
    for part in path.parts:
        if part in {path.anchor, '.'}:
            continue
        if part == '..':
            raise rejected()
        current = os.open(part, DIRECTORY_FLAGS, dir_fd=current)
        stack.callback(os.close, current)
    return current


def _child(stack: ExitStack, parent: int, name: str, *, new: bool) -> int:
    try:
        os.mkdir(name, 0o700, dir_fd=parent)
        os.fsync(parent)
    except FileExistsError:
        if new:
            raise rejected() from None
    current = os.open(name, DIRECTORY_FLAGS, dir_fd=parent)
    stack.callback(os.close, current)
    if stat.S_IMODE(os.fstat(current).st_mode) != 0o700:
        raise rejected()
    return current


def _signature(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _scan(directory: int, expected: bytes) -> bytes:
    before = _signature(os.fstat(directory))
    # The new producer has exactly one named output. Any other candidate,
    # including a subdirectory/config/link, fails the entire scan.
    if sorted(os.listdir(directory)) != ['answer.md']:
        raise rejected()
    with ExitStack() as stack:
        fd = os.open('answer.md', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                     dir_fd=directory)
        stack.callback(os.close, fd)
        original = os.fstat(fd)
        if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1
                or stat.S_IMODE(original.st_mode) != 0o600 or original.st_size != len(expected)
                or original.st_size > LIMIT):
            raise rejected()
        pieces, size = [], 0
        while True:
            piece = os.read(fd, min(65536, LIMIT - size + 1))
            if not piece:
                break
            size += len(piece)
            if size > LIMIT:
                raise rejected()
            pieces.append(piece)
        raw = b''.join(pieces)
        if (_signature(os.fstat(fd)) != _signature(original)
                or _signature(os.stat('answer.md', dir_fd=directory, follow_symlinks=False)) != _signature(original)
                or raw != expected):
            raise rejected()
    if sorted(os.listdir(directory)) != ['answer.md'] or _signature(os.fstat(directory)) != before:
        raise rejected()
    return raw


class CheckedAnswerMaterializer:
    """Explicit application composition, not a general directory import API."""
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.blobs = BlobStore(data_dir, max_bytes=LIMIT)

    def collect(self, source: AnswerSource, answer: str) -> AnswerCollection:
        source = AnswerSource.model_validate(source.model_dump(mode='json'))
        if content_sha256(SCAN_PROFILE) != SCAN_PROFILE_V1_SHA256:
            raise unavailable()
        try:
            raw = answer.encode('utf-8')
        except (UnicodeError, AttributeError):
            raise rejected() from None
        if len(raw) > LIMIT or source.answer_bytes != len(raw) or source.answer_sha256 != sha256_bytes(raw):
            raise rejected()
        # Bounded known-signature checks, not a claim that arbitrary secrets or
        # mathematical/source correctness can be inferred from prose.
        if b'\0' in raw or any(re.search(pattern, raw) for pattern in SUSPECT):
            raise rejected()
        try:
            with ExitStack() as stack:
                root = _directory(stack, self.data_dir)
                outputs = _child(stack, root, 'codex-answer-outputs', new=False)
                # Not derived from an HTTP path or artifact locator. Never reuse
                # a crashed collection, or let a later scan overwrite its files.
                directory = _child(stack, outputs, uuid4().hex, new=True)
                fd = os.open('answer.md', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=directory)
                with os.fdopen(fd, 'wb') as writer:
                    writer.write(raw)
                    writer.flush()
                    os.fsync(writer.fileno())
                os.fsync(directory)
                checked = _scan(directory, raw)
                info = self.blobs.write(checked, expected_sha256=source.answer_sha256)
                # Blob storage can take time; require the original complete
                # inventory still to agree before returning an owner receipt.
                if _scan(directory, raw) != checked or self.blobs.read(info.sha256, info.size) != checked:
                    raise rejected()
        except ApiError as error:
            raise artifact_error(error) from None
        except OSError:
            raise unavailable() from None
        return AnswerCollection(version='codex-checked-answer-collection-v1', source=source,
            producer='codex-checked-answer-materializer-v1', scan_profile_sha256=content_sha256(SCAN_PROFILE),
            writer_stop='synchronous-owner-closed', files=[OutputFile(logical_path='answer.md', size=len(raw),
                sha256=source.answer_sha256, media_type='text/markdown; charset=utf-8', import_kind='markdown')])
