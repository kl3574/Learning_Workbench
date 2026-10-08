# Fixed 486939 combined Review gate

Fixed detached source: 4869393654446c1dfcb0da97b9dca5fa7429b36f. Isolated worktree: $HOME/.cache/learning-workbench-acceptance/m63-review-combined-486939-oct05. PRODUCT_DESIGN v3.0.15 SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. No engineering file was edited, staged, merged or pushed by this task.

The Review source and CI workflow are byte-identical to 905eccdd667001ec8e545cb534d5282ef6949836. The eight session interrupt UI paths are byte-identical to 22dade7996f13634202250ef5e1c05dc976214a5. The first-parent 5d8bc7ef4f34bd08e6327053e874ed062a935ae8 comparison changes only tests/e2e/review.spec.ts and .github/workflows/ci.yml; 1523 other engineering inputs and progress bytes remain unchanged. SOURCE_BINDINGS.json records exact per-path hashes.

Static-list-01 ran the requested bare selector review.spec.ts. Playwright command exit0 listed three tests in two files because draft-review.spec.ts also matched. The wrapper's exactly-two guard exited1, before any business test or Chrome execution. Original runner, command, log, failure.json and receipt remain unchanged; LIST_SELECTION_FAILURE.json records the actual wrapper outcome. This is a list-only selector failure, not a product failure.

Root authorized the precise file selector in a new runner. Static-list-02 actually listed exactly review.spec.ts:36 and :187, two tests in one file, command/wrapper0. The absolute new runner is run-exact-file.py, SHA b756b15c48239e6eefcaf41e19d4a0a27c75576cdfc8bd825cc8a5ad5de5b39a. Both runners create unique stages and refuse to overwrite key files; the native run requires the successful two-test list receipt and matching runner hash. Only this first real business execution followed:

```
bash scripts/node.sh npm --prefix apps/web run test:e2e -- tests/e2e/review.spec.ts
```

Native-run-02: 2 PASS, individual durations 15.4s and 10.7s, Playwright total 29.1s. Actual command and wrapper exit0. UTC 2026-10-04T20:33:00.246644Z to 2026-10-04T20:33:29.780717Z; wrapper elapsed29.53395212299074s. Original log SHA 8cdedf6526644841530bcefbbf73724d0a22c1e3887a4cc4721dd823f6198102. This was one execution of the two original cases, with original 30000ms per-test budget, one worker, default zero retries and unchanged locators/assertions/config. No additional business test or retry was run. The original Playwright lifecycle and owned fixture cleanup returned successfully; no separate host/process probe was performed.

All three stages bind full1525 engineering inputs before/after; each pair is exact and clean at the fixed detached head. The final full Git/working manifest is also exact. The seven complete maps provide10675 input bindings. Private short TMPDIR/data/results use mode0700. Dependencies use existing read-only reuse links; Vite caches are separate local directories. No dependency installation occurred.

The first case's payload-free timing is67615bytes, SHA1df8aebd7c78d9d53ad6e70e228eedde0e5cca4e248e54ce7b4028769651fadf. It contains43 phases and306 HTTP metadata rows, dropped0/0, observed timeout30000/retry0. Body-finally is12817.295382ms; Review return starts11717.039141ms, click returns11740.230710ms, and the original mobile-screenshot statement starts12554.016560ms. Timing excludes fixture setup and page.request polling; HTTP headers do not establish JSON/React completion. Static route/status counts include a403 Import read and412 Workbench save, without interpreting their bodies or attributing a cause.

The second case's277byte late-response-phases.json, SHA13adfbe64a73dd353092ab0fa0d2a9e68a154e4fb9315083de0d37898560e13f, records exactly one delayed captured200, other independent page visible, fulfillment/handler completion, and the finite client-chain marker. The original two zero-count assertions and current409 assertion passed as part of the unchanged test. The marker does not claim all React rendering/effects have completed.

These results establish only the new486 two-case combination gate. Original c02/905 seals remain unchanged; 905's original native status stays NOT_RUN. The prior full133 PASS remains scoped to22dade, not486. Both original public CI132PASS/1FAIL events remain failures with unique cause UNKNOWN. Instrumentation adds synchronous work and can change scheduling; this local PASS is not a unique-cause diagnosis or CI fix.

Actual model, Provider, Codex CLI and host-tool execution were not invoked by this bounded task and are NOT_RUN coverage. No new global network/action sentinel or all-process zero-count proof is claimed. No actual key was configured and no remote action was requested.

Only SAFE_CANDIDATES.json exact entries are proposed for root readback. They contain private runner source, metadata, ordinary logs, receipts and complete engineering maps, copied without transformation. Timing/late-phase closed shapes and every variable string domain were checked against fixed static values; ordinary logs were read. Screenshots, actual-review-history.json, DB, browser profile, cookie, key, cache, ZIP and all unspecified runtime data were neither read nor admitted. No private runtime directory is recursively copied.
