# Independent static review: Codex turn UI 629003c8

Source: `629003c89b205b066c1a9abe80fb11aef19093b2`, base `f11c170d7ba9bee88a88fe104f3a0a9b44bef753`. Sole PRODUCT_DESIGN v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. Exactly 11 changed files (926 additions, 7 deletions). One independent peer, two review axes; no claim of two separate reviewers.

## Standards

No separately confirmed Standards finding. New command/form/memory modules have closed typed records, immutable original command/basis checks, bounded conflict resolution, and guarded storage. Existing generated clients and current-session decoder are reused. This conclusion is a static scoped review, not proof of all implementation properties.

## Spec: one P2 OPEN_STATIC

**Fresh permission is missing at explicit unsent-form restoration.** `apps/web/src/features/codex/useCodexTurns.ts:90-98` checks only cached `identity`/`allowed`, immediately copies the selected original prompt and refs into visible form state (line 94), then persists a new branch using cached `actorRef`. Unlike preparation-detail reads and command execution, this path never calls `fresh` or `port.session`. `CodexTurnPanel.tsx:44` exposes this callback directly; the prompt is rendered at lines 31-40.

Concrete source-level counterpath: an author A successfully reads the local records, while an older A form remains un-restored. The actual server session subsequently becomes actor B, learner, or a Policy-locked session without a local generation notification. Clicking “恢复原表单” still uses cached A and reveals the old prompt/refs and saves a new A branch, with zero permission read at that action. A later POST would have fresh checks, but that does not protect the earlier academic disclosure. The existing actor test (`CodexTurnPanel.test.tsx:151-163`) first explicitly refreshes; it does not cover this boundary. Sole lines 1816 and 1828 require current access at academic delivery. This is a static counterpath, not a peer-executed test or browser observation.

Minimal repair: before revealing or branching a recovered form, capture its original actor/workspace and use the existing guarded async fresh academic read; discard late callbacks on access/port/store/unmount change. Preserve the original form and leave zero POST on failure. Do not rebuild an old command or change its key.

## Corrected preliminary observation

An earlier message classified the absence of a separate original page/access-generation field as a P2. That classification is withdrawn: the current hook has live page/access/revocation/port/store guards plus fresh identity checks, and this review established no bypass of those checks. `OBSERVATION_CORRECTION.json` preserves the observation and correction. Root clarified explicit same-actor original-key recovery semantics; no production fix is claimed. This withdrawn item is not counted among confirmed findings.

## Other reviewed boundaries

- Explicit prepare/cancel only; refresh/GET do not auto-POST. `execute:158-171` freshly checks the original actor, persists the full original key/body/basis, then rechecks before POST. Storage failure retains isolated memory. Replayed durable ACK short-circuits POST.
- Original ACK is decoded and retained before scope checks (`execute:172-178`), so late responses belong to the original command. No form-consumption path deletes later input. 412/409 retain original command/CAS; independent GET does not rewrite it.
- Unsent snapshots keep exact Unicode and selected block refs; switching the reader does not replace a chosen ref. The form offers zero or one explicit block; this is a limited UI selector, not a claim of all possible context selections.
- Academic forms, preparation details and original prepare commands are filtered by current admitted author state and actor; safe control reads/cancel remain available to valid learner/author. The finding above identifies a missing fresh transition check in one restoration action.
- Parent dirty/safe/isolation state includes the turn module; memory remains protected through unmount and beforeunload. A store save is considered durable only after the existing transaction completion.
- Bootstrap changes only add a ready current-session ID selection callback. Bootstrap command/ACK/wire files are unchanged in this delta. A selected ID still needs an independent current GET before preparing.
- No start, grant, model/tool execution, result stub, new HTTP route, backend or generated-contract change exists in these 11 files. UI wording explicitly describes the limited prepare/control scope.

## Evidence and limits

No application, test, database, browser, CLI/model, network or system diagnostic was executed for this review. Author-reported gate counts are not adopted as peer execution evidence. Tests were read as source only. No overall M6.3, native, permission-race or runtime acceptance is asserted. Full non-progress Git inventory is included solely to bind the fixed source; it does not claim that all inventoried files were reviewed or executed. Source and prior sealed reports remain unchanged.
