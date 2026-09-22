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
        elif operation["kind"] == "temporary_fixture_session":
            assert re.fullmatch(rb"[A-Za-z0-9_-]{20,}", removed)
            assert operation["replacement"] == "<REDACTED_TEMPORARY_SESSION>"
        elif operation["kind"] == "temporary_fixture_csrf":
            assert re.fullmatch(rb"[0-9a-f]{64}", removed)
            assert operation["replacement"] == "<REDACTED_TEMPORARY_CSRF>"
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
    assert manifest["format"] == "m61-group-native-completion-public-v1"
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
                               ("run_log_sha256", "run.log"), ("log_sha256", "run.log")]:
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
    actual_rows = []
    for name, row in by_alias.items():
        if not name.startswith("native/05-") or not name.endswith("-actual.json"):
            continue
        value = json.loads(safe(root, row["public_path"]).read_bytes())
        recovery, cancel = value["recovery"], value["cancellation"]
        assert recovery["database_before"] == recovery["database_after"]
        assert len(set(recovery["api_processes"])) == 2
        assert recovery["job"] == value["completed"] and recovery["draft"] == value["draft"]
        before, after = recovery["provider_before"], recovery["provider_after"]
        assert before["received_request_count"] == before["validated_request_count"] == 1
        assert after["received_request_count"] == after["validated_request_count"] == 0
        assert before["target_initialization"] == "published_once" and after["target_initialization"] == "reused_exact"
        assert before["target_refs"] == after["target_refs"] and len(after["target_refs"]) == 4
        assert cancel["attempts"][0] == cancel["attempts"][1]
        assert cancel["original_cancel_ack"] == cancel["readback"]
        assert cancel["readback"]["status"] == "cancelled"
        assert cancel["second_prepared"]["consent_id"] is None
        assert cancel["second_prepared"]["summary"]["candidate"] is None
        assert cancel["second_prepare_ack"]["id"] != value["completed"]["summary"]["id"]
        entity = value["draft"]["root"]["entity"]
        if entity != "lesson":
            assert recovery["private_solution"] == value["solution"] == cancel["private_before_lock"]
            assert value["solution"]["ref"] in value["draft"]["private_solution_refs"]
        if entity == "assessment":
            request, draft = value["prepared"]["request"], value["draft"]
            assert request["allowed_modes"] == draft["root"]["allowed_modes"] == ["independent", "open_book"]
            assert request["time_limit_seconds"] == draft["root"]["time_limit_seconds"] == 600
            assert "lesson_ref" not in request
            assert [target["ref"] for target in value["prepared"]["preparation"]["targets"]] == request["target_concept_refs"] == draft["questions"][0]["concept_refs"]
        if "numeric" in value:
            first, second = value["first_preview_ack"], value["second_preview_ack"]
            assert first["decision"] == second["decision"] == "pending"
            assert value["decline_ack"] == dict(id=first["id"], revision=2, operation_sha256=first["operation_sha256"], decision="decline", applied=True, job=None)
            assert value["decline_readback"] == dict(first, revision=2, decision="decline", job=None, job_revision=None, result=None)
            ack, numeric = value["approve_ack"], value["numeric"]
            assert ack == dict(id=second["id"], revision=2, operation_sha256=second["operation_sha256"], decision="approve_once", applied=True, job=ack["job"])
            assert ack["job"]["id"] == numeric["job"]["id"] == numeric["result"]["job_id"]
            assert numeric["target"] == second["target"] and numeric["candidate"] == value["draft"]["candidate"]
            assert numeric["result"]["outcome"] == "environment_unavailable" and numeric["result"]["verdict"] == "BLOCKED" and numeric["result"]["exit_code"] == 1
            if entity == "assessment":
                assert numeric["target"] == value["solution"]["payload"]["question"]
                assert numeric["plan"] == value["solution"]["payload"]["answer"]["numeric_plan"]
        actual_rows.append(entity)
    assert sorted(actual_rows) == ["assessment", "lesson", "practice_set"]
    png = json.loads(safe(root, by_alias["native/tracked-png-readback/readback.json"]["public_path"]).read_bytes())
    for row in png["rows"]:
        captured = by_alias["native/" + row["capture_alias"]]
        assert row["current_sha256"] == row["git_sha256"] == captured["raw_sha256"]
        assert row["bytes"] == captured["raw_bytes"] and row["exact_byte_match"]
        if args.repo:
            data = subprocess.check_output(["git", "show", row["git_commit"] + ":" + row["path"]], cwd=args.repo)
            assert sha(data) == row["git_sha256"] and len(data) == row["bytes"]
    for relative in actual:
        data = safe(root, relative).read_bytes()
        assert not re.search(rb"learning_session=[A-Za-z0-9_-]{20,}|x-csrf-token:\s*[0-9a-f]{64}|Bearer\s+[A-Za-z0-9._-]{20,}", data, re.I), relative
    print(json.dumps({"public_files": len(actual), "aliases": len(aliases), "raw_aliases_verified": raw_verified,
                      "receipt_bindings_verified": receipts, "publication_scan": "PASS", "actual_roots": actual_rows,
                      "four_git_blobs": "PASS" if args.repo else "NOT_CHECKED", "numeric": "Two actual BLOCKED/environment_unavailable results", "tests_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
