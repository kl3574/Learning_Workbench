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


def test_actual_old_profile_bytes_roundtrip_without_new_execution_authority():
    from pathlib import Path
    from packages.contracts.canonical import canonical_bytes, strict_json
    from services.api.app.codex_turn_dto import CodexCommandOperation
    raw = (Path(__file__).parents[1]/'fixtures/codex-operation/literal-v1.json').read_bytes()
    value = strict_json(raw)
    old = profile.LiteralOperationProfile.model_validate(value['profile'])
    closure = profile.LiteralOperationClosure.model_validate(value['closure'])
    operation = CodexCommandOperation.model_validate(value['operation'])
    result = profile.LiteralOperationResult.model_validate(value['result'])
    assert canonical_bytes({name: model.model_dump(mode='json') for name, model in
        [('profile', old), ('closure', closure), ('operation', operation), ('result', result)]}) == raw
    assert old.version == 'codex-synthetic-literal-profile-v1'
    assert profile.CodexOperationRegistry.projection(closure) == operation
    assert result.text == 'Original v1 synthetic result α'
    registry = profile.CodexOperationRegistry([old])
    assert registry.available(old) is False
    assert registry.prepare(closure.workspace_id, closure.turn_id, operation.command_text) is None
    from services.api.app.application.errors import ApiError
    with pytest.raises(ApiError) as denied:
        registry.execute(closure, result.operation_sha256)
    assert denied.value.code == 'CODEX_RUNTIME_UNAVAILABLE'


@pytest.mark.parametrize('helper', ['strict_json', 'canonical_bytes', 'content_sha256', 'sha256_bytes', 'result_digest'])
def test_changed_related_interpretation_or_receipt_code_invalidates_profile(monkeypatch, helper):
    frozen = profile.LiteralOperationProfile.current()
    registry = profile.CodexOperationRegistry([frozen])
    original = getattr(profile, helper)
    def same_behavior(*args, **kwargs):
        return original(*args, **kwargs)
    monkeypatch.setattr(profile, helper, same_behavior)
    assert registry.available(frozen) is False
