# PR54 Tutor failure: bounded independent read

This report analyzes the captured pull-request browser job 106614412143 in run 35686445167, attempt 1. The original result remains **98 passed, 1 failed**, with the original **5000 ms** assertion at `tests/e2e/tutor.spec.ts:195`. No rerun, source edit, timeout change, backend repair, model invocation, or private database read was performed. Root cause remains unestablished.

## Identity and evidence

The CI checkout log names `6aa987b3bdb2610ad369775f01ac743405e5ce86`, rather than assuming workflow head metadata names the checkout. A recorded read-only GitHub commit GET confirms that merge commit's tree is `ada44be07e92c82466e9874cfb5c5a4afb935d4f`, exactly the local Git tree of `2cf5caa3f966f919997c37b64d0bbf0e332438df`. Eight cited source files match that tree byte-for-byte.

The 282475-byte artifact ZIP hashes to `f55eb0053d8c0f4eaeac9eb866e67615053eec9652a1bf9daafe0b5d95e4cfde`, matching the captured GitHub artifact digest. All four ZIP members were rehashed and compared to their extracted bytes. The failure case diagnostic is **35562 bytes**, SHA `28e2bdae4813d2a1a85156141a35d75c02ab759d5b90a49f69d72f5e3bebaded`. The separate **1752-byte** JSON belongs to the diagnostic helper's own intentional failure test and is not evidence of this Tutor case. The ZIP contains no trace archive, server log, database, or failed-case final success JSON.

## Actual sequence

Times below are milliseconds since this observer began at 2026-09-22T04:36:53.049Z. They are arrival times in one Node clock, not server execution times.

| Observed fact | Time / meaning |
| --- | --- |
| Original completed-heading assertion begins | 8942.015 |
| Consent POST request 67 / HTTP 201 / finished | 8964.271 / 9239.918 / 9240.490 |
| Exact Run GET 69 / HTTP 200 / finished | 9255.572 / 9534.156 / 9535.265; body was not captured |
| Final SSE request 73, after_seq=3 | 9537.107 |
| Last delivered DOM snapshot | 9545.010: queued, observing, grant acknowledged, consent linked |
| Final SSE request 73 HTTP 200 | 13520.530; 3983.423 after request, 426.305 before assertion freeze |
| Original failure frozen | 13946.835; assertion elapsed 5004.820 |
| Post-failure probes | 13946.853–14350.677; Run probe failed; runtime-file probe completed with counters 1 received / 1 validated / 0 invalid |

The frozen observation has 238 events and zero omitted events. The last SSE request has no finished/failed callback before freezing and no captured frames. Three earlier streams (54, 58, 65) have `net::ERR_ABORTED`; none is the final stream 73. Source `useTutor.ts:36–64` explicitly stops/replaces observers when rereading and breaks to refresh on selected events. These facts do not identify an unexpected cancellation of stream 73, a parser fault, or a server terminal state.

`error-context.md:123–132` independently shows the queued heading, the observing status and the fixed no-answer placeholder. The screenshot was visually inspected: it shows the real Reader and the consent panel's acknowledged/current/linked state. The right panel is scrolled below the task heading; the image cannot independently establish that heading's state or a server failure.

## What state=failed means

**`post_assertion.run.state="failed"` means the read probe threw, not that the Run had status failed.** `tutorDiagnostic.ts:98–105` performs an API-request GET with a 400 ms timeout, rejects non-OK HTTP, then parses JSON. `read()` catches any exception into the same failed label. Line 122 additionally validates the safe projection (run identity, recognized status, last sequence, job revision). A missing bound Run also takes this path, though this test binds its accepted id at line 179. A true successful observation of a failed Run would be shaped as `state="complete", value.status="failed"`.

The probe returned no value, HTTP status, exception class, or failure stage. Its 403.824 ms total post window is compatible with the inner 400 ms request timeout but **does not prove that cause**. The outer 500 ms unresolved-probe fallback is a different `state="timeout"` label. Runtime `state="complete"` means the local control-file projection was read successfully; it is not a Provider completion receipt or a Tutor completed state (`tutorRuntime.ts:149–152`, `tutor_native_fixture.py:47–69`). Its later 1/1/0 counters do not prove when the request occurred relative to the assertion deadline, nor that output was consumed or committed.

A second diagnostic limitation is concrete: `answer_present=true` is the nonempty text of the answer container (`tutorDiagnostic.ts:87`), and `TutorEvidence.tsx:8` puts the fixed no-answer placeholder in that container when answer text is empty. Here the DOM dump explicitly contains that placeholder. This boolean must not be cited as evidence that model answer bytes were delivered.

## Minimum next diagnosis, not executed

Preserve the original 5000 ms assertion and frozen snapshot. On a separately authorized diagnostic attempt, distinguish the Run probe stages with a small allowlisted result: request start/settle in the same observer clock; timeout/transport, non-OK HTTP status, JSON decoding, or invalid safe projection. Do not serialize arbitrary exception messages, bodies, cookies, or headers. Keep post-assertion facts explicitly later, even if a later read reports completed.

If that bounded probe still cannot locate the boundary, capture only safe same-Run metadata at owner commit, server SSE emission, browser event acceptance, and snapshot acceptance: stage, monotonic sequence, state/type, safe reason enum, and observer receipt time. Local clocks must retain their own domains; compare causally linked sequence identities rather than subtracting unrelated clocks. This separates backend not committed, transport not delivered, decoder rejected, and UI not accepted without claiming any of them happened here. The currently missing backend/Provider ledger and frame evidence cannot be recovered from the four-member archive.

This report makes no claim about hosted-model capability, answer correctness, learning outcomes, M6.1 completion, or the M5.4 blocker. The debugging skill's reproduction/fix phases were intentionally omitted because this task authorized artifact-only diagnosis and explicitly prohibited new test runs.
