# M6.2 numeric review observations — bounded implementation

Sole authority: PRODUCT_DESIGN.md 3.0.7, SHA256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d. Isolated baseline e100f1b2ce02ccd0af85e2596b53ba2a24da9cda. Eight scoped implementation/test files (including the subsequently authorized Jobs owner port); the six preceding material-reader files are unchanged. This slice adds internal read-only observation and historical verification; no HTTP/UI/review Job/decision/publication eligibility or new numeric execution path.

`NumericService` and `GroupNumericService` expose `read_review_numeric(connection, identity, candidate) -> ReviewNumericObservation` and `verify_review_numeric(connection, identity, observation) -> None`. `ReviewNumeric` routes the corresponding draft-id/revision interface through the actual candidate catalog/owner. Each call requires the caller transaction, reloads current author session and Policy, and reuses the actual full material owner reader: exact candidate, complete group/private hash, source material and original checked Provider history are revalidated.

Observations preserve all actual checks in the existing repository's SQLite rowid insertion order (bounded by its 100-check quota). Each check retains its original approval record, complete plan/runtime manifest and profile, original preview/decision/cancel command prefix, exact Job snapshot and input, Job event prefix, admitted/actual-start facts, terminal result and complete preserved stdout/stderr bytes. For generated questions the private plan is obtained by the actual numeric owner from its exact question member; complete candidate and original candidate-record SHA bind all original private solution bytes. Human review obtains full private content through the separate material port. No newest/preferred/PASS check is selected.

Import explicitly returns `coverage=no_numeric_owner_pipeline` and no execution observations after real catalog/Import lookup. This is a fact about the existing owner, not a declaration that the material has no mathematical or numerical obligations.

Historical verification checks the original explicit check revision, command prefix and Job revision/events against actual durable history. A subsequent legitimate preview, decision, Job transition, cancellation or appended actual-start field does not replace the frozen old facts. `expired` is evaluated at the original observed_at. Existing caller SQLite snapshots can predate another connection's commit despite a later wall-clock observation timestamp; the implementation therefore does not reconstruct snapshot membership from timestamps. A real WAL snapshot/second-writer test and same-created_at append test exercise these boundaries.

The descriptor hashes all returned observation bytes but is not proof of occurrence. A later real Review owner must persist and authenticate the exact descriptor/observation as part of its own history before accepting it as old review evidence. This internal verifier does not authenticate arbitrary caller-rehashed JSON as having been observed in the past. GET does not register, repair, preview, approve, prepare/check a runtime, start an executor or modify any table.

## Actual verification

| Stage | Actual result | Scope |
| --- | --- | --- |
| 01-owner-red | 1 FAIL | Real generation and two previews succeed; missing new read method gives actual RED. |
| 02-owner-green | 2 PASS | Single/group actual owner read/verify in query-only caller transaction, second connection/runtime methods prohibited. |
| 03-history-boundaries | 1 FAIL, 28 PASS | New test compared two distinct member-ref model classes directly. Complete fields matched; no product failure was hidden. |
| 04-static-ruff | PASS | Six product files and then-current test. |
| 05-static-mypy | PASS | Initial six product files, before the later Jobs owner boundary fix. |
| 06-complete-history-green | 37 PASS, 41.38 s | Corrected complete-ref comparison plus real concurrent snapshot, current Policy and missing-owner boundaries. |
| 07-related-numeric-regressions | 56 PASS, 104.70 s | Existing single/group numeric services/workers and Provider history tests. |
| 08-final-ruff | PASS | Initial seven source files, before the later Jobs owner boundary fix. |
| 09-jobs-owner-prefix-green | 39 PASS, 43.71 s | New Jobs-owned event-prefix port and two explicit synthetic ledger callback/nonempty output cases. |
| 10-owner-history-regressions | 26 PASS, 1 deselected, 27.82 s | Affected worker/history cases; the real sandbox gate already ran in 07 and is explicitly deselected here. |
| 11-owner-final-ruff | PASS | All eight final source files. |
| 12-owner-final-mypy | PASS | All seven final product files. |

Stage 01 has 952 declared non-progress source files. Stages 02–12 have 954, including the three new untracked files with null Git identities. Every run has its original UTC start/end, exit, command, log SHA/bytes, runner, scoped source snapshots and matching before/after source inventory. Different stages are not asserted to share the same source version. The new tests use real SQLite/controlled loopback generation and ledger-only numeric fixtures. Recovery observes the actual committed permission and records BLOCKED/outcome_unknown without executing the plan.

The existing 07 runtime regression separately exercises the real sandbox gate and requires the original exact environment failure: bwrap RTM_NEWADDR denied, environment_unavailable/BLOCKED, no numerical assertions and no ordinary-process fallback. Its test PASS proves correct preservation of BLOCKED, not arithmetic success. No hosted vendor or user key was accessed. Existing synthetic published targets are fixture setup, not publication of generated drafts.

All original failures are retained. Temporary databases, secrets/session stores and runtime caches remain private fixture directories and are not selected for evidence publication. Original selected logs are private and must receive explicit field-based sanitation if later published.

Independent static review identified direct job_events access in the first implementation. Root authorized the necessary eighth file: AuthoringJobRepository now exposes a typed event_prefix in the same caller transaction, verifies complete owned history and the exact revision, and returns the frozen event prefix. The numeric facade no longer queries Jobs tables. Two added tests explicitly inject synthetic ledger callbacks and BLOCKED output facts through the actual owner/worker, without executing a numeric process; they prove old-observation preservation and exact nonempty stdout/stderr readback, not physical execution. Original 37-case and 56-case receipts are preserved as earlier-stage evidence; final 39-case results are not added to them as distinct coverage.

Independent static review is recorded separately. The final independent review found no remaining definite blocker after that fix and rechecked the completed 09/10/11/12 receipts, log hashes, 954 before/after source entries and eight final source snapshots. Final commit/source bindings are recorded separately; no tests were rerun by the reviewer. Full M6.2 review workflow, approval, numeric result selection for publication, mathematical/source/pedagogical checks and hosted-provider acceptance remain outside this slice.
