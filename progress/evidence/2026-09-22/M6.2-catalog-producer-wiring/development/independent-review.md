# Independent static review: M6.2 catalog producer wiring and read lookup

Result: no remaining blocking finding in the final seven-file candidate. This is a bounded static review plus read-only verification of already-produced execution receipts. I did not run application code, tests, Provider requests, or database operations, and wrote only this independent cache.

Reviewed worktree: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-catalog-wiring-active`, detached baseline `2ab067b9d832c0aa64699a9a56e879d2ab6c6ac5`. The final seven source files are preserved under `final-inputs/`; `source-final-pins.json` has SHA256 `96f518c2bbb7ccfa160b6c34763e3c8ebec949b1de2e799b515d249143d87997`, independently reproduced from live bytes and equal to the implementer's final manifest. Initial `inputs/` and `source-pins.json` intentionally preserve the intermediate large-revision RED phase; they are not final pins.

## Findings and boundaries

- **Producer transactions:** Import registration occurs immediately after each real Draft insert (`import_worker.py:226-236`) inside the existing preview transaction (`199-263`). Single Authoring registers the checked candidate at `authoring_worker.py:180-181` inside `_finish` (`101-185`); group registers at `authoring_group_worker.py:203-204` inside the transaction that also persists its plan, candidate, terminal Job, and owner summary (`104-208`). The group path covers lesson, practice_set, and assessment. `Database.transaction` rolls back on every escaping exception (`database.py:51-59`). Registration does not add an author-session requirement to learner Import execution. The positive learner Import test is `test_draft_candidate_catalog.py:218`.
- **Conflict rollback and allowed recovery:** Global identity comparison remains keyed by draft ID before comparing workspace, owner, source kind, and entity (`draft_candidate_repository.py:68-90`). The actual Authoring process special-cases `DRAFT_IDENTITY_CONFLICT` by rethrowing (`authoring_worker.py:228-233`, `authoring_group_worker.py:251-256`), so its same invocation cannot catch the conflict and mint a second ID. `test_draft_candidate_catalog.py:244` uses real checked Provider output, controlled UUID allocation, whole-database before/after hashes, and a one-request assertion for both single/group. It separately expires the lease and verifies approved existing recovery can adopt that same checked result using a later candidate ID without another Provider request. This does not establish a permanent failed state after conflict. Import's batch conflict test (`311`) collides on its second member, covers same/cross workspace, and observes full SQL rollback before the existing separate failure transaction. BlobStore filesystem writes remain outside SQL rollback; no filesystem rollback claim is made.
- **Read-only lookup:** `draft_candidates.py:25-43` first checks access, reloads the real active author session, checks Policy again, selects the exact registered workspace/revision, and calls exactly the registered source owner. The returned complete identity must equal the registry identity. `draft_candidate_repository.py:22-60` performs only SELECTs, validates typed inputs and stored linkage, and never probes unrelated owner tables or repairs a missing entry. Tests use `PRAGMA query_only=ON` and all-table hashes for real Import and all four Authoring roots (`test_draft_candidate_catalog.py:64,76`); missing registration, altered hash, wrong owner availability, stale sessions, other workspace, and live assessment restrictions are covered at `102-216`. The repository is a low-level catalog reader; authorization belongs to the application lookup and concrete owners.
- **Owner evidence is still necessary:** Authoring resolvers call `verify_history` (`authoring.py:34-83`, `authoring_group.py:30-75`); existing repositories bind candidate payloads to the owner's raw result, source Job, terminal result, and group plan (`authoring_repository.py:105-121`, `authoring_group_repository.py:109-130,186-205`). Service history verification reads the original checked Provider result. Import resolution verifies its original preview membership, metadata hash, retained source bytes, and block body (`imports.py:65-109`). No owner validation is replaced with a catalog hash, and no network call or numeric execution is added by this lookup. Registry creation/read does not approve private solutions, mathematical correctness, review decisions, or publication.
- **Large revision issue is closed:** The intermediate code could bind a schema-valid integer greater than SQLite int64 and raise OverflowError. Final `draft_candidate_repository.py:35-39` rejects that unrepresentable revision with 412 only after finding an identity in the current workspace. Missing and cross-workspace identities still return 404. Tests at `test_draft_candidate_catalog.py:94-145` cover `2**63`, `10**100`, missing identity, and cross workspace. This leaves the shared core Revision schema unchanged.
- **Historical fixtures and scope:** The old v15 generation fixture explicitly isolates only the newly added register method (`test_draft_candidate_owners.py:311-322`) while retaining real owner/Provider history. Production has no missing-table skip. Both `0001_baseline.sql` and `0016_draft_candidate_identities.sql` match the baseline bytes, as recorded in `support-source-pins.json`; this was not a repeated migration audit. This candidate implements producer registration and an internal lookup port, not the full review/read/decision workflow or full M6.2.

## Execution evidence read, not rerun

For every listed run I compared actual log bytes/SHA256 against its receipt and independently compared all 948 before/after input entries. Each is stable. Copies and the exact comparisons are in `receipts/` and `evidence-audit.json`.

| Receipt | Observed result | Relationship to final candidate |
| --- | --- | --- |
| 07-boundaries-red | 2 failed, 28 passed | Preserves both Authoring collision failures before the rethrow fix |
| 08-conflict-green | 4 passed | Focused Authoring/Import conflict repair evidence |
| 09-owner-focused | 117 passed | Before two repository Literal annotations and the later large-revision code/tests |
| 10-ruff / 11-mypy / 12-mypy-green | Ruff PASS; mypy 2 errors; corrected mypy PASS | Retains the genuine type-check repair sequence |
| 13-import-existing | 5 passed | Existing durable Import/recovery/cancel/rollback/confirmation cases before the large-revision change |
| 14-large-revision-red | 2 failed, 10 passed | Preserves actual OverflowError cases |
| 15-large-revision-green | 12 passed | All seven reviewed final files exactly match the run input manifest |
| 16-ruff-final / 17-mypy-final | PASS / PASS | All seven reviewed final files exactly match the run input manifests |

No full-suite, unified-root gate, vendor-service, or CI claim follows from these focused local results. Root owns integration and final gates. No additional test execution is requested by this static review.

## Final seven-file SHA256 pins

- `services/api/app/application/authoring_worker.py`: `6cbc0034fa28b2b7994efb9c7293b7364f5fad876b127fe0f0330fa4309f4841`
- `services/api/app/application/authoring_group_worker.py`: `1841d98f4aef29b3ae0336ae6f43cb5831f7dc6dadf4a841b2e9dafc391f578f`
- `services/api/app/application/draft_candidates.py`: `74c54125fd06b3794575f242abff18455a008cc9ac8473bf149d6386db27bb37`
- `services/api/app/infrastructure/draft_candidate_repository.py`: `61dd14193afb03c3ba7e564577724a07aa4bcaaab25bbe5219b15a8b0cf9db21`
- `services/api/app/infrastructure/import_worker.py`: `bb2ccd35b2d67ba99f6642f7f1d958d34595f4d09b3315bbbfc9df817099876e`
- `tests/integration/test_draft_candidate_catalog.py`: `a7a704f5037e77f82498997d88625a0401c042bb4e517b2aa560e497fcfbd728`
- `tests/integration/test_draft_candidate_owners.py`: `9d77a7304757e34327532d2c20e85ea584b24a4beee4fcb1a74007ac6209fa5c`
