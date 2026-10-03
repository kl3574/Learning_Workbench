# Independent CI terminal archive: 0ede5f94

Read-only GitHub API observation of the existing push and pull-request runs. No workflow rerun/cancel, source edit, remote mutation or product re-execution. Raw API responses, all 12 job logs and four digest-verified artifact ZIPs remain private.

- push run 37083065732: success; 6/6 jobs success; https://github.com/kl3574/Learning_Workbench/actions/runs/37083065732.
  - security-publication: success; PASS: scanned 16270 staged/tracked files
  - browser: success; 841 modules transformed.; Running 125 tests using 1 worker; 125 passed (28.7m)
  - backend: success; Success: no issues found in 236 source files; 751 passed, 2 warnings in 36.94s
  - frontend: success; Test Files  137 passed (137); Tests  949 passed (949); Duration  47.32s (tests 49%, environment 39%, import 9%, transform 3%); 841 modules transformed.
  - integration: success; 2078 passed, 2 skipped, 2 warnings in 2953.25s (0:49:13)
  - spec-contracts: success; 744 passed, 2 warnings in 432.49s (0:07:12)
- pull_request run 37083068519: success; 6/6 jobs success; https://github.com/kl3574/Learning_Workbench/actions/runs/37083068519.
  - security-publication: success; PASS: scanned 16270 staged/tracked files
  - frontend: success; Test Files  137 passed (137); Tests  949 passed (949); Duration  69.18s (environment 45%, tests 42%, import 11%, transform 2%); 841 modules transformed.
  - integration: success; 2078 passed, 2 skipped, 2 warnings in 1566.82s (0:26:06)
  - spec-contracts: success; 744 passed, 2 warnings in 366.05s (0:06:06)
  - browser: success; 841 modules transformed.; Running 125 tests using 1 worker; 125 passed (21.2m)
  - backend: success; Success: no issues found in 236 source files; 751 passed, 2 warnings in 30.04s

Actual push checkout is 0ede5f94cf9bd7569e568bad15d73bc8ac26ea44. Actual PR merge checkout is ba1716ca9a2d97cc8140c3d58841467258e88caa. Both Git commit API trees are e0daf97de9ac0e76214e178e039b0ed1317bea0d; every job checkout was read back separately from its original log. Counts across Python jobs overlap and are not a full-suite sum.

All four actual Single/Restore numeric artifacts retain environment_unavailable / BLOCKED / exit 1 / empty assertions / null output; explicit subsequent publication is HTTP 409 PUBLISH_NUMERIC_REQUIRED and external model calls are zero. Integration environment skips are preserved in CI_TERMINAL.json. Software CI success is not physical numerical PASS or academic approval.

Publication boundary: only SAFE_SHARE.json entries are eligible. Raw job logs, API envelopes, ZIPs, stderr, watcher logs, runtime caches and unlisted files are excluded. Derived terminal/NUMERIC summaries explicitly select safe metadata and bind raw SHA256; they are not claimed as byte-for-byte raw logs. Copied numeric JSONs permit only declared exact home-prefix normalization. Raw archives and original hashes are unchanged.
