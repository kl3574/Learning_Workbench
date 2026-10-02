# Content form submit race repair

Final commit: `50d960fec1a0dc5644f75f8b16e3c7252d1a4791`.
Parent: `3be34e9fc320a1543b8d694426c680b7b06bbbc9`; original feature: `e0e24592879ee60b437a6d7d5ff25632a58efae5`.
Tree: `$HOME/.cache/learning-workbench-acceptance/m62-content-impact-form-submit-race-oct02`, branch `fix/m62-content-impact-form-submit-race-oct02`, CLEAN.

This report supplements the prior Content impact review/form-recovery report at `m62-content-impacts-ui-independent-evidence-oct02/REPORT.md`. The original e0 feature, 3be repair, their trees and all earlier evidence remain frozen. 3be alone contains the independently confirmed submit race below and must not be treated as the final repair. Integrate 3be followed by 50d960fe (or their reviewed equivalent), not 3be alone.

The fixed source retains the task's v3.0.11 specification SHA `35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29`. Root's separately adopted v3.0.12 adds Restore numeric work; none of that work is mixed into this bounded repair. No backend, dependency, generated, progress, specification or main-tree file changed.

## Confirmed P1 and repair

Root identified and the independent reviewer reproduced a race in 3be's real ContentImpactsPanel: submit captures the original reason and awaits a journal read while inputs are still editable. The user types a newer reason during that wait. After the original command becomes durable, the old `if (submittedForm) releaseForm(...)` unconditionally deleted the newer unsent form, overriding the existing exact-match check. This loses user input without explicit discard, contrary to the same §4.3/§20.13 protection requirements as the original finding.

The production change only removes that unconditional deletion and its boolean argument. `consumeForm` now exclusively decides whether the current form exactly matches the original frozen basis, decision, reason and artifact IDs. The original click still sends its original immutable command once; a newer mismatching form remains protected in page memory and can be explicitly restored. No new key, auto-send, automatic basis replacement, session expansion or persistence of secrets was added.

The exact independent probe was copied unchanged into the repository as `apps/web/src/features/contentImpacts/independentFormReview.test.tsx`:
SHA-256 `ccfe9db864b8e223e77a62f781ba3c88dd3aa451312ba1da040f395541d74f9f`.
It uses the real Panel, delays only the submit-time journal load, changes the actual enabled textarea, resolves the read, verifies one original request/ACK and its original durable body, then verifies the newer Unicode/newline reason remains in owned form memory. The same test command is red at 3be and green at 50d960fe. Raw independent red evidence is copied verbatim under `external-review-red/`; its log SHA remains `1b106a6922862eb31501a57a12bfd796a9f44844814c6deb866f6c191a94b1a8`.

An existing direct-hook 412 test had submitted reason arguments without updating the controlled form and expected that mismatching form to be erased. After removing the unsafe erasure it failed, correctly preventing a second adoption while unsent input remained. The test now performs the same two `changeForm` actions as the UI before its two explicit submissions. All existing old-head, 412, preserved-command, new-key and current-read assertions remain. No production behavior was added to accommodate that shortcut.

## Final gates and binding

All six final gates used identical 14,032 input files, with unchanged before/after hashes. SOURCE_BINDING.json validates every tracked byte against the final Git objects, the three changed paths, the clean tree and the unchanged 3be tree.

| Gate | Result | Evidence directory |
| --- | --- | --- |
| Original independent test, unchanged command/test bytes | 1 PASS | `original-probe-fixed-final` |
| Content impacts and all Authoring | 116 PASS / 17 files | `focused-final` |
| Full Web suite | 660 PASS / 103 files | `full-web-final` |
| Strict unused/type checks | PASS | `lint-final` |
| TypeScript + production build | PASS / 809 modules; existing chunk-size advisory | `build-final` |
| Real native Chromium + SQLite/HTTP/IndexedDB | 2 PASS, 1.1 minutes | `native-final` |

Each directory contains exact command, log, exit code and full input hashes. Native config has no global webServer and uses only RestartRuntime's owned random loopback ports/private SQLite/browser data. Dependencies belong to this new tree; only the unchanged pinned toolchain is shared read-only. Native execution uses the short private TMPDIR to avoid the already documented host quota/socket limits.

The two native cases are unchanged from 3be: real publication → actual discovery → explicit decisions → competing 412 → original lost-ACK replay → true IDB ACK-write abort → role cycle/save-only recovery → exact-to-ID-only correction → three fixed-member pages/two filters/restart/old parent pin/assessment Policy; and unsubmitted Unicode/newline form → two real role cycles → fresh original-session restoration → changed current target retaining old basis/blocked save → close cancellation/explicit discard → zero Content POST/journal/decisions. They remain green after the exact-consumption change. NATIVE_READBACK.json independently validates request/receipt digests, identical original replay, retained original exact receipt, later ID-only classification, old parent reference and the second scenario's zero writes.

The new submit-race interleaving is specifically proved by the real-Panel DOM test with a deferred journal read. The native cases verify the surrounding actual browser/HTTP/IndexedDB flow; this report does not claim that the new interleaving itself was forced in native Chromium.

## Preserved intermediate outcomes and limits

`original-probe-green` first established that the unchanged independent test passed after the three-line production correction. `focused-before-test-adaptation` records 115 PASS / 1 FAIL from the mismatching direct-hook fixture described above. All raw outcomes remain; final focused is 116 PASS. No failed assertion was removed or weakened.

Temporary forms remain page memory, protected by before-unload and explicit discard; forced browser termination is outside that durability guarantee. Original commands remain separately durable and same-page/access/session-restricted. No provider, credential inspection, remote operation or external publication occurred. Synthetic software decisions confer no academic, numerical, source-quality or teaching approval. Full backend/M6.2 acceptance, the separate ReviewPanel issue and approved Restore numeric implementation are outside this repair. Root/another agent performs the final independent review of these implementation commits.
