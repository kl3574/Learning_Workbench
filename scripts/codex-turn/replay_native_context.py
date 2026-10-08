#!/usr/bin/env python3
"""Prepare pinned native03 sources or run their 15 offline mechanical tests.

Provision/fetch are explicit engineering setup stages. No model, CLI, AppServer,
foreign handle or production registration is invoked. Existing replay inputs stay
unchanged; a fixture PASS supplies no platform mapping or InputProof authority.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import urllib.request

from replay_core_producer import graph_digest, test_summary, verify_graph
from replay_http_gate import (
    Recorder, differences, guarded_cache, inventory, normalize_metadata, require,
    sha256, utc, write_json,
)

ASSETS = {
    "retained-request-source.json", "retained-request.patch",
    "replay_retained_request.py", "replay_http_gate.py", "replay_core_producer.py",
    "_rust_retained_request.py", "retained_request_foreign_tests.py", "LICENSE", "NOTICE",
}
FIELDS = {
    "schema_version", "status", "spec", "source", "inherited_inputs", "patch",
    "changed_files", "complete_source_graph", "test_metadata", "lock_sha256",
    "rust", "test_selection", "profile", "historical_results", "production_boundary", "licensing",
}
SOURCE_SHA = "351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927"
BASE_SHA = "9a8c163b2683280dfdae0145018f7f8c0cd14804ac87741ef4cf52a20988be28"
LOCK_SHA = "5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c"
SELECTOR = "session::retained_outbound_snapshot::tests::"
CHANGED = {
    "codex-rs/core/src/client.rs", "codex-rs/core/src/retained_metadata.rs",
    "codex-rs/core/src/session/mod.rs",
    "codex-rs/core/src/session/retained_outbound_snapshot.rs",
    "codex-rs/core/src/session/retained_outbound_snapshot_tests.rs",
}


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def load(path: Path) -> dict:
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def verify_inputs(bundle: Path) -> dict:
    manifest = load(bundle / "native-context-source.json")
    require(set(manifest) == FIELDS and type(manifest["schema_version"]) is int
            and manifest["schema_version"] == 1, "Closed native manifest schema required")
    require(manifest["spec"] == {"version": "3.0.15", "sha256":
            "b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec"}, "Sole fixed specification required")
    require(set(manifest["inherited_inputs"]) == ASSETS, "Unexpected inherited source input")
    require(manifest["inherited_inputs"]["retained-request-source.json"] == BASE_SHA,
            "Fixed Metadata06 source manifest required")
    for name, digest in manifest["inherited_inputs"].items():
        path = bundle / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                "Inherited source input mismatch")
    base = load(bundle / "retained-request-source.json")
    require(manifest["source"] == base["source"]
            and manifest["source"]["archive_sha256"] == SOURCE_SHA
            and manifest["source"]["commit"] == "a956835d020762cb2b570053af06f643a11c0ecc",
            "Fixed official upstream source required")
    require(manifest["test_metadata"] == base["test_metadata"]
            and manifest["rust"] == base["rust"]
            and manifest["licensing"] == base["licensing"], "Inherited fixed setup mismatch")
    require(manifest["lock_sha256"] == LOCK_SHA, "Original lock required")
    require(manifest["patch"]["file"] == "native-context.patch"
            and sha256(bundle / "native-context.patch") == manifest["patch"]["sha256"],
            "Native incremental patch mismatch")
    rows = manifest["changed_files"]
    require(len(rows) == 5 and {row["path"] for row in rows} == CHANGED,
            "Exactly five native source paths required")
    for row in rows:
        require(set(row) == {"path", "before_sha256", "after_sha256", "after_bytes", "after_mode"}
                and type(row["after_bytes"]) is int and row["after_bytes"] > 0
                and type(row["after_mode"]) is int and row["after_mode"] == 0o664,
                "Closed changed-file identity required")
    for phase in ["source", "normalized"]:
        require(set(manifest["complete_source_graph"][phase]) == {"rows", "sha256"}
                and type(manifest["complete_source_graph"][phase]["rows"]) is int
                and manifest["complete_source_graph"][phase]["rows"] == 8787,
                "Complete native source graph required")
    selection = manifest["test_selection"]
    require(selection["package"] == "codex-core" and selection["filter"] == SELECTOR
            and selection["expected_passed"] == 15 and selection["expected_filtered"] == 2694
            and len(selection["test_names"]) == 15 and len(set(selection["test_names"])) == 15
            and all(name.startswith(SELECTOR) for name in selection["test_names"])
            and selection["argv_tail"] == ["test", "--locked", "--offline", "-p", "codex-core",
                                           "--lib", SELECTOR, "--", "--nocapture"],
            "Fixed nonzero15 offline selector required")
    profile = {key: value for key, value in manifest["profile"].items() if key != "scope"}
    require(profile == {"CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
                        "CARGO_PROFILE_DEV_INCREMENTAL": "false", "CARGO_PROFILE_TEST_INCREMENTAL": "false",
                        "CARGO_INCREMENTAL": "0", "CARGO_BUILD_JOBS": "2", "RUST_TEST_THREADS": "2"},
            "Fixed bounded test profile required")
    require(manifest["production_boundary"]["registration"] is False
            and manifest["production_boundary"]["native_capture_to_producer_or_FFI"] == "NOT_CONNECTED",
            "No production or bridge admission permitted")
    return manifest


def full_inventory(root: Path) -> dict:
    result = inventory(root)
    for relative, row in result.items():
        row["mode"] = (root / relative).lstat().st_mode & 0o7777
    return result


def verify_native(root: Path, manifest: dict, phase: str) -> dict:
    files = full_inventory(root)
    expected = manifest["complete_source_graph"][phase]
    require(len(files) == expected["rows"] and graph_digest(files) == expected["sha256"],
            "Complete native bytes/modes/link graph mismatch")
    require(sha256(root / "codex-rs/Cargo.lock") == LOCK_SHA, "Original lock changed")
    return files


def prepare(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
            bundle: Path, recorder: Recorder) -> int:
    require(args.archive is not None, "Prepare needs fixed source archive")
    archive = Path(args.archive).resolve(strict=True)
    require(archive.is_file() and sha256(archive) == SOURCE_SHA, "Official archive mismatch")
    base_output = output / "metadata24"
    row = recorder.run("metadata24-prepare-only", [sys.executable, str(bundle / "replay_retained_request.py"),
                       "--archive", str(archive), "--output-dir", str(base_output), "--prepare-only"], bundle)
    if row["exit_code"] != 0:
        return row["exit_code"] or 1
    inherited = load(base_output / "report.json")
    require(inherited["replay_exit_code"] == 0 and inherited["foreign_test"]["status"] == "NOT_RUN",
            "Source-only inherited preparation required")
    base_manifest = load(bundle / "retained-request-source.json")
    original = Path(inherited["paths"]["original"])
    normalized = Path(inherited["paths"]["patched"])
    verify_graph(inventory(original), base_manifest, "original")
    verify_graph(inventory(normalized), base_manifest, "normalized")
    source = output / "source"
    shutil.copytree(normalized, source, symlinks=True)
    # The inherited prepare-only already normalized its own independent copy.
    # Restore exactly the original metadata in this new source fork, retaining
    # its parent unchanged. Only the new test copy is then normalized below.
    metadata = manifest["test_metadata"]
    original_metadata = original / metadata["path"]
    require(sha256(original_metadata) == metadata["before_sha256"], "Original metadata mismatch")
    shutil.copyfile(original_metadata, source / metadata["path"])
    raw_base = inventory(source)
    verify_graph(raw_base, base_manifest, "patched")
    report["source_fork"] = {"inherited_normalized_parent_preserved": True,
                             "restored_original_metadata": metadata["path"],
                             "scope": "Exact0.160 metadata restored only in new fork; not release-build equivalence"}
    patch = bundle / "native-context.patch"
    for label, flags in [("native-apply-check", ["--check"]), ("native-apply", [])]:
        row = recorder.run(label, ["git", "apply", *flags, str(patch)], source)
        if row["exit_code"] != 0:
            return row["exit_code"] or 1
    source_files = verify_native(source, manifest, "source")
    require(differences(raw_base, inventory(source)) == sorted(CHANGED), "Native patch exceeded five paths")
    for row in manifest["changed_files"]:
        before = raw_base.get(row["path"])
        require((before["sha256"] if before else None) == row["before_sha256"], "Native before identity mismatch")
        after = source_files[row["path"]]
        require(after == {"kind": "file", "bytes": row["after_bytes"], "mode": row["after_mode"],
                          "sha256": row["after_sha256"]}, "Native after identity mismatch")
    tests = output / "test-source"
    shutil.copytree(source, tests, symlinks=True)
    normalize_metadata(tests, metadata)
    test_files = verify_native(tests, manifest, "normalized")
    require(differences(source_files, test_files) == [metadata["path"]], "Test normalization exceeded metadata")
    test_text = (tests / "codex-rs/core/src/session/retained_outbound_snapshot_tests.rs").read_text()
    names = sorted(SELECTOR + name for name in re.findall(r"#\[tokio::test\]\s+async fn (\w+)\(", test_text))
    require(names == manifest["test_selection"]["test_names"], "Native source test names mismatch")
    write_json(output / "source-before-files.json", source_files)
    write_json(output / "test-before-files.json", test_files)
    report["paths"] = {"source": str(source), "tests": str(tests), "inherited_original": str(original),
                       "inherited_normalized": str(normalized)}
    report["source_graph"] = {"source": manifest["complete_source_graph"]["source"],
                              "normalized": manifest["complete_source_graph"]["normalized"]}
    return 0


def download(url: str, path: Path, digest: str, report: dict, size: int | None = None) -> None:
    require(not path.exists(), "Download output must be new")
    row = {"url": url, "started_at_utc": utc(), "expected_sha256": digest, "status": "RUNNING"}
    report.setdefault("downloads", []).append(row)
    try:
        budget = size if size is not None else 2_000_000
        with urllib.request.urlopen(url, timeout=60) as response, path.open("xb") as output:
            row.update(final_url=response.geturl(), http_status=response.status)
            while chunk := response.read(min(1_048_576, budget + 1)):
                require(len(chunk) <= budget, "Official download byte budget exceeded")
                output.write(chunk)
                budget -= len(chunk)
        require(sha256(path) == digest and (size is None or path.stat().st_size == size),
                "Official download checksum/size mismatch")
        row["status"] = "PASS"
    except Exception:
        row["status"] = "FAIL"
        raise
    finally:
        row["ended_at_utc"] = utc()
        if path.exists():
            row.update(bytes=path.stat().st_size, actual_sha256=sha256(path))


def provision(output: Path, report: dict, manifest: dict, recorder: Recorder) -> int:
    rust = manifest["rust"]
    download(rust["official_manifest_url"], output / "official-rust-manifest.toml",
             rust["official_manifest_sha256"], report)
    toolchain = output / "toolchain"
    components = [row for row in rust["official_components"] if row["name"] != "rustfmt-preview"]
    require({row["name"] for row in components} == {"rustc", "cargo", "rust-std"}, "Fixed Rust components required")
    for component in components:
        archive = output / Path(component["url"]).name
        download(component["url"], archive, component["sha256"], report, component["bytes"])
        destination = output / (component["name"] + "-unpacked")
        destination.mkdir()
        with tarfile.open(archive, "r:xz") as handle:
            members = handle.getmembers()
            require(len(members) <= 100_000 and sum(row.size for row in members) <= 2_000_000_000,
                    "Official component extraction budget exceeded")
            roots = set()
            for member in members:
                path = PurePosixPath(member.name)
                require(path.parts and not path.is_absolute() and ".." not in path.parts
                        and "\\" not in member.name and not any(ord(c) < 32 for c in member.name),
                        "Unsafe official component path")
                roots.add(path.parts[0])
            require(len(roots) == 1, "Single official component root required")
            handle.extractall(destination, filter="data")
        installer = destination / next(iter(roots)) / "install.sh"
        require(installer.is_file() and not installer.is_symlink(), "Official installer required")
        command = ["sh", str(installer), "--prefix=" + str(toolchain), "--sysconfdir=" + str(toolchain / "etc"),
                   "--docdir=" + str(toolchain / "share/doc/rust"), "--libdir=" + str(toolchain / "lib"),
                   "--bindir=" + str(toolchain / "bin"), "--mandir=" + str(toolchain / "share/man"), "--disable-ldconfig"]
        row = recorder.run("install-" + component["name"], command, destination)
        if row["exit_code"] != 0:
            return row["exit_code"] or 1
    for name, expected in rust["installed_binary_sha256"].items():
        require(sha256(toolchain / "bin" / name) == expected, "Installed pinned Rust binary mismatch")
    report["toolchain"] = {"path": str(toolchain), "version": "1.95.0", "official_components_verified": True,
                           "global_installation": False, "compiler_binary_sha256": rust["installed_binary_sha256"]}
    return 0


def run_stage(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
              recorder: Recorder) -> int:
    require(args.prepared_dir and args.toolchain_dir and args.cargo_home, "Stage needs owned prepared source/toolchain/cache")
    prepared = Path(args.prepared_dir).resolve(strict=True)
    prior = load(prepared / "report.json")
    require(prior["mode"] == "prepare" and prior["status"] == "PASS"
            and prior["manifest_sha256"] == report["manifest_sha256"], "Matching actual prepared source required")
    source = prepared / "source"
    tests = prepared / "test-source"
    source_before = verify_native(source, manifest, "source")
    test_before = verify_native(tests, manifest, "normalized")
    toolchain = guarded_cache(args.toolchain_dir, ".rustup")
    cache = guarded_cache(args.cargo_home, ".cargo")
    bins = {name: toolchain / "bin" / name for name in ["rustc", "cargo", "rustdoc"]}
    for name, path in bins.items():
        require(path.is_file() and not path.is_symlink()
                and sha256(path) == manifest["rust"]["installed_binary_sha256"][name], "Pinned Rust binary required")
    environment = os.environ.copy()
    removed = [key for key in list(environment) if key.startswith("CARGO_PROFILE_") or key in {
        "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER",
        "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTC_WRAPPER", "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER", "CARGO_INCREMENTAL",
    }]
    for key in removed:
        del environment[key]
    task = {key: value for key, value in manifest["profile"].items() if key != "scope"}
    for name in ["rustup-home", "tmp"]:
        (output / name).mkdir()
    task.update(CARGO_HOME=str(cache), RUSTUP_HOME=str(output / "rustup-home"),
                RUSTC=str(bins["rustc"]), RUSTDOC=str(bins["rustdoc"]),
                CARGO_TARGET_DIR=str(output / "target"), TMPDIR=str(output / "tmp"))
    environment.update(task)
    environment["PATH"] = str(toolchain / "bin") + os.pathsep + environment.get("PATH", os.defpath)
    report["task_environment"] = {**task, "PATH_PREPEND": str(toolchain / "bin"), "removed_override_keys": removed}
    for name in ["rustc", "cargo"]:
        row = recorder.run(name + "-version", [str(bins[name]), "--version", "--verbose"], tests, environment, task)
        require(row["exit_code"] == 0, "Version command failed")
        text = (recorder.receipts / (name + "-version") / "stdout.log").read_text()
        require(re.search(r"(?m)^release: 1\.95\.0$", text) is not None, "Rust1.95.0 required")
    # Complete this actual0 precondition before launching the dependent Cargo.
    health = output / "tmp" / "owned-health"
    with health.open("xb") as stream:
        stream.write(b"owned-native-context-health\n")
        stream.flush()
        os.fsync(stream.fileno())
    require(health.read_bytes() == b"owned-native-context-health\n", "Owned temp readback failed")
    health.unlink()
    report["prelaunch_health"] = {"status": "PASS", "write_fsync_read_delete": True,
                                 "scope": "Only own tiny file; not full capacity qualification"}
    command = [str(bins["cargo"])] + (["fetch", "--locked"] if args.mode == "fetch" else manifest["test_selection"]["argv_tail"])
    row = recorder.run("cargo-" + args.mode, command, tests / "codex-rs", environment, task)
    result = row["exit_code"] if row["exit_code"] and row["exit_code"] > 0 else (1 if row["exit_code"] else 0)
    if args.mode == "test":
        text = (recorder.receipts / "cargo-test" / "stdout.log").read_text(errors="replace")
        stderr = (recorder.receipts / "cargo-test" / "stderr.log").read_text(errors="replace")
        summary = test_summary(text, manifest["test_selection"])
        compile_failed = summary["summary"] is None and not re.search(r"(?m)^running \d+ tests$", text) and "could not compile" in stderr
        report["tests"] = {**summary, "actual_cargo_exit": row["exit_code"],
                           "status": "NOT_RUN" if compile_failed else ("PASS" if result == 0 and summary["selection_matches"] else "FAIL"),
                           "tests_executed": 0 if compile_failed else (summary["summary"]["passed"] + summary["summary"]["failed"] if summary["summary"] else "UNKNOWN"),
                           "compile_failure": compile_failed, "scope": manifest["test_selection"]["scope"]}
        if result == 0 and not summary["selection_matches"]:
            result = 1
    source_after = verify_native(source, manifest, "source")
    test_after = verify_native(tests, manifest, "normalized")
    require(source_before == source_after and test_before == test_after, "Source changed during Cargo")
    write_json(output / "source-after-files.json", source_after)
    write_json(output / "test-after-files.json", test_after)
    report["source_before_after_exact"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prepare", "provision", "fetch", "test"], required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--archive")
    parser.add_argument("--prepared-dir")
    parser.add_argument("--toolchain-dir")
    parser.add_argument("--cargo-home")
    args = parser.parse_args()
    output = Path(args.output_dir).absolute()
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError:
        print("Output must be a new owned directory; nothing overwritten", file=sys.stderr)
        return 1
    bundle = Path(__file__).resolve().parent
    report = {"schema_version": 1, "mode": args.mode, "started_at_utc": utc(), "status": "RUNNING",
              "manifest_sha256": sha256(bundle / "native-context-source.json"), "runner_sha256": sha256(Path(__file__)),
              "commands": [], "tests": {"status": "NOT_RUN", "tests_executed": 0}, "production": "NOT_ADMITTED",
              "not_connected": ["nativecapture to producer/FFI", "qualified source/mapping/catalog/FinalAuth/InputProof",
                                "existing durable record_start ledger to actual send"],
              "not_run": ["foreign17", "fullcore/API/HTTP/guardian/platform suites", "Windows", "CLI/AppServer/models/actualsend"]}
    report["ci_context"] = {key: os.environ[key] for key in [
        "GITHUB_SHA", "GITHUB_REF", "GITHUB_EVENT_NAME", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
    ] if key in os.environ}
    write_json(output / "report.json", report)
    previous_umask = os.umask(0o002)
    try:
        manifest = verify_inputs(bundle)
        recorder = Recorder(output, report)
        if args.mode == "prepare":
            result = prepare(args, output, report, manifest, bundle, recorder)
        elif args.mode == "provision":
            result = provision(output, report, manifest, recorder)
        else:
            result = run_stage(args, output, report, manifest, recorder)
        verify_inputs(bundle)
        report["status"] = "PASS" if result == 0 else "FAIL"
    except KeyboardInterrupt:
        result = 130
        report.update(status="INTERRUPTED", error="Interrupted; no automatic retry")
    except Exception as error:
        result = 1
        report.update(status="FAIL", error_type=type(error).__name__, error="Stage failed; retained receipts identify actual command")
    finally:
        os.umask(previous_umask)
    report.update(ended_at_utc=utc(), actual_exit=result)
    write_json(output / "report.json", report)
    print(json.dumps({"mode": args.mode, "status": report["status"], "actual_exit": result,
                      "tests": report["tests"], "production": "NOT_ADMITTED", "report": str(output / "report.json")}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
