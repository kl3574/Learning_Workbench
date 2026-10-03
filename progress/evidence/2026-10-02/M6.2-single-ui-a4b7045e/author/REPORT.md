# Single generated worked-example UI evidence

Fixed source: `a4b7045e435e0c4fa7c2b2364ade2407a8cd9afc` in `m62-single-publication-ui-oct02`; clean tracked worktree. Sole specification: v3.0.13, SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`.

## Delivered scope

Dedicated Single publication panel/client/schema/journal/page memory/hook, connected through the named Single Authoring/Review branch. Uses the existing four-field POST; server allocates the new r1, with initial current=null. Original ACK, independent candidate published_ref GET and later current GET remain distinct. Reads original generation materials and warnings plus all numerical checks; never submits the historical draft display warning. Strict latest complete PASS and explicit human decisions/warning instances precede UI admission; the server still owns complete execution, frozen Review endpoint, current ledger and atomic publication verification. A BLOCKED numeric result gives an explicit no-PASS/no-publication message.

Command actor continuity is proved only within this page and exact immutable command. Fresh Session identity/workspace/Policy are checked for prepare, original-command send, form recovery and save-only memory recovery. Page/access generation must still match; no cross-refresh Numeric/Review replay authority is added. Late ACKs remain bound to their original actor in page memory. Unsent forms have versions; submitting or replaying an older command cannot consume subsequently accepted input.

Authoring initialization is separately repaired: early subject reads wait for academic journal admission, safe cancellation remains usable, and permission/journal admission is independent of control operation sequencing. Late control/academic loads preserve the other partition; explicit refresh, Policy denial and workspace change supersede old admission.

## Commit chain

- `3d9701526f5a586accc74d37b9a38a3a309a3a5c`: required published_ref DTO/contracts base (separate prior report).
- `4232676b5669592d260f994edd94b4392e003ab6`: initial UI; 897 Web PASS. Superseded by the following review fixes.
- `8d9de3f094d5a5118b7432f88a4b66229e218d74`: deterministic Authoring admission race repair; 905 Web PASS. Three RED traces preserved.
- `eeba82315fb761a9dc230a4c327b6335319d473a`: original actor proof and fresh identity recovery checks; 33 Single focused PASS.
- `fd8aa16e98f920e11c7f04185a7cef1fa1d1aa0e`: exact Single published_ref must remain original r1, ordinary current still allows later revisions.
- `a4b7045e435e0c4fa7c2b2364ade2407a8cd9afc`: exact submitted form version consumption; 39 Single focused PASS.

## Final results at a4b7045e

- PASS: full Web Vitest, **917 tests / 131 files**, `web-final-reviewed.log`.
- PASS: TypeScript and unused-local/parameter lint, `lint-final-reviewed.log`.
- PASS: production build, `build-final-reviewed.log`. Existing large-chunk advisory remains; not a build failure.
- PASS: private actual-frontend hook/client/fake-IDB capture, **1 test**, `capture-final-reviewed.log`; its exact probe is retained beside this report.
- PASS: independent actor, r1 and late-form probes were copied byte-for-byte into regression tests and passed. The late-form probe retains SHA256 `0b73f3f720e8766b316e31703c19b6ddb87dc418e24767c8fe5784b1e8c065d2`.

`single-publication-actual.json` contains the captured controlled UI transport requests/responses, synthetic Job/numeric/Review fixtures, original ACK and separate GET projections. It excludes headers, Session objects, actor IDs, CSRF, tokens, cookies and raw environment. Its `limits` explicitly mark backend SQLite, physical numeric runtime, native browser and human content quality **NOT_RUN**. This is software-boundary evidence, not a successful real publication or physical numerical PASS.

## Preserved failures and limits

The initial whole-Web initialization failure is retained as `web-full-authoring-admission-race-fail.log` (896 PASS / 1 FAIL). Deterministic detail, cancellation and overlapping-recovery RED logs are `authoring-admission-red.log`, `authoring-admission-cancel-red.log`, and `authoring-admission-overlap-red.log`; the same cases pass after the separate repair. Actor, r1 and form consumption RED logs remain `single-actor-red.log`, `single-readback-r1-red.log`, and `single-form-consumption-red.log`. Earlier test-only stale-node/timing failures remain labeled separately. Do not present these historical snapshots as the final source gate.

No backend publication owner, database, canonical specification, e2e diagnostic or root native test was changed here. Backend state projection on the DTO-only base was previously NOT_ACCEPTED until the separate backend owner implements it. Combined real native/SQLite/physical-runtime acceptance belongs to root's integrated tree; environment BLOCKED results must remain BLOCKED. Reviewers are independently rechecking these fixed client corrections.
