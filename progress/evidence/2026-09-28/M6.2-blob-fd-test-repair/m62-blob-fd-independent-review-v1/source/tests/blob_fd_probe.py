"""Fresh-process BlobStore descriptor probe; fault modes are test-only controls."""
import argparse
import errno
import os
from pathlib import Path

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.blobs import BlobStore


def descriptors() -> dict[int, tuple[int, int, int, int]]:
    result = {}
    for value in os.listdir('/proc/self/fd'):
        try:
            info = os.fstat(int(value))
        except OSError as error:
            if error.errno == errno.EBADF:
                # The directory reader used to enumerate /proc is already closed.
                continue
            raise
        result[int(value)] = (info.st_dev, info.st_ino, info.st_mode, info.st_rdev)
    return result


def probe(directory: Path, fault: str) -> None:
    store = BlobStore(directory)
    info = store.write(b'data')
    path = directory / info.relative_path
    path.unlink()
    path.mkdir(mode=0o700)
    sentinel = os.open('/dev/null', os.O_RDONLY)
    injected = None
    try:
        before = descriptors()
        for index in range(10):
            for operation in [lambda: store.read(info.sha256), lambda: store.write(b'data')]:
                try:
                    operation()
                except ApiError as error:
                    assert (error.status, error.code) == (503, 'BLOB_STORAGE_UNAVAILABLE')
                else:
                    raise AssertionError('Unsafe blob operation was accepted')
            if index == 0:
                if fault == 'leak':
                    injected = os.open('/dev/null', os.O_RDONLY)
                elif fault in {'close', 'replace'}:
                    os.close(sentinel)
                    sentinel = None
                    if fault == 'replace':
                        injected = os.open(directory / 'replacement-control', os.O_CREAT | os.O_RDONLY, 0o600)
        after = descriptors()
        assert after == before, 'Blob descriptor identities changed: ' + repr((before, after))
        assert not list(directory.rglob('.blob-*.tmp'))
    finally:
        if injected is not None:
            os.close(injected)
        if sentinel is not None:
            os.close(sentinel)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('fault', choices=['none', 'leak', 'close', 'replace'])
    args = parser.parse_args()
    probe(args.directory, args.fault)
