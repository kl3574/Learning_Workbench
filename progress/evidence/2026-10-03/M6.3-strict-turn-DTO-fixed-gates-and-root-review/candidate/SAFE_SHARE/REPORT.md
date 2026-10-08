# Codex turn contract slice

Fixed final source: `8da88ed890a25ee9ed6753fb6b4599625e449bf8`, following initial DTO seam `760af1e44c5447f60ba53248fbdd694ee25c774d`. Base sole v3.0.15 is `de7e21dd046e2c70d11aa95c80f6f69d308de4e8`, SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. Root inventory-only commit 50ec is separately cherry-picked as 071bccba.

Implemented 47 named strict objects plus closed SSE payload, operation and SafeCode aliases. Two standalone generated artifacts derive from the same Pydantic models without adding registered endpoints. Current session projection uses CodexCurrentSessionView; the original bootstrap ACK/view decoder, ordinary Provider DTO, 54 core and 0001 retain exact base bytes. New nullable fields are required. Self-contained guards cover bounded identities/order, precise block references, tool budget binding, grant/dispatch linkage, complete approval control bases, file before/after pairs, exact answer UTF-8 SHA, manifest membership/totals/hash, and distinct Import child bindings. Semantic permission, private freeze hash, owner membership, protocol truth and authorization still require the real owners.

| Fixed source | Actual verification | Result and limit |
|---|---|---|
| 760af1e4 | 7 selected contract files | 456 PASS in 133.49s; includes registered/OpenAPI equality at 116 runtime operations and 147 declared operations. This original source remains NOT_ACCEPTED because of the separately confirmed P2 below. |
| 760af1e4 | Ruff, mypy, verify-spec, web strict, standalone contract strict | PASS; mypy 253 source files; 82 generated artifacts, 54 core models; Node v24.21.0. |
| 760af1e4 | Independent pure DTO revision counterexample | 4 FAIL: actual started r2 and completed/failed/unknown below terminal r4 were wrongly admitted. Root independently confirmed completed/r2. Original evidence is retained. |
| 8da88ed8 | 6 selected contract files (132 new DTO tests included) | 342 PASS in 3.57s. API projection suite from 760 was not counted again: this two-file correction has no schema/registration change. |
| 8da88ed8 | Exact same private counterexample bytes | 4 PASS in 0.19s; this overlaps the permanent negative scenarios and is not four additional product behaviors. |
| 8da88ed8 | Ruff, mypy, verify-spec, web strict, standalone contract strict | PASS; mypy 253 source files, 82 artifacts/54 core/147 declarations, Node v24.21.0. |

The narrow P2 correction requires revision >=3 for an actual start and >=4 for an actual terminal operation. It does not invent history for an unstarted close. Original ACK r2 remains a decision, not execution. Parent owner work must integrate and independently verify the registered handlers.

Both formal source stages bind all 1393 tracked non-progress engineering inputs to their exact Git blob and SHA256 before and after; only progress/ is excluded. Inputs are unchanged and the worktree was clean at both stage completions. Dependency links reuse existing read-only Python/Node dependencies; no installation occurred. Separate private runner and counterexample sources are explicitly hashed. Ordinary verify-spec performs its existing synthetic in-memory schema/fixture structural checks; no Codex CLI, account, model, turn, tool, external request, or system probe was executed.

Development failures are retained: initial mypy list variance errors (session-output transcription, explicitly not a raw log), and one test-harness substring assertion that mistook the declared price_unknown literal for the TypeScript unknown type. It was corrected to inspect identifiers outside string literals. These are distinct from the real approval revision P2 and from formal fixed-source gates.

Exact source/old-generated equality and synthetic ACK canonical preservation are verified; this slice does not claim a new real historical SQLite ACK migration oracle. No runtime/HTTP registration, ordinary Provider interface, bootstrap decoder, migration, canonical specification, root progress, remote or application UI was changed. Full combined Python/Web/native, runtime recovery and real model/tool acceptance are NOT_RUN here. Prior overall failures/BLOCKED states are not erased.

Sharing is allowed only for SAFE_SHARE.json entries and PUBLIC_OUTER_ALLOWLIST.json metadata. Temporary fixtures, DB/ZIP files, caches and dependency trees are excluded. Public candidates use only exact local-home prefix replacement; raw originals are unchanged.
