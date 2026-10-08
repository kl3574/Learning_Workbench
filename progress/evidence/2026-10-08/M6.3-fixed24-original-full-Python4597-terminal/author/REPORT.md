# Fixed 24ac original complete Python gate — actual terminal

Fixed runtime HEAD: `24ac44bc627d33f26199c89b6150897da6ea1279`. This task created an isolated owned checkout, fresh locked/offline venv, owned fixed Node/tsc dependency copies and fresh private TMPDIR. Source inventory excludes only literal `progress/`; all 1579 engineering files have Git/index/live blob SHA256/bytes/Git modes/full POSIX modes bound before/after. Fresh checkout's only full-mode difference (replay_core_producer.py 0775→0755) was recorded and aligned on this owned tree before inventory; canonical was never changed by this task.

Only original full test argv: `uv run --frozen --offline --no-sync pytest`. No added filter, retry, fallback, collection-only substitute or assertion/numeric-guard change. Runtime override is only TMPDIR `$HOME/.cache/learning-workbench-acceptance/m63-final-auth-24ac-complete-python-private-temp-oct08/python`; UV_LINK_MODE absent, HOME/CODEX_HOME not explicitly read or overridden. One detached recorder owned uv and the directly observed pytest child; it waited for the actual child terminal before capturing the receipt and after-map. Launcher actual0 means started only.

Actual pytest native exit: **0**. Actual collection: **[4599]**. Exact terminal footer:

```
=========== 4597 passed, 2 skipped, 3 warnings in 3215.47s (0:53:35) ===========
```

Exact skip report (each remains SKIP, never numeric PASS):

```
SKIPPED [1] tests/integration/test_authoring_numeric_runtime.py:46: BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained
SKIPPED [1] tests/integration/test_restore_numeric_actual_runtime.py:42: BLOCKED_ENVIRONMENT: actual sealed Restore evaluator did not return a numeric PASS; no fallback
```

Full tracked-source before/after/current equality: **True**; runtime Git clean: **True**. Current canonical engineering bytes/modes/index remain equal to the captured fixed reference: **False** (its progress HEAD may advance independently). Recorder metadata errors: `[]`. All known owned recorder/uv/pytest identities are inactive; exact suite/recorder log files have no holder. Logs and all actual command/receipt files are retained privately.

Original full Python Ruff, Mypy and verify-spec results: `{'ruff': 0, 'mypy': 0, 'verify-spec': 0}`. Mypy actual output covers 295 source files; verify-spec is M0 structural baseline only, with product acceptance and real Codex NOT_RUN. Static 1579 before/after maps are exact. Dependency terminal readback binds owned Node files/modes/links and venv package METADATA.

Canonical later authorized tooling delta from fixed24: `['scripts/codex-turn/README.md', 'scripts/codex-turn/core-producer-source.json', 'scripts/codex-turn/core-producer.patch', 'scripts/codex-turn/replay_core_producer.py']`; current canonical's own HEAD/index/live exact: **True**. These later tooling bytes are outside this gate. This test result does not claim a complete-suite run of the later canonical source HEAD.

No frontend or native gate was rerun. No model, real user key/profile, actual CLI/AppServer, host probe or remote action was performed by this task. These test results do not implement or admit the genuine Python↔Rust request/handle bridge, complete production InputProof, same-auth facts or executor qualification. All prior FAIL, interrupted, skip and accepted historical packets remain separate and unmodified. This gate applies only to fixed 24ac source and the recorded owned environment.
