# Fixed-799 local Tutor measurement: no local reproduction

Source is detached `79908fb941898eb2b515719ce175c68dde3c71ef`, tree `f8d97f6c22be33ff59edd00950c6f3be741646ba`, PRODUCT_DESIGN 3.0.6 SHA-256 `30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924`. This is a separate cache worktree. The active M6.1 and groups worktrees were not changed by this diagnostic. The earlier CI readback public package remains frozen.

The sole exact Tutor native case ran three times. All three complete cases passed, including the original 5000 ms completed-heading assertion, exact original answer, one validated loopback request, restored Run, and evidence-boundary assertions. There was no vendor request, arbitrary sleep, injected response, timeout change, disabled worker, remote CI rerun, or product fix. This does not resolve the two historical CI browser failures (each 95 PASS / 1 Tutor FAIL; both Authoring cases passed).

| Directory | Actual case execution | Verdict | Original completed assertion | Measurement |
|---|---:|---|---:|---|
| run-01 | 0 | command failed: no tests found | not executed | Anchored grep did not match Playwright's full title; retained setup failure |
| run-02 | 1 | PASS | 2358.801 ms | Client/clock/original diagnostic complete; backend atexit export absent |
| run-03 | 2 | PASS | 2345.622 ms | 12,616 backend events, 0 dropped; full client/clock data |
| run-04 | 3 | PASS | 2336.638 ms | 12,049 backend events, 0 dropped; full client/clock data |

Only the diagnostic export changed after run-02: Uvicorn completed shutdown but did not invoke the atexit export, so the test-only middleware now exports after its lifespan returns, after worker shutdown. The initial missing backend data remains missing; it was not reconstructed. Run-03 and run-04 have identical before/after fingerprints. The before/after records also verify that removing only declared observation statements yields the exact original test file, preserving all business assertions.

## Measurement and scope

The test-only factory installs SQLite Connection wrappers, owner/worker method wrappers and an ASGI send observer. Production database, worker, provider, repository and SSE source files retain their fixed-799 bytes. Python events use a single `time.monotonic_ns()` clock and span/connection/thread identities. SQLite records BEGIN call start/acquisition/error, commit return, Connection.execute count/time; fetch/iteration and cursor methods are not separately timed. Method spans are inclusive and nested wall times, not CPU samples. ASGI captures only response status and SSE id/type, never bodies or headers. Events remain in memory until shutdown. JavaScript adds optional calls to record parsed SSE events, Run snapshot return/setRun and DOM state into a bounded browser array, using that browser's original `performance.now()` timestamps.

Node records the original assertion call's start/return. Before grant and after assertion, read-only clock requests and browser evaluations bracket Python/browser time with Node timestamps. `analyze.py` uses the envelope of observed offset intervals, not wall time subtraction or an unjustified exact offset. Python-to-Node envelopes are 3.938 / 3.575 ms wide, browser-to-Node 1.320 / 1.220 ms in the two complete runs. Same clock rate within these short intervals is an explicit mapping assumption; raw brackets remain available. Browser event retrieval after the assertion preserves event timestamps and is not a synchronous deadline snapshot. Existing post-assertion Run reads are not evidence for earlier backend state.

The local config retains the original case and expectations and omits the two unused shared webServer processes because this single case owns its API/UI through TutorRuntime. All four normal workers run. This isolated local single-case workload does not reproduce the entire CI 96-case workload, runner scheduling, or environment. Instrumentation adds overhead; there is no uninstrumented performance baseline or measured zero-overhead claim. No additional tests or repeated CI commands were run. Local Python 3.12.13, Node 24.21.0, Playwright 1.63.0, Chrome 153.0.8010.52 are recorded in `after-measurement.json`.

## Direct observations

All following intervals are milliseconds relative to assertion start, derived from retained clock brackets. Provider receipt means the checked receipt returned after its transaction; Tutor commit is the transaction containing the real final repository operation. SSE send return means ASGI accepted the send, while parsed and DOM events are separate browser observations.

| Stage | run-03 | run-04 |
|---|---:|---:|
| Provider complete receipt return | 1551.492–1555.430 | 1639.481–1643.056 |
| Tutor final transaction commit return | 1778.472–1782.410 | 1761.274–1764.850 |
| Completed SSE send return | 2251.700–2255.638 | 1932.327–1935.902 |
| Completed SSE parsed | 2253.680–2255.000 | 1934.220–1935.441 |
| Completed Run snapshot returned | 2334.380–2335.700 | 2000.620–2001.841 |
| Completed DOM observed | 2336.580–2337.900 | 2003.020–2004.241 |

On the same Python clock, final commit to completed SSE send start was 473.165 / 170.919 ms. On the same browser clock, completed SSE parsed to confirmed snapshot return was 80.7 / 66.4 ms, followed by 2.2 / 2.4 ms to DOM completed. These local samples do not show a large transport/DOM tail, and do not locate CI's unobserved deadline state. Run-04 assertion returned about 333 ms after the DOM observer event; the measurement does not identify the Playwright scheduling mechanism responsible.

During the two complete assertion windows, Authoring idle claim write transactions held through commit return for at most 0.429 / 0.597 ms; Numeric claims at most 1.023 / 0.292 ms. Their waits can be much longer (Numeric up to 228.905 / 78.594 ms): time waiting for another writer is distinct from time holding the write transaction. Authoring's recover_unfinished transactions, while a Tutor dispatch was active, held up to 64.512 / 52.558 ms. Those are not proven empty-recovery measurements.

Run-03 recorded one Authoring recover_unfinished BEGIN OperationalError after 50.469 ms. Its observed wait overlapped Tutor `_consume` and `_finish` write intervals, not the other way around. The exact SQLite error code/message was not captured, so this is not a recorded `SQLITE_BUSY` assertion. Tutor still passed. Run-04 recorded a Tutor `_prepare` BEGIN wait of 178.573 ms; most overlapping measured writer time belonged to AnyIO request transactions not further named by this probe, while overlapping Authoring recovery/claim and Numeric claim holds were each below 0.05 ms. This does not justify blaming the added idle claims.

Owner validation work is substantial in these local traces: `TutorRepository.source_state` was entered 150 / 151 times in the assertion window, and `_load` 731 / 739 times. These are inclusive/nested counts, not additive wall-time attribution. The fixed code calls complete message/thread/history checks from `source_state`; Provider guards, recovery and reads invoke these paths. `_finish` held the Tutor writer transaction for 169.931 / 80.297 ms while `TutorRepository.finish` itself lasted only 6.555 / 1.732 ms, so the surrounding guarded work is a distinct investigation target. ImportWorker maintenance also has write transactions and must not be omitted from a contention model.

## Bounded next diagnostic choices, not repairs

1. If obtaining a naturally failing sample is separately authorized, keep the assertion unchanged and use the exact same clock/connection/event identities to locate Provider receipt and Tutor final commit relative to the actual boundary. Do not replace that observation with an after-failure GET.
2. Refine the currently unnamed AnyIO writer spans and separate ImportWorker maintenance owners; compare actual wait overlaps. Do not infer that a long idle-worker wait means that worker blocked Tutor.
3. Inspect repeated guarded owner scans and recover_unfinished's active-lease checks inside transactions. A future optimization needs a security-preserving contract and an independently failing comparison; these PASS samples do not approve weakening history/Policy checks.
4. If backend final commit occurs in time but the UI misses the deadline, retain SSE frame send, parser receipt, snapshot read and DOM marks to distinguish delivery from rendering. No longer timeout is proposed.

## Evidence handling

Raw files remain in this cache directory. The public subdirectory is a finite copy of source/hashes, commands, safe original diagnostics, timing events and replayable analysis, with literal local HOME replaced by `<LOCAL_HOME>`. No session/profile/database, storage state, trace, HAR, request headers, provider secret, or answer body is copied there. Original synthetic screenshots and the existing full synthetic success artifact remain raw-only because timing evidence does not require publishing them. Manifest entries bind every copied derivative to its original SHA-256 and describe the sole path substitution. No new evidence is merged, committed or published by this subtask.
