"""Read-only complete-profile inspection; no subprocess or global configuration."""
from copy import deepcopy
from pathlib import Path

import pytest

from packages.contracts.canonical import strict_json
from services.api.app.infrastructure import codex_bootstrap_runtime as module
from services.api.app.application.codex_bootstrap_models import BootstrapFreeze
from services.api.app.serialization import canonical_json, content_sha256


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
        'cleanup': 'SIGKILL-owned-group-wait-close-pipes', 'reap_seconds': 2, 'parent_death': 'SIGKILL-before-fence-and-exec'}
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


@pytest.mark.parametrize('version', ['codex-local-control-profile-v1', 'codex-local-control-profile-v2'])
def test_original_profiles_remain_readable_but_cannot_use_new_observer(tmp_path, version):
    runtime = module.LocalCodexBootstrapRuntime(tmp_path, tmp_path / 'missing-cli')
    current = runtime.freeze('workspace_default')
    old = strict_json(current.description_json)
    old['version'] = version
    old['schemas'] = dict(module.HISTORICAL_SCHEMAS)
    if version.endswith('-v1'):
        old.pop('launcher_source_utf8')
        old['launcher'] = str(Path(module.__file__).with_name('codex_probe_isolation.py'))
        old['resources'].pop('parent_death')
    historical = BootstrapFreeze.model_validate({**current.model_dump(), 'description_json': canonical_json(old),
        'scope': {**current.scope.model_dump(), 'bootstrap_profile_sha256': content_sha256(old)}})
    before = historical.model_dump()
    runtime.validate_frozen(historical)
    assert runtime.validity(historical) == 'changed'
    assert historical.model_dump() == before


def test_confirmed_root_mode_change_is_changed_not_environment_unknown(tmp_path):
    runtime = module.LocalCodexBootstrapRuntime(tmp_path, tmp_path / 'missing-cli')
    original = runtime.freeze('workspace_default')
    workspace = tmp_path / 'codex-broker/workspace'
    workspace.chmod(0o755)
    assert runtime.validity(original) == 'changed'


def test_control_schemas_have_complete_local_reference_closures():
    from packages.contracts.canonical import sha256_bytes
    directory = Path(module.__file__).with_name('codex_protocol')
    for relative, digest in module.CONTROL_SCHEMAS_V3.items():
        raw = (directory / relative).read_bytes()
        assert sha256_bytes(raw) == digest
        document = strict_json(raw)
        def visit(value):
            if isinstance(value, dict):
                if '$ref' in value:
                    reference = value['$ref']
                    assert reference.startswith('#/')
                    target = document
                    for part in reference[2:].split('/'):
                        target = target[part.replace('~1', '/').replace('~0', '~')]
                    assert isinstance(target, dict)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(document)
    assert workspace.stat().st_mode & 0o777 == 0o755


def test_restored_root_is_changed_without_reading_old_directory_or_creating_new_one(tmp_path, monkeypatch):
    original = module.LocalCodexBootstrapRuntime(tmp_path / 'original', tmp_path / 'missing-cli').freeze('workspace_default')
    restored = tmp_path / 'restored'
    runtime = module.LocalCodexBootstrapRuntime(restored, tmp_path / 'missing-cli')
    actual_lstat = Path.lstat
    def guarded_lstat(path, *args, **kwargs):
        assert not path.is_relative_to(tmp_path / 'original'), 'read a different restored workspace root'
        return actual_lstat(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', guarded_lstat)
    assert runtime.validity(original) == 'changed'
    assert not restored.exists()


def test_historical_decode_does_not_use_current_admission_configuration(tmp_path, monkeypatch):
    runtime = module.LocalCodexBootstrapRuntime(tmp_path, tmp_path / 'missing-cli')
    original = runtime.freeze('workspace_default')
    monkeypatch.setattr(module, 'CONFIG', b'synthetic next deployment configuration\n')
    monkeypatch.setattr(module, 'RESOURCES', {**module.RESOURCES, 'cpu_seconds': 4})
    monkeypatch.setattr(module, 'MODEL', 'synthetic-next-model')
    monkeypatch.setattr(module, 'ADAPTER_VERSION', 'synthetic-next-adapter')
    runtime.validate_frozen(original)
    assert runtime.validity(original) == 'changed'
