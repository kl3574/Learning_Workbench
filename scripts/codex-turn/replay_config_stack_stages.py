#!/usr/bin/env python3
"""Diagnose one actual Config152 stack failure in a separate remote CI scope.

The exact tools/profile and original gate remain unchanged. One test function
adds only declared stderr stage markers. Two explicit single-case trials and a
conditional original36 scope cannot prove cause, Config152, production admission,
or a native InputProof. No stack override, boxing experiment, or repair.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

MANIFEST_FILE = "config-stack-stages-source.json"
MANIFEST_BYTES = 8357
MANIFEST_SHA = "4d157b31c14d515ed619594ad255781307f98afaf37ac3d808f1e64f013730d8"
CASE = "tools::executed_tool_calls::request_metadata::tests::recorder_refreshes_without_changing_execution_features_or_claiming_missing_history"
GROUP = "tools::executed_tool_calls::request_metadata::tests::"
BRANCH = "fix/M6.3-config-stack-stages"
PARENT_PATH = "scripts/codex-turn/replay_frozen_config_materialization.py"
PARENT_MANIFEST = "scripts/codex-turn/frozen-config-materialization-source.json"
ASSET_PATHS = {
    PARENT_PATH, PARENT_MANIFEST,
    "scripts/codex-turn/frozen-config-materialization.patch",
    "scripts/codex-turn/frozen-config-materialization-README.md",
    ".github/workflows/frozen-config-materialization.yml",
    "scripts/codex-turn/replay_http_gate.py",
    "scripts/codex-turn/replay_core_producer.py",
}
FIELDS = {
    "schema_version", "status", "branch", "failure_anchor", "parent_assets",
    "spec", "source", "prepared_graph", "lock_sha256", "test_metadata", "profile",
    "single_case", "conditional_group", "limits", "production_boundary",
    "v1_assets", "minimal_red_anchor", "instrumentation", "instrumented_graph",
}

V1_ASSETS = {'.github/workflows/config-stack-diagnosis.yml': {'bytes': 7304,
                                                  'sha256': 'e8b34c585d9b00fb4448d7716bc924410a653dfa936513e0d017eee3aa31e6e6'},
 'scripts/codex-turn/CONFIG_STACK_DIAGNOSIS.md': {'bytes': 2257,
                                                  'sha256': '267aacfa0aeca945b9ea6c2ceb332b7a8898c1cebfd3b7762edb1681d0bba2e3'},
 'scripts/codex-turn/config-stack-diagnosis-source.json': {'bytes': 5269,
                                                           'sha256': '2397784a2f2d8501d2fb3542b6bb6c1132b7a578a3070333c9cf683c4394c197'},
 'scripts/codex-turn/replay_config_stack_diagnosis.py': {'bytes': 21314,
                                                         'sha256': '4a428a90e547c1c092ded4298bab3186c94b1898c700b7d15956cd164390784c'}}
MINIMAL_RED_ANCHOR = {'attempt': 1,
 'case': 'tools::executed_tool_calls::request_metadata::tests::recorder_refreshes_without_changing_execution_features_or_claiming_missing_history',
 'cause': 'UNDETERMINED',
 'collection_exit': 0,
 'each_cargo_exit': 101,
 'each_complete_footer': False,
 'each_individual_ok_count': 0,
 'each_running_count': 1,
 'exact_collection_count': 1,
 'head': 'e62044e40f45126fd9de73b9a92c30d3ba6d15d3',
 'job_id': 114156691390,
 'report_sha256': '4d182741c5028bc098c0908d22932f0f874924078c7c525f6be3569501db2245',
 'run_id': 38032670192,
 'status': 'RED_REPRODUCED',
 'trials': 2}
INSTRUMENTATION = {'after': {'bytes': 87279,
           'kind': 'file',
           'mode': 436,
           'sha256': '2f867a7f1b9eb4adb6630d4fe1ab8d05c2f4e63b9cc7b4ae38ee09b9fa2b9b7a'},
 'before': {'bytes': 85527,
            'kind': 'file',
            'mode': 436,
            'sha256': 'efbcb4dd389b66a8b4f04919163519955bc4c0a47f0e3aac043cf9561880e1f1'},
 'marker_prefix': 'LW_STACK_STAGE_V1',
 'marker_statement_count': 16,
 'original_assertions_and_data_exact': True,
 'patch': {'bytes': 4538,
           'file': 'config-stack-stages.patch',
           'sha256': 'ef783cce1597e269a722769001e427c9a642d93330eb437b802b6e66a0de8f8a'},
 'path': 'codex-rs/core/src/tools/executed_tool_calls/request_metadata_tests.rs',
 'scope': 'Diagnostic test instrumentation only; no production repair',
 'stage_names': ['entry',
                 'fixture.before',
                 'fixture.after',
                 'refresh.before',
                 'refresh.after',
                 'reload.before',
                 'reload.after',
                 'metadata.before',
                 'metadata.direct.after',
                 'metadata.nested.before',
                 'repeat_refresh.before',
                 'repeat_refresh.after',
                 'attach_prompt.before',
                 'attach_prompt.after',
                 'metadata.after',
                 'exit']}
INSTRUMENTED_GRAPH = {'normalized': {'rows': 8797,
                'sha256': '51c0aa735f2e59b163c09142130db5551f264e481cd6000fcad55160343f7fa2'},
 'source': {'rows': 8797,
            'sha256': 'a88b1c8079e36d6b1cb01e8a23970562034e97982d38bd95cea5bb010c64a76d'}}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_object(pairs: list) -> dict:
    value = {}
    for key, item in pairs:
        require(key not in value, "Duplicate JSON member")
        value[key] = item
    return value


def load(path: Path) -> dict:
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def checked_file(path: Path, expected: dict) -> None:
    require(type(expected) is dict and set(expected) == {"bytes", "sha256"}
            and type(expected["bytes"]) is int and expected["bytes"] > 0
            and type(expected["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]) is not None,
            "Closed file pin required")
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size == expected["bytes"]
            and sha256(path) == expected["sha256"], "Byte-exact parent asset required")


def verify_inputs(bundle: Path) -> tuple:
    path = bundle / MANIFEST_FILE
    checked_file(path, {"bytes": MANIFEST_BYTES, "sha256": MANIFEST_SHA})
    contract = load(path)
    require(type(contract) is dict and set(contract) == FIELDS
            and type(contract["schema_version"]) is int and contract["schema_version"] == 1
            and contract["status"] == "STAGE_DIAGNOSIS_CANDIDATE_NOT_RUN"
            and contract["branch"] == BRANCH, "Closed diagnostic contract required")
    require(os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("GITHUB_EVENT_NAME") in {"push", "workflow_dispatch"}
            and re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", "")) is not None,
            "Only the independent diagnostic CI ref is permitted")
    require("RUST_MIN_STACK" not in os.environ, "No inherited stack override permitted")
    anchor = contract["failure_anchor"]
    require(type(anchor) is dict and set(anchor) == {
                "head", "run_id", "job_id", "attempt", "scope", "actual_cargo_exit",
                "complete_footer", "actual_running_count", "individual_ok_lines",
                "prior_complete_scopes_passed", "stderr_sha256",
            } and anchor["head"] == "10ccea200815ba15448d07253f0ed6fc58f9e30c"
            and all(type(anchor[key]) is int for key in [
                "run_id", "job_id", "attempt", "actual_cargo_exit", "actual_running_count",
                "individual_ok_lines", "prior_complete_scopes_passed",
            ]) and anchor["run_id"] == 38030198967 and anchor["job_id"] == 114149335638
            and anchor["attempt"] == 1 and anchor["scope"] == "executed-metadata36"
            and anchor["actual_cargo_exit"] == 101 and anchor["complete_footer"] is False
            and anchor["actual_running_count"] == 36 and anchor["individual_ok_lines"] == 24
            and anchor["prior_complete_scopes_passed"] == 85
            and anchor["stderr_sha256"] == "33c928efc5e53240544ef1866e2e088b5e3e30b7862eca1bf3a3286ebf5b68c1",
            "Exact incomplete original36 failure evidence required")
    conditional = contract["conditional_group"]
    require(type(conditional) is dict and set(conditional) == {
                "parent_scope_label", "selector", "expected_nonzero_count", "condition", "trials",
            } and conditional["parent_scope_label"] == "executed-metadata36"
            and conditional["selector"] == GROUP
            and type(conditional["expected_nonzero_count"]) is int
            and conditional["expected_nonzero_count"] == 36
            and type(conditional["trials"]) is int and conditional["trials"] == 1
            and conditional["condition"] == (
                "Both exact single-case trials completed without matching the actual stack-overflow signature"
            ), "Fixed conditional original36 diagnostic required")
    assets = contract["parent_assets"]
    require(type(assets) is dict and set(assets) == ASSET_PATHS,
            "Exact seven parent assets required")
    repo = bundle.parents[1]
    for name, pin in assets.items():
        checked_file(repo / name, pin)
    require(contract["v1_assets"] == V1_ASSETS, "Exact immutable diagnostic v1 assets required")
    for name, pin in contract["v1_assets"].items():
        checked_file(repo / name, pin)
    red = contract["minimal_red_anchor"]
    require(red == MINIMAL_RED_ANCHOR
            and all(type(red[key]) is int for key in [
                "run_id", "job_id", "attempt", "exact_collection_count", "collection_exit",
                "trials", "each_running_count", "each_cargo_exit", "each_individual_ok_count",
            ]) and red["each_complete_footer"] is False,
            "Both exact original single-case RED trials must remain historical evidence")
    addition = contract["instrumentation"]
    require(addition == INSTRUMENTATION
            and type(addition["marker_statement_count"]) is int
            and addition["original_assertions_and_data_exact"] is True,
            "Closed stage-only SDK test instrumentation required")
    patch = addition["patch"]
    checked_file(bundle / patch["file"], {"bytes": patch["bytes"], "sha256": patch["sha256"]})
    require(contract["instrumented_graph"] == INSTRUMENTED_GRAPH
            and all(type(row["rows"]) is int and row["rows"] == 8797
                    and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
                    for row in contract["instrumented_graph"].values()),
            "Exact stage-instrumented full graphs required")
    # Both imported replay helpers have been pinned before any parent code loads.
    spec = importlib.util.spec_from_file_location("_config_stack_parent", repo / PARENT_PATH)
    require(spec is not None and spec.loader is not None, "Exact parent module required")
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    manifest = parent.verify_inputs(bundle)
    addition = manifest["frozen_config_materialization"]
    require(contract["spec"] == manifest["spec"]
            and contract["source"] == manifest["source"]
            and contract["prepared_graph"] == manifest["complete_source_graph"]
            and contract["lock_sha256"] == manifest["lock_sha256"]
            and contract["test_metadata"] == manifest["test_metadata"]
            and contract["profile"] == manifest["profile"]
            and addition["patch_asset_number"] == 14
            and addition["selected_application_number"] == 11,
            "Original Config152 source/profile/lock contract required")
    single = contract["single_case"]
    require(type(single) is dict and set(single) == {
                "name", "package", "expected_nonzero_count", "list_argv_tail",
                "run_argv_tail", "trials",
            } and single["name"] == CASE and single["package"] == "codex-core"
            and type(single["expected_nonzero_count"]) is int
            and single["expected_nonzero_count"] == 1
            and type(single["trials"]) is int and single["trials"] == 2
            and single["list_argv_tail"] == [
                "test", "--locked", "--offline", "-p", "codex-core",
                "--lib", CASE, "--", "--exact", "--list",
            ] and single["run_argv_tail"] == [
                "test", "--locked", "--offline", "-p", "codex-core",
                "--lib", CASE, "--", "--exact", "--nocapture",
            ], "Exact nonzero single case and two explicit trials required")
    scopes = [scope for scope in manifest["test_selection"]["scopes"]
              if scope["label"] == "executed-metadata36"]
    require(len(scopes) == 1, "Original36 scope required")
    group = scopes[0]
    require(group["package"] == "codex-core" and group["filter"] == GROUP
            and group["expected_passed"] == 36
            and len(group["test_names"]) == len(set(group["test_names"])) == 36
            and CASE in group["test_names"]
            and group["argv_tail"] == [
                "test", "--locked", "--offline", "-p", "codex-core",
                "--lib", GROUP, "--", "--nocapture",
            ], "Original finite36 names and argv required")
    require(contract["limits"] == {
                "changes_to_SDK_source": True,
                "SDK_source_change_scope": "Exactly one existing test function gains stderr stage markers",
                "changes_to_diagnostic_v1_assets": False,
                "changes_to_original_assertions_or_data": False,
                "changes_to_original_test_assets_or_selection_manifest": False,
                "changes_to_build_profile": False, "RUST_MIN_STACK_override": False,
                "full152_gate": "NOT_RUN", "clippy": "NOT_RUN",
                "baseline3b_comparison": "NOT_INCLUDED",
            } and contract["production_boundary"] == {
                "registration": False, "default_executor": None,
                "complete_InputProof": "NOT_ESTABLISHED", "status": "NOT_ADMITTED",
            }, "Diagnostics cannot repair or admit production")
    return contract, parent, manifest, group


def observe(parent, recorder, label: str, row: dict, scope: dict) -> dict:
    stdout = (recorder.receipts / label / "stdout.log").read_text(errors="replace")
    stderr = (recorder.receipts / label / "stderr.log").read_text(errors="replace")
    observed = parent.test_summary(stdout, scope)
    overflowed = re.findall(
        r"(?m)^thread '([^']+)' (?:\([0-9]+\) )?has overflowed its stack$", stderr,
    )
    red = (row["exit_code"] != 0 and observed["actual_running_counts"] == [scope["expected_passed"]]
           and CASE in overflowed and "fatal runtime error: stack overflow, aborting" in stderr)
    compile_failed = (not observed["actual_running_counts"] and "could not compile" in stderr)
    observed.update(
        label=label, actual_cargo_exit=row["exit_code"], stack_overflow_reproduced=red,
        stack_overflow_test_names=overflowed,
        actual_complete_footer=observed["summary"] is not None,
        actual_individual_ok_count=len(observed["actual_passed_test_names"]),
        status=("RED" if red else "NOT_RUN" if compile_failed else "PASS"
                if row["exit_code"] == 0 and observed["selection_matches"] else "FAIL"),
    )
    stage_lines = re.findall(r"(?m)^LW_STACK_STAGE_V1 .*$", stderr)
    stages = []
    malformed = []
    for line in stage_lines:
        match = re.fullmatch(
            r"LW_STACK_STAGE_V1 stage=([a-z_.]+)(?: iteration=([0-3]) enabled=(false|true))?",
            line,
        )
        if match is None:
            malformed.append(line)
            continue
        stage, iteration, enabled = match.groups()
        bare = stage in {"entry", "fixture.before", "fixture.after", "exit"}
        if (stage not in INSTRUMENTATION["stage_names"]
                or bare != (iteration is None)
                or (iteration is not None
                    and enabled != ["false", "true", "false", "true"][int(iteration)])):
            malformed.append(line)
            continue
        stages.append({"stage": stage, "iteration": None if iteration is None else int(iteration),
                       "enabled": None if enabled is None else enabled == "true"})
    expected = [{"stage": name, "iteration": None, "enabled": None}
                for name in ["entry", "fixture.before", "fixture.after"]]
    for index, enabled in enumerate([False, True, False, True]):
        names = ["refresh.before", "refresh.after", "reload.before", "reload.after",
                 "metadata.before", "metadata.direct.after", "metadata.nested.before"]
        if enabled:
            names.extend(["repeat_refresh.before", "repeat_refresh.after"])
        names.extend(["attach_prompt.before", "attach_prompt.after", "metadata.after"])
        expected.extend({"stage": name, "iteration": index, "enabled": enabled} for name in names)
    expected.append({"stage": "exit", "iteration": None, "enabled": None})
    prefix_matches = stages == expected[:len(stages)]
    complete_trace = stages == expected
    observed.update(
        stage_trace_expected_count=len(expected),
        actual_stage_marker_count=len(stages),
        actual_stage_order_matches_prefix=prefix_matches,
        actual_stage_trace_complete=complete_trace,
    )
    observed.update(
        actual_stage_markers=stages, malformed_stage_lines=malformed,
        actual_last_stage_marker=stages[-1] if stages else None,
        interpretation="Observed execution boundaries only; marker insertion can perturb frame layout",
        cause="UNDETERMINED",
    )
    if malformed or not prefix_matches or (observed["status"] == "PASS" and not complete_trace):
        observed["status"] = "FAIL"
    return observed


def collect(parent, recorder, label: str, argv: list[str], expected: list[str],
            cwd: Path, environment: dict, task: dict, output: Path, report: dict) -> bool:
    parent.prelaunch_health(output, report, label)
    row = recorder.run(label, argv, cwd, environment, task)
    text = (recorder.receipts / label / "stdout.log").read_text(errors="replace")
    names = sorted(re.findall(r"(?m)^(\S+): test$", text))
    matches = (bool(expected) and names == sorted(expected)
               and len(names) == len(set(names)) == len(expected))
    report.setdefault("collections", []).append({
        "label": label, "actual_cargo_exit": row["exit_code"],
        "actual_names": names, "expected_nonzero_count": len(expected),
        "selection_matches": matches, "scope": "Collection only; never behavior PASS",
    })
    parent.write_json(output / "report.json", report)
    return row["exit_code"] == 0 and matches


def instrumented_target_names(data: bytes, original: bytes) -> list[str]:
    text = data.decode("utf-8")
    stripped, marker_count = re.subn(
        r'(?m)^([ \t]*)eprintln!\(\n\1    "LW_STACK_STAGE_V1 stage=[^"\n]+"\n\1\);\n',
        "", text,
    )
    require(marker_count == INSTRUMENTATION["marker_statement_count"]
            and stripped.encode("utf-8") == original,
            "Only the declared 16 stderr statements may alter original test bytes")
    names = re.findall(r"#\[(?:test|tokio::test)\]\s+(?:async )?fn (\w+)\(", text)
    require(len(names) == len(set(names)) == 36 and "#[test_case" not in text,
            "Independent instrumented target declaration names required")
    return sorted(GROUP + name for name in names)


def instrument_sources(parent, source: Path, tests: Path, output: Path, contract: dict,
                       manifest: dict, recorder, report: dict) -> tuple:
    addition = contract["instrumentation"]
    path = addition["path"]
    stage_manifest = {**manifest, "complete_source_graph": contract["instrumented_graph"]}
    # Run all inherited original-byte guards before any diagnostic source change.
    parent.verify_prepared(tests, manifest, "normalized")
    expected_original = [
        scope["test_names"] for scope in manifest["test_selection"]["scopes"][:11]
    ]
    expected_auth = [
        scope["test_names"]
        for scope in manifest["effective_static_auth"]["test_selection"]["scopes"]
    ]
    expected_config = [
        scope["test_names"]
        for scope in manifest["frozen_config_materialization"]["test_selection"]["scopes"]
    ]
    original_names = parent.source_test_names(tests)
    auth_names = parent.static_auth_source_names(tests)
    config_names = parent.frozen_config_source_names(tests)
    require(original_names == expected_original, "Original135 test declaration names changed")
    require(auth_names == expected_auth, "Original auth13 test declaration names changed")
    require(config_names == expected_config, "Original Config4 test declaration names changed")
    target_indices = [
        index for index, names in enumerate(expected_original) if CASE in names
    ]
    require(len(target_indices) == 1
            and len(expected_original[target_indices[0]]) == 36,
            "Unique original36 target declaration scope required")
    target_index = target_indices[0]
    report["original_declaration_checks_before_overlay"] = {
        "original135": original_names, "auth13": auth_names, "Config4": config_names,
        "inherited_original_source_guards": "PASS",
    }
    parent.write_json(output / "report.json", report)
    applications = []
    snapshots = {}
    target_declarations = {}
    for phase, label, root in [("source", "source", source), ("normalized", "test", tests)]:
        before = parent.verify_prepared(root, manifest, phase)
        require(before.get(path) == addition["before"], "Exact uninstrumented target required")
        target_before = (root / path).read_bytes()
        parent.write_json(output / (label + "-uninstrumented-files.json"), before)
        for suffix, flags in [("check", ["--check"]), ("apply", [])]:
            row = recorder.run("stage-markers-" + label + "-" + suffix,
                               ["git", "apply", *flags,
                                str(Path(__file__).resolve().parent / addition["patch"]["file"])], root)
            require(row["exit_code"] == 0, "Stage-only diagnostic patch failed")
        after = parent.verify_prepared(root, stage_manifest, phase)
        require(parent.differences(before, after) == [path]
                and after[path] == addition["after"],
                "Diagnostic instrumentation exceeded its sole test path")
        names = instrumented_target_names((root / path).read_bytes(), target_before)
        require(names == expected_original[target_index],
                "Instrumented original36 test declaration names changed")
        target_declarations[phase] = names
        parent.write_json(output / (label + "-before-files.json"), after)
        applications.append({"phase": phase, "changed_paths": [path],
                             "before_graph": contract["prepared_graph"][phase],
                             "after_graph": contract["instrumented_graph"][phase],
                             "exact_source_change": True})
        snapshots[phase] = after
    # All other source rows are exact. Only the independently parsed target row
    # replaces its saved original declaration group; inherited guards stay intact.
    after_original = list(original_names)
    after_original[target_index] = target_declarations["normalized"]
    require(after_original == expected_original,
            "Original135 declarations must survive diagnostic instrumentation")
    report["diagnostic_instrumentation"] = {
        "scope": addition["scope"], "applications": applications,
        "original_assertions_and_data_exact": True,
        "declaration_names_unchanged": True, "SDK_source_changed": True,
        "independent_target36_names": target_declarations,
        "after_original135": after_original,
        "unchanged_auth13": auth_names, "unchanged_Config4": config_names,
        "names_preservation_basis": "Independent target36 parse and all other source rows exact",
        "inherited_original_guards_run_before_overlay": True,
        "stripping_declared_markers_restores_each_original_target": True,
        "cause": "UNDETERMINED", "production": "NOT_ADMITTED",
    }
    parent.write_json(output / "report.json", report)
    return snapshots["source"], snapshots["normalized"], stage_manifest


def diagnose(args, output: Path, report: dict, contract: dict, parent, manifest: dict,
             group: dict, recorder) -> int:
    prepared = Path(args.prepared_dir).resolve(strict=True)
    prior = parent.load(prepared / "report.json")
    bindings = contract["parent_assets"]
    require(prior["mode"] == "prepare" and prior["status"] == "PASS"
            and prior["manifest_sha256"] == bindings[PARENT_MANIFEST]["sha256"]
            and prior["runner_sha256"] == bindings[PARENT_PATH]["sha256"],
            "Actual matching prepare-only source required")
    fetched = parent.load(Path(args.fetch_dir).resolve(strict=True) / "report.json")
    require(fetched["mode"] == "fetch" and fetched["status"] == "PASS"
            and fetched["manifest_sha256"] == bindings[PARENT_MANIFEST]["sha256"]
            and fetched["runner_sha256"] == bindings[PARENT_PATH]["sha256"]
            and fetched.get("source_before_after_exact") is True,
            "Actual same-source locked dependency fetch required")
    source, tests = prepared / "source", prepared / "test-source"
    source_before, test_before, stage_manifest = instrument_sources(
        parent, source, tests, output, contract, manifest, recorder, report,
    )
    try:
        toolchain = parent.guarded_cache(args.toolchain_dir, ".rustup")
        cache = parent.guarded_cache(args.cargo_home, ".cargo")
        bins = {name: toolchain / "bin" / name for name in ["rustc", "cargo", "rustdoc"]}
        for name, path in bins.items():
            require(path.is_file() and not path.is_symlink()
                    and parent.sha256(path) == manifest["rust"]["installed_binary_sha256"][name],
                    "Pinned owned Rust binary required")
        component = manifest["rust"]["clippy_component"]
        archive = toolchain.parent / Path(component["url"]).name
        require(archive.is_file(), "Exact provisioned Clippy archive required")
        for name, expected in parent.clippy_binary_hashes(archive).items():
            require((toolchain / "bin" / name).is_file()
                    and not (toolchain / "bin" / name).is_symlink()
                    and parent.sha256(toolchain / "bin" / name) == expected,
                    "Original provisioned Clippy component required")
        environment = os.environ.copy()
        removed = [key for key in list(environment) if key.startswith("CARGO_PROFILE_") or key in {
            "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER",
            "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTC_WRAPPER",
            "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER", "CARGO_INCREMENTAL",
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
        report["task_environment"] = {
            **task, "PATH_PREPEND": str(toolchain / "bin"), "removed_override_keys": removed,
        }
        for name in ["rustc", "cargo"]:
            row = recorder.run(name + "-version", [str(bins[name]), "--version", "--verbose"],
                               tests, environment, task)
            require(row["exit_code"] == 0, "Version command failed")
            text = (recorder.receipts / (name + "-version") / "stdout.log").read_text()
            require(re.search(r"(?m)^release: 1\.95\.0$", text) is not None, "Rust1.95 required")
        cwd = tests / "codex-rs"
        single = {"expected_passed": 1, "test_names": [CASE]}
        if not collect(parent, recorder, "stack-single-list",
                       [str(bins["cargo"])] + contract["single_case"]["list_argv_tail"],
                       [CASE], cwd, environment, task, output, report):
            report["diagnosis_status"] = "COLLECTION_FAILED"
            return 1
        for trial in [1, 2]:
            label = "cargo-stack-single-" + str(trial)
            parent.prelaunch_health(output, report, label)
            row = recorder.run(label,
                               [str(bins["cargo"])] + contract["single_case"]["run_argv_tail"],
                               cwd, environment, task)
            report["behavior_trials"].append(observe(parent, recorder, label, row, single))
            parent.write_json(output / "report.json", report)
        singles = report["behavior_trials"]
        if any(row["stack_overflow_reproduced"] for row in singles):
            report["conditional_group"].update(status="NOT_RUN", reason="Single-case RED observed")
        else:
            group_list = ["test", "--locked", "--offline", "-p", "codex-core",
                          "--lib", GROUP, "--", "--list"]
            if not collect(parent, recorder, "stack-original36-list",
                           [str(bins["cargo"])] + group_list, group["test_names"],
                           cwd, environment, task, output, report):
                report["conditional_group"].update(status="COLLECTION_FAILED")
                report["diagnosis_status"] = "COLLECTION_FAILED"
                return 1
            label = "cargo-stack-original36"
            parent.prelaunch_health(output, report, label)
            row = recorder.run(label, [str(bins["cargo"])] + group["argv_tail"],
                               cwd, environment, task)
            observed = observe(parent, recorder, label, row, group)
            report["behavior_trials"].append(observed)
            report["conditional_group"].update(status=observed["status"], executed=True)
        rows = report["behavior_trials"]
        if any(row["stack_overflow_reproduced"] for row in rows):
            report["diagnosis_status"] = "RED_REPRODUCED"
            return 1
        if all(row["status"] == "PASS" for row in rows):
            report["diagnosis_status"] = "NO_RED_WITH_STAGE_MARKERS_IN_DECLARED_SCOPE"
            return 0
        report["diagnosis_status"] = "NON_STACK_FAILURE"
        return 1
    finally:
        source_after = parent.verify_prepared(source, stage_manifest, "source")
        test_after = parent.verify_prepared(tests, stage_manifest, "normalized")
        require(source_before == source_after and test_before == test_after,
                "Diagnostic Cargo changed source")
        parent.write_json(output / "source-after-files.json", source_after)
        parent.write_json(output / "test-after-files.json", test_after)
        report["source_before_after_exact"] = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["verify", "diagnose"], required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prepared-dir")
    parser.add_argument("--fetch-dir")
    parser.add_argument("--toolchain-dir")
    parser.add_argument("--cargo-home")
    args = parser.parse_args()
    output = Path(args.output_dir).absolute()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    bundle = Path(__file__).resolve().parent
    report = {
        "schema_version": 1, "mode": args.mode, "status": "RUNNING",
        "commands": [], "behavior_trials": [], "collections": [],
        "diagnosis_status": "NOT_RUN",
        "conditional_group": {"status": "NOT_RUN", "executed": False},
        "full152_gate": "NOT_RUN", "clippy": "NOT_RUN", "production": "NOT_ADMITTED",
        "manifest_sha256": sha256(bundle / MANIFEST_FILE), "runner_sha256": sha256(Path(__file__)),
        "ci_context": {key: os.environ[key] for key in [
            "GITHUB_SHA", "GITHUB_REF", "GITHUB_EVENT_NAME", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
        ] if key in os.environ},
    }
    parent = None
    result = 1
    previous_umask = os.umask(0o002)
    try:
        contract, parent, manifest, group = verify_inputs(bundle)
        report.update(started_at_utc=parent.utc(), failure_anchor=contract["failure_anchor"],
                      minimal_red_anchor=contract["minimal_red_anchor"],
                      declared_instrumentation=contract["instrumentation"], cause="UNDETERMINED")
        parent.write_json(output / "report.json", report)
        if args.mode == "verify":
            report["diagnosis_status"] = "INPUTS_VERIFIED_ONLY"
            result = 0
        else:
            require(all([args.prepared_dir, args.fetch_dir, args.toolchain_dir, args.cargo_home]),
                    "Diagnostic stage needs exact prepared/fetched/toolchain/cache inputs")
            recorder = parent.Recorder(output, report)
            result = diagnose(args, output, report, contract, parent, manifest, group, recorder)
        verify_inputs(bundle)
        report["status"] = "PASS" if result == 0 else "FAIL"
    except KeyboardInterrupt:
        result = 130
        report.update(status="INTERRUPTED", stage_error="Interrupted; no automatic retry")
    except Exception as error:
        result = 1
        report.update(status="FAIL", stage_error_type=type(error).__name__,
                      stage_error="Stage failed; retained receipts preserve actual observations")
    finally:
        os.umask(previous_umask)
        report["actual_exit"] = result
        if parent is not None:
            report["ended_at_utc"] = parent.utc()
            parent.write_json(output / "report.json", report)
        else:
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "mode": args.mode, "status": report["status"], "actual_exit": result,
        "diagnosis_status": report["diagnosis_status"],
        "full152_gate": "NOT_RUN", "production": "NOT_ADMITTED",
    }))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
