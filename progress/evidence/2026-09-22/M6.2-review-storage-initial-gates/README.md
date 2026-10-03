# Original combined storage gate failure

Fixed code 72e4e64ce0e97b444146fe237efee9f199da16dc, 964 engineering inputs unchanged and Git-matched.
Actual whole Python: 2519 passed, 1 failed, 1 numeric-environment skipped, 2 warnings, 698.43s.
The original failure is test_content_store.py:232: process-wide file-descriptor count changed from15 to14.
No descriptor identity trace exists for that original schedule; do not infer which resource closed or a unique cause.
Ruff, mypy186 and specification checks passed. All four raw receipts/logs/inventories and the source composition are retained.

A separate actual unrelated descriptor closure reproduced the original assertion. Its later isolated-process test repair
and negative leak/foreign-close/same-count-replacement controls are separate evidence, not a rewrite of this FAIL.
No native, vendor, numeric execution, human approval or Quality workflow success is established by this package.
The verifier checks public integrity or replays exact path substitutions against original raw hashes; it does not rerun tests.
