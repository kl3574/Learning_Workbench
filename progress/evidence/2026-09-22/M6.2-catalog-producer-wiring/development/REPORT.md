# M6.2 candidate catalog producer wiring — bounded development evidence

Base: `2ab067b9d832c0aa64699a9a56e879d2ab6c6ac5`, detached worktree `m62-catalog-wiring-active`. Only five production files and two integration test files change. PRODUCT_DESIGN 3.0.7, AGENTS, migrations 0001/0016 and progress are unchanged. This slice adds no review approval, HTTP route, Provider call, content publication or migration repair.

## Delivered behavior

- Import complete_preview registers every actual validated candidate in the same SQLite transaction as the original draft rows, complete preview and awaiting_approval transition. Learner Import remains supported. The catalog is an identity fact, not author permission or approval; imported question identity still covers public metadata only, while the owner rechecks the private preview/source history.
- Single Authoring and all three group roots register the actual immutable candidate after original candidate storage and before the terminal Job/owner record write, in that same transaction. Group identity retains its original full payload/private-solution hash; no bytes or statuses are rewritten to imply review.
- `DraftCandidates.lookup(connection, identity, draft_id, expected_revision) -> ResolvedDraftCandidate` checks current Policy and reloads the actual active author session, locates the exact workspace/revision catalog identity, selects only the registered source_kind and delegates to that complete real owner. Missing registrations stay missing. Lookups do not call register/admit, initialize or repair. A real `PRAGMA query_only=ON` connection succeeds for all five producer cases, with every table hash unchanged.
- Lookup rejects bool/float/string/nonpositive revisions and invalid IDs with 422 SCHEMA_INVALID; missing or other-workspace identities return 404 DRAFT_CANDIDATE_UNREGISTERED; absent exact revision returns 412 DRAFT_REVISION_MISMATCH. An unavailable configured owner yields 503 DRAFT_OWNER_UNAVAILABLE. Catalog shape/linkage or mismatched owner identity yields 503 DRAFT_OWNER_INTEGRITY; the real owner's original integrity/permission errors remain visible.

## Conflict and recovery boundaries

Two actual Authoring process REDs proved the original generic ApiError fallback would roll back a conflicting candidate and immediately call finish again with another UUID. Both workers now propagate DRAFT_IDENTITY_CONFLICT, leaving that attempt's candidate/catalog/plan/Job-terminal writes rolled back. This is not a permanent terminal state: the existing expired-lease recovery can later adopt the same checked Provider result under a newly allocated identity. Tests exercise that later recovery, retain the conflicting existing catalog unchanged and observe exactly one total loopback Provider request.

Import's whole preview batch rolls back when its second candidate conflicts, including the first candidate and all SQLite blob references/metadata/Job writes. Its existing separate failure transaction is preserved and can honestly mark the import failed. Existing content-addressed blob files written before the SQLite failure are not claimed to be filesystem-transactional or deleted here.

The v15 upgrade tests explicitly suppress only the newly added registration hook while generating historical v15 records; their checked Provider history and original owner writes remain real. Production code never skips registration because a table is absent. Separate historical fixtures remove catalog rows under explicit test-only trigger removal to verify missing-catalog lookup does not repair and admitted writes still roll back with their caller.

## Actual validation

Each command has its original output.log, receipt, complete 948 non-progress input hashes before/after and bounded production/test source copies. Every run's inputs were stable. All historical failures are retained:

| Stage | Actual result |
|---|---|
| 01 Import tracer RED | 1 FAIL, catalog missing |
| 02 Import tracer GREEN | 1 PASS |
| 03 Authoring tracer RED | 4 FAIL, single + three group catalogs missing |
| 04 Authoring tracer GREEN | 5 PASS |
| 05 lookup RED | 1 FAIL, port absent |
| 06 lookup GREEN | 1 PASS |
| 07 boundaries RED | 28 PASS / 2 FAIL, both Authoring conflict fallbacks |
| 08 conflict GREEN | 4 PASS |
| 09 candidate catalog + original owners + migration | 117 PASS, 2 existing deprecation warnings, 57.83 s |
| 10 Ruff | 7 selected files PASS |
| 11 mypy | 2 errors: missing local Literal variable annotations |
| 12 mypy | 5 selected production files PASS |
| 13 existing Import stage/confirmation/cancel/recovery/rollback | 5 PASS, 29 deselected, 2.03 s |
| 14 large revision RED | 2 FAIL / 10 PASS: SQLite integer binding overflow |
| 15 large revision GREEN | 12 PASS, 27 deselected, 2 existing warnings, 5.49 s |
| 16 final Ruff | 7 selected files PASS |
| 17 final mypy | 5 selected production files PASS |

The 117-case run preceded two local variable type-annotation additions, then a narrowly tested large-revision boundary fix. After the workspace-scoped identity lookup succeeds, valid positive revisions above SQLite int64 maximum return the existing 412 instead of overflowing a parameter binding. Missing/other-workspace identities still return 404. This changes no core Revision constraint. `post-owner-focused.diff` records the exact two-file delta after the 117-case run; stages 15–17 exercise the final source. No claim is made that the 117 cases or full gates were rerun on that final source or a later commit. Root owns later fixed full gates.

No real vendor, numeric process, browser, system policy change or API key was used. Real controlled loopback protocol fixtures have synthetic credentials and are not vendor proof. `tmp/` contains private runtime databases and is excluded from the evidence manifest; do not publish it. The manifest allowlist also excludes tool caches. Independent read-only review found no remaining blocker and matched the final seven source files; see independent-review.md/json. Local commit `23dab0d150132f23c156608e8aa0b4f081726822` changes only the seven authorized files; the worktree is clean, and all 948 non-progress tracked files match their actual Git blobs. See commit-receipt.json and final-inputs.json.
