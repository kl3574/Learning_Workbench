# a944 publication CI: complete read-only observation

**Both observed workflows ended in FAILURE.** Observation and artifact acquisition are complete; the platform acceptance is not declared complete. No rerun, dispatch, product test, source/progress edit, or remote mutation occurred.

| Event | Actual run | Workflow head | Actual checkout in every job log | Result |
| --- | --- | --- | --- | --- |
| push | [36379289323](https://github.com/kl3574/Learning_Workbench/actions/runs/36379289323) | `a944ebfbdb835a731393977a606db5b473846e98` | `a944ebfbdb835a731393977a606db5b473846e98` | failure |
| pull_request | [36379291042](https://github.com/kl3574/Learning_Workbench/actions/runs/36379291042) | `a944ebfbdb835a731393977a606db5b473846e98` | `fc68b39c5d17aee48768dc983ccac49ee387ebe3` | failure |

Both are run attempt 1. The two actual Git trees equal `b97979924cf310f7577d9624499afa9648dc33a7`; workflow bytes also match exactly. The PR merge parents and API objects are retained separately from the authoritative per-job checkout log lines. These results apply only to a944 / its recorded PR merge checkout, not isolated 84a comparison work, older fb16/507 results, or later commits.

| Scope | push | pull_request |
| --- | --- | --- |
| Unit + security | 731 passed; 2 warnings; 32.61 s | 731 passed; 2 warnings; 33.06 s |
| Contract + `test_spec_*.py` | 604 passed; 2 warnings; 253.50 s | 604 passed; 2 warnings; 355.93 s |
| Integration | 1570 passed; 1 environment skip; 2 warnings; 1323.16 s | 1570 passed; 1 environment skip; 2 warnings; 1808.98 s |
| Frontend tests | 511 passed / 1 failed; 87 passing files / 1 failing file | 512 passed / 88 files |
| Frontend lint / typecheck / build | lint and typecheck pass; build skipped after test failure | all pass |
| Native browser | 105 passed / 1 failed; 19.7 min | 105 passed / 1 failed; 18.7 min |
| Backend static | Ruff pass; mypy 204 source files pass | Ruff pass; mypy 204 source files pass |
| Publication scanner | 12493 staged/tracked files pass | 12493 staged/tracked files pass |

Job test scopes overlap; their counts are not summed into a unique-test total. There are 9 successful and 3 failed jobs across the two runs. Browser build steps passed before the native tests; this does not replace the skipped push frontend build step.

## Installation and numeric environment

All six backend/integration/browser installation steps succeeded. All six complete logs independently show the exact four installed packages: `bubblewrap=0.11.1-1ubuntu0.3`, `apparmor=5.0.2-0ubuntu1~26.04.1`, `libapparmor1:amd64=5.0.2-0ubuntu1~26.04.1`, `libseccomp2:amd64=2.6.0-2ubuntu5`. This is installation evidence, not a blanket sandbox/security or numeric-execution claim.

Both integration logs explicitly preserve `SKIPPED [1] tests/integration/test_authoring_numeric_runtime.py:46: BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained`. The skip remains an execution limitation and is never reported as numeric runtime success. See push log line 451 and PR log line 479.

## Actual failures and boundaries

1. Push frontend: `ReviewImportShell.test.tsx:58:76`, case `actual Import and Shell preserve review reason until explicit close without submitting import or review`; the Import dialog remained present when `waitFor(...toBeNull())` expired. Complete failure log and bounded safe excerpt are retained. The original reporter records a 2381 ms failed-case duration and a 3974 ms two-test file duration, but no click timestamp, assertion entry timestamp, or monotonic deadline. A PR pass on the same tree does not establish a cause or classify this as a flaky test. Diagnosis remains separate.
2. Push and PR browser: the real Tutor loopback case `tests/e2e/tutor.spec.ts:148:1` failed at line 195 waiting 5000 ms for the exact completed-state heading. Both retain full log, diagnostic JSON, error context, and screenshot. Matching visible symptoms do not prove a shared cause, prove that a completion event had been produced and lost, or equate this run to older CI failures. This observation task makes no causal diagnosis.

The new narrow Import publication native case passed in both runs (12.3 s each): explicit synthetic human decisions, lost publication ACK, original-command recovery, and separate current read. Three controlled Authoring diagnostic native cases also passed in both. These are selected actual case results, not proof that all platform behavior or earlier Authoring causes are resolved. `bounded-native-slice-lines.json` preserves the exact lines.

## Original evidence and local derivation error

The two original ZIP downloads match their server-provided SHA256 digests. Each contains 8 files: 3 files for the actual failed Tutor case and 5 diagnostic JSON files from passing controlled/Authoring cases. The latter are not additional test failures. All 16 archive member sizes/hashes and extracted bytes are checked. Original screenshots remain unchanged and private; this cache is not advertised as a sanitized public package.

A local auditing tool had a real variable-shadowing error: the extracted member target replaced the intended audit output target. The original ZIP, API responses, downloads, and log receipts were untouched. The resulting misplaced audit and the original faulty script are retained, the defect was corrected to a separate `member_target`, and the overwritten derived diagnostic was restored exactly from the original ZIP. The corrected audit and final offline verifier compare every extracted file to the archive. `local-audit-attempt01-error.json` records the failure and repair; this was not a product-test rerun.

One monitoring process performed 13 polls at a 150-second cadence, with individual sleeps of 50 seconds, and exited normally after terminal poll p13 at `2026-09-28T05:22:21.247933+00:00`. The final audit verifies 97 acquisition receipts plus the separate discovery receipt, 12 complete job logs, 6 exact installations, and both archives. No capture failure is present.

## Complete job log index

| Event / job | Original log | SHA256 |
| --- | --- | --- |
| push / integration | `logs/push-integration-108791498121.log` | `d0baa0f0fbcbf9f46350a75856cbce2f90a93cd68296b41bf8d4f32a23294374` |
| push / security-publication | `logs/push-security-publication-108791498280.log` | `bc04d77d8bec036cd39b99ab2d23aed365df1b093ee39a8d6d87c770030b1008` |
| push / spec-contracts | `logs/push-spec-contracts-108791498285.log` | `ac9d30edb6facbf32f62ba3243099f3970b53ce88ac011768338411389221976` |
| push / browser | `logs/push-browser-108791498315.log` | `a5b40093960e912f6483c71d99656f58e444c8e411c05ff7a3584fd1f7f8b388` |
| push / frontend | `logs/push-frontend-108791498320.log` | `76eed27dc745865cb24f4aa2eb2c409c97c75a4a3df24bef0b995266a87ff383` |
| push / backend | `logs/push-backend-108791498325.log` | `d435abb858c4784c4cc5fb09d812b9d94b9b55606f1c6a93c7ad42c9904d2e1e` |
| pull_request / browser | `logs/pull_request-browser-108791503905.log` | `bee69038921e2ae652351338593eef968faeda8b92e75ecc54db467cd518febc` |
| pull_request / security-publication | `logs/pull_request-security-publication-108791504014.log` | `610eef62b3881f6c89735f11fbbbb76ab1cabc3305b4317768279aa2f757bb3b` |
| pull_request / frontend | `logs/pull_request-frontend-108791504015.log` | `2ab81f85a5a188ac2ea9f3bad57c00ac2c734ff8cce5d0b589a69e04ce561b5d` |
| pull_request / backend | `logs/pull_request-backend-108791504042.log` | `1432dd38e59797187ff673e5ef537b9801dad74e9998080921fb2b69827c9dae` |
| pull_request / integration | `logs/pull_request-integration-108791504071.log` | `b416b72d8b2ee79730966d0c0a2466fde8d09ea243aa2d09e97288d412c5b50d` |
| pull_request / spec-contracts | `logs/pull_request-spec-contracts-108791504093.log` | `5629a26e9ef9c9c95108242e0c2947bc3a51714f0a97f17f6cf79469d37e9edd` |

Local replay: `python verify_frozen.py`. It checks the frozen manifest, actual job/source bindings, both server archive digests, and every ZIP/extracted member; it makes zero network requests and runs zero product tests. Generated Python bytecode directories are excluded from the evidence manifest and explicitly listed in `MANIFEST_EXCLUSIONS.json`.
