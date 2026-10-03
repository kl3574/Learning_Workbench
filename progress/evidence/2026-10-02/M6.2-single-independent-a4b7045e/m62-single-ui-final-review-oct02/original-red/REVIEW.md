# Independent UI review: 4232676b

Fixed diff: `git diff 3d970152...4232676b`. The original UI worktree was read only and remained clean. Independent probes were added only to a separate detached worktree. Sole normative source: PRODUCT_DESIGN.md v3.0.13, SHA256 949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05. Parallel review slots were occupied, so the two axes below were examined separately by this reviewer.

## Standards

No confirmed hard standards violation or useful heuristic finding. The changed feature uses the existing named transport, strict DTO, DraftStore, access generation and guarded write conventions. This does not establish the semantic correctness of those guards. Tool-enforced formatting/type issues were not reclassified as review findings.

## Spec

1. **P1 — a fresh different actor still inherits same-page replay eligibility.** `apps/web/src/features/singlePublication/useSinglePublication.ts:53` accepts the current actor ID, but `:79` and `:190` authorize command replay only by page ID and access generation. After an original unknown command is persisted, a fresh session response identifying a different actor while the page counter is unchanged still yields `canReplay=true`; explicit `execute` actually invokes publish again with the original key/body. This violates the requested original-session command boundary and the original-command semantics in §20.15.1. A local event counter cannot override an observed different authenticated session. Retain a page-memory command-to-original-actor proof and require the fresh actor to match; missing proof or changed actor is read-only, while the existing cross-page/access-generation refusal remains.

   Reproduction: `independentActorReview.test.tsx`; `actor-red.log` fails the eligibility assertion; `actor-post-red.log` separately fails because publish call count is 2, expected 1. No physical browser or real server publication is claimed by these controlled hook probes.

2. **P2 — published GET accepts a later r2 as the original publication reference.** `singlePublicationSchema.ts:15-20` checks the state/null relationship but never applies the existing `singlePublishedRef` r1 validation from `:22-25` to a non-null GET `published_ref`. A strict-shape response with state published and revision 2 is accepted and can be displayed as the original publication. §20.15.1 fixes Single's original publication at r1, and §20.15.2 requires that exact original ref even after current advances. Validate non-null Single GET refs with the existing helper; ordinary current reads must continue to allow r2.

   Reproduction: `independentReadbackReview.test.ts`; `readback-r1-red.log` fails because the r2 readback did not throw.

Other examined boundaries: warning instances come from the original generation preparation plus all ordered numeric checks; every warning instance must be confirmed, while wire codes deduplicate. Latest numeric gating does not silently choose an older PASS. Current publication GET, original ACK, and later current reads remain separate; no GET auto-publishes. Original body/key and late ACKs survive IDB failure; Policy loss hides protected data; form recovery rereads its exact basis and resets final confirmation; group publication stays excluded. Source NOT_APPLICABLE with truly empty sources is compatible with existing admission; this review found and prompted a separate Single-only backend historical-verifier fix (c65372cf), not a new UI/spec requirement.

Original feature suite: 6 files / 27 tests PASS on fixed 4232676b. Independent semantic probes: 2 distinct defects, 3 failing runs retained (P1 eligibility and execution are separate runs of one defect). No physical numeric, native browser, or full-stage PASS is inferred.

Totals: Standards 0 confirmed findings; Spec 2 findings, worst P1. The UI owner acknowledged both and is implementing fixes; this report applies to the pinned original commit only.
