"""Actual local files/BlobStore; trusted synthetic facts, not host isolation proof."""
import os

import pytest

from packages.contracts.canonical import sha256_bytes
from services.api.app.application.codex_artifact_models import AnswerSource
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure import codex_answer_materializer as owner


def source(raw):
    return AnswerSource(version='codex-checked-answer-source-v1', workspace_id='workspace_test',
        session_id='session_test', turn_id='turn_test', job_id='job_test', execution_owner_id='owner_test',
        start_sha256='1'*64, model_result_sha256='2'*64, runtime_profile_sha256='3'*64,
        operation_result_sha256=[], answer_sha256=sha256_bytes(raw), answer_bytes=len(raw))


def test_real_closed_file_full_scan_and_blob_copy_preserve_exact_answer(tmp_path):
    raw = '# Synthetic\n\nα + β\n'.encode()
    materializer = owner.CheckedAnswerMaterializer(tmp_path)
    result = materializer.collect(source(raw), raw.decode())
    paths = list((tmp_path/'codex-answer-outputs').glob('*/answer.md'))
    assert len(paths) == 1 and paths[0].read_bytes() == raw
    assert result.writer_stop == 'synchronous-owner-closed'
    assert result.files[0].sha256 == sha256_bytes(raw)
    assert materializer.blobs.read(sha256_bytes(raw), len(raw)) == raw
    paths[0].write_bytes(b'changed after copy')
    assert materializer.blobs.read(result.files[0].sha256, result.files[0].size) == raw


@pytest.mark.parametrize('kind', ['extra', 'symlink', 'hardlink', 'fifo', 'changed'])
def test_complete_scan_rejects_whole_batch_and_registers_no_blob(tmp_path, monkeypatch, kind):
    original = owner._scan
    changed = False
    def dirty(directory, raw):
        nonlocal changed
        if not changed:
            changed = True
            if kind == 'extra':
                fd = os.open('config.toml', os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600, dir_fd=directory)
                os.close(fd)
            elif kind == 'hardlink':
                os.link('answer.md', 'other.md', src_dir_fd=directory, dst_dir_fd=directory)
            else:
                os.unlink('answer.md', dir_fd=directory)
                if kind == 'symlink':
                    os.symlink('missing', 'answer.md', dir_fd=directory)
                elif kind == 'fifo':
                    os.mkfifo('answer.md', 0o600, dir_fd=directory)
                else:
                    fd = os.open('answer.md', os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600, dir_fd=directory)
                    os.write(fd, b'other')
                    os.close(fd)
        return original(directory, raw)
    monkeypatch.setattr(owner, '_scan', dirty)
    with pytest.raises(ApiError):
        owner.CheckedAnswerMaterializer(tmp_path).collect(source(b'answer'), 'answer')
    assert not (tmp_path/'blobs').exists()


def test_source_hash_mismatch_cannot_write_any_output(tmp_path):
    with pytest.raises(ApiError, match='完整安全'):
        owner.CheckedAnswerMaterializer(tmp_path).collect(source(b'original'), 'replacement')
    assert list(tmp_path.iterdir()) == []


def test_constructor_performs_no_file_operations(tmp_path):
    owner.CheckedAnswerMaterializer(tmp_path/'absent')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('answer', ['unsafe\0text', 'api_key = synthetic-marker',
    '-----' + 'BEGIN PRIVATE KEY' + '-----\nsynthetic'])
def test_known_secret_or_configuration_content_is_not_exported(tmp_path, answer):
    with pytest.raises(ApiError) as error:
        owner.CheckedAnswerMaterializer(tmp_path).collect(source(answer.encode()), answer)
    assert error.value.code == 'CODEX_ARTIFACT_REJECTED'
    assert list(tmp_path.iterdir()) == []


def test_late_extra_candidate_rejects_even_after_blob_copy(tmp_path, monkeypatch):
    materializer = owner.CheckedAnswerMaterializer(tmp_path)
    write = materializer.blobs.write
    def altered(*args, **kwargs):
        result = write(*args, **kwargs)
        directory = next((tmp_path/'codex-answer-outputs').iterdir())
        (directory/'unexpected.md').write_bytes(b'extra')
        return result
    monkeypatch.setattr(materializer.blobs, 'write', altered)
    with pytest.raises(ApiError) as error:
        materializer.collect(source(b'answer'), 'answer')
    assert error.value.code == 'CODEX_ARTIFACT_REJECTED'
    # An unreferenced content-addressed file is not an accessible artifact.
    assert materializer.blobs.read(sha256_bytes(b'answer'), 6) == b'answer'
