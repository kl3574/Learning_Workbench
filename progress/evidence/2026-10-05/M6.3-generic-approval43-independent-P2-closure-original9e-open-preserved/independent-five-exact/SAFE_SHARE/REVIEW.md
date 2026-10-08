# Independent GenericApproval safe-decline delta closure

Fixed candidate `43c70d660d98904903bd607a4661b3b95710293e`, base `9e4ce1bab62d23cef0ef3f3354fa606ee62d090b`. **Standards: zero new P1/P2. Spec: zero new P1/P2; SAFE_DECLINE_BLOCKED_BY_PRIOR_APPROVE_COMMAND is CLOSED_STATIC for this fixed candidate.** The original9e P2 OPEN_STATIC report and its seals remain byte-identical. This is an independent source and admitted archival evidence review, with no new product execution and no overall acceptance or publication claim.

## Review identity and normative scope

I authored none of the product source, owner tests, native harnesses or merges. One reviewer evaluated Standards and Spec separately. PRODUCT_DESIGN v3.0.15 is the sole product/engineering norm, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. Memory was used only for project identity/preservation, never as specification. The review reads the immutable source and precisely93 owner-selected safe candidates rooted at `m63-generic-approval-safe-decline-evidence-oct05/safe-candidates`, plus its three explicitly authorized outer/raw seals. Unlisted raw failed logs, private fixtures, DB/cookies/CSRF, browser profile/cache, keys, TMPDIR and archives were not read. No CLI, model, network, host or product probe was run.

## Standards axis

The correction is confined to the existing command-presence predicate and its two decline call sites. `useCodexApprovals.ts:144` accepts only an optional literal `decline` filter; the default continues to match every prior command for the same actor and target. `:146` applies the filter only to new decline. `CodexApprovalsPanel.tsx:51` uses the same filter for the decline button. The existing fresh access admission, execute path, command/body/key construction, persistence-before-POST, immutable original ACK, replay, form memory, scope invalidation and academic approve guard are unchanged. Panel affordance and handler therefore share the same rule.

The delta is3 paths,46 additions/3 deletions: two production files4+/3- and one test file42+.1519/1522 base inputs are byte/mode/type/blob/size/SHA-identical. Two production files at43 equal their fixed11a versions exactly. The final tests add learner/independent/open_book rejected-approve cases, unknown-approve preservation and the reverse negative case that an unknown prior decline still blocks a new approve while original decline replay remains explicit. No unrelated repair, backend/schema/profile/registry change or new defect was found within this delta.

## Spec axis and closure rationale

§20.17.4 (`PRODUCT_DESIGN.md:1738`) allows valid same-workspace learner/author decline without protected operation text, using the complete revision/hash in the safe turn approval_controls. §20.17.7 (`:1828`) keeps safe decline available under independent/open_book, while new approval requires current author/academic authority and original actor; original key/body and historical ACK remain independent facts. The old same-target any-command predicate disabled decline after a rejected or unknown approve, even with a fresh actual pending safe control. The new decline-only filter removes that obstruction without granting approval or automatic retry.

A new explicit decline receives a new key and the complete current safe-control basis. It leaves the old full approve record untouched, even if that old result is unknown. A prior decline still blocks another new decline. New approve still uses the unfiltered predicate and original authority checks. The server's existing CAS/hash/owner/unique-decision checks remain unchanged, so a stale pending control cannot override an actual later decision. This report closes the fixed source finding only; it does not alter the original9e OPEN inference or retrospectively attribute either old full-Web failure to this defect.

## Immutable input and candidate readback

All93 candidate files were read and their size and SHA256 matched the explicit PUBLIC_CANDIDATES entries. Original raw hashes were reconstructed using only the declared exact home-prefix substitution, resolving literal-marker ambiguity against fixed size/hash; PNG bytes are identity. No excluded raw log was opened to do this. The raw PUBLIC_CANDIDATES, REPORT and PACKAGE_SEAL hashes match the parent's supplied values. The PACKAGE_SEAL outer references match their selected candidate reconstructions. Eleven full candidate source files equal the actual fixed Git blobs; owner and P2 patches equal the exact Git deltas.

All12 immutable Git head manifests were independently bound:18180 path-input records and1517 distinct actual Git blobs, with mode/type/blob/size/SHA checked. All11 Generic UI owned paths relative to412 are present;1511 existing412 inputs remain exact. For actual selected runs, six before/after gate pairs plus three native before/terminal sets and two successful native after sets give20 maps and30440 runtime input bindings, all exact to their respective immutable Git heads. Summary GATE_BINDINGS contains27 historical pairs and NATIVE_BINDINGS four runs; the other21 historical gate pairs and earlier9e positive native were **not** rebound from unselected originals in this delta.

The original9e preserved hashes are:

- REVIEW.md `2660ac4d67567d0f60a5e0df4cd156dd3df091ebf78ed300ba144bf6cf55c555`
- READBACK.json `8554207c7736a3b5f5f2ee857a9b6a662c35a9eb18a192ae3fdf2399dba28d11`
- SAFE_SHARE.json `26a1e826e3f7a42c974a8136f6ad0f9191e7f90384d996c5bfb8dc5134127c3f`
- OUTER_METADATA.json `dfc3fe36add7824b060c407cb96fb5ab032b8a701dc37056f43bd11677a143c6`

## Actual selected regression evidence

| Original stage | Fixed source | Readback result and limits |
| --- | --- | --- |
| red-safe-decline-02 |29fcdd0a|Actual terminal receipt exit1 with full1522 before/after exact; safe owner summary declares3FAIL/19PASS. Raw failed log excluded/unread; its original SHA is retained.|
| green-safe-decline |11a7099d|Actual admitted log38PASS/3files, exit0, full1522 before/after exact. The complete component test file is byte-identical29fc/11a:18023 bytes, SHA256 `89c2082821d5ecc41c9124ec6866413e8f1e5c4ee908c3098d02b211670aa73c`.|
| closure-full-web |43c70d66|Actual admitted log1399PASS/166files, exit0, full1522 before/after exact. Original log SHA `f1b44048956562dd34973d229ef09ccfef75477d141b4763757dd090f59c4f5d`.|
| closure-strict/build/spec |43c70d66|Three actual exit0 receipts/admitted logs, full1522 before/after exact. Strict is TypeScript unused/type checking; build retains existing chunk advisory; spec is the original structural baseline gate, not M6.3 acceptance.|

The final43 component file adds two more cases after11a, so the complete final file is **not** claimed byte-identical to RED29fc. The exact29fc→11a RED/GREEN relation remains preserved; final full-Web includes the expanded final source. No new focused40-test gate is invented or added to the full1399 count.

## Actual selected native evidence and visual readback

The RED9e and GREEN43 counter runs share **identical complete bytes** for native.mjs, controlled_api.py and run.py, bound to the actual command/run receipts. RED has before and terminal-source, both full1522 exact, actual exit1; no successful after/receipt exists or is fabricated. GREEN43 and final positive43 each have before/after/terminal-source full1522 exact and exit0. Commands, harness hashes, timestamps and original log hashes are recorded in READBACK. Both GREEN original logs were admitted and read; the RED failed raw log remains excluded.

Selected RED counter-observation and failure directly show an actual approve HTTP403, approval still pending at r1, original approve retained, safe decline disabled, one synthetic memory request and zero literal execution. Selected GREEN observation shows the same actual403/pendingr1/prior-retained facts with decline enabled. The unchanged harness then asserts explicit new decline key/full safe body, whole original approve journal unchanged, no new protected approval GET and zero literal execution. This is now a controlled executed counterexample plus its repair evidence; it does not rewrite the original independent static-only9e report.

The separate positive43 harness verifies full operation DOM disclosure, persistence before POST, loss of an actual200 ACK, reload with zero automatic POST, explicit same-key/full-body/byte-identical original ACK replay, unchanged durable ACK after independent current GET reaches completed, and learner safe-only decline of a second unsupported empty-registry operation. It uses two explicitly prepared synthetic memory-protocol model requests and one explicitly released pure literal operation; the literal result asserts zero host actions, provider requests and files written. It does not execute a real Codex CLI, remote model or physical command, and does not establish production sandbox, server restart or all actor/permission timing cases. The component tests cover independent/open_book; those modes were not exercised by this Chrome run.

I individually viewed all10 selected1440/390 PNGs. Counter RED shows pendingr1 with grey disabled decline, GREEN shows pendingr1 with enabled decline. The positive learner PNG is captured after a saved decline and appropriately shows disabled decline with a historical decline ACK; it must not be confused with the RED pending-before-decision obstruction. The desktop operation view contains the synthetic full command; mobile views show portions of long scrollable details, and no single mobile PNG is claimed to contain the full command or ACK. Full DOM/durable assertions come from the independently read harness and bound receipts, not from the cropped images alone. All screenshot hashes match their safe candidates and selected successful receipts where present.

## Preserved failures and acceptance limits

The selected QUALIFICATIONS and ERRATUM retain the original031 two full-Web failures, prior9e bounded PASS coverage gap, and the checkout/index-lock preflight as NOT_RUN_PRODUCT. No unique cause is assigned to the original031 failures by this repair. The preflight lacked a product-start source manifest and product run.log; no replacement source map or success is fabricated.

Parent reports separate root412 full native132PASS/1FAIL; that full run is not independently read in this delta and is not replaced by these scoped43 successes. This closure therefore authorizes no whole-platform acceptance, real provider/CLI/host capability or remote publication claim. It is a fixed-source P2 closure with explicitly selected actual evidence and zero new source findings.

## Explicit safe sharing

Only5 authored text candidates (REVIEW.md, REVIEW.json, READBACK.json, FIXED_SOURCE_INPUTS.json and VERIFY_READONLY.py) plus2 outer metadata names are selected. Their only transformation is exact home-prefix replacement. The archival transformed verifier is not a runnable equivalent. The raw independent working package and intermediate source-only readback are not recursively admitted. Publication remains a root decision; no external application was written.

Bounded pure `inspect` of exactly5 proposed text candidates returned zero findings; it supplements manual provenance review and is not a history-wide or product test gate.
