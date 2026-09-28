# Exact fb16 push and PR CI evidence

Both first-attempt pipelines succeeded with six jobs each: push 36371453103 and PR 36371456878. Start with `raw/REPORT.md`, `raw/TASK_RECEIPT.json`, `raw/p12-audit.json`, and `raw/source/verification.json`.

All twelve **complete** original job logs are included. The sole transformation replaces exact CI runner account path prefixes with `<CI_HOME>/`; every replacement is identified by its original/public byte offsets and original span hash in `manifest.json`. No log lines, warnings, skips, commands, test counts, or error values are omitted. Logs with substitutions are derivatives, not raw-byte-identical logs. Original acquisition receipts retain the hashes of the raw originals, while the outer manifest binds raw and public hashes.

Each integration job has 1504 passed, one explicit sealed-numeric BLOCKED_ENVIRONMENT skip, and two dependency warnings. Each browser job has 102 passed. All six APT steps succeeded, with four precise official package versions verified from each original log. This CI success does not establish calculator execution, live provider behavior, human mathematical/pedagogical approval, or complete M6.2 acceptance. No vulnerabilities are asserted resolved by this package.

Actual checkout: push `fb16dcc3857830acc22677f83dbd285701bea202`; PR merge `74f76a4254d5a6dcd3e4df578b8cf3d5a64a78b3`. Both source trees are `2be7fb71a175a36ba80db030f5a9bcc849ecd07a`. The current PR API merge SHA differs and is preserved separately; it is not used to substitute the checkout proven by all six PR job logs.

The final artifact APIs returned no artifacts and no job failed in these two runs. There are consequently no new failure attachments in this package. The earlier 507 CI failures, screenshots and diagnostics remain unchanged in their original evidence; a later successful run does not identify or close their causes.

`manifest.json` accounts for every private raw file, including the original 314-member manifest, intermediate polls and interpreter bytecode excluded from this minimal package. Raw originals are unchanged. Included prior readers are evidence of how GET-only monitoring occurred; do not execute them to refetch or overwrite these captures. All log content originates from public GitHub synthetic CI. GitHub's original masked authorization marker remains masked and unchanged. No local database, model key, learner text, SessionIdentity value, CSRF value, or local runtime is included.

Run `python verify.py` for public-only hashes, spans and exact member-set checks. Run `python verify.py --raw-base <private-original-cache> --ci-home <exact-original-CI-home>` for complete raw inventory/hash checks and exact byte replay. Both modes are offline and execute no product tests. The public manifest's original acquisition hashes always refer to original bytes, even when a public derivative contains path substitutions.

This is a prepared evidence package, not remote publication. The packaging task performed no retry, dispatch, merge, source edit or product test. Its scanner result supplements explicit provenance review and is not a general guarantee about arbitrary sensitive prose.
