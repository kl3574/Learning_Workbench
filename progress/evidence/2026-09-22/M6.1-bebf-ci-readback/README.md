# bebf806 CI readback: original failures preserved

Read-only evidence for PR 53 head `bebf80601b3debf788d446ed2b3abf0847b392bc`. The [push run 35677956691](https://github.com/kl3574/Learning_Workbench/actions/runs/35677956691) and [PR run 35677959449](https://github.com/kl3574/Learning_Workbench/actions/runs/35677959449) both completed with failure. This package contains all 12 job logs, both original failure-artifact inventories and their finite extracted contents, API metadata, exact source evidence and command records. No CI rerun, test execution, source edit, Issue/PR write, vendor request or repair was performed by this subtask.

| Job | Push | Pull request |
|---|---|---|
| browser | **94 PASS, 2 FAIL** | **95 PASS, 1 FAIL** |
| integration | **763 PASS, 1 FAIL, 1 SKIP**, 2 warnings | 764 PASS, 1 SKIP, 2 warnings |
| backend | 633 PASS, 2 warnings | 633 PASS, 2 warnings |
| spec-contracts | 543 PASS, 2 warnings | 543 PASS, 2 warnings |
| frontend | 401 tests PASS / 72 files | 401 tests PASS / 72 files |
| security-publication | success | success |

Both new Authoring browser cases (`authoring.spec.ts:80` and `:110`) passed in both runs. The numeric-runtime integration skip explicitly says `BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained`. These results do not prove successful sealed calculator execution, production model support, or complete M6.1 delivery.

## Exact checkout and scope

Each job's own `git log -1 --format=%H` output was inspected. All six push jobs checked out `bebf80601b3debf788d446ed2b3abf0847b392bc`; all six PR jobs checked out GitHub's merge commit `5579332adcd9259c6390624b61106e23e8856817`. Both API run heads report bebf806, but that head is not the PR job checkout. The two actual commits have the same Git tree, `a7f63f5475d7bf62385bf74823bc11235575c948`. The PR merge parents are base `81d2b92e2f9ed24631988f860a1fba528f2c4ad7` and bebf806. `checkout-identity.json` and all 12 log locators retain this evidence.

The only changes from 79908fb are four progress files. PRODUCT_DESIGN remains 3.0.6, SHA-256 `30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924`; the selected workflow, tests and implementation source files are byte-identical to 79908fb. These CI runs exercise the existing worked_example scope, not the independently developing 3.0.7 group drafts. Earlier ref/PR metadata is retained as the separate 02:28:53 UTC publication snapshot, not presented as a new live PR query.

## Actual failures

1. **Both browser jobs:** `tests/e2e/tutor.spec.ts:195` failed the original 5000 ms visibility assertion for heading `真实任务状态：completed`. Push log lines 771–809 and PR log lines 759–796 contain the exact assertion and verdict. The full cases were not completed; later answer/restoration assertions cannot be counted as passed for these cases.
2. **Push browser only:** `grading-recovery.spec.ts:57` failed at result helper line 41, called from line 79. `GET /api/v1/attempts/{id}/result` returned HTTP **409**, while the helper expected **200** (and separately permits 202 while polling). This occurred when obtaining the first original grading revision after submission, before the later deliberate frozen-answer fault and regrade-recovery actions. The failing response body is not captured, so the exact API error code and server-side state are unknown. Push browser log lines 747–769 preserve the original failure.
3. **Push integration only:** `test_cancel_during_actual_http_stops_once_and_preserves_real_dispatch_facts` failed at `test_tutor_runs.py:359`. The before/after `lease_owner` values matched, but `lease_until` changed from `2026-09-22T02:13:10.197294Z` to `2026-09-22T02:13:10.509294Z`, an increase of **312 ms**. The assertion requires both fields to match across the cancellation operation while the worker runs concurrently. The trace does not identify which operation changed the lease; it does not establish that cancellation itself rewrote it. Push integration log lines 389–520 preserve the failure and summary. Assertions after this failure were not reached.

The extra push failures are distinct from the previous 79908fb run summaries. This package does not assume a shared cause or infer a source regression from failures in unchanged code.

## Tutor observations and their owners

The diagnostic schema is owned by `tests/e2e/tutorDiagnostic.ts`, not by the Tutor Run API. In particular, **`post_assertion.run.state = "failed"` is a `ReadResult` probe failure**, returned when the diagnostic read operation throws. It is **not** a successfully read business `Run.status = "failed"`. Both artifacts have this probe state and no `run.value`; neither contains a successful post-failure Run state or Provider terminal receipt. The helper's 400 ms GET timeout and exception sanitization do not preserve the precise reason for either probe failure.

Times below use each artifact's own Node `performance.now()` clock relative to that observer's start. Times from different runs are not subtracted.

| Observation | Push | Pull request |
|---|---:|---:|
| Original completion assertion started | 8620.972 ms | 8581.481 ms |
| Frozen already-delivered metadata | 13627.969 ms | 13582.798 ms |
| Last delivered DOM receipt | 9239.841 ms, queued | 9171.362 ms, queued |
| Last SSE request, after_seq=3 | id 79, 9226.037 ms | id 77, 9162.801 ms |
| HTTP 200 for that request | 13296.930 ms | 13359.375 ms |
| finished/failed for that request before freeze | neither observed | neither observed |
| Post-failure Run probe | ReadResult failed, no value | ReadResult failed, no value |
| Post-failure test-only runtime | 1 received / 1 byte-validated / 0 invalid | 1 received / 1 byte-validated / 0 invalid |

Both last DOM receipts also report observing, grant acknowledgment and linked consent. `answer_present` is only the existing helper's DOM predicate; it does not prove a checked or complete answer. HTTP 200 does not establish streamed-frame receipt, reducer application, or terminal Run state. There is no backend lock/worker/Provider-receipt timestamp or SSE frame instrumentation in these CI artifacts. The last delivered DOM is not a synchronous snapshot at the assertion deadline, and post-failure probes cannot establish the earlier backend state.

All three failure screenshots were visually inspected: the grading screenshot shows an independent-assessment view; the two Tutor screenshots show synthetic Reader material with the right pane scrolled into the granted test-only loopback consent. Their error-context DOM includes a queued Tutor heading. They are post-failure artifacts and may reflect teardown; they are not precise deadline screenshots. The small diagnostic-self-test JSON in each ZIP is expected test output from a **passing** diagnostic test, not an additional failed CI case.

## Package integrity and limits

Exactly 22 necessary read-only `gh api --method GET` calls were made: six run/jobs/artifact metadata requests, 12 job logs, two artifact downloads and two actual-commit metadata requests. Each recorded command explicitly sets uppercase/lowercase HTTP(S) proxy to `http://127.0.0.1:10808` and clears uppercase/lowercase NO_PROXY. All completed successfully. ZIP SHA-256 values match GitHub's supplied digest:

- Push artifact `10673049890`: `d51647566df4bf64eb0a903fa8342950c511ecac5908b0d57ad295412768c570`, 446146 bytes, six extracted files.
- PR artifact `10673249643`: `7751ffd1f9fdedf9d0aae318a5780c2c0e57062066da49fec7dfa1de1e0aea91`, 281407 bytes, four extracted files.

Raw ZIPs and original bytes remain in this new cache directory. The public copy contains only finite logs, metadata, source evidence and reviewed synthetic failure artifacts. Literal CI/local HOME prefixes are replaced with `<CI_HOME>` / `<LOCAL_HOME>` only where present, with original and derivative hashes bound in the manifest. No session/profile, database, storage state, HAR, trace or archive is copied into the public package. Existing 79908fb CI and local-measurement packages remain separate and unchanged. No inferred repair or historical root cause is claimed.
