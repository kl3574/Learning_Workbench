Read-only CI monitoring completed at 2026-09-28T03:22:19Z. Both first-attempt pipelines succeeded with all six jobs successful: push run 36371453103 and pull_request run 36371456878, API head fb16dcc3857830acc22677f83dbd285701bea202 (source ce42bf8cae734e49166a1472184fd9c3fa875bc7).

The actual checkout in all six push job logs is fb16dcc3857830acc22677f83dbd285701bea202. All six PR logs instead identify the real merge checkout 74f76a4254d5a6dcd3e4df578b8cf3d5a64a78b3. Git API records verify equal source trees 2be7fb71a175a36ba80db030f5a9bcc849ecd07a and equal workflows. The independently read current PR API merge_commit_sha was 2e6e32555551e5a2606bd7bd210f7389b4f2375f; that field is not substituted for the observed checkout.

Results per pipeline:

- backend: 731 passed, 2 dependency warnings; Ruff, mypy (198 source files), and document sandbox probe passed.
- frontend: 482 passed in 82 files; lint/typecheck and build passed.
- spec-contracts: 603 passed, 2 dependency warnings; specification verification passed.
- browser: 102 passed; push 13.2 minutes, PR 14.6 minutes.
- integration: 1504 passed, 1 skipped, 2 dependency warnings; push 1702.35 seconds, PR 1713.72 seconds.
- security-publication: scanner passed over 11761 files. This does not independently certify every file's content provenance.

The integration skip is explicit at test_authoring_numeric_runtime.py:46: BLOCKED_ENVIRONMENT, real sealed calculator execution did not occur and original failure is retained. The two warnings are FastAPI/Starlette TestClient deprecations. CI success does not establish that blocked runtime, live provider behavior, human mathematical/pedagogical approval, or complete milestone acceptance.

All six required APT steps succeeded, and the original logs show bubblewrap 0.11.1-1ubuntu0.3, apparmor and libapparmor1:amd64 5.0.2-0ubuntu1~26.04.1, and libseccomp2:amd64 2.6.0-2ubuntu5. These jobs actually used Ubuntu 26.04.

Twelve complete job logs, every captured acquisition receipt, and final API snapshots were independently hash-checked by audit-readback.py. No acquisition errors occurred; both artifacts APIs returned no artifacts, so there are no failure attachments to download. Original captures remain numbered and unmodified. Initial discovery used p01/p02; the single bounded monitor then polled every 150 seconds (plus request time) through terminal p12 and exited automatically. No workflow dispatch, retry, cancellation, GitHub write, worktree mutation, or local product test was performed.

Replay entry points: p12-audit.json, p12-summary.json, source/verification.json, monitor-terminal.json, and original logs/* with their individual receipts. The private cache is not a sanitized public evidence package.
