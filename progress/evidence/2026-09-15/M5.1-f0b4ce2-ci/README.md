# M5.1 secret-control basis repair publication f0b4ce2: actual CI results

Publication head: f0b4ce2e39a3bc374751379051553108ad6a57ed. Software anchor: 254a4ffe70dcab9db56663cc37245a33ae1495a5. Final checks: {"success": 12}. All results are actual observations; this collector performed no rerun or cancellation.

- push: run 34948788382, success, actual run attempt 1.
- pull_request: run 34948793859, success, actual run attempt 1.

- pull_request / backend, job 104314500528: success. ======================= 537 passed, 2 warnings in 23.23s =======================
- pull_request / browser, job 104314499974: success.   87 passed (11.9m)
- pull_request / frontend, job 104314500185: success.  Test Files  52 passed (52) |       Tests  323 passed (323)
- pull_request / integration, job 104314500179: success. ================= 584 passed, 2 warnings in 364.03s (0:06:04) ==================
- pull_request / security-publication, job 104314500289: success. 
- pull_request / spec-contracts, job 104314500334: success. ================= 386 passed, 2 warnings in 139.32s (0:02:19) ==================
- push / backend, job 104314481294: success. ======================= 537 passed, 2 warnings in 22.80s =======================
- push / browser, job 104314481066: success.   87 passed (12.0m)
- push / frontend, job 104314481237: success.  Test Files  52 passed (52) |       Tests  323 passed (323)
- push / integration, job 104314481064: success. ================= 584 passed, 2 warnings in 351.27s (0:05:51) ==================
- push / security-publication, job 104314480882: success. 
- push / spec-contracts, job 104314481245: success. ================= 386 passed, 2 warnings in 137.44s (0:02:17) ==================

Observed failure excerpts, if any:
None in these final checks.

Every completed job has actual start/end times, original API metadata and complete log hashes. Browser verdicts are derived from actual numbered tests/e2e rows and terminal summaries, with expected source case count87 recorded separately. Test counts from overlapping spec/backend/integration selections must not be summed into a full-suite count. A failed assertion establishes the observed failure, not its product cause. Earlier e480 failures remain unchanged in their own package.

All12 checkout logs are bound to their actual checkout commit and GitHub Git commit tree responses in final-ci-receipt.json. PR synthetic merge identity remains distinct from the publication head, even when their tree hashes match. PR49 state is the final timestamped API observation, not a guarantee about later changes.

Immutable Git blobs prove all600 source inventory inputs at f0b4ce2 equal254a4ff, aggregate b00ae17d2d6e87e01aee18c0082ff1eee32c4be891d343fe4bd1b8df48417452. The265 publication changes are progress/evidence plus docs/ui/m1-session-three-way-conflict.png, previously attributed to the direct native test output. The working tree is not used for these comparisons. Original local fullPython1494 is historical evidence at its original software anchor, not a newly executed publication-head run. Separately recorded local254a gates/native87 are not replaced by this CI receipt. No private provider-test files or user keys were read; separate user-authorized vendor smoke is outside this CI collection and does not establish platform generation, search, Codex, model quality or learning effectiveness.

Every payload has original/public SHA-256 and byte counts. Raw JSON and logs stay unchanged in private cache. Personal and hosted-runner path prefixes and concrete runtime identity/secret-location values are normalized with per-file counts. Explicit synthetic fixture constants and type declarations remain. Complete logs preserve ANSI; final receipt excerpts remove ANSI for readability while retaining original line numbers. Browser rows require an actual tests/e2e path, excluding build checkmarks.

Aggregate: SHA-256 of UTF-8 JSON for the path-sorted array [{"path":public_relative_path,"sha256":public_sha256},...], using json.dumps(sort_keys=True,separators=(",",":"),ensure_ascii=True), without trailing newline. Manifest is excluded from the aggregate and included in the bounded path/key/provider-token/session/CSRF/locator/staging scan. This scan is not an all-secrets or future-log guarantee. No repository edits, local tests, rerun, cancellation, push, ready or merge occurred in this collection.
