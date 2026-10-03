# PR55 grading recovery: bounded private feedback report

The original CI failure remains unresolved by this check. At the exact observed checkout `89b9d2279364e83c2dbddd1b3418c8c206ec9845`, the first local launch was blocked by a private TMPDIR path-length error before business operations; the separately authorized second execution, using a short private TMPDIR, passed the unchanged original case once. This local PASS means **not reproduced locally**, not fixed, flaky, or CI green.

## Original CI evidence

- PR55 push run `35689944640`, browser job `106624590630`. The original job log's actual `git log -1 --format=%H` output is the exact checkout above (lines119–120), not a PR merge guess.
- The original job invokes `make test-e2e`; Playwright reports `98 passed`, `1 failed`. At `grading-recovery.spec.ts:79`, the first call to `result()` fails its line41 HTTP-status assertion: expected200, received409. The original failure is preserved without rewriting its status.
- The original full log stays in its existing private cache; `ci-log-excerpts.json` binds that exact path, bytes, SHA256 and selected original line numbers.
- Artifact10677454514 was downloaded read-only. Exact ZIP:169963bytes, SHA256 `5398d56bdbfef2b2aff0ea2a5d55b23415e82fb9fd66fc206d4b567a36ef725a`. All four members are inventoried; only this case's error context and screenshot were extracted. Two unrelated Tutor JSON members were not extracted or read for this diagnosis.
- The error context records the status assertion and the original call site. It does **not** provide the 409 response body, server error code, submission ACK, request ordering, or a network trace.
- The 1440×900 PNG was actually viewed with `view_image`. It shows the independent test still on its answer form, the end-test section, a pale/disabled-looking submit button, the abandon button, policy verification text, and the footer session-saving text. The Agent panel says model/network were not called and the standard answer was not requested. These are visible UI facts; the screenshot cannot establish why the request returned409 or reconstruct submission ordering.

## Two distinct local attempts

Both execute this exact command from the detached worktree:

```sh
bash scripts/node.sh npm --prefix apps/web run test:e2e -- grading-recovery.spec.ts --retries=0
```

Both preserve the original test's120s timeout, original helper/assertions, original Playwright configuration, one worker and zero Playwright retries. No product, test, timeout, assertion or CI configuration was edited. The first local failure was not a reproduction of the CI symptom.

| Attempt | Actual interval UTC | Actual outcome | Limits |
| --- | --- | --- | --- |
| 01, root-level original files | 05:42:53.293926–05:42:57.840875 | exit1; driver4.2517s; Chrome `SingletonSocket` path too long at `RestartRuntime.openBrowser` | Browser launch failed before first result/409 business trigger. Original files retained. |
| 02, `02-short-tmp/` | 05:46:06.431630–05:46:15.600315 | exit0; Playwright1PASS8.5s; case7.0s; driver8.8942s | TMPDIR only changed to exclusive `/tmp/lw62-pd8uolb_`; this was explicit repair of the diagnostic setup, not a retry of the CI symptom to wash a failure green. |

Local tools were Python3.12.13, Nodev24.21.0 and GoogleChrome153.0.8010.52. Reused package/toolchain entries were read-only by arrangement; `.vite`, `.vite-temp` and `.cache` were isolated. Both attempts' shared toolchain metadata inventories match before/after. The subprocess environment contains only explicitly selected standard/local test values and no inherited supplier/API-key variables. The original case uses owned synthetic test data and its existing private answer-fault helper; there were no real vendor or numeric calls and no production database use.

The second case's actual JSON records initial grading revision1, a retained actual failed regrade Job, restoration of the original synthetic private-answer row, recovery to grading revision2 using two distinct explicit commands, preserved original responses, no runtime errors, and `actual_human_math_approval: NOT_RUN`. It proves this one original synthetic local scenario reached its existing assertions, not mathematical approval or the whole99-case native gate.

## Source boundaries and diagnostic stopping point

All four before/after input maps contain946 non-progress tracked source files, match one another, and individually match the fixed Git blobs. Fourteen focused files are also copied byte-for-byte with Git/SHA pins. `m62-active` was not changed by this task. Local source matching is distinct from matching the CI machine or proving a cause.

Source reading, not runtime cause evidence: line79 is before the deliberate private-answer removal at line84. The line77–79 sequence clicks submit/confirm and calls the result helper; the source does not await a submission HTTP ACK there. The UI calls its asynchronous submission operation from the confirm handler, and the grading service has an explicit409 branch for an absent submitted snapshot. These locators describe the code and possible future observation boundaries only. The downloaded artifact has no error body or event ordering to connect that particular branch to the CI409. No root cause is asserted, and no additional hypothesis testing, instrumentation, fix, or repeated run was performed.

The diagnosing-bugs feedback phase therefore has an actual original-case command and a CI failure, but no locally reproduced target failure or established deterministic reproduction rate. Later diagnosis/fix phases were not claimed complete. Further execution would be a separate authorized task.

`cleanup-readback.json` records both original global configuration ports closed and both logged global Uvicorn PIDs absent at readback. The original case awaited its existing runtime cleanup in `finally`; we did not delete runtime evidence, kill by port, modify system settings, or claim a full descendant-process audit. Private runtime directories remain preserved separately.

## Private retention and replay

This directory is a **private checkpoint**, not a public publication package. `manifest.json` is a finite allowlist of logs, receipts, drivers, input maps, the original artifact ZIP, two selected artifact files, the successful local JSON and focused source snapshots. `verify.py` rehashes that allowlist, checks the aggregate and original external CI log, replays ZIP-member hashes, and checks four exact input maps and both real receipt/log bindings. It does not execute product code or tests.

The allowlist excludes `tmp/`, `global-data/`, `02-short-tmp/global-data/`, browser profiles, runtime SQLite files, bootstrap/session/CSRF material and other private runtime files. Those are not read or exported by the verifier. Do not publish the entire directory or ZIP without a separately reviewed redaction allowlist. No source commit, push, PR change, CI retry, supplier request, system-policy change, human approval or release action was taken.
