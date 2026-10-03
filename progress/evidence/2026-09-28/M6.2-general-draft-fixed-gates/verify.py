"""Replay every fixed gate original, path edit, stage receipt, and source input."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

sys.dont_write_bytecode = True
import publication_scanner


EA_CACHE = "m62-general-draft-combined-gates-v1"
E58_CACHE = "m62-draft-main-combined-gates-v1"
COMP_CACHE = "m62-general-draft-main-integration-v1"
ROOT = Path(__file__).resolve().parent


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def pin(raw: bytes) -> dict[str, int | str]:
    return {"bytes": len(raw), "sha256": sha(raw)}


def safe(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    assert not path.is_absolute() and ".." not in path.parts and path.parts, name
    return root / name


def checked(path: Path, item: dict, prefix: str = "") -> bytes:
    raw = path.read_bytes()
    assert pin(raw) == {"bytes": item[prefix + "bytes"], "sha256": item[prefix + "sha256"]}, str(path)
    return raw


def replay(raw: bytes, spans: list[dict]) -> bytes:
    result = []
    end = 0
    for item in spans:
        start = item["start"]
        stop = item["end"]
        assert end <= start <= stop <= len(raw)
        assert sha(raw[start:stop]) == item["raw_span_sha256"]
        assert "\n" not in item["replacement"]
        result.append(raw[end:start])
        result.append(item["replacement"].encode())
        end = stop
    result.append(raw[end:])
    output = b"".join(result)
    assert raw.count(b"\n") == output.count(b"\n")
    return output


def run_git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def tree(repo: Path, head: str) -> dict[str, dict[str, str]]:
    found = {}
    for entry in run_git(repo, "ls-tree", "-rz", head).split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, kind, git_blob = meta.decode().split()
        name = path.decode()
        if name.startswith("progress/"):
            continue
        assert kind == "blob", (head, name, kind)
        found[name] = {"git_mode": mode, "git_blob": git_blob}
    return found


def rows(raw: bytes) -> tuple[str | None, dict[str, dict[str, object]]]:
    obj = json.loads(raw)
    head = obj.get("head") if isinstance(obj, dict) else None
    values = obj["files"] if isinstance(obj, dict) else obj
    assert len(values) == len({row["path"] for row in values})
    assert [row["path"] for row in values] == sorted(row["path"] for row in values)
    mapped = {}
    for row in values:
        assert row["git_matches"] is True
        actual = row.get("actual_blob", row.get("git_blob_sha1"))
        indexed = row.get("indexed_blob", row.get("git_blob_sha1"))
        assert actual == indexed
        mapped[row["path"]] = {
            "bytes": row["bytes"],
            "sha256": row["sha256"],
            "git_mode": row["git_mode"],
            "git_blob": actual,
        }
    return head, mapped


def log_outcomes(logs: dict[tuple[str, str], bytes]) -> None:
    ea_python = logs[(EA_CACHE, "python")]
    e58_python = logs[(E58_CACHE, "03b-related-final")]
    assert b"SKIPPED [1] tests/integration/test_authoring_numeric_runtime.py:46: BLOCKED_ENVIRONMENT" in ea_python
    assert re.search(rb"2991 passed, 1 skipped, 2 warnings in [^\n]+", ea_python)
    assert re.search(rb"239 passed, 2 warnings in [^\n]+", e58_python)
    ea_web = re.sub(rb"\x1b\[[0-9;]*m", b"", logs[(EA_CACHE, "web")])
    e58_web = re.sub(rb"\x1b\[[0-9;]*m", b"", logs[(E58_CACHE, "web")])
    assert re.search(rb"Test Files\s+88 passed", ea_web)
    assert re.search(rb"Tests\s+512 passed", ea_web)
    assert re.search(rb"Test Files\s+91 passed", e58_web)
    assert re.search(rb"Tests\s+538 passed", e58_web)


def verify_source(repo: Path, composition: dict, snapshots: dict[str, dict]) -> dict:
    base_commit = composition["public_base"]
    base_tree = tree(repo, base_commit)
    assert len(base_tree) == composition["public_base_engineering_paths"] == 1051
    integrated = composition["integrated"]
    isolated = composition["isolated"]
    assert len(integrated["overrides"]) == 32
    assert len(integrated["added_paths"]) == 15
    assert len(integrated["modified_paths"]) == 17
    assert not integrated["absent_paths"]
    assert len(isolated["absent_paths"]) == 11
    assert len(isolated["overrides"]) == 3
    assert not isolated["added_paths"]

    e58_tree = dict(base_tree)
    for name in integrated["absent_paths"]:
        assert name in e58_tree
        del e58_tree[name]
    for name, item in integrated["overrides"].items():
        assert name in integrated["added_paths"] + integrated["modified_paths"]
        raw = checked(safe(ROOT, item["public_path"]), item)
        assert blob(raw) == item["git_blob"]
        e58_tree[name] = {"git_mode": item["git_mode"], "git_blob": item["git_blob"]}
    assert len(e58_tree) == integrated["path_count"] == 1066
    ea_tree = dict(e58_tree)
    for name in isolated["absent_paths"]:
        assert name in ea_tree
        del ea_tree[name]
    for name, item in isolated["overrides"].items():
        assert name in e58_tree and name not in isolated["absent_paths"]
        raw = checked(safe(ROOT, item["public_path"]), item)
        assert blob(raw) == item["git_blob"]
        ea_tree[name] = {"git_mode": item["git_mode"], "git_blob": item["git_blob"]}
    assert len(ea_tree) == isolated["path_count"] == 1055

    cache = {}
    def object_bytes(object_id: str) -> bytes:
        if object_id not in cache:
            data = run_git(repo, "cat-file", "blob", object_id)
            assert blob(data) == object_id
            cache[object_id] = data
        return cache[object_id]

    base_sources = {name: object_bytes(item["git_blob"]) for name, item in base_tree.items()}
    e58_sources = dict(base_sources)
    for name in integrated["absent_paths"]:
        del e58_sources[name]
    for name, item in integrated["overrides"].items():
        e58_sources[name] = checked(safe(ROOT, item["public_path"]), item)
    ea_sources = dict(e58_sources)
    for name in isolated["absent_paths"]:
        del ea_sources[name]
    for name, item in isolated["overrides"].items():
        ea_sources[name] = checked(safe(ROOT, item["public_path"]), item)

    for head, actual_sources, actual_tree in (
        (integrated["commit"], e58_sources, e58_tree),
        (isolated["commit"], ea_sources, ea_tree),
    ):
        expected = snapshots[head]
        assert set(expected) == set(actual_sources) == set(actual_tree)
        for name, item in expected.items():
            data = actual_sources[name]
            assert pin(data) == {"bytes": item["bytes"], "sha256": item["sha256"]}, (head, name)
            assert blob(data) == item["git_blob"] == actual_tree[name]["git_blob"], (head, name)
            assert item["git_mode"] == actual_tree[name]["git_mode"], (head, name)

    directly_verified = []
    for head, computed in ((integrated["commit"], e58_tree), (isolated["commit"], ea_tree)):
        exists = subprocess.run(
            ["git", "cat-file", "-e", head + "^{commit}"], cwd=repo,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        ).returncode == 0
        if exists:
            assert tree(repo, head) == computed
            directly_verified.append(head)
    return {
        "public_git_base": base_commit,
        "base_paths": len(base_tree),
        "integrated_paths_reconstructed": len(e58_sources),
        "isolated_paths_reconstructed": len(ea_sources),
        "integrated_overrides": len(integrated["overrides"]),
        "isolated_absent": len(isolated["absent_paths"]),
        "isolated_replacements": len(isolated["overrides"]),
        "direct_git_commit_trees_verified_if_present": directly_verified,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-repo", type=Path, help="Git checkout containing the public 4cc base tree")
    parser.add_argument("--raw-base", type=Path, help="Private cache parent containing all named original gate caches")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_bytes())
    listed = {"manifest.json"}
    for item in manifest["public_files"]:
        name = item["path"]
        assert name not in listed
        listed.add(name)
        checked(safe(ROOT, name), item)
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}
    assert listed == actual, {"unlisted": sorted(actual - listed), "missing": sorted(listed - actual)}
    assert manifest["excluded_original_members"] == [] and manifest["excluded_log_lines"] == 0
    assert manifest["scanner_exceptions"] == []
    scan_record = json.loads((ROOT / "PUBLICATION_SCAN.json").read_bytes())
    scanner_bytes = (ROOT / "publication_scanner.py").read_bytes()
    assert sha(scanner_bytes) == scan_record["scanner_sha256"]
    assert not scan_record["findings"] and not scan_record["exceptions"]
    for name in sorted(listed):
        findings = publication_scanner.inspect(manifest["publication_prefix"] + name, (ROOT / name).read_bytes())
        assert not findings, (name, findings)

    mappings = {}
    originals = {}
    counts = {}
    span_count = 0
    for item in manifest["raw_mappings"]:
        key = (item["raw_cache"], item["raw_path"])
        assert key not in mappings
        mappings[key] = item
        counts[key[0]] = counts.get(key[0], 0) + 1
        public = checked(safe(ROOT, item["public_path"]), item, "public_")
        assert public.count(b"\n") == item["line_count_public"] == item["line_count_original"]
        span_count += len(item["spans"])
        if args.raw_base:
            raw = checked(safe(args.raw_base, key[0] + "/" + key[1]), item, "raw_")
            assert replay(raw, item["spans"]) == public, key
            assert raw.count(b"\n") == item["line_count_original"]
            originals[key] = raw
        else:
            assert not item["spans"] or item["raw_sha256"] != item["public_sha256"]
            if not item["spans"]:
                assert item["raw_sha256"] == item["public_sha256"]
            originals[key] = public
    assert len(mappings) == 60 and counts == manifest["raw_owner_counts"]
    assert counts[EA_CACHE] == 29 and counts[E58_CACHE] == 30 and counts[COMP_CACHE] == 1
    assert manifest["raw_owner_scope"][COMP_CACHE] == "COMPOSITION.json only"
    if args.raw_base:
        for owner in (EA_CACHE, E58_CACHE):
            actual_paths = {p.relative_to(args.raw_base / owner).as_posix()
                            for p in (args.raw_base / owner).rglob("*") if p.is_file()}
            assert actual_paths == {name for cache, name in mappings if cache == owner}
    assert set(name for cache, name in mappings if cache == COMP_CACHE) == {"COMPOSITION.json"}

    composition = json.loads((ROOT / "source-composition.json").read_bytes())
    comp_original = originals[(COMP_CACHE, "COMPOSITION.json")]
    assert pin(comp_original) == {
        "bytes": composition["original_composition_bytes"],
        "sha256": composition["original_composition_sha256"],
    }
    comp = json.loads(comp_original)
    assert comp["isolated_full_python_commit"] == composition["isolated"]["commit"]
    assert comp["integrated_commit"] == composition["integrated"]["commit"]
    assert comp["isolated_engineering_paths"] == composition["isolated"]["path_count"]
    assert comp["integrated_engineering_paths"] == composition["integrated"]["path_count"]
    changed = {item["path"]: item for item in comp["changed_paths"]}
    isolated = composition["isolated"]
    integrated = composition["integrated"]
    assert len(changed) == comp["changed_path_count"] == 14
    assert set(changed) == set(isolated["absent_paths"]) | set(isolated["overrides"])
    for name, item in changed.items():
        if name in isolated["absent_paths"]:
            assert item["ea"] is None
        else:
            source = isolated["overrides"][name]
            assert item["ea"] == {"mode": source["git_mode"], "blob": source["git_blob"]}

    bound_stages = json.loads((ROOT / "stage-bindings.json").read_bytes())
    assert len(bound_stages) == 14
    stage_names = {
        EA_CACHE: {"python", "ruff", "mypy", "spec", "web", "web-lint", "web-build"},
        E58_CACHE: {"03b-related-final", "ruff", "mypy", "spec", "web", "web-lint", "web-build"},
    }
    expected_stage_keys = {(cache, stage) for cache, names in stage_names.items() for stage in names}
    assert {(item["raw_cache"], item["stage"]) for item in bound_stages} == expected_stage_keys
    snapshots = {}
    logs = {}
    for stage in bound_stages:
        cache = stage["raw_cache"]
        name = stage["stage"]
        receipt_bytes = originals[(cache, name + "/receipt.json")]
        before = originals[(cache, name + "/inputs-before.json")]
        after = originals[(cache, name + "/inputs-after.json")]
        log = originals[(cache, name + "/test.log")]
        runner = originals[(cache, stage["runner"])]
        receipt = json.loads(receipt_bytes)
        embedded_head, parsed = rows(before)
        assert before == after
        assert embedded_head in (None, stage["head"])
        assert sha(before) == stage["input_sha256"]
        if args.raw_base or not mappings[(cache, name + "/receipt.json")]["spans"]:
            assert sha(receipt_bytes) == stage["receipt_sha256"]
        if args.raw_base or not mappings[(cache, name + "/test.log")]["spans"]:
            assert sha(log) == stage["log_sha256"] and len(log) == stage["log_bytes"]
        assert receipt.get("head", receipt.get("code_commit")) == stage["head"]
        assert receipt.get("input_count", receipt.get("source_count")) == stage["input_count"] == len(parsed)
        assert receipt.get("inputs_unchanged", receipt.get("source_unchanged")) is True
        assert receipt["exit_code"] == stage["exit_code"] == 0 and receipt["timeout"] is False
        assert receipt["command"] == stage["command"]
        assert receipt["log_sha256"] == stage["log_sha256"]
        assert receipt["log_bytes"] == stage["log_bytes"]
        assert receipt["runner_sha256"] == stage["runner_sha256"]
        if args.raw_base or not mappings[(cache, stage["runner"])]["spans"]:
            assert sha(runner) == stage["runner_sha256"]
        if args.raw_base:
            assert sha(log) == receipt["log_sha256"] and len(log) == receipt["log_bytes"]
        if stage["head"] in snapshots:
            assert snapshots[stage["head"]] == parsed
        else:
            snapshots[stage["head"]] = parsed
        logs[(cache, name)] = log
    assert len(snapshots[composition["isolated"]["commit"]]) == 1055
    assert len(snapshots[composition["integrated"]["commit"]]) == 1066
    for name, item in changed.items():
        source = snapshots[integrated["commit"]][name]
        assert item["integrated"] == {"mode": source["git_mode"], "blob": source["git_blob"]}
    log_outcomes(logs)

    source_summary = {"source_reconstruction": "NOT_RUN: pass --git-repo"}
    if args.git_repo:
        source_summary = verify_source(args.git_repo, composition, snapshots)
        assert sha(run_git(args.git_repo, "show", composition["public_base"] + ":scripts/check_publication.py")) == scan_record["scanner_sha256"]
    print(json.dumps({
        "public_files_verified": len(listed),
        "raw_original_mappings": len(mappings),
        "raw_original_replay": "COMPLETE" if args.raw_base else "NOT_RUN: pass --raw-base",
        "path_replacement_spans": span_count,
        "original_log_lines_excluded": manifest["excluded_log_lines"],
        "stages": len(bound_stages),
        "ea_full_python": "2991 PASS; 1 actual sealed numeric BLOCKED_ENVIRONMENT SKIP; 2 dependency warnings",
        "e58_related_python": "239 PASS; 2 dependency warnings; full Python NOT_RUN",
        "ea_web": "512 PASS / 88 files",
        "e58_web": "538 PASS / 91 files",
        "source": source_summary,
        "scanner_findings": 0,
        "scanner_exceptions": 0,
        "product_tests": 0,
        "network_requests": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
