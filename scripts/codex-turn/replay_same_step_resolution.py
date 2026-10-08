#!/usr/bin/env python3
"""Prepare pinned same-Step repair sources or validate 9+22+7+10 and Clippy.

Only explicit CI setup provisions Rust/fetches dependencies. This engineering
entry never runs Codex CLI, AppServer, a model, foreign handle or a sender, and
cannot register a model/InputProof or claim full-core/production acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tomllib
import urllib.request

from replay_core_producer import graph_digest, verify_graph
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
    "schema_version", "status", "spec", "source", "inherited_inputs", "native03", "patch",
    "changed_files", "complete_source_graph", "test_metadata", "lock_sha256", "rust",
    "test_selection", "profile", "source_binding", "clippy", "clippy_repair", "production_boundary", "licensing",
}
SOURCE_SHA = "351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927"
BASE_SHA = "9a8c163b2683280dfdae0145018f7f8c0cd14804ac87741ef4cf52a20988be28"
LOCK_SHA = "5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c"
NATIVE_PATCH_SHA = "6b94dd7b84ac84f166335e42ab1fe1bd994c17ecac3cbcde35b95c273932426e"
R2_PINS_SHA = "4bd60a1dde7bb2d14e6791d0c5ae89119e89d610188b61ca6acb9f0c3317312d"
CLIPPY_SHA = "ac779bc9839dd47180806b133e4e2563c4a34716284cd5b8fede8ef289f452ca"
REPAIR_PATCH_SHA = "345c9e3c6c66751c68a4a92b8c895027a90f3e48541aca12da7c456829fa5f8c"
REPAIR_BEFORE_GRAPH = {"rows": 8789, "sha256":
                       "444a0c518583e501e1cb045e04316349436ea9a2897edcccb61554101bbcb400"}
REPAIR_BEFORE_FILES = {
    "codex-rs/core/src/retained_metadata_tests.rs":
        "366ea6c52a8fab4fa180884eb92320673af99195eb6aeb1b18841c61566bf94d",
    "codex-rs/core/src/session/retained_outbound_snapshot_tests.rs":
        "56cad20ddb172fa27a5f8a6ba90cf585209ae73056498657f4528f3597b63b2d",
}
SCOPES = [
    ("manager9", "codex-models-manager", "manager::retained_model_resolution::tests::", 9),
    ("native22", "codex-core", "session::retained_outbound_snapshot::tests::", 22),
    ("step-settings7", "codex-core", "session::step_settings::tests::", 7),
    ("metadata10", "codex-core", "client::retained_metadata::tests::", 10),
]
CHANGED = {
    "codex-rs/models-manager/src/manager.rs",
    "codex-rs/models-manager/src/retained_model_resolution.rs",
    "codex-rs/models-manager/src/retained_model_resolution_tests.rs",
    "codex-rs/core/src/session/step_settings.rs", "codex-rs/core/src/session/step_settings_tests.rs",
    "codex-rs/core/src/session/turn_context.rs", "codex-rs/core/src/session/mod.rs",
    "codex-rs/core/src/session/retained_outbound_snapshot.rs",
    "codex-rs/core/src/session/retained_outbound_snapshot_tests.rs",
}
CLIPPY_ARGV = ["clippy", "--locked", "--offline", "-p", "codex-models-manager",
              "-p", "codex-core", "--lib", "--tests", "--no-deps"]


class MissingClippyTool(RuntimeError):
    """A required owned Clippy tool is absent; no Cargo test is started."""


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def load(path: Path) -> dict:
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def test_summary(text: str, scope: dict) -> dict:
    matches = re.findall(
        r"(?m)^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; "
        r"(\d+) measured; (\d+) filtered out; finished in [^\n]+$", text,
    )
    summary = None
    if len(matches) == 1:
        state, *counts = matches[0]
        summary = {"state": state, **dict(zip(
            ["passed", "failed", "ignored", "measured", "filtered"], map(int, counts),
        ))}
    names = sorted(re.findall(r"(?m)^test (\S+) \.\.\. ok$", text))
    running = list(map(int, re.findall(r"(?m)^running (\d+) tests?$", text)))
    selected = (summary is not None and summary["state"] == "ok"
                and summary["passed"] == scope["expected_passed"]
                and summary["failed"] == summary["ignored"] == summary["measured"] == 0
                and running == [scope["expected_passed"]] and names == scope["test_names"])
    return {"summary": summary, "actual_passed_test_names": names,
            "actual_running_counts": running, "selection_matches": selected,
            "filtered_count_scope": "Actual observation only; never an inherited expected count"}


def verify_inputs(bundle: Path) -> dict:
    manifest = load(bundle / "same-step-resolution-source.json")
    require(set(manifest) == FIELDS and type(manifest["schema_version"]) is int
            and manifest["schema_version"] == 1, "Closed same-Step source contract required")
    require(manifest["spec"] == {"version": "3.0.15", "sha256":
            "b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec"}, "Sole fixed specification required")
    require(set(manifest["inherited_inputs"]) == ASSETS
            and manifest["inherited_inputs"]["retained-request-source.json"] == BASE_SHA,
            "Fixed Metadata24 inherited inputs required")
    for name, digest in manifest["inherited_inputs"].items():
        path = bundle / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                "Inherited source input mismatch")
    base = load(bundle / "retained-request-source.json")
    require(manifest["source"] == base["source"] and manifest["source"]["archive_sha256"] == SOURCE_SHA
            and manifest["source"]["commit"] == "a956835d020762cb2b570053af06f643a11c0ecc",
            "Fixed official archive required")
    require(manifest["test_metadata"] == base["test_metadata"] and manifest["licensing"] == base["licensing"],
            "Original metadata normalization/license contract required")
    require({k: v for k, v in manifest["rust"].items() if k != "clippy_component"} == base["rust"],
            "Original pinned Rust setup required")
    component = manifest["rust"]["clippy_component"]
    require(component["name"] == "clippy-preview" and component["sha256"] == CLIPPY_SHA
            and component["url"] == "https://static.rust-lang.org/dist/2026-04-16/clippy-1.95.0-x86_64-unknown-linux-gnu.tar.xz"
            and component["download_max_bytes"] == 20_000_000, "Pinned official Clippy component required")
    require(manifest["lock_sha256"] == LOCK_SHA, "Original Cargo lock required")
    native = manifest["native03"]
    require(native["patch_file"] == "native-context.patch" and native["patch_sha256"] == NATIVE_PATCH_SHA
            and sha256(bundle / "native-context.patch") == NATIVE_PATCH_SHA,
            "Exact Native03 incremental patch required")
    require(native["source_graph"] == {"rows": 8787, "sha256":
            "df5d1917e2de209945096aa8f64796fdaf76374da6c468d69bb8553e3d42ccd3"},
            "Fixed Native03 source graph required")
    require(manifest["patch"]["file"] == "same-step-resolution.patch"
            and sha256(bundle / "same-step-resolution.patch") == manifest["patch"]["sha256"],
            "Final same-Step patch mismatch")
    require(manifest["source_binding"]["r2_source_pins_sha256"] == R2_PINS_SHA
            and manifest["source_binding"]["no_model_version_authority"] is True, "Fixed r2 source binding required")
    repair = manifest["clippy_repair"]
    require(set(repair) == {"patch_file", "patch_sha256", "before_graph", "changed_files",
                           "status", "repair_author_manifest_sha256"}
            and repair["patch_file"] == "clippy-repair.patch"
            and repair["patch_sha256"] == REPAIR_PATCH_SHA
            and sha256(bundle / "clippy-repair.patch") == REPAIR_PATCH_SHA
            and repair["before_graph"] == REPAIR_BEFORE_GRAPH,
            "Fixed actual66 Clippy repair patch and before graph required")
    repair_rows = repair["changed_files"]
    require(len(repair_rows) == 2 and {row["path"] for row in repair_rows} == set(REPAIR_BEFORE_FILES),
            "Exactly two affected test sources required")
    for row in repair_rows:
        require(set(row) == {"path", "before_sha256", "after_sha256", "after_bytes", "after_mode"}
                and row["before_sha256"] == REPAIR_BEFORE_FILES[row["path"]]
                and type(row["after_bytes"]) is int and row["after_bytes"] > 0
                and type(row["after_mode"]) is int and row["after_mode"] == 0o664,
                "Closed repair source byte/fullmode identity required")
    rows = manifest["changed_files"]
    require(len(rows) == 9 and {row["path"] for row in rows} == CHANGED,
            "Exactly nine same-Step source paths required")
    for row in rows:
        require(set(row) == {"path", "before_sha256", "after_sha256", "after_bytes", "after_mode"}
                and type(row["after_bytes"]) is int and row["after_bytes"] > 0
                and type(row["after_mode"]) is int and row["after_mode"] == 0o664,
                "Closed source byte/fullmode identity required")
    for phase in ["source", "normalized"]:
        graph = manifest["complete_source_graph"][phase]
        require(set(graph) == {"rows", "sha256"} and type(graph["rows"]) is int
                and graph["rows"] == 8789, "Complete source graph required")
    selections = manifest["test_selection"]
    require(len(selections["scopes"]) == 4 and selections["selected_total"] == 48
            and selections["same_step_selected_total"] == 31 and selections["affected_ordinary_selected_total"] == 7
            and selections["affected_metadata_selected_total"] == 10,
            "Fixed nonzero31 plus affected ordinary7 and metadata10 required")
    for scope, (label, package, selector, count) in zip(selections["scopes"], SCOPES):
        require(scope["label"] == label and scope["package"] == package and scope["filter"] == selector
                and type(scope["expected_passed"]) is int and scope["expected_passed"] == count
                and len(scope["test_names"]) == len(set(scope["test_names"])) == count
                and scope["test_names"] == sorted(scope["test_names"])
                and all(name.startswith(selector) for name in scope["test_names"])
                and scope["argv_tail"] == ["test", "--locked", "--offline", "-p", package,
                                           "--lib", selector, "--", "--nocapture"],
                "Exact fixed source selector required")
    require(manifest["clippy"]["argv_tail"] == CLIPPY_ARGV, "Existing-rules two-package Clippy required")
    require({k: v for k, v in manifest["profile"].items() if k != "scope"} == {
        "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
        "CARGO_PROFILE_DEV_INCREMENTAL": "false", "CARGO_PROFILE_TEST_INCREMENTAL": "false",
        "CARGO_INCREMENTAL": "0", "CARGO_BUILD_JOBS": "2", "RUST_TEST_THREADS": "2",
    }, "Fixed bounded compilation profile required")
    require(manifest["production_boundary"]["registration"] is False
            and manifest["production_boundary"]["qualification"] == "Unqualified"
            and manifest["production_boundary"]["authoritative_model_version"] is None,
            "No production qualification permitted")
    return manifest


def full_inventory(root: Path) -> dict:
    result = inventory(root)
    for relative, row in result.items():
        row["mode"] = (root / relative).lstat().st_mode & 0o7777
    return result


def verify_prepared(root: Path, manifest: dict, phase: str) -> dict:
    files = full_inventory(root)
    graph = manifest["complete_source_graph"][phase]
    require(len(files) == graph["rows"] and graph_digest(files) == graph["sha256"],
            "Complete same-Step source bytes/fullmodes/links mismatch")
    require(sha256(root / "codex-rs/Cargo.lock") == LOCK_SHA, "Original Cargo lock changed")
    return files


def source_test_names(root: Path) -> list[list[str]]:
    result = []
    for relative, selector in [
        ("codex-rs/models-manager/src/retained_model_resolution_tests.rs", SCOPES[0][2]),
        ("codex-rs/core/src/session/retained_outbound_snapshot_tests.rs", SCOPES[1][2]),
    ]:
        text = (root / relative).read_text()
        result.append(sorted(selector + name for name in re.findall(r"#\[tokio::test\]\s+async fn (\w+)\(", text)))
    text = (root / "codex-rs/core/src/session/step_settings_tests.rs").read_text()
    names = re.findall(r"#\[(?:test|tokio::test)\]\s+(?:async )?fn (\w+)\(", text)
    function = "model_resolution_preserves_startup_overrides_and_instruction_provenance"
    require(names.count(function) == 1, "Fixed parameterized ordinary test required")
    names.remove(function)
    labels = re.findall(r'#\[test_case\([^\n]+; "([^"]+)"\)\]', text)
    require(labels == ["explicit instructions", "model-derived instructions"], "Fixed two case labels required")
    result.append(sorted([SCOPES[2][2] + name for name in names] + [
        SCOPES[2][2] + function + "::" + re.sub(r"[^A-Za-z0-9_]", "_", label) for label in labels
    ]))
    metadata = (root / "codex-rs/core/src/retained_metadata_tests.rs").read_text()
    result.append(sorted(SCOPES[3][2] + name for name in re.findall(r"#\[test\]\s+fn (\w+)\(", metadata)))
    return result


def prepare(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
            bundle: Path, recorder: Recorder) -> int:
    require(args.archive is not None, "Prepare needs fixed local source archive")
    archive = Path(args.archive).resolve(strict=True)
    require(archive.is_file() and sha256(archive) == SOURCE_SHA, "Official archive mismatch")
    parent = output / "metadata24"
    row = recorder.run("metadata24-prepare-only", [sys.executable, str(bundle / "replay_retained_request.py"),
                       "--archive", str(archive), "--output-dir", str(parent), "--prepare-only"], bundle)
    if row["exit_code"] != 0:
        return row["exit_code"] or 1
    inherited = load(parent / "report.json")
    require(inherited["replay_exit_code"] == 0 and inherited["foreign_test"]["status"] == "NOT_RUN",
            "Prepare-only parent required; no Cargo/library call")
    base = load(bundle / "retained-request-source.json")
    original = Path(inherited["paths"]["original"])
    normalized = Path(inherited["paths"]["patched"])
    verify_graph(inventory(original), base, "original")
    verify_graph(inventory(normalized), base, "normalized")
    source = output / "source"
    shutil.copytree(normalized, source, symlinks=True)
    metadata = manifest["test_metadata"]
    original_metadata = original / metadata["path"]
    require(sha256(original_metadata) == metadata["before_sha256"], "Original0.160 metadata required")
    shutil.copyfile(original_metadata, source / metadata["path"])
    raw_base = inventory(source)
    verify_graph(raw_base, base, "patched")
    report["source_fork"] = {"parent_preserved": True, "only_original_metadata_restored": metadata["path"],
                             "source_version": "0.160.0", "test_version": "0.0.0", "release_equivalence": False}
    for label, filename, expected in [
        ("native03", "native-context.patch", manifest["native03"]),
        ("same-step-r2", "same-step-resolution.patch", manifest),
        ("clippy-repair", "clippy-repair.patch", manifest["clippy_repair"]),
    ]:
        before = full_inventory(source)
        if label == "clippy-repair":
            require(len(before) == REPAIR_BEFORE_GRAPH["rows"]
                    and graph_digest(before) == REPAIR_BEFORE_GRAPH["sha256"],
                    "Exact actual66 source required before Clippy repair")
        for suffix, flags in [("check", ["--check"]), ("apply", [])]:
            row = recorder.run(label + "-" + suffix, ["git", "apply", *flags, str(bundle / filename)], source)
            if row["exit_code"] != 0:
                return row["exit_code"] or 1
        after = full_inventory(source)
        rows = expected["changed_files"]
        require(differences(before, after) == sorted(row["path"] for row in rows), "Patch exceeded fixed source paths")
        for row in rows:
            previous = before.get(row["path"])
            require((previous["sha256"] if previous else None) == row["before_sha256"], "Before source mismatch")
            require(after[row["path"]] == {"kind": "file", "bytes": row["after_bytes"],
                    "sha256": row["after_sha256"], "mode": row["after_mode"]}, "After source/fullmode mismatch")
        if label == "native03":
            graph = manifest["native03"]["source_graph"]
            require(len(after) == graph["rows"] and graph_digest(after) == graph["sha256"], "Native03 graph mismatch")
    source_files = verify_prepared(source, manifest, "source")
    tests = output / "test-source"
    shutil.copytree(source, tests, symlinks=True)
    normalize_metadata(tests, metadata)
    test_files = verify_prepared(tests, manifest, "normalized")
    require(differences(source_files, test_files) == [metadata["path"]], "Only one workspace normalization allowed")
    require(source_test_names(tests) == [scope["test_names"] for scope in manifest["test_selection"]["scopes"]],
            "Exact source test-name candidates required")
    write_json(output / "source-before-files.json", source_files)
    write_json(output / "test-before-files.json", test_files)
    report["paths"] = {"source": str(source), "tests": str(tests), "inherited_original": str(original),
                       "inherited_normalized": str(normalized)}
    report["source_graph"] = manifest["complete_source_graph"]
    report["source_names_checked"] = True
    return 0


def download(url: str, path: Path, digest: str, report: dict, max_bytes: int,
             expected_size: int | None = None) -> None:
    require(not path.exists(), "Download output must be new")
    row = {"url": url, "started_at_utc": utc(), "expected_sha256": digest, "status": "RUNNING"}
    report.setdefault("downloads", []).append(row)
    try:
        budget = max_bytes
        with urllib.request.urlopen(url, timeout=60) as response, path.open("xb") as stream:
            row.update(final_url=response.geturl(), http_status=response.status)
            while chunk := response.read(min(1_048_576, budget + 1)):
                require(len(chunk) <= budget, "Official download byte budget exceeded")
                stream.write(chunk)
                budget -= len(chunk)
        require(sha256(path) == digest and (expected_size is None or path.stat().st_size == expected_size),
                "Official download checksum/size mismatch")
        row["status"] = "PASS"
    except Exception:
        row["status"] = "FAIL"
        raise
    finally:
        row["ended_at_utc"] = utc()
        if path.exists():
            row.update(bytes=path.stat().st_size, actual_sha256=sha256(path))


def clippy_binary_hashes(archive: Path) -> dict:
    require(sha256(archive) == CLIPPY_SHA, "Pinned official Clippy archive required")
    result = {}
    with tarfile.open(archive, "r:xz") as handle:
        for name in ["cargo-clippy", "clippy-driver"]:
            rows = [row for row in handle.getmembers() if row.name.endswith("/bin/" + name)]
            require(len(rows) == 1 and rows[0].isfile(), "Unique official Clippy binary required")
            stream = handle.extractfile(rows[0])
            require(stream is not None, "Official Clippy binary unavailable")
            result[name] = hashlib.sha256(stream.read()).hexdigest()
    return result


def provision(output: Path, report: dict, manifest: dict, recorder: Recorder) -> int:
    rust = manifest["rust"]
    official = output / "official-rust-manifest.toml"
    download(rust["official_manifest_url"], official, rust["official_manifest_sha256"], report, 2_000_000)
    catalog = tomllib.loads(official.read_text())
    component = rust["clippy_component"]
    clippy = catalog["pkg"]["clippy-preview"]["target"][rust["host"]]
    require(clippy["available"] is True and clippy["xz_url"] == component["url"]
            and clippy["xz_hash"] == component["sha256"], "Clippy pin differs from verified official manifest")
    toolchain = output / "toolchain"
    components = [row for row in rust["official_components"] if row["name"] != "rustfmt-preview"] + [component]
    require({row["name"] for row in components} == {"rustc", "cargo", "rust-std", "clippy-preview"},
            "Fixed four official components required")
    for row in components:
        archive = output / Path(row["url"]).name
        download(row["url"], archive, row["sha256"], report,
                 row.get("download_max_bytes", row.get("bytes", 0)), row.get("bytes"))
        destination = output / (row["name"] + "-unpacked")
        destination.mkdir()
        with tarfile.open(archive, "r:xz") as handle:
            members = handle.getmembers()
            require(len(members) <= 100_000 and sum(member.size for member in members) <= 2_000_000_000,
                    "Official component extraction budget exceeded")
            roots = set()
            for member in members:
                relative = PurePosixPath(member.name)
                require(relative.parts and not relative.is_absolute() and ".." not in relative.parts
                        and "\\" not in member.name and not any(ord(c) < 32 for c in member.name),
                        "Unsafe official component path")
                roots.add(relative.parts[0])
            require(len(roots) == 1, "Single official component root required")
            handle.extractall(destination, filter="data")
        installer = destination / next(iter(roots)) / "install.sh"
        require(installer.is_file() and not installer.is_symlink(), "Official installer required")
        command = ["sh", str(installer), "--prefix=" + str(toolchain), "--sysconfdir=" + str(toolchain / "etc"),
                   "--docdir=" + str(toolchain / "share/doc/rust"), "--libdir=" + str(toolchain / "lib"),
                   "--bindir=" + str(toolchain / "bin"), "--mandir=" + str(toolchain / "share/man"), "--disable-ldconfig"]
        result = recorder.run("install-" + row["name"], command, destination)
        if result["exit_code"] != 0:
            return result["exit_code"] or 1
    for name, expected in rust["installed_binary_sha256"].items():
        require(sha256(toolchain / "bin" / name) == expected, "Installed pinned Rust binary mismatch")
    archive = output / Path(component["url"]).name
    bindings = clippy_binary_hashes(archive)
    for name, expected in bindings.items():
        require(sha256(toolchain / "bin" / name) == expected, "Installed Clippy binary differs from verified archive")
    report["toolchain"] = {"path": str(toolchain), "version": "1.95.0", "official_components_verified": True,
                           "global_installation": False, "clippy_binary_sha256": bindings,
                           "compiler_binary_sha256": rust["installed_binary_sha256"]}
    return 0


def prelaunch_health(output: Path, report: dict, label: str) -> None:
    row = {"label": label, "started_at_utc": utc(), "status": "RUNNING"}
    report.setdefault("prelaunch_health", []).append(row)
    path = output / "tmp" / ("owned-health-" + label)
    data = b"owned-same-step-health\n"
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        require(path.read_bytes() == data, "Owned temp health readback failed")
        path.unlink()
        row.update(status="PASS", bytes=len(data), write_fsync_read_delete=True,
                   scope="Only new owned tiny file; not capacity qualification")
    except Exception:
        row["status"] = "FAIL"
        raise
    finally:
        row["ended_at_utc"] = utc()
        write_json(output / "report.json", report)


def run_stage(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
              recorder: Recorder) -> int:
    require(args.prepared_dir and args.toolchain_dir and args.cargo_home, "Stage needs owned preparation/toolchain/cache")
    prepared = Path(args.prepared_dir).resolve(strict=True)
    prior = load(prepared / "report.json")
    require(prior["mode"] == "prepare" and prior["status"] == "PASS"
            and prior["manifest_sha256"] == report["manifest_sha256"]
            and prior["runner_sha256"] == report["runner_sha256"], "Matching actual prepared source required")
    source, tests = prepared / "source", prepared / "test-source"
    source_before = verify_prepared(source, manifest, "source")
    test_before = verify_prepared(tests, manifest, "normalized")
    toolchain = guarded_cache(args.toolchain_dir, ".rustup")
    cache = guarded_cache(args.cargo_home, ".cargo")
    bins = {name: toolchain / "bin" / name for name in ["rustc", "cargo", "rustdoc"]}
    for name, path in bins.items():
        require(path.is_file() and not path.is_symlink()
                and sha256(path) == manifest["rust"]["installed_binary_sha256"][name], "Pinned owned Rust binary required")
    component = manifest["rust"]["clippy_component"]
    archive = toolchain.parent / Path(component["url"]).name
    if not archive.is_file():
        raise MissingClippyTool("Official Clippy archive missing")
    for name, expected in clippy_binary_hashes(archive).items():
        path = toolchain / "bin" / name
        if not path.is_file():
            raise MissingClippyTool("Owned Clippy binary missing")
        require(not path.is_symlink() and sha256(path) == expected,
                "Official archive-bound Clippy binary required; missing tool is BLOCKED")
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
    task.update(CARGO_HOME=str(cache), RUSTUP_HOME=str(output / "rustup-home"), RUSTC=str(bins["rustc"]),
                RUSTDOC=str(bins["rustdoc"]), CARGO_TARGET_DIR=str(output / "target"), TMPDIR=str(output / "tmp"))
    environment.update(task)
    environment["PATH"] = str(toolchain / "bin") + os.pathsep + environment.get("PATH", os.defpath)
    report["task_environment"] = {**task, "PATH_PREPEND": str(toolchain / "bin"), "removed_override_keys": removed}
    for name in ["rustc", "cargo"]:
        row = recorder.run(name + "-version", [str(bins[name]), "--version", "--verbose"], tests, environment, task)
        require(row["exit_code"] == 0, "Version command failed")
        text = (recorder.receipts / (name + "-version") / "stdout.log").read_text()
        require(re.search(r"(?m)^release: 1\.95\.0$", text) is not None, "Rust1.95.0 required")
    result = 0
    try:
        if args.mode == "fetch":
            prelaunch_health(output, report, "fetch")
            row = recorder.run("cargo-fetch", [str(bins["cargo"]), "fetch", "--locked"], tests / "codex-rs", environment, task)
            result = positive_exit(row["exit_code"])
        else:
            report["tests"].update(status="RUNNING", scopes=[], selected_total_passed=0)
            for scope in manifest["test_selection"]["scopes"]:
                if scope["label"] == "step-settings7":
                    prelaunch_health(output, report, "ordinary-list")
                    argv = [str(bins["cargo"]), "test", "--locked", "--offline", "-p", "codex-core",
                            "--lib", scope["filter"], "--", "--list"]
                    row = recorder.run("ordinary-test-list", argv, tests / "codex-rs", environment, task)
                    listed = (recorder.receipts / "ordinary-test-list" / "stdout.log").read_text(errors="replace")
                    names = sorted(re.findall(r"(?m)^(\S+): test$", listed))
                    report["ordinary_test_list"] = {"actual_exit": row["exit_code"], "test_names": names,
                                                     "matches_fixed_source_candidates": names == scope["test_names"],
                                                     "scope": "Collection only; never behavior PASS"}
                    if row["exit_code"] != 0 or names != scope["test_names"]:
                        result = positive_exit(row["exit_code"]) or 1
                        break
                prelaunch_health(output, report, scope["label"])
                row = recorder.run("cargo-" + scope["label"], [str(bins["cargo"])] + scope["argv_tail"],
                                   tests / "codex-rs", environment, task)
                stdout = (recorder.receipts / ("cargo-" + scope["label"]) / "stdout.log").read_text(errors="replace")
                stderr = (recorder.receipts / ("cargo-" + scope["label"]) / "stderr.log").read_text(errors="replace")
                observed = test_summary(stdout, scope)
                compiled_zero = (observed["summary"] is None and not observed["actual_running_counts"]
                                 and "could not compile" in stderr)
                observed.update(label=scope["label"], package=scope["package"], actual_cargo_exit=row["exit_code"],
                                status="NOT_RUN" if compiled_zero else ("PASS" if row["exit_code"] == 0 and observed["selection_matches"] else "FAIL"),
                                compile_failed_before_tests=compiled_zero)
                report["tests"]["scopes"].append(observed)
                report["tests"]["tests_executed"] += sum(observed["actual_running_counts"])
                if observed["summary"]:
                    report["tests"]["selected_total_passed"] += observed["summary"]["passed"]
                write_json(output / "report.json", report)
                if row["exit_code"] != 0 or not observed["selection_matches"]:
                    result = positive_exit(row["exit_code"]) or 1
                    break
            report["tests"]["status"] = "PASS" if result == 0 and report["tests"]["selected_total_passed"] == 48 else "FAIL"
            if report["tests"]["status"] == "PASS":
                prelaunch_health(output, report, "clippy")
                row = recorder.run("cargo-clippy", [str(bins["cargo"])] + CLIPPY_ARGV,
                                   tests / "codex-rs", environment, task)
                result = positive_exit(row["exit_code"])
                report["clippy"] = {"status": "PASS" if result == 0 else "FAIL", "actual_cargo_exit": row["exit_code"],
                                     "scope": "Only selected two packages library/tests, existing workspace rules, no -D warnings"}
            else:
                result = result or 1
                report["clippy"].update(reason="Prior actual test/compile/selection failure; no fallback or retry")
    finally:
        source_after = verify_prepared(source, manifest, "source")
        test_after = verify_prepared(tests, manifest, "normalized")
        require(source_before == source_after and test_before == test_after, "Source changed during Cargo")
        write_json(output / "source-after-files.json", source_after)
        write_json(output / "test-after-files.json", test_after)
        report["source_before_after_exact"] = True
    return result


def positive_exit(code: int | None) -> int:
    if type(code) is int and code == 0:
        return 0
    return code if type(code) is int and code > 0 else 1


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
              "manifest_sha256": sha256(bundle / "same-step-resolution-source.json"), "runner_sha256": sha256(Path(__file__)),
              "commands": [], "tests": {"status": "NOT_RUN", "tests_executed": 0},
              "clippy": {"status": "NOT_RUN", "actual_cargo_exit": None}, "production": "NOT_ADMITTED",
              "not_run": ["foreign17", "fullcore/API/HTTP/guardian/platform suites", "Windows", "Codex CLI/AppServer/models/send"]}
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
    except MissingClippyTool as error:
        result = 1
        report.update(status="BLOCKED", error_type=type(error).__name__, error="Required owned Clippy tool missing; no Cargo test started")
        report["clippy"].update(status="NOT_RUN", reason="BLOCKED: required owned Clippy tool missing")
    except Exception as error:
        result = 1
        report.update(status="FAIL", error_type=type(error).__name__, error="Stage failed; retained receipts identify the actual command")
    finally:
        os.umask(previous_umask)
    report.update(ended_at_utc=utc(), actual_exit=result)
    write_json(output / "report.json", report)
    print(json.dumps({"mode": args.mode, "status": report["status"], "actual_exit": result,
                      "tests": report["tests"], "clippy": report["clippy"], "production": "NOT_ADMITTED",
                      "report": str(output / "report.json")}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
