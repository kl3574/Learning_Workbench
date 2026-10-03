# M6.2 exact historical block comparison — implementation evidence

The implemented slice is a read-only comparison of two explicitly selected historical revisions of one real Reader block. The candidate is `05aa1af2fd000654b0d7b62e5eae32998c81d43f`, based on `833f0a84168638ba5ce421c70cd2f20a71e45e48`. It changes 12 files. Independent review and parent integration are pending. This report is the implementer's execution record, not independent approval.

## Normative scope and implementation

The sole product/engineering specification is PRODUCT_DESIGN.md, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`: R-04/R-09/R-21/R-28/R-29, §§4.3, 6.5, 9.1, 15.2, 19.3 and 20.1–20.2, plus existing exact Content/history GET contracts. This is a bounded part of those requirements, not completion of R-21 or M6.2.

ReaderDocument mounts an initially closed comparison below each real block's SourcePanel. The new feature uses the existing generated client, registered session/history/metadata/body GETs and closed OpenAPI shape checker. It verifies the chosen block entity/id/revision, strong quoted metadata ETag, exact projection ref, full ContentBlock metadata SHA and decoded text re-encoded to UTF-8 against body SHA and ETag. The metadata canonicalization argument is limited to this closed model's fixed ASCII keys and safe integer revisions with all persisted defaults present; it is not a general Python/JavaScript float or Unicode-key canonicalizer. Current provenance is the authorized server projection: its ETag authenticates block metadata, not independent source verification or approval. The existing response.text transport is not an independent original-byte download; decoding changes fail the hash check.

The user chooses both versions explicitly. Workspace+block ID owns the selection, so a changed current revision does not replace chosen refs. Collapse retains this mounted page's choices and clears body results; reopening does not automatically read bodies. Target/workspace/access changes clear old state and reject late responses. Reads check current session/Policy before and after completion, including role changes that could alter provenance. Displayed results receive sequential permission checks every two seconds; a permission check unresolved for two further seconds clears content. Focus/visibility invalidation clears results. Local access generation changes clear immediately. Cross-profile server changes are detected by actual reads; instantaneous remote notifications or retraction of previously read material are not claimed. Open-book material remains readable under the existing server policy; active independent attempts are rejected.

The line comparison uses common complete-line prefix/suffix and marks the whole changed middle. It is O(n+m), not a quadratic minimal-edit algorithm. More than 100,000 combined UTF-16 units or 2,000 combined lines yields intact side-by-side originals with an explicit limit message. No trimming, newline/Unicode normalization, or formula equivalence inference occurs. History paging is explicit, strictly descending, rejects duplicate/conflicting pages and is bounded to 200 options, with remaining history stated. Existing Reader/note editing and four navigation entries are unchanged. No backend, generated contract, migrations, public review_state vocabulary or external services changed.

## Executed evidence

`run-ledger.json` preserves every exact command, HEAD, exit code, time, full log hash and declared source input binding. Each stage has original `run.log`, `receipt.json`, `inputs-before.json`, and `inputs-after.json`; source bytes are retained by SHA in `source-pool/`. Development stages intentionally contain changed/untracked input bytes relative to their then-HEAD. The verification checks those facts; it does not relabel them clean Git inputs.

| Stages | Actual result and interpretation |
| --- | --- |
| 01 → 03 | Missing exact-read implementation RED; stage 02 is an additional fixture URL query-order failure; stage 03 is 1 PASS after matching generated query ordering. |
| 04 → 05 | 2 real failures accepted modified metadata under an old ref/ETag and an unknown projection field; strict shape/full metadata hash repair gives 3 PASS. |
| 06 → 07 | Missing bounded-diff implementation: 2 FAIL → 2 PASS. |
| 08 → 09 | Missing selection UI: 1 FAIL → 1 PASS. |
| 10 | 23 PASS covering exact rejection, bounded diff and ownership/selection/late results. |
| 11 → 12 | Real role-change failure retained role-dependent content across the before/after read boundary; corrected permission-basis comparison gives 24 PASS across three new test files. |
| 13 → 14 | Real current-Policy failure retained already displayed content after another profile began a test; sequential current permission checks give 25 PASS. |
| 15 → 16 | Two fixture literal-widening TypeScript diagnostics retained; fixture annotations corrected; strict TypeScript including noUnused checks PASS. |
| 17 | Fixed `b20f4aa9110829cf096bcae21e980e95b358a048`: 62 Reader tests PASS in five files (25 new plus 37 existing). |
| 18 | Same fixed source: TypeScript/Vite build PASS, 753 modules; normal large-chunk warning retained. |
| 19 | Same fixed source: specification gate PASS, 76 artifacts/54 core models/119 declared routes/97 registered routes. Product acceptance and real-provider evaluation remain NOT_RUN in that gate. |
| 20 | Same fixed source: actual native test FAIL at 30 seconds waiting for the exact-label select locator. Actual page already contained the intended two comboboxes and real r1/r2 options. It had not yet executed body comparison acceptance. |
| probe | Controlled same-DOM Chromium probe: exact label count 0; exact combobox role count 1; role locator selects successfully. This is a locator diagnostic, not app acceptance. |
| 21 | Final `05aa1af2fd000654b0d7b62e5eae32998c81d43f`: one actual native feature test PASS, 7.0 seconds (test 4.6 seconds). Only four select-locator lines changed after b20; all product/test assertions, request behavior, 30-second test timeout and retry=0 remain unchanged. |

The native case uses the existing synthetic Reader r1/r2 learning-package fixture through the actual Import application and database owners, then reads the selected block revisions through actual HTTP. It checks both complete original strings with exact textContent equality, both metadata hashes, visible changed lines, no default pair, selection retention across collapse, desktop/narrow container bounds, local pre scrolling, unchanged learning progress and no content/domain mutation requests. No response mock, fake approval or model call is used. The ordinary Playwright config and fixed ports are unchanged; both preflights proved them free. Runtime data is private and excluded from this evidence manifest. NO_COLOR/FORCE_COLOR warnings are preserved. This single native case is not the complete native suite or human mathematical approval.

Final static/unit/build/spec execution remains at b20. `native-locator-only.diff` proves that final 05aa changes only the native test locator; this report does not pretend those gates were re-executed at 05aa. The 17–21 fixed gates each have 952 declared source inputs, all checked against their actual Git HEAD and unchanged before/after. The runner scope excludes progress/, docs/ui/ and symlinks; it is not the parent's different whole-engineering manifest count. Worktree status after native is clean, so no tracked screenshot restoration was necessary.

## Screenshots and limits

Actual screenshots are under `native-final-output/block-version-compare-actu-c3b4f-t-desktop-and-narrow-widths/`: `block-compare-controls-390.png`, `block-compare-original-390.png`, `block-compare-1440.png`. Implementer inspection confirms readable stacked narrow controls and locally scrolling long source lines. The desktop locator screenshot includes a long unpainted area caused by capture across the parent's scroll viewport; it is retained as an original and does not prove a complete desktop visual review. Actual desktop/narrow no-overflow assertions passed. The initial failed screenshot and error-context.md remain under native-output. No screenshot was redrawn or masked.

The test uses an inline diagnostic attachment with refs/geometry/read-only observations; the default reporter did not persist that inline attachment as a separate file. The retained full command log and unchanged permanent assertions establish the execution result; no unretained JSON is invented as an evidence member.

## Security, remaining scope and handoff

Current permission and stale-response checks have behavior coverage; metadata/body integrity failures fail closed. A bounded source/model verification also checks both checked-in synthetic wire fixtures against the actual Python ContentBlock owner and canonical function. That check is not a new product test or an external call. No user credential was used or stored in source/evidence. Native databases, blobs and generated private runtime material remain outside the evidence/publication scope.

No independent review has yet been accepted. No merge, push, GitHub change, complete backend/full-web/full-native run, real model evaluation, teaching correctness check, restore, impact propagation or higher-revision publication was performed in this slice. Those are NOT_RUN/out of scope, not implied PASS. Next: parent and independent reviewer inspect fixed candidate and all original evidence, resolve concrete findings, then the parent decides integration and bounded combined validation.
