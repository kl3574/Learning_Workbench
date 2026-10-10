#!/usr/bin/env python3
"""Replay the fifteenth patch asset / twelfth selected native owner application with independent original135/auth13/Config4/owner23 counts.

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
    "direct_lifetime_checkpoint", "executed_sampling_binding", "test_selection", "profile", "source_binding", "clippy", "clippy_repair", "sampling_preparation", "instruction_materials", "executed_state_checkpoint", "executed_regressions", "production_boundary", "licensing",
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
SAMPLING_PREPARATION = {'patch_file': 'retained-sampling-preparation-after-clippy.patch',
 'patch_sha256': '56f191d4a15da152e2642c61ac8ad1052738704c79fec978922942e781a04e64',
 'before_graph': {'rows': 8789,
                  'sha256': 'ffb3d1f75047df58a15a6aa15425967cdc7d976b5022319567bb50a8d3763ef5'},
 'changed_files': [{'path': 'codex-rs/core/src/session/mod.rs',
                    'before_sha256': 'e1854f77b62ca09dddf85c54aac95486835a6777303a736b00919e780d296717',
                    'after_sha256': 'bb707b8fa373d2610b45332a5746f4faeb471e05ab43946fd143a57dc248a7ff',
                    'after_bytes': 210632,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/turn.rs',
                    'before_sha256': '8c27407110003a384cc7a9f85985d83ff824378f1feb22e7e5c19d927d77ca1d',
                    'after_sha256': 'cf864e39583fead77612fcf8312606d5d8ed5879f2c3c62d19adc9f2227daa52',
                    'after_bytes': 125898,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_outbound_snapshot_tests.rs',
                    'before_sha256': '51bd3c4d439d83d9d3450a9635a6ab6b9102cd44b5fe2f430eaaef7edca6adf5',
                    'after_sha256': 'aa8f9977b12921bcf72c392bf5979eab06809bdbbd733e43f7b1dbc76d83f13b',
                    'after_bytes': 38117,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_sampling_preparation.rs',
                    'before_sha256': None,
                    'after_sha256': 'cafa07813e8abdb3eb3d266505fa5d3e7b693f3919957438284d45583510bf15',
                    'after_bytes': 8749,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_sampling_preparation_tests.rs',
                    'before_sha256': None,
                    'after_sha256': '2c07dcb01654f9db5b20d2fa7fd8ca08d569a9b5e39cbe3b4e33a5c52d57d578',
                    'after_bytes': 13489,
                    'after_mode': 436}],
 'frozen_source_pins_sha256': '009eedf465bfa776fd1f293d8faec58864131f7b2608150774f814e100cd87e0',
 'frozen_manifest_sha256': '801f552f6865cd0d7b4d5a1c5651b97cf2a58ccc9625af8432e7967f5c235cdf',
 'original_patch_sha256': '89aab184712b6d6fa6349fc665c6cef52c6d3d05bd0d76d930fc031b69b3a77f',
 'status': 'RAM candidate; true58 and Clippy NOT_RUN; no production admission'}
INSTRUCTION_MATERIALS = {'patch_file': 'retained-instruction-materials.patch',
 'patch_sha256': '098953da16ebf403c3b31d0feb19a831b3bf80810131d194ec50fdb3d6702e12',
 'before_graph': {'rows': 8791,
                  'sha256': '4d9ed864538e8084352cc7360b76b29d0b7b8ee75927125c797da7c2c90a7039'},
 'changed_files': [{'path': 'codex-rs/core/src/agents_md_checkpoint_tests.rs',
                    'before_sha256': None,
                    'after_sha256': '7b89e14b4cc72324a37a36068d616ba09327eee44cd2cce095717656d7763120',
                    'after_bytes': 3827,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/agents_md_manager.rs',
                    'before_sha256': '6e15ec972549b0dbdc3b64b40e04b8e88e7e28a01a9d355e17b083cecf2d59b7',
                    'after_sha256': '9ff588575991ce4fb2cc6d86b689c1ae0b6913d8a86a169e6b320b037aff2a49',
                    'after_bytes': 10315,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/environment.rs',
                    'before_sha256': '78466f34d58934ce2932934b6a77368f9c30a46e2703f2b94179b12afdcb1017',
                    'after_sha256': '026aa82c73f1c7a396b567fc01aeaaf24495d28677c3703fbce95b9cebd2d0ab',
                    'after_bytes': 15232,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/mcp.rs',
                    'before_sha256': '672284362e5693709ee4787d0e04efa5cdd78ae3dcebe1743d4dddd82530220a',
                    'after_sha256': 'f65ce83083b57c1098e8de081e51067b201a03e35dc5df91cd2f66ff8baad1a7',
                    'after_bytes': 49794,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/mod.rs',
                    'before_sha256': 'bb707b8fa373d2610b45332a5746f4faeb471e05ab43946fd143a57dc248a7ff',
                    'after_sha256': '16d2651bf5b68d10f0bdafb95b364080f22ee5c070e7a77a011f145c9c7d43a4',
                    'after_bytes': 211740,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_outbound_snapshot_tests.rs',
                    'before_sha256': 'aa8f9977b12921bcf72c392bf5979eab06809bdbbd733e43f7b1dbc76d83f13b',
                    'after_sha256': 'd92fb31e8621ede989af30e2fb12a00fb808b96edab2c2d3b24c8d3553b476c5',
                    'after_bytes': 38284,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_sampling_instruction_tests.rs',
                    'before_sha256': None,
                    'after_sha256': '2dce88b8cb25be18269dd587e631e86ed46807cf34045ab9ea5eba5ff09e66cd',
                    'after_bytes': 11533,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_sampling_preparation.rs',
                    'before_sha256': 'cafa07813e8abdb3eb3d266505fa5d3e7b693f3919957438284d45583510bf15',
                    'after_sha256': '8ae505fd218cac5fb3c92e8f39c80619fa0ae39c108c078c2d02ad32c3078a49',
                    'after_bytes': 11258,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/session.rs',
                    'before_sha256': '2da4c0288596269fbb6df6d9a04a389e8ce0184be77ee2bcce765521e63702a5',
                    'after_sha256': '090da8de560a9326bdadd7995dc35afb639d1e94dab8f261aa7f8261b0c05e61',
                    'after_bytes': 94084,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/world_state.rs',
                    'before_sha256': '5385374e5def781ed081dac2901e9d010106239ebeca38b5c7292df52f818203',
                    'after_sha256': 'b60680cc657ed6ed55bb1314dab5c8a51c6530a5d7d871950e7f3d04d257124e',
                    'after_bytes': 15366,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/state/session.rs',
                    'before_sha256': '3dedb51926cd6d341c667daa0152d7e36d487e97119c2c0e2dcaab7a93df7e44',
                    'after_sha256': '2bd87da9028dc44c091bed60839d1a02bdf0dd943253a9ddea16c16c07afb1ab',
                    'after_bytes': 18080,
                    'after_mode': 436}],
 'unformatted_patch_sha256': '1a84968a61a9108612fd82b3d48dbfbcc2daab47d9f88c868e6381758932a397',
 'status': 'RAM candidate; source70 and Clippy NOT_RUN; no production admission',
 'scope': 'Actual Session instruction/config and applied-manager lifetimes only; no complete '
          'contributor/executed versions or trusted PREGRANT owner'}
EXECUTED_STATE_CHECKPOINT = {'patch_file': 'executed-tool-calls-checkpoint.patch',
 'patch_sha256': 'a0da138f3d4f847f81356680301538a5e53b7f8df1317deb2be77dda14c5ddb7',
 'before_graph': {'rows': 8793,
                  'sha256': '69c605abba0daa10e0d174445f7894861eba024afd1cbd9ea9a5d091dbee7f6c'},
 'changed_files': [{'path': 'codex-rs/core/src/tools/executed_tool_calls.rs',
                    'before_sha256': '06cb4d27fec0da47dd7e981ccf8f5a4b900d6dc8362f1ded8ab1290f7c0d7d9f',
                    'after_sha256': 'a83c8bd18d01841c884732525b9981fd8a313e7e482e9268cc2135e53eb4d21d',
                    'after_bytes': 33137,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/tools/executed_tool_calls_checkpoint_tests.rs',
                    'before_sha256': None,
                    'after_sha256': '97df3691a51b9aea27155c615795f847e517051be3dffae7964b10bb2c0fd9e9',
                    'after_bytes': 11527,
                    'after_mode': 436}],
 'status': 'RAM candidate; source121 and Clippy NOT_RUN; no production admission',
 'scope': 'Foundation Option-state mutex-visit checkpoint only; separate executed_sampling_binding '
          'adds sampling attachment. Pending Direct atomics, MCP revision and final contributors '
          'excluded; no InputProof authority.'}
EXECUTED_REGRESSIONS = {'source_pins': [{'path': 'codex-rs/core/src/tools/executed_tool_calls_direct_tests.rs',
                  'bytes': 6978,
                  'sha256': '21febb49952f70795cbdeb24c83d02c027cb20dbd67eb64e385fa2099f59ddf1',
                  'mode': 436},
                 {'path': 'codex-rs/core/src/tools/executed_tool_calls/request_metadata.rs',
                  'bytes': 27565,
                  'sha256': '7e64b0cdf215d1aeac549a97f3bcce7815fb70c2d22a48f0b5cecb47d4fdd004',
                  'mode': 436},
                 {'path': 'codex-rs/core/src/tools/executed_tool_calls/request_metadata_tests.rs',
                  'bytes': 85527,
                  'sha256': 'efbcb4dd389b66a8b4f04919163519955bc4c0a47f0e3aac043cf9561880e1f1',
                  'mode': 436}],
 'direct_prefix': 'tools::executed_tool_calls::direct_tests::',
 'direct_count': 3,
 'request_metadata_prefix': 'tools::executed_tool_calls::request_metadata::tests::',
 'request_metadata_count': 36,
 'scope': 'Original finite direct/request-metadata test fixtures stay byteexact; request-metadata '
          'final implementation uses the exact post-Direct after-pin. Collection never substitutes '
          'for behavior.'}
EXECUTED_SAMPLING_BINDING = {'patch_file': 'retained-sampling-executed-state-binding.patch',
 'patch_sha256': '381352d3bebe91dcce60ff9c8b1b3576dc3220334919865bac8293ec6a257505',
 'before_graph': {'rows': 8794,
                  'sha256': 'd60b03708a3a5917b747f481a661a1f1fb978d789a045dfb0afb3be7b95b2fa6'},
 'changed_files': [{'path': 'codex-rs/core/src/session/retained_sampling_executed_state_tests.rs',
                    'before_sha256': None,
                    'after_sha256': 'ae364cfe0f1cdf535ca9b9abafbba06164278a840e9c45315ae16da39e350761',
                    'after_bytes': 14153,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/session/retained_sampling_preparation.rs',
                    'before_sha256': '8ae505fd218cac5fb3c92e8f39c80619fa0ae39c108c078c2d02ad32c3078a49',
                    'after_sha256': '763b127ca77e181b8d78c4a0e819278173644bfdfb35a73d41ff5c9aa438bac6',
                    'after_bytes': 12906,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/tools/executed_tool_calls/request_metadata.rs',
                    'before_sha256': '5f13e13ea19c60eecaba864507906ca9bc74dc3b57ba976bbd7a7b7d50233359',
                    'after_sha256': '06d2b4155fe34f725062b4576989c33aada9ec6acf5b671aa2c1be0783a289a6',
                    'after_bytes': 27384,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/tools/executed_tool_calls/sampling_checkpoint_tests.rs',
                    'before_sha256': None,
                    'after_sha256': 'a37ff251c31e16b3aac89d172f2cc94a15773cced8103d63230149763b4aada0',
                    'after_bytes': 5040,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/tools/mod.rs',
                    'before_sha256': '510635e3ae67e4c63e1feaf6d645f25dc2590f54391645dddeec0a84c1d17616',
                    'after_sha256': 'f03cc3cfda6d6df4cb8f1de3fdf734fa0298e0f649f7c3fb4671d77fc00490ec',
                    'after_bytes': 5375,
                    'after_mode': 436}],
 'source_cases': [{'label': 'sampling-executed6',
                   'prefix': 'session::retained_sampling_preparation::executed_state_tests::',
                   'path': 'codex-rs/core/src/session/retained_sampling_executed_state_tests.rs',
                   'parent_path': 'codex-rs/core/src/session/retained_sampling_preparation.rs',
                   'parent_declaration': '#[cfg(test)]\n'
                                         '#[path = "retained_sampling_executed_state_tests.rs"]\n'
                                         'mod executed_state_tests;',
                   'expected_nonzero_count': 6},
                  {'label': 'sampling-attachment2',
                   'prefix': 'tools::executed_tool_calls::request_metadata::sampling_checkpoint_tests::',
                   'path': 'codex-rs/core/src/tools/executed_tool_calls/sampling_checkpoint_tests.rs',
                   'parent_path': 'codex-rs/core/src/tools/executed_tool_calls/request_metadata.rs',
                   'parent_declaration': '#[cfg(test)]\n'
                                         '#[path = "sampling_checkpoint_tests.rs"]\n'
                                         'mod sampling_checkpoint_tests;',
                   'expected_nonzero_count': 2}],
 'status': 'Known-history source129 and original Clippy PASS in actual dbf1f7f87bf582ddb7ba154584846ba5080c370f run37891588614; source135 own behavior and Clippy NOT_RUN; production not admitted',
 'scope': 'Only sampling attachment binds existing executed Option-state checkpoint lifetime; no '
          'Direct atomics/MCP/post-lock budget/final-contributor version authority, no trusted '
          'PREGRANT/InputProof qualification or durable-start/send connection'}
DIRECT_LIFETIME_CHECKPOINT = {'patch_file': 'direct-lifetime-checkpoint.patch',
 'patch_sha256': '7ca38b3cf9aa3001f4d9ae2aef37b12d0a436dff0b0181f6e332ec2910ae35bc',
 'before_graph': {'rows': 8796,
                  'sha256': '13b12cd29533cec65e8c64b5c295cb530f695b2a3266b46ff88a05228f8a7f42'},
 'changed_files': [{'path': 'codex-rs/core/src/tools/executed_tool_calls.rs',
                    'before_sha256': 'a83c8bd18d01841c884732525b9981fd8a313e7e482e9268cc2135e53eb4d21d',
                    'after_sha256': '19fc63c29c50984eb657e875fbe34fc26240869bcc5509cae0aecfdce637da54',
                    'after_bytes': 33978,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/tools/executed_tool_calls/request_metadata.rs',
                    'before_sha256': '06d2b4155fe34f725062b4576989c33aada9ec6acf5b671aa2c1be0783a289a6',
                    'after_sha256': '7e64b0cdf215d1aeac549a97f3bcce7815fb70c2d22a48f0b5cecb47d4fdd004',
                    'after_bytes': 27565,
                    'after_mode': 436},
                   {'path': 'codex-rs/core/src/tools/executed_tool_calls_direct_checkpoint_tests.rs',
                    'before_sha256': None,
                    'after_sha256': '17062f2aabf605cb1ced0992dc8f1669ca93d1e96546f51d488e201c51c2f118',
                    'after_bytes': 8308,
                    'after_mode': 436}],
 'test_path': 'codex-rs/core/src/tools/executed_tool_calls_direct_checkpoint_tests.rs',
 'parent_path': 'codex-rs/core/src/tools/executed_tool_calls.rs',
 'parent_declaration': '#[cfg(test)]\n'
                       '#[path = "executed_tool_calls_direct_checkpoint_tests.rs"]\n'
                       'mod direct_checkpoint_tests;',
 'prefix': 'tools::executed_tool_calls::direct_checkpoint_tests::',
 'expected_nonzero_count': 6,
 'status': 'Engineering source135 candidate; actual135/Clippy NOT_RUN; production not admitted',
 'scope': 'Option-state plus accepted Direct-writer/reset lifetime invalidation only. The bounded '
          'Drop test observes completion while the state lock is held; it does not establish '
          'barrier-time atomic blocking or new dynamic reset authenticity. No full atomic '
          'snapshot, MCP/final-byte authority, trusted PREGRANT/InputProof, or sender admission.'}
DIRECT_CHECKPOINT_PREFIX = 'tools::executed_tool_calls::direct_checkpoint_tests::'
EXECUTED_DIRECT_PREFIX = 'tools::executed_tool_calls::direct_tests::'
EXECUTED_METADATA_PREFIX = 'tools::executed_tool_calls::request_metadata::tests::'
EXECUTED_PREFIX = 'tools::executed_tool_calls::checkpoint_tests::'
INSTRUCTION_CHILD_PREFIX = 'session::retained_outbound_snapshot::tests::instruction_material_tests::'
APPLIED_INSTRUCTIONS_PREFIX = 'agents_md_manager::checkpoint_tests::'
SAMPLING_CHILD_PREFIX = "session::retained_outbound_snapshot::tests::sampling_preparation_tests::"
SCOPES = [
    ("manager9", "codex-models-manager", "manager::retained_model_resolution::tests::", 9),
    ("native39", "codex-core", "session::retained_outbound_snapshot::tests::", 39),
    ("step-settings7", "codex-core", "session::step_settings::tests::", 7),
    ("metadata10", "codex-core", "client::retained_metadata::tests::", 10),
    ("applied-instructions5", "codex-core", APPLIED_INSTRUCTIONS_PREFIX, 5),
    ("executed-state12", "codex-core", EXECUTED_PREFIX, 12),
    ("executed-direct3", "codex-core", EXECUTED_DIRECT_PREFIX, 3),
    ("executed-metadata36", "codex-core", EXECUTED_METADATA_PREFIX, 36),
    ('sampling-executed6', 'codex-core', 'session::retained_sampling_preparation::executed_state_tests::', 6),
    ('sampling-attachment2', 'codex-core', 'tools::executed_tool_calls::request_metadata::sampling_checkpoint_tests::', 2),
    ("direct-checkpoint6", "codex-core", DIRECT_CHECKPOINT_PREFIX, 6),
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


def verify_legacy_inputs(bundle: Path) -> dict:
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
    sampling = manifest["sampling_preparation"]
    require(sampling == SAMPLING_PREPARATION
            and sha256(bundle / sampling["patch_file"]) == sampling["patch_sha256"],
            "Closed five-row sampling patch after exact Clippy repair required")
    instruction = manifest["instruction_materials"]
    require(instruction == INSTRUCTION_MATERIALS
            and sha256(bundle / instruction["patch_file"]) == instruction["patch_sha256"],
            "Closed eleven-row inert instruction patch after exact source58 required")
    executed = manifest["executed_state_checkpoint"]
    require(executed == EXECUTED_STATE_CHECKPOINT
            and sha256(bundle / executed["patch_file"]) == executed["patch_sha256"],
            "Closed two-row Option-state checkpoint patch after exact source70 required")
    require(manifest["executed_regressions"] == EXECUTED_REGRESSIONS,
            "Original finite executed regression source contract required")
    binding = manifest["executed_sampling_binding"]
    require(binding == EXECUTED_SAMPLING_BINDING
            and sha256(bundle / binding["patch_file"]) == binding["patch_sha256"],
            "Closed three-existing/two-new sampling executed binding after source121 required")
    direct = manifest["direct_lifetime_checkpoint"]
    require(direct == DIRECT_LIFETIME_CHECKPOINT
            and sha256(bundle / direct["patch_file"]) == direct["patch_sha256"],
            "Closed Direct lifetime patch after exact repaired source129 required")
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
                and graph["rows"] == 8797, "Complete source graph required")
    selections = manifest["test_selection"]
    require(len(selections["scopes"]) == 11 and selections["selected_total"] == 135
            and selections["same_step_selected_total"] == 48 and selections["affected_ordinary_selected_total"] == 7
            and selections["affected_metadata_selected_total"] == 10
            and selections["native_guard_selected_total"] == 22
            and selections["native_sampling_selected_total"] == 10
            and selections["native_instruction_selected_total"] == 7
            and selections["applied_instruction_selected_total"] == 5
            and selections["executed_state_selected_total"] == 12
            and selections["prior70_selected_total"] == 70
            and selections["checkpoint_subtotal"] == 82
            and selections["executed_regression_selected_total"] == 39
            and selections["original_executed_direct_selected_total"] == 3
            and selections["original_request_metadata_selected_total"] == 36
            and selections["prior121_selected_total"] == 121
            and selections["sampling_executed_selected_total"] == 6
            and selections["sampling_attachment_selected_total"] == 2
            and selections["sampling_binding_selected_total"] == 8
            and selections["prior129_selected_total"] == 129
            and selections["direct_checkpoint_selected_total"] == 6,
            "Fixed original121 plus sampling-executed6/attachment2 required")
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


STATIC_AUTH_CLIPPY_ARGV = ["clippy", "--locked", "--offline", "-p", "codex-model-provider",
                          "--lib", "--tests", "--no-deps"]
STATIC_AUTH_MANIFEST_SHA = "cf037cff5507ad91ba1db8b4a4f897fb4d505b53d36385306591bffc6c12dbd5"
LEGACY_MANIFEST_SHA = "5008f10471cdfe2ae7b937e511f0cfa661b90b85f3cf4b048db7aac8e542dcc0"
LEGACY_RUNNER_SHA = "571b5d84c609b2b412c9de58a61d7e851e24d51f2bba54efc57431e1668ad7dc"



STATIC_AUTH_FIELDS = {
    "schema_version", "status", "spec", "source",
    "baseline", "patch", "changed_files", "before_graph",
    "after_graph", "test_metadata", "lock_sha256", "profile",
    "test_selection", "clippy", "production_boundary", "licensing",
    "limitations", "supporting_auth_source_pins", "patch_asset_number", "selected_application_number",
}
STATIC_AUTH_BASELINE = json.loads('''{
  "manifest_file": "same-step-resolution-source.json",
  "manifest_bytes": 51255,
  "manifest_sha256": "5008f10471cdfe2ae7b937e511f0cfa661b90b85f3cf4b048db7aac8e542dcc0",
  "runner_file": "replay_same_step_resolution.py",
  "runner_bytes": 65105,
  "runner_sha256": "571b5d84c609b2b412c9de58a61d7e851e24d51f2bba54efc57431e1668ad7dc",
  "workflow_path": ".github/workflows/same-step-resolution.yml",
  "workflow_bytes": 5508,
  "workflow_sha256": "52cbdbc177c537019df677a38cc2c84ea94b304f7ce329fa610c3d585e5a9bbb",
  "original_selected_total": 135,
  "scope": "Old artifacts preserved byte-for-byte; no historical PASS or production qualification is inherited",
  "existing_patch_asset_count": 12,
  "selected_patch_applications": 9,
  "selection": "retained-request cumulative replacement followed by eight incrementals; first three alternatives are not applied serially"
}''')
STATIC_AUTH_FILES = json.loads('''[
  {
    "path": "codex-rs/model-provider/src/auth.rs",
    "before_bytes": 30476,
    "before_sha256": "1c1042b33df733ffb583d19bd3102c8511ab37b9e5e8cd91a673103321f249d8",
    "after_bytes": 41328,
    "after_sha256": "581fa80ada444b747033b53fa68597f92db5689df59365d4179581c7a51026ca",
    "before_mode": 436,
    "after_mode": 436
  },
  {
    "path": "codex-rs/model-provider/src/lib.rs",
    "before_bytes": 1604,
    "before_sha256": "0ec8bc9a91e752099602042e33152e3a6c1477d2ca757ab54cb1489a5a94d1f2",
    "after_bytes": 1650,
    "after_sha256": "a15a0026ade6a229125129688c35e28988316526673639dda4d176d209febea1",
    "before_mode": 436,
    "after_mode": 436
  },
  {
    "path": "codex-rs/model-provider/src/provider.rs",
    "before_bytes": 55121,
    "before_sha256": "adabad97f59dbc593431a9c47911e74d1fd9d48648b874026a23db86b32ec5a1",
    "after_bytes": 60511,
    "after_sha256": "04869e48b805efcd4e4f19402fd9248929acb1452673a32e72b8aca47c4173cf",
    "before_mode": 436,
    "after_mode": 436
  }
]''')
STATIC_AUTH_BOUNDARY = json.loads('''{
  "registration": false,
  "default_executor": null,
  "qualification": "Unqualified",
  "authoritative_model_version": null,
  "InputProof": "NOT_CLOSED",
  "native_owner": "NOT_CLOSED",
  "same_Arc_FrozenResponsesRequest": "NOT_CONNECTED",
  "secret_locator_and_version": "NOT_CONNECTED",
  "durable_start_to_actual_send": "NOT_CONNECTED",
  "actual_model_CLI_AppServer_send": "NOT_RUN",
  "status": "NOT_ADMITTED",
  "scope": "Static effective auth resolution only; mutable Request plus same owned snapshot is not freeze/send authority"
}''')
STATIC_AUTH_SUPPORTING_PINS = json.loads('''[
  {
    "path": "codex-rs/model-provider-info/src/lib.rs",
    "bytes": 31061,
    "sha256": "941a8ec0e8be4b45080cac3df3d052999a4cb104811575634b1a9ed510690958",
    "scope": "api_key actual Result<Option<String>>, no ambient lookup when env_key=None; validate Result<(),String>"
  },
  {
    "path": "codex-rs/model-provider/src/bearer_auth_provider.rs",
    "bytes": 3212,
    "sha256": "8db9f8a849d0fee2c6c349af69f2335ef403b65a54a4e216eb9f5ea284aa4949",
    "scope": "String constructor and final actual token-to-HeaderValue path"
  }
]''')


def verify_static_auth_inputs(bundle: Path) -> dict:
    require(sha256(bundle / "same-step-resolution-source.json") == LEGACY_MANIFEST_SHA
            and sha256(bundle / "replay_same_step_resolution.py") == LEGACY_RUNNER_SHA,
            "Byte-exact original135 contract and runner required")
    legacy = verify_legacy_inputs(bundle)
    path = bundle / "effective-static-auth-source.json"
    require(path.is_file() and not path.is_symlink()
            and sha256(path) == STATIC_AUTH_MANIFEST_SHA,
            "Fixed independent effective-static-auth source manifest required")
    addition = load(path)
    require(type(addition) is dict and set(addition) == STATIC_AUTH_FIELDS
            and type(addition["schema_version"]) is int and addition["schema_version"] == 1
            and type(addition["status"]) is str and bool(addition["status"]),
            "Closed typed static-auth asset contract required")
    require(addition["baseline"] == STATIC_AUTH_BASELINE
            and set(addition["baseline"]) == set(STATIC_AUTH_BASELINE)
            and all(type(addition["baseline"][key]) is int for key in [
                "manifest_bytes", "runner_bytes", "workflow_bytes", "existing_patch_asset_count",
                "selected_patch_applications", "original_selected_total"])
            and type(addition["patch_asset_number"]) is int and addition["patch_asset_number"] == 13
            and type(addition["selected_application_number"]) is int
            and addition["selected_application_number"] == 10,
            "Thirteenth asset is only the tenth selected application; no serial alternatives")
    prior_workflow = bundle.parents[1] / addition["baseline"]["workflow_path"]
    require(prior_workflow.is_file() and not prior_workflow.is_symlink()
            and sha256(prior_workflow) == STATIC_AUTH_BASELINE["workflow_sha256"],
            "Preserved original135 workflow required")
    require(addition["source"] == legacy["source"] and addition["spec"] == legacy["spec"]
            and addition["before_graph"] == legacy["complete_source_graph"]
            and addition["profile"] == legacy["profile"]
            and addition["test_metadata"] == legacy["test_metadata"]
            and addition["lock_sha256"] == LOCK_SHA
            and addition["licensing"] == legacy["licensing"],
            "Static-auth asset must extend the exact ninth-application source")
    for graph_set in ["before_graph", "after_graph"]:
        require(type(addition[graph_set]) is dict and set(addition[graph_set]) == {"source", "normalized"},
                "Both complete graphs required")
        for graph in addition[graph_set].values():
            require(type(graph) is dict and set(graph) == {"rows", "sha256"} and type(graph["rows"]) is int
                    and graph["rows"] == 8797 and type(graph["sha256"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", graph["sha256"]) is not None,
                    "Typed complete source graph required")
    patch = addition["patch"]
    require(type(patch) is dict and set(patch) == {"file", "bytes", "sha256"}
            and patch["file"] == "effective-static-auth.patch"
            and type(patch["bytes"]) is int and patch["bytes"] == 18064
            and patch["sha256"] == "aa9f2352605942c48d47450ff3803209bd0e8af7a7e369d92936f64307ace8f3",
            "Exact thirteenth patch asset required")
    patch_path = bundle / patch["file"]
    require(patch_path.is_file() and not patch_path.is_symlink()
            and patch_path.stat().st_size == patch["bytes"]
            and sha256(patch_path) == patch["sha256"], "Fixed static-auth patch bytes required")
    rows = addition["changed_files"]
    require(type(rows) is list and len(rows) == 3 and rows == STATIC_AUTH_FILES,
            "Exactly three fixed static-auth source changes required")
    for row in rows:
        require(type(row) is dict and set(row) == {"path", "before_bytes", "before_sha256", "after_bytes",
                             "after_sha256", "before_mode", "after_mode"}
                and type(row["path"]) is str
                and all(type(row[key]) is int and row[key] > 0 for key in ["before_bytes", "after_bytes"])
                and type(row["before_mode"]) is int and row["before_mode"] == 0o664
                and type(row["after_mode"]) is int and row["after_mode"] == 0o664
                and all(type(row[key]) is str and re.fullmatch(r"[0-9a-f]{64}", row[key]) is not None
                        for key in ["before_sha256", "after_sha256"]),
                "Typed before/after bytes and fullmode pins required")
    selected = addition["test_selection"]
    require(type(selected) is dict and set(selected) == {"scopes", "selected_total", "source_candidates_only", "status"}
            and type(selected["selected_total"]) is int and selected["selected_total"] == 13
            and selected["source_candidates_only"] is True and selected["status"] == "NOT_RUN"
            and type(selected["scopes"]) is list and len(selected["scopes"]) == 2,
            "Independent auth13 source candidates required")
    for scope, (label, selector, count) in zip(selected["scopes"], [
        ("effective-auth8", "auth::tests::controlled_static_", 8),
        ("effective-provider5", "provider::tests::controlled_static_snapshot_", 5),
    ]):
        require(type(scope) is dict and set(scope) == {"label", "package", "filter", "expected_passed", "test_names", "argv_tail"}
                and scope["label"] == label and scope["package"] == "codex-model-provider"
                and scope["filter"] == selector
                and type(scope["expected_passed"]) is int and scope["expected_passed"] == count
                and type(scope["test_names"]) is list
                and len(scope["test_names"]) == len(set(scope["test_names"])) == count
                and all(type(name) is str and name.startswith(selector) for name in scope["test_names"])
                and scope["test_names"] == sorted(scope["test_names"])
                and scope["argv_tail"] == ["test", "--locked", "--offline", "-p", "codex-model-provider",
                                           "--lib", selector, "--", "--nocapture"],
                "Exact fixed independent static-auth selector required")
    lint = addition["clippy"]
    require(type(lint) is dict and set(lint) == {"original_argv_tail", "provider_argv_tail", "rules", "status"}
            and lint["original_argv_tail"] == CLIPPY_ARGV
            and lint["provider_argv_tail"] == STATIC_AUTH_CLIPPY_ARGV
            and type(lint["rules"]) is str and lint["status"] == "NOT_RUN",
            "Separate original/provider Clippy commands under existing rules required")
    boundary = addition["production_boundary"]
    require(type(boundary) is dict and set(boundary) == set(STATIC_AUTH_BOUNDARY) and boundary == STATIC_AUTH_BOUNDARY
            and boundary["registration"] is False and boundary["default_executor"] is None
            and boundary["authoritative_model_version"] is None
            and boundary["qualification"] == "Unqualified" and boundary["status"] == "NOT_ADMITTED",
            "Snapshot foundation cannot admit production")
    require(addition["supporting_auth_source_pins"] == STATIC_AUTH_SUPPORTING_PINS
            and type(addition["limitations"]) is list
            and all(type(item) is str for item in addition["limitations"]),
            "Static source evidence and unresolved boundaries required")
    manifest = dict(legacy)
    manifest["effective_static_auth"] = addition
    manifest["complete_source_graph"] = addition["after_graph"]
    manifest["test_selection"] = dict(legacy["test_selection"])
    manifest["test_selection"]["scopes"] = legacy["test_selection"]["scopes"] + selected["scopes"]
    manifest["test_selection"]["selected_total"] = 148
    return manifest


def static_auth_source_names(root: Path) -> list[list[str]]:
    result = []
    for relative, prefix, expected_count in [
        ("codex-rs/model-provider/src/auth.rs", "auth::tests::", 8),
        ("codex-rs/model-provider/src/provider.rs", "provider::tests::", 5),
    ]:
        text = (root / relative).read_text()
        names = re.findall(r"#\[test\]\s+fn (controlled_static_\w+)\(", text)
        require(len(names) == len(set(names)) == expected_count,
                "Exact independent static-auth source test names required")
        result.append(sorted(prefix + name for name in names))
    return result


def selection_groups(scopes: list[dict], manifest: dict) -> dict:
    groups = {}
    for label, expected, total in [
        ("original135", manifest["test_selection"]["scopes"][:11], 135),
        ("effective_static_auth13", manifest["effective_static_auth"]["test_selection"]["scopes"], 13),
        ("frozen_config4", manifest["frozen_config_materialization"]["test_selection"]["scopes"], 4),
        ("native_owner23", manifest["native_pregrant_owner"]["test_selection"]["scopes"], 23),
    ]:
        labels = [scope["label"] for scope in expected]
        observed = [scope for scope in scopes if scope["label"] in labels]
        passed = sum(scope["summary"]["passed"] for scope in observed if scope["summary"])
        complete = len(observed) == len(labels) and {scope["label"] for scope in observed} == set(labels)
        status = "PASS" if complete and passed == total and all(scope["status"] == "PASS" for scope in observed) else (
            "FAIL" if any(scope["status"] == "FAIL" for scope in observed) else "NOT_RUN")
        groups[label] = {"status": status, "selected_total_expected": total,
                         "selected_total_passed": passed,
                         "tests_executed": sum(sum(scope["actual_running_counts"]) for scope in observed),
                         "scope_labels_observed": [scope["label"] for scope in observed],
                         "scope": "Actual observations on this twelfth-application owner graph; no inherited PASS"}
    return groups


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
    for relative, selector, direct_count in [
        ("codex-rs/models-manager/src/retained_model_resolution_tests.rs", SCOPES[0][2], 9),
        ("codex-rs/core/src/session/retained_outbound_snapshot_tests.rs", SCOPES[1][2], 22),
    ]:
        text = (root / relative).read_text()
        direct = re.findall(r"#\[tokio::test\]\s+async fn (\w+)\(", text)
        require(len(direct) == len(set(direct)) == direct_count, "Unique fixed direct test names required")
        names = [selector + name for name in direct]
        if direct_count == 22:
            declaration = '#[path = "retained_sampling_preparation_tests.rs"]\nmod sampling_preparation_tests;'
            require(text.count(declaration) == 1, "Exact native sampling child module required")
            child = (root / "codex-rs/core/src/session/retained_sampling_preparation_tests.rs").read_text()
            child_names = re.findall(r"#\[tokio::test\]\s+async fn (\w+)\(", child)
            require(len(child_names) == len(set(child_names)) == 10, "Unique ten sampling child candidates required")
            names += [SAMPLING_CHILD_PREFIX + name for name in child_names]
            declaration = '#[path = "retained_sampling_instruction_tests.rs"]\nmod instruction_material_tests;'
            require(text.count(declaration) == 1, "Exact native instruction child module required")
            child = (root / "codex-rs/core/src/session/retained_sampling_instruction_tests.rs").read_text()
            child_names = re.findall(r"#\[tokio::test\]\s+async fn (\w+)\(", child)
            require(len(child_names) == len(set(child_names)) == 7, "Unique seven instruction child candidates required")
            names += [INSTRUCTION_CHILD_PREFIX + name for name in child_names]
            require(len(names) == len(set(names)) == 39, "Unique native22 plus sampling10 plus instruction7 required")
        result.append(sorted(names))
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
    manager = (root / "codex-rs/core/src/agents_md_manager.rs").read_text()
    declaration = '#[cfg(test)]\n#[path = "agents_md_checkpoint_tests.rs"]\nmod checkpoint_tests;'
    require(manager.count(declaration) == 1, "Exact applied-manager checkpoint child module required")
    child = (root / "codex-rs/core/src/agents_md_checkpoint_tests.rs").read_text()
    names = re.findall(r"#\[tokio::test\]\s+async fn (\w+)\(", child)
    require(len(names) == len(set(names)) == 5, "Unique five applied-manager candidates required")
    result.append(sorted(APPLIED_INSTRUCTIONS_PREFIX + name for name in names))
    executed = (root / "codex-rs/core/src/tools/executed_tool_calls.rs").read_text()
    declaration = '#[cfg(test)]\n#[path = "executed_tool_calls_checkpoint_tests.rs"]\nmod checkpoint_tests;'
    require(executed.count(declaration) == 1, "Exact executed-state checkpoint child module required")
    child = (root / "codex-rs/core/src/tools/executed_tool_calls_checkpoint_tests.rs").read_text()
    names = re.findall(r"#\[test\]\s+fn (\w+)\(", child)
    require(len(names) == len(set(names)) == 12, "Unique twelve executed-state candidates required")
    result.append(sorted(EXECUTED_PREFIX + name for name in names))
    declaration = '#[cfg(test)]\n#[path = "executed_tool_calls_direct_tests.rs"]\nmod direct_tests;'
    require(executed.count(declaration) == 1, "Exact original direct-tests child module required")
    for pin in EXECUTED_REGRESSIONS["source_pins"]:
        path = root / pin["path"]
        require(path.is_file() and path.stat().st_size == pin["bytes"]
                and sha256(path) == pin["sha256"] and path.stat().st_mode & 0o7777 == pin["mode"],
                "Original executed regression source bytes/fullmode required")
    request = (root / "codex-rs/core/src/tools/executed_tool_calls/request_metadata.rs").read_text()
    declaration = '#[cfg(test)]\n#[path = "request_metadata_tests.rs"]\nmod tests;'
    require(request.count(declaration) == 1, "Exact original request-metadata child module required")
    for relative, prefix, count in [
        ("codex-rs/core/src/tools/executed_tool_calls_direct_tests.rs", EXECUTED_DIRECT_PREFIX, 3),
        ("codex-rs/core/src/tools/executed_tool_calls/request_metadata_tests.rs", EXECUTED_METADATA_PREFIX, 36),
    ]:
        child = (root / relative).read_text()
        names = re.findall(r"#\[(?:test|tokio::test)\]\s+(?:async )?fn (\w+)\(", child)
        require(len(names) == len(set(names)) == count and "#[test_case" not in child,
                "Unique fixed original executed regression source names required")
        result.append(sorted(prefix + name for name in names))
    for case in EXECUTED_SAMPLING_BINDING["source_cases"]:
        parent = (root / case["parent_path"]).read_text()
        require(parent.count(case["parent_declaration"]) == 1,
                "Exact sampling executed-state child module required")
        child = (root / case["path"]).read_text()
        names = re.findall(r"#\[(?:test|tokio::test)\]\s+(?:async )?fn (\w+)\(", child)
        count = case["expected_nonzero_count"]
        require(count > 0 and len(names) == len(set(names)) == count and "#[test_case" not in child,
                "Unique nonzero sampling executed-state source names required")
        result.append(sorted(case["prefix"] + name for name in names))
    direct = DIRECT_LIFETIME_CHECKPOINT
    parent = (root / direct["parent_path"]).read_text()
    require(parent.count(direct["parent_declaration"]) == 1,
            "Exact Direct lifetime child module required")
    child = (root / direct["test_path"]).read_text()
    names = re.findall(r"#\[(?:test|tokio::test)\]\s+(?:async )?fn (\w+)\(", child)
    count = direct["expected_nonzero_count"]
    require(count > 0 and len(names) == len(set(names)) == count and "#[test_case" not in child,
            "Unique nonzero Direct lifetime source test names required")
    result.append(sorted(direct["prefix"] + name for name in names))
    return result

def prepare_static_auth(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
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
        ("sampling-preparation", manifest["sampling_preparation"]["patch_file"], manifest["sampling_preparation"]),
        ("instruction-materials", manifest["instruction_materials"]["patch_file"], manifest["instruction_materials"]),
        ("executed-state-checkpoint", manifest["executed_state_checkpoint"]["patch_file"], manifest["executed_state_checkpoint"]),
        ("executed-sampling-binding", manifest["executed_sampling_binding"]["patch_file"], manifest["executed_sampling_binding"]),
        ("direct-lifetime-checkpoint", manifest["direct_lifetime_checkpoint"]["patch_file"], manifest["direct_lifetime_checkpoint"]),
        ("effective-static-auth", manifest["effective_static_auth"]["patch"]["file"], manifest["effective_static_auth"]),
    ]:
        before = full_inventory(source)
        if label == "clippy-repair":
            require(len(before) == REPAIR_BEFORE_GRAPH["rows"]
                    and graph_digest(before) == REPAIR_BEFORE_GRAPH["sha256"],
                    "Exact actual66 source required before Clippy repair")
        if label == "sampling-preparation":
            graph = manifest["sampling_preparation"]["before_graph"]
            require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                    "Exact repaired source299 required before sampling patch")
        if label == "instruction-materials":
            graph = manifest["instruction_materials"]["before_graph"]
            require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                    "Exact source58 required before inert instruction patch")
        if label == "executed-state-checkpoint":
            graph = manifest["executed_state_checkpoint"]["before_graph"]
            require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                    "Exact source70 required before Option-state checkpoint patch")
        if label == "executed-sampling-binding":
            graph = manifest["executed_sampling_binding"]["before_graph"]
            require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                    "Exact source121 required before sampling executed-state binding")
        if label == "direct-lifetime-checkpoint":
            graph = manifest["direct_lifetime_checkpoint"]["before_graph"]
            require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                    "Exact repaired source129 required before Direct lifetime patch")
        if label == "effective-static-auth":
            graph = manifest["effective_static_auth"]["before_graph"]["source"]
            require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                    "Exact ninth-application source required before static-auth addition")
        patch_root = source / "codex-rs" if label in {"instruction-materials", "executed-state-checkpoint", "executed-sampling-binding", "direct-lifetime-checkpoint"} else source
        for suffix, flags in [("check", ["--check"]), ("apply", [])]:
            row = recorder.run(label + "-" + suffix, ["git", "apply", *flags, str(bundle / filename)], patch_root)
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
    require(source_test_names(tests) == [scope["test_names"] for scope in manifest["test_selection"]["scopes"][:11]],
            "Exact original135 source test-name candidates required")
    require(static_auth_source_names(tests) == [scope["test_names"] for scope in manifest["effective_static_auth"]["test_selection"]["scopes"]],
            "Exact independent auth13 source test-name candidates required")
    write_json(output / "source-before-files.json", source_files)
    write_json(output / "test-before-files.json", test_files)
    report["paths"] = {"source": str(source), "tests": str(tests), "inherited_original": str(original),
                       "inherited_normalized": str(normalized)}
    report["source_graph"] = manifest["complete_source_graph"]
    report["source_names_checked"] = True
    return 0



FROZEN_CONFIG_MANIFEST_SHA = "c9de17b7b4d5a545ea8cefdde4d1c91aed9b8c9807b030e6d1a2565ba9347f51"
FROZEN_CONFIG_MANIFEST_BYTES = 7100
STATIC_AUTH_RUNNER_SHA = "368ba9372a00529ebee1be3652377db73cd3131cee7752a429a1921eb680c42f"
FROZEN_CONFIG_PREFIX = "config::tests::config_materialization_replay_"
FROZEN_CONFIG_CONTRACT = json.loads('{\n  "after_graph": {\n    "normalized": {\n      "rows": 8797,\n      "sha256": "8477fabaa8349c64d89f703738662245d9f058b769e79e70bbd228e59472e159"\n    },\n    "source": {\n      "rows": 8797,\n      "sha256": "7a5dc99a885459a82173546f5411031000c491a56f457a7926258479dd6a39e7"\n    }\n  },\n  "baseline": {\n    "existing_patch_asset_count": 13,\n    "manifest_bytes": 9309,\n    "manifest_file": "effective-static-auth-source.json",\n    "manifest_sha256": "cf037cff5507ad91ba1db8b4a4f897fb4d505b53d36385306591bffc6c12dbd5",\n    "original_selected_total": 148,\n    "runner_bytes": 81422,\n    "runner_file": "replay_effective_static_auth.py",\n    "runner_sha256": "368ba9372a00529ebee1be3652377db73cd3131cee7752a429a1921eb680c42f",\n    "scope": "Byte-exact prior engineering artifacts preserved; no prior PASS or native qualification inherited.",\n    "selected_patch_applications": 10,\n    "workflow_bytes": 5938,\n    "workflow_path": ".github/workflows/effective-static-auth.yml",\n    "workflow_sha256": "a42fb00fef7a150d229de43915ef8a23634112deb34a45f116eb4e7e4c26cccf"\n  },\n  "before_graph": {\n    "normalized": {\n      "rows": 8797,\n      "sha256": "843bf6342b8e4e559a0daad997608f0328f76a1a83fabf4f07cf3613d9c042ad"\n    },\n    "source": {\n      "rows": 8797,\n      "sha256": "7304a734db206fc7462c89a4434248e649ae562b7a81c82c656399f9b674c2de"\n    }\n  },\n  "changed_files": [\n    {\n      "after_bytes": 211054,\n      "after_mode": 436,\n      "after_sha256": "59481f8da09bacb32786bc219316dca379d77b42fbe64de9976c74b8618545e7",\n      "before_bytes": 200720,\n      "before_mode": 436,\n      "before_sha256": "854f5a6b184714740500b8d3eae2bb04cb88172efccf11d38a74f2f6189c0341",\n      "path": "codex-rs/core/src/config/mod.rs"\n    },\n    {\n      "after_bytes": 434968,\n      "after_mode": 436,\n      "after_sha256": "8ef4a8747e4bc4c3501ae4ec0d4d7263ebf38871e77e707452718e7f819769d0",\n      "before_bytes": 428597,\n      "before_mode": 436,\n      "before_sha256": "f0bc5025f20a1f2b00a85fa7df62f3c49c7a3f9e342c901f1907b41a4b40d1e0",\n      "path": "codex-rs/core/src/config/config_tests.rs"\n    }\n  ],\n  "clippy": {\n    "original_argv_tail": [\n      "clippy",\n      "--locked",\n      "--offline",\n      "-p",\n      "codex-models-manager",\n      "-p",\n      "codex-core",\n      "--lib",\n      "--tests",\n      "--no-deps"\n    ],\n    "provider_argv_tail": [\n      "clippy",\n      "--locked",\n      "--offline",\n      "-p",\n      "codex-model-provider",\n      "--lib",\n      "--tests",\n      "--no-deps"\n    ],\n    "rules": "Existing workspace rules only; no -D warnings; independent actual exits and receipts",\n    "status": "NOT_RUN"\n  },\n  "licensing": {\n    "LICENSE_sha256": "d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc",\n    "NOTICE_sha256": "9d71575ecfd9a843fc1677b0efb08053c6ba9fd686a0de1a6f5382fd3c220915",\n    "scope": "Original upstream LICENSE and NOTICE preserved byte-for-byte for the upstream-derived patch. This does not select a license for the Learning Workbench repository."\n  },\n  "limitations": [\n    "Only SDK captured Config inputs and20 typed materialization source slots are added; private opaque context cannot be caller-constructed or serialized as authority.",\n    "Live legacy wrapper calls the same materializer/capture path; replay consumes actual captured context without filesystem argument or missing-field fallback.",\n    "Remaining permission/path/requirements helper effect chains are not globally qualified; no pure SessionServices/native Session/Step/platform owner admission.",\n    "Four future source tests exercise actual SDK fixture/full Config equality/nonempty warnings/changed live files/live invalid catalog/missing source cause/observed absence; source declarations alone are not passing execution.",\n    "Version normalization0.160.0to0.0.0 only for test metadata; original lock exact; not release equivalence.",\n    "No local source execution/build/environment or key probes; actual future GitHub engineering Cargo tests/Clippy use explicit setup only."\n  ],\n  "lock_sha256": "5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c",\n  "patch": {\n    "bytes": 33238,\n    "file": "frozen-config-materialization.patch",\n    "sha256": "9178e8981b7b5148146081a8acd460ecdad0b7c2d55c1db2d1369fb727c2b7b0"\n  },\n  "patch_asset_number": 14,\n  "production_boundary": {\n    "authoritative_model_version": null,\n    "complete_InputProof": "NOT_ESTABLISHED",\n    "default_executor": null,\n    "native_Session_Step_owner": "NOT_IMPLEMENTED",\n    "qualification": "Unqualified",\n    "real_Agent": "NOT_RUN",\n    "registration": false,\n    "status": "NOT_ADMITTED"\n  },\n  "profile": {\n    "CARGO_BUILD_JOBS": "2",\n    "CARGO_INCREMENTAL": "0",\n    "CARGO_PROFILE_DEV_DEBUG": "0",\n    "CARGO_PROFILE_DEV_INCREMENTAL": "false",\n    "CARGO_PROFILE_TEST_DEBUG": "0",\n    "CARGO_PROFILE_TEST_INCREMENTAL": "false",\n    "RUST_TEST_THREADS": "2",\n    "scope": "New bounded remote test profile, not original-profile or release CLI binary equivalence"\n  },\n  "schema_version": 1,\n  "selected_application_number": 11,\n  "source": {\n    "archive_root": "codex-a956835d020762cb2b570053af06f643a11c0ecc",\n    "archive_sha256": "351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927",\n    "archive_url": "https://codeload.github.com/openai/codex/tar.gz/a956835d020762cb2b570053af06f643a11c0ecc",\n    "commit": "a956835d020762cb2b570053af06f643a11c0ecc",\n    "release_tag": "rust-v0.160.0",\n    "repository": "https://github.com/openai/codex"\n  },\n  "spec": {\n    "sha256": "b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec",\n    "version": "3.0.15"\n  },\n  "status": "SOURCE_CANDIDATE_TESTS_NOT_RUN",\n  "test_metadata": {\n    "after_sha256": "436af5eb66ede70feba73b71a890a429722e35ae811657bd117d7e34bc751f38",\n    "after_version": "0.0.0",\n    "before_sha256": "e558c28aaf94c9f20c7d57224eb9509084e31110850aad24d04bef7811dc335d",\n    "before_version": "0.160.0",\n    "path": "codex-rs/Cargo.toml",\n    "scope": "Only local workspace package versions are normalized for the upstream original lock. This does not prove release binary or profile equivalence.",\n    "section": "workspace.package"\n  },\n  "test_selection": {\n    "scopes": [\n      {\n        "argv_tail": [\n          "test",\n          "--locked",\n          "--offline",\n          "-p",\n          "codex-core",\n          "--lib",\n          "config::tests::config_materialization_replay_",\n          "--",\n          "--nocapture"\n        ],\n        "expected_passed": 4,\n        "filter": "config::tests::config_materialization_replay_",\n        "label": "frozen-config4",\n        "package": "codex-core",\n        "test_names": [\n          "config::tests::config_materialization_replay_accepts_observed_absence",\n          "config::tests::config_materialization_replay_keeps_captured_file_sources",\n          "config::tests::config_materialization_replay_preserves_values_and_warnings",\n          "config::tests::config_materialization_replay_rejects_missing_source_record"\n        ]\n      }\n    ],\n    "selected_total": 4,\n    "source_candidates_only": true,\n    "status": "NOT_RUN"\n  }\n}\n')


def verify_frozen_config_inputs(bundle: Path) -> dict:
    baseline = verify_static_auth_inputs(bundle)
    path = bundle / "frozen-config-materialization-source.json"
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size == FROZEN_CONFIG_MANIFEST_BYTES
            and sha256(path) == FROZEN_CONFIG_MANIFEST_SHA,
            "Fixed independent frozen Config manifest required")
    addition = load(path)
    require(type(addition) is dict and set(addition) == set(FROZEN_CONFIG_CONTRACT)
            and addition == FROZEN_CONFIG_CONTRACT,
            "Closed exact fourteenth-asset Config contract required")
    binding = addition["baseline"]
    require(type(addition["schema_version"]) is int and addition["schema_version"] == 1
            and type(addition["patch_asset_number"]) is int and addition["patch_asset_number"] == 14
            and type(addition["selected_application_number"]) is int
            and addition["selected_application_number"] == 11
            and binding["existing_patch_asset_count"] == 13
            and binding["selected_patch_applications"] == 10
            and binding["original_selected_total"] == 148,
            "Fourteenth patch asset is only the eleventh selected application")
    for base_path, expected_bytes, expected_sha in [
        (bundle / binding["manifest_file"], binding["manifest_bytes"], binding["manifest_sha256"]),
        (bundle / binding["runner_file"], binding["runner_bytes"], binding["runner_sha256"]),
        (bundle.parents[1] / binding["workflow_path"], binding["workflow_bytes"], binding["workflow_sha256"]),
    ]:
        require(base_path.is_file() and not base_path.is_symlink()
                and base_path.stat().st_size == expected_bytes and sha256(base_path) == expected_sha,
                "Prior static-auth artifacts must remain byte-exact")
    require(binding["manifest_sha256"] == STATIC_AUTH_MANIFEST_SHA
            and binding["runner_sha256"] == STATIC_AUTH_RUNNER_SHA
            and addition["source"] == baseline["source"]
            and addition["spec"] == baseline["spec"]
            and addition["before_graph"] == baseline["complete_source_graph"]
            and addition["profile"] == baseline["profile"]
            and addition["test_metadata"] == baseline["test_metadata"]
            and addition["lock_sha256"] == LOCK_SHA
            and addition["licensing"] == baseline["licensing"],
            "Config slice must extend only the exact tenth-application graph")
    for phase in ["before_graph", "after_graph"]:
        graphs = addition[phase]
        require(type(graphs) is dict and set(graphs) == {"source", "normalized"},
                "Both fixed Config source graphs required")
        for graph in graphs.values():
            require(type(graph) is dict and set(graph) == {"rows", "sha256"}
                    and type(graph["rows"]) is int and graph["rows"] == 8797
                    and type(graph["sha256"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", graph["sha256"]) is not None,
                    "Typed complete 8797-row Config graph required")
    patch = addition["patch"]
    require(type(patch) is dict and set(patch) == {"file", "bytes", "sha256"}
            and patch["file"] == "frozen-config-materialization.patch"
            and type(patch["bytes"]) is int and patch["bytes"] == 33238
            and patch["sha256"] == "9178e8981b7b5148146081a8acd460ecdad0b7c2d55c1db2d1369fb727c2b7b0",
            "Exact fourteenth Config patch asset required")
    patch_path = bundle / patch["file"]
    require(patch_path.is_file() and not patch_path.is_symlink()
            and patch_path.stat().st_size == patch["bytes"]
            and sha256(patch_path) == patch["sha256"],
            "Fixed combined Config source/test patch required")
    rows = addition["changed_files"]
    require(type(rows) is list and len(rows) == 2
            and sorted(row["path"] for row in rows) == [
                "codex-rs/core/src/config/config_tests.rs",
                "codex-rs/core/src/config/mod.rs",
            ], "Exactly two native Config source paths required")
    for row in rows:
        require(type(row) is dict and set(row) == {
                    "path", "before_bytes", "before_sha256", "before_mode",
                    "after_bytes", "after_sha256", "after_mode",
                }
                and all(type(row[key]) is int and row[key] > 0
                        for key in ["before_bytes", "after_bytes"])
                and type(row["before_mode"]) is int and row["before_mode"] == 0o664
                and type(row["after_mode"]) is int and row["after_mode"] == 0o664
                and all(type(row[key]) is str
                        and re.fullmatch(r"[0-9a-f]{64}", row[key]) is not None
                        for key in ["before_sha256", "after_sha256"]),
                "Typed fixed Config bytes and fullmodes required")
    selected = addition["test_selection"]
    require(type(selected) is dict and set(selected) == {
                "scopes", "selected_total", "source_candidates_only", "status",
            } and type(selected["selected_total"]) is int and selected["selected_total"] == 4
            and selected["source_candidates_only"] is True and selected["status"] == "NOT_RUN"
            and type(selected["scopes"]) is list and len(selected["scopes"]) == 1,
            "Independent nonzero Config4 source candidates required")
    scope = selected["scopes"][0]
    require(type(scope) is dict and set(scope) == {
                "label", "package", "filter", "expected_passed", "test_names", "argv_tail",
            } and scope["label"] == "frozen-config4" and scope["package"] == "codex-core"
            and scope["filter"] == FROZEN_CONFIG_PREFIX
            and type(scope["expected_passed"]) is int and scope["expected_passed"] == 4
            and type(scope["test_names"]) is list
            and len(scope["test_names"]) == len(set(scope["test_names"])) == 4
            and scope["test_names"] == sorted(scope["test_names"])
            and all(type(name) is str and name.startswith(FROZEN_CONFIG_PREFIX)
                    for name in scope["test_names"])
            and scope["argv_tail"] == [
                "test", "--locked", "--offline", "-p", "codex-core",
                "--lib", FROZEN_CONFIG_PREFIX, "--", "--nocapture",
            ], "Actual config::tests namespace and fixed four behavior tests required")
    lint = addition["clippy"]
    require(lint["original_argv_tail"] == CLIPPY_ARGV
            and lint["provider_argv_tail"] == STATIC_AUTH_CLIPPY_ARGV
            and lint["status"] == "NOT_RUN",
            "Original two-package and independent provider Clippy commands required")
    boundary = addition["production_boundary"]
    require(boundary["registration"] is False and boundary["default_executor"] is None
            and boundary["qualification"] == "Unqualified"
            and boundary["authoritative_model_version"] is None
            and boundary["complete_InputProof"] == "NOT_ESTABLISHED"
            and boundary["native_Session_Step_owner"] == "NOT_IMPLEMENTED"
            and boundary["real_Agent"] == "NOT_RUN" and boundary["status"] == "NOT_ADMITTED",
            "Config capture/replay cannot admit production or native owner")
    manifest = dict(baseline)
    manifest["static_auth_baseline"] = baseline
    manifest["frozen_config_materialization"] = addition
    manifest["complete_source_graph"] = addition["after_graph"]
    manifest["test_selection"] = dict(baseline["test_selection"])
    manifest["test_selection"]["scopes"] = baseline["test_selection"]["scopes"] + selected["scopes"]
    manifest["test_selection"]["selected_total"] = 152
    return manifest


def frozen_config_source_names(root: Path) -> list[list[str]]:
    parent = (root / "codex-rs/core/src/config/mod.rs").read_text()
    declaration = '#[cfg(test)]\n#[path = "config_tests.rs"]\nmod tests;'
    require(parent.count(declaration) == 1,
            "Actual SDK config::tests child module declaration required")
    child = (root / "codex-rs/core/src/config/config_tests.rs").read_text()
    names = re.findall(
        r"#\[tokio::test\]\s+async fn (config_materialization_replay_\w+)\(", child,
    )
    require(len(names) == len(set(names)) == 4,
            "Unique exact four frozen Config source declarations required")
    return [sorted("config::tests::" + name for name in names)]


def prepare_frozen_config(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
            bundle: Path, recorder: Recorder) -> int:
    baseline = manifest["static_auth_baseline"]
    result = prepare_static_auth(args, output, report, baseline, bundle, recorder)
    if result != 0:
        return result
    addition = manifest["frozen_config_materialization"]
    source, tests = output / "source", output / "test-source"
    source_before = verify_prepared(source, baseline, "source")
    test_before = verify_prepared(tests, baseline, "normalized")
    write_json(output / "static-auth-source-before-files.json", source_before)
    write_json(output / "static-auth-test-before-files.json", test_before)
    applications = []
    for phase, root, before in [
        ("source", source, source_before),
        ("normalized", tests, test_before),
    ]:
        graph = addition["before_graph"][phase]
        require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                "Exact auth8 graph required before eleventh Config application")
        for row in addition["changed_files"]:
            require(before.get(row["path"]) == {
                        "kind": "file", "bytes": row["before_bytes"],
                        "sha256": row["before_sha256"], "mode": row["before_mode"],
                    }, "Exact Config before bytes/fullmode required")
        for suffix, flags in [("check", ["--check"]), ("apply", [])]:
            command = recorder.run(
                "frozen-config-" + phase + "-" + suffix,
                ["git", "apply", *flags, str(bundle / addition["patch"]["file"])], root,
            )
            if command["exit_code"] != 0:
                return positive_exit(command["exit_code"])
        after = verify_prepared(root, manifest, phase)
        changed = sorted(row["path"] for row in addition["changed_files"])
        require(differences(before, after) == changed,
                "Config patch exceeded exactly two native source paths")
        for row in addition["changed_files"]:
            require(after[row["path"]] == {
                        "kind": "file", "bytes": row["after_bytes"],
                        "sha256": row["after_sha256"], "mode": row["after_mode"],
                    }, "Exact Config after bytes/fullmode required")
        applications.append({
            "phase": phase, "changed_paths": changed,
            "before_graph": graph, "after_graph": addition["after_graph"][phase],
            "exact_bytes_fullmodes_and_graph": True,
        })
    source_files = verify_prepared(source, manifest, "source")
    test_files = verify_prepared(tests, manifest, "normalized")
    require(differences(source_files, test_files) == [manifest["test_metadata"]["path"]],
            "Only original test metadata normalization differs between final graphs")
    require(source_test_names(tests) == [
                scope["test_names"] for scope in manifest["test_selection"]["scopes"][:11]
            ], "Original135 source candidates must remain exact on new Config graph")
    require(static_auth_source_names(tests) == [
                scope["test_names"]
                for scope in manifest["effective_static_auth"]["test_selection"]["scopes"]
            ], "Independent auth13 source candidates must remain exact on new Config graph")
    require(frozen_config_source_names(tests) == [
                scope["test_names"] for scope in addition["test_selection"]["scopes"]
            ], "Actual four Config test source names must match fixed manifest")
    write_json(output / "source-before-files.json", source_files)
    write_json(output / "test-before-files.json", test_files)
    report["source_graph"] = manifest["complete_source_graph"]
    report["frozen_config_application"] = {
        "patch_asset_number": 14, "selected_application_number": 11,
        "applications": applications, "source_candidates_only": True,
        "behavior_tests": "NOT_RUN", "production": "NOT_ADMITTED",
    }
    report["frozen_config_source_names_checked"] = True
    return 0



NATIVE_OWNER_MANIFEST_SHA = "29eda0690cccf3f2bb1fc019f924c13eb26fe7db1973cb302120749c04324f60"
NATIVE_OWNER_MANIFEST_BYTES = 11591
FROZEN_CONFIG_RUNNER_SHA = "24f6a5404506b4ff7679b804fcc6d92ce86d852b22f4f2e2975e5742334f8200"
NATIVE_OWNER_PREFIX = "session::pregrant_owner::tests::pregrant_owner_"
NATIVE_OWNER_CONTRACT = json.loads('{\n  "after_graph": {\n    "normalized": {\n      "rows": 8799,\n      "sha256": "34e0a0728c53d092bcadef645063273e0a208cce01328ade32a8fb155e291458"\n    },\n    "source": {\n      "rows": 8799,\n      "sha256": "4878337017b976781faf770a857806897f3affb1d835e574d0d48bc76aa053ed"\n    }\n  },\n  "baseline": {\n    "existing_patch_asset_count": 14,\n    "manifest_bytes": 7100,\n    "manifest_file": "frozen-config-materialization-source.json",\n    "manifest_sha256": "c9de17b7b4d5a545ea8cefdde4d1c91aed9b8c9807b030e6d1a2565ba9347f51",\n    "original_selected_total": 152,\n    "runner_bytes": 102190,\n    "runner_file": "replay_frozen_config_materialization.py",\n    "runner_sha256": "24f6a5404506b4ff7679b804fcc6d92ce86d852b22f4f2e2975e5742334f8200",\n    "scope": "Exact SQLite-repaired Config152 source assets preserved; no prior PASS inherited.",\n    "selected_patch_applications": 11,\n    "workflow_bytes": 6726,\n    "workflow_path": ".github/workflows/frozen-config-materialization.yml",\n    "workflow_sha256": "1b0c154e9bb89eaae8c0f7e923e62d78eb91205390f857902350a71c2381e0f0"\n  },\n  "before_graph": {\n    "normalized": {\n      "rows": 8797,\n      "sha256": "8477fabaa8349c64d89f703738662245d9f058b769e79e70bbd228e59472e159"\n    },\n    "source": {\n      "rows": 8797,\n      "sha256": "7a5dc99a885459a82173546f5411031000c491a56f457a7926258479dd6a39e7"\n    }\n  },\n  "changed_files": [\n    {\n      "after_bytes": 211733,\n      "after_mode": 436,\n      "after_sha256": "1540b905b5f133c05b04eb8ef13a78aa1aa0fd847b8ca50892e23c9d6f6da728",\n      "before_bytes": 211054,\n      "before_mode": 436,\n      "before_sha256": "59481f8da09bacb32786bc219316dca379d77b42fbe64de9976c74b8618545e7",\n      "path": "codex-rs/core/src/config/mod.rs"\n    },\n    {\n      "after_bytes": 211771,\n      "after_mode": 436,\n      "after_sha256": "fe6d42aebed3b12a9c82d2999c8258e6205dd2d600969abc7c762f0fcfa329ce",\n      "before_bytes": 211740,\n      "before_mode": 436,\n      "before_sha256": "16d2651bf5b68d10f0bdafb95b364080f22ee5c070e7a77a011f145c9c7d43a4",\n      "path": "codex-rs/core/src/session/mod.rs"\n    },\n    {\n      "after_bytes": 15142,\n      "after_mode": 436,\n      "after_sha256": "a08393912de0fa29c42bdd1c6a8806c96aa52a7e5eccc9d3400dd9ef94b86eed",\n      "before_bytes": null,\n      "before_mode": null,\n      "before_sha256": null,\n      "path": "codex-rs/core/src/session/pregrant_owner.rs"\n    },\n    {\n      "after_bytes": 19000,\n      "after_mode": 436,\n      "after_sha256": "897e9303407deb755a70dede0192bc0951a4cfb132c12395f1a1e50c83cb8cb7",\n      "before_bytes": null,\n      "before_mode": null,\n      "before_sha256": null,\n      "path": "codex-rs/core/src/session/pregrant_owner_tests.rs"\n    },\n    {\n      "after_bytes": 13351,\n      "after_mode": 436,\n      "after_sha256": "d4907b7875dfe4cce4501dbad5b88a4d60e09e085702574c77f62412a6ab145a",\n      "before_bytes": 12906,\n      "before_mode": 436,\n      "before_sha256": "763b127ca77e181b8d78c4a0e819278173644bfdfb35a73d41ff5c9aa438bac6",\n      "path": "codex-rs/core/src/session/retained_sampling_preparation.rs"\n    },\n    {\n      "after_bytes": 94105,\n      "after_mode": 436,\n      "after_sha256": "7185f121923081d127fee8bb019f4f4512ea4fbf736d4e887fba1f7670010466",\n      "before_bytes": 94084,\n      "before_mode": 436,\n      "before_sha256": "090da8de560a9326bdadd7995dc35afb639d1e94dab8f261aa7f8261b0c05e61",\n      "path": "codex-rs/core/src/session/session.rs"\n    },\n    {\n      "after_bytes": 16566,\n      "after_mode": 436,\n      "after_sha256": "9ebf51631fc05eef578c9914d0fe20da3ab3251272afd63cb03abd5b2823d41a",\n      "before_bytes": 16377,\n      "before_mode": 436,\n      "before_sha256": "5bbd6a42791cce988964e46831678ad7aa5829bd7f95a617a594b63f028c30fe",\n      "path": "codex-rs/core/src/session/step_settings.rs"\n    }\n  ],\n  "clippy": {\n    "original_argv_tail": [\n      "clippy",\n      "--locked",\n      "--offline",\n      "-p",\n      "codex-models-manager",\n      "-p",\n      "codex-core",\n      "--lib",\n      "--tests",\n      "--no-deps"\n    ],\n    "provider_argv_tail": [\n      "clippy",\n      "--locked",\n      "--offline",\n      "-p",\n      "codex-model-provider",\n      "--lib",\n      "--tests",\n      "--no-deps"\n    ],\n    "rules": "Existing workspace rules only; no -D warnings; independent actual exits and receipts",\n    "status": "NOT_RUN"\n  },\n  "licensing": {\n    "LICENSE_sha256": "d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc",\n    "NOTICE_sha256": "9d71575ecfd9a843fc1677b0efb08053c6ba9fd686a0de1a6f5382fd3c220915",\n    "scope": "Original upstream LICENSE and NOTICE preserved byte-for-byte for the upstream-derived patch. This does not select a license for the Learning Workbench repository."\n  },\n  "limitations": [\n    "Native generic Session and consumed Step lifetime are source mechanics only; common provider/history/window/Step producer and platform adapter remain unavailable.",\n    "SDK-captured Config replay and same native Config Arc binding cannot establish complete InputProof, sender authority or consent.",\n    "checked_start always refuses CompleteInputProofUnavailable; no CLI, AppServer, model, provider or sender is invoked by this gate.",\n    "Original135, auth13, repairedConfig4 and owner23 require their own exact source declarations, nonzero collection, behavior counts/names/footer and exits on this graph.",\n    "Both original two-package and independent provider Clippy commands retain their own actual receipts and exits; no inherited PASS or fallback.",\n    "The ordinary SDK fixture constructs runtime test values only; it is not a production source producer or native authority.",\n    "Original lock, pinned Rust setup and bounded profile remain unchanged; metadata normalization is not release/profile equivalence."\n  ],\n  "lock_sha256": "5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c",\n  "owner_candidate_receipt": {\n    "bytes": 4667,\n    "scope": "Source receipt only; no execution qualification.",\n    "sha256": "fb214c1409e032c14c15e0bb5bbce42ac0381d2deedfcedb64297bb7b3d9b8c1",\n    "version": "native-pregrant-owner-v4"\n  },\n  "patch": {\n    "bytes": 39095,\n    "file": "native-pregrant-owner.patch",\n    "sha256": "934c891a435cbd0b7fc6714037a47868ba11378fb9a17015647e379a94e39fa3"\n  },\n  "patch_asset_number": 15,\n  "production_boundary": {\n    "authoritative_model_version": null,\n    "complete_InputProof": "NOT_CLOSED",\n    "default_executor": null,\n    "joint_native_source_producer": "NOT_IMPLEMENTED",\n    "mechanical_native_owner": "SOURCE_CANDIDATE_TESTS_NOT_RUN",\n    "ordinary_active_task_registered": false,\n    "platform_rust_adapter": "NOT_IMPLEMENTED",\n    "production_runtime_services_constructed": false,\n    "qualification": "Unqualified",\n    "real_Agent": "NOT_RUN",\n    "registration": false,\n    "sender_available": false,\n    "status": "NOT_ADMITTED",\n    "test_fixture_is_production_authority": false\n  },\n  "profile": {\n    "CARGO_BUILD_JOBS": "2",\n    "CARGO_INCREMENTAL": "0",\n    "CARGO_PROFILE_DEV_DEBUG": "0",\n    "CARGO_PROFILE_DEV_INCREMENTAL": "false",\n    "CARGO_PROFILE_TEST_DEBUG": "0",\n    "CARGO_PROFILE_TEST_INCREMENTAL": "false",\n    "RUST_TEST_THREADS": "2",\n    "scope": "New bounded remote test profile, not original-profile or release CLI binary equivalence"\n  },\n  "schema_version": 1,\n  "selected_application_number": 12,\n  "source": {\n    "archive_root": "codex-a956835d020762cb2b570053af06f643a11c0ecc",\n    "archive_sha256": "351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927",\n    "archive_url": "https://codeload.github.com/openai/codex/tar.gz/a956835d020762cb2b570053af06f643a11c0ecc",\n    "commit": "a956835d020762cb2b570053af06f643a11c0ecc",\n    "release_tag": "rust-v0.160.0",\n    "repository": "https://github.com/openai/codex"\n  },\n  "spec": {\n    "sha256": "b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec",\n    "version": "3.0.15"\n  },\n  "status": "SOURCE_CANDIDATE_TESTS_NOT_RUN",\n  "test_metadata": {\n    "after_sha256": "436af5eb66ede70feba73b71a890a429722e35ae811657bd117d7e34bc751f38",\n    "after_version": "0.0.0",\n    "before_sha256": "e558c28aaf94c9f20c7d57224eb9509084e31110850aad24d04bef7811dc335d",\n    "before_version": "0.160.0",\n    "path": "codex-rs/Cargo.toml",\n    "scope": "Only local workspace package versions are normalized for the upstream original lock. This does not prove release binary or profile equivalence.",\n    "section": "workspace.package"\n  },\n  "test_selection": {\n    "scopes": [\n      {\n        "argv_tail": [\n          "test",\n          "--locked",\n          "--offline",\n          "-p",\n          "codex-core",\n          "--lib",\n          "session::pregrant_owner::tests::pregrant_owner_",\n          "--",\n          "--nocapture"\n        ],\n        "expected_passed": 23,\n        "filter": "session::pregrant_owner::tests::pregrant_owner_",\n        "label": "native-owner23",\n        "package": "codex-core",\n        "test_names": [\n          "session::pregrant_owner::tests::pregrant_owner_a_foreign_executed_checkpoint_cannot_replace_native_state",\n          "session::pregrant_owner::tests::pregrant_owner_cancel_rejects_existing_snapshots_and_new_retention",\n          "session::pregrant_owner::tests::pregrant_owner_checked_start_cannot_admit_complete_input_proof",\n          "session::pregrant_owner::tests::pregrant_owner_config_changed_since_capture_is_rejected_before_ownership",\n          "session::pregrant_owner::tests::pregrant_owner_drop_closes_state_even_when_a_snapshot_keeps_arcs_alive",\n          "session::pregrant_owner::tests::pregrant_owner_equal_config_value_cannot_replace_its_owned_arc",\n          "session::pregrant_owner::tests::pregrant_owner_equal_history_reset_invalidates_the_old_generation",\n          "session::pregrant_owner::tests::pregrant_owner_equal_instruction_reset_invalidates_the_old_generation",\n          "session::pregrant_owner::tests::pregrant_owner_equal_thread_ids_do_not_replace_the_actual_session",\n          "session::pregrant_owner::tests::pregrant_owner_equal_turn_config_value_cannot_replace_the_native_config_arc",\n          "session::pregrant_owner::tests::pregrant_owner_equal_turn_ids_do_not_replace_the_actual_step",\n          "session::pregrant_owner::tests::pregrant_owner_instruction_text_change_is_not_hidden_by_an_unchanged_token",\n          "session::pregrant_owner::tests::pregrant_owner_later_equal_settings_replacement_invalidates_the_snapshot",\n          "session::pregrant_owner::tests::pregrant_owner_missing_configured_model_cannot_borrow_the_steps_model",\n          "session::pregrant_owner::tests::pregrant_owner_noop_executed_recorder_refresh_revokes_the_old_checkpoint",\n          "session::pregrant_owner::tests::pregrant_owner_previous_started_turn_cannot_enter_pregrant",\n          "session::pregrant_owner::tests::pregrant_owner_reference_metadata_change_invalidates_unchanged_items",\n          "session::pregrant_owner::tests::pregrant_owner_rejects_a_foreign_config_capture_object",\n          "session::pregrant_owner::tests::pregrant_owner_retains_the_actual_session_step_and_config_arcs",\n          "session::pregrant_owner::tests::pregrant_owner_sdk_capture_replaces_caller_instruction_materials",\n          "session::pregrant_owner::tests::pregrant_owner_shutdown_after_retention_is_closed",\n          "session::pregrant_owner::tests::pregrant_owner_shutting_down_state_cannot_enter_pregrant",\n          "session::pregrant_owner::tests::pregrant_owner_step_must_be_the_turns_actual_settings_snapshot"\n        ]\n      }\n    ],\n    "selected_total": 23,\n    "source_candidates_only": true,\n    "status": "NOT_RUN"\n  }\n}\n')


def verify_inputs(bundle: Path) -> dict:
    baseline = verify_frozen_config_inputs(bundle)
    path = bundle / "native-pregrant-owner-source.json"
    require(path.is_file() and not path.is_symlink()
            and path.stat().st_size == NATIVE_OWNER_MANIFEST_BYTES
            and sha256(path) == NATIVE_OWNER_MANIFEST_SHA,
            "Fixed independent native owner manifest required")
    addition = load(path)
    require(type(addition) is dict and set(addition) == set(NATIVE_OWNER_CONTRACT)
            and addition == NATIVE_OWNER_CONTRACT,
            "Closed exact fifteenth-asset native owner contract required")
    binding = addition["baseline"]
    require(type(addition["schema_version"]) is int and addition["schema_version"] == 1
            and type(addition["patch_asset_number"]) is int and addition["patch_asset_number"] == 15
            and type(addition["selected_application_number"]) is int
            and addition["selected_application_number"] == 12
            and all(type(binding[key]) is int for key in [
                "manifest_bytes", "runner_bytes", "workflow_bytes", "existing_patch_asset_count",
                "selected_patch_applications", "original_selected_total",
            ]) and binding["existing_patch_asset_count"] == 14
            and binding["selected_patch_applications"] == 11
            and binding["original_selected_total"] == 152,
            "Fifteenth patch asset is only the twelfth selected application")
    for base_path, expected_bytes, expected_sha in [
        (bundle / binding["manifest_file"], binding["manifest_bytes"], binding["manifest_sha256"]),
        (bundle / binding["runner_file"], binding["runner_bytes"], binding["runner_sha256"]),
        (bundle.parents[1] / binding["workflow_path"], binding["workflow_bytes"], binding["workflow_sha256"]),
    ]:
        require(base_path.is_file() and not base_path.is_symlink()
                and base_path.stat().st_size == expected_bytes and sha256(base_path) == expected_sha,
                "Exact SQLite-repaired Config artifacts required")
    require(binding["manifest_sha256"] == FROZEN_CONFIG_MANIFEST_SHA
            and binding["runner_sha256"] == FROZEN_CONFIG_RUNNER_SHA
            and addition["source"] == baseline["source"]
            and addition["spec"] == baseline["spec"]
            and addition["before_graph"] == baseline["complete_source_graph"]
            and addition["profile"] == baseline["profile"]
            and addition["test_metadata"] == baseline["test_metadata"]
            and addition["lock_sha256"] == LOCK_SHA
            and addition["licensing"] == baseline["licensing"],
            "Owner slice must extend only the exact SQLite-repaired eleventh graph")
    for phase, expected_rows in [("before_graph", 8797), ("after_graph", 8799)]:
        graphs = addition[phase]
        require(type(graphs) is dict and set(graphs) == {"source", "normalized"},
                "Both complete native owner source graphs required")
        for graph in graphs.values():
            require(type(graph) is dict and set(graph) == {"rows", "sha256"}
                    and type(graph["rows"]) is int and graph["rows"] == expected_rows
                    and type(graph["sha256"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", graph["sha256"]) is not None,
                    "Typed complete before/after native owner graph required")
    patch = addition["patch"]
    require(type(patch) is dict and set(patch) == {"file", "bytes", "sha256"}
            and patch["file"] == "native-pregrant-owner.patch"
            and type(patch["bytes"]) is int and patch["bytes"] == 39095
            and patch["sha256"] == "934c891a435cbd0b7fc6714037a47868ba11378fb9a17015647e379a94e39fa3",
            "Exact fifteenth native owner patch asset required")
    patch_path = bundle / patch["file"]
    require(patch_path.is_file() and not patch_path.is_symlink()
            and patch_path.stat().st_size == patch["bytes"]
            and sha256(patch_path) == patch["sha256"],
            "Fixed combined native source/test patch required")
    rows = addition["changed_files"]
    require(type(rows) is list and len(rows) == 7
            and len({row["path"] for row in rows}) == 7,
            "Exactly five modified and two introduced native paths required")
    introduced = []
    for row in rows:
        require(type(row) is dict and set(row) == {
                    "path", "before_bytes", "before_sha256", "before_mode",
                    "after_bytes", "after_sha256", "after_mode",
                } and type(row["path"]) is str
                and type(row["after_bytes"]) is int and row["after_bytes"] > 0
                and type(row["after_mode"]) is int and row["after_mode"] == 0o664
                and type(row["after_sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", row["after_sha256"]) is not None,
                "Typed fixed native after bytes/fullmode required")
        if row["before_bytes"] is None:
            require(row["before_sha256"] is None and row["before_mode"] is None,
                    "Introduced native paths require absent before facts")
            introduced.append(row["path"])
        else:
            require(type(row["before_bytes"]) is int and row["before_bytes"] > 0
                    and type(row["before_mode"]) is int and row["before_mode"] == 0o664
                    and type(row["before_sha256"]) is str
                    and re.fullmatch(r"[0-9a-f]{64}", row["before_sha256"]) is not None,
                    "Typed fixed native before bytes/fullmode required")
    require(sorted(introduced) == [
                "codex-rs/core/src/session/pregrant_owner.rs",
                "codex-rs/core/src/session/pregrant_owner_tests.rs",
            ], "Only owner and its test child may be introduced")
    selected = addition["test_selection"]
    require(type(selected) is dict and set(selected) == {
                "scopes", "selected_total", "source_candidates_only", "status",
            } and type(selected["selected_total"]) is int and selected["selected_total"] == 23
            and selected["source_candidates_only"] is True and selected["status"] == "NOT_RUN"
            and type(selected["scopes"]) is list and len(selected["scopes"]) == 1,
            "Independent nonzero native owner23 source candidates required")
    scope = selected["scopes"][0]
    require(type(scope) is dict and set(scope) == {
                "label", "package", "filter", "expected_passed", "test_names", "argv_tail",
            } and scope["label"] == "native-owner23" and scope["package"] == "codex-core"
            and scope["filter"] == NATIVE_OWNER_PREFIX
            and type(scope["expected_passed"]) is int and scope["expected_passed"] == 23
            and type(scope["test_names"]) is list
            and len(scope["test_names"]) == len(set(scope["test_names"])) == 23
            and scope["test_names"] == sorted(scope["test_names"])
            and all(type(name) is str and name.startswith(NATIVE_OWNER_PREFIX)
                    for name in scope["test_names"])
            and scope["argv_tail"] == [
                "test", "--locked", "--offline", "-p", "codex-core",
                "--lib", NATIVE_OWNER_PREFIX, "--", "--nocapture",
            ], "Actual private owner namespace and exact23 behavior tests required")
    require(addition["clippy"] == baseline["frozen_config_materialization"]["clippy"]
            and addition["clippy"]["original_argv_tail"] == CLIPPY_ARGV
            and addition["clippy"]["provider_argv_tail"] == STATIC_AUTH_CLIPPY_ARGV
            and addition["clippy"]["status"] == "NOT_RUN",
            "Original two-package and independent provider Clippy commands remain exact")
    boundary = addition["production_boundary"]
    require(boundary["registration"] is False and boundary["default_executor"] is None
            and boundary["qualification"] == "Unqualified"
            and boundary["authoritative_model_version"] is None
            and boundary["complete_InputProof"] == "NOT_CLOSED"
            and boundary["joint_native_source_producer"] == "NOT_IMPLEMENTED"
            and boundary["platform_rust_adapter"] == "NOT_IMPLEMENTED"
            and all(boundary[key] is False for key in [
                "sender_available", "production_runtime_services_constructed",
                "ordinary_active_task_registered", "test_fixture_is_production_authority",
            ]) and boundary["real_Agent"] == "NOT_RUN" and boundary["status"] == "NOT_ADMITTED",
            "Mechanical native owner cannot admit production or complete InputProof")
    manifest = dict(baseline)
    manifest["frozen_config_baseline"] = baseline
    manifest["native_pregrant_owner"] = addition
    manifest["complete_source_graph"] = addition["after_graph"]
    manifest["test_selection"] = dict(baseline["test_selection"])
    manifest["test_selection"]["scopes"] = baseline["test_selection"]["scopes"] + selected["scopes"]
    manifest["test_selection"]["selected_total"] = 175
    return manifest


def native_owner_source_names(root: Path) -> list[list[str]]:
    parent = (root / "codex-rs/core/src/session/mod.rs").read_text()
    require(parent.count("pub(crate) mod pregrant_owner;") == 1,
            "Actual private SDK owner module declaration required")
    owner = (root / "codex-rs/core/src/session/pregrant_owner.rs").read_text()
    declaration = '#[cfg(test)]\n#[path = "pregrant_owner_tests.rs"]\nmod tests;'
    require(owner.count(declaration) == 1, "Actual native owner test child required")
    child = (root / "codex-rs/core/src/session/pregrant_owner_tests.rs").read_text()
    names = re.findall(r"#\[tokio::test\]\s+async fn (pregrant_owner_\w+)\(", child)
    require(len(names) == len(set(names)) == 23,
            "Unique exact23 native owner source declarations required")
    return [sorted("session::pregrant_owner::tests::" + name for name in names)]


def prepare(args: argparse.Namespace, output: Path, report: dict, manifest: dict,
            bundle: Path, recorder: Recorder) -> int:
    baseline = manifest["frozen_config_baseline"]
    result = prepare_frozen_config(args, output, report, baseline, bundle, recorder)
    if result != 0:
        return result
    addition = manifest["native_pregrant_owner"]
    source, tests = output / "source", output / "test-source"
    source_before = verify_prepared(source, baseline, "source")
    test_before = verify_prepared(tests, baseline, "normalized")
    write_json(output / "config-source-before-files.json", source_before)
    write_json(output / "config-test-before-files.json", test_before)
    applications = []
    for phase, root, before in [
        ("source", source, source_before),
        ("normalized", tests, test_before),
    ]:
        graph = addition["before_graph"][phase]
        require(len(before) == graph["rows"] and graph_digest(before) == graph["sha256"],
                "Exact repaired Config graph required before twelfth owner application")
        for row in addition["changed_files"]:
            target = root / row["path"]
            if row["before_bytes"] is None:
                require(row["path"] not in before and not target.exists() and not target.is_symlink(),
                        "New native owner path must be actually absent")
            else:
                require(before.get(row["path"]) == {
                            "kind": "file", "bytes": row["before_bytes"],
                            "sha256": row["before_sha256"], "mode": row["before_mode"],
                        }, "Exact native before bytes/fullmode required")
        for suffix, flags in [("check", ["--check"]), ("apply", [])]:
            command = recorder.run(
                "native-owner-" + phase + "-" + suffix,
                ["git", "apply", *flags, str(bundle / addition["patch"]["file"])], root,
            )
            if command["exit_code"] != 0:
                return positive_exit(command["exit_code"])
        after = verify_prepared(root, manifest, phase)
        changed = sorted(row["path"] for row in addition["changed_files"])
        require(differences(before, after) == changed,
                "Owner patch exceeded exactly seven native source paths")
        for row in addition["changed_files"]:
            require(after[row["path"]] == {
                        "kind": "file", "bytes": row["after_bytes"],
                        "sha256": row["after_sha256"], "mode": row["after_mode"],
                    }, "Exact native after bytes/fullmode required")
        applications.append({
            "phase": phase, "changed_paths": changed,
            "before_graph": graph, "after_graph": addition["after_graph"][phase],
            "exact_bytes_fullmodes_and_graph": True,
        })
    source_files = verify_prepared(source, manifest, "source")
    test_files = verify_prepared(tests, manifest, "normalized")
    require(differences(source_files, test_files) == [manifest["test_metadata"]["path"]],
            "Only original test metadata normalization differs between final owner graphs")
    require(source_test_names(tests) == [
                scope["test_names"] for scope in manifest["test_selection"]["scopes"][:11]
            ], "Original135 candidates remain exact on the new owner graph")
    require(static_auth_source_names(tests) == [
                scope["test_names"]
                for scope in manifest["effective_static_auth"]["test_selection"]["scopes"]
            ], "Independent auth13 candidates remain exact on the new owner graph")
    require(frozen_config_source_names(tests) == [
                scope["test_names"]
                for scope in manifest["frozen_config_materialization"]["test_selection"]["scopes"]
            ], "RepairedConfig4 candidates remain exact on the new owner graph")
    require(native_owner_source_names(tests) == [
                scope["test_names"] for scope in addition["test_selection"]["scopes"]
            ], "Actual23 private owner source names must match the fixed manifest")
    write_json(output / "source-before-files.json", source_files)
    write_json(output / "test-before-files.json", test_files)
    report["source_graph"] = manifest["complete_source_graph"]
    report["native_owner_application"] = {
        "patch_asset_number": 15, "selected_application_number": 12,
        "applications": applications, "source_candidates_only": True,
        "behavior_tests": "NOT_RUN", "production": "NOT_ADMITTED",
    }
    report["native_owner_source_names_checked"] = True
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
                collections = []
                if scope["label"] == "native39":
                    collections = [
                        ("native", scope["filter"], scope["test_names"], 39),
                        ("sampling-child", SAMPLING_CHILD_PREFIX,
                         [n for n in scope["test_names"] if n.startswith(SAMPLING_CHILD_PREFIX)], 10),
                        ("instruction-child", INSTRUCTION_CHILD_PREFIX,
                         [n for n in scope["test_names"] if n.startswith(INSTRUCTION_CHILD_PREFIX)], 7),
                    ]
                elif scope["label"] == "step-settings7":
                    collections = [("ordinary", scope["filter"], scope["test_names"], 7)]
                elif scope["label"] == "applied-instructions5":
                    collections = [("applied-instructions", APPLIED_INSTRUCTIONS_PREFIX,
                                    scope["test_names"], 5)]
                elif scope["label"] == "executed-state12":
                    collections = [("executed-state", EXECUTED_PREFIX, scope["test_names"], 12)]
                elif scope["label"] == "executed-direct3":
                    collections = [("executed-direct", EXECUTED_DIRECT_PREFIX, scope["test_names"], 3)]
                elif scope["label"] == "executed-metadata36":
                    collections = [("executed-metadata", EXECUTED_METADATA_PREFIX, scope["test_names"], 36)]
                elif scope["label"] in {"sampling-executed6", "sampling-attachment2", "direct-checkpoint6"}:
                    collections = [(scope["label"], scope["filter"], scope["test_names"], scope["expected_passed"])]
                if scope["label"] in {"effective-auth8", "effective-provider5", "frozen-config4", "native-owner23"}:
                    collections = [(scope["label"], scope["filter"], scope["test_names"], scope["expected_passed"])]
                for label, selector, expected_names, expected_count in collections:
                    prelaunch_health(output, report, label + "-list")
                    argv = [str(bins["cargo"]), "test", "--locked", "--offline", "-p", scope["package"],
                            "--lib", selector, "--", "--list"]
                    row = recorder.run(label + "-test-list", argv, tests / "codex-rs", environment, task)
                    listed = (recorder.receipts / (label + "-test-list") / "stdout.log").read_text(errors="replace")
                    names = sorted(re.findall(r"(?m)^(\S+): test$", listed))
                    matches = (expected_count > 0 and len(expected_names) == expected_count
                               and names == expected_names
                               and len(names) == len(set(names)) == expected_count)
                    if label == "native":
                        for prefix, count in [(SAMPLING_CHILD_PREFIX, 10), (INSTRUCTION_CHILD_PREFIX, 7)]:
                            actual_children = [n for n in names if n.startswith(prefix)]
                            expected_children = [n for n in expected_names if n.startswith(prefix)]
                            matches = (matches and actual_children == expected_children
                                       and len(actual_children) == len(set(actual_children)) == count)
                    report[label + "_test_list"] = {
                        "actual_exit": row["exit_code"], "test_names": names,
                        "expected_nonzero_count": expected_count,
                        "matches_fixed_source_candidates": matches,
                        "scope": "Collection only; never behavior PASS",
                    }
                    if row["exit_code"] != 0 or not matches:
                        result = positive_exit(row["exit_code"]) or 1
                        break
                if result:
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
            report["tests"].update(selection_groups(report["tests"]["scopes"], manifest))
            report["tests"]["status"] = "PASS" if (
                result == 0 and report["tests"]["selected_total_passed"] == 175
                and all(report["tests"][label]["status"] == "PASS"
                        for label in ["original135", "effective_static_auth13", "frozen_config4", "native_owner23"])
            ) else "FAIL"
            if report["tests"]["original135"]["status"] == "PASS":
                prelaunch_health(output, report, "clippy")
                row = recorder.run("cargo-clippy", [str(bins["cargo"])] + CLIPPY_ARGV,
                                   tests / "codex-rs", environment, task)
                clippy_result = positive_exit(row["exit_code"])
                result = result or clippy_result
                report["clippy"] = {"status": "PASS" if clippy_result == 0 else "FAIL", "actual_cargo_exit": row["exit_code"],
                                     "scope": "Only selected two packages library/tests, existing workspace rules, no -D warnings"}
            else:
                result = result or 1
                report["clippy"].update(reason="Original135 selection did not PASS; no fallback or retry")
            if report["tests"]["effective_static_auth13"]["status"] == "PASS":
                prelaunch_health(output, report, "effective-static-auth-clippy")
                row = recorder.run("cargo-effective-static-auth-clippy",
                                   [str(bins["cargo"])] + STATIC_AUTH_CLIPPY_ARGV,
                                   tests / "codex-rs", environment, task)
                provider_clippy_result = positive_exit(row["exit_code"])
                result = result or provider_clippy_result
                report["effective_static_auth_clippy"] = {
                    "status": "PASS" if provider_clippy_result == 0 else "FAIL",
                    "actual_cargo_exit": row["exit_code"],
                    "scope": "Only model-provider library/tests, existing workspace rules, no -D warnings",
                }
            else:
                report["effective_static_auth_clippy"].update(
                    reason="Independent auth13 did not PASS; no fallback or retry")
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
              "manifest_sha256": sha256(bundle / "native-pregrant-owner-source.json"), "runner_sha256": sha256(Path(__file__)),
              "frozen_config_manifest_sha256": FROZEN_CONFIG_MANIFEST_SHA, "frozen_config_runner_sha256": FROZEN_CONFIG_RUNNER_SHA,
              "static_auth_manifest_sha256": STATIC_AUTH_MANIFEST_SHA, "static_auth_runner_sha256": STATIC_AUTH_RUNNER_SHA,
              "legacy_manifest_sha256": LEGACY_MANIFEST_SHA, "legacy_runner_sha256": LEGACY_RUNNER_SHA,
              "commands": [], "tests": {"status": "NOT_RUN", "tests_executed": 0,
                                        "original135": {"status": "NOT_RUN", "selected_total_expected": 135},
                                        "effective_static_auth13": {"status": "NOT_RUN", "selected_total_expected": 13},
                                        "frozen_config4": {"status": "NOT_RUN", "selected_total_expected": 4},
                                         "native_owner23": {"status": "NOT_RUN", "selected_total_expected": 23}},
              "clippy": {"status": "NOT_RUN", "actual_cargo_exit": None},
              "effective_static_auth_clippy": {"status": "NOT_RUN", "actual_cargo_exit": None},
              "production": "NOT_ADMITTED",
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
                      "tests": report["tests"], "clippy": report["clippy"],
                      "effective_static_auth_clippy": report["effective_static_auth_clippy"], "production": "NOT_ADMITTED",
                      "report": str(output / "report.json")}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
