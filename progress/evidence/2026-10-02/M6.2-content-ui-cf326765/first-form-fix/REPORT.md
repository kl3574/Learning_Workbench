# Content impact UI independent review and bounded form repair

Reviewed base: `e0e24592879ee60b437a6d7d5ff25632a58efae5`.
Fixed repair: `3be34e9fc320a1543b8d694426c680b7b06bbbc9` (direct child of the reviewed base).
Repair tree: `$HOME/.cache/learning-workbench-acceptance/m62-content-impacts-ui-independent-oct02`, branch `fix/m62-content-impact-form-recovery-oct02`, CLEAN.
The original implementation tree remains CLEAN at exactly e0e245. Main, backend, generated contracts, progress, dependencies and the specification were not modified.

The frozen review contract was PRODUCT_DESIGN.md v3.0.11, SHA-256 `35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29`, particularly §4.3 / §20.11 / §20.13. During this work root adopted v3.0.12 separately; this fixed UI repair does not implement or claim its new Restore numeric semantics. Source and gates remain bound to the requested e0e245 base.

## Findings

**Spec: one P1 data-loss finding, repaired here.** At base e0e245, ContentImpactsPanel's Form held decision/reason/artifact IDs/confirmation only in child useState. On role/Policy changes, useContentImpacts.clear removed `frozen`, unmounting Form and clearing its dirty indication. Restoring author permission did not restore those unsubmitted bytes or even a safe existence notice. The private original 33-case run produced 32 PASS and 1 actual product FAIL in `focused-private-tmp`. `independent.test.tsx` preserves the original probe. This contradicts §4.3 line245 (“不允许只因组件卸载而丢数据”) and §20.13 line1238 (hide protected payload while retaining necessary undurable memory). Root explicitly approved this bounded P1 repair.

The repair retains a separate page-only form with its exact frozen basis, keyed by workspace and original in-memory session identity. Policy/role changes and component removal hide it while preserving a non-subject existence notice and exit protection. Only an explicit recovery operation, after a new actual Session read and current event/target reads, can display the original session's form. Another session cannot extract it. Restoration clears confirmation, retains original reason/Unicode/newlines and basis, does not issue a Content POST, and does not adopt a newer target or head. A changed current basis blocks the form save until explicit discard and new adoption. The existing original command/ACK memory and journal are separate. A form is consumed only once its exact command is durable; the two existing Shell controls that explicitly discard temporary forms now also discard this workspace's temporary Content forms. No session secret enters IndexedDB, API bodies or report artifacts. Cross-refresh Content replay remains unavailable; §20.10.1 has not been extended.

**Standards: no additional blocking finding in this bounded diff.** Changes remain in the dedicated feature, its tests, one Authoring aggregation test, one native scenario and the two existing explicit-discard Shell paths. All runtime DTOs remain generated/closed. No owner alias, fake event/job, new backend route, migration or dependency was introduced. The isolated reviewer had all four agent slots occupied; standards and spec were reviewed separately by the same reviewer, not represented as two independent subagent reviews. Once root assigned the repair, the resulting code became an implementation and was handed to another agent/root for final independent review.

## Other audited boundaries

- `client.ts` and `useContentImpacts.ts` discover event IDs only from the real public list/detail responses or an immutable original command. The original native chain produces its main event via real UI Edit → exact saved candidate Review → explicit synthetic human decision → publication. Extra pagination/current-target revisions are explicitly controlled ContentService owner publications, never SQL event insertion or guessed outbox IDs.
- `schema.ts` validates closed summaries/views/receipts, ref identity and revisions, snapshot classification, target/ref/body binding, canonical request/receipt digests, target sets, history order, and legacy read-only semantics. ID-only evidence is not promoted when the current target differs from the frozen exact reference.
- The list retains the applied filter/limit/cursor while more pages are read. Duplicate pages and invalid client limits are rejected. The actual server's three-page high-water sequence excludes a later real publication; a new first page includes it. Two filters and restart discovery are covered. Backend strict query/ledger integrity is inherited; this review did not rerun the complete backend suite or claim a new proof of every backend integrity case.
- The selected target/current ref/head is explicitly read and adopted. A real two-context competing decision gets 412, preserves its original command, and requires a new read before adoption. ACK never overwrites the separately read current status. The original command's page/access/session/body/key is preserved for explicit replay; other page/access/session attempts are blocked.
- Unknown initial permission prevents subject journal reads, listing and target reads. Delayed list/current/fresh restoration callbacks cannot repopulate a paused scope. Actual assessment Policy hides rendered payload and yields HTTP409. Received ACK plus actual IDB transaction abort survives the isolated-memory role cycle; save-only recovery sends no HTTP.
- Authoring aggregation probes independently show isolated Content memory does not enable the role-control exit while Authoring is busy/unread or Review is unsafe. When those other owners are safe, the intended isolated-memory exit remains available. Existing consent and Review safe checks were retained.

## Final exact-source gates

All five final gates used the same 14,031 input files, with identical before/after SHA-256 lists and no source changes during execution. SOURCE_BINDING.json verifies all tracked bytes against the final Git objects, all eight changed paths, clean status, unchanged original tree and the frozen spec hash.

| Gate | Actual result | Evidence directory |
| --- | --- | --- |
| Content impacts + all Authoring focused | 115 PASS / 16 files | `focused-fixed-final` |
| Full Web suite | 659 PASS / 102 files | `full-web-fixed-final` |
| Strict unused/type check | PASS | `lint-fixed-final` |
| TypeScript and production build | PASS / 809 modules; existing large-chunk advisory | `types-build-fixed-final` |
| Actual native Chromium + HTTP/SQLite/IndexedDB | 2 PASS, 1.1 minutes | `native-fix-04` |

Each directory contains the exact command, exit code, log hash and complete input hashes. `native-fix-04.config.mjs` has no global webServer: each RestartRuntime owns random loopback API/UI ports and private SQLite/browser directories. The only shared toolchain is the unchanged pinned toolchain symlink; this review installed its own node_modules and Python environment. A short private TMPDIR avoids the host /tmp quota and Chromium socket-length limit.

The first native test covers the original actual publication/discovery/decision chain, exact→ID-only historical correction, true two-context CAS, original lost-ACK replay, true IDB abort, isolated memory, role cycle, fixed-member pagination, two filters, restart, original parent Lesson pin and assessment Policy. The second native test uses actual UI input and two actual cross-tab learner/author cycles, verifies original Unicode/newline reason, fresh permission/current reads, reset confirmation, preserved old basis after real target publication, disabled stale save, close/cancel retention and explicit close discard. It records zero actual Content decision POST requests, zero journal commands and zero server decisions for this unsubmitted form scenario.

`NATIVE_READBACK.json` independently verifies canonical request/receipt digests, identical replay body/key, immutable first receipt, exact/ID-only distinction, three unique old-cursor members, the original parent reference, and the new scenario's zero writes and reason digest. Actual native artifacts are under `native-fix-04-artifacts`.

The original 33-case product-red set was first rerun after the repair as `focused-fix-01`: 33 PASS. The form assertion was updated to explicitly request restoration before reading protected text, as required by the new recovery guard; automatic redisplay is not the intended behavior. Additional cases cover repeated cycles, new same-workspace session, late fresh Session/current responses, changed target, workspace isolation, removal/reopening, exact durable consumption and other-owner unsafe aggregation. The original failing test file and log remain unchanged.

## Preserved failures and limits

- `native`: Playwright transform cache failed before tests with host /tmp quota (`-122`).
- `focused-red`: the same host temporary-cache problem caused four import failures and zero executed tests. This is not the product-red finding.
- `native-private-tmp`: a too-long private TMPDIR caused Chromium SingletonSocket path failure before product use. Switching to a short private directory resolved it.
- `native-short-tmp`: the untouched reviewed base's original native scenario passed (26.7s), independent from the implementation author's evidence.
- `focused-private-tmp`: the real P1 product red, 32 PASS / 1 FAIL, preserved.
- `native-fix-01`: original chain PASS; new scenario omitted the required one-time authentication helper and correctly encountered the unestablished-session UI. Test initialization corrected; guards unchanged.
- `native-fix-02`: original chain PASS; the new second page sent its shortcut before UI restoration. Added the existing “UI 会话已保存” readiness wait.
- `native-fix-03`: original chain PASS; recovery had actually restored the text (failure ARIA snapshot contains the correctly named textbox and original text), but exact getByLabel matched label textContent including restored textarea content. The test now uses the actual accessible textbox role/name to verify its value. No product behavior was changed for this locator fix.
- Final `native-fix-04`: both complete scenarios PASS. Earlier screenshots, raw logs and intermediate test files remain retained.

This is page-memory protection, not durability across forced browser termination. Before-unload protection and explicit discard remain necessary. Protected restoration fails closed when current permission or source material cannot be verified. No new API/provider/remote action occurred. Synthetic human decisions test software behavior only: mathematical, numerical, source-quality and teaching approval remain NOT_RUN. This review/repair is not complete M6.2 acceptance and does not address the separately assigned ReviewPanel temporary-form issue.
