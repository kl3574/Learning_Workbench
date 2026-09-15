# M5.1 corrected-test publication e4807e9: actual CI results

Publication head: e4807e97661147e243c2d40f65d8d4fb5af79a82. Software/test-fix anchor: 0c7fc52a177ef36c55d51be61ca373870516cba4. Final checks: {"success": 10, "failure": 2}. These are actual observations, including failures; no rerun or cancellation was performed by this collector.

- push: run 34943028958, failure, actual run attempt 1.
- pull_request: run 34943033862, failure, actual run attempt 1.

- pull_request / backend, job 104295888590: success. ======================= 537 passed, 2 warnings in 22.60s =======================
- pull_request / browser, job 104295888563: failure.   84 passed (11.9m)
- pull_request / frontend, job 104295888470: success.  Test Files  52 passed (52) |       Tests  314 passed (314)
- pull_request / integration, job 104295888283: success. ================= 584 passed, 2 warnings in 192.89s (0:03:12) ==================
- pull_request / security-publication, job 104295888502: success. 
- pull_request / spec-contracts, job 104295888509: success. ================= 386 passed, 2 warnings in 141.20s (0:02:21) ==================
- push / backend, job 104295871561: success. ======================= 537 passed, 2 warnings in 24.09s =======================
- push / browser, job 104295871623: success.   85 passed (11.8m)
- push / frontend, job 104295871360: failure.  Test Files  1 failed | 51 passed (52) |       Tests  1 failed | 313 passed (314)
- push / integration, job 104295871653: success. ================= 584 passed, 2 warnings in 265.68s (0:04:25) ==================
- push / security-publication, job 104295871724: success. 
- push / spec-contracts, job 104295871655: success. ================= 386 passed, 2 warnings in 138.15s (0:02:18) ==================

Observed failures, if any:
- push frontend: line 255:  FAIL  src/features/providers/ProviderSettings.test.tsx > policy hides previously read summaries but preserves only safe revoke identities
- push frontend: line 256: TestingLibraryElementError: Unable to find role="button" and name "确认发送撤销授权"
- push frontend: line 510: ##[error]TestingLibraryElementError: Unable to find role="button" and name "确认发送撤销授权"

The new push frontend failure concerns the policy/revoke-confirmation case, distinct from the original6c refresh-count failure. The raw log and DOM remain available; an absent confirmation button in this test observation does not by itself establish the product cause or a Policy bypass. PR frontend results must not be extrapolated to the push result.

The PR browser also fails its actual-independent-assessment settings case (provider-settings.spec.ts:112), at136:163: after clicking delete-secret-reference, the5-second toBeVisible assertion cannot find the r3 original-command confirmation. It reports84 passed and1 failed; push browser reports85 passed. The final PR run artifacts API returns total_count=0. The log names an error-context path, but no downloadable artifact or DOM-cause proof is available from that API observation.

All12 checkout logs are bound to their actual checkout commit and GitHub git-commit tree responses in final-ci-receipt.json. A PR synthetic merge commit is not renamed to the head commit; tree equality is separately recorded. PR49 status is the timestamped final API readback, not a guarantee about future updates.

Actual immutable Git comparison proves all600 inventoried inputs at e480 equal0c; its131 changed paths are progress only. The original local fullPython/native acceptance anchor remains769, and0c has separately documented focused fix gates. Old6c CI failures are retained in their own package. CI spec/backend/integration selections overlap and must not be added to replace local fullPython1494. No real paid provider, model/search/Codex or learning-effectiveness validation is implied.

Every payload has original/public SHA-256 and byte counts. Raw API JSON and logs remain unchanged in private cache. Only personal/hosted-runner path prefixes and any concrete runtime identity/secret-location values are normalized, with counts per file. Explicit synthetic constants and type declarations remain. Full logs retain ANSI escapes; final receipt excerpts remove ANSI for readability while preserving original line numbers. Browser rows require actual tests/e2e source, excluding unrelated build checkmarks.

The aggregate is SHA-256 of UTF-8 JSON for the path-sorted array [{"path":public_relative_path,"sha256":public_sha256},...], using json.dumps(sort_keys=True,separators=(",",":"),ensure_ascii=True) without a trailing newline. Manifest is excluded from the aggregate but included in the bounded path/key/provider-token/session/CSRF/locator/staging scan. This scan is not an all-secrets or future-log guarantee. The collector made read-only GitHub GETs and immutable local Git reads; no repository edit, local test, push, ready/merge, rerun or cancellation occurred.
