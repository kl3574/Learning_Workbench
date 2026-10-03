# Existing text concept retention — backend slice

Fixed source `617fb0045383c868e07cdf9a76428b4214cbd4fa`, parent `7a6a8a2a0cc4dca86abd437bd7cd532423a48167`; isolated worktree `m62-text-concept-retention-oct03`, clean. Sole PRODUCT_DESIGN v3.0.13 SHA256 remains `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`. This is a new separately tested slice, not covered by root's earlier complete gates.

The three production changes admit existing public text with original concepts through the existing internal `draft-base-material-dependencies-v2`. It already holds the full root/descendant exact edge witness; either concepts or depends_on now requires it. Old no-reference V1 gets no new fields/defaults, and a concept-bearing V1 or a V2 missing its witness fails closed. The candidate payload and Review bind the full base hash without extending any external DTO. Content verifies the frozen witness in the publication transaction, passes the original root concept pins into its existing closure, then verifies the published witness with only the edited root advanced. Metadata arrays keep their original order. Only title/body are editable; other kinds/null bases remain closed. No schema/spec/migration/generated files changed.

## Fixed validation

| Evidence | Actual result / scope |
|---|---|
| `12-fixed-backend-related.log`, `fixed-backend-gate.json` | 280 PASS, 2 existing FastAPI/Starlette deprecation warnings, 269.80s, exit 0. Exact 20-file command is recorded. Includes 16 new concept HTTP/owner tests, 7 original V1 and 5 original V2 representation tests, existing Edit create/read/Review/publication/integrity/migrations, Content repository/HTTP and Restore HTTP. These subsets are included in 280, not additional passes. |
| `13-fixed-ruff.log` | Six changed Python files, PASS. |
| `14-fixed-mypy.log` | Full services/api scope, 236 source files, PASS. |
| `fixed-backend-inputs-before.json` / `after.json` | 1318 complete git-tracked non-progress files unchanged across the fixed gate; only progress/ and ignored tools/runtime/test state excluded. This differs from earlier limited 1063/1064 inventories and the independent capture's 16013 tracked files including progress. |

The fixed run uses only synthetic, new private test databases. Runtime state/cache directories are excluded from deliverables. No existing user database, credentials, environment secrets, external model or network provider was inspected or used. Synthetic human decisions establish protocol behavior, not mathematical/source/teaching approval.

## Failure history retained

`01-base-rejection-red.log` is the unmodified 7a backend refusing a valid concept-bearing text at actual HTTP create (409 DRAFT_EDIT_SCOPE_UNSUPPORTED). Its test and production source snapshots are retained. `02-pin-current-red.log` is the explicitly intermediate, unaccepted V2 admission without original root pin propagation: after concept current advanced, publishing returned 409 CONTENT_HASH_MISMATCH, correctly refusing the attempted latest-pin reinterpretation. Adding original pin propagation closes that tracer. It is not evidence that the baseline ever published a wrong pin.

The first `03-original-pins-green.log` filename reflects intended validation but actually records FAIL: the new read-only owner probe omitted its required BEGIN. Test harness corrected, `04` is 1 PASS. `05` records 7 FAIL/5 PASS because new assertions expected 409 where the existing Draft owner intentionally returns 503 DRAFT_EDIT_INTEGRITY; product error semantics were not changed. `07` asserts the precise existing status/code pairs and is 12 PASS. `09` extends the matrix to 16 PASS. `08` is 12 old-oracle representation PASS. Original logs and source snapshots were not overwritten; none of those intermediate results substitutes for the fixed 280 gate.

## Integrity / compatibility boundaries

| Condition | Verified behavior |
|---|---|
| Root concepts alone; root concepts plus ordered depends_on; concept/prerequisite current advances to r2 | Real HTTP create/PATCH/GET/new Review/synthetic human/publish succeeds; old IDs/order, root and descendant exact r1 pins survive; title/body and actual r2 readback exact. |
| Frozen original root pin, descendant concept pin, dependency-block concept pin, or concept metadata corrupted | Draft GET, original create/PATCH ACKs, old/new Review and new publish/original publication ACK refuse; all table hashes unchanged. Existing errors are explicit 409 CONTENT_HASH_MISMATCH or 503 DRAFT_EDIT_INTEGRITY, not generic success. |
| Only the newly published root pin corrupted | Published draft GET and original publication ACK refuse. Earlier draft r1 GET, create/PATCH ACK and original candidate Review remain byte-identical because they bind intact earlier facts. |
| New root concept edge removed inside publication transaction | Whole publication rolls back, including current and owner facts; dropping the synthetic fault and retrying the original key succeeds once. |
| Changed current base / learner role / attempted concepts/depends_on/body_path/kind PATCH | 412 exact-base CAS / 403 current-role rejection / 422 immutable-field rejection. Original candidate remains, no automatic rebase or field editing. Existing Policy tests are also in the 280 run. |
| Old no-concepts V1 and V2 | Existing 316 V1 fixtures unchanged. The scope agent independently captured actual 7a V2 rows and HTTP replay bodies; all 12 approved raw files were copied byte-for-byte and hash-checked. New-code tests preserve canonical record/command/publication bytes, base/candidate hashes and rendered original ACK bodies. |

The V2 independent capture report and hashes remain in `legacy-v2-capture/`; its actual old-code replay had unchanged full table hashes. The cross-version oracle in this slice parses/canonicalizes and renders those original bytes; it does **not** claim reopening the original captured database with new code. Separate integration tests exercise new-code real HTTP replays. The external record version remains `draft-edit-record-v1`; only the existing base discriminant is V2, with no new format version.

Freeze-time onward is the integrity guarantee. This slice cannot identify an arbitrary self-consistent bare concept-pin replacement made before the original freeze, nor coordinated replacement of all authoritative bytes. It performs no repair of damaged stored edges.

At this backend commit the old browser guards still reject concepts. UI support and actual native acceptance are separately assigned and must be integrated/tested before claiming the user-facing vertical slice complete. This report does not claim native, full Python, full Web, remote CI, release, numeric execution or academic acceptance for 617.
