# Independent readback: complete Python at 814cda7f

No confirmed blocking discrepancy. This review read existing artifacts and Git objects only; it did not execute pytest, a product gate, the archived runner or sealing script.

The original terminal log and receipt establish 3582 collected, **3580 passed, 2 skipped, 2 warnings in 2324.29s (0:38:44)**, exit 0. Both skips explicitly report BLOCKED_ENVIRONMENT for actual Single/Restore sealed runtime tests. This is not a physical numeric PASS. Runner process duration 2325.062 seconds and UTC timestamps are retained separately from pytest duration.

All 1321 complete tracked non-progress paths were independently enumerated from fixed Git 814cda7f73e864af7a499c0486b4fe9bc46fccb9; every before hash/size matched Git and the current isolated tree. Before/after bytes are equal, and actual private run_gates.py is bound in both. Sole spec hash remains 949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05. The full command has no selected test subtree. Focused, Web/native and CI results are not added to this count.

Private package manifest nine items and seven explicit candidate mappings verify. Only exact personal-home/runner prefixes produce its <LOCAL_HOME>/<RUNNER_HOME> derivatives; original four raw scanner findings remain FAIL and candidate scanner/header/JSON-field checks pass. Audit ran 2681 explicit checks, all PASS.

The subsequent 13-file public package also matches its exact outer manifest: seven previously verified safe payloads remain byte-identical; four metadata files are mapped and only metadata/SAFE_SHARE.json needs exact home-prefix replacement to $HOME/$RUNNER_HOME. Its summary retains the original counts and environment boundary. This is public-copy readback, not a new product test.

Explicit publication candidates from the producer remain REPORT.md, python.log, python-receipt.json, python-before.json, python-after.json, run_gates.py, seal_python.py under its safe-share directory. No runtime, cache, test database, raw directory glob or additional payload is admitted. The independent receipt package has its own separate SAFE_SHARE.json.
