"""Verify public hashes, exact stage input reconstruction and optional private replay."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(root, relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and ".." not in path.parts
    return root / relative


def checked(path, row, prefix=""):
    raw = path.read_bytes()
    assert len(raw) == row[prefix + "bytes"] and sha(raw) == row[prefix + "sha256"], str(path)
    return raw


def replay(raw, spans):
    chunks, end = [], 0
    for span in spans:
        assert end <= span["start"] < span["end"] <= len(raw)
        assert sha(raw[span["start"]:span["end"]]) == span["raw_span_sha256"]
        chunks.extend([raw[end:span["start"]], span["replacement"].encode()])
        end = span["end"]
    return b"".join([*chunks, raw[end:]])


def input_bytes(index, key):
    base = index["baseline"]
    delta = index["snapshots"][key]
    rows = {row["path"]: row for row in base["files"] if row["path"] not in delta["absent"]}
    rows.update({row["path"]: row for row in delta["overrides"]})
    value = {"head": delta["head"], "files": [rows[name] for name in sorted(rows)]}
    raw = (json.dumps(value, indent=2) + "\n").encode()
    assert sha(raw) == key
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-base", type=Path)
    parser.add_argument("--git-repo", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_bytes())
    expected = {"manifest.json"}
    for row in manifest["public_files"]:
        expected.add(row["path"])
        checked(safe(root, row["path"]), row)
    assert expected == {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    source_index = json.loads((root / "source-map.json").read_bytes())
    input_index = json.loads((root / "input-map.json").read_bytes())
    sources = {}
    git_rows = 0
    for digest, row in source_index["sources"].items():
        if row["method"] == "public-git":
            git_rows += 1
            if not args.git_repo:
                continue
            raw = subprocess.check_output(["git", "show", source_index["public_base"] + ":" + row["path"]], cwd=args.git_repo)
            blob = subprocess.check_output(["git", "rev-parse", source_index["public_base"] + ":" + row["path"]], cwd=args.git_repo, text=True).strip()
            assert blob == row["git_blob"]
        else:
            raw = checked(safe(root, row["path"]), row)
        assert sha(raw) == digest and len(raw) == row["bytes"]
        sources[digest] = raw
    reconstructed = {key: input_bytes(input_index, key) for key in input_index["snapshots"]}
    for raw in reconstructed.values():
        data = json.loads(raw)
        for row in data["files"]:
            assert row["sha256"] in source_index["sources"]
            assert row["bytes"] == source_index["sources"][row["sha256"]]["bytes"]
    covered = {}
    for row in manifest["raw_mappings"]:
        covered.setdefault(row["raw_cache"], set()).add(row["raw_path"])
        if row["method"] == "file":
            derived = checked(safe(root, row["public_path"]), row, "public_")
        elif row["method"] == "source":
            derived = sources.get(row["raw_sha256"])
        elif row["method"] == "input":
            derived = reconstructed[row["raw_sha256"]]
        else:
            raise AssertionError(row["method"])
        if derived is not None and row["method"] != "file":
            assert len(derived) == row["raw_bytes"] and sha(derived) == row["raw_sha256"]
        if args.raw_base:
            raw = checked(safe(args.raw_base, row["raw_cache"] + "/" + row["raw_path"]), row, "raw_")
            assert derived is not None, "--git-repo required for complete private replay"
            assert replay(raw, row.get("spans", [])) == derived
    if args.raw_base:
        for cache, info in manifest["raw_manifests"].items():
            original = checked(safe(args.raw_base, cache + "/" + info["path"]), info)
            value = json.loads(original)
            members = value.get("members", value.get("files"))
            assert covered[cache] == {item["path"] for item in members} | {info["path"]}
    print(json.dumps({"public_files": len(expected), "raw_mappings": len(manifest["raw_mappings"]),
                      "source_pool": len(source_index["sources"]), "public_git_sources": git_rows,
                      "public_git_verified": bool(args.git_repo), "complete_input_snapshots_reconstructed": len(reconstructed),
                      "private_replay": bool(args.raw_base), "excluded_log_lines": 0}, indent=2))


if __name__ == "__main__":
    main()
