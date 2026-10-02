# M6.2 Note manual re-anchor and historical Retrieval acceptance

Fixed implementation: `44e66c8030970831604e760dd8a6a6880a43b7ea`, branch `feat/m62-note-reanchor-native-oct02`, parent `98eaf27de7b241de11b714a0e47cc54f120604b2`.

Worktree: `$HOME/.cache/learning-workbench-acceptance/m62-note-reanchor-native-oct02`, CLEAN. This report and all raw evidence live in the separate `m62-note-reanchor-native-evidence-oct02` directory. Later main-tree integration or Reader fixes are outside this evidence binding.

Normative input: PRODUCT_DESIGN.md v3.0.12, SHA256 `1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7`; no spec/progress/generated/backend/route edits. §10.4 line 526 requires exact ref/quote/context and original Unicode codepoints. §20.11 lines 1218–1220 require Note stale with no automatic migration, manual re-anchoring, explicit stale/rebuild with old scope, and unchanged Lesson/Course pins. General local-draft protection is line 246 and §9.3 line 461.

## Outcome and scope

PASS: a real browser imported original synthetic public material, created an original Note and index through UI, edited its public block through the actual CodeMirror UI, saved the draft, requested a new Review, made explicit synthetic human decisions, and published block r2. API reads proved the old Note became stale with its original r1 anchor and Markdown unchanged. The new Note UI separately read and verified the actual current block ref/full metadata/body, accepted a real browser selection only after another fresh permission read, adopted that exact selection into the local Note draft, and used the existing explicit Note CAS save to append Note r3.

The original block-r1 Retrieval scope explicitly reported stale. Only another explicit UI rebuild produced a completed actual Job. Querying that same scope then returned the original body and exact r1 ref, with current_ref=r2 and HISTORICAL_REVISION; a unique token present only in r2 produced no_match. Current Lesson and Course refs remained the original complete refs, and Lesson r1 retained the original block pin. Rebuild is not a scope upgrade.

The fixture is original synthetic pure text, not a mathematical or pedagogical approval claim. It has no pre-existing grades or private solutions: empty learning evidence is compared before/after, but this case does not claim preservation of a populated assessment corpus. No Provider, SQL publication injection, or direct REST replacement of the main user actions was used. API is used for readback only. This slice does not add routes, current-pointer rewriting, automatic re-anchoring, cross-page command replay, or changes to any numeric owner.

## Changes (nine files)

- `apps/web/src/features/notes/NoteReanchor.tsx`: new read-only source preparation. Lines 14–49 isolate workspace/Note/original-ref/access/lifecycle, validate fresh strict session, deny independent/unknown Policy, and clear temporary source on focus/visibility/access/periodic permission loss. Lines 50–72 explicitly read same-ID current, reuse the exact Content metadata/body verifier, repeat permission after read and before local adoption. Lines 74–89 distinguish old anchor from frozen new source/selection and explicit local adoption. Later current changes never replace the frozen selected ref.
- `apps/web/src/features/notes/NotesPanel.tsx`: lines 140–145 adopt into the latest `editorRef`, retaining concurrent Markdown; all existing IDB/conflict/save guards remain. Line 150 mounts the source selector only for a saved stale Note. Server persistence remains the existing explicit CAS save, not the selection component.
- `apps/web/src/features/reader/selection.ts`: lines 61–72 map browser LF-normalized textarea UTF-16 positions into the untouched original source, then reuse exact selection validation/codepoint/context creation. ReaderDocument itself is unchanged in this commit.
- `apps/web/src/features/notes/notes.css`: bounded layout, wrapping exact hashes/source, no horizontal overflow at 390/1440.
- `apps/web/src/features/notes/NoteReanchor.test.tsx`: 19 component cases against actual UI and the HTTP boundary (parameterized cases contain further lifecycle subcases).
- `apps/web/src/features/notes/NotesPanelReanchor.test.tsx`: two actual NotesPanel/useNoteDrafts/DraftStore integration cases with real fake-indexeddb transactions. Deferred fresh permission retains concurrently typed Markdown; actual IDB put quota failure protects the complete new-anchor candidate and preserves the old durable candidate. Remount recovers both and requires explicit local conflict selection; zero server writes.
- `apps/web/src/features/reader/selection.test.ts`: five permanent tests for real textarea LF/CRLF/lone-CR normalization, astral/combining text, cross-line original quote, 40-codepoint exact prefix/suffix, surrogate splitting, empty/out-of-range selections.
- `tests/e2e/contentImpactsData.ts`: optional pre-edit UI callback and optional revised-body argument, preserving original defaults for existing callers.
- `tests/e2e/note-reanchor-publication.spec.ts`: actual native end-to-end chain and complete readback described above.

`changed-source.json`, `change.patch`, and `source.tar` preserve all nine changed files with Git blob IDs and SHA256. `fixed-readback.json` verifies every final gate's full 1242-input inventory against committed worktree bytes.

## Fixed gates

All four final stages run against CLEAN `44e66c80`. Each has `before.json`, `after.json`, command/exit/time/HEAD/log SHA in `receipt.json`, and raw `run.log`. All 1242 captured inputs are unchanged during every stage.

| Stage | Actual command (from repository root) | Result |
|---|---|---|
| fixed-focused | `bash scripts/node.sh npm --prefix apps/web test -- src/features/notes src/features/reader src/features/retrieval` | PASS, 134 tests / 14 files, 4.12s |
| fixed-lint | `bash scripts/node.sh npm --prefix apps/web run lint` | PASS, strict TypeScript/no-unused checks |
| fixed-build | `bash scripts/node.sh npm --prefix apps/web run build` | PASS, TypeScript + Vite, 835 transformed modules |
| fixed-native | `bash scripts/node.sh node apps/web/node_modules/@playwright/test/cli.js test --config $HOME/.cache/learning-workbench-acceptance/m62-note-reanchor-native-evidence-oct02/playwright.config.ts note-reanchor-publication.spec.ts --workers=1` | PASS, 1 actual native test, 16.5s case / 17.2s suite |

Native environment was explicit short private TMPDIR `$HOME/.cache/nran` and `LEARNING_E2E_OUTPUT_DIR=<evidence>/fixed-native-output`. Private config has `webServer:undefined`; RestartRuntime used actual random local ports and its own SQLite/application data/browser profile. No default 5173/8765 services were used. No full Python or full native suite was rerun for this bounded UI slice.

## Native originals and visual inspection

Under `fixed-native-output/note-reanchor-publication--72af0-rical-bytes-and-parent-pins/`:

- `note-reanchor-and-historical-retrieval.json`: actual publication refs/Review chain, original/stale/updated Notes, original and repeated index commands/ACKs, initial/stale/historical query DTOs, parent Lesson and current Course/Lesson refs, evidence snapshots, bounded write trace, and page errors (empty).
- `note-new-source-selection-1440.png`, `note-new-source-selection-390.png`: verified exact r2/body SHA and actual selected source before local adoption. Both inspected; wrapped hashes/source and vertically scrolling modal, no horizontal overflow.
- `note-manual-reanchor-1440.png`, `note-manual-reanchor-390.png`: explicit saved Note r3, exact r2 anchor and retained Markdown. Mobile image inspected.
- `old-scope-rebuilt-original-body.png`: old r1 scope and completed rebuild/index status, inspected; precise historical hit/body is recorded in the JSON and asserted in the actual UI/HTTP test, not fully visible within this screenshot's viewport.

The automatic raw artifact names are unchanged. `MANIFEST.json` lists SHA256 and length for every evidence file.

## Preserved failures and test corrections

1. `native-red`: FAIL on unchanged original product `98eaf27d`, 1239 captured inputs unchanged. Real import/Note/index/Edit/Review/publish/stale checks passed; click timed out at the missing manual current-source re-anchor button. Original log, screenshot, and error context remain. `red-readback.json` verifies every non-test input equals the original Git baseline. Original test/helper bytes have been reconstructed from the retained development delta and matched exactly against the initial captured hashes; copies are `verified-original-test.ts` and `verified-original-contentImpactsData.ts`, SHA-bound to the original run.
2. `native-green-01`: FAIL after the complete new re-anchor and historical rebuild worked. The test wrongly expected CJK query `复核流程` to produce no match, despite shared lexical tokens with original text. Changed only the fixture's r2-only token and the query to `reanchornewevidenceonly`, and captured the historical result before the negative query. Retrieval implementation was not changed. This stage's original exact test/helper, log, screenshot and error context remain.
3. `native-green-02`: PASS, 20.5s case / 20.8s suite, 1240 inputs unchanged; precursor to final screenshots/candidate-current explanation/unit tests. It is not presented as final source evidence.
4. `component-01.log`: 17 PASS / 1 FAIL because fake timers were enabled after the real permission poll was scheduled. Corrected only the test clock arrangement (wait for real bounded poll); `component-02.log`: 18 PASS.
5. `panel-selection-01.log`: 38 PASS / 2 FAIL from unsupported jest-dom matcher names in the new test harness. Corrected to actual DOM property assertions.
6. `panel-selection-02.log`: 39 PASS / 1 FAIL because the new test expected a quota-recovered candidate to overwrite the old durable primary automatically. Corrected to assert both candidates survive and explicitly choose the recovered candidate through the real conflict UI; no product behavior changed. `panel-selection-03.log`: 59 PASS.
7. Precommit `focused-final` and `lint-final`: PASS, 134 tests and strict check; retained separately, superseded by fixed-commit stages above.

## Remaining boundaries

- Other Notes behaviors and known pre-existing Reader source selection handling are not claimed repaired here. Parent is handling ReaderDocument reuse of this shared selection helper independently.
- Read-only source preparation is intentionally ephemeral; after explicit local adoption, the existing Note draft owns persistence and unsaved protection. The two stages are visibly separate; read/selection/adoption issue no Note write.
- Material is exact as read; if Content current changes later, the candidate retains the actual selected ref. No hidden current substitution or parent-pin update occurs.
- Policy is checked before/after fetching and before adoption, with access-generation/focus/visibility clearing and bounded polling. This is ordinary local session enforcement, not a claim of instantaneous cross-process push notification.
- No mathematical correctness, new score, private-solution modification, or full M6.2 completion is inferred from these UI tests.
