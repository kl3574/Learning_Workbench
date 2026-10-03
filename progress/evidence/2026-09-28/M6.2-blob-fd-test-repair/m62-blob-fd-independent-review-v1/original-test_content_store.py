"""Raw blob integrity, publication and failure tests; no database side effects."""

import errno
import hashlib
import io
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure import blobs
from services.api.app.infrastructure.blobs import BlobStore


def digest(data):
    return hashlib.sha256(data).hexdigest()


def assert_error(operation, status, code):
    with pytest.raises(ApiError) as raised:
        operation()
    assert (raised.value.status, raised.value.code) == (status, code)
    return raised.value


def assert_no_temporary_files(data_dir):
    assert not list(data_dir.rglob(".blob-*.tmp"))


def test_constructor_performs_no_io_and_missing_data_directory_is_not_created(tmp_path, monkeypatch):
    data_dir = tmp_path / "absent"
    with monkeypatch.context() as patch:
        patch.setattr(os, "open", lambda *args, **kwargs: pytest.fail("constructor attempted I/O"))
        store = BlobStore(data_dir)
        assert store.max_bytes == 50 * 1024 * 1024
    assert not data_dir.exists()
    assert_error(lambda: store.write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert not data_dir.exists()


@pytest.mark.parametrize("data", [b"", b"raw\r\nbytes\xff\x00", "含公式 $x^2$\n".encode(), b"a" * 150_000])
@pytest.mark.parametrize("stream", [False, True])
def test_raw_bytes_and_streams_round_trip_with_private_modes(tmp_path, data, stream):
    store = BlobStore(tmp_path)
    source = io.BytesIO(data) if stream else data
    info = store.write(source, expected_sha256=digest(data))
    assert info.sha256 == digest(data) and info.size == len(data)
    assert info.relative_path == f"blobs/{info.sha256[:2]}/{info.sha256}"
    assert store.read(info.sha256, expected_size=info.size) == data
    assert (tmp_path / info.relative_path).read_bytes() == data
    assert stat.S_IMODE((tmp_path / info.relative_path).stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "blobs").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / info.relative_path).parent.stat().st_mode) == 0o700
    if stream:
        assert not source.closed
    with pytest.raises(FrozenInstanceError):
        info.size = 0
    assert_no_temporary_files(tmp_path)


def test_repeat_write_does_not_replace_existing_inode(tmp_path):
    store = BlobStore(tmp_path)
    info = store.write(b"immutable")
    path = tmp_path / info.relative_path
    before = path.stat()
    assert store.write(b"immutable") == info
    after = path.stat()
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
    assert_no_temporary_files(tmp_path)


def test_concurrent_same_content_writes_preserve_one_verified_object(tmp_path):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: BlobStore(tmp_path).write(b"shared"), range(24)))
    assert len(set(results)) == 1
    assert BlobStore(tmp_path).read(results[0].sha256) == b"shared"
    assert_no_temporary_files(tmp_path)


def test_stream_budget_reads_only_the_limit_plus_one_and_cleans_partial_file(tmp_path):
    class TrackingStream(io.BytesIO):
        def __init__(self, value):
            super().__init__(value)
            self.requested = []

        def read(self, amount=-1):
            self.requested.append(amount)
            return super().read(amount)

    source = TrackingStream(b"x" * 1_000_000)
    store = BlobStore(tmp_path, max_bytes=65_536)
    assert_error(lambda: store.write(source), 413, "BLOB_TOO_LARGE")
    assert source.requested == [65_536, 1]
    assert source.tell() == 65_537
    assert_no_temporary_files(tmp_path)
    assert not list((tmp_path / "blobs").glob("*/*"))


def test_exact_budget_and_zero_byte_budget_accept_complete_input(tmp_path):
    store = BlobStore(tmp_path, max_bytes=3)
    assert store.read(store.write(io.BytesIO(b"abc")).sha256) == b"abc"
    empty = BlobStore(tmp_path, max_bytes=0)
    assert empty.read(empty.write(b"").sha256) == b""


def test_oversize_bytes_are_rejected_before_filesystem_io(tmp_path):
    data_dir = tmp_path / "absent"
    assert_error(lambda: BlobStore(data_dir, max_bytes=2).write(b"abc"), 413, "BLOB_TOO_LARGE")
    assert not data_dir.exists()


@pytest.mark.parametrize("bad_hash", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "../escape", "a" * 64 + "\n", 123])
def test_invalid_hashes_never_construct_paths(tmp_path, bad_hash):
    store = BlobStore(tmp_path)
    assert_error(lambda: store.write(b"data", expected_sha256=bad_hash), 422, "SCHEMA_INVALID")
    assert_error(lambda: store.read(bad_hash), 422, "SCHEMA_INVALID")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("bad_size", [-1, True, "1", 1.5])
def test_invalid_expected_size_is_rejected(tmp_path, bad_size):
    assert_error(lambda: BlobStore(tmp_path).read(digest(b"data"), bad_size), 422, "SCHEMA_INVALID")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("bad_limit", [-1, True, "1", 1.5])
def test_invalid_budget_is_rejected(tmp_path, bad_limit):
    assert_error(lambda: BlobStore(tmp_path, bad_limit), 422, "SCHEMA_INVALID")


@pytest.mark.parametrize("source", ["text", bytearray(b"bytes"), None, io.StringIO("text"), io.StringIO("")])
def test_invalid_source_is_rejected_without_publishing(tmp_path, source):
    assert_error(lambda: BlobStore(tmp_path).write(source), 422, "SCHEMA_INVALID")
    assert_no_temporary_files(tmp_path)
    assert not list(tmp_path.glob("blobs/*/*"))


def test_closed_input_is_safe_schema_error(tmp_path):
    source = io.BytesIO(b"data")
    source.close()
    assert_error(lambda: BlobStore(tmp_path).write(source), 422, "SCHEMA_INVALID")
    assert_no_temporary_files(tmp_path)


def test_expected_hash_mismatch_removes_partial_blob(tmp_path):
    assert_error(lambda: BlobStore(tmp_path).write(b"data", digest(b"other")), 409, "CONTENT_HASH_MISMATCH")
    assert_no_temporary_files(tmp_path)
    assert not list(tmp_path.glob("blobs/*/*"))


@pytest.mark.parametrize("operation", ["read", "write"])
@pytest.mark.parametrize("location", ["data", "ancestor", "blobs", "shard", "target"])
def test_symlinks_at_all_path_levels_are_refused(tmp_path, operation, location):
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    payload = b"external content"
    sha256 = digest(payload)
    data_dir = tmp_path / "data"
    data_dir.mkdir(mode=0o700)
    (data_dir / "blobs").mkdir(mode=0o700)
    (data_dir / "blobs" / sha256[:2]).mkdir(mode=0o700)
    target = data_dir / "blobs" / sha256[:2] / sha256
    if location == "data":
        path = tmp_path / "linked-data"
        path.symlink_to(data_dir, target_is_directory=True)
        data_dir = path
    elif location == "ancestor":
        path = tmp_path / "linked-parent"
        path.symlink_to(tmp_path, target_is_directory=True)
        data_dir = path / "data"
    elif location == "blobs":
        target.parent.rmdir()
        target.parent.parent.rmdir()
        (data_dir / "blobs").symlink_to(external, target_is_directory=True)
    elif location == "shard":
        target.parent.rmdir()
        target.parent.symlink_to(external, target_is_directory=True)
    else:
        external_file = external / "private-file"
        external_file.write_bytes(payload)
        external_file.chmod(0o600)
        target.symlink_to(external_file)
    before = sorted((p.name, p.read_bytes()) for p in external.iterdir() if p.is_file())
    store = BlobStore(data_dir)

    def action():
        return store.read(sha256) if operation == "read" else store.write(payload)

    error = assert_error(action, 503, "BLOB_STORAGE_UNAVAILABLE")
    assert str(tmp_path) not in error.message
    after = sorted((p.name, p.read_bytes()) for p in external.iterdir() if p.is_file())
    assert before == after
    assert_no_temporary_files(tmp_path)


@pytest.mark.parametrize("operation", ["read", "write"])
@pytest.mark.parametrize("kind", ["directory", "fifo", "hardlink"])
def test_nonregular_or_aliased_targets_are_refused(tmp_path, operation, kind):
    store = BlobStore(tmp_path)
    info = store.write(b"data")
    path = tmp_path / info.relative_path
    path.unlink()
    if kind == "directory":
        path.mkdir(mode=0o700)
    elif kind == "fifo":
        os.mkfifo(path, mode=0o600)
    else:
        external = tmp_path / "external"
        external.write_bytes(b"data")
        external.chmod(0o600)
        os.link(external, path)
    def action():
        return store.read(info.sha256) if operation == "read" else store.write(b"data")

    assert_error(action, 503, "BLOB_STORAGE_UNAVAILABLE")
    assert_no_temporary_files(tmp_path)


def test_repeated_unsafe_reads_and_writes_do_not_leak_file_descriptors(tmp_path):
    store = BlobStore(tmp_path)
    info = store.write(b"data")
    path = tmp_path / info.relative_path
    path.unlink()
    path.mkdir(mode=0o700)
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(10):
        assert_error(lambda: store.read(info.sha256), 503, "BLOB_STORAGE_UNAVAILABLE")
        assert_error(lambda: store.write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert len(os.listdir("/proc/self/fd")) == before
    assert_no_temporary_files(tmp_path)


def test_predictable_name_collision_does_not_remove_someone_elses_temporary(tmp_path, monkeypatch):
    class FixedUuid:
        hex = "0" * 32

    directory = tmp_path / "blobs"
    directory.mkdir(mode=0o700)
    existing = directory / f".blob-{FixedUuid.hex}.tmp"
    existing.write_bytes(b"another writer")
    existing.chmod(0o600)
    monkeypatch.setattr(blobs, "uuid4", FixedUuid)
    assert_error(lambda: BlobStore(tmp_path).write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert existing.read_bytes() == b"another writer"


def test_missing_atomic_rename_support_fails_closed_without_overwriting_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(blobs.ctypes, "CDLL", lambda *args, **kwargs: object())
    assert_error(lambda: BlobStore(tmp_path).write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert not list(tmp_path.glob("blobs/*/*"))
    assert_no_temporary_files(tmp_path)


def test_existing_blob_with_public_permissions_is_refused(tmp_path):
    store = BlobStore(tmp_path)
    info = store.write(b"data")
    (tmp_path / info.relative_path).chmod(0o644)
    assert_error(lambda: store.read(info.sha256), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert_error(lambda: store.write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert_no_temporary_files(tmp_path)


def test_hash_corruption_is_rejected_on_read_and_never_repaired_by_write(tmp_path):
    store = BlobStore(tmp_path)
    info = store.write(b"data")
    path = tmp_path / info.relative_path
    path.write_bytes(b"evil")
    inode = path.stat().st_ino
    assert_error(lambda: store.read(info.sha256), 409, "CONTENT_HASH_MISMATCH")
    assert_error(lambda: store.write(b"data"), 409, "CONTENT_HASH_MISMATCH")
    assert path.read_bytes() == b"evil" and path.stat().st_ino == inode
    assert_no_temporary_files(tmp_path)


def test_read_checks_expected_size_and_configured_byte_budget(tmp_path):
    store = BlobStore(tmp_path)
    info = store.write(b"data")
    assert_error(lambda: store.read(info.sha256, expected_size=3), 409, "CONTENT_HASH_MISMATCH")
    assert_error(lambda: BlobStore(tmp_path, max_bytes=3).read(info.sha256), 413, "BLOB_TOO_LARGE")


def test_missing_blob_is_safe_unavailable_error_and_read_creates_nothing(tmp_path):
    assert_error(lambda: BlobStore(tmp_path).read(digest(b"missing")), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert list(tmp_path.iterdir()) == []


def test_source_read_failure_cleans_random_temporary_and_redacts_private_path(tmp_path):
    class BrokenStream(io.BytesIO):
        def read(self, amount=-1):
            if self.tell():
                raise OSError(errno.EIO, f"private source {tmp_path}/secret.txt")
            return super().read(amount)

    error = assert_error(lambda: BlobStore(tmp_path).write(BrokenStream(b"data")), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert str(tmp_path) not in error.message and "secret.txt" not in error.message
    assert_no_temporary_files(tmp_path)


def test_fsync_failure_before_rename_does_not_publish_or_retain_temp(tmp_path, monkeypatch):
    store = BlobStore(tmp_path)
    original = os.fsync

    def fail_file_sync(descriptor):
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError(errno.EIO, "injected private device failure")
        original(descriptor)

    monkeypatch.setattr(os, "fsync", fail_file_sync)
    assert_error(lambda: store.write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert not list(tmp_path.glob("blobs/*/*"))
    assert_no_temporary_files(tmp_path)


def test_atomic_rename_failure_preserves_other_blobs_and_cleans_temporary(tmp_path, monkeypatch):
    store = BlobStore(tmp_path)
    previous = store.write(b"previous")

    def fail_rename(*args):
        raise OSError(errno.EIO, "injected private directory failure")

    monkeypatch.setattr(blobs, "_rename_noreplace", fail_rename)
    assert_error(lambda: store.write(b"next"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert store.read(previous.sha256) == b"previous"
    assert not (tmp_path / "blobs" / digest(b"next")[:2] / digest(b"next")).exists()
    assert_no_temporary_files(tmp_path)


def test_directory_sync_failure_after_rename_reports_failure_and_leaves_valid_unreferenced_blob(tmp_path, monkeypatch):
    store = BlobStore(tmp_path)
    original_rename = blobs._rename_noreplace
    original_sync = os.fsync
    published = False

    def record_rename(*args):
        nonlocal published
        original_rename(*args)
        published = True

    def fail_post_publish_sync(descriptor):
        if published:
            raise OSError(errno.EIO, "injected directory sync failure")
        original_sync(descriptor)

    monkeypatch.setattr(blobs, "_rename_noreplace", record_rename)
    monkeypatch.setattr(os, "fsync", fail_post_publish_sync)
    assert_error(lambda: store.write(b"data"), 503, "BLOB_STORAGE_UNAVAILABLE")
    assert published and store.read(digest(b"data")) == b"data"
    assert_no_temporary_files(tmp_path)


def test_target_created_during_publication_is_not_overwritten(tmp_path, monkeypatch):
    original = blobs._rename_noreplace

    def race(source_dir, source, target_dir, target):
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=target_dir)
        with os.fdopen(descriptor, "wb") as existing:
            existing.write(b"evil")
        original(source_dir, source, target_dir, target)

    monkeypatch.setattr(blobs, "_rename_noreplace", race)
    assert_error(lambda: BlobStore(tmp_path).write(b"data"), 409, "CONTENT_HASH_MISMATCH")
    sha256 = digest(b"data")
    assert (tmp_path / "blobs" / sha256[:2] / sha256).read_bytes() == b"evil"
    assert_no_temporary_files(tmp_path)


def test_file_sync_precedes_atomic_rename_and_directory_sync_follows(tmp_path, monkeypatch):
    events = []
    original_sync = os.fsync
    original_rename = blobs._rename_noreplace

    def sync(descriptor):
        events.append("file_sync" if stat.S_ISREG(os.fstat(descriptor).st_mode) else "directory_sync")
        original_sync(descriptor)

    def rename(source_dir, source, target_dir, target):
        assert source.startswith(".blob-") and source.endswith(".tmp")
        descriptor = os.open(source, os.O_RDONLY, dir_fd=source_dir)
        with os.fdopen(descriptor, "rb") as temporary:
            assert temporary.read() == b"data"
        events.append("rename")
        original_rename(source_dir, source, target_dir, target)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(blobs, "_rename_noreplace", rename)
    BlobStore(tmp_path).write(b"data")
    assert events.index("file_sync") < events.index("rename")
    assert events[events.index("rename") + 1:] == ["directory_sync", "directory_sync"]
