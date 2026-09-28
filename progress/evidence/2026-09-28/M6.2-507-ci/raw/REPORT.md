# Exact-head remote CI readback: 507ac58

**Final remote outcome: push SUCCESS; PR FAILURE due to two actual browser failures.** The exact package installation blocker is resolved in these actual runs. This is not an all-green PR, successful numeric-calculator execution, hosted-model acceptance, or whole-platform acceptance.

| Identity | Push | Pull request |
|---|---|---|
| Run | [36368224612](https://github.com/kl3574/Learning_Workbench/actions/runs/36368224612) | [36368226913](https://github.com/kl3574/Learning_Workbench/actions/runs/36368226913) |
| Attempt | 1 | 1 |
| Run head SHA | `507ac58b17e4a68b4e0f852cc6a64b535cf3235c` | `507ac58b17e4a68b4e0f852cc6a64b535cf3235c` |
| Actual checkout, all six original job logs | `507ac58b17e4a68b4e0f852cc6a64b535cf3235c` | `f74cd7a8f81a8b51abf06ae12fb62a51da3bb99d` |
| Final outcome | completed / success, 6 success jobs | completed / failure, 5 success jobs + browser failure |

The actual PR commit has parents `2cf5caa3f966f919997c37b64d0bbf0e332438df` and the stated head. Both actual checkouts have Git tree `d81e65cd659919496247e75ae8eeefb53801d5f4`, verified against GitHub commit API originals and the local fixed Git tree. They are distinct commits with identical tracked content. The PR identity snapshot is draft/open PR55; this task did not change its state, merge or publish anything.

## Installation and sandbox facts

Each event's backend, integration and browser job used Ubuntu 26.04.1, runner image `ubuntu-26.04` version `20260920.143.1`. All **six** actual install steps succeeded. All six complete raw logs contain matching dpkg-query rows:

- `bubblewrap 0.11.1-1ubuntu0.3`
- `apparmor 5.0.2-0ubuntu1~26.04.1`
- `libapparmor1:amd64 5.0.2-0ubuntu1~26.04.1`
- `libseccomp2:amd64 2.6.0-2ubuntu5`

The unchanged workflow also checked that the expected AppArmor profile file existed and ran `bwrap --version`. Both backend jobs actually executed the fixed synthetic **document** runtime probe, which reported PASS. That document-probe result is not a numeric-runtime verdict. Other jobs used the specified Ubuntu 24.04 image.

The workflow was read from GitHub at **both actual checkout commits**, not inferred from a branch name. Both copies are byte-identical (5618 bytes, Git blob `b370cea4fa114da560c13273488db2c167706b6e`, SHA256 `bb3d318269b3d6a6f49cfc69bd633adf22632fefae3b83da707433da77498ffe`), with exactly three `.3` pins. Originals, API acquisition receipts and decode/hash verification are under `source/`.

This establishes actual APT resolution and execution of subsequent checks after the earlier `.1` installation failure. It does **not** change ADR 0007's explicit security qualification: `.3` is not a fix for CVE-2026-87766, and current application-specific constraints do not prove general bubblewrap immunity. The exact published ADR is separately pinned in `source/ADR-0007.md` and `source/ADR-pin.json`. No sandbox flag, dependency looseness or test expectation was changed by this readback task.

## Actual product/static checks

| Job | Push actual result | PR actual result |
|---|---|---|
| backend | 731 passed, 2 dependency warnings, 23.28s; Ruff PASS, mypy 196 files PASS, document probe PASS | 731 passed, 2 dependency warnings, 33.01s; same static/probe success |
| integration | 1472 passed, **1 skipped**, 2 dependency warnings, 1632.11s | 1472 passed, **1 skipped**, 2 dependency warnings, 1657.62s |
| spec-contracts | 603 passed, 2 dependency warnings, 359.72s; actual spec verification PASS | 603 passed, 2 dependency warnings, 343.25s; actual spec verification PASS |
| frontend | 77 test files / 453 tests passed; lint, typecheck and build job steps success | 77 test files / 453 tests passed; same step success |
| security-publication | 11460 staged/tracked files scanned; PASS | 11460 staged/tracked files scanned; PASS |
| browser | **101 passed**, 13.2m, 1 worker | **99 passed / 2 failed**, 18.8m, 1 worker |

These suites are reported separately; their counts are not added into a unique-test total. Dependency warnings are the original Starlette/httpx/AnyIO deprecations, not hidden failures. The publication scanner itself says manual provenance review remains required.

Both integration logs explicitly report the same skip at `tests/integration/test_authoring_numeric_runtime.py:46`: `BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained`. A green CI job with this original skip must not be represented as successful sealed arithmetic execution. No skip or expected result was introduced here.

## Remaining real browser failures

The PR's failure log is retained unchanged with SHA256 `3c1d436f4bc5953c99fb20e83486dda5ba771e65424a996ba249ba62b8f877d5`:

1. `authoring-groups.spec.ts:294`: lost prepare ACK recovery reached successful identical replay, then the exact read-details button did not appear within the existing 10-second click window (`readPrepared:48`, caller 322). Screenshot: acknowledged command, empty list, disabled controls. Root cause remains UNKNOWN; a pending post-replay list/consumption is consistent with source and screenshot but not uniquely proven.
2. `tutor.spec.ts:148`: the existing 5-second completed-heading assertion failed at line 195. The actual frozen observer shows the final event request had not delivered a response by the assertion boundary. It does not establish completed bytes being dropped by the UI. Independent post-assertion observations do not establish earlier backend timing. Root cause remains UNKNOWN.

`FAILURE_REPORT.md` separates observations, supported hypotheses, missing evidence and discriminating next diagnostics. The original ZIP's GitHub digest was checked and all seven members retained; no raw failed evidence was replaced by excerpts. It contains the two actual failure contexts/screenshots, the real Tutor diagnostic, and two separate passing diagnostic-helper outputs. Exact relevant sources are copied from the proven identical Git tree. No browser rerun, server startup, test modification, timeout increase or retry-to-green was performed. Prior failures and this run's separate successful push are not erased by either result.

## Acquisition and verification

Final API snapshot is label **21**. All 12 jobs are terminal, with all 12 complete original logs under `logs/`. `21-audit.json` mechanically verifies acquisition hashes, one exact checkout per completed job, all six installed-package sets, GitHub commit/tree binding, actual workflow bytes and event/head/run-attempt identity. `initial-captures-verification.json` additionally verifies the four initial-discovery receipt formats. Original acquisition stdout/stderr and timestamps are preserved; `readback.py` only issues read-only GitHub API requests and never dispatches a workflow.

The final manifest covers all retained originals, sources, helpers, derived readbacks, reports and receipt. No repository worktree was modified. Cache evidence is private working evidence until the parent performs its separate publication/provenance review; this task did not upload it. No model key or external model request was used. The separately reviewed publication-admission candidate and ongoing Review UI work are outside this exact CI head and its acceptance claims.
