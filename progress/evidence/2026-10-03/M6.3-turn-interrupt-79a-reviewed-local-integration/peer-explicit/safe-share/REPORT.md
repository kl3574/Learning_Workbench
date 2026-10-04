# Independent static review: M6.3 interrupt

Input: `cc2cc675f91a2794c44267e46687422d5ae50019...79a3c0da4bef9d948bcd6a969a25ff55fd5833a0`, isolated `m63-turn-interrupt-owner-oct04`, clean when read. Production remains `1b49cb6870f2b8e89337ddd26da82b5e46391e75`; the final commit adds tests only. Sole v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

This is one independent reviewer, with separate Standards and Spec passes. All four agent slots were occupied; no extra parallel reviewer was claimed. Review used fixed Git, the full changed code/tests/generated diff, unchanged owner/access/job helpers and the sole specification. Zero product, test, database, CLI, model, browser, network or security-probe execution. The author's dynamic gates are not counted as this review's results.

## Standards

One P3 workflow finding: PRODUCT_DESIGN.md §18.4, line 908, requires small commits to contain the task_id. The complete messages of `1b49cb68` and `79a3c0da` are respectively `feat(codex): persist interrupt through the shared Jobs stop owner` and `test(codex): cover interrupt races and immutable stop bindings`; neither contains M6.3. The branch correctly contains M6.3. This is a source-history labeling issue, not a product/permission defect. Preserve the already frozen commits; a normal later integration commit should include M6.3 and explicitly name these source commits, while retaining this original finding.

No additional confirmed documented-standard breach or actionable code-smell finding in the reviewed change. The typed v4 wrapper preserves original v1/v2/v3 models, the single existing Jobs stop reducer owns state changes, and the new migration owns only the independent interrupt membership. It does not write Provider/Session facts via foreign SQL, hand-edit public response semantics, or add ambient app-factory effects.

## Spec

Zero confirmed product-contract findings against §20.17.5/7 (lines 1754–1760 and 1812–1832). `CodexTurnService.interrupt` lines 89–112 rechecks current control identity and complete history before original-key/full-body replay, then applies current session CAS for a genuinely new command. Known wrong session/turn gives 409, unknown/cross-workspace remains 404. The route uses existing unique-header, Origin/CSRF and strict query/body boundaries; subject data is absent and current learner/Policy-safe control remains available.

`request_stop` lines 404–458 shares the real transaction/reducer with Jobs cancellation and approval decline. Interrupt has an independent public command and a private `interrupt_stop` namespace, so equal strings cannot turn an unrelated original Jobs cancel ACK into a current interrupt ACK. First request and pre-start terminal release retain their distinct session revisions; observations/new keys do not recreate a terminal or claim a remote interrupt. The repository checks the enclosing request/ACK, original private stop body/snapshot, actor/workspace/session/turn and current historical revisions, plus independent membership/digests and Jobs/Run witnesses. Missing tails, members or the entire interrupt family are not rebuilt by a read.

Original ACKs survive later terminal/new-turn/current state and application reconstruction. Final delivery uses a fresh safe-identity check. Tests explicitly cover concurrent same/new keys and Jobs entry, rollback before/after append, learner and real assessment Policy, late logout, rehashed binding damage, lost-owner recovery, pending unsupported approval, and late response/usage retention. Reading these tests does not establish that they passed in this review.

## Limits and merge boundary

This implementation registers a real local interruption request and convergence path. It does not implement or prove an actual app-server/CLI interrupt adapter, reliable remote process mapping, process termination, file-writer quiescence, actual model billing or whole M6.3 completion. The controlled peer and same-database application reconstruction do not prove physical/OS restart acceptance.

The separate memory-operation branch uses Codex event v5; this reviewed branch uses v4/0031. Future integration must retain both decoders, envelope unions, reducers and full checks, then run the combined owner gates. This report covers only fixed 79a3, not that future merge.

Summary: Standards 1 P3 history-label finding; Spec 0 confirmed findings. No confirmed product blocker; no dynamic acceptance claim.
