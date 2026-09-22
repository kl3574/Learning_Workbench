# 0024: Quality review history in the caller transaction

Status: internal persistence slice; not the M6.2 application acceptance.

PRODUCT_DESIGN.md 3.0.7 §7, §15, §20.1, §20.3 and Appendix A require exact
candidate binding, unchanged historical content and explicit human decisions.
Migration 0017 supplies append-only storage. This adapter composes the checked
Jobs adapter and candidate catalog; it does not inherit an unrelated owner or
write Jobs SQL. The shared 54 core models and existing migrations are unchanged.

`ReviewRepository(connection, workspace_id)` requires an active caller
transaction on every read/write. `bind` retains the actual initial review Job,
its complete typed input and original create command. `load` returns a named
pending state with no receipt, or a complete machine-first history and current
receipt. `binding` includes the same full verification. `append_machine`,
`append_decision` and `record_cancel` append their exact records/commands.
`replay(actor, route, key, body)` checks the entire stored history before returning
the original command and ACK, not the latest projection.

The revision domains remain distinct: create has a candidate revision basis
and original queued Job ACK; decisions have adjacent review revisions; cancel
has historical Job revisions and the Jobs-owned cancel/no-op semantics.
Machine records retain complete owner material, frozen numeric observations,
the deterministic structural report and original artifact binding. Reads
recompute the structural report using the original requested checks, verify the
exact completed Job result, all canonical bytes/hashes, each adjacent revision,
all commands/attachments and the current projection. An intact latest row does
not excuse a damaged earlier record. Numeric observations remain frozen; later
numeric history does not rewrite them.

Machine mathematical/sources/independent-pedagogy results remain NOT_RUN.
Human decisions retain the original structural result and NOT_RUN independent
pedagogy; each new receipt references the original machine report followed by
that decision's attachments in requested order. Earlier attachments remain in
their original immutable revision. A human actor identifier and typed input
are historical data, not proof of current authorization or human review.

Each repository write uses its own savepoint, including final full readback.
If the caller catches an error and commits, this method leaves no partial
Quality mutation. It does not undo Jobs/artifact work the caller performed
before entering the method. The future application must wrap the entire
Jobs + Quality operation in its outer transaction/savepoint, recheck current
author/Policy and candidate/material/numeric owners, and authenticate physical
artifact bytes/manifests/profile/access through the artifact owner port.
Persistence verifies the exact artifact row/blob/manifest association only;
neither valid JSON nor SQL foreign keys grant artifact ownership/access.

Existing reviews with no audit binding remain byte-preserved and explicitly
unverifiable; no Job/history/approval is backfilled. Sanitized backup copies may
set the current projection's reviewer_session_id to NULL while retaining opaque
historical actor IDs and complete original receipt bytes. New decisions still
use the existing session foreign key on the current projection.

Closed internal models suppress repr and ValidationError input text. Protected
revalidation and machine-result construction reject serializer warnings as
fixed safe errors, including malformed model_construct/model_copy values.

Tests use disposable real SQLite databases and explicitly synthetic intent,
including real controlled-loopback producer fixtures for generated candidates.
No vendor, numeric subprocess, HTTP review handler, review worker, publication,
independent pedagogy approval or real human content approval is implemented or
claimed by this slice. Original failures and exact fixed-source test receipts
are retained separately from the final passing gates.
