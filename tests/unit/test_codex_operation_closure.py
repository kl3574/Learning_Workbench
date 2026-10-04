"""No executable code is run by these controlled closure comparisons."""
import pytest
from services.api.app.application import codex_operation_profile as profile


@pytest.mark.parametrize('name', ['prepare', 'execute', 'projection'])
def test_changed_registry_code_invalidates_original_profile(monkeypatch, name):
    frozen = profile.LiteralOperationProfile.current()
    registry = profile.CodexOperationRegistry([frozen])
    original = getattr(profile.CodexOperationRegistry, name)
    def replacement(*args, **kwargs):
        return original(*args, **kwargs)
    monkeypatch.setattr(profile.CodexOperationRegistry, name, replacement)
    assert registry.available(frozen) is False


def test_escaped_surrogate_is_unsupported_instead_of_throwing():
    registry = profile.CodexOperationRegistry([profile.LiteralOperationProfile.current()])
    assert registry.prepare('workspace_one', 'turn_one',
        '{"text":"\\ud800","version":"codex-synthetic-literal-command-v1"}') is None
