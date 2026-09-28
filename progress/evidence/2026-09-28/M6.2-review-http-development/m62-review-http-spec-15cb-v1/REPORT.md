# HTTP Spec axis — fixed 15cb608

Read-only review of `ba8fa72...15cb60882751f32d2d6f5b14516dfe6611c40fcc`, four commits, ten changed files. All reviewed sources are fixed Git blobs. Sole specification: PRODUCT_DESIGN.md 3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. No tests rerun.

No blocking Spec finding in this API-composition slice. The three specified review routes are registered with strict existing owner DTOs, current authenticated session, unique control headers, CSRF/Origin protection for writes, exact idempotency keys and rejection of unknown/duplicate query fields. Human decisions remain session-authored; the HTTP layer does not accept a client reviewer or turn machine NOT_RUN into approval (Appendix A, lines 1969–1970; §20.4 line 1011).

`main.py` constructs actual Import/single/group candidate and numeric owner mappings, registers Quality report plus existing Import artifact readers, and starts/stops the actual ReviewWorker inside the existing lifespan. Constructors add no lifecycle-triggering call. Generic Jobs dispatch preserves existing consumer branches and gives draft_review its safe read/cancel methods. Current access and real artifact bytes remain enforced by the underlying reviewed application ports; download responses are attachments and explicitly non-cacheable (Appendix A line 1958; §20.2).

Generated OpenAPI adds only the three requested operations. New request/response component models are closed, typed schema projections; generated TypeScript carries the corresponding exact body/response/path/header associations. Route coverage advances three routes while retaining 23 missing routes and `product_acceptance: NOT_RUN`, consistent with §20.1 and the bidirectional coverage rule at lines 1935–1937. No unrelated endpoint was removed or widened in the inspected semantic diff.

The committed tests exercise real local HTTP/SQLite/worker, rejected decisions, actor identity, stale revision, original ACK, active assessment Policy, revoked/lowered sessions, safe cancellation and worker lifespan; these are read test definitions, not independently rerun evidence. Synthetic decision fixtures are not human content certification.

Scope remains partial M6.2: browser review UI, publishing, version comparison, impact propagation and restoration are absent from this slice and require later work (§19 stage table line 945). This report does not grant those functions or overall platform acceptance. Root must integrate final workflow f5 changes and validate the exact combined source.
