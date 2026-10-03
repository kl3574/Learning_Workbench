# Six-migration evidence fixture and the new candidate catalog

Candidate commit: `6e0954add5573bc0d8c84c856712abb6565d5410`, parent `88daa0a23dab0e69f7009b9af670671c45f90924`. Only two integration test files changed; the second file changes only the historical fixture comment. The isolated worktree is clean. No production, migration, root/progress, native, GitHub or Provider operation was changed or executed by this bounded fix.

The existing `01-original-red` was found when this task resumed, then its raw log, receipt and 949 before/after source records were verified without overwriting or repeating it. It is an actual single-case failure, not a collection-order inference: `test_migration_marks_only_old_submissions_legacy_and_recovery_never_rewrites_grades` calls `legacy_storage`, then the real Import worker reaches the new catalog registration and raises `sqlite3.OperationalError: no such table: draft_candidate_identities`. The fixture installed exactly migrations 0001–0006, which intentionally predate the catalog. The original failure log and source snapshots remain intact.

`legacy_storage` already suspends later evidence hooks while producing actual historical rows. It now also suspends only the newly added registration in that same `monkeypatch.context`. The test-only registration hook asserts exactly six installed migrations, absence of the catalog table, and Import ownership; it cannot silently handle current storage. The context exits before actual database upgrade. No missing-table exception is caught or ignored in production.

The existing post-upgrade safe Import case additionally reads every preview candidate through `DraftCandidateRepository.lookup`, asserting Import ownership. Lookup never registers rows, so this verifies that the real producer has resumed registration after the temporary hook ends. All original immutable grade, audit, manual-review, submission-byte, recovery/quarantine, foreign-key and safe-import assertions remain. The independent late-failure test body is unchanged.

| Stage | Actual result | Scope |
| --- | --- | --- |
| 01-original-red | 1 FAIL, 2 deprecation warnings | Original single migration case, original source |
| 02-focused-green | 3 PASS, 2 deprecation warnings | All three specified legacy failure cases |
| 03-related-green | 22 PASS, 2 deprecation warnings | Entire learning_evidence and evidence_independent_review files |
| 04-ruff | PASS | Both changed test files |

Each run records 949 unchanged source files. The RED-to-GREEN source difference is exactly the two test files listed above. The three focused cases are included in the 22-case run; their counts are not additive. No full-suite success is claimed here, and no new mypy execution was needed for this test-only change. `committed-inputs.json` separately binds all final source bytes to actual Git blobs and the successful 22-case input inventory.

Commands, actual timestamps/exits and raw output hashes are recorded under the stage directories. `run.py` and the first RED are preserved; `run_bounded.py` is the successor runner with an outer 240-second process bound. Neither assertions nor product timeouts were weakened. Only explicitly listed text/source/JSON files in `manifest.json` are evidence candidates; private pytest data and dependency caches are excluded.

PRODUCT_DESIGN.md 3.0.7 remains the sole specification, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.
