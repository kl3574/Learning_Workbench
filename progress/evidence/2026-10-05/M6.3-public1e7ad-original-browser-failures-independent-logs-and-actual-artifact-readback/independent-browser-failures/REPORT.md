# Two original browser job failures

Both original attempt-1 browser jobs are **FAIL**: push run 37241154917/job 111549980428 and PR run 37241158099/job 111549989024 each planned 133 tests with one worker and finished **2 failed, 131 passed**. Each original CI step reports exit 2; capture receipt exit 0 only means the original log fetch succeeded. Log size/SHA-256 and empty stderr are independently verified against both original receipts.

| Event and actual checkout | Original failures and precise observation |
|---|---|
| push, `1e7ad7a8656c0dc8373d4181fa3002f385ed1847` | grading.spec.ts:66 case: grading_revision expected 3, received 0; 30000ms test timeout; grade helper:26:254, caller:77:25. review.spec.ts:36 case: 30000ms test timeout, locator.evaluate target page/context/browser closed while waiting for the history heading at review.spec.ts:155:152. |
| PR, `88da38fc07cd1d797e1171943a00159842421ac3` | authoring.spec.ts:7 case: owned test server exited before readiness; Vite Port 40581 already in use; authoringRuntime.ts:70:85, start:110:7, authoring.spec.ts:9:19. review.spec.ts:36 case: URL reader parameter poll expected true, received false; 30000ms test timeout at review.spec.ts:147:75. |

The same review case has different original failure locations in the two events. Across the two jobs there are four failed occurrences and three unique cases. The PR authoring failure is the recorded early server exit; its logged frame shows a 20_000ms readiness deadline and 1000ms fetch timeout, but the observed error is port-in-use. Port owner/lifecycle was not investigated. The push grading helper frame returns 0 on HTTP 202, but this packet does not contain a complete response history or establish the underlying grading/provider cause or completion of the case's 412/rebase path. Target closure after timeout does not independently establish a browser crash.

PR original log additionally records a GitCommitInfo git-diff timeout of 3000ms. Original case titles, failure blocks, assertions, timeout lines, stack traces, and log line locators are retained in REPORT.json. Actual checkout tree IDs are NOT_CAPTURED.

- PR original log: 104133 bytes, SHA-256 `038485bcec030dfa638bc1eabd90a596c8e3188896120aa88c9edf6ddde05c8c`; failures:831,864; summary:889,892; CI step exit:894.
- push original log: 104651 bytes, SHA-256 `56459e8afae09f3ef1f8f73afe3a3bed492f31939f87f780724ab5d12deae1c3`; failures:818,848; summary:872,875; CI step exit:877.

Only eight explicitly authorized original log/metadata files were read. No new API/observer/browser/test/probe/model execution, product/timeout/source modification, rerun/cancel, or remote write occurred. No screenshot, ZIP, error-context file, runtime, database, secret, or user payload artifact was opened. Existing captured8-v1/44 snapshot and 27f packets remain unchanged. Integration remains running per root task context and was not reobserved here; these browser FAILs do not establish a terminal whole-run result or whole M6.3 acceptance.
