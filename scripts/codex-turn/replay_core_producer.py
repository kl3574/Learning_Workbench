#!/usr/bin/env python3
"""Replay 14 pinned local codex-core producer tests; no CLI or model execution.

Uses the HTTP replay's validated extraction, patch application, one metadata
normalization and actual-command recorder. Default tests are strictly offline
and locked; full core/guardian suites and production admission are outside it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from replay_http_gate import (
    Recorder, execute, guarded_cache, inventory, require, sha256, utc,
    verify_source, write_json,
)


def graph_digest(files: dict) -> str:
    data = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def verify_graph(files: dict, manifest: dict, phase: str) -> None:
    expected = manifest["complete_source_graph"][phase]
    require(len(files) == expected["rows"] and graph_digest(files) == expected["sha256"],
            f"Complete {phase} source graph mismatch (bytes, modes or links)")
    link = manifest["complete_source_graph"]["preserved_symlink"]
    require(files.get(link["path"]) == {"kind": "symlink", "target": link["target"]},
            "Original upstream license symlink missing or changed")


def test_summary(text: str, scope: dict) -> dict:
    matches = re.findall(
        r"test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; "
        r"(\d+) measured; (\d+) filtered out", text,
    )
    summary = None
    if len(matches) == 1:
        state, *counts = matches[0]
        summary = {"state": state, **dict(zip(
            ["passed", "failed", "ignored", "measured", "filtered"], map(int, counts),
        ))}
    names = sorted(re.findall(r"(?m)^test (\S+) \.\.\. ok$", text))
    return {"summary": summary, "actual_passed_test_names": names,
            "selection_matches": summary == {
                "state": "ok", "passed": scope["expected_passed"], "failed": 0,
                "ignored": 0, "measured": 0, "filtered": scope["expected_filtered"],
            } and names == scope["test_names"]}


def run_tests(args: argparse.Namespace, output: Path, report: dict, manifest: dict) -> int:
    require(args.toolchain_dir and args.cargo_home,
            "Tests require --toolchain-dir and --cargo-home")
    toolchain = guarded_cache(args.toolchain_dir, ".rustup")
    cache = guarded_cache(args.cargo_home, ".cargo")
    bins = {name: toolchain / "bin" / name for name in ["rustc", "cargo", "rustdoc"]}
    for name, path in bins.items():
        require(path.is_file() and not path.is_symlink(), f"Standalone {name} required")
        require(sha256(path) == manifest["rust"]["installed_binary_sha256"][name],
                f"Pinned {name} SHA256 mismatch")
    env = os.environ.copy()
    removed = [key for key in [
        "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS",
        "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTC_WRAPPER", "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER",
    ] if key in env]
    for key in removed:
        del env[key]
    task_env = {
        "CARGO_HOME": str(cache), "RUSTUP_HOME": str(output / "rustup-home"),
        "RUSTC": str(bins["rustc"]), "RUSTDOC": str(bins["rustdoc"]),
        "CARGO_TARGET_DIR": str(output / "target"), "CARGO_BUILD_JOBS": "2",
    }
    (output / "rustup-home").mkdir()
    env.update(task_env)
    env["PATH"] = str(toolchain / "bin") + os.pathsep + env.get("PATH", os.defpath)
    recorded_env = {**task_env, "PATH_PREPEND": str(toolchain / "bin"),
                    "removed_build_override_keys": removed}
    report["task_environment"] = recorded_env
    core_output = output / "core-tests"
    core_output.mkdir()
    recorder = Recorder(core_output, report)
    source = Path(report["paths"]["patched"])
    for name in ["rustc", "cargo"]:
        row = recorder.run(name + "-version", [str(bins[name]), "--version", "--verbose"],
                           source, env, recorded_env)
        require(row["exit_code"] == 0, f"{name} version command failed")
        text = (recorder.receipts / (name + "-version") / "stdout.log").read_text(encoding="utf-8")
        require(re.search(r"(?m)^release: 1\.95\.0$", text) is not None,
                f"{name} is not Rust 1.95.0")
    selection = manifest["test_selection"]
    require(selection["package"] == "codex-core" and selection["strict_locked_offline"] is True,
            "Expected fixed offline codex-core selection")
    require([scope["expected_passed"] for scope in selection["scopes"]] == [11, 2, 1]
            and selection["selected_total"] == 14, "Expected exactly 11+2+1 selected tests")
    report["test"] = {"scope": "14-test local subset", "status": "RUNNING",
                      "actual_exit_code": None, "scopes": [], "actual_selected_passed": 0}
    result = 0
    for scope in selection["scopes"]:
        command = [str(bins["cargo"]), "test", "-p", "codex-core", "--lib", scope["filter"],
                   "--locked", "--offline", "--", "--test-threads=2"]
        row = recorder.run(scope["label"], command, source / "codex-rs", env, recorded_env)
        text = (recorder.receipts / scope["label"] / "stdout.log").read_text(
            encoding="utf-8", errors="replace",
        )
        observed = test_summary(text, scope)
        observed.update(label=scope["label"], actual_exit_code=row["exit_code"])
        report["test"]["scopes"].append(observed)
        if observed["summary"]:
            report["test"]["actual_selected_passed"] += observed["summary"]["passed"]
        if row["exit_code"] != 0:
            result = row["exit_code"] if row["exit_code"] is not None and row["exit_code"] > 0 else 1
            break
        if not observed["selection_matches"]:
            result = 1
            report["test"]["selection_error"] = "Zero Cargo exit did not prove the exact nonzero selection"
            break
        stderr = (recorder.receipts / scope["label"] / "stderr.log").read_text(
            encoding="utf-8", errors="replace",
        )
        binaries = re.findall(r"Running unittests .* \(([^\n]+)\)", stderr)
        require(len(binaries) == 1, "Cannot bind actual selected test binary from Cargo receipt")
        binary = Path(binaries[0]).resolve(strict=True)
        target = (output / "target").resolve(strict=True)
        require(target in binary.parents and binary.is_file(), "Test binary outside owned target")
        identity = {"path": str(binary), "sha256": sha256(binary), "bytes": binary.stat().st_size,
                    "scope": scope["label"], "metadata": "test-only normalized0.0.0"}
        report.setdefault("actual_test_binaries", []).append(identity)
        write_json(output / "report.json", report)
    report["test"].update(status="PASS" if result == 0 else "FAIL", actual_exit_code=result)
    if result == 0:
        require(len(report["test"]["scopes"]) == 3
                and report["test"]["actual_selected_passed"] == 14,
                "Expected exactly14 selected PASS; zero or partial selection is not success")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Original pinned local Codex archive")
    parser.add_argument("--output-dir", required=True, help="New nonexistent private output directory")
    parser.add_argument("--toolchain-dir", help="Task-owned standalone Rust1.95.0 prefix")
    parser.add_argument("--cargo-home", help="Separately prepared task-owned Cargo dependency cache")
    parser.add_argument("--prepare-only", action="store_true", help="Apply and validate; run no Cargo or Rust")
    args = parser.parse_args()
    output = Path(args.output_dir).absolute()
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as error:
        print(f"Output directory must be new; nothing overwritten: {error}", file=sys.stderr)
        return 1
    output = output.resolve()
    manifest_path = Path(__file__).with_name("core-producer-source.json")
    report = {
        "schema_version": 1, "started_at_utc": utc(), "status": "RUNNING",
        "replay_wrapper_sha256": sha256(Path(__file__).resolve()),
        "production": "INCOMPLETE / NOT_ADMITTED", "invocation": [sys.executable, *sys.argv],
        "commands": [], "graph": {"nodes": [], "edges": []},
        "test_scope": "fixed11controlled+2stockWSheaders+1stockinternalcache, strict locked offline",
        "historical_http_client": "114 PASS / 6 FAIL retained; not superseded by core subset",
        "plain_facts": "Mechanical consistency only, not trusted InputProof or owner authority",
        "not_run": ["complete2676 core lib suite", "guardian tests", "API190 replay", "HTTP tests",
                    "FinalAuth", "control ledger to actual HTTP send binding", "Codex CLI", "AppServer", "models",
                    "platform acceptance", "production profile admission"],
    }
    write_json(output / "report.json", report)
    try:
        # Reuse the unchanged HTTP preparation mechanism; its final node marks
        # source-only verification, followed below by a separate core-tested node.
        prepare_args = SimpleNamespace(archive=args.archive, prepare_only=True,
                                       toolchain_dir=None, cargo_home=None, all_lib=False, offline=True)
        result = execute(prepare_args, output, report, manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for phase, filename in [("original", "original-files.json"), ("patched", "patched-files.json"),
                                ("normalized", "normalized-files.json")]:
            verify_graph(json.loads((output / filename).read_text(encoding="utf-8")), manifest, phase)
        report["complete_graph_verification"] = "PASS: complete bytes/modes/links"
        if not args.prepare_only:
            result = run_tests(args, output, report, manifest)
        original = Path(report["paths"]["original"])
        patched = Path(report["paths"]["patched"])
        verify_source(original, manifest, "original")
        verify_source(patched, manifest, "normalized")
        verify_graph(inventory(original), manifest, "original")
        final = inventory(patched)
        verify_graph(final, manifest, "normalized")
        write_json(output / "core-final-files.json", final)
        require(sha256(Path(args.archive)) == manifest["source"]["archive_sha256"], "Input archive changed")
        report["graph"]["nodes"].append({"id": "core-final", "files_sha256": sha256(output / "core-final-files.json")})
        report["graph"]["edges"].append({"from": "final", "to": "core-final", "changed_files": [],
                                         "core_test_scopes": [] if args.prepare_only else report["test"]["scopes"]})
        report["status"] = "PASS" if result == 0 else "FAIL"
    except KeyboardInterrupt:
        result = 130
        report.update(status="INTERRUPTED", error="KeyboardInterrupt; receipts retained, no rerun")
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
