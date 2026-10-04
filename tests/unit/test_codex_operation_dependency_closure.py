"""Actual project-owned transitive dependencies, never a host runtime probe."""
import pytest
from services.api.app.application import codex_operation_profile as profile
from services.api.app import serialization, codex_turn_dto as dto


@pytest.mark.parametrize('module,name', [(serialization, 'canonical_bytes'), (dto, '_distinct'), (dto, '_unicode')])
def test_actual_project_global_dependency_change_invalidates_original_profile(monkeypatch, module, name):
    frozen = profile.LiteralOperationProfile.current()
    registry = profile.CodexOperationRegistry([frozen])
    original = getattr(module, name)
    def same_result(*args, **kwargs):
        return original(*args, **kwargs)
    monkeypatch.setattr(module, name, same_result)
    assert registry.available(frozen) is False


def test_captured_pydantic_validator_code_change_invalidates_original_profile(monkeypatch):
    frozen = profile.LiteralOperationProfile.current()
    registry = profile.CodexOperationRegistry([frozen])
    # Pydantic captured this original function. Replacing only its module alias
    # would not change actual validation; replace code on the real callable.
    def changed(value):
        if value == '':
            raise ValueError('Synthetic changed validation')
        return value
    monkeypatch.setattr(dto._path, '__code__', changed.__code__)
    assert registry.available(frozen) is False
