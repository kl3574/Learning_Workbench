# Independent review of the numeric Provider-history correction

No blocking defect found in the exact reviewed correction. The prior confirmed gap is addressed in both single-block and group numeric protected access and worker admission. This is a bounded source review plus independent verification of another agent's raw regression evidence; this reviewer did not rerun tests or execute a provider/calculator/browser.

Scope is the seven explicitly named product files (six application files and main.py), four existing numeric fixture files, and the final new regression test. The instruction called these “8 product” files, but its explicit list contains seven. No unlisted eighth product file is inferred. HEAD remains `bebf80601b3debf788d446ed2b3abf0847b392bc`; PRODUCT_DESIGN 3.0.7 remains SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.

## Source review

- `services/api/app/application/authoring.py:33` and `authoring_group.py:29` expose typed `verify_history(conn, identity, identifier)` on the actual owning services. They require an active caller transaction and retain the original context, checked Provider receipt/artifact, outcome/usage and raw-output checks. They do not open another connection, dispatch another request, or grant a synthetic Provider capability.
- `authoring_numeric_service.py:29-36` and `authoring_group_numeric_service.py:32-39` retain numeric repository/context history checks, require the injected real Authoring owner, verify the original source Job through that owner, and compare the owner's candidate with the already verified numeric candidate. Missing owner fails with `503 AUTHORING_OUTPUT_UNAVAILABLE`. Protected preview/read/decision check history before ACK replay and before new runtime preparation or Job mutation.
- `authoring_numeric_worker.py:73-86` and `authoring_group_numeric_worker.py:81-95` retain the original approving-session/current Policy and exact numeric input guards, then verify the actual owning Authoring history and full candidate. The existing process path uses this check before launch permission, and `_watch` uses it before lease renewal. No fallback, implicit redispatch or alternate execution identity was added.
- The separate `_control_history` functions preserve the prior repository/context-only behavior for safe Job read/cancel. These paths do not acquire Provider bytes, require the new owner dependency, or invoke the protected academic guard. Generic JobService's ownerless instances therefore remain suitable for their existing safe control operations. This is a static statement; the new regression's safe-control cases use the current author identity, not a separate learner/Policy-lock runtime experiment.
- `main.py:86-93` supplies the existing real `AuthoringService` or `AuthoringGroupService` instance, already composed with the actual `CheckedDispatch`, to each matching numeric service and worker. The four existing fixture changes only add the same explicit owner constructor argument; business assertions were not changed.

The precise eleven-file correction is preserved in `exact-fix.patch`, SHA256 `9e3235400ace34a3dfedeeb53327429b41d18e1368f2315a61441615de05383b`. Every before snapshot matches the clean RED run's declared SHA; every current snapshot matches the GREEN run's declared SHA. The eleven reviewed files remained unchanged during this review.

## Independently verified evidence

Original evidence is in sibling cache `m61-numeric-provider-history-verification-v1`. Its `run_check.py` records commands, stdout/stderr, per-file fingerprints and timings. I read the script, actual logs, receipts and snapshots. I verified log sizes/SHA and exact before/after equality, rather than relying only on the reported totals.

| Evidence | Actual result | Raw log SHA256 |
|---|---|---|
| `red-fixture-repaired` | 12 failed, 2 passed, 2 warnings in 13.92s | `dd94182fcdd9f4806f525815c6926b6f0957543449477d2d377705afd6e8713e` |
| `green` | 18 passed, 2 warnings in 18.16s | `1487f9fa5bca2fd77eba057349372c7e696296011d720d406e52353891c0db2f` |
| `ruff-green` | Passed on the six owner/service/worker product files and new test | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `mypy-green` | No issues in six owner/service/worker source files | `ab35ee42183d4d6d3ba483825ab037d18a5a15622d03be01d82220b1564851ff` |

Each of these four runs has exactly identical 938-file before/after metadata within the runner's declared scope, which excludes progress. RED-to-GREEN content changes are exactly the seven product files, four fixture files and one new test. All 18 saved `source-green` files match both their source manifest and the GREEN input manifest. The seven product files/four fixture files read by this reviewer match GREEN, including main.py, even though main.py is not one of the six mypy/ruff product targets.

The clean RED's twelve failures are all `DID NOT RAISE ApiError`: five protected operations (new preview, preview replay, read, pending approval, approval replay) and worker guard-before-admission, for each single/group variant. The two safe-control cases pass. Earlier contaminated RED evidence remains in the originating cache; it is not substituted for the clean RED result.

The final test is `tests/integration/test_authoring_numeric_provider_history.py`, SHA256 `e1cf499ff0c9ccebb799d818a83c718b0d7de6637981096da6b2d6b3c243ac7a`. Compared with clean RED, its helper now injects the actual Authoring owner into workers, and four new missing-owner preview/worker cases were added. AST comparison confirms the three original test function bodies/decorators, including all original artifact-damage and safe-control assertions, are unchanged. The helper change does not replace the expected artifact error with the missing-owner error.

These cases first generate a real checked result through an explicit controlled loopback test Provider, then damage only its private cached artifact bytes. They preserve the original stored digest/receipt/candidate, prove the original Authoring read rejects, and compare table hashes and runtime counters after rejection. No calculator is executed. Worker regression scope is the original `_access` immediately before `begin`, not a full `process` run; `_watch` coverage in this review is static. Four missing-owner cases assert the distinct `AUTHORING_OUTPUT_UNAVAILABLE` error and absence of any execution record.

The structured readback and all exact receipt bindings are in `evidence-readback.json`; the test-only delta is `new-regression-test-delta.patch`. The original damaged-history public package remains unchanged and describes the pre-fix state. This review is not numeric PASS, native acceptance, race-freedom proof, CI causality, or complete M6.1 acceptance. No product/test files, private SQLite/credential state, native ports or remote resources were modified/accessed by this review beyond read-only source and safe evidence metadata/logs.
