#!/usr/bin/env python3
"""Rebuild the pinned private core cdylib and run 17 actual foreign memory tests.

No Codex CLI, AppServer, transport, model, secret store, ledger or production
qualification is invoked. Existing core22/HTTP replay inputs remain independent.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace
from replay_http_gate import Recorder, execute, guarded_cache, inventory, require, sha256, utc, verify_source, write_json
from replay_core_producer import verify_graph


def verify_foreign_inputs(bundle: Path, manifest: dict) -> dict:
    fields = manifest["foreign_inputs"]
    paths = {"owner": bundle / fields["owner_file"], "tests": bundle / fields["tests_file"],
             "helper": bundle / "replay_http_gate.py",
             "graph_helper": bundle / "replay_core_producer.py"}
    expected = {"owner": fields["owner_sha256"], "tests": fields["tests_sha256"],
                "helper": fields["existing_preparation_helper_sha256"],
                "graph_helper": fields["existing_graph_helper_sha256"]}
    actual = {}
    for name, path in paths.items():
        require(path.is_file() and not path.is_symlink(), "Fixed source file required")
        require(sha256(path) == expected[name], "Foreign source input SHA256 mismatch")
        actual[name] = {"path": str(path), "sha256": expected[name]}
    selection = manifest["foreign_test_selection"]
    require(selection["test_methods"] == 17 and len(selection["test_names"]) == 17
            and len(set(selection["test_names"])) == 17
            and selection["strict_locked_offline"] is True
            and selection["build_package"] == "codex-core"
            and selection["crate_type"] == "cdylib", "Expected fixed nonzero17 foreign selection")
    return actual


def build_and_test(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
                   bundle: Path) -> int:
    require(args.toolchain_dir and args.cargo_home, "Build needs task-owned toolchain and Cargo cache")
    toolchain = guarded_cache(args.toolchain_dir, ".rustup")
    cache = guarded_cache(args.cargo_home, ".cargo")
    binaries = {name: toolchain / "bin" / name for name in ["rustc", "cargo", "rustdoc"]}
    for name, binary in binaries.items():
        require(binary.is_file() and not binary.is_symlink(), "Standalone Rust binary required")
        require(sha256(binary) == manifest["rust"]["installed_binary_sha256"][name], "Pinned Rust binary mismatch")
    environment = os.environ.copy()
    removed = [name for name in ["RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS",
                                "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTC_WRAPPER", "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER"] if name in environment]
    for name in removed:
        del environment[name]
    task = {"CARGO_HOME": str(cache), "RUSTUP_HOME": str(output / "rustup-home"),
            "RUSTC": str(binaries["rustc"]), "RUSTDOC": str(binaries["rustdoc"]),
            "CARGO_TARGET_DIR": str(output / "target"), "CARGO_BUILD_JOBS": "2"}
    (output / "rustup-home").mkdir()
    environment.update(task)
    environment["PATH"] = str(toolchain / "bin") + os.pathsep + environment.get("PATH", os.defpath)
    recorded = {**task, "PATH_PREPEND": str(toolchain / "bin"), "removed_build_override_keys": removed}
    report["task_environment"] = recorded
    stage = output / "foreign-memory"
    stage.mkdir()
    recorder = Recorder(stage, report)
    source = Path(report["paths"]["patched"])
    for name in ["rustc", "cargo"]:
        row = recorder.run(name + "-version", [str(binaries[name]), "--version", "--verbose"], source, environment, recorded)
        require(row["exit_code"] == 0, "Rust version command failed")
        version = (recorder.receipts / (name + "-version") / "stdout.log").read_text()
        require(re.search(r"(?m)^release: 1\.95\.0$", version) is not None, "Expected Rust1.95.0")
    report["foreign_test"] = {"status": "NOT_RUN", "actual_exit_code": None, "methods": 0}
    command = [str(binaries["cargo"]), "rustc", "-p", "codex-core", "--lib", "--crate-type", "cdylib", "--locked", "--offline"]
    row = recorder.run("core-cdylib-build", command, source / "codex-rs", environment, recorded)
    report["build"] = {"actual_exit_code": row["exit_code"], "status": "PASS" if row["exit_code"] == 0 else "FAIL"}
    if row["exit_code"] != 0:
        return row["exit_code"] if row["exit_code"] and row["exit_code"] > 0 else 1
    binary = output / "target" / "debug" / "libcodex_core.so"
    require(binary.is_file() and not binary.is_symlink(), "Expected freshly built owned Linux cdylib")
    require((output / "target").resolve() in binary.resolve().parents, "Library outside owned target")
    libraries = output / "libraries"
    libraries.mkdir()
    retained = libraries / "libcodex_core.so"
    shutil.copyfile(binary, retained)
    retained.chmod(0o400)
    digest = sha256(retained)
    require(digest == sha256(binary), "Retained library changed during copy")
    before = retained.stat()
    report["actual_library"] = {"compiled_path": str(binary), "retained_path": str(retained), "bytes": before.st_size,
                                "sha256": digest, "retained_posix_mode": "0400", "device": before.st_dev, "inode": before.st_ino,
                                "scope": "Fresh test-normalized owned library; not originalCLI or production loader"}
    report["foreign_inputs"] = verify_foreign_inputs(bundle, manifest)
    write_json(output / "report.json", report)
    command = [sys.executable, "-I", "-S", "-B", str(bundle / manifest["foreign_inputs"]["tests_file"]),
               "--library", str(retained), "--sha256", digest]
    row = recorder.run("foreign-memory17", command, source, environment, recorded)
    text = (recorder.receipts / "foreign-memory17" / "stderr.log").read_text(errors="replace")
    names = sorted(re.findall(r"(?m)^(test_\S+) \([^\n]+\) \.\.\. ok$", text))
    footers = re.findall(r"(?m)^Ran (\d+) tests in [^\n]+$", text)
    selected = (names == manifest["foreign_test_selection"]["test_names"]
                and footers == ["17"] and text.rstrip().endswith("OK"))
    report["foreign_test"] = {"status": "PASS" if row["exit_code"] == 0 and selected else "FAIL",
                              "actual_exit_code": row["exit_code"], "methods": len(names), "test_names": names,
                              "selection_matches": selected, "scope": "Actual ctypes17 foreign memory tests, no send"}
    verify_foreign_inputs(bundle, manifest)
    after = retained.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and sha256(retained) == digest and (after.st_mode & 0o7777) == 0o400, "Owned frozen library changed")
    report["owned_library_preserved_after_tests"] = True
    if row["exit_code"] != 0:
        return row["exit_code"] if row["exit_code"] and row["exit_code"] > 0 else 1
    return 0 if selected else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output-dir", required=True, help="New nonexistent private output directory")
    parser.add_argument("--toolchain-dir")
    parser.add_argument("--cargo-home")
    parser.add_argument("--prepare-only", action="store_true", help="Source verification only; zero Cargo/Rust/foreign calls")
    args = parser.parse_args()
    output = Path(args.output_dir).absolute()
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as error:
        print(f"Output must be new; nothing overwritten: {error}", file=sys.stderr)
        return 1
    output = output.resolve()
    bundle = Path(__file__).resolve().parent
    manifest_path = bundle / "retained-request-source.json"
    report = {"schema_version": 1, "started_at_utc": utc(), "status": "RUNNING", "production": "INCOMPLETE / NOT_ADMITTED",
              "invocation": [sys.executable, *sys.argv], "runner_sha256": sha256(Path(__file__).resolve()),
              "commands": [], "graph": {"nodes": [], "edges": []},
              "foreign_test": {"status": "NOT_RUN", "actual_exit_code": None, "methods": 0},
              "not_run": ["core22/full2684", "HTTP8/full120", "API190", "guardian suites", "Codex CLI", "AppServer", "models", "actual HTTP transport/send", "platform suites", "production admission"],
              "not_implemented": ["trusted SecretStore/config owner", "InputProof metering", "durable record_start/permit to retained handle and send", "restart accounting", "qualified loader/resource/network executor"],
              "panic_boundary": "Default hook unchanged; catch_unwind status does not guarantee silence; panic branch not tested",
              "loader_boundary": "Owned immutable path/hash/inode only; not qualified general loader or comprehensive TOCTOU guarantee"}
    write_json(output / "report.json", report)
    # git apply creates new regular sources from 0666 masked by the process
    # umask. Bind this task-local setting so complete POSIX graphs are portable.
    previous_umask = os.umask(0o002)
    report["preparation_umask"] = {"task": "0002", "previous": f"{previous_umask:04o}",
                                   "scope": "This replay process only; restored before return"}
    try:
        manifest = json.loads(manifest_path.read_text())
        report["foreign_inputs"] = verify_foreign_inputs(bundle, manifest)
        prepare = SimpleNamespace(archive=args.archive, prepare_only=True, toolchain_dir=None, cargo_home=None, all_lib=False, offline=True)
        result = execute(prepare, output, report, manifest_path)
        for phase in ["original", "patched", "normalized"]:
            verify_graph(json.loads((output / (phase + "-files.json")).read_text()), manifest, phase)
        report["complete_source_graph_verified"] = True
        if not args.prepare_only:
            result = build_and_test(args, output, report, manifest, bundle)
        original = Path(report["paths"]["original"])
        source = Path(report["paths"]["patched"])
        verify_source(original, manifest, "original")
        verify_source(source, manifest, "normalized")
        verify_graph(inventory(original), manifest, "original")
        final = inventory(source)
        verify_graph(final, manifest, "normalized")
        write_json(output / "foreign-final-files.json", final)
        require(sha256(Path(args.archive)) == manifest["source"]["archive_sha256"], "Input archive changed")
        require(sha256(manifest_path) == report["inputs"]["manifest_sha256"], "Source manifest changed")
        verify_foreign_inputs(bundle, manifest)
        report["status"] = "PASS" if result == 0 else "FAIL"
        report["scope"] = "source-only verified; foreign tests NOT_RUN" if args.prepare_only else "fresh cdylib +17 actual foreign memory tests"
    except KeyboardInterrupt:
        result = 130
        report.update(status="INTERRUPTED", error="Interrupted; receipts retained, no automatic rerun")
    except Exception as error:
        result = 1
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        os.umask(previous_umask)
    report["ended_at_utc"] = utc()
    report["replay_exit_code"] = result
    write_json(output / "report.json", report)
    print(json.dumps({"status": report["status"], "actual_exit_code": result, "foreign_test": report["foreign_test"],
                      "report": str(output / "report.json"), "production": report["production"]}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
