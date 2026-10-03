"""Executable receipt is bound to immutable bytes, not a mutable pathname."""
import fcntl
import hashlib
import os

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure import codex_probe


def test_binary_snapshot_remains_original_when_path_or_inode_changes(tmp_path, monkeypatch):
    original = b'synthetic pinned executable'
    binary = tmp_path / 'executable'
    binary.write_bytes(original)
    monkeypatch.setattr(codex_probe, 'PINNED_BYTES', len(original))
    monkeypatch.setattr(codex_probe, 'PINNED_SHA256', hashlib.sha256(original).hexdigest())
    with codex_probe.sealed_binary(binary) as descriptor:
        binary.write_bytes(b'mutated original inode')
        binary.unlink()
        binary.write_bytes(b'replaced pathname')
        assert os.pread(descriptor, len(original), 0) == original
        seals = fcntl.fcntl(descriptor, codex_probe.F_GET_SEALS)
        assert seals & 15 == 15
        with pytest.raises(PermissionError):
            os.write(descriptor, b'x')
    with pytest.raises(OSError):
        os.fstat(descriptor)


@pytest.mark.parametrize('contents', [b'wrong', b'right-with-extra-bytes'])
def test_unrecognized_binary_cannot_reach_process_start(tmp_path, monkeypatch, contents):
    binary = tmp_path / 'executable'
    binary.write_bytes(contents)
    monkeypatch.setattr(codex_probe, 'PINNED_BYTES', 5)
    monkeypatch.setattr(codex_probe, 'PINNED_SHA256', hashlib.sha256(b'right').hexdigest())
    with pytest.raises(ApiError) as error, codex_probe.sealed_binary(binary):
        pytest.fail('unrecognized executable was admitted')
    assert error.value.code == 'CODEX_ADAPTER_UNSUPPORTED'
