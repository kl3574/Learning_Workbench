# M6.2 candidate catalog migration — development evidence

Implementation is limited to migrations/0016_draft_candidate_identities.sql and tests/integration/test_draft_candidate_migration.py in m62-active, based on 2cf5caa. Root implements the runtime owner ports and their separate real-owner tests. No existing migration, owner table payload, human review decision or published Content is rewritten by this slice.

Actual runs, retained independently:

- 01-first: 35 PASS in 1.18s, Ruff PASS.
- 02-receipt-boolean-red: 2 FAIL, 38 deselected in 0.15s. Both tests showed malformed JSON Boolean revisions being accepted before explicit type guards. These failures and exact source copies remain unchanged.
- 03-final: 40 PASS in 1.29s, Ruff PASS after integer and embedded plan identity fixes.
- 04-final-typed-identities: 42 PASS in 1.32s, Ruff PASS after explicit text identity guards and two float-revision rollback cases.

Every run has 23 declared source inputs copied and hashed before/after, all unchanged during its own command window. Root was independently editing other files; these are focused development results, not a whole-repository fixed gate. Each receipt records the real argv/time/exit/log SHA. Final pins and independently rechecked raw hashes are in summary.json. The independent reviewer ran no code; both initial SQL findings are statically closed at the final two source hashes.

Tests use real temporary SQLite migrations, FKs, failures, transactional DDL rollback and online backups. Their deliberately structural owner-table fixtures are not complete owner-authenticated generation/import records. A catalog entry cannot stand in for runtime history/permission checks or approval. Root's separate tests cover genuine owner flows.

Raw temporary databases are under private-pytest-* and are private test artifacts. They are not part of any public export allowlist. Logs/receipts/source copies are finite evidence candidates only; this folder has not been presented as a publication-scanned public package. No vendor, production database, browser/native run, system policy modification, remote write, review approval or new HTTP endpoint is part of this task.
