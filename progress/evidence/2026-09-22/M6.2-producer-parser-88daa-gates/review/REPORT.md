# Independent native artifact readback

Result: no blocking mismatch or actual credential/personal-data exposure observed in the reviewed native artifacts. This read-only review ran no tests, application code, Provider calls, database queries, or network calls and changed no source. Only this independent cache was created.

The gate corresponds to commit `88daa0a23dab0e69f7009b9af670671c45f90924`. Its unchanged actual log is **12 passed (1.3m)** with zero retries. The original receipt/runner prose estimated ten; `native-count-note.json` explicitly corrects that prose without changing the raw result. Independent readback confirms the log length/SHA, 949 identical before/after source entries, and all manifest entries marked Git-matching. The nine test/fixture sources inspected for scope match the exact gate input hashes. Details: `verification.json`, `evidence-pins.json`, `source-pins.json`.

## Numeric and approval boundaries

| Actual root | Observed numeric result | Review/publication state |
| --- | --- | --- |
| Single block | `BLOCKED`, `environment_unavailable`, exit 1; no assertions/output hash | draft; mathematics, sources and independent pedagogy `NOT_RUN` |
| Lesson group | Same actual BLOCKED outcome for exact example member | draft; all three review dimensions `NOT_RUN` |
| Assessment group | Same actual BLOCKED outcome for exact question/private NumericPlan | draft; all three review dimensions `NOT_RUN` |
| Practice group | No numeric execution in this test; `numeric_check_ids=[]` | draft; all three review dimensions `NOT_RUN` |

The three numeric-result screenshots show BLOCKED explicitly and retain NOT_RUN review text. `approve_once` records the controlled UI decision to execute one numeric check; it is not a mathematical, source, pedagogical, or publication approval. Structural PASS checks and fixture arithmetic text do not establish arithmetic PASS. The practice screenshots show its full synthetic plan/private answer but no numeric result. The single receipt's `declined_preview`/`approved_preview` fields preserve the initial pending preview responses, not the final decision state; the actual single decline/no-Job behavior is asserted at `authoring.spec.ts:142-146`, and the final numeric result is separately retained. Group receipts additionally retain decision ACK/readback.

## Real recovery, cancellation and permission scope

The lesson, practice and assessment receipts each retain the same database device/inode and an actual changed API process pair: lesson `273576→273844`, practice `274005→274257`, assessment `274472→274779`. Each first process received and validated one controlled loopback request; each restarted process received/validated zero. Full Job, Draft, targets, and available private solution match before/after restart. New runtime control reports `reused_exact`; no Provider reconfiguration/reseeding is performed by the restart read. The receipts and `authoring-groups.spec.ts:191-232` support this specific three-group recovery claim, not a single-authoring restart claim.

Each group cancels a distinct second, unconsented Job after a real author-to-learner role change. Both retry attempts retain the same original key/body, the actual original cancel ACK equals final readback, revision is 2, and the already completed first Job/one consumed Provider request remain intact. The dropped ACK seam uses `route.fetch()` before browser abort, then continues the second real request; it fabricates no response (`authoring-groups.spec.ts:136-187`). Tests assert protected detail/candidate/plan/private-answer/numeric regions are removed without reload and real academic endpoints return 403 (`152-159`). These are passing source assertions and JSON readbacks, not post-demotion screenshots: the private screenshots intentionally show the earlier explicit author read.

The separate no-proof single case retains zero dispatch and a cancelled safe Job; the completed single case retains exactly one prepare/dispatch and safe authoring/numeric kinds after role change. Submission and grading-recovery receipts remain scoped to real HTTP/worker acknowledgement and explicit synthetic fault recovery; their human mathematical approval is NOT_RUN.

## Visual and privacy inspection

All **15 PNGs** were opened individually, with their exact filenames recorded in `viewed-images.json`. All **13 geometry records** satisfy their measured viewport/dialog/inner horizontal bounds: 390-wide narrow views and 1440-wide broad views; document imports have screenshots but no separate geometry JSON. Numeric, synthetic candidate/private-answer and import warning text are visibly legible in the captured regions. The screenshots cover portions of vertically scrolling dialogs; this is not an assertion that each image displays the entire dialog.

No actual API key, session/CSRF token, Authorization header, private key, email, personal identity, or personal learner material was observed in these JSON/PNG artifacts. The shown private solutions are original synthetic answers explicitly labeled unreviewed. Checked test setup uses literal synthetic Provider secret constants; bootstrap capability remains in runtime memory and is removed from the URL before captures. JSON key/pattern screening found no credential/contact matches, supplemented by source review and all-image visual inspection. This conclusion is bounded to the reviewed artifacts, not every file under the execution cache. `privacy-readback.json` records that boundary.

`artifact-pins.json` records every test-results file's path, byte length and SHA256, with PNG dimensions. Exact copied bytes are under `artifacts/`; semantic/geometry readbacks are preserved separately. The original evidence and source are unchanged. This controlled loopback native gate is not a vendor-service proof, arithmetic PASS, full native suite, human review, or explanation of either earlier CI failure. Both earlier CI causes remain unresolved here; root owns the full Python and unified gates.
