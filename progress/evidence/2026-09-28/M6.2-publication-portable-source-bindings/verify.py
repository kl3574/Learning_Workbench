#!/usr/bin/env python3
"""Verify source bytes using only the two public-history commits in bindings.json.

This performs no product tests, network access, checkout, or repository writes.
Original fixed commits are evidence labels and are never resolved by Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

sys.dont_write_bytecode = True


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def parse(data: bytes) -> object:
    return json.loads(data, object_pairs_hook=json_object)


def relative(path: str) -> str:
    p = PurePosixPath(path)
    require(bool(path) and not p.is_absolute() and ".." not in p.parts
            and str(p) == path, "noncanonical relative path")
    return path


def read(root: Path, path: str) -> bytes:
    p = root / relative(path)
    require(not p.is_symlink() and p.is_file(), "missing or linked package member")
    require(p.resolve().is_relative_to(root.resolve()), "member escapes package")
    return p.read_bytes()


def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, "Git read failed: " + args[0])
    return result.stdout


def engineering_tree(repo: Path, commit: str) -> dict[str, dict]:
    require(len(commit) == 40 and all(c in "0123456789abcdef" for c in commit),
            "invalid pinned commit")
    raw = git(repo, "ls-tree", "-r", "-z", commit)
    tree = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, name = item.split(b"\t", 1)
        mode, kind, blob = header.decode().split()
        path = relative(name.decode())
        if path.startswith("progress/"):
            continue
        require(kind == "blob" and path not in tree, "unsupported Git entry")
        tree[path] = {"git_mode": mode, "git_blob_sha1": blob}
    objects = sorted({row["git_blob_sha1"] for row in tree.values()})
    payload = git(repo, "cat-file", "--batch", data="".join(x + "\n" for x in objects).encode())
    cursor = 0
    checked = {}
    for wanted in objects:
        end = payload.index(b"\n", cursor)
        blob, kind, length = payload[cursor:end].decode().split()
        require(blob == wanted and kind == "blob", "unexpected Git object")
        cursor = end + 1
        length = int(length)
        body = payload[cursor:cursor + length]
        require(len(body) == length and payload[cursor + length:cursor + length + 1] == b"\n",
                "truncated Git blob")
        calculated = hashlib.sha1(b"blob " + str(length).encode() + b"\0" + body).hexdigest()
        require(calculated == blob, "Git object digest mismatch")
        checked[blob] = {"bytes": length, "sha256": sha(body)}
        cursor += length + 1
    require(cursor == len(payload), "extra Git batch bytes")
    for row in tree.values():
        row.update(checked[row["git_blob_sha1"]])
    return dict(sorted(tree.items()))


def input_rows(data: object) -> dict[str, dict]:
    if isinstance(data, dict):
        require(all(isinstance(v, dict) for v in data.values()), "invalid input manifest")
        return {relative(k): v for k, v in data.items()}
    require(isinstance(data, list), "invalid input manifest")
    result = {}
    for row in data:
        require(isinstance(row, dict), "invalid input row")
        path = relative(row["path"])
        require(path not in result, "duplicate input row")
        result[path] = row
    return result


def main(root: Path, repo: Path) -> dict:
    manifest = parse(read(root, "manifest.json"))
    actual_paths = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    require(actual_paths == set(manifest["files"]) | {"manifest.json"}, "package member set mismatch")
    for path, row in manifest["files"].items():
        data = read(root, path)
        require(len(data) == row["bytes"] and sha(data) == row["sha256"], "package digest mismatch: " + path)
    bindings = parse(read(root, "bindings.json"))
    require(bindings["engineering_exclusion"] == "progress/", "unsupported engineering scope")
    base_commit = bindings["public_base_commit"]
    overlay_commit = bindings["public_overlay_commit"]
    require(git(repo, "merge-base", base_commit, overlay_commit).decode().strip() == base_commit,
            "public base is not an ancestor of overlay")
    base = engineering_tree(repo, base_commit)
    overlay = engineering_tree(repo, overlay_commit)
    require(len(base) == bindings["base_engineering_files"], "base count mismatch")
    require(len(overlay) == bindings["overlay_engineering_files"], "overlay count mismatch")
    summaries = []
    for target in bindings["targets"]:
        overrides = target["overlay_paths"]
        require(len(set(overrides)) == len(overrides), "duplicate overlay path")
        reconstructed = dict(base)
        for path in overrides:
            relative(path)
            require(path in overlay and not path.startswith("progress/"), "invalid overlay path")
            reconstructed[path] = overlay[path]
        expected = parse(read(root, target["expected_engineering_manifest"]))
        require(reconstructed == expected, "full source reconstruction mismatch: " + target["id"])
        require(len(reconstructed) == target["engineering_files"], "source count mismatch")
        package = target["original_public_package"]
        package_bytes = read(root, package["manifest_copy"])
        require(sha(package_bytes) == package["manifest_sha256"], "original package manifest mismatch")
        original_manifest = parse(package_bytes)
        original_rows = original_manifest.get("files", original_manifest.get("included_raw"))
        verified_inputs = 0
        for evidence in target["final_input_manifests"]:
            raw = read(root, evidence["copy"])
            require(sha(raw) == evidence["sha256"] and len(raw) == evidence["bytes"], "original input digest mismatch")
            matches = [r for r in original_rows if r["raw_path"] == evidence["original_raw_path"]
                       and r.get("raw_cache", target["original_raw_cache"]) == target["original_raw_cache"]]
            require(len(matches) == 1, "ambiguous original package input mapping")
            mapping = matches[0]
            require(mapping["raw_sha256"] == mapping["public_sha256"] == evidence["sha256"]
                    and mapping["raw_bytes"] == mapping["public_bytes"] == evidence["bytes"]
                    and mapping["public_path"] == evidence["original_public_path"],
                    "original public input mapping mismatch")
            rows = input_rows(parse(raw))
            require(len(rows) == evidence["input_count"], "input count mismatch")
            require(set(rows) <= set(reconstructed), "unknown original engineering input")
            if target["input_scope"] == "entire_engineering_tree":
                require(set(rows) == set(reconstructed), "incomplete original full-tree inputs")
            else:
                require(target["input_scope"] == "original_827_explicit_engineering_inputs"
                        and len(rows) == 827, "unexpected observer execution scope")
            for path, row in rows.items():
                source = reconstructed[path]
                require(row["sha256"] == source["sha256"] and row["bytes"] == source["bytes"],
                        "original execution input mismatch: " + path)
                for key in ("git_blob_sha1", "git_blob"):
                    if key in row:
                        require(row[key] == source["git_blob_sha1"], "original Git blob mismatch")
                if "git_mode" in row:
                    require(row["git_mode"] == source["git_mode"], "original Git mode mismatch")
                if "git_matches" in row:
                    require(row["git_matches"] is True, "original input did not match Git")
            verified_inputs += len(rows)
        summaries.append({"id": target["id"], "original_fixed_commit": target["original_fixed_commit"],
                          "source_files": len(reconstructed), "overlay_paths": len(overrides),
                          "final_input_manifest_count": len(target["final_input_manifests"]),
                          "verified_input_records": verified_inputs, "input_scope": target["input_scope"]})
    return {"status": "PASS", "scope": "source portability only; no product tests executed",
            "git_commits_read": [base_commit, overlay_commit], "targets": summaries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-repo", type=Path, required=True,
                        help="a normal or bare repository containing the public main history")
    args = parser.parse_args()
    try:
        print(json.dumps(main(Path(__file__).resolve().parent, args.git_repo), indent=2, sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError) as error:
        # Avoid echoing environment-dependent absolute paths from native errors.
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__,
                          "detail": str(error) if isinstance(error, ValueError) else "verification input unavailable or invalid"}))
        raise SystemExit(1)
