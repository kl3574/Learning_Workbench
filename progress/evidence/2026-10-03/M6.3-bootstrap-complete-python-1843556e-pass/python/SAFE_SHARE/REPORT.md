# Complete Python revalidation at 1843556e

Fixed detached source: `1843556e1c01b48e60082969e78d2a82b3848b45`. The reviewed legacy Review backup test correction triggered this one complete run; no selection, fixture retry, timeout changes, production changes, or source edits occurred during execution.

Actual command:

```text
uv run --frozen --no-sync pytest tests/contract tests/unit tests/integration --tb=short --basetemp=$HOME/.cache/lw-m63-1843-oct04/pytest -o cache_dir=$HOME/.cache/learning-workbench-acceptance/m63-bootstrap-full-python-1843556e-oct04/pytest-cache
```

Result: **3688 collected; 3686 PASS, 0 FAIL, 0 ERROR, 2 environment SKIP, 2 existing dependency warnings; exit 0.** Pytest reports 2199.36 seconds (36:39); the runner monotonic interval is 2200.257 seconds. Raw receipt retains UTC start `2026-10-03T16:26:50.338110+00:00` and finish `2026-10-03T17:03:30.809743+00:00`.

Both physical numeric limitations remain explicit: Authoring sealed runtime did not execute its calculator; Restore sealed evaluator did not return a numeric PASS. Tests retained their existing BLOCKED_ENVIRONMENT skips without a fallback. The two warnings are the existing Starlette/httpx and AnyIO BlockingPortal deprecations. No dependency synchronization or installation occurred.

All **1381 tracked nonprogress engineering inputs** were compared byte-for-byte against blobs read from the fixed Git commit before and after pytest. Both full manifests are identical, no untracked engineering probes were present, and the source worktree remains clean. `progress/`, ignored installed dependency trees, runtime data and caches are outside that engineering-input count. The exact private runner bytes and SHA are included in each manifest. Existing read-only dependency symlinks were reused. Process-local settings were only the new short TMPDIR, PYTHONDONTWRITEBYTECODE=1 and empty PYTEST_ADDOPTS; no global environment was modified. Sole PRODUCT_DESIGN v3.0.14 SHA remains `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`.

The original full gate at `dcfda8c270dff3e6db75011c50ffa7d6f5826512` remains a separately sealed **FAIL**: 3683 PASS, 1 FAIL, 2 setup ERROR, 2 environment SKIP, exit 1. Its original log and report hashes were read back unchanged. The old backup assertion was separately corrected and reviewed; both earlier setup-error files pass in this new complete run. Their original causes remain **UNKNOWN**. This PASS neither explains those causes nor alters the original UTC/monotonic discrepancy, failed traces or safe metadata receipt.

This is the complete Python contract/unit/integration scope requested by root, not a new Web/native run, a physical numeric PASS, overall Broker acceptance, or model/account/tool acceptance. Existing controlled peers were used by the tests; no extra CLI/control/model/vendor/account/tool invocation or system probe was added.

Explicit share candidates are only listed logs, receipts, manifests, report and runner/sealing scripts. Raw DBs, backup ZIPs, keys, credentials, basetemp and pytest-cache material are excluded. Candidate transformation is exact `$HOME` prefix to `$HOME` only; originals remain intact.
