# Legacy Review backup test contract repair

Base `bd3b9375b41cf9a726260e7497a7302f11c3db04`; test-only fixed `b51de327fe74cdc476a52e061fe2e044072d2267`. Only `tests/integration/test_review_storage_migration.py` changes, in the one legacy backup test. No production, migration, specification, timeout, or other test changes.

The prior test expected the reviewer foreign key to be nulled and all sessions deleted. Existing Session-owned backup sanitation preserves historical actor identity/references, replaces both authentication hashes, revokes the actor, and clears transient bootstrap/idempotency records. The revised test checks exact receipt UTF-8 BLOB bytes and the full original Review row, original actor ID/workspace/role/expiry, exact disabled authentication sentinels distinct from original hashes, revocation, cleared transient records, empty new review-history tables, integrity/FK checks, and unchanged complete logical source database dump. The SQL legacy fixture does not establish authentication or actual human approval.

| Stage | Actual result | Fixed source |
| --- | --- | --- |
| 01 original exact single test | 1 FAIL at old reviewer-null assertion; exit 1 | bd3b |
| 02 first revised invocation | NOT_RUN: caller supplied incorrect full commit argument; runner rejected before pytest launch | no product execution |
| 03 revised single test | 1 PASS; exit 0 | b51de327 |
| 04 seven relevant backup/migration files | 65 PASS, 2 existing dependency warnings, 18.86 seconds; exit 0 | b51de327 |
| 05 changed-file Ruff | PASS; exit 0 | b51de327 |

The 65-test regression includes the revised test; the separate single PASS is a repeated validation, not an additional unique case. Every executed stage binds all 1381 tracked nonprogress engineering inputs to exact Git blob bytes and unchanged before/after manifests. Progress and ignored installed dependencies/caches/runtime files are excluded; private runner SHA is included. Source tree is clean.

Original complete Python gate remains FAIL at dcfda8c270dff3e6db75011c50ffa7d6f5826512: 3683 PASS, 1 FAIL, 2 ERROR, 2 environment SKIP, exit 1. Its sealed report and artifacts are unchanged. This narrow correction does not close the two setup errors or supersede full-gate acceptance. Original UTC duration 6906.8653 seconds versus monotonic 2250.136 seconds remains preserved without a cause claim. A complete integrated rerun is required to alter acceptance.

Explicit share candidates contain only listed evidence, source copies, and logs. No database, backup ZIP, authentication material, pytest cache, or basetemp is eligible. Only exact local-home prefix replacement is applied.
