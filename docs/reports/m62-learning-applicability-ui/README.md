# M6.2 Learning evidence applicability UI

This bounded slice implements the approved PRODUCT_DESIGN.md §20.11 Learning
applicability read/decision flow, starting from backend/contract baseline
`8fb64dc1f7d91628692123d70e232f807922110f`. It does not establish completion of M6.2.

The ConceptStates source entry uses an actual original evidence ID. Current
applicability is explicitly read; only returned relevant event IDs can select a
filtered event decision head. A second explicit action freezes the exact original
evidence/pins, current basis and event head for a human usable/confirmed_stale
decision with a reason and optional authorized artifact IDs. Reads and pagination
do not replace the frozen basis. A 412 retains the original request and requires
an explicit current read and adoption before a new correction command.

Strict generated DTO validation and pin/body/receipt checks separate current GET
results from historical ACKs. Original commands are committed to their own
IndexedDB journal before HTTP. Unknown results keep the original body/key; replay
requires an explicit action, current authority, original page/access and the
original session binding retained only in page memory. Received ACKs or rejection
records survive IDB failure and panel unmount in isolated memory. Saving that
memory never sends HTTP or updates origin. Browser/panel close protection and an
explicit path to role controls preserve this recovery path. No CSRF, cookie or
session credential is persisted in this journal.

The approved v3.0.10 cross-page edit-command contract does not expand Learning
journal replay in this slice. Old page/access originals remain read-only.
Integrating the new SessionResponse generated contract is a separate combined
verification step; this branch uses its fixed backend baseline without modifying
security DTOs or generated files.

## Executed verification

- Focused applicability and existing Learning tests: **32 PASS** (`focused-03`).
- Entire web suite: **578 PASS**, 95 files (`full-web-02`).
- Typecheck, no-unused-symbol check and production build: **PASS**
  (`types-03`, `lint-02`, `build-02`). The existing large-chunk advisory remains.
- Native actual SQLite/HTTP/IndexedDB test: **1 PASS** (`native-08`), covering
  original imported questions, actual submission and explicit synthetic human
  regrade, two real Content owner publication events, exact and ID-only relevance,
  competing old-head commands in separate browser contexts, lost ACK, identical
  key/body replay, actual ACK-save IDB transaction abort, role revocation and
  panel unmount, hidden payload and close guard, original-session memory-only
  save, explicit correction, multi-event usability, browser/API restart, and
  active independent-assessment Policy hide/HTTP409 followed by abandonment.
- Actual receipt readback: **PASS** (`native-receipt-readback`), including both
  relation classifications and unchanged original evidence, grade/private-answer
  tables and original reference bindings. Usable never upgrades the original
  unreviewed evidence's eligibility. Layout assertions passed at 390 and 1440px;
  the 390px capture was inspected, not a complete accessibility audit.

Earlier native failures remain in private evidence: an incorrect test route
waiter, hidden-details locator, ambiguous select label (fixed with an explicit
accessible name), a socket failure in the first shared-journal competition
harness, and a premature assertion on the transient memory guard before the real
HTTP ACK. The competition test now uses independent browser contexts and waits
for the actual replay response. The socket failure's precise original transport
cause is not claimed diagnosed. Native 06, 07 and final 08 passed progressively
expanded coverage. These failures are not erased by the later PASS results.

No backend implementation, schema, migration, generated contract, product spec,
progress record or remote state was changed. Test-only Content publication uses
the real owner service to create original synthetic revisions; it is not a
production Concept editor. Private-answer content is not added to the UI or its
journal; Learning verifies those private pins server-side.

Private evidence retains raw command/exit records, failed runs, original actual
receipts, screenshots and source before/after hashes. Runtime credentials from
failed browser diagnostics remain private. Real mathematical/source-rights,
independent teaching, provider/paid-call/Codex quality and final root integration
are **NOT_RUN** here. All human decisions in these tests are original synthetic
software acceptance judgments.
