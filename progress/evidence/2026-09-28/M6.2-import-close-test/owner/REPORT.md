# M6.2 Review Import close test diagnosis

Fixed candidate: `36b501cf8da071909fbb5628b7354de70d5d1825`, based on `a944ebfbdb835a731393977a606db5b473846e98`. Only `apps/web/src/features/draftReview/ReviewImportShell.test.tsx` changed. Product source and default test timeout/retry settings are unchanged. This is the implementer's bounded diagnosis and validation receipt; independent review is pending.

The sole product specification is PRODUCT_DESIGN.md, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. Section 4.3 (line 239) requires explicit handling of unsaved changes before close/unmount; section 20.8 (line 1136) retains existing unsaved close protection. Section 19.3 defines this evidence receipt. No prior design package supplies requirements.

## Observed failure and limits

The copied complete push frontend log (`ci-push-frontend.log`, SHA256 `76eed27dc745865cb24f4aa2eb2c409c97c75a4a3df24bef0b995266a87ff383`, 86,301 bytes) reports 511 passed / 1 failed. Its failing case is `actual Import and Shell preserve review reason until explicit close without submitting import or review`, at original test line 58:76: the Import dialog remained when the test expected null. The received dialog and failure are at log lines 327–1012; final totals are at 1026–1027. The retained log does not record the close button's disabled state at the failed click. The matching PR PASS reported by the parent is not used as causal proof in this audit.

The unchanged original focused test was executed once in stage 01 and passed (one case; the other was filtered). This did not reproduce or resolve the remote failure. No full suite, native browser or remote CI was rerun by this task. Node 24.21.0 and npm 11.19.0 match the original log; that match alone does not establish identical scheduling.

## Ranked hypotheses and controlled check

Before modifying the original test, the candidate causes were: (1) a publication ledger read keeps the existing discard button disabled when the synthetic test clicks; (2) review polling or dirty-state propagation changes close safety; (3) a stale DOM node or reopening after an enabled close handler. The evidence most directly supports (1); no claim is made that all possible causes in the historical remote run are eliminated.

Source chain, unchanged between a944 and the final candidate:

- `PublicationPanel.tsx:11–21`: receipt identity participates in the selected owner; its busy state reports `safe` through an effect.
- `usePublication.ts:33–54`: refresh reads the session, then awaits the real publication command store load before finishing. A changed selection starts this effect again.
- `ReviewPanel.tsx:23–32` and `ImportWorkflow.tsx:19–22`: aggregate and propagate dirty/safe state into Shell.
- `Shell.tsx:109–111,236`: dirty or unsafe Import opens confirmation. The discard button is disabled while unsafe; its enabled handler directly closes both dialogs.
- The original test awaited only the existence of the reason field, used `fireEvent.change` even if that field was disabled, and clicked discard without checking whether the button was enabled. A synthetic change can populate a disabled input; a disabled React button does not invoke its click handler.

Stage 02 used a private diagnostic copy of the original test. The original permanent test and all product files remained unchanged. A barrier delayed only `publicationCommandStore.load` after receipt GET, then delegated to its original real IndexedDB implementation; it did not substitute invented commands or alter the API response. Assertions and emitted metadata establish that the discard button was disabled and connected, and the reason was the same live DOM node. The original immediate click was performed once. Releasing the load later enabled that button while Import remained open and the reason remained present; no writes occurred. The original final null assertion then failed. This is a controlled reproduction of the symptom through a demonstrated mechanism.

Stage 03 changed only the order of the load release/readiness wait and the same one discard click. It passed the unchanged final null and no-write assertions. `probe-single-variable.diff` preserves that difference. The successful reporter did not include the probe's console output; its source assertions and actual PASS, rather than invented stdout, are the evidence. These two stages support the fixture repair. They do not supply the missing click-time trace from remote CI, whose precise cause remains a **supported candidate**.

## Permanent repair and additional observed failure

The original test now waits, using default `waitFor`, until the reason is editable before changing it and until discard is enabled before one explicit click. Its reason retention, final null, no commit, no import confirmation and GET-only assertions remain intact.

A new permanent regression uses real Shell, ImportWorkflow, Review/Publication components and real IndexedDB stores, with the existing synthetic GET transport and other existing fixture boundaries. It first enters a reason through an enabled field, demonstrates the existing return-from-close protection, then explicitly refreshes publication permissions and gates the actual ledger load. A disabled discard click must leave Import and the reason present. Completing the real load must not replay that ignored click. A new explicit enabled click then closes Import; no write endpoint or Import commit is allowed. The load spy is restored in `afterEach`; the barrier is released in `finally`. This is component and persistence behavior coverage, not real HTTP or browser end-to-end validation.

Stage 04, the initial form of this new regression, actually failed: 2 passed / 1 failed. It had no dirty reason and attempted closing immediately after the child indicated a gated load. Import closed, so no confirmation dialog was found. The source's multi-effect safe notification provides a plausible parent-notification window; the retained observation does not prove its exact internal ordering, a lost user draft, or the historical remote failure. No product correction was made for that separate no-dirty scenario. Stage 06 narrowed the new regression to the original dirty-form scope described above and passed all three cases. Stage 04 is retained as a distinct observation, not relabelled as the original RED or as a repaired product defect.

## Actual execution ledger

| Stage | Result | Source |
|---|---|---|
| 01 original focused | 1 PASS, 1 filtered/skipped | clean a944 |
| 02 gated ledger / original click order | 1 FAIL, 1 filtered/skipped | a944 plus private diagnostic copy |
| 03 enabled click control | 1 PASS, 1 filtered/skipped | a944 plus changed diagnostic copy |
| 04 initial permanent guard | 2 PASS, 1 FAIL, distinct no-dirty scope | a944 plus test edit |
| 05 strict lint | PASS | exact stage 04 source |
| 06 dirty guard | 3 PASS | final test bytes, before commit |
| 07 final Review + Publication | 49 PASS / 9 files | clean 36b501c |
| 08 final strict lint | PASS: `tsc --noEmit --noUnusedLocals --noUnusedParameters` | clean 36b501c |

All eight complete logs, commands, exit codes, inputs before/after and receipts are retained. `run-ledger.json` records exact hashes and distinguishes development modifications from actual Git. Final stages have 1,040 source paths, all matching the fixed Git objects before and after; the engineering inventory includes tracked files except `progress/`, including `docs/ui`. Historical diagnostic copies and edits are preserved in the content-addressed source pool, with their actual non-Git status. `VERIFY.json` records checks against the actual Git objects rather than merely trusting input labels. No test timeout, retry count, assertion expectation or product close guard was relaxed.

No provider, secret, GitHub, main tree or other agent's worktree was changed. No screenshot was generated. The original CI failure stays failed; independent review and any integration are the parent's next steps. The no-dirty observation remains separate and may warrant a later bounded investigation; this change does not claim all close scheduling concerns are settled.

## Replay and handoff

Read `TASK_RECEIPT.json`, `final.diff`, `probe-single-variable.diff`, `run-ledger.json` and the complete per-stage logs. `final-source-pins.json` binds the final test and relevant unchanged source; `source-pool/` binds every actual executed input. `PRIVATE_MANIFEST.json` hashes the frozen evidence members. `freeze.py` is the verification/build script used before freezing; do not rerun it into the frozen directory. This private evidence package has not been prepared or certified for public publication.
