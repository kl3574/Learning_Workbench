# M6.2 saved edit review and publication UI

This slice implements R-21/R-24/R-25/R-26/R-27/R-38 against the approved
PRODUCT_DESIGN.md v3.0.9, SHA-256
`a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98`,
starting from `1ad328d`. It does not establish completion of M6.2.

Reader explicitly admits an independently read, exact saved EditDraftSnapshot
to Review. A dirty local buffer, unresolved command or conflict cannot become
the review candidate. Edit publication uses its own strict basis and IndexedDB
command journal. The basis binds the full original block metadata and body,
saved candidate, selected human review, warnings, and predicted base+1 reference.
Import publication keeps its existing separate basis and journal.

Original publication commands and ACKs remain distinct from explicit GET current
results. Failed local writes retain the original command or received receipt in
isolated page memory, including the shared Review command path. Current authority
is required to display or save protected records; the original session must match
before saving retained memory. This save never sends HTTP or changes command
origin. Old pages and access generations remain read-only; no cross-session
command continuation contract is introduced. Unsaved command memory prevents
closing, with an explicit discard option. Existing temporary review forms retain
their prior explicit-close and Policy-clear behavior.

## Verified

- Full web tests: **581 passed**, 96 files (`full-web-02`).
- Focused edit/review/Import publication tests: **92 passed** (`unit-04`).
- Typecheck and production build: **PASS** (`types-final-01`, `build-final-01`).
  The build retains the large-chunk advisory; no bundle-size acceptance is claimed.
- Four real native regressions: **4 passed** (`native-04`): existing editor,
  Import publication, Review recovery, and the new edit publication path.
- The new native path uses actual SQLite, HTTP and IndexedDB: native editing,
  machine review, explicit synthetic human decisions, base+1 publication, lost
  ACK and same-key replay, actual IDB transaction abort while saving that ACK,
  role revocation and Reader unmount, hidden protected payload and close guard,
  same-session memory save without HTTP, independent current read, unchanged
  old Lesson pin, and browser/API restart readback. Screenshots at 390 and 1440
  pixels were inspected; geometry assertions pass.

The first full web run was **580 passed / 1 failed**: an unchanged
ProviderSettings test timed out waiting for the secret retry button. Its isolated
run passed all 7 tests; the exact full command then passed without a code change
to that area. The initial failure is retained, and its timing cause is not claimed
fixed. A first native launch also correctly refused the wrong Node version;
subsequent runs used the existing pinned Node 24.21.0 toolchain.

Private evidence retains raw logs, command/exit-code records, before/after source
manifests, changed source copies, native actual receipts, screenshots and failure
originals. The changed-source manifest SHA-256 is
`611a0abee776e8d515445cb3843260d888a097a317e8af0587ae3d5db43881b1`;
the private evidence index SHA-256 is
`05185538f64b62d36cbc584c7cd492f1055b2febdc0ea5bcd6ee666ebd841ce9`.
Raw private paths and runtime profiles are not published in this receipt.

## Remaining boundaries

The existing editor still uses a textarea. The specification's CodeMirror 6
source-editor requirement remains an explicit M6.2 gap for a subsequent slice.
No provider, paid call, real content-quality approval, mathematical correctness,
source-rights acceptance or independent teaching acceptance was performed.
Synthetic author decisions verify software behavior only. No backend schema,
generated contract, product specification, progress or remote state was changed.
