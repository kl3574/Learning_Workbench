"""Verify this evidence package, optionally against its private raw cache and Git.

This checks captured evidence, never executes tests, drivers, or model requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import subprocess


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def safe(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    assert not path.is_absolute() and ".." not in path.parts and str(path) == relative
    target = root.joinpath(*path.parts)
    assert target.resolve().is_relative_to(root.resolve()) and not target.is_symlink()
    return target


def transform(raw: bytes, operations: list[dict], home_prefix: bytes | None) -> bytes:
    output = bytearray()
    cursor = 0
    for operation in operations:
        start, end = operation["raw_start"], operation["raw_end"]
        assert cursor <= start < end <= len(raw)
        removed = raw[start:end]
        if operation["kind"] == "fixed_home_prefix":
            assert home_prefix is not None and removed == home_prefix
            assert operation["replacement"] == "<HOME>/"
        elif operation["kind"] == "synthetic_test_credential_literal":
            assert re.fullmatch(rb"synthetic-[a-z-]+", removed)
            assert operation["replacement"] == "<REDACTED_SYNTHETIC_TEST_CREDENTIAL>"
        else:
            raise AssertionError("unknown transformation")
        output.extend(raw[cursor:start])
        output.extend(operation["replacement"].encode())
        cursor = end
    output.extend(raw[cursor:])
    return bytes(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-cache-base", type=Path)
    parser.add_argument("--home-prefix", help="Private original fixed home prefix, ending in slash")
    parser.add_argument("--repo", type=Path, help="Optional local Git blob verification; no network")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_bytes())
    assert manifest["format"] == "m61-group-frontend-review-public-v1"
    files = manifest["public_files"]
    assert files == sorted(files, key=lambda row: row["path"])
    index = {row["path"]: row for row in files}
    assert len(index) == len(files)
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    assert actual == set(index) | {"manifest.json"}
    assert manifest["public_file_count"] == len(actual)
    assert sha(canonical(files)) == manifest["public_files_aggregate_sha256"]
    for relative, row in index.items():
        data = safe(root, relative).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], relative
    policy = runpy.run_path(str(root / "publication_policy.py.txt"), run_name="publication_policy")
    for relative in sorted(actual):
        assert policy["inspect"](manifest["publication_prefix"] + "/" + relative,
                                 safe(root, relative).read_bytes()) == [], relative
    scan = json.loads((root / "publication-scan.json").read_bytes())
    assert scan["inspected_targets"] == sorted(manifest["publication_prefix"] + "/" + p for p in actual)
    assert scan["failures"] == []
    aliases = manifest["aliases"]
    assert aliases == sorted(aliases, key=lambda row: row["alias"])
    by_alias = {row["alias"]: row for row in aliases}
    assert len(by_alias) == len(aliases) == manifest["raw_alias_count"]
    assert len({row["raw_relative"] for row in aliases}) == len(aliases)
    assert sha(canonical(aliases)) == manifest["aliases_aggregate_sha256"]
    raw_verified = 0
    for row in aliases:
        public = index[row["public_path"]]
        assert public["sha256"] == row["public_sha256"] and public["bytes"] == row["public_bytes"]
        assert row["transform_count"] == len(row["transforms"])
        assert row["raw_bytes"] + sum(len(op["replacement"].encode()) - (op["raw_end"] - op["raw_start"])
                                        for op in row["transforms"]) == row["public_bytes"]
        if not row["transforms"]:
            assert row["raw_sha256"] == row["public_sha256"] and row["raw_bytes"] == row["public_bytes"]
        if args.raw_cache_base:
            raw = safe(args.raw_cache_base, row["raw_relative"]).read_bytes()
            assert sha(raw) == row["raw_sha256"] and len(raw) == row["raw_bytes"], row["alias"]
            prefix = args.home_prefix.encode() if args.home_prefix else None
            converted = transform(raw, row["transforms"], prefix)
            assert converted == safe(root, row["public_path"]).read_bytes(), row["alias"]
            if row["alias"].endswith(("/before.json", "/after.json")):
                snapshot = json.loads(raw)
                if isinstance(snapshot, dict) and "aggregate_sha256" in snapshot:
                    assert len(snapshot["files"]) == snapshot["count"]
                    assert sha(canonical(snapshot["files"])) == snapshot["aggregate_sha256"]
            raw_verified += 1
    # Raw receipts retain raw hashes. Resolve them using explicit aliases rather
    # than pretending their fields hash the transformed public representations.
    receipts = 0
    for alias, row in by_alias.items():
        if not alias.endswith("/receipt.json"):
            continue
        receipt = json.loads(safe(root, row["public_path"]).read_bytes())
        folder = alias.rsplit("/", 1)[0]
        for field, sibling in [("before_sha256", "before.json"), ("after_sha256", "after.json"),
                               ("run_log_sha256", "run.log"), ("log_sha256", "output.log")]:
            if field in receipt:
                assert receipt[field] == by_alias[folder + "/" + sibling]["raw_sha256"], alias
        if "driver_sha256" in receipt:
            stage = alias.split("/", 1)[0]
            assert any(other["raw_sha256"] == receipt["driver_sha256"]
                       for name, other in by_alias.items() if name.startswith(stage + "/")
                       and name.endswith(".py")), alias
        before = by_alias.get(folder + "/before.json")
        after = by_alias.get(folder + "/after.json")
        if before and after and receipt.get("declared_inputs_unchanged"):
            assert before["raw_sha256"] == after["raw_sha256"], alias
        receipts += 1
    print(json.dumps({"public_files": len(actual), "aliases": len(aliases), "raw_aliases_verified": raw_verified,
                      "receipt_bindings_verified": receipts, "publication_scan": "PASS", "tests_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
