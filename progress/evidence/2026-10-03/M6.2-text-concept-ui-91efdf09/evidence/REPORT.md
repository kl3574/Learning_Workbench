# Original concept retention in the text editing UI

Fixed source `91efdf09fdcae04328d483edcbc21ad0d30a4bd9`, parent `617fb0045383c868e07cdf9a76428b4214cbd4fa`; clean isolated tree `m62-text-concepts-ui-oct03`. The sole PRODUCT_DESIGN v3.0.13 remains SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`. No original checkout, integration tree, remote, canonical spec, backend, DTO/generated file or E2E helper changed.

Two production guard changes admit public text blocks with existing concepts: DraftEditor removes only the nonempty-concepts rejection, displaying the original concept ID array and order in a PRE under the existing fresh author/Policy-ready view. Publication basis validation removes the same categorical rejection while retaining the strict base shape, exact complete metadata SHA, original body SHA, candidate/review binding and complete predicted publication metadata SHA. Target construction still spreads the full original metadata and changes only revision, title and body SHA. Title/body remain the only editable/submitted fields. Non-text/private blocks remain outside the editor.

The visible labels are `保留的原概念 ID` and `原概念 ID 只读记录`. The UI shows original IDs only; it does not infer or claim visible original Concept revisions from bare IDs. The backend's frozen dependency witness owns that exact historical pin guarantee. The old unsupported-concepts UI assertion was removed; its dependency-order and non-text assertions remain. No broader permission or replay rule changed.

## Actual verification

- Corrected positive UI probe: old guard 1 FAIL, fixed 1 PASS, through the real hook, fake IndexedDB and controlled external EditPort. It creates an actual local command, obtains its historical ACK, separately reads the draft, edits title/body and checks exact create/PATCH bodies plus retained read-only ID order.
- Positive publication schema/journal probe: old guard 1 FAIL, fixed 1 PASS; original concepts and dependencies keep their order across durable IndexedDB close/reopen. A literal full-target hash was independently computed using Python canonical JSON/SHA256.
- Final same-byte new probes on old guards: **6 FAIL / 6 PASS**. Positive admission and permission-UI cases cannot get past the old unsupported-concepts guard; the negative metadata tamper checks already pass. Both final test files have exactly the same SHA256 in old/fixed captures.
- Final related suite: **77 PASS across 9 files, 3.61 seconds**. This includes all 12 new probes, original draft-editor hooks/commands/recovery and edit-publication owners. Rejects concept removal/reordering/substitution, dependency reordering, body/metadata damage, altered target hash and injected concept request fields. Learner and active independent/open-book states do not render concept IDs or creation controls.
- Final strict TypeScript/no-unused: **PASS**. Every stage has unchanged inputs; final frozen source was captured before committing and matches all five committed file hashes. The final tracked-plus-untracked capture has 16030 files (includes historical evidence); it is not the root's narrower executable-input count.

All initial failures remain in `STAGES.json`: `ui-green` was an invalid synthetic ACK missing required `state`, not a production acceptance failure; the fixture was corrected and the exact corrected RED/GREEN rerun. Initial strict TypeScript failed because a test mutated an optional concept array without narrowing; the test used its known concrete fixture array, then the final same-byte RED and GREEN were captured. Original logs/receipts were never overwritten or relabeled.

`SOURCE_VARIANTS.json` maps each changed-file variant needed by every before.json to exact archived bytes. Earlier uncommitted variants were reconstructed only if their bytes match the original recorded SHA256; all 11 required variants match. Original before/after lists and command receipts remain private originals.

## Scope and handoff

This is bounded frontend validation using synthetic material. No physical numeric, external Provider/model, full Web, full Python or native gate was run by this UI slice. The backend owner received the fixed commit and owns the separate real-browser Import/Reader/Edit/Review/publication/restart path. That result must be linked separately; it is not counted here. Standards/Spec self-review found the change confined to the existing public-text/title/body contract and current permission gating. Independent review is delegated to the backend/native owner.

Dependencies were installed only into this tree's ignored node_modules with offline npm ci and the frozen existing lock. No environment or key was read/exported. `SAFE_SHARE.json` explicitly lists the prepared private candidate files; only exact <LOCAL_HOME> and <RUNNER_HOME> prefixes are replaced by <LOCAL_HOME> and <RUNNER_HOME>. Original path scanner findings remain raw FAIL; candidate scanning is a separate result, not remote publication.
