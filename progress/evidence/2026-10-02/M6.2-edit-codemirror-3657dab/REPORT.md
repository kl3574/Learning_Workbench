# CodeMirror and edit Review/publication integration

Final commit `3657dab6554fd8587a85aa0fde6c9ecf13045d27`, clean isolated worktree `m62-codemirror-publication-combined-oct02`, branch `feat/m62-codemirror-publication-combined-oct02`, base `8fb64dc1f7d91628692123d70e232f807922110f`.

Scope: reviewed Edit UI + CodeMirror + minimal brace-expansion patch. No main or earlier fixed worktree edits; no providers, secrets, GitHub or remote publication operations. Explicitly kept the frozen v3.0.9 behavior; the newly approved v3.0.10 actor-session contract is not implemented or claimed here. No specification, progress, generated contracts or backend edits in this combination.

## Commits and merge resolution

1. `49faad072acd23bf9bb94d72922f1755c7ac9bc0`: reviewed Edit UI, equivalent to eae3ec2.
2. `03dac22ba16ea57df833659234ca02a11f2b9a6d`: CodeMirror, equivalent to d82a2c4 with the DraftEditor conflict resolved under resolving-merge-conflicts skill. Retained both sides: Review/publication memory protection and candidate invalidation, plus raw CM source. Shared editorDisabled includes reviewState.dirty and !reviewState.safe and is passed to both fieldset and CM. ConflictResolution keeps its original command/server identity key and disabled propagation.
3. `6d2dfb578d11b5a434c73cf6c6bda23b9dfa1736`: equivalent to security patch 986f7cf. Independent JSON readback proves exactly one package entry changed, brace-expansion 5.0.9 to 5.0.12, and only version/resolved/integrity changed. Actual separate node_modules installed via npm ci reads 5.0.12.
4. `3dbbe73be5197546405cf4238dfc3d5ab2d24de5`: real CM/Review DOM test and native combined probes.
5. `3657dab6554fd8587a85aa0fde6c9ecf13045d27`: narrow the native probe to the actual readonly DOM and recovery fills; remove browser-global Undo from another focus target. Product implementation unchanged.

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Focused editor/Review/edit publication | PASS 79 tests / 11 files | stage04-focused; unit and implementation bytes unchanged through final |
| Final full Web | PASS 586 tests / 97 files | stage19-final-fullweb |
| Final strict TypeScript/lint | PASS | stage20-final-lint |
| Final production build | PASS 794 modules | stage21-final-build; chunk-size warning retained |
| Final four native cases | PASS editor, Import publication, draft Review, edit publication | stage18-final-native, native-result.json, native-artifacts |
| npm audit | PASS total 0 | stage07-audit; final dependency bytes unchanged |
| Bounded scanner | PASS all 26 changed combined files | stage22-final-scan |

Every receipt includes exact command, UTC time, actual exit code and raw-log hash. All five final gates use the same 13872 source inputs with equal before/after SHA256 manifests. COMMIT_BINDING.json verifies all 26 changed files against final Git commit bytes. Full Python was NOT_RUN in this isolated UI combination; root owns the backend gate.

## Probe boundaries

The actual DraftEditor/ReviewPanel DOM test creates two isolated real CM transactions, returns to exact saved text, and confirms undoDepth=2. An unsaved Review form and then an in-flight Review refresh each set CM readOnly/contenteditable=false. Direct real view.dispatch input and undo cannot change source, undo depth or exact durable IndexedDB records. After recovery, the same undo history works and subsequent Unicode/TeX/newline text is saved. No server PATCH is sent. Only test-scoped geometry and session/HTTP fixtures are used; this is the direct CM input/undo mechanism verification.

Native edit publication checks actual contenteditable=false, aria-readonly=true and not.toBeEditable during dirty Review and a held successful real HTTP Review GET; then verifies real contenteditable.fill and exact text after recovery. It records the actual activeElement without routing keys through another element. It does not pretend a scroller keyboard event covers the CM input handler. Each source update invalidates the Review candidate, even after returning to equal text, so the test explicitly revalidates the exact saved draft before resuming Review.

The four native cases retain actual two-tab 412 conflicts, exact source/journal/server text and SHA, Policy hiding, real IDB abort and memory recovery, explicit synthetic human decisions, original publication key/body/ACK replay, pinned old Lesson references, browser/API restart, and zero page errors. Mobile 390px CM and edit-publication screenshots were inspected; existing 390/1440 layout assertions pass. Synthetic decisions establish software behavior only, never genuine mathematical/source/pedagogy approval.

## Preserved failed, interrupted and superseded attempts

- stage01: focused 78 PASS/1 FAIL; the new test initially created undo history after entering Review. First source update correctly invalidated the candidate, triggering reload; second immediate transaction was gated. History is now created before Review.
- stage02: lint FAIL in the new test; DraftStore.load returns a map, fixed using Object.values.
- stage03: INTERRUPTED exit130 after three passes; stopped the fourth probe when invalid candidate/form sequencing was known. Never counted as four-test PASS.
- stage05: three native PASS/one FAIL. Disabled content DOM cannot be focused; keys hit the still-focused note. Raw screenshot retained.
- stages10/11: single native FAIL. Remounting a textarea with nonempty initial child text causes installed Playwright exact getByLabel matching to include that child text. Actual DOM evidence is preserved in stage11/artifacts/probe-form-dom.json. Installed getElementLabels/elementText source was checked. The new probe uses the textbox role with exact accessible name, without altering product DOM.
- stage12: single native PASS; stage13: four native assertions PASS. Subsequent strict evidence readback exposed the scroller browser-Undo probe undoing the previous Review note, changing dirty state (source stayed unchanged). Therefore stage13 is superseded and not used to claim disabled-state coverage. Final native removes that unrelated browser Undo and verifies readonly attributes and recovered fills; direct CM input/nonempty Undo stays covered by the DOM test. The first attempted report generation failed its readback assertion and was not published as acceptance.
- stages14-17: earlier full Web/lint/build/scan PASS; final stages18-22 repeat all combined gates after the precise probe correction.

## Remaining scope

v3.0.9 page/access continuity limits remain; v3.0.10 actor-session replay is separate work. No claim of full M6.2 completion, complete browser-suite coverage, actual teaching approval or future vulnerability immunity. Observed npm audit total is 0; existing build >500kB chunk warning remains. Raw runtime evidence stays private and was not committed.
