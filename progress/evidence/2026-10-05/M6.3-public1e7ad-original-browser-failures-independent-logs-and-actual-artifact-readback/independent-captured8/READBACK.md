# Original CI log independent readback

Eight original completed job logs were independently read and hash/size checked against their original capture receipts. Each receipt has capture exit 0 and empty stderr. Only 36 explicitly allowed input files were read: eight stdout/command/receipt/stderr quartets and snapshots 02, 07, 11, 44. No new API request, observer, product execution, test, model call, host security probe, source change, rerun/cancel, or remote write was performed.

The fixed events are push 37241154917 and pull_request 37241158099, attempt 1, source head `1e7ad7a8656c0dc8373d4181fa3002f385ed1847`. Push logs record actual checkout at that head; PR logs record actual merge checkout `88da38fc07cd1d797e1171943a00159842421ac3`, merging the source head into `e2877101d9c2bda0f793a460db63ef496350c6b4`. Actual checkout tree IDs and original Git commit/tree objects are **NOT_CAPTURED** in the allowed inputs. No tree equivalence is inferred.

| Original job, separately in each event | Real recorded result | Scope |
|---|---|---|
| frontend | 167 files, 1421 tests passed | Vitest; original lint/typecheck/build steps also present; chunk size warning greater than 500 kB |
| backend | 994 passed, 3 warnings | pytest tests/unit tests/security; ruff All checks passed, mypy no issues in 290 source files |
| spec-contracts | 962 passed, 2 warnings | pytest tests/contract tests/unit/test_spec_*.py; make verify-spec step present |
| security-publication | PASS, scanned 22290 staged/tracked files | Original path/credential scan; original log says manual provenance review remains required |

The two shared pytest warnings are FastAPI/httpx TestClient deprecation and deprecated anyio.abc.BlockingPortal alias. Backend additionally records the original Pydantic serialization warning for `thread_id=True`, bool where str was expected, at `test_typed_interrupt_is_rechecked_without_enabling_python_field_alias_input[True]`. Full original warning blocks with log line locators are retained in READBACK.json.

Snapshot 44 at `2026-10-04T23:23:29.738120+00:00` records four completed successful jobs per event; browser and integration remain `in_progress` with null conclusion in both events. This is a historical file readback, not a fresh observation. Full-run PASS is not established. Counts are job-specific and overlap across Python commands; they are not a distinct-test total and do not establish the default full Python suite or whole M6.3 acceptance.

27f local full-suite running evidence was not accessed or modified. Reports and input allowlist are private candidates only; no canonical files were changed.
