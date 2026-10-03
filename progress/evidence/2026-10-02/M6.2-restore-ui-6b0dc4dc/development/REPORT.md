# Historical public ContentBlock Restore UI — fixed implementation evidence

- Implementation commit: `da867f4c253123934b4cabb1c8b7e53e7259e942`.
- Isolated clean worktree: `$HOME/.cache/learning-workbench-acceptance/m62-restore-ui-oct02`.
- Base UI combination: `3657dab6554fd8587a85aa0fde6c9ecf13045d27`; spec-only commits supplied by root were cherry-picked as b20fc04, 439a7ad, 38e3ded, 2c5c041. Root should pick only da867f4c for implementation. No main/integration tree edits, remote action, provider call or secret use.
- Sole normative document: PRODUCT_DESIGN.md v3.0.11, SHA256 `35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29`; stable v3.0.9 content and all subsequent supplied amendments were read. Restore follows §20.11; §20.10.1 extends only Edit create/PATCH, so Restore does not adopt cross-page actor replay.
- No backend, migrations, generated contracts, DraftEditor, Learning, progress, package/lock or spec implementation changes. The new Restore UI uses existing strict Restore create/read plus existing Review/publication endpoints. Reader remains a reader; original/public source and proposed restore fields are displayed read-only.

## Delivered behavior and boundaries

A user explicitly reads two real historical block revisions, selects one exact returned ref, and separately reads active current plus complete original/current metadata/body. Create requires a reason and explicit confirmation and writes a dedicated versioned Restore journal before POST. Server create ACK does not stand in for actual candidate GET. Snapshot checks reject owner aliases, mismatched candidate/source/base, raw-body or metadata corruption, and inconsistent published refs. Proposed block revision is current +1; every other old metadata field and raw Unicode/LaTeX/newline byte is checked against the old ref.

The actual saved `authoring_restore` candidate enters the existing real Review UI. Publication preparation re-reads exact Restore GET, selected Review, old source and active current, requires the matching fresh human decision, and displays that actual basis. Every warning instance plus a separate publication confirmation is required. Publication has its own strict owner basis/journal; no Import/Edit owner alias is used. The request retains the original four publication fields and key. Backend remains authoritative for full source/provenance/dependency integrity, current+1 CAS and transaction effects. A current race returns 412 without silently rebasing a retained candidate; user must explicitly create/review a new candidate.

Unknown ACKs retain the complete original command; only explicit same-page/same-access replay is enabled. IndexedDB failure prevents sending a first undurable command; a received ACK that cannot be saved is isolated in memory. Original-session memory recovery only saves facts, performs no HTTP write, and never rewrites original page/access identity. Permission/Policy loss hides all Restore candidate/journal material, fences late callbacks and aborts in-flight local writes; memory remains close-unsafe through unmount and author/learner/author role cycles. A different current session cannot save another session's held payload. No credentials or their hashes are persisted. Retained command identity is also checked against the owning workspace/block.

ReaderDocument reports Restore state under a separate `restore:<block-id>` key to existing Shell close/navigation protection. BlockVersionCompare scopes selections by workspace/block and prevents replacing a dirty or close-unsafe Restore selection. ReviewPanel has a closed Restore branch; existing Edit/Import branches are retained. These are the only three shared product files changed.

## Fixed-source verification

All stages below bound identical 13,891 input files before and after. `COMMIT_BINDING.json` binds all 22 changed files to the git commit and those gate bytes; worktree is clean.

| Stage | Exact command after capture wrapper | Result |
|---|---|---|
| stage06-focused | `bash scripts/node.sh apps/web/node_modules/.bin/vitest run --root apps/web src/features/contentRestore src/features/reader/versionCompare src/features/draftReview` | PASS 100 tests / 13 files |
| stage07-full-web | `bash scripts/node.sh apps/web/node_modules/.bin/vitest run --root apps/web` | PASS 629 tests / 102 files |
| stage11-lint | `bash scripts/node.sh npm --prefix apps/web run lint` | PASS tsc with noUnusedLocals/noUnusedParameters |
| stage12-build | `bash scripts/node.sh npm --prefix apps/web run build` | PASS tsc + 806 modules; existing >500KB chunk warning retained |
| stage10-native-final | `bash scripts/node.sh apps/web/node_modules/.bin/playwright test --config $HOME/.cache/learning-workbench-acceptance/m62-restore-ui-development-oct02/native-final.config.mjs` | PASS 2 actual Chromium tests, 27.8s |
| stage13-publication-scan | `python scripts/check_publication.py` | PASS 22 staged files; bounded scanner, not a guarantee of all possible private text detection |

`git diff --cached --check` also passed before commit. Own installed dependencies and venv were used, without sharing mutable node_modules with a running gate. No full Python suite was rerun: backend is unchanged; root owns integrated backend gates. Shared Review/Reader regression was covered by full Web; this slice's native tests cover Restore, not a new all-product native acceptance claim.

## Test-to-source mapping

- `restoreSchema.test.ts`: all 11 ContentBlock kind snapshots, strict closed create/ACK DTOs, Unicode code-point reason limit, alternate owner denial, original body normalization/corruption, changed kind/dependencies, wrong published-state/ref rejection. `restoreSchema.ts` and `restoreClient.ts` enforce live response shape and visible cross-bindings.
- `restorePublicationCommands.test.ts`: dedicated Restore owner, immutable body/key/basis and ACK collision protection, full source fields/body, independent target hash, fresh Review and per-instance warning acknowledgement; actual fake-indexeddb transactions through DraftStore.
- `useRestoreDrafts.test.tsx`: real journal-before-HTTP assertions; exact lost-ACK retry; no automatic candidate read; first IDB failure zero POST; ACK memory recovery and wrong-session isolation; old-page read-only preservation; body/hash/identity/nonhistorical-source denial; Policy hiding; 412 retains source/base/body; known create ACK cannot be relabeled; foreign workspace/block cannot execute.
- `useRestorePublication.test.tsx`: immutable lost-ACK replay, independently read current vs historical ACK, stale read/candidate/access callback fencing, undurable zero-HTTP write, actual old-page restriction, 403 hiding, wrong ACK four cases, current race, received ACK isolated across unmount and original-session-only recovery; foreign block cannot prepare/replay/read current.
- `RestorePanel.test.tsx`: actual rendered controls, first save failure preserves exact Unicode/multiline form and full held command; Policy hides original body/hash; unmount retains close guard; explicit original-session save makes no HTTP request. Existing versionCompare and Review tests cover their shared branches.
- `tests/e2e/content-restore.spec.ts:86`: actual imported synthetic r1/r2 proof with a pinned old dependency; real version-comparison selection; dedicated create lost ACK and exact replay; actual candidate GET; real Review job and explicit synthetic human math/source decisions; fresh preparation and warning confirmations; actual publish lost ACK; actual IndexedDB transaction abort after replay ACK; learner role hides payload, beforeunload remains guarded, author role saves only retained ACK and old-access replay stays disabled; exact r3 metadata/body/hash readback; Lesson r2 bytes/pins unchanged; browser plus API restart keeps the same database inode, exact journal bytes and published GET. Real Chromium screenshots at widths 1440 and 390, with no horizontal overflow; 390 screenshot was visually inspected.
- `tests/e2e/content-restore.spec.ts:157`: after primary UI prepares base r2, a second real Restore candidate goes through real HTTP Review/human/publication and advances current to r3; primary UI publication returns 412, original journal remains pinned to r2, candidate remains draft, actual current equals the winner. Competitor setup uses actual local endpoints, not SQL injection or fake server mutation.

Native JSON readback (`native-final-artifacts/**/restore-flow.json`, `restore-race.json`) independently verified exact create/publication retry body/key equality, owner `authoring_restore`, source r1/base r2/proposed proof r3, immutable published ref distinct from candidate SHA, retained ACK, two API generations, zero captured page errors, independent pedagogy NOT_RUN and exact `RESTORE_BASE_CHANGED` 412. HTTP, journal and parent readback assertions themselves remain in the committed native test. Synthetic human judgments are protocol fixtures, not real content quality approval.

## Earlier failures and corrections retained

- `initial-checks.txt` accurately summarizes pre-capture runs (17 then 27 Restore tests PASS) and TS2345 from passing an optional-argument memory-discard helper directly to forEach. Fixed test cleanup to a one-argument lambda. These are summaries, not recreated raw logs.
- stages01/02: earlier source focused 84 PASS/lint PASS; stage03 native 2 PASS on earlier source, retained separately. Later source changes added explicit block/workspace method guards and more schema/form tests, so final acceptance uses stages06/07/10/11/12/13.
- stage04-focused: 94 PASS, 1 FAIL. New DOM test filled/clicked while preparation was still busy; fireEvent can target disabled controls. Corrected test to wait for actual enabled textarea, matching real browser actionability. No product behavior relaxed.
- stage05-focused: 94 PASS, 1 FAIL. Test changed Policy as soon as the memory-retention alert appeared, before the deliberately rejected first store.save had run; the unconsumed once-only fault then rejected memory recovery. Corrected test to wait for the actual persistence error before Policy transition. The retained-memory signal is intentionally earlier than durable success/failure. Also corrected final test readback to parse DraftRecord.text. Final test checks the original preservation assertion without weakening it.
- stages08/09: launcher configuration errors, exit127: `scripts/npm.sh` does not exist. No lint/build executed in these stages. Reran exact intended operations with the repository's `scripts/node.sh npm` in stages11/12; both PASS. All original logs and receipts retained.

## Material limitations / NOT_RUN

- Existing Restore snapshot exposes strict `candidate_sha256` and `source_material_sha256` but not their complete server-only canonical provenance/dependency descriptors. Frontend verifies strict hash shape, all visible fields/old metadata/body/target hashes, cross-read candidate identity and real server GET; it does not claim to reconstruct those server-only hashes. This canonical-contract gap was reported to root; no interface was invented or expanded.
- Native full publication is demonstrated for proof; all 11 kinds are DTO/source-binding tests, not 11 native publication demonstrations. worked_example retains the backend's fresh numeric NOT_RUN publication blocker when no current-candidate numeric owner evidence exists. This UI does not transfer old numeric/quality approval or claim worked_example publication delivery.
- Cross-page unknown Restore command replay remains deliberately disabled by the existing owner contract. v3.0.10 grants actor-session replay only to Edit create/PATCH. Integrated actor-session backend/generated-contract gates are root's separate slice.
- No provider, GitHub, mathematical/teaching/source-rights approval, old Question/private solution/grade rewrite, parent-pin rewrite, full M6.2 acceptance or production release is claimed.

Evidence hashes: `MANIFEST.json`; final verification receipt: `FINAL_READBACK_VERIFIED.json`.
