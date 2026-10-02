# M6.2 Content impact decisions evidence

This receipt covers the Content impact read and per-object decision HTTP slice of
PRODUCT_DESIGN.md v3.0.9 §20.11. The specification SHA-256 is
`a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98`.
The implementation starts at `b8619a9`; shared checked snapshot and artifact
owner ports are committed separately in `71c4d30`. `source-manifest.json` pins
the exact implementation and tests exercised by the captured commands.

Implemented routes are `GET /api/v1/content/impacts/{event_id}` and
`POST /api/v1/content/impacts/{event_id}/decisions`. Migration 0022 adds only
Content-owned decision history and heads. The implementation validates frozen
event snapshots, full current references, actual artifact bytes, original
command identity, CAS revisions, receipt hashes, and contiguous immutable
history. Reports are SQLite query-only transactions, and decision transactions
write only Content decision rows. Exact, ID-only candidate, and legacy states
remain distinct. Policy checks run before reads and original receipt replay.

## PASS

- Captured final focused suite: **87 passed in 20.33s**. This includes strict
  transport/schema validation, zero-write failures and reads, concurrent CAS,
  corrections, original receipt replay, actual artifact byte corruption,
  owner boundaries, policy changes, history corruption, rollback, pagination,
  and migration preservation. See `focused.log` and `focused.xml`.
- The focused suite starts a real loopback uvicorn HTTP server, sends actual
  HTTP GET/POST requests, restarts the server, and checks byte-identical replay.
  Its JUnit properties record actual event snapshot, request, and receipt
  SHA-256 values. Fixtures and author decisions are synthetic; no provider is
  called.
- Ruff over the API and changed tests: **All checks passed** (`lint.log`).
- Full API mypy: **no issues found in 215 source files** (`types.log`).
- Earlier broader regression: **168 passed in 82.91s**, covering artifact
  owners, Review HTTP, Content repository, edit publication HTTP, draft edit
  reads, and Content decisions HTTP. This preceded the final SQL protection
  against replacing an immutable receipt; the final focused suite includes
  that protection and its direct database regression. This earlier result is
  a tool transcript result, not an additional archived raw log.

`commands.json` records command arguments, exit codes, UTC capture time, and
SHA-256 values of the captured logs. Commands used the repository's existing
Python environment; no package installation or external service was needed.

## NOT_RUN in this slice

Browser UI acceptance, central generation of the combined route catalog,
the final combined branch gate, and other M6.2 modules are outside this slice.
No live model, source verification, mathematical correctness, or pedagogical
quality acceptance was performed. A valid author decision receipt records
the explicit author action; these tests do not establish the truth of that
decision or completion of the whole M6.2 milestone.
