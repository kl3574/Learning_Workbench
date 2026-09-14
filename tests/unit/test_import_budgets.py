"""Explicit budgets expand resource limits without relaxing manifest semantics."""

from dataclasses import replace

import pytest

from packages.contracts.budgets import ImportBudgets
from packages.contracts.validation import parse_manifest
from services.api.app.infrastructure.config import Settings


def manifest(entries):
    return {"package_id": "budget_test", "profile": "learner", "created_at": "2026-09-14T00:00:00Z",
            "files": entries}


def entry(path="course.json", size=0):
    return {"path": path, "size": size, "sha256": "0" * 64, "media_type": "application/json", "visibility": "learner"}


def test_manifest_resource_limits_can_expand_but_path_visibility_and_shape_remain_strict():
    defaults = ImportBudgets()
    expanded = replace(defaults, max_package_files=2002, max_package_bytes=defaults.max_package_bytes + 1)
    entries = [entry()] + [entry(f"assets/a{i}.txt") for i in range(2000)]
    with pytest.raises(ValueError):
        parse_manifest(manifest(entries))
    assert len(parse_manifest(manifest(entries), budgets=expanded).files) == 2001
    with pytest.raises(ValueError):
        parse_manifest(manifest([entry(size=defaults.max_package_bytes + 1)]))
    assert parse_manifest(manifest([entry(size=defaults.max_package_bytes + 1)]), budgets=expanded).files[0].size == defaults.max_package_bytes + 1
    for invalid in [entry("../unsafe"), entry(size=-1), {**entry(), "unknown": "rejected"},
                    {**entry(), "visibility": "author_private"}, {**entry(), "size": "1"}]:
        with pytest.raises(ValueError):
            parse_manifest(manifest([invalid]), budgets=expanded)
    with pytest.raises(ValueError):
        parse_manifest(manifest([entry(), entry()]), budgets=expanded)


@pytest.mark.parametrize("field", list(ImportBudgets.__dataclass_fields__))
@pytest.mark.parametrize("invalid", [0, -1, True, 1.5])
def test_invalid_budget_never_starts_a_parser(field, invalid):
    with pytest.raises(ValueError):
        ImportBudgets(**{field: invalid})


def test_environment_configuration_covers_all_five_budgets(monkeypatch, tmp_path):
    monkeypatch.setenv("LEARNING_DATA_DIR", str(tmp_path / "data"))
    for key, value in {"UPLOAD_BYTES": 90000000, "BLOCK_CHARACTERS": 500000, "PACKAGE_BYTES": 300000000,
                       "PACKAGE_FILES": 3000, "COMPRESSION_RATIO": 120}.items():
        monkeypatch.setenv(f"LEARNING_MAX_{key}", str(value))
    assert Settings.from_env().import_budgets == ImportBudgets(90000000, 500000, 300000000, 3000, 120)
    assert not (tmp_path / "data").exists()
