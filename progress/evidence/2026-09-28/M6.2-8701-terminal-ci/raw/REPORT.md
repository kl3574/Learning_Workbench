# 8701 terminal CI and bounded Tutor comparison

Actual push run 36389800538 completed **SUCCESS**. Actual PR run 36389807970 completed **FAILURE solely browser**. Both are attempt 1; no rerun, dispatch, cancellation, product retest, source/main/progress change or remote mutation was performed. A single owned monitor used 150-second GET cadence, ended naturally at p12, and preserved all polling stdout/receipts. An additional bounded early GET captured the newly known PR failure into separate paths; the later monitor copies are byte-identical.

Push actual checkout is `8701c8a04b654c2462e4311f0128201507ebaf7e`. PR actual merge checkout is `d8205101aaa035c7f1594f40305ae66b8e239837`, distinct from its head_sha. Complete job logs and independent Git commit API bodies bind both to tree `dca622334045f5136345d2f604c4a9e892bf893c`, also matching the local public-head Git tree. Fifteen Tutor/test fixture/dispatch/DB/workflow source paths are byte-identical to 4cc; this does not claim the entire product composition is unchanged.

| Actual scope | Push | PR |
| --- | --- | --- |
| backend | 731 PASS, 2 warnings | 731 PASS, 2 warnings |
| integration | 1665 PASS, 1 numeric environment SKIP, 2 warnings, 1958.30 s | 1665 PASS, 1 numeric environment SKIP, 2 warnings, 1108.22 s |
| frontend | 538 PASS / 91 files | 538 PASS / 91 files |
| spec-contracts | 608 PASS, 2 warnings | 608 PASS, 2 warnings |
| security | 13456-file scan PASS | 13456-file scan PASS |
| browser | 107 PASS, 14.9 m | 106 PASS / 1 FAIL, 20.0 m |

Scopes overlap and are not summed. Both numeric skips retain the exact original BLOCKED_ENVIRONMENT statement that the real sealed runtime did not execute the calculator and the original FAIL is retained. No numeric execution success is claimed. All six backend/integration/browser APT steps succeeded with actual dpkg-query lines binding bubblewrap 0.11.1-1ubuntu0.3, apparmor/libapparmor1 5.0.2-0ubuntu1~26.04.1, libseccomp2 2.6.0-2ubuntu5.

All 12 complete logs were captured and hash-verified. Push browser log SHA256 is `1e56b768411ed203b9531f63dde10dea870a6a6a106cb3163afbb7d85173eef3`; line745 records the original Tutor case `tutor.spec.ts:148` PASS (14.8 s), and line768 records 107 PASS. No push failure artifact was uploaded, so there is no successful-run internal diagnostic timeline available to compare with PR.

PR browser log SHA256 is `4a0fe73b75c267dd5724d05fbc7ea3a96155f9f4f6be9cf2276dced4a770efeb`. Line774 records that case's failure (18.3 s); lines798–819 preserve the original completed-heading failure at line195 with the original 5000 ms timeout; lines833–835 retain 106 PASS / 1 FAIL. Failure-summary wall timestamps are not assertion start/deadline timestamps.

Original PR artifact 10956473483 is 297100 bytes; SHA256 `7c5c0440c62c657a2951f15898107770bf3626ec297f39abbc12c5116fd7c4e9` matches GitHub's digest. All eight members are preserved and verified against ZIP bytes. There is **no trace file in this original artifact**. The original Tutor diagnostic is 101869 bytes, SHA256 `733cc814b701bee79ad8507342143862a06afeb4ca80f06661a9016ab3b4832c`. Error context and original PNG are retained. The PNG was actually inspected solely for publication privacy: synthetic original textbook and explicit loopback proposal/consent metadata, no visible credential. It is not edited and not evidence of a unique failure cause.

## What the PR capture supports

Node completion_assertion_start is 9791.452064 ms and the synchronous freeze is 14793.909155 ms. Last SSE id76 / after_seq3 starts at 10559.703297 ms, receives HTTP 200 at 14518.852423 ms, and delivers validated answer_delta seq4 at 14539.471653 ms followed by event_applied at 14539.481672 ms. The last observed DOM is running / r5 / seq4. There are 247 Node events, 24 browser records and 7 DOM projections; invalid/omitted=0 and all projections match their accepted source. A container's answer_present flag is not used as proof of answer bytes; the recorded validated/applied event establishes the increment.

API periodic snapshot is on its own perf_counter_ns epoch, read after the assertion. It has 96 records, invalid/omitted=0, no contention; the last records include answer_delta frame_offered, asgi_send_returned and owner_read_entered. No Provider/Tutor terminal commit or completed frame is recorded. This is not proof of a worker exception, lockup or final persisted state after the capture. API source time is not placed inside the Node assertion deadline.

The post-failure Run diagnostic read records `state=failed`, while synthetic runtime received=1 / validated=1 / invalid=0. Actual fixed source `tutorDiagnostic.ts:167–175` uses a 400 ms GET timeout within the 500 ms outer observation cap, then collapses GET/HTTP/JSON/safeRun errors to that same failed marker. Its post-observation duration is 409.716265 ms; no exception class or HTTP status was preserved. The duration is compatible with multiple causes and does not prove timeout. The marker is not Run.failed. Final worker state and the precise read failure kind remain **UNKNOWN**.

## Comparison and next evidence boundary

The 8701 PR has the same observed answer_delta-before-freeze pattern as the two 4cc failures. Original a944 captures instead had no response to the last SSE before freeze. The current 8701 push proves a single original-case PASS in its own log, but has no uploaded internal success timeline. These different sources cannot be merged into a synthetic sequence, and a current PASS does not close earlier failures or establish a fix.

No product or test repair is claimed. Further discriminating evidence would require independently reviewed, default-off synthetic-only observation: a safe read-failure category and same-API-clock guard/DB/first-chunk/consume/finish entry/commit-return markers, with unchanged request counts and original 5-second assertion. Existing missing post-read information cannot be reconstructed by inference, and reducing checks or increasing the assertion timeout would not explain these original failures.

Sole norm remains PRODUCT_DESIGN.md SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`, especially lines593–595/1409 for persisted terminal/SSE and R-29/942 for separate evidence levels. No real provider/key or runtime database was accessed. All originals here are private; public derivatives require exact span mapping, unchanged scanner and offline raw replay. Successful current CI stages are not a whole-platform, real-model or teaching-quality acceptance claim.
