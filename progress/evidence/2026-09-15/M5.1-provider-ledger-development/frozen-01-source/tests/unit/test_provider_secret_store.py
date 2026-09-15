"""Synthetic secrets through the explicit private-store boundary only."""

import os

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
