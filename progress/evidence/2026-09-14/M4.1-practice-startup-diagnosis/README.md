# Practice startup diagnosis — development evidence only

Source under observation: `9a803c24a17df8b621370d18dfe528db10d76325`. Twelve observed source/test files were byte-identical before and after these experiments. No production source, original assertion or timeout was changed. This package contains no successful functional verification and does not supersede the original complete-suite failure.

The original exact-link failure was a missing `无法打开此精确链接` heading. The original five-question failure was the saved label after the second reload at `practice.spec.ts:66`; the five answers, first reload, explicit hint and explicit solution had already completed. The original two error-context files contain error details and test source, **no failure DOM**. Only the error blocks are included here.

| Stage | Actual outcome and limit |
| --- | --- |
| 01 | Zero tests: temporary package module-mode/import.meta harness error. |
| 02 | Two failures earlier than the original locations: preview blank, and bootstrap saved missing. Observer cleanup also timed out. |
| 03 | One failure at the original bad-reference heading assertion. The observed document was blank and 40 actual module requests failed with `net::ERR_INSUFFICIENT_RESOURCES`. |
| 04 | One earlier bootstrap failure; 40 module resource failures. Observed request concurrency peaked at 49; observer cleanup timeout is separate. |
| 05 | Two failures with physically separate per-Vite-process cache directories. Actual resource failures remained 42/41. Shared optimized cache was therefore not necessary for this observed mechanism. |
| 06 | One earlier `Page crashed` during import role readback. FD/limit samples are startup-only; they are not a peak or failure-time proof. |
| 07 | Zero tests: API startup SQLite commit raised `disk I/O error`; the planned Chrome logging experiment never reached a browser. |
| 08 | Zero tests with child-shell soft nofile 4096 / hard 524288: API startup again failed with SQLite `disk I/O error`. This cannot decide the effect of that limit on browser loading. |

Stage 03's count is **40**, correcting an early hand-count of 39. All failed stages and the observer-only failures remain visible. Early speculative explanations involving startup `canLeave`, local CAS or policy state were not established; no production change was justified by these probes. The final nofile control was the last run, and owned servers were stopped.

After this diagnosis was sealed, the root agent separately reported a same-host `/tmp` SQLite `pwrite64` failure with `EDQUOT`. That separate trace is not reproduced here. It must not be used to claim every original browser failure was proven to have the same cause. The original CI/full-suite and any later disk-backed rerun remain separate evidence.

Public derivations retain actual resource pathnames (with only the local exact-checkout prefix replaced), error reasons and event ordering. Ledger summaries omit all DOM, storage records, HTTP bodies, full URLs and runtime capabilities. Browser profiles, databases, screenshots, full traces and optimized cache directories are excluded. The archived `.ts.txt` files are diagnostic code, not executable or automatically discoverable tests; source excerpts and path redactions are explicitly listed in the manifest. An observer's code may contain local DOM capture routines, but their outputs are absent from this public package.

`manifest.json` maps every selected raw input hash to its public derivative hash. The adjacent private input map identifies original local files for audit. `inspection.json` records the current publication scanner and the manual synthetic-provenance review; a scanner pass is not functional test evidence.
