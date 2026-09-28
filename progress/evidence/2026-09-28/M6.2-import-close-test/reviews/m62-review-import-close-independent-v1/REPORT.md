# 36b501 independent Standards and diagnostic-boundary review

Result: **no blocking finding for this one-file test repair**. This is this agent's independent Standards/source/evidence review. Root's separate Spec review is a different author and record; this report does not claim two nested parallel reviews.

Fixed comparison: `git diff a944ebfbdb835a731393977a606db5b473846e98...36b501cf8da071909fbb5628b7354de70d5d1825`. One commit and one changed path: `apps/web/src/features/draftReview/ReviewImportShell.test.tsx` (61 additions / 3 deletions). Tree clean. PRODUCT_DESIGN.md is the sole product/engineering standard, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`; relevant rules are line 239 (unsaved close/unmount protection), line 741 (distinct verification layers), lines 898–900 (evidence and completion boundaries), line 1136 (preserve existing close protection). No network/issue lookup supplies requirements.

## Standards axis

No documented-standard breach or blocking smell in the changed hunk. At test lines 50–59, default `waitFor` now requires the reason to be editable and discard enabled before the original single discard click. Final-null, reason retention, zero Import commit, no confirmation and GET-only assertions remain. No timeout, retry setting, product guard, generated contract or production code changed.

The new test (lines 65–120) uses the existing Shell/ImportWorkflow/Review/Publication components and production DraftStore/publication ledger implementation backed by `fake-indexeddb`. Its temporary spy delays only `load` and then delegates to the original method; it does not invent ledger records. Existing `useImportWorkflow`, transport and auxiliary-hook fixtures remain synthetic. This is component/persistence coverage, not real browser IndexedDB, real HTTP, or product end-to-end evidence.

The disabled click and later enabled click are two explicitly different actions in the new regression: ignored disabled click cannot auto-replay when the load completes; the unchanged original case still has one discard click. The new assertions require the same open dialog and preserved reason before that new explicit enabled click, then closure and no write. `finally` releases the barrier; `afterEach` restores the spy and closes the stores. Shared setup duplicates the existing fixture shape but does not justify a new abstraction for this bounded repair. No heuristic smell is treated as a hard violation.

## Diagnostic evidence and causal limit

The unchanged state chain was read before the owner narrative: usePublication refresh/busy around real ledger load (lines 33–54), PublicationPanel safe propagation (11–21), ReviewPanel aggregate guard/forms (23–32, 72–77), ImportWorkflow forwarding (19–22), Shell guard/discard (109–111, 236). It supports a mechanism, not reconstruction of the missing remote click trace.

The exact original 86,301-byte CI log remains SHA256 `76eed27dc745865cb24f4aa2eb2c409c97c75a4a3df24bef0b995266a87ff383`. Original focused stage01 PASS does not resolve it. Stage02 actually fails after metadata records one held load, connected disabled discard, same reason node; after release the button enables but the dialog/reason remain and writes are empty. Stage03 changes the release/readiness/click order and passes the original final-null/no-write assertions. Its passing log contains no probe stdout; source assertions plus recorded PASS are the available evidence. Remote CI did not record whether its own button was disabled at the click. Therefore the diagnosis is a supported candidate, not a proven unique historical root cause, and no remote PASS is claimed.

## Separate stage04 observation and data risk

Stage04 is a real 2 PASS / 1 FAIL on a different no-dirty scenario. Its frozen source never enters the new reason, and closes after observing the child's held ledger read; the confirmation dialog is absent. This is an unresolved close-guard/notification-window observation in unchanged product code. The several effect hops make a stale parent guard plausible, but exact ordering was not traced. Stage06's dirty-form regression does not fix or reclassify stage04.

The recorded stage04 setup has no unsaved review reason/publication confirmation and no write request. The pending operation is a read; existing persisted commands are not deleted by the close handler or hook cleanup. Thus these records do not demonstrate lost user text, lost durable commands, duplicate submission or publication. They also do not establish safety for every unsaved/in-flight window. A later bounded clean/busy-state investigation remains appropriate. This pre-existing separate observation is not a blocker to the scoped test-only repair and must not be described as resolved.

## Independent verification

All 1089 owner-manifest members were read and checked against actual size/SHA256; inventory completeness, original CI bytes, complete eight logs/receipts, before/after inputs, runner hashes and every CAS input were verified. Actual Git objects were read independently: 1023 distinct input blobs, exact per-stage mismatch accounting. Stage01 is 1040/1040 Git; stages02–03 are 1040/1041 plus the exact private diagnostic copy; stages04–06 are 1039/1040 against base because the permanent test is modified; stage06 test bytes equal fixed final. Stages07–08 each bind all 1040 inputs to 36b501. Fifteen owner final-source copies plus the additional DraftStore context are pinned locally.

Actual final evidence is stage06 3 PASS; stage07 49 PASS / 9 files; stage08 strict TypeScript PASS including noUnused checks. Neither this review nor those focused gates prove full Web/native/remote CI success. `VERIFY.json` and `verify.stdout` provide machine results; `verify_owner.py` only reads owner/tree and writes this separate review cache. One initial mistaken `run.log` lookup is retained in READ_ERROR.json; the actual `test.log` files were subsequently read. No tests, network calls, source/index/progress mutations, or new publication were performed.
