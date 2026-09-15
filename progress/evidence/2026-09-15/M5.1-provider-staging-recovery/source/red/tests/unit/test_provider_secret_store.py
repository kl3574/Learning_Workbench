"""Synthetic secrets through the explicit private-store boundary only."""

import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.provider_secret_store import FileSecretStore, preferred_secret_store


def test_constructor_has_no_io_and_reopened_store_preserves_version_and_fingerprint(tmp_path):
    from services.api.app.infrastructure.provider_secret_store import FileSecretStore

    root = tmp_path / 'private-secrets'
    store = FileSecretStore(root)
    assert not root.exists()
    store.initialize()
    locator = store.put('synthetic-test-secret-one')
    fingerprint = store.fingerprint(b'synthetic-command-one')
    reopened = FileSecretStore(root)
    assert reopened.read(locator) == 'synthetic-test-secret-one'
    assert reopened.fingerprint(b'synthetic-command-one') == fingerprint
    assert reopened.fingerprint(b'synthetic-command-two') != fingerprint
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in root.iterdir())
    assert 'synthetic-test-secret-one' not in locator
    store.delete(locator)
    assert not reopened.available(locator)


def test_same_locator_equal_length_byte_replacement_is_not_a_secret_rotation(tmp_path):
    from services.api.app.infrastructure.provider_secret_store import FileSecretStore

    root = tmp_path / 'private-secrets'
    store = FileSecretStore(root)
    store.initialize()
    locator = store.put('synthetic-secret-A')
    path = root / locator
    original = path.read_bytes()
    path.write_bytes(original[:-1] + b'B')
    assert len(path.read_bytes()) == len(original)
    assert not store.available(locator)


@pytest.mark.parametrize('attack', ['symlink_directory', 'symlink_secret', 'hardlink_secret', 'world_readable', 'lost_key'])
def test_filesystem_violations_fail_closed_without_secret_or_path_in_error(tmp_path, attack):
    root = tmp_path / 'private-secrets'
    store = FileSecretStore(root)
    store.initialize()
    locator = store.put('synthetic-secret-protected')
    if attack == 'symlink_directory':
        moved = tmp_path / 'moved-private'
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
    elif attack == 'symlink_secret':
        original = root / locator
        moved = root / 'not-a-version'
        original.rename(moved)
        original.symlink_to(moved)
    elif attack == 'hardlink_secret':
        os.link(root / locator, root / 'second-link')
    elif attack == 'world_readable':
        (root / locator).chmod(0o644)
    elif attack == 'lost_key':
        (root / 'fingerprint.key').unlink()
        with pytest.raises(ApiError):
            store.initialize()
        assert not (root / 'fingerprint.key').exists()
    with pytest.raises(ApiError) as error:
        store.read(locator)
    assert not store.available(locator)
    assert str(root) not in str(error.value) and 'synthetic-secret-protected' not in str(error.value)


def test_explicit_system_adapter_precedes_fallback_without_initialization(tmp_path):
    # An explicitly supplied test adapter proves selection only, not actual OS storage.
    adapter = FileSecretStore(tmp_path / 'injected-adapter')
    selected = preferred_secret_store(tmp_path / 'fallback', system_adapter=adapter)
    assert selected is adapter
    assert not (tmp_path / 'fallback').exists() and not (tmp_path / 'injected-adapter').exists()


CRASHING_WRITER = '''
import os,sys
from pathlib import Path
from services.api.app.infrastructure.provider_secret_store import FileSecretStore
store=FileSecretStore(Path(sys.argv[1]))
mode=sys.argv[2]
original_link,original_unlink=os.link,os.unlink
def link(*args,**kwargs):
    if mode=='before_link':
        os._exit(77)
    if mode=='paused_link':
        print('STAGING_READY',flush=True)
        if sys.stdin.readline().strip()!='release':
            os._exit(79)
    return original_link(*args,**kwargs)
def unlink(name,*args,**kwargs):
    if mode=='after_link' and str(name).startswith('.staging-'):
        os._exit(78)
    return original_unlink(name,*args,**kwargs)
os.link,os.unlink=link,unlink
store.put('synthetic-crash-only-key')
'''


@pytest.mark.parametrize('point,exit_code', [('before_link', 77), ('after_link', 78)])
def test_process_crash_staging_is_recovered_without_changing_fingerprint_key(tmp_path, point, exit_code):
    from tests.integration.test_provider_config import config_storage

    _, identity, store, service = config_storage(tmp_path)
    key_before = (store.root / 'fingerprint.key').read_bytes()
    result = subprocess.run([sys.executable, '-c', CRASHING_WRITER, str(store.root), point],
        capture_output=True, timeout=5)
    assert result.returncode == exit_code
    stages = list(store.root.glob('.staging-*'))
    assert len(stages) == 1
    assert stages[0].stat().st_nlink == (2 if point == 'after_link' else 1)
    service.cleanup_orphan_secrets(identity)
    assert not list(store.root.glob('.staging-*'))
    assert not list(store.root.glob('secret_*'))
    assert (store.root / 'fingerprint.key').read_bytes() == key_before


@pytest.mark.parametrize('operation', ['cleanup', 'initialize', 'put'])
def test_active_staging_writer_excludes_other_recovery_initialization_and_writers(tmp_path, operation):
    from tests.integration.test_provider_config import config_storage

    _, identity, store, service = config_storage(tmp_path)
    child = subprocess.Popen([sys.executable, '-c', CRASHING_WRITER, str(store.root), 'paused_link'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    entered, finished = threading.Event(), threading.Event()
    def competing_operation():
        entered.set()
        try:
            if operation == 'cleanup':
                service.cleanup_orphan_secrets(identity)
            elif operation == 'initialize':
                FileSecretStore(store.root).initialize()
            else:
                FileSecretStore(store.root).put('synthetic-second-writer')
        finally:
            finished.set()
    try:
        assert child.stdout.readline().strip() == 'STAGING_READY'
        with ThreadPoolExecutor(max_workers=1) as workers:
            future = workers.submit(competing_operation)
            assert entered.wait(2)
            completed_while_writer_active = finished.wait(0.15)
            child.stdin.write('release\n')
            child.stdin.flush()
            child.communicate(timeout=5)
            future.result(timeout=5)
        assert not completed_while_writer_active
        assert child.returncode == 0
        assert not list(store.root.glob('.staging-*'))
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=5)
