# Finite independent early CI readback

Assessment: **PASS_LIMITED_EIGHT_COMPLETED_JOB_READBACK**. Public source `079a008cf88b37e4517cb391503a1e7393ccf374`; PRODUCT_DESIGN v3.0.15 SHA-256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec` binds exactly in both spec-contracts original logs. This does not accept either whole run, whole CI, M6.3, or model behavior.

Only the explicitly delegated 39 original files were opened: 8 completed-job command/receipt/stdout/stderr sets, snapshot14, and its three API command/receipt pairs. No network/API, collector, dispatch, rerun, cancel, code, progress, or remote mutation was performed. Original API payloads and all four browser/integration logs were not opened.

Snapshot14 observed `2026-10-07T14:08:38.197663+00:00`: original push `37632652743` and pull_request `37632662238`, attempt 1, both `in_progress` with no conclusion. This is only the recorded early observation.

| Event | Job / ID | Original stdout bytes | Actual result, kept per job |
|---|---|---:|---|
| push | backend / 112830648507 | 44701 | Ruff PASS; mypy 295 source files; pytest 1114 passed, 3 warnings (77.81s) |
| push | frontend / 112830648865 | 60775 | Vitest 1421 tests in 167 files passed; build 879 modules; npm audit reports 4 vulnerabilities (3 low, 1 high), chunk warning >500 kB |
| push | spec-contracts / 112830648905 | 39638 | verify-spec PASS, M0_structural_baseline_only; pytest 962 passed, 2 warnings (576.45s) |
| push | security-publication / 112830649006 | 21008 | Scanner PASS, 23175 staged/tracked files; manual provenance review remains required; numeric findings count not printed |
| pull_request | backend / 112830674907 | 45258 | Ruff PASS; mypy 295 source files; pytest 1114 passed, 3 warnings (76.66s) |
| pull_request | frontend / 112830674842 | 64779 | Vitest 1421 tests in 167 files passed; build 879 modules; npm audit reports 4 vulnerabilities (3 low, 1 high), chunk warning >500 kB |
| pull_request | spec-contracts / 112830674580 | 40389 | verify-spec PASS, M0_structural_baseline_only; pytest 962 passed, 2 warnings (575.52s) |
| pull_request | security-publication / 112830674820 | 22147 | Scanner PASS, 23175 staged/tracked files; manual provenance review remains required; numeric findings count not printed |

All eight original captures have exit code 0, empty stderr, and stdout/stderr sizes plus SHA-256 exactly matching their original receipts. Recorded command/job identities match snapshot14. Full captured stdout was decoded and read; all eight contain their final cleanup tail and no GitHub `##[error]` annotation. These checks bind the captured bytes, not an unseen CI working directory.

Push checkout is the public source head. Each pull_request job instead checks out `refs/remotes/pull/56/merge` at `e9eb82d41dd87649be6c8090c35b5052ccb1319c`; the original merge line binds expected head `079a008cf88b37e4517cb391503a1e7393ccf374` into base `e2877101d9c2bda0f793a460db63ef496350c6b4`. This is the recorded PR merge checkout, not a wrong-source finding.

Backend warnings are the Starlette/httpx deprecation, anyio BlockingPortal alias deprecation, and a Pydantic serializer warning from the synthetic negative typed-interrupt test (boolean supplied where thread_id expects str). Spec warnings are the first two deprecations. Frontend numeric warning count is not reported; preserve the npm vulnerability notice, Vite large-chunk warning, and jsdom performance advisory. No dependency or warning repair is in this read-only task.

Both verify-spec results retain `scope=M0_structural_baseline_only`, `product_acceptance=NOT_RUN`, `real_codex=NOT_RUN`, `real_provider=NOT_RUN`, `learning_effectiveness=NOT_RUN`, and `publication=NOT_CHECKED`. Their structural counts are individually 6 embedded files, 82 generated artifacts, 54 models, 38 requirements, 147 routes, 53 SQL tables including FTS, 33 target scenarios, and 27 tasks. Package receipt bodies are omitted.

**CI working before/after input maps remain NOT_CAPTURED.** Neither snapshot14, matching original log hashes, nor scanner PASS proves those maps or input completeness. The original-source rehash only establishes review-time stability of the selected evidence files.

The SAFE-CANDIDATE manifest selects 120 exact original safe lines across eight separate candidates, with original line locators and hashes. Full original logs, API material, package/profile receipt bodies, environment lines, absolute runner paths, and private payloads are excluded. These local candidates remain NOT_UPLOADED and require the root independent review before any public use.

The later 12-job complete CI log review must be performed separately when all original jobs and logs are available. This early eight-job review cannot substitute for it.
