# Independent Single publication UI review

Reviewed fixed `4232676b5669592d260f994edd94b4392e003ab6` (18-file commit, parent `3d9701526f5a586accc74d37b9a38a3a309a3a5c`) in detached isolated tree `$HOME/.cache/learning-workbench-acceptance/m62-single-publication-ui-review-oct02`. Exact command: `git diff 3d9701526f5a586accc74d37b9a38a3a309a3a5c...4232676b5669592d260f994edd94b4392e003ab6`. Product/source tracked diff remained empty. Own npm install. Sole spec: PRODUCT_DESIGN.md v3.0.13 SHA949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05. Prior full v3.0.12 and complete approved v13 delta read; §20.15 and recovery/permission requirements applied. The UI author's later uncommitted useAuthoring initialization change is excluded.

All four agent slots were occupied. Standards and Spec were reviewed as separate axes by this reviewer; no claim of two independent child reviews. AGENTS selects PRODUCT_DESIGN.md as sole engineering specification; no issue/provider/remote lookup or setup changes were made.

## Standards

No separately confirmed documented-standard violation. The change uses named owner routes/ports, preserves distinct Single vs Import/Restore/Group identities, uses the generated closed DTOs, and confines command/confirmation state to its own store and page-memory module. TypeScript strict/noUnused passes. Shared-pattern duplication is not reported as a defect absent a demonstrated consequence; the substantive form-consumption finding is listed under Spec.

## Spec

**P2 — A later accepted confirmation form is silently consumed by the earlier publication attempt.** `useSinglePublication.ts:136-148` awaits the initial ledger read before reserving busy/working; while it is pending, real Panel controls still accept changes. `execute` then calls `releaseSinglePublicationForm(workspace, originalSession, command.basis)` at line87 without checking that the held selected/confirmed value is the submitted value. Line92 clears the visible basis. The old command correctly sends once, but the newly edited form disappears from both the UI and held memory.

This violates the preservation boundary in §4.3 (line247: unsynchronized changes require save/discard/cancel) and §4.4 (line263: changes while a request runs belong to a later request, not a silent alteration of the current one), and the explicit local confirmation preservation behavior claimed by this new UI. It does **not** demonstrate unauthorized publication: the original explicit click remains authorization for its frozen old command. It demonstrates loss of subsequent accepted local selections. No body/secret exposure is alleged.

Reproduction uses the real SinglePublicationPanel, original controlled fixture and real IndexedDB store; only the first submit-time store.load Promise is held. Prepare; check both same-code warning instances and the final checkbox; click publish; while held uncheck warning2 and final confirmation. Assert original actor memory now contains selected=[0], confirmed=false. Release the first read. The original exact four-field POST completes once, then memory unexpectedly becomes[]. Expected: do not accept later editing while a submitted operation is being reserved, or retain it without consuming a different form version.

Root and the UI owner received the failing probe. No product file was changed by this review. The immutable raw diagnostic probe intentionally records the old open-input window; a fix that freezes controls at entry may require a separate permanent regression that measures native `:disabled`/fieldset semantics, rather than pretending the old diagnostic is an unchanged green test. Exact-value consumption can make the original diagnostic green directly.

## Actual verification

- original-focused:40PASS across8files,1257inputs unchanged. Covers strict journal/replay, old page/access, unknown ACK, actor-bound retained ACK persistence, IDB write failure, owner/current separation, warning instances, old numeric rejection, Review branch and published numeric admission.
- independent-probes-01:2PASS/1FAIL across3probes,1258inputs unchanged. FAIL is the concrete form loss above. PASS: first ledger read failure preserves exact form and causes no POST; late candidate read after Policy hides payload and cannot overwrite original confirmation or submit.
- strict-lint:PASS,1258inputs unchanged.
- Browser native/physical runtime/full Web/full Python:NOT_RUN by this independent review. Root's separately reported3native passes and actual numeric environment BLOCKED evidence are not attributed to this SHA review's tests. No model/provider call was made.

Raw probe archived as independentSingleReview.test.tsx SHA0b73f3f720e8766b316e31703c19b6ddb87dc418e24767c8fe5784b1e8c065d2. Original red log independent-probes-01/run.log SHAe5fe6b55e6148aab584cd87654caf828a29dd7a09622e410f2dc1b87a060b410. Reproduce from the isolated review tree with `bash scripts/node.sh npm --prefix apps/web test -- src/features/singlePublication/independentSingleReview.test.tsx`. red-readback.json proves fixed423 and empty tracked diff. review-scope.json binds all18original files to exact Git bytes.

## Bounded conclusion

Standards:0confirmed findings. Spec:1confirmed P2 form-preservation blocker on4232676b. The other reviewed journal/page/access/late-response and ACK/current boundaries have no additional independently demonstrated defect in this review; this is not a complete backend/physical execution acceptance or approval of later unpublished fixes.

## Separate reviewer coordination

After this fixed423 audit, the implementation/review owner reported a separate actor-provenance P1 fix eeba82315fb761a9dc230a4c327b6335319d473a and a forthcoming published_ref r1 validation fix. Those are not independently verified or counted as this review's discoveries;423 must not be called globally clear of those externally reported defects. The owner chose exact form-version consumption for the P2 above, aiming to run the original diagnostic unchanged; its future result is NOT_RUN here.
