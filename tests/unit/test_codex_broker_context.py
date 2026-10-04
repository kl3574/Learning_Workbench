"""Stable server-owned Broker scope never imports the user's CLI home."""
from contextlib import contextmanager

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure import codex_probe


def prepared(tmp_path, monkeypatch):
    binary = tmp_path / 'synthetic-binary'
    binary.write_bytes(b'controlled transport only')
    @contextmanager
    def snapshot(_):
        yield 17
    monkeypatch.setattr(codex_probe, 'sealed_binary', snapshot)
    reads = []
    def observe(self, descriptor, broker):
        assert descriptor == 17
        reads.append(broker)
        return codex_probe.unavailable()
    monkeypatch.setattr(codex_probe.LocalCodexProbe, '_observe', observe)
    return codex_probe.LocalCodexProbe(tmp_path / 'managed', binary), reads


def test_each_refresh_reuses_same_private_context_and_keeps_account_material_local(tmp_path, monkeypatch):
    probe, reads = prepared(tmp_path, monkeypatch)
    assert not probe.data_directory.exists()
    probe.read()
    home = probe.data_directory / 'codex-broker' / 'home'
    marker = home / 'account-marker'
    marker.write_bytes(b'synthetic account state retained, never read by adapter')
    probe.read()
    assert reads == [home.parent, home.parent]
    assert marker.read_bytes() == b'synthetic account state retained, never read by adapter'
    assert (home / 'config.toml').read_bytes() == codex_probe.CONFIG
    assert home.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize('damage', ['config', 'directory_permission', 'directory_symlink'])
def test_changed_broker_context_blocks_observation_without_reset_or_fallback(tmp_path, monkeypatch, damage):
    probe, reads = prepared(tmp_path, monkeypatch)
    probe.read()
    broker = probe.data_directory / 'codex-broker'
    if damage == 'config':
        (broker / 'home' / 'config.toml').write_bytes(b'[features]\nhooks=true\n')
    elif damage == 'directory_permission':
        (broker / 'workspace').chmod(0o755)
    else:
        (broker / 'workspace').rmdir()
        (broker / 'workspace').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ApiError) as error:
        probe.read()
    assert error.value.code == 'CODEX_BROKER_CONFIG_CHANGED'
    assert len(reads) == 1


def test_absent_cli_does_not_create_an_empty_account_context(tmp_path, monkeypatch):
    monkeypatch.setattr(codex_probe.shutil, 'which', lambda _:None)
    assert codex_probe.LocalCodexProbe(tmp_path / 'absent').read() == codex_probe.unavailable()
    assert not (tmp_path / 'absent').exists()
