"""Cross-process ownership of a persisted bootstrap permit, never a retry lease."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
from collections.abc import Iterator

from ..application.errors import ApiError


class CodexExecutionOwners:
    def __init__(self, data_directory: Path):
        self.directory = data_directory / 'codex-control-owners'

    @contextmanager
    def hold(self, owner_id: str) -> Iterator[bool]:
        # Owner IDs are server-generated opaque IDs, never a user-supplied path.
        if not owner_id.startswith('codex_owner_') or not owner_id[12:].isalnum():
            raise ApiError(409, 'CODEX_CONTROL_INTEGRITY', '控制实例归属无法核验。')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ApiError(503, 'CODEX_BOOTSTRAP_UNAVAILABLE', '本地控制执行边界不可用。')
        fd = os.open(self.directory / owner_id, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise ApiError(503, 'CODEX_BOOTSTRAP_UNAVAILABLE', '本地控制执行边界不可用。')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
            else:
                try:
                    yield True
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
