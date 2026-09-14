"""Verify a fresh single-document extraction and generated structural artifacts.

Successful output is explicitly not product acceptance, publication, a real
provider call, or a mathematical/pedagogical review.
"""
# Imports below follow repo-root bootstrapping for standalone CLI execution.
# ruff: noqa: E402
from __future__ import annotations

from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from packages.contracts.spec_catalog import route_catalog, spec_metadata, traceability
from packages.contracts.validation import validate_package
from scripts.extract_spec import extract
from scripts.generate_contracts import generate


def verify(root: Path = ROOT) -> dict:
    spec = root / "PRODUCT_DESIGN.md"
    tracking = traceability(spec)
    routes = route_catalog(spec)
    for model in dm.CONTRACTS.values():
        Draft202012Validator.check_schema(model.model_json_schema())
    with tempfile.TemporaryDirectory(prefix="learning-spec-") as temporary:
        isolated = Path(temporary)
        single_document = isolated / "PRODUCT_DESIGN.md"
        single_document.write_bytes(spec.read_bytes())
        paths = extract(single_document, isolated)
        if extract(single_document, isolated) != paths:
            raise ValueError("extraction is not idempotent")
        with sqlite3.connect(":memory:") as connection:
            connection.executescript((isolated / "migrations/0001_baseline.sql").read_text())
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise ValueError("foreign keys disabled")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("DDL foreign key check failed")
            tables = connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        process = subprocess.run([sys.executable, str(isolated / "scripts/generate_fixtures.py")],
                                 cwd=isolated, capture_output=True, text=True, check=False)
        if process.returncode:
            raise ValueError("isolated fixture generation failed: " + process.stderr)
        first_archives = {path.name: path.read_bytes() for path in (isolated / "fixtures/synthetic").glob("*.zip")}
        repeat = subprocess.run([sys.executable, str(isolated / "scripts/generate_fixtures.py")],
                                cwd=isolated, capture_output=True, text=True, check=False)
        if repeat.returncode:
            raise ValueError("repeat fixture generation failed")
        for name, data in first_archives.items():
            if (isolated / "fixtures/synthetic" / name).read_bytes() != data:
                raise ValueError("fixture archive bytes not deterministic")
        receipts = [asdict(validate_package(path)) for path in sorted((isolated / "fixtures/synthetic").glob("*.zip"))]
        if {receipt["profile"] for receipt in receipts} != {"author", "learner"}:
            raise ValueError("both fixture profiles required")
        # The standalone embedded serializer and application serializer must agree.
        module_spec = importlib.util.spec_from_file_location("isolated_fixture_generator", isolated / "scripts/generate_fixtures.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        for sample in [{"值": 1.0, "a": [1, True, None]}, {"𐀀": 2, "": 1}]:
            if module.canonical(sample) != canonical_bytes(sample):
                raise ValueError("embedded and runtime canonical serialization differ")
    generated_count = generate(root, check=True)
    return {**spec_metadata(spec), "status": "PASS", "scope": "M0_structural_baseline_only",
            "embedded_files": len(paths), "models": len(dm.CONTRACTS), "sql_tables_including_fts": tables,
            "requirements": len(tracking["requirements"]), "target_scenarios": len(tracking["scenarios"]),
            "tasks": len(tracking["tasks"]), "routes": len(routes["routes"]), "generated_artifacts": generated_count,
            "package_receipts": receipts, "product_acceptance": "NOT_RUN", "publication": "NOT_CHECKED",
            "real_provider": "NOT_RUN", "real_codex": "NOT_RUN", "learning_effectiveness": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True, indent=2))
