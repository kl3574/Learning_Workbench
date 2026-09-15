# M4.1 Route development checks

Bounded development evidence, not milestone acceptance or an exact-commit full gate.

Final focused result: 38 passed (28 new Route/scope/activity checks, 8 root route-source checks, 2 existing course-history checks), Ruff passed, Mypy passed on six new production files. The final source files are post-run observations; source-before manifests were not captured for these development runs.

The first tests had 16 passes and 3 failures: wrong expected existing hash-error HTTP status, omitted required workspace title in a test fixture, and invalid fixture skill. After those test corrections, 22 passed. The expanded run had 37 passes and 1 fixture failure because SQLite correctly rejected malformed JSON; the final test uses duplicate-key JSON that satisfies SQLite syntax but requires strict application rejection. Initial typing and test-lint failures are retained, including their exact diagnostics.

`manifest.json` binds each raw input hash to its public derivative. The private raw-path and CSRF replacement mapping is stored outside this directory. CSRF values are replaced only when appearing as complete hexadecimal X-CSRF-Token/csrf_token fields. Pytest abbreviated hexadecimal prefixes map to the same uniquely matching full field token, preserving ellipsis and adjacent context; known repository/pytest roots and process addresses are redacted. No outcome, assertion, count, source logic or diagnostic meaning is changed. The source snapshots contain original synthetic test inputs, not personal study data.

No database, browser profile, DOM snapshot, cookie, raw CSRF, provider credential, or private absolute source path is included. No tests were rerun during packaging. Automated inspect and explicit known-value readback supplement manual review; they do not guarantee recognition of arbitrary secrets or prove full product correctness.
