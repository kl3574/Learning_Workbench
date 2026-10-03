"""Read-only complete-profile inspection; no subprocess or global configuration."""
from copy import deepcopy
from pathlib import Path

import pytest

from packages.contracts.canonical import strict_json
from services.api.app.infrastructure import codex_bootstrap_runtime as module


def test_freeze_contains_complete_frames_and_observer_closure_without_start(tmp_path, monkeypatch):
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('freeze started a process'))
    runtime = module.LocalCodexBootstrapRuntime(tmp_path, tmp_path / 'missing-cli')
    frozen = runtime.freeze('workspace_default')
    assert frozen.available is False and runtime.validity(frozen) == 'unavailable'
    private = strict_json(frozen.description_json)
    frames = [strict_json(raw) for raw in private['request_frames_utf8']]
    assert [item['method'] for item in frames] == ['initialize', 'initialized', 'thread/start']
    assert frames[-1]['params']['cwd'] == str(tmp_path / 'codex-broker/workspace')
    assert frames[-1]['params']['approvalPolicy'] == 'never' and frames[-1]['params']['sandbox'] == 'read-only'
    assert frames[-1]['params']['baseInstructions'] == frames[-1]['params']['developerInstructions'] == ''
    assert private['resources'] == {'wall_seconds': 8, 'cpu_seconds': 5, 'address_space_bytes': 2147483648,
        'file_size_bytes': 16777216, 'descriptors': 128, 'core_bytes': 0, 'combined_output_bytes': 65536,
        'cleanup': 'SIGKILL-owned-group-wait-close-pipes', 'reap_seconds': 2}
    members = {member['path']: member for member in private['deployment']}
    for suffix in ('codex_bootstrap_runtime.py', 'codex_probe_isolation.py', 'canonical.py', 'serialization.py',
                   'codex_bootstrap_models.py', 'json/decoder.py', 'jsonschema/validators.py', 'uv.lock'):
        assert any(path.endswith(suffix) for path in members), suffix
    before = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    assert runtime.validity(frozen) == 'unavailable'
    assert {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()} == before
    # Changes in even an ancillary validation member invalidate the original
    # runtime plan; they do not mutate its bytes or its historical receipt.
    changed = deepcopy(private['deployment'])
    next(item for item in changed if item['path'].endswith('json/decoder.py'))['sha256'] = 'f' * 64
    monkeypatch.setattr(module, '_deployment', lambda: changed)
    assert runtime.validity(frozen) == 'changed'
    runtime.validate_frozen(frozen)


def test_confirmed_configuration_change_is_changed_without_repair(tmp_path, monkeypatch):
    monkeypatch.setattr(module.subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('inspection started a process'))
    runtime = module.LocalCodexBootstrapRuntime(tmp_path, tmp_path / 'missing-cli')
    original = runtime.freeze('workspace_default')
    config = Path(strict_json(original.description_json)['broker_root']) / 'home/config.toml'
    bad = b'synthetic changed configuration\n'
    config.write_bytes(bad)
    assert runtime.validity(original) == 'changed'
    assert config.read_bytes() == bad
    runtime.validate_frozen(original)
