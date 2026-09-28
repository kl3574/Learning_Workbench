# Stage 22 validation-scope correction

The operator's stage 22 exclusion list missed `test_review_history.py::test_generated_owner_history_preserves_exact_numeric_observation_without_running_it`, parametrized with single and assessment. This existing test prepares two controlled loopback generations. This was a test-selection error, not a product defect, and does not satisfy the intended no-Provider validation selection. The actual pytest child was interrupted with SIGINT; the driver saved exit 1, complete log and unchanged before/after input maps. Pytest also emitted a teardown stash KeyError following interruption. No completed test total or full-gate PASS is claimed for stage 22.

A read-only count observation at approximately 2026-09-28 05:42:10 UTC found both stage-22 temporary fixture databases. The following is an explicitly transcribed tool observation, not retained database evidence:

| Temporary runtime alias | provider_dispatches | provider_terminals | authoring_numeric_checks | authoring_numeric_executions |
|---|---:|---:|---:|---:|
| PYTEST_RUNTIME_22/test_generated_owner_history_p0 | 1 | 1 | 0 | 0 |
| PYTEST_RUNTIME_22/test_generated_owner_history_p1 | 1 | 1 | 0 | 0 |

The tool also listed a `pcurrent` symlink to the second fixture; it is not a third execution. Only row counts were read, never private commands, credentials or request bodies. A later attempt to export those counts to JSON failed an `assert len(databases)==1` because the temporary fixture directories were no longer available. That capture failure is retained in `controlled-fixture-capture-failure.txt`. No database or original stdout artifact was preserved from the first count observation, and the count table must not be described as a re-playable retained DB check.

Fixed source 5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d explains the bounded fixture: `tests/integration/test_review_history.py:306–337`; single preparation in `test_authoring_numeric_service.py:54–65`; group preparation in `test_authoring_group_numeric_service.py:84` onward. `tests/provider_protocol_fixture.py:112–154` supplies an explicit local server bound to 127.0.0.1. The numeric test runtime is an in-process ledger double and the history test forbids prepare/check/manifest/run_checked during persistence checks. These tests are not vendor calls, real model-quality validation, real numeric execution or real human approval. No user key was accessed.

Stage 25 keeps the same fixed product source, explicitly excludes the missed function, and records verbose per-test results. Its result is separate from stage 22. The private package excludes all pytest runtime databases and blobs; source, logs, input maps, receipts and this correction remain retained.
