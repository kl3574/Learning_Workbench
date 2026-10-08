# Independent static closure: turn-form recovery

Fixed `db5a6bceaeadf099de9b3a9e6d6a7ce786071db2`, parent `629003c89b205b066c1a9abe80fb11aef19093b2`. Exact two-endpoint delta: four files, 139 insertions and 11 deletions. One peer reviewed Standards and Spec separately. No application or tests were executed.

## Standards

No new confirmed finding. `useCodexTurns.ts:90–116` reuses the existing strict form decoder, immutable snapshot reader, session checker, guarded persistence and error handling. `CodexTurnPanel.tsx` explicitly discards the handled async result; its two existing test changes await the actual restore completion before retaining the prior assertions. The repair does not introduce a second storage or access protocol.

## Spec

The original cached-access recovery P2 is **CLOSED_STATIC**. Sole v3.0.15 `PRODUCT_DESIGN.md:1816`, `:1828` and `:1830` require current actor/workspace/Policy and rechecking protected delivery. The fixed flow has the following concrete checks:

- `useCodexTurns.ts:91–96`: synchronously claims the existing operation scope, validates the complete original snapshot, then freshly reads strict session identity with the original actor and current author/no-independent/no-open-book requirement.
- `:97–104`: reloads the exact snapshot ID, requires full structural equality with the original, rejects conflicting held data, and freshly checks access again. A damaged durable record throws; it cannot fall back to a remembered list item.
- `:106–110`: creates a distinct draft/snapshot branch only after admission; retains it until actual guarded persistence completes; then freshly checks access before delivery. The original ID and bytes are not written.
- `:111–115`: only a still-valid operation exposes prompt/refs and the success message. Loss of current access hides protected state; already committed original-actor facts are retained. Existing `currentScope/valid` (`:30–31`), `fresh` (`:45–51`) and writer cleanup (`:55–64`) guard page/access, admission, port/store replacement and unmount.
- The recovery function calls no prepare/cancel POST and constructs no remote command. It does not grant a permit or start a turn. Persist-before-POST and old ACK decoders are unchanged.

The previous separate-original-generation observation remains withdrawn, exactly as recorded in the original 629 package. This closure does not revive it or claim that db5 fixed it. The original OPEN report and its correction record remain unchanged.

## Test-source and evidence correspondence

The new `turnFormRestore.test.tsx:26–45` preserves the original five countercase bodies: unannounced actor change, learner, independent, open-book and workspace change. The fixed file adds eleven cases: exact successful read/commit ordering; permission change during local read; permission loss during branch persistence; changed/conflicting/missing local baseline; and admission/workspace/port/store/unmount while reading. These assert original record retention, no unauthorized protected delivery and no prepare/cancel POST. Unicode prompt and exact refs remain covered.

Offline original-RED readback verified all three saved production files byte-for-byte against 629 and the recorded exit 1 / five failed cases. The final test file is not whole-file byte-identical: imports were extended and eleven cases appended. Its original setup and five-case body, lines 11 through the old end, are byte-identical. The initial whole-file prefix check returned false for that reason and is preserved as a comparison-scope observation. No fixed GREEN or full-gate result is claimed from this static inspection.

## Limits and sharing

This establishes source-level closure of the reported recovery defect, not browser, IndexedDB scheduling, full UI or M6.3 acceptance. Author gates were RUNNING when requested; their later outcome is separate evidence. The complete non-progress Git inventory binds immutable source blobs, not an executed-test input map. No source, original sealed package or root checkout was modified.

Only the explicit `SAFE_SHARE.json` candidates and `PUBLIC_OUTER_ALLOWLIST.json` entries are offered. Copies are exact original bytes with no path transformation. The package contains authored review text, fixed source patch and hash/path metadata; it contains no DB, archive, credentials, account data, raw transport headers or actual runtime responses.
