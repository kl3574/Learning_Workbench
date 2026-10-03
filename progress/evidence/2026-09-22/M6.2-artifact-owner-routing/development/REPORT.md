# M6.2 explicit artifact owner routing — bounded development evidence

Base: 416b53261dafa0ddbdec3adf4ef2deab058b866b, isolated m62-artifact-owner-active. Sole specification: PRODUCT_DESIGN.md 3.0.7, SHA256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d, in particular the existing controlled download contract at line 1958 and DownloadArtifact at line 1237. DECISION.md is an engineering compatibility note, not an additional specification.

The existing HTTP download URI now delegates to an explicit ArtifactsService registry containing only the actual Import reader. Exact artifact id/workspace and Jobs-owned kind select the registered profile/kind; no id prefix, missing-owner fallback, caller-supplied owner, or Quality implementation is introduced. Unknown or unregistered ownership rejects with ARTIFACT_OWNER_UNAVAILABLE. Import-origin binding is checked before the existing frozen-budget blob reader returns bytes; strict stored manifest errors are safe CONTENT_HASH_MISMATCH responses.

The facade and direct read_artifact port use the caller's real SQLite transaction, reload the actual session and current role/expiry/revocation/workspace, and check workspace Policy. HTTP no longer uses the old trusted in-process ImportService.download admission path. That compatibility method remains only for existing internal Import callers and still receives the new profile/kind/source integrity checks. A future Quality reader must implement and register its own permission and immutable membership checks. untrusted_quality_receipt remains an untrusted Import attachment. Asset visibility retains its own producer record; it is not replaced with the original package visibility.

Final validation:

- 08-current-session-green: 27 new integration cases PASS, 23.39 seconds.
- 09-import-document-regressions: 64 existing cases PASS, 43.15 seconds, across actual Import repository/HTTP, Document HTTP/worker, and parser exit-race tests. Includes current independent-attempt Policy, private original, exact original/receipt/asset bytes and restart checks.
- 10-ruff: seven changed files PASS.
- 11-mypy: six changed product files PASS.
- Each final run independently recorded the same 963 declared non-progress source files before and after; the audit also re-read all 963 against current worktree bytes. This is bounded validation, not a full-repository gate or proof of unimplemented Quality/report/review/publishing flows.

The new cases use actual Import uploads/parsing and real cookie sessions. They cover all four produced Import profiles, explicit unknown/unregistered owner, direct unknown-profile rejection, wrong actual Jobs kind, reattachment to another actual Import job, cross-workspace artifact/source/job, wrong source membership, malformed manifest (including unknown field and boolean version), hash/size/file damage, stale author after role change, revoked/expired/missing/rebound session, and the real authentication-to-owner window. The direct-owner read-only case sets query_only, prohibits a second database connection and compares full SQLite dumps before/after. Existing HTTP headers, download bytes and private permission behavior remain covered.

All development failures are retained:

| Stage | Actual result | Meaning |
| --- | --- | --- |
| 01-unknown-owner-red | 1 FAIL | Original HTTP returned 200 after a real Import artifact's profile changed to unregistered quality_report. |
| 02-unknown-owner-green | 1 FAIL | Despite its historical directory name, this is a failed test: implementation returned 409 but the test read the wrong error JSON level. |
| 03-origin-manifest-red | 6 FAIL, 11 PASS | Actual source-membership/rebinding and malformed-manifest gaps before integrity hardening. |
| 04-origin-manifest-green | 17 PASS | Origin/manifest fixes at that stage. |
| 05-complete-owner-cases | 24 PASS | Four actual profiles/private/cross-workspace cases added. |
| 06-ruff-red | 17 E701 | Test formatting errors, corrected without changing the assertions. |
| 07-final-owner-cases | 3 FAIL, 24 PASS | Test hook initially targeted interfaces.http.authenticate; the live call is in interfaces.boundary. No product failure was inferred. |
| 08-current-session-green | 27 PASS | Correct actual authentication seam and direct-owner negative. |
| 09-import-document-regressions | 64 PASS | Existing five-file regression scope. |
| 10-ruff | PASS | Seven changed files. |
| 11-mypy | PASS | Six changed product files. |

The repeated stages overlap and must not be added as unique cases. The final 27 new and 64 existing cases are disjoint scopes. The first stage has 961 declared inputs (new test only), later stages 963 (two new product modules also present); these counts are not claimed invariant across development stages. Actual execution commands, UTC timing, exits, source bytes, hashes and original outputs remain in each stage. Untracked files have null base Git blobs, not fabricated Git identifiers. Final commit binding is recorded separately when available.

No new HTTP operation, main/Quality wiring, core schema, migration, specification, approval, content publication, numeric execution or vendor call occurred. Test databases, pytest temp directories, mypy caches and any runtime authentication material remain private and are excluded from the evidence manifest. This private cache is not an automatically publishable bundle; a future publication must independently scan and exactly redact any private values while preserving raw hashes.
