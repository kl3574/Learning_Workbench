# Learning-state held-route cleanup diagnosis

Spec: PRODUCT_DESIGN.md 3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`; requirement R-29. Base `1fffd996e9334f7f28dcdeb970430c9aa4052ee3`; fix `e618f3d919656206c6428f1bb7a41f34c3fd6136`.

Only `tests/e2e/learning-state.spec.ts:42` changes: teardown uses `page.unrouteAll({ behavior: 'wait' })` after releasing the gate. It waits for pending real route callbacks before removing interception; it neither ignores callback errors nor changes timeout, retry, product behavior or the original test assertions. No model/provider call, secret access, schema migration, external publication or full native-suite rerun occurred.

## Original evidence and precise scope

The sole original native run is retained in `m62-sep28-native-gate-v1`, 92 PASS / 9 FAIL, original run-log SHA `573bde09580919283cf778bed18e29ff32a321ac78e93eca3151e5ae4fa6ea22`. Its learning-state case has two distinct errors: `route.fulfill: Route is already handled!` at line 40, and another page's independent-mode text not found within 5 seconds at line 42. The blank failure screenshot adds no causal timing evidence.

This fix addresses only the route teardown secondary error. The original other-page visibility timeout remains UNKNOWN, and the other eight native failures remain unchanged. The original case was already PASS in one isolated before run, so its later PASS is not reported as a historical-failure reproduction/fix.

## Feedback and diagnosis

01: unchanged original single native case, 1 PASS in 7.1 seconds. It uses original test/runtime/expect timeouts, private dynamic-port RestartRuntime, and a private config omitting unrelated fixed-port server startup.

02: actual Chromium/installed Playwright minimal copy of the held-response/cleanup pattern, three fixed iterations: all three `route.fulfill: Route is already handled!`, exit 1. No application, active assessment, AbortController, multiple requests or closed target was necessary. The first recorder omitted the external probe from before/after input manifests; its source is retained with explicit post-run-only capture metadata. No stronger source-freeze claim is made for that probe.

Before further controls, ranked hypotheses were stated: (1) removal of the active interception automatically continues the request before its released callback fulfils; (2) duplicate callback invocation; (3) request cancellation/response disposal. The minimal reproduction records one callback per still-open page and does not cancel requests, removing the latter two as necessary conditions.

03: an improved, source-bound probe extracts and executes the actual test's finally block, not a separately rewritten cleanup implementation. External probe and config bytes are now included in before/after input manifests. All three fixed iterations reproduce the exact error, exit 1, log SHA `233d7f65710833ce752d05f461d962c2b6dba1c35cde023c016e58fea8360bdb`.

The locally installed Playwright implementation corroborates the mechanism: removing the current server route handler calls `continue({ isFallback: true })`; continuing sets the handled state, so a later fulfil rejects it. Default `unroute` does not wait for active callbacks. The `wait` mode drains active handler invocations before updating interception patterns. Dependency bytes/version have a separately labelled post-run readback.

04: only the actual test cleanup call changes to waiting mode; the unchanged extraction probe executes it on actual Chromium. All three iterations pass. Every event ledger places fulfil completion before removal completion. Log SHA `ffc1c1dca3281c126d02d65a3ae928c6172ecf3d00ac83f56ae64d48343548d1`.

05: the original complete single native case runs once after the fix: 1 PASS in 7.1 seconds, log SHA `34956570469b23b02a835285dc53e0296ce489a79ce85a057a434e44c8897937`. No assertion, timeout, retry or error suppression changed. 06: git diff --check exits 0.

All six runs retain complete log/receipt/before/after inputs. Each run's 981 repository inputs independently matches exact Git blob bytes at its declared before/fix commit. Probe03+04 directly exercise the actual inline teardown in the regression evidence; no production helper or copied permanent test implementation was introduced for this one-callsite test change. The private probes remain clearly named diagnostic evidence, not shipped application code. No DEBUG instrumentation entered repository source.

## Remaining work

Root may independently review/adopt the single-file commit. Continue original other-page visibility diagnosis using an actual timing/network ledger if it recurs; do not infer it was repaired by this teardown change. Full native suite, CI, deployment, agent model-answer quality and platform completion are not validated by this slice.
