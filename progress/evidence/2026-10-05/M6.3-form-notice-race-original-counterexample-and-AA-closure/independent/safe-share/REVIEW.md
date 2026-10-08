# Independent late form-save notice repair review

Fixed source: `aa85092f73aa85b53eb200039ee5b4b8ccbb63c1`; original combined base: `4353a05570afd9f2378c904b5594998de21bc474`; test-only RED: `62d0b53101815efc1e6da336b78b1efd2c2228ae`. Sole norm remains PRODUCT_DESIGN v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. One independent reviewer authored none of this source and evaluated Standards and Spec separately. No two parallel axis reviewers or new product test execution by this reviewer is claimed.

The narrow repair is ready for root integration: Standards 0; Spec 0 additional findings. The original4353 combined full Web **1 FAIL /1277 PASS** and original combination report remain unchanged. The passing Web result below belongs to aa85092, not to that earlier source. No canonical merge, combined Python PASS or whole M6.3 acceptance is claimed.

## Standards

Zero additional findings. The full delta is two paths,35 insertions and2 deletions:32 new controlled test lines and3+/2- runtime lines in `useCodexTurns.ts`. The runtime change extracts the existing complete autosave write-admission predicate into `admitted`, passes that same function to the existing writer and also uses it before reporting a late autosave failure. It adds no new request, subscription, mutation, storage format or broader error handling. The existing `.then`, `.finally`, writer lifecycle, memory retention, persistence guard, command/ACK handling and other hook branches are unchanged.

Pure reconstruction of the two edited runtime statements reproduces the entire original4353 hook byte-for-byte. All1493 fixed source inputs have the same file membership as4353;1491 entries are unchanged. All server, Artifact512, SSE95 generator, DTO, original command, ACK, form/storage and memory owner source therefore remain at the reviewed combined bytes. The test-only RED commit changes only the test file; that complete test file remains byte-identical at the fix.

## Spec

Zero additional findings. PRODUCT_DESIGN:1001 requires discarding stale asynchronous results across workspace/session/context changes; §20.17.7:1828 binds browser recovery to page/access generation and freshly read original actor/workspace/Policy, while retaining late ACKs under their original command. The fix applies the existing hook's live admission predicate to a notification that previously checked only component scope. The predicate includes original form actor, current hook actor, author/assessment eligibility, write admission and page/access scope. The original predicate's write semantics are unchanged.

When the explicit fresh session read detects a different actor or denied author/Policy state, the existing path hides protected state and clears `actorRef`. The new late form-save catch therefore cannot replace that newer denial notice. It does not change where the original ACK/form is retained, change its actor, release the unsaved form, expose protected prompt/ACK details or resend a prepare command. The close/retained-memory protection and explicit local recovery path remain unchanged. This is admission to a UI notice using the latest observed hook identity/access state; it is not a new server-side authorization check or guarantee about an unobserved server change.

The added controlled Promise test explicitly waits until the actor-denial notice is visible, then releases the delayed save which throws. Its RED fails at line271 because that notice has been replaced. At the fix it also verifies original actor/ACK and form retention, absence of protected prompt/command DOM and one prepare call. This establishes the controlled notice-overwrite mechanism. The original4353 full Web failure log alone is not claimed to contain this whole event trajectory, and the fix does not reclassify the original actor/ACK isolation as having failed.

## Original actual gates and independent readback

The controlled RED at62d0b531 is **1 FAIL /34 skipped**, exit1, log SHA256 `fe37e6eb4c5d661e60031f721df34ac96d7ede154b67c20c7ad65558062730ff`. At aa85092 the exact same complete test bytes produce **1 PASS /34 skipped**, exit0, log SHA256 `bfc40035823761a20e923c161ad4a6e4f9afa8a57b7de5f9f9d2be7a3f7688f9`. The skipped cases are not counted as PASS.

At the fixed source, all Codex regression is **296 PASS in15 files**, log SHA256 `bf3a1aa01997efe18a229dc7414fb4fe2f1e14739db22191d806d3a2093f2891`. Full Web is **1279 PASS in157 files**, exit0,13.79s Vitest /14.143887715006713s runner, log SHA256 `15e9b218821b23a9d22ecf04fb8696ca9b80b1816a09f26c2289a5ceec812a6e`. Strict Web types and Web build each have original terminal exit0 at aa85092. These overlapping gate counts are not additive. They are React/Vitest synthetic-port checks, not browser/native UI or real-provider acceptance.

All six repair gates have exact complete1493 before/after Git input maps. The extra original4353 full Web FAIL pair was independently bound again to its original source; its log remains SHA256 `12e3aaa0edec1b77b0686c871f267d44b2d04260ddf9f4592548bf11412db7aa`. The original combined report, JSON, readback and two seals remain unchanged. This preserves the full failure and does not retroactively fill it with aa85092 success.

The pure verifier completed with exit0. `READBACK.json` SHA256 is `013fa09ec0949eaa58ef7faa8a935aa2265744a2253359d135792cbb0e2bd7d3`; it checks1493 fixed inputs,1491 unchanged prior entries, seven original before/after pairs and10451 Git map bindings. It verifies exact receipts/logs, byte-identical RED/fixed tests, the unchanged original write predicate, controlled Promise ordering, old failure/seal preservation and all live fixed worktree bytes.

No product test, model, CLI, network or host probe was run by this reviewer. This UI review does not admit a Python terminal result from4353 or assert the fix was merged into canonical. Whole M6.3, external provider/App Server, physical numeric sandbox, mathematical/source/pedagogical approval and a real browser/native SSE consumer remain separate. Only explicit safe candidates may be published; raw failed logs, databases, credentials and temporary runtime contents remain private.
