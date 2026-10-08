"""Pure bounded language tests; no process, filesystem or network probe."""
import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_operation_profile import (
    CodexOperationRegistry, LiteralCommand, LiteralOperationProfile,
)
from services.api.app.application.errors import ApiError


def test_production_registry_is_empty_and_never_infers_support():
    registry = CodexOperationRegistry()
    body = canonical_bytes(LiteralCommand(version='codex-synthetic-literal-command-v1', text='Synthetic α')).decode()
    assert registry.prepare('workspace_one', 'turn_one', body) is None


def test_complete_operation_is_derived_from_exact_registered_interpreter_and_owner():
    profile = LiteralOperationProfile.current()
    registry = CodexOperationRegistry([profile])
    text = 'Synthetic α\nno model continuation'
    body = canonical_bytes(LiteralCommand(version='codex-synthetic-literal-command-v1', text=text)).decode()
    closure, operation = registry.prepare('workspace_one', 'turn_one', body)
    assert operation.command_text == body and operation.read_files == []
    assert closure.argv == ['synthetic-memory-literal-v1', text] and closure.environment == {}
    result = registry.execute(closure, 'a'*64)
    assert result.text == text
    assert result.host_actions == result.provider_requests == result.files_written == 0
    other = registry.prepare('workspace_one', 'turn_two', body)
    assert other[1].filesystem_scope_sha256 != operation.filesystem_scope_sha256


@pytest.mark.parametrize('raw', ['[]', '{}', '{"version":"shell","text":"echo unsafe"}',
    '{"version":"codex-synthetic-literal-command-v1","text":"x","shell":true}',
    '{ "version":"codex-synthetic-literal-command-v1","text":"x"}',
    '{"version":"codex-synthetic-literal-command-v1","text":"'+'x'*257+'"}'])
def test_no_unknown_fields_shell_fallback_or_noncanonical_input(raw):
    registry = CodexOperationRegistry([LiteralOperationProfile.current()])
    assert registry.prepare('workspace_one', 'turn_one', raw) is None


def test_withdrawn_or_changed_closure_cannot_execute():
    registry = CodexOperationRegistry([LiteralOperationProfile.current()])
    closure, _ = registry.prepare('workspace_one', 'turn_one', canonical_bytes(
        LiteralCommand(version='codex-synthetic-literal-command-v1', text='Synthetic')).decode())
    with pytest.raises(ApiError) as unavailable:
        CodexOperationRegistry().execute(closure, 'a'*64)
    assert unavailable.value.code == 'CODEX_RUNTIME_UNAVAILABLE'
    with pytest.raises(ApiError) as altered:
        registry.execute(closure.model_copy(update={'argv': ['different', 'Synthetic']}), 'a'*64)
    assert altered.value.code == 'CODEX_BINDING_INVALID'
