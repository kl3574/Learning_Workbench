# Independent review: actor session continuity combined with CodeMirror / Edit Review

Reviewed commit `b78f781393dd4f266b2db73c26a366f4476d615c`; scope `git diff b78f781^...b78f781` and its interaction with the approved CodeMirror / Edit Review combination. Sole normative document PRODUCT_DESIGN.md v3.0.11 SHA35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29, especially §20.10.1. Root requested read-only original-tree review. Original tree remains CLEAN at the fixed SHA. All reproduction was in a detached independent worktree with own node_modules and venv; only a seven-case private test file was added there. No production edit, remote/provider action or secret extraction.

## Standards

No documented-standard violation or actionable baseline design-smell finding within this delta. The server projects the existing trusted identity instead of introducing an authentication alias. Client wire DTO, journal discriminator, original command/basis checks and transport boundaries remain explicit. The Review and CodeMirror guard production files are byte-identical to approved 3657dab; merge-sensitive useDraftEditor retains reviewSnapshot invalidation, exact saved-head Review admission, pending-memory isolation, abort/generation fencing and close protection.

## Spec

No blocker found within reviewed §20.10.1 behavior.

- `services/api/app/application/sessions.py:18` returns `SessionIdentity.id`. `infrastructure/security.py:54-67` independently creates random cookie material and `session_<uuid4>` ID. ID is neither cookie/CSRF nor their derivation. Both actual response contracts require actor_session_id and forbid extras; actual GET is no-store and DB-zero-write, role-cycle/API-restart stable, fresh bootstrap distinct. Role ACK remains a historical receipt; replay consults fresh GET.
- `editJournal.ts:9-49` strictly separates preserved v1 from required actor/workspace/route v2. Route is derived from the exact operation. Original body, baseline and CAS are one durable record; immutable collision checks prohibit changing actor under an existing command key. No current actor is filled into legacy rows.
- `useDraftEditor.ts:129-160` admits only matching base/workspace/original actor for v2, with v1 retaining page/access limits. Every execute first reads and validates fresh SessionResponse, current author and both assessment Policy IDs. Cross-page/access PATCH re-reads the exact old draft revision and matches candidate/payload; create verifies the exact original content ref. Original key/body/CAS are then sent only after durable original persistence. Permission failures, malformed/unknown session or stale async response stop before mutation and hide material; no GET auto-replay. Read/base validation failures are not mislabeled as mutation rejection (`sent` guard).
- Server DraftEditService continues revalidating actual authenticated actor/role/Policy inside the write transaction; DraftEditRepository selects recorded idempotency receipts by real workspace/actor/route/key and validates original body. Actor headers do not change identity; body actor claims are forbidden. Fresh authenticated actor cannot recover the old client's commands through ordinary UI or obtain an old actor's receipt.
- DraftEditor and MarkdownSourceEditor files exactly match 3657dab. Shared `editorDisabled` still includes dirty/unsafe Review and conflict/non-draft states; CM blocks doc-changing transactions while disabled, resets undo on identity/external replacement and clears state on unmount. ConflictResolution preserves identity key and disabled propagation.

## Independent verification

Fixed identical 13,971 before/after source inputs in all four stages, including the independent seven-case probe. SOURCE_BINDING.json separately verifies every 13,970 tracked file byte against b78f781; original review tree is still clean.

| Stage | Command after capture wrapper | Result |
|---|---|---|
| stage01-focused | `bash scripts/node.sh apps/web/node_modules/.bin/vitest run --root apps/web src/features/draftEditor src/features/editPublication src/features/draftReview` | PASS 102 / 13 files, including 7 independent negative cases |
| stage02-http | `.venv/bin/python -m pytest -q tests/integration/test_session_actor_continuity.py tests/contract/test_api_projection.py` | PASS 114, 143.95s; existing Starlette/AnyIO deprecations only |
| stage03-native | `bash scripts/node.sh apps/web/node_modules/.bin/playwright test --config $HOME/.cache/learning-workbench-acceptance/m62-session-editor-independent-evidence-oct02/native.config.mjs` | PASS 2 actual Chromium flows / 36.8s |
| stage04-lint | `bash scripts/node.sh npm --prefix apps/web run lint` | PASS |

Private `sessionIndependent.test.tsx` cases: fresh GET workspace mismatch, revoked 401 and missing actor; delayed Session GET released after Policy pause for both create/PATCH; damaged original material for create/PATCH. Every case checks zero mutation calls and exact original journal bytes/record unchanged. Permission failures additionally verify payload hidden; original-material failures do not create a new key or turn into a false recorded mutation rejection.

Actual browser editor flow independently repeats real create lost ACK→reload original replay, original unexecuted PATCH CAS→competing actual HTTP update→412 three-way recovery, later PATCH committed/lost ACK→browser/API restart→same-actor original replay, new actor denial, v1 raw record retention, Unicode/LaTeX/blank lines, CM undo/identity isolation, actual IDB abort and role-cycle memory recovery. SQLite readback is one draft, revisions 1/2/3/4 and exactly four successful commands all bound to original actor. Retained journal v2 actor/route fields, no csrf/cookie/token_hash, unchanged v1 legacy raw, identical replay key/body and two API generations were independently read back from editor-flow.json. Zero page errors.

Second native repeats real saved Edit→Review→explicit synthetic human decision→publication, unchanged parent pins, original ACK/current distinction and restart. Native sourceGuards only prove actual contenteditable=false / readonly UI and recovery behavior; they do not claim keyboard-handler coverage from scroller focus. Actual disabled CM dispatch and nonempty Undo are independently covered by the existing focused DOM tests. No full Web/Python suite or global M6.2 completion is claimed by this bounded independent review; root's other fixed evidence covers those separate gates. No new failure occurred in these four independent stages.

Remaining boundaries: v3.0.10 actor continuity is only Edit create/PATCH; Review, Edit publication, Restore and other journals retain their owner rules. Unsaved memory still cannot survive forced browser termination. Synthetic human judgments remain protocol fixtures, not academic/source/teaching approval. This independent tree has 106 runtime operations; root's Content impact-list integration and final 107/127 regeneration are outside this review.

Findings: Standards 0; Spec 0; no new blocker found within the reviewed scope.
