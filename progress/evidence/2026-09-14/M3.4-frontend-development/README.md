# M3.4 frontend development evidence

This package records bounded development checks, not root exact-source full-suite acceptance or content-review approval. All browser data and screenshots use the project's original synthetic assessment fixture. No provider was called, no mastery probability was computed, and normal imported reference answers remained needs_review.

## Actual checks

| Captured run | Actual result | Scope |
|---|---|---|
| First type check | Failed, 3 TypeScript diagnostics | New required history/policy fields were missing from old typed fixtures, plus an unused import. |
| Second type check | Passed | Strict generated DTOs bound and typed fixtures updated. |
| Focused unit rounds | 47/9 files, then 50/11 files passed | Overlapping grading/review/target tests, not additive independent counts. |
| Native round 1 | 0 passed, 2 failed | The two new actual HTTP/worker/browser scenarios were still under harness development. |
| Native round 2 | 1 passed, 1 failed | Actual cross-page independent-policy boundary passed; first scenario reached both screenshots and failed on the close-button name. |
| Native round 3 | 2 passed, 17.8 seconds | Original submitted Unicode answers/steps; real grade 1/2; complete immutable history; saved old-version reload; exact Reader parent/hash navigation; 390px Agent drawer; current Evidence IDs; actual delayed old response after another page starts an independent attempt. |
| Complete web units | 212 tests / 33 files passed, 3.06 seconds | Current frontend development source. |
| Lint | Both captured checks passed | TypeScript strict/unused checks. |
| Build | Passed | Vite retains its >500kB chunk warning: approximately 619kB entry and 2.94MB Markdown/MathJax asset, uncompressed. |

The native runtime authenticates through the actual launcher, imports the original learnpack through the real UI, and uses isolated real SQLite/API/worker/Chrome instances. Route interception only delays actual server responses; it does not fabricate parser, grading or policy responses. Native round 3 includes browser-page reload, not an actual API-process restart; root restart tests are separate.

## Failed harness assumptions and corrections

1. Round 1 scenario 1 read the Reader URL immediately after clicking a material link. The production action first verifies the frozen course/lesson/block chain and body hash asynchronously. The URL was still the review URL, so the test parsed null. The corrected test waits for the actual Reader URL, then preserves all exact course/lesson/block assertions.
2. Round 1 scenario 2 treated mounting the history section as completion of the initial result read. It installed the delayed-response route before that initial read finished, then tried to click a still-disabled refresh button. The corrected setup waits for the actual current version 2 and enabled refresh control before delaying a new read. The late-response and real independent-policy assertions remain.
3. Round 2 scenario 1 used the literal name “关闭 Agent 助教”; the existing native control is “关闭Agent 助教”. Only the test locator was corrected. The original close behavior and 10-second action limit were not changed.

These are diagnoses of the locally observed development failures, not claims about unrelated earlier CI failures. All raw logs and error contexts remain at their original local paths. Public error extracts contain only the first Error details fenced block; full DOM dumps and Test source attachments are intentionally excluded.

## Actual visual review

All five included PNGs were opened with the image viewer during development; PNG bytes are unchanged. Before 1440 showed all five current-feedback items above the history section, requiring a long jump, with redundant inherited heading spacing. The reviewed implementation limits detailed feedback to the selected question, hides current feedback when an older summary is selected, and gives history headings explicit spacing. The intermediate 390 screenshot also exposed raw assessment IDs after reload; the final view uses truthful generic “测试范围 / 测试作答 / 测试复盘” fallback labels until titles resolve. Exact refs remain in their details.

The final 1440 and 390 screenshots show the selected old null-score version and specific exclusion reasons, without suggesting a mastery probability. The 390 scenario asserts no horizontal overflow in the central scroll pane and exercises opening and closing the actual Agent drawer. Screenshots are cropped to the real browser viewport; scrollable content below the visible area remains available. They are not full-page or native-zoom evidence.

## Source binding and commands

`owned-source-after-native.json` is the original 26-file source hash capture made after native round 3; base HEAD identifies the starting checkout, not a commit containing these then-dirty changes. Its aggregate hashes sorted lines `sha256 + two spaces + repository-relative path + LF`. `source-publication-readback.json` compares those captured bytes with live bytes during packaging. No earlier full-repository source pin was captured for these development rounds; none is invented. Root's exact-checkout gates and CI must establish final committed-source coverage separately.

Commands were run from the repository root:

- `bash scripts/node.sh npm --prefix apps/web run typecheck`
- `bash scripts/node.sh npm --prefix apps/web run test -- src/features/review src/features/grading src/features/assessment/target.test.ts`
- `bash scripts/node.sh npm --prefix apps/web run test`
- `bash scripts/node.sh npm --prefix apps/web run lint`
- `bash scripts/node.sh npm --prefix apps/web run build`
- `bash scripts/node.sh apps/web/node_modules/.bin/playwright test --config=<temporary-config>`

The included sanitized native config is the final captured config. Its output-directory value changed between the three runs; earlier config bytes were not independently preserved. Personal workspace paths and Node process IDs in logs/config are replaced, while raw hashes remain in `manifest.json`. No full browser trace, profile, database, credential, request cookie, token value, or original error-context DOM is copied. Scanner checks supplement this manual provenance review and do not certify arbitrary prose automatically.
