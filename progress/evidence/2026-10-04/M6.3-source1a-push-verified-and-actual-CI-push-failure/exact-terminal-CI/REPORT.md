# M6.3 exact 1a CI readback

Source `1a6473dadcf71623008188f465586495ab28a204`. This collection performed read-only GitHub API calls for the two specified runs, their six Jobs each, twelve original Job logs and two Git commit objects. No rerun, source/metadata change, push, merge, release, deployment, application/model/CLI execution, account-secret read or numeric execution occurred.

| Actual event | Run | Terminal outcome | backend | spec-contracts | integration | frontend | browser |
|---|---:|---|---:|---:|---|---|---|
| push | 37207897702 | **FAILURE**, five Jobs success, browser failure | 911 PASS | 956 PASS | 2358 PASS, 2 ENV SKIP | 1278 PASS / 157 files | **129 PASS, 1 FAIL** |
| pull_request | 37207899600 | **SUCCESS**, all six Jobs success | 911 PASS | 956 PASS | 2358 PASS, 2 ENV SKIP | 1278 PASS / 157 files | **130 PASS** |

Both security-publication Jobs completed successfully. Counts are reported per Job and per event; overlapping/repeated gates are not summed. The push browser failure identifies `tests/e2e/tutor.spec.ts:148:1`, Job `111452843003`. Its cause is **NOT_DETERMINED** by this bounded readback. The PR success does not explain or close that push failure.

Each integration log explicitly reports `BLOCKED_ENVIRONMENT` for `test_authoring_numeric_runtime.py:46` and `test_restore_numeric_actual_runtime.py:42`. These are environment skips, not physical numeric PASS. No artifact ZIP or numeric result artifact was downloaded in this task. Old 4b/other run evidence was not substituted.

All twelve original logs were downloaded successfully and each has one actual `git log -1 --format=%H` checkout result. All six push Jobs checked out `1a6473dadcf71623008188f465586495ab28a204`. All six PR Jobs checked out `773b7b5e36b9d6b66cc8af7a26bc1e1c8d8da155`. The API commit objects verify that the PR checkout has the recorded PR base and exact 1a source as its two parents, and both have tree `55b699134d461e76e749b714c589224a44d405be`. A read-only local `git rev-parse` of fixed 1a independently matches that tree. Exact parents and source hashes are recorded in READBACK.json.

METADATA_READBACK.json preserves the first bounded metadata snapshot. READBACK.json binds original stdout/error/command receipts, per-log SHA and checkout facts. PARSED_LOGS.json supplements the initial conservative parser: ANSI escape sequences were removed only in memory to recover frontend and browser counters/locations. Raw bytes were not modified. Only numeric outcome fragments and static test paths are included; original logs, raw API bodies and error streams remain private because they may contain unrelated account or request context.

All fetches used a fixed timeout and at most four concurrent read-only requests. No continuous polling was needed: the first snapshot already showed twelve terminal Jobs. RAW_MANIFEST.json enumerates original evidence. SAFE_SHARE.json is an explicit allowlist; it does not authorize copying raw APIs/logs or entire directories. This is actual CI evidence for the specified 1a events, not a claim that whole M6.3 is accepted or later local source was tested by these events.
