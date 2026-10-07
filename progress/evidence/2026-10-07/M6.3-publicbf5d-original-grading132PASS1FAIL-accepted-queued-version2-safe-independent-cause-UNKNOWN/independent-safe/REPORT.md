# Original publicbf browser failure — finite independent diagnosis

This report is PRIVATE. It contains selected safe facts and byte/hash bindings, not complete raw logs. No test, browser, model, network, secret, host probe, archived owner script, CI dispatch, cancellation or rerun was executed. Source/index/remote were not changed. Only this private report directory was written.

## Scope and source identity

- Project: Learning Workbench 学习平台 only.
- Canonical HEAD: `bf5d2df4e7ee5156993169cdd9610fa014bdae4f`; tree `1dceb32a663607aabfafabd68aa4457f2d904daf`.
- Source gate anchor: `101cee47d8e746dddac81fb6e8829069fcabff09`.
- Sole normative specification: PRODUCT_DESIGN.md v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.
- All inspected relevant source files match canonical HEAD byte-for-byte. Relevant grading/UI/helper/runtime source has no delta between anchor101 and publicbf. This does not reproduce either run or establish environment parity.
- PR original checkout records merge commit `268208560ffce5a5e202acfb60d5fa1c6ebb975a` at line185. Its object is unavailable locally; same-tree parity is task-supplied and was not independently inferred from the head field.

## Original concrete failure

The failing test is `tests/e2e/grading.spec.ts:66:1`:

> two browser profiles keep a stale manual-review baseline through an actual 412 before explicit three-way rebase

Original push job112915059557 has raw SHA256 `363d5580777ed73f65f64dd4aea1805addf92d93774f4f224dd7519d6a600609`, 102112 bytes. Its same-test terminal line737 reports FAIL and 32.3s. Failure heading line835 binds the same test. Expected/actual lines839–840 are `Expected: 3` / `Received: 0`. Call log line843 explicitly reports `Test timeout of 30000ms exceeded`. Stack lines852–853 bind helper26 and caller77. The actual original footer is 1 failed /132 passed (39.1m), lines865/867. These counts are read from original Playwright output, not job status.

Original PR job112915084185 has raw SHA256 `a6a26b400d49329752a46b584838f0b849496081f13e319ba0cf38166a70b393`, 94831 bytes. Its same-test terminal line736 reports PASS and 29.1s. Its original footer line833 is 133 passed (38.5m).

All selected lines have zero-based half-open byte offsets and SHA256 of exact line bytes including their line ending in SAFE-LINE-BINDINGS.json. Source spans have equivalent bindings in SOURCE-BINDINGS.json.

## What 0 and timeout establish

The source helper at grading.spec.ts24–27 polls `GET /api/v1/attempts/{id}/result`. HTTP202 returns the sentinel0 immediately; only HTTP200 parses the grading result and returns its grading_revision. Caller77 awaits revision3 before checking score0.25 and null scores on the remaining items. The observed0 therefore establishes the poll's observed HTTP202 path. It is not a score, not an observed grading revision0, and not proof that the job was merely queued/running.

GradingService.result() at grading.py51–70 returns AssessmentGradingJob for every latest-job status other than completed. This includes failed and cancelled. assessment_http.py57–65 projects that job as HTTP202. The test helper does not parse the202 body or bind job status. The product UI does: useGradingResult.ts43–51 reads job identity/status, retains the last completed result, and exposes failed/cancelled. The job API validates its job/input binding; repository.load_grade() validates completed job, revision, result digest and unique completed terminal event.

The log establishes whole-test budget exhaustion at30s. The passing PR's29.1s shows little observed margin on that run; it does not prove CI load, setup overhead, worker delay or a timeout defect. Test-level setup creates its own API/UI/browser via RestartRuntime; those stages share the test budget, but individual stage durations are absent from these logs. A timing correction is not justified solely by the adjacent duration.

The test code binds the original stale regrade POST to HTTP412 and the displayed A/B/base comparison before the final rebase. Reaching caller77 means these preceding awaits/assertions did not abort the test. It does not create an independent captured final POST/JobRef receipt: final sendReview() only clicks the confirm UI, then caller77 reads whichever latest job result the server exposes. No accepted final command identifier, actual job terminal status, allocation revision or per-stage timeline is present in the selected failure evidence.

## Worker/cause boundary

GradingWorker.claim() selects queued or expired running jobs, respects next_retry_at and the workspace independent-attempt guard; lease duration is90s. Compute validates frozen submission/assignment/private pins and base grade, applies signed review items, then finish atomically persists the new grade and completed job. Valid compute errors can produce a failed job; result() still exposes it as202. ImportWorker's single maintenance tick advances evidence recovery, recommendation, retrieval, then grading; its idle loop waits0.25s. These source possibilities were inspected without invoking the worker. The logs do not identify which path occurred.

Terminal logs alone leave root cause UNKNOWN. The subsequently read original retained context narrows the end-state as below; it still cannot identify why runtime progress was late. The prior079 ReviewReaderURL timeout is a different historical test and was not treated as this failure's cause. The fixed101 local133P is task-supplied historical evidence, not a new test run or proof that this original push is accepted.

## Minimal safe next step and fix boundary

No production behavior fix is justified by the available evidence. Do not change worker leases, bypass an independent guard, retry a mutation, increase global/test timeouts, delete the actual412/three-way comparison, or loosen exact revision3/score0.25/null assertions to force a green result.

The minimal evidence-supported next implementation is a bounded metadata-only observer on this original grading test. Mirror the already tracked Review observer pattern (review.spec.ts7–49): test-scoped observer inside the existing30s, finite phase/caller enums, monotonic elapsed_ms, existing GET result HTTP status and request duration, capped phase/poll arrays, synchronous safe JSON write at body-finally with fixture-finally fallback. Preserve original runtime isolation, real UI seeding, control flow, original202 sentinel return, original exact assertions, all test/body/individual assertion deadlines and single explicit command. Do not move fixtures to worker scope or give setup a separate budget. No additional request, wait, retry, DOM/auth/value collection or mutation is required. Scheduling overhead must be stated and cannot itself establish cause. This candidate remains NOT_IMPLEMENTED/NOT_RUN in this read-only task.

The existing helper submitAssessment() at assessmentTestData.ts21–35 observes exact POST submit202 and verifies AttemptSnapshot id/status. grading.spec.ts23 instead waits for the current-result region to appear; it does not directly capture that submission receipt. An explicit initial-grade baseline readback or final regrade receipt/status binding can strengthen test readiness/diagnostics, but would alter synchronization and require a separately reviewed change. They are not causally supported fixes for this original late completion. In particular, adding a missing POST observer cannot be described as fixing a command that was not sent: the retained original UI already displays acceptance.

The original retained artifact `browser-failure-push-37657156244-1` contains the exact paths bound by push log856/860/863:

- grading-two-browser-profil-1cfaf-e-explicit-three-way-rebase/error-context.md
- grading-two-browser-profil-1cfaf-e-explicit-three-way-rebase/test-failed-1.png
- grading-two-browser-profil-1cfaf-e-explicit-three-way-rebase/test-failed-2.png

A private read should extract only the grading task status label, grading revision, accepted-manual-command boolean, and job error code. Do not emit identifiers, reason/answer text, AuthCase/CSRF/cookies or database contents. Configuration trace isoff, so a full trace is neither expected nor required. Root downloaded this one original retained artifact and extracted only the three exact members. This diagnosis did not perform network access and privately read only the selected original context.

### Original artifact safe end-state readback

Original error-context.md is28392 bytes/368 lines, SHA256 `10a3a4023b39babb043c1a80112504e0442f663ea2386f945e0d8444dca331ff`; source artifact ID11500549632. ARTIFACT-SAFE-BINDINGS.json records exact line bytes/offsets/hash, the root extraction provenance hashes and only fixed labels/booleans.

- Line197: UI grading task status isqueued (fixed heading `评分任务排队中`; source mapping AssessmentResult.tsx15/39).
- Line198: progress label iswaiting for grading.
- Lines202/204: last completed result/version2 isvisible.
- Line241: this grading task isnot ended.
- Line243: manual review command accepted=true. That receipt explicitly says it isnot proof of completed grading; do not treat the phrase “completed grading” inside that negation as a success label.
- The complete selected context contains no fixed grading-version3 label, no failed/cancelled job heading, and no whitelisted GRADING_FAILED/GRADING_INPUT_INVALID/GRADING_LEASE_LOST code.

These are end-state UI observations, consistent with the log202 sentinel and unfinished revision3. They support a visibly accepted command plus an observed queued task at capture. UI polling can be stale; the snapshot does not prove the server stayed queued throughout the poll, the exact acceptance/claim/completion timestamps, or why the task waslate. Root cause therefore remains UNKNOWN; the missing-response-observer theory cannot be promoted to cause or repair. No raw context, IDs, reasons/answers or images were copied into this report.

The historical Review test's current SetupTiming explicitly remains test-scoped and inside the original timeout, so it supplies no precedent for a setup/body budget split. All improvements proposed here keep that boundary.

## Actual verification and acceptance

| Item | Status | Exact meaning |
|---|---|---|
| Selected original-log hash/line bindings | PASS | Actual private bytes hashed; safe facts checked against the exact lines |
| Relevant source vs canonical HEAD | PASS | Read-only byte equality, not functional correctness |
| Relevant source anchor101 → publicbf comparison | PASS | No relevant source delta; no environment or runtime claim |
| Original push browser | FAIL | Original1F132P; retained as failure |
| Original PR browser | PASS | Original133P; completed-job scope only |
| New tests / reproduction / regression | NOT_RUN | None authorized or executed |
| New CI rerun/dispatch/cancel | NOT_RUN | None performed |
| Original artifact safe field extraction | PASS | Original UI accepted/pending queued, old version2, no version3 label; snapshot scope only |
| Production root cause / production fix validation | UNKNOWN / NOT_RUN | No proven lateness cause or verified repair |
| Whole-CI acceptance | NOT_DERIVED | Browser evidence cannot close live integration or other acceptance |
| M6.3 | NOT_ACCEPTED | No completion claim |

Normative preservation: PRODUCT_DESIGN.md18–19 forbids choosing weaker requirements;732 preserves frozen submission/grade history and null unknown scores;20.2 preserves strict answer/knowledge-evidence boundaries;2693 requires the explicit CAS-bound manual regrade command to create a new revision without rewriting the old grade.
