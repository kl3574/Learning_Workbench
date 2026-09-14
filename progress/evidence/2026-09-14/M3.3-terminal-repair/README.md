# M3.3 passive grading refresh and terminal candidate recovery

This is a bounded repair of the existing assessment native scenario. It is not the final full-suite or CI acceptance. No product source was changed during the original observation or controlled RED runs. The sole product specification remains PRODUCT_DESIGN.md.

## Two distinct findings

The original final native suite and CI failures are recorded separately by the parent. An unchanged-assertion observer replay passed local recovery then failed the old final assertion: submitted receipt revision 3 versus actual completed-worker revision 5. Grading is a legitimate later transition. The permanent test now first reads the actual stable needs_review snapshot; restoring local drafts must leave that snapshot and submitted responses unchanged. It does not relax the response comparison or permit writes after submission.

The second finding was a lost native click. A true result HTTP 200 was held until pointerdown. Its completion callback launched a passive Attempt GET, which set the same busy state used by the local recovery button. Before pointerup the button became disabled, so no click event reached the restore handler. The candidate stayed safely in IndexedDB; this was not a lost draft or an observed component remount.

The first controlled pointer-schedule observer recorded the same article node, result/Attempt timing, and no click, but its disabled field referred to the answer input; it did not directly prove the recovery button's disabled or pointerup state. The later permanent test closes that gap with the actual button:

- RED: pointerdown true, pointerup true, disabledBeforePointerUp true, clicks 0; original three-way heading assertion fails.
- GREEN: identical permanent test bytes, pointerdown true, pointerup true, disabledBeforePointerUp false, clicks 1; complete case passes (10.2s).

This real controlled response schedule reproduces the outcome and mechanism. It does not claim that the original CI pointer timestamps were recorded.

## Minimal repair

Two product files changed. useAssessmentAttempt.retry distinguishes a passive grading refresh from a foreground user reread. Passive refresh neither toggles shared busy nor clears existing local-operation errors. Epoch/full-reference/read consistency, reconcile against the latest candidate, genuine CAS/idempotency, foreground busy, and terminal write protection are retained. AssessmentView uses that dedicated passive callback when grading completes. IndexedDB/CAS algorithms and policies are unchanged.

The original test's local two-page candidate preservation and explicit safe close remain. It now also holds genuine API responses at a native gesture boundary, uses an actual viewport/hit check, and establishes the legitimate completed-worker baseline before checking terminal immutability. There are no manufactured parsed grades, increased timeouts, retries, or assertion deletion.

## Actual checks and failed harness history

- Original observer launcher first failed to load import.meta under a temporary CommonJS context: no tests executed. A temporary type=module marker fixed the isolated harness.
- Original observer replay: one failure on expected revision 3 versus observed 5; three-way recovery passed in that run.
- First controlled locator-click schedule: one failure at the missing three-way heading, same product source.
- First permanent manual-mouse instrumentation: 90s timeout because it did not first scroll/hit-check the actual button. It is a harness failure, not product RED. Timeout was not enlarged.
- Corrected permanent RED: one expected failure at the unchanged three-way heading, actual button disabled before pointerup and zero native clicks.
- Same permanent test after the two-source repair: one passed, 10.2s. All candidate/terminal assertions complete.
- Full frontend units: 201 passed / 29 files, 3.10s. Lint and build passed. The existing >500kB chunk warning remains.

The raw artifacts are unchanged at their original temporary locations. This package contains bounded error excerpts, scalar observer projections, source hashes/diff and original boolean gesture receipts. It intentionally excludes full DOM, report attachments, profiles, databases, authorization values and screenshots. The source diff is intentional reviewable code, not an accidental failed-test source attachment.

Commands: each focused native run used the actual Playwright CLI with its privately captured temporary configuration (configuration files are not included in this package) and grep for the existing two-page preservation scenario. Unit/lint/build used bash scripts/node.sh npm --prefix apps/web run test|lint|build; stdout records actual underlying commands. The original and enhanced test hashes are in source-comparison.json. Seven product paths were captured through diagnosis; only the two stated product paths change in GREEN. Final fixed-source complete gates remain the parent's task.

publication.inspect scans every packaged file; manual provenance review additionally limits input to original synthetic tests and code. The scanner is bounded and is not a general guarantee of private-data recognition. A separate receipt lists final hashes including the inspection file itself.
