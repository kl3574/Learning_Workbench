# M6.3 Review late-response client barrier — bounded owner evidence

Fixed source: `22eb3168ab9aed7d7e7d50d437919feebb75ba6d`, isolated from `d69de81045ff6c9ff2f345643f0fd412e2d108fb`. Only `tests/e2e/review.spec.ts`, `tests/e2e/responseJsonBarrier.ts` and `tests/e2e/responseJsonBarrier.check.ts` changed. Sole PRODUCT_DESIGN remains v3.0.15 / SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. Production code, generated client, norm, original native config, timeouts, retries and existing locators are unchanged. No canonical edits.

## Fixed-head results

| Named check | Actual terminal result | UTC end | Log SHA256 |
| --- | --- | --- | --- |
| exact-review | 2 PASS; child exit 0, wrapper 0; original tracked native config, exactly the two Review business tests | 2026-10-04T18:16:41.808937Z | fb459bc734096415af2a06893f1b338ee324949acd9cf73813223b40c14986dc |
| exact-mechanism | 3 PASS; exit 0; separate controlled loopback mechanism tests | 2026-10-04T18:16:13.875706Z | 024d0307eb4cd62590cab64c29772596097ec3e5e7a4ce469e94290fe46be4de |
| exact-types | bounded strict TypeScript, exit 0 | 2026-10-04T18:16:12.711176Z | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| exact-web-strict | existing Web lint/strict TypeScript, exit 0 | 2026-10-04T18:16:13.363471Z | b9df407f06dd3350bcb5d41df640c2603d5d70f268d57fe256fe1159da11cc68 |
| exact-diff | git diff --check base..HEAD, exit 0 | 2026-10-04T18:20:27.683818Z | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

Actual Review command: `bash scripts/node.sh apps/web/node_modules/.bin/playwright test --config tests/e2e/playwright.config.ts '(^|/)review\.spec\.ts$'`. The anchored file regex avoids selecting a different `draft-review.spec.ts`; it does not change either original Review business test. The three `.check.ts` mechanism cases are only selected by the explicit private config and do not increase the ordinary `*.spec.ts` full-suite count. No sleep, new retry, enlarged timeout or production hook was introduced.

The Review phase record shows exactly one held request, captured status 200, another page visibly in a real independent attempt, the owned handler's fulfillment, handler drain, then JSON/client-chain observation. The original two zero-count DOM assertions and the original current backend 409 assertion then passed. The first Review case also retained real local upload/worker/manual grading/history, original submission, selected revision after reload, Reader target and evidence assertions. Its two original 1440/390 screenshots were visually read; they contain synthetic grading history, no credential or private user material. They do not independently prove the second test's invisible-state assertion.

## What the barrier proves

`observeNextResponseJson` watches only the next exact URL and GET, restores fetch when claiming it, and instruments only that returned Response's first json call. It does not initiate a request, clone or inspect the body, persist academic payload, or substitute either original promise/value/error. A MessageChannel task is posted only after the JSON promise settles. The task follows the current finite microtask adoption chain.

The controlled browser checks execute the actual `apps/web/src/api/client.ts` and generated client against an inert loopback fixture. While a controlled JSON gate is held, route fulfillment and unrouteAll(wait) have completed but client processing has not. The new barrier remains pending. After release, it observes the actual transport/generated-client continuation with identical value or error; a third case verifies original fetch/json promise identity, an unrelated request left alone and exactly one target request. The fixture's DOM assignment is synchronous and representative; it is not the production React hook.

Static readback of the unchanged actual chain (`api/client.ts`, generated `createApiClient`, `features/grading/useGradingResult.ts`) establishes that the hook's first `current()` after the result await, or its catch/current branch, is synchronous after promise adoption. The real Review case exercises that actual hook. This is a bounded JSON/client synchronous-branch barrier, **not** proof that all React scheduler renders/effects have flushed. Existing DOM assertions are retained after the marker; no global React completion claim is made.

## Original RED and retained failures

The complete original mechanism test file is byte-identical between `a5c11f7b` RED and `7f50da35` GREEN: SHA256 `9ad9d8bcb579643d2b88e51e4ff8aadb47abf77aee3f1924305c6275ea81265f`. RED actually ran two browser cases and both failed the behavioral assertion: handler-only completion was already true while JSON had started and client continuation remained false. It was not an import/type failure. The same full test file then passed both cases using the new observer. The later final file adds a third identity case and safe phase instrumentation; it is not described as the original entire RED file.

| Stage/source | Original outcome retained |
| --- | --- |
| red-handler / a5c11f7b | Node wrapper preflight exit 1: missing isolated .toolchain link; browser/product NOT_RUN. Existing dependency symlink added, no install. |
| red-handler-02 / a5c11f7b | 2 behavioral FAIL; raw log SHA256 459c650f1b7ada76c2e18109de17b6b7226c9b9efc5b4674817ff45748390a5d. |
| green-client / 7f50da35 | Same full original test file: 2 PASS. |
| fixed-mechanism / 036f59b4 | 2 PASS, 1 FAIL: added identity case timed out at the original 30 seconds. Cause not established. |
| review-native / 036f59b4 | Original Review 2 PASS at that source, separate from final source. |
| identity-observation / 4bd40625 | Added payload-free phase record; identity single case 1 PASS. This does not establish the prior timeout's cause. |
| focused-types / 4bd40625 | Actual TS2683 implicit-this error; retained. 480b392a adds the transparent wrapper's this type only. |
| final-review / 480b392a | 1 PASS, 1 FAIL: Route is already handled! at route.fulfill. Raw log SHA256 7e68637238484f21fbac2e7c76d90775e6014659b73d065e4e5ac38946d7df04. Not upgraded by later passes. |
| route-phase / f0173107 | Single Review case 1 PASS; actual safe phase trace held three GETs: original 200 and two subsequent 409s. |
| exact-review / 22eb3168 | Final narrow original two cases 2 PASS; exactly one held 200, original current 409 remains. |

The three-GET observation demonstrates that the former interceptor covered more than the intended old response. Final `times: 1` holds only that original request; because the route unregisters on entry, the test explicitly awaits its own handler promise as well as unrouteAll(wait). It then waits for JSON consumption and the bounded client continuation. This is a test-scope correction. Neither this observation nor a later pass is asserted to be the unique cause of the historical RouteAlreadyHandled failure. Root's original 412 full-suite failure remains separate with cause UNKNOWN; root's d69 full 133 PASS belongs to d69, not this source.

## Provenance and publication boundary

`SOURCE_BINDINGS.json` and eight complete Git maps bind 12,189 path/object records, 1,511 distinct Git blob bytes and all seven implementation commits plus the base. All 21 original stages retain command, receipt, raw log and full before/after maps. Their 64,004 map records were checked against those fixed Git objects, with exact source equality in each stage. The final live tree has all 1,524 nonprogress inputs exact; 1,521 of the base's 1,522 inputs are unchanged, with one changed test and two new test files. Tracked progress history was not altered.

The initial runner bound test files and full repository inputs but did not separately hash its private mechanism/type config in its receipts. The later `run-bound.py` adds those explicit before/after hashes. All final five named checks use that runner and bind the three private config/type files unchanged. The original receipts are preserved, not retroactively enlarged. Supplemental focused type checking uses the installed official Playwright types for the repository's existing .mjs import convention; it is not a claim that an additional whole-e2e type gate exists.

Publication candidates are an explicit allowlist, not a recursive runtime copy. Candidate text may only replace the literal `${HOME}` prefix with `${HOME}`; each transformation is byte-verified and both hashes recorded. PNGs and repository source bytes remain exact. Successful short logs and the inert mechanism RED log were individually read. Other failed raw logs, runtime profiles, databases, keys, caches, ZIPs and TMPDIR contents remain private; their original raw log hashes and qualified outcomes remain in receipts/history. The two admitted PNGs were viewed at their original dimensions.

Only local synthetic tests and existing software checks ran. There was no actual Codex/model execution, external model cost, physical operation, host-security probe, source push or remote publication. No full Web unit suite/full Python/full native suite was run by this owner for this test-only change, and no whole M6.3 acceptance is claimed. Independent review of this fixed delta is pending.
