# Owner-backed review material port

Sole authority: PRODUCT_DESIGN.md 3.0.7, SHA256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d. Isolated implementation based on 75b0ca5f83d809816b338c2d70cc5bfb9f1a3f83; six permitted files only. This is an internal read-only material port, not a human review decision, publication, new HTTP endpoint, numeric execution, or completed M6.2.

`DraftCandidates.read_review_material(connection, identity, draft_id, expected_revision)` selects the exact registered owner and returns `CheckedReviewMaterial`. It requires the caller's existing transaction, reloads the current author session and Policy, and never repairs missing catalog identities. Each actual Import/single/group owner supplies its complete original material. Generated material verifies the original candidate, Job/command history and complete checked Provider artifact, then revalidates exact Content sources and group targets. No current-pointer substitution or implicit source expansion is used.

Import material contains its typed public payload (including full block body/citations), original input/source identity and warnings; private solutions are explicitly excluded because the existing Import candidate hash does not bind them. Single material contains the complete original candidate record, original input and complete prepared context. Group material additionally includes the actual persisted content plan and complete root, ordered members and private solutions. The descriptor hashes all these frozen fields; mutable Draft state and current numeric check IDs are absent. A later real numeric preview leaves the generated descriptor unchanged.

The tests use actual SQLite producers, a synthetic loopback Provider, real checked dispatch receipts/artifacts and controlled fixture corruption. They do not call a hosted vendor, execute numeric code, approve academic content or publish generated drafts. Existing published synthetic targets are test setup only. Query-only transactions, a prohibited second database connection, connection total_changes and all-table hashes establish read-only behavior. Positive generation covers single worked example and lesson/practice_set/assessment groups; it is not a quality or exhaustive content matrix.

## Actual runs (original names and failures retained)

| Stage | Actual result | Meaning |
| --- | --- | --- |
| 01-import-red | 1 FAIL | New real Import read test reaches missing material port, after real producer/lookup. |
| 02-import-green | 1 FAIL | Name is historical: new test incorrectly expected whole document instead of the selected heading block. |
| 03-owner-boundaries | 8 FAIL, 21 PASS | New test used `.solution` instead of `.payload` and `.create` instead of `.create_attempt`. |
| 04-static-ruff | PASS | Initial five product files and new test. |
| 05-static-mypy | PASS | Initial five product files. |
| 06-complete-owner-boundaries | 7 FAIL, 32 PASS | New fixture's ImportWorker module, invalid model_copy construction/equality, and expected status differed from existing owner contract. Failures preserved; production denial was not relaxed. |
| 07-repr-red | 3 FAIL, 3 PASS | Actual ValidationError input disclosure. Repr assertion's newline handling was inadequate; this run does not prove repr safety. |
| 08-repr-red-corrected | 4 FAIL, 2 PASS | Corrected unique line assertion additionally reproduces Import repr disclosure. |
| 09-material-green | 2 FAIL, 43 PASS | All six privacy tests PASS after using existing AuthoringModel; two new source tests compared distinct DTO classes instead of all exact fields. |
| 10-related-regressions | 106 PASS | Existing catalog/owner/Import HTTP/single and group context tests, 69.32 s. |
| 11-final-ruff | PASS | Product and then-current new test. |
| 12-final-mypy | PASS | Final five product files, unchanged thereafter. |
| 13-final-material-green | 45 PASS | Final new file, 36.86 s. Complete reference fields and order checked; missing body paths reached. |
| 14-final-test-ruff | PASS | All six final files. |

Every run has original command, start/end UTC, exit code, log SHA/bytes, scoped source snapshots, runner and before/after source inventories. Stage 01 has 950 declared non-progress source files; later stages have 951, including both new untracked files with null Git identity. Every individual run's before/after inventory is equal. The stages are different source versions; they are not asserted equal to each other. The 106 old regressions predate only the final test assertion correction; their five product files match the final product bytes. All original failing logs remain private, including synthetic temporary session representations. No blanket cache copy or public upload is authorized by this report.

Independent review identified the repr/error disclosure and found no other definite blocking issue in its bounded static owner/transaction/history review. Its original pins and final addendum live in the separate `m62-review-material-independent-review-v1` cache. Final commit/source bindings are recorded separately; test-time null Git identities are not retroactively rewritten.

Remaining boundaries: no review Job/receipt/decision lifecycle, HTTP/UI wiring, human approval, publication or numeric execution is implemented here. Import private solutions require their own future immutable review scope. Mathematical, source-truth, pedagogical, hosted-provider and full M6.2 acceptance remain unproved. No main/progress/spec/core/migration or remote changes were made by this slice.
