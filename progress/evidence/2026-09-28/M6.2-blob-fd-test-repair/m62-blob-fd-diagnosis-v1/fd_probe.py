"""Controlled closure of one unrelated descriptor; no fabricated FD counts."""
import os
import pytest
from services.api.app.infrastructure.blobs import BlobStore


@pytest.fixture(autouse=True)
def close_unrelated_descriptor_during_real_read(request, monkeypatch):
    if request.node.name != 'test_repeated_unsafe_reads_and_writes_do_not_leak_file_descriptors':
        yield
        return
    descriptor = os.open('/dev/null', os.O_RDONLY)
    closed = False
    real_read = BlobStore.read

    def read(self, *args, **kwargs):
        nonlocal closed
        if not closed:
            os.close(descriptor)
            closed = True
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(BlobStore, 'read', read)
    try:
        yield
    finally:
        if not closed:
            os.close(descriptor)
