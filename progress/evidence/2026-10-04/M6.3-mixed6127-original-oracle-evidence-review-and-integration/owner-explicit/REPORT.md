# M6.3 interrupt and approved-operation coexistence regression

Fixed `6127acdf2964efa27da639f17eccd47779f967a8` adds one integration test file (239 lines) above `ee76a13d22728e31880ef1ac223b5f3572832893`. Production source, earlier tests, specification, canonical worktree, and earlier evidence are unchanged. Both commits contain M6.3: initial `0999696b97324d6d5da95e69deffdb4b3fc68adc`, then the narrow test-oracle correction `6127acdf2964efa27da639f17eccd47779f967a8`.

Sole PRODUCT_DESIGN.md v3.0.15 SHA is `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`, byte-identical to the previously fully read specification. The scenarios apply its actual operation/interrupt/history contract in sections 20.17.4, 20.17.5, and 20.17.7.

The new file is `tests/integration/test_codex_interrupt_operation_coexistence.py` in `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-interrupt-operation-coexist-owner-oct04`. It uses actual local HTTP/owners, callback_turn/consent_case, real prepared requests from the trusted Provider owner, and the explicitly registered LiteralOperationProfile memory interpreter. It does not create owner events or forge SQL history. The reused interpreter_events observer targets only the test thread and one execute code object; it never replaces licensed code or inspects system state.

Three actual workflows expand into five cases:

1. Approve and actually complete the memory operation, then interrupt the still-active turn. Full original decision ACK bytes survive the interrupt and later terminal state; operation revision/result remain completed, current Job projection is independently checked against safe turn control, model response remains retained, and no second model request occurs.
2. Pending and approved-but-not-executed variants: interrupt before execute; the real owner refuses execution, the interpreter is observed zero times, the first model response remains the only transport request, close facts are preserved, and any original decision/interrupt ACK replays unchanged.
3. Interrupt and ordinary Jobs-cancel variants: stop the first queued turn with zero model requests, then make a new HTTP preparation/proposal/grant/start in the same session from its current revision. A new memory operation succeeds once. Reading the old terminal turn and replaying its original stop while the new turn is active leaves the complete current session unchanged; the new turn subsequently completes normally.

## Original failure and correction

The first fixed source (`0999696b`) produced **1 FAIL / 4 PASS**, exit 1 in 16.60 seconds. Its failed assertion required full GenericApprovalView equality across interrupt. The only reported difference was dynamic `job_revision: 3 -> 4`; original complete decision ACK equality had already passed. Section 20.17.4 explicitly separates current Job revision from immutable operation-decision facts. This was a test-oracle error, not a confirmed production defect.

The correction changes only that new test: all original operation facts remain compared, while the view's Job and Job revision must equal current independently read safe turn control. No production code was repaired or weakened. The original source, command, raw log, full Git maps, and exit receipt remain in `initial-five/` and the first commit. Raw failure log SHA: `9086df3af23ae344d2ea6fd0d59f09eee8ce008f5d9ffc78b9c093f269bd8aca`. The raw failure log stays private because pytest failure context may include fixture authentication representation; only its hash and this fixed summary are candidates.

## Fixed limited gate

- New file alone: 5 PASS, exit 0, 16.75 seconds.
- New file plus existing test_codex_approved_operation_http.py and test_codex_turn_interrupt_http.py: **9 PASS**, exit 0, 28.76 seconds. Started `2026-10-04T12:43:54.071565+00:00`; ended `2026-10-04T12:44:22.829726+00:00`.
- New-file Ruff: exit 0, All checks passed.
- git diff --check from the fixed base: exit 0.
- Each invocation preserved complete 1465 nonprogress Git input maps before and after, exactly equal, all actual blobs matching fixed Git and clean status. Separate per-run source copies and runner/command/source hashes are in the evidence receipts.
- Final nine-case raw success log SHA: `bc216f3b144b26919c0f0f3cf84ccf787c4685c64bac9fdd8b2d7e1f3f71f493`.

Commands use `uv run --frozen --no-sync`, the existing read-only dependency symlink, and an independent private TMPDIR/basetemp. The gate retained two existing dependency deprecation warnings. No dependencies were installed. No full UI, Chrome, full Python, CLI, external model/provider, tool process, network service, database security probe, or system diagnostic was run for this subtask. These five tests do not upgrade whole-M6.3 or real-runtime acceptance.

The exact `publication-candidates/allowlist.json` is candidates-only for root review. It includes the new test, runner, report/binding, final gate success logs/commands/receipts/full maps, and initial failure command/receipt/full maps/source (not its raw failure log). Text transformation is solely `<LOCAL_HOME>` to `<LOCAL_HOME>`, with hashes and replacement counts. No test data directory, DB, secrets, profile, cache, or TMP contents are included.
