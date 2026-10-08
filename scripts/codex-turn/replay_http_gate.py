#!/usr/bin/env python3
"""Reproduce the pinned upstream library slice in a new private directory.

Python standard library only. Requires git; a test run additionally requires the
specified standalone Rust toolchain and a separately prepared Cargo cache.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_file(root: Path, relative: str, expected: str | None) -> None:
    path = root / relative
    if expected is None:
        require(not path.exists() and not path.is_symlink(), f"Expected absent file: {relative}")
    else:
        require(path.is_file() and not path.is_symlink(), f"Expected regular file: {relative}")
        require(sha256(path) == expected, f"SHA256 mismatch: {relative}")


def inventory(root: Path) -> dict:
    """Bind all source files, executable modes and symlinks without following links."""
    files = {}
    for directory, directories, names in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in sorted(directories + names):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                files[relative] = {"kind": "symlink", "target": os.readlink(path)}
            elif path.is_file():
                files[relative] = {"kind": "file", "sha256": sha256(path),
                                   "bytes": path.stat().st_size, "mode": path.stat().st_mode & 0o777}
    return dict(sorted(files.items()))


def differences(before: dict, after: dict) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def safe_extract(archive: Path, destination: Path, expected_root: str) -> Path:
    """Validate the complete pinned tar before writing files; create links last."""
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        require(len(members) <= 100_000, "Archive member budget exceeded")
        require(sum(member.size for member in members) <= 1_000_000_000, "Archive byte budget exceeded")
        by_name = {}
        links = []
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in member.name,
                    f"Unsafe archive path: {member.name!r}")
            require(path.parts and path.parts[0] == expected_root, "Unexpected archive root")
            require(not any(ord(char) < 32 for char in member.name), "Control character in archive path")
            name = path.as_posix()
            require(name not in by_name, f"Duplicate archive path: {name}")
            require(member.isfile() or member.isdir() or member.issym(),
                    f"Unsupported archive entry: {name}")
            by_name[name] = member
            if member.issym():
                require(member.linkname and not member.linkname.startswith("/")
                        and "\\" not in member.linkname, f"Unsafe symlink: {name}")
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), member.linkname))
                require(target.startswith(expected_root + "/"), f"Escaping symlink: {name}")
                links.append((name, target, member.linkname))
        link_names = {name for name, _, _ in links}
        for name in by_name:
            require(not any(parent.as_posix() in link_names for parent in PurePosixPath(name).parents),
                    f"Archive entry beneath symlink: {name}")
        for name, target, _ in links:
            require(target in by_name and by_name[target].isfile(),
                    f"Symlink target must be an in-archive regular file: {name}")
        destination.mkdir()
        for name, member in by_name.items():
            if member.issym():
                continue
            path = destination / name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                source = handle.extractfile(member)
                require(source is not None, f"Missing archive body: {name}")
                with source, path.open("xb") as output:
                    shutil.copyfileobj(source, output)
                path.chmod(member.mode & 0o777)
        for name, _, target_text in links:
            (destination / name).symlink_to(target_text)
    return destination / expected_root


class Recorder:
    def __init__(self, output: Path, report: dict):
        self.receipts = output / "receipts"
        self.receipts.mkdir()
        self.report = report

    def run(self, label: str, command: list[str], cwd: Path, env: dict | None = None,
            task_environment: dict | None = None) -> dict:
        receipt = self.receipts / label
        receipt.mkdir()
        row = {"label": label, "command": command, "cwd": str(cwd), "started_at_utc": utc(),
               "task_environment": task_environment or {}, "exit_code": None}
        write_json(receipt / "command.json", row)
        self.report["commands"].append(row)
        try:
            with (receipt / "stdout.log").open("wb") as stdout, (receipt / "stderr.log").open("wb") as stderr:
                completed = subprocess.run(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr, check=False)
            row["exit_code"] = completed.returncode
        except OSError as error:
            row["launch_error"] = str(error)
            raise
        finally:
            row["ended_at_utc"] = utc()
            row["outputs"] = {name: {"path": str(receipt / name), "sha256": sha256(receipt / name),
                                     "bytes": (receipt / name).stat().st_size}
                              for name in ["stdout.log", "stderr.log"] if (receipt / name).exists()}
            write_json(receipt / "command.json", row)
        return row


def verify_source(root: Path, manifest: dict, phase: str) -> None:
    for row in manifest["changed_files"]:
        check_file(root, row["path"], row["before_sha256" if phase == "original" else "after_sha256"])
    for row in manifest["preserved_files"]:
        check_file(root, row["path"], row["sha256"])
    metadata = manifest["test_metadata"]
    check_file(root, metadata["path"], metadata["after_sha256" if phase == "normalized" else "before_sha256"])
    if phase != "original":
        for row in manifest["candidate_crate_files"]:
            check_file(root, row["path"], row["sha256"])


def normalize_metadata(root: Path, metadata: dict) -> None:
    path = root / metadata["path"]
    data = path.read_bytes()
    section = re.search(rb"(?ms)^\[workspace\.package\]\r?\n(.*?)(?=^\[|\Z)", data)
    require(section is not None, "Missing workspace.package section")
    old = b'version = "' + metadata["before_version"].encode("ascii") + b'"'
    new = b'version = "' + metadata["after_version"].encode("ascii") + b'"'
    match = re.search(rb"(?m)^" + re.escape(old) + rb"$", section.group(1))
    require(match is not None and section.group(1).count(old) == 1, "Unexpected workspace version metadata")
    start = section.start(1) + match.start()
    path.write_bytes(data[:start] + new + data[start + len(old):])
    check_file(root, metadata["path"], metadata["after_sha256"])


def guarded_cache(path: str, global_name: str) -> Path:
    cache = Path(path).resolve(strict=True)
    global_cache = (Path.home() / global_name).resolve()
    require(cache.is_dir(), "Expected task-owned directory")
    require(cache != global_cache and global_cache not in cache.parents,
            f"Refusing global {global_name} cache")
    return cache


def execute(args: argparse.Namespace, output: Path, report: dict) -> int:
    bundle = Path(__file__).resolve().parent
    manifest_path = bundle / "source.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = Path(args.archive).resolve(strict=True)
    report["inputs"] = {"archive": str(archive), "archive_sha256": sha256(archive),
                        "manifest_sha256": sha256(manifest_path), "script_sha256": sha256(Path(__file__).resolve())}
    require(report["inputs"]["archive_sha256"] == manifest["source"]["archive_sha256"], "Archive SHA256 mismatch")
    patch = bundle / manifest["patch"]["file"]
    require(sha256(patch) == manifest["patch"]["sha256"], "Patch SHA256 mismatch")
    for name in ["LICENSE", "NOTICE"]:
        require(sha256(bundle / name) == manifest["licensing"][name + "_sha256"], f"Bundle {name} SHA256 mismatch")
    shutil.copyfile(manifest_path, output / "source-input.json")
    recorder = Recorder(output, report)
    source = safe_extract(archive, output / "original", manifest["source"]["archive_root"])
    verify_source(source, manifest, "original")
    original = inventory(source)
    write_json(output / "original-files.json", original)
    report["graph"]["nodes"].append({"id": "original", "files_sha256": sha256(output / "original-files.json")})
    patched = output / "patched" / manifest["source"]["archive_root"]
    patched.parent.mkdir()
    shutil.copytree(source, patched, symlinks=True)
    git = shutil.which("git")
    require(git is not None, "git executable required")
    for label, options in [("git-apply-check", ["--check"]), ("git-apply", [])]:
        row = recorder.run(label, [git, "apply", *options, str(patch)], patched)
        require(row["exit_code"] == 0, f"{label} failed; see retained receipt")
    verify_source(patched, manifest, "patched")
    after_patch = inventory(patched)
    require(differences(original, after_patch) == sorted(row["path"] for row in manifest["changed_files"]),
            "Patch changed files outside the four-path source slice")
    write_json(output / "patched-files.json", after_patch)
    report["graph"]["nodes"].append({"id": "patched", "files_sha256": sha256(output / "patched-files.json")})
    report["graph"]["edges"].append({"from": "original", "to": "patched", "receipts": ["git-apply-check", "git-apply"],
                                     "changed_files": differences(original, after_patch)})
    normalize_metadata(patched, manifest["test_metadata"])
    verify_source(patched, manifest, "normalized")
    normalized = inventory(patched)
    require(differences(after_patch, normalized) == [manifest["test_metadata"]["path"]], "Unexpected metadata changes")
    write_json(output / "normalized-files.json", normalized)
    report["graph"]["nodes"].append({"id": "normalized", "files_sha256": sha256(output / "normalized-files.json")})
    report["graph"]["edges"].append({"from": "patched", "to": "normalized", "changed_files": differences(after_patch, normalized),
                                     "operation": "test-only workspace.package.version 0.160.0 -> 0.0.0"})
    report["source_verification"] = "PASS"
    report["paths"] = {"original": str(source), "patched": str(patched)}
    result = 0
    if not args.prepare_only:
        require(args.toolchain_dir and args.cargo_home, "Test run requires --toolchain-dir and --cargo-home")
        toolchain = guarded_cache(args.toolchain_dir, ".rustup")
        cargo_home = guarded_cache(args.cargo_home, ".cargo")
        bins = {name: toolchain / "bin" / name for name in ["rustc", "cargo", "rustdoc"]}
        for name, path in bins.items():
            require(path.is_file() and not path.is_symlink(), f"Standalone {name} required")
            require(sha256(path) == manifest["rust"]["installed_binary_sha256"][name], f"Pinned {name} SHA256 mismatch")
        env = os.environ.copy()
        removed = [key for key in ["RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS",
                                   "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTC_WRAPPER", "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER"] if key in env]
        for key in removed:
            del env[key]
        task_env = {"CARGO_HOME": str(cargo_home), "RUSTUP_HOME": str(output / "rustup-home"),
                    "RUSTC": str(bins["rustc"]), "RUSTDOC": str(bins["rustdoc"]),
                    "CARGO_TARGET_DIR": str(output / "target"), "CARGO_BUILD_JOBS": "2"}
        (output / "rustup-home").mkdir()
        env.update(task_env)
        env["PATH"] = str(toolchain / "bin") + os.pathsep + env.get("PATH", os.defpath)
        recorded_env = {**task_env, "PATH_PREPEND": str(toolchain / "bin"), "removed_build_override_keys": removed}
        report["task_environment"] = recorded_env
        for name in ["rustc", "cargo"]:
            row = recorder.run(name + "-version", [str(bins[name]), "--version", "--verbose"], patched, env, recorded_env)
            require(row["exit_code"] == 0, f"{name} version command failed")
            text = (recorder.receipts / (name + "-version") / "stdout.log").read_text(encoding="utf-8")
            require(re.search(r"(?m)^release: 1\.95\.0$", text) is not None, f"{name} is not 1.95.0")
        command = [str(bins["cargo"]), "test", "-p", "codex-http-client", "--lib"]
        if not args.all_lib:
            command.append(manifest["test_selection"]["default_filter"])
        command.append("--locked")
        if args.offline:
            command.append("--offline")
        command.extend(["--", "--test-threads=2"])
        row = recorder.run("cargo-library-test", command, patched / "codex-rs", env, recorded_env)
        result = row["exit_code"]
        text = (recorder.receipts / "cargo-library-test" / "stdout.log").read_text(encoding="utf-8", errors="replace")
        matches = re.findall(r"test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out", text)
        report["test"] = {"scope": "all-lib" if args.all_lib else "gate-subset", "actual_exit_code": result,
                          "status": "PASS" if result == 0 else "FAIL", "summary": None}
        if matches:
            state, passed, failed, ignored, measured, filtered = matches[-1]
            report["test"]["summary"] = dict(zip(["passed", "failed", "ignored", "measured", "filtered"],
                                                  map(int, [passed, failed, ignored, measured, filtered])))
        if result == 0:
            expected = manifest["test_selection"]["all_lib_expected_total" if args.all_lib else "default_expected_passed"]
            require(report["test"]["summary"] is not None and int(matches[-1][1]) == expected
                    and int(matches[-1][2]) == 0 and int(matches[-1][3]) == 0,
                    "Zero cargo exit did not prove the expected test selection")
    else:
        report["test"] = {"scope": "prepare-only", "status": "NOT_RUN", "actual_exit_code": None}
    verify_source(source, manifest, "original")
    verify_source(patched, manifest, "normalized")
    require(inventory(source) == original, "Original source directory changed")
    final = inventory(patched)
    write_json(output / "final-files.json", final)
    require(final == normalized, "Build/test changed source files; retained for inspection")
    require(sha256(archive) == report["inputs"]["archive_sha256"], "Input archive changed")
    report["graph"]["nodes"].append({"id": "final", "files_sha256": sha256(output / "final-files.json")})
    report["graph"]["edges"].append({"from": "normalized", "to": "final", "changed_files": [],
                                     "test_receipt": None if args.prepare_only else "cargo-library-test"})
    report["original_preserved"] = True
    report["source_and_lock_preserved_after_test"] = True
    return result if result is not None and result >= 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Local official archive; SHA256 must match source.json")
    parser.add_argument("--output-dir", required=True, help="New, nonexistent private output directory")
    parser.add_argument("--toolchain-dir", help="Task-owned standalone Rust 1.95.0 prefix containing bin/")
    parser.add_argument("--cargo-home", help="Separately prepared task-owned Cargo dependency cache")
    parser.add_argument("--offline", action="store_true", help="Add cargo --offline; retain a missing-cache failure")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--prepare-only", action="store_true", help="Extract, check/apply and verify; execute no Cargo or Rust")
    selection.add_argument("--all-lib", action="store_true", help="Run all library tests; never mask known/full gate failures")
    args = parser.parse_args()
    output = Path(args.output_dir).absolute()
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as error:
        print(f"Output directory must be new; nothing overwritten: {error}", file=sys.stderr)
        return 1
    output = output.resolve()
    report = {"schema_version": 1, "started_at_utc": utc(), "status": "RUNNING", "production": "INCOMPLETE / NOT_ADMITTED",
              "invocation": [sys.executable, *sys.argv], "commands": [], "graph": {"nodes": [], "edges": []},
              "not_run": ["Codex CLI", "AppServer", "models", "platform acceptance", "production profile admission"]}
    write_json(output / "report.json", report)
    try:
        result = execute(args, output, report)
        report["status"] = "PASS" if result == 0 else "FAIL"
    except KeyboardInterrupt:
        result = 130
        report.update(status="INTERRUPTED", error="KeyboardInterrupt; receipts retained, no automatic rerun")
    except Exception as error:
        result = 1
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    report["ended_at_utc"] = utc()
    report["replay_exit_code"] = result
    write_json(output / "report.json", report)
    print(json.dumps({"status": report["status"], "exit_code": result, "test": report.get("test"),
                      "report": str(output / "report.json"), "production": report["production"]}, ensure_ascii=False))
    if "error" in report:
        print(report["error"], file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
