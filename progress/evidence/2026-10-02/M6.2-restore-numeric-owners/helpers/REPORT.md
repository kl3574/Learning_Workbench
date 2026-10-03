# Restore numeric UI support checkpoint

Fixed commit: 61db5588737db0ac1f09ae18c4c44982fb20f081, parent 34bb546d956e69534ff57373eeeeeddca361986f. Scope: four UI support modules and four associated fixture/test files. No hook, panel, specification, progress, main composition or remote mutation.

The schema interpreter reads generated restore-numeric-schemas.json, with no handwritten replacement DTO. It enforces closed required fields, finite numbers, Unicode/codepoint bounds, exact original source slices and JSON decimal relations when supplied the saved Restore snapshot. Intrinsic symbol/binding relations, snapshot discovery, complete check/result relationships and original preview/decision ACK distinctions are checked. Matching source or a numeric PASS does not constitute mathematical approval.

The numeric command journal preserves the original owner/workspace/page/actual non-secret actor-session ID/access generation, route identities, complete body, original key and ACK. CSRF/cookie/session comparison handles are not persisted. New-page, different-actor or changed-generation replay remains inadmissible. IndexedDB persistence uses the existing transaction-completion and abort guard; conflicts and different ACKs are refused. Page memory retains commands/ACKs whose persistence failed and permits recovery only for the original session handle. Root owns unsent form memory separately.

Client methods are session/draft/current/preview/check/decide through the shared generated request transport. At this checkpoint the three real owner routes have not been registered in this tree. The client explicitly refuses to send if API_ENDPOINTS lacks the operation; it never inserts a substitute endpoint or bypasses shared session/CSRF handling. Real composition and final generated routing remain an integration dependency. The only type bridge is guarded by the actual generated endpoint registry; it can be replaced with direct typed calls after the real backend has registered all three routes.

## Validation

- Focused schema, command store/memory and client: 65 tests / 3 files PASS.
- Strict TypeScript lint: PASS.
- Full Web: 726 tests / 107 files PASS.
- TypeScript and production Vite build: PASS, 813 modules transformed. Existing large-chunk advisory preserved in raw log.
- Full Web/build fixed inputs: 14,346 tracked files byte-identical before/after and Git tree clean.
- Native UI/actual execution and complete Restore workflow: NOT_RUN for this support checkpoint; root and backend owner integrate them separately. No Provider calls.

Initial focused run: 64 PASS, 1 FAIL. The foreign-candidate negative fixture shared the same candidate object between snapshot and material; structuredClone retained the alias, so mutation changed both identities. The test now replaces only the material candidate and proves refusal. The initial TypeScript run also exposed the fixture's overly broad DraftCandidate entity type, corrected to explicit block. Original failing logs remain in this evidence directory; no production validator was weakened to satisfy them.
