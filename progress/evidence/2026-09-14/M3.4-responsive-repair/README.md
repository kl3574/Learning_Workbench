# M3.4 narrow viewport repair development evidence

This package records a bounded layout diagnosis and focused checks. It is not final exact-source/full-suite acceptance. Parent retains the original exact 47e02d9 full run: 65 passed, one viewport failure; its supplied error-context hash is retained in the manifest. The first unmodified isolated replay passed. No original failing-run event ledger exists, so the controlled mechanism below is not asserted to be the unique cause of that earlier failure.

## Observed mechanism and minimal repair

The first observer found a real resize interval in which the browser viewport was 390px wide while React still supplied desktop columns: the central scroll pane was 0px wide. Its settled paragraph was only 56px high and section 169px, ruling out an intrinsically oversized submit section. The grading component is a following sibling, not part of the submit section. No remount or focus change was observed.

A controlled native replay deferred actual registered resize listeners, preserving browser layout and actual API/worker behavior. With original CSS, the original section scroll ran against width 0 and a 1439px-high section. Releasing the same listeners restored width 390, clamped the huge scroll offset to the bottom, and left the paragraph outside its scroll viewport; the unchanged 5000ms viewport assertion failed. Adding only a CSS media rule produced green under the same controlled schedule.

The repair inserts `.workbench-grid{grid-template-columns:0 0 minmax(0,1fr) 0 0}` into the existing max-width 819px query. Browser CSS now determines narrow grid width before React resize callbacks. No existing assessment assertion, timeout, policy, grade, draft, or scroll-restoration logic was changed. Breakpoints at 820px and above do not match the new rule.

The permanent native regression imports the original synthetic assessment through real UI, submits through the real backend/worker, observes real needs_review, and then controls only delivery of native resize listeners. With old CSS it recorded width 0, scrollTop 9936 before callbacks, and paragraph y -992 after callbacks. With fixed CSS it recorded width 390, scrollTop 908 before and after callbacks, and the paragraph inside y 761.7–817.7 of the central viewport. The before/after PNGs were actually opened with the image viewer: before shows the scoring list at its bottom with the submission explanation absent; after shows the submission heading and complete explanation. Image bytes are unchanged; these are normal 390×844 browser viewports, not zoom evidence.

## All captured run outcomes

| Run | Actual result and limitation |
|---|---|
| First temporary config | Invalid string grep option; no tests executed. |
| Unmodified isolated old case | 1 passed, 6.5s; no conclusion about the original full-run failure. |
| Instrumented old case | 1 passed, 6.7s; actual responsive interval observed. |
| Controlled delayed listeners / original CSS | 1 failed on original paragraph viewport assertion. |
| Same schedule / runtime CSS override | 1 passed, 6.5s; only proposed CSS added at runtime. |
| Misnamed permanent-red config | Accidentally selected the old assessment case; 1 passed, 6.6s. This is not permanent-test RED. |
| Correct permanent test / original CSS | 1 failed: width 0 and post-listener viewport ratio 0. |
| Same permanent test bytes / fixed CSS | 1 passed, 5.8s. |
| Original old case / fixed CSS | 1 passed, 6.6s; original scroll and viewport assertions unchanged. |
| Existing frontend lint command | Passed; its configured scope is apps/web, not native test files. |
| Parent targeted strict native type check | Passed with exit 0; 202 listed dependencies include the corrected new test. Temporary ambient binding resolves existing relative Playwright .mjs imports to the installed official index.d.ts without an `any` fallback or suppressed diagnostics. This is a targeted extra, not a complete native-test type gate. |
| Extra standalone strict native tsc attempt | Failed. New direct Window casts generated TS2352; existing .mjs declaration resolution also generated helper implicit-any diagnostics. This nonstandard extra command is not reported as a passed configured gate. |

The two configuration mistakes and failed extra type check are retained. Parent subsequently changed only the new test's type declaration to augment Window and removed the casts; parent `stripTypeScriptTypes` comparison records byte-identical emitted JavaScript. The native RED/GREEN here remains bound to original test SHA 7cb2ab15…, not retrospectively relabeled as execution on the later type-declaration bytes. Parent's separate targeted strict check is bound to a30874f9… at implementation commit 63e4786; its exact receipt, declaration binding, configuration, output, 202-file list, prior test source and runtime-equivalence proof are included with raw/public hashes.

## Source scope, commands and publication

`source/source-before.json` and matching after files cover eight observed original relevant files, not a whole-repository pin. The active three-file captures include original/fixed CSS, the new regression, and the unchanged old assessment test. Original CSS SHA is 3489b987…; fixed CSS is 0119af03…; old assessment test stays 4bdde8c2…. `active-final-freeze.json` predates the parent-only type correction. Parent owns final source commits, independent reviews and full gates.

Native commands use `bash scripts/node.sh apps/web/node_modules/.bin/playwright test --config=<captured temporary config>`. The sanitized controlled specs/configs are included; replace `<workspace>`, `<exact-checkout>` and `<probe>` with the corresponding local paths to replay. The permanent regression source lives in the repository; parent preserved its pre-type-correction bytes locally and matched their SHA with both native captures. Frontend lint used `bash scripts/node.sh npm --prefix apps/web run lint`. The failed additional command was `bash scripts/node.sh apps/web/node_modules/.bin/tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext --moduleResolution bundler --allowImportingTsExtensions --types node --typeRoots apps/web/node_modules/@types tests/e2e/responsive-layout.spec.ts`.

Every published payload is checked with the repository publication scanner and manually scoped to original synthetic UI evidence. Logs normalize local personal paths and Node process IDs; manifest entries preserve both raw and public hashes. Geometry ledgers are explicitly filtered event projections, not claimed full timelines. Original raw logs, ledgers, error contexts, and screenshots remain privately at their original locations. No full DOM dump, browser profile, database, bootstrap value or credential is included. Scanner checks supplement the manual review and do not guarantee arbitrary prose detection.
