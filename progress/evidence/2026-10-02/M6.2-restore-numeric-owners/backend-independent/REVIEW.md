# Independent Restore numeric helper/backend review

Reviewer: restore_numeric_helper_review. Date: 2026-10-02.

## Scope and identities

- Initial frontend review: fixed fb0217d2db037aebd0f43315a6321cf51b4bd7eb, only restoreNumericClient/Schema/Store/Memory and their tests/fixtures (8 files). Hook, panel, form, other UI ownership excluded.
- Backend static baseline: 4a89abb9a6a533870dac212649ce6a3c6b8885b7; final static review and all reviewer-run tests below: ea3d92ae6a54b4b2b2d9c1e40e6ecb9232fe9ffa.
- Independent detached worktree: $HOME/.cache/learning-workbench-acceptance/m62-restore-numeric-backend-independent-restorehelper-oct02. Clean after tests. No audited source edits, no network, no provider requests, no remote publication.
- Read AGENTS.md and complete sole PRODUCT_DESIGN.md v3.0.12 (4255 lines); SHA256 1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7. Standards and specification axes considered together; other team slots were occupied, so this reviewer did not spawn its own reviewers.

## Findings

Initial helper P1 (already sent to implementation owner): fb0217 restoreNumericSchema.ts:139-142 recomputed Python learning-json-1 numeric result hashes through JavaScript canonical JSON. A legitimate Python actual=3.0 serializes as 3.0, but parsed JS reserialization emits 3, rejecting valid server terminal results. Existing restoreNumericSchema.test.ts:78-87 synthesizes the result hash using JS and masks this interoperability case. Parent independently reproduced the actual Python-to-TS failure and owns its repair/retest. This report does not claim reviewer-run frontend tests or certify later frontend SHAs.

No additional substantiated P1/P2 finding in the bounded helper static review or in the final ea3d92ae backend review. This is a bounded review conclusion, not proof of absence of defects.

Backend assessment: append-only SQL constraints and separately checked heads/memberships reject single-sided corruption, missing/tail/all rows and conflicting replacements; history and original command ACKs remain distinct from current state; owner-routed Jobs, source/base admission, immutable numeric input, retained output hashes and explicit process-start records are checked; first publication requires current numeric observation, whereas historical Review and committed publication ACKs use the original verified prefix. Reviewed ea3 changes include future-fact observation rejection, per-Job verified input reads, and bounded Jobs-owned queue traversal.

## Reviewer-executed checks at ea3d92ae

Interpreter: $HOME/Desktop/learning/Learning_Workbench/.venv/bin/python (Python 3.12), PYTHONDONTWRITEBYTECODE=1. All pytest temporary data lived in this private evidence directory, outside source.

- PASS: tests/integration/test_restore_numeric_service.py, test_restore_numeric_integrity.py, test_restore_numeric_execution.py, test_restore_numeric_migration.py, test_restore_numeric_actual_runtime.py: 56 passed, 1 skipped, 62.15s. Raw log: ea3-focused.log.
- PASS: private test_independent_probes.py: 4 passed, 4.20s. Raw log: ea3-private-probes.log. These independently freeze Review before any material, while preview is pending, and after execution admission; later approval/start/synthetic PASS must keep historical Review unchanged and reject first publication with PUBLISH_NUMERIC_OBSERVATION_STALE with zero read-path table changes. Fourth probe creates 33 invalid owner scheduling hints and verifies a healthy later Restore Job executes on the next bounded traversal, with no execution of the invalid hints.
- BLOCKED_ENVIRONMENT, not numeric PASS: actual sealed runtime probe recorded 353 manifest members, actual process start 2026-10-02T11:59:58.163522Z, exit_code 1, environment_unavailable/BLOCKED, stderr 'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted'. Original JSON: pytest-tmp/test_actual_restore_numeric_se0/physical-probe.json. The pytest skip above is this host boundary, not an unattempted probe.

## Limits

SyntheticExecution/LedgerRuntime cases establish protocol/state-machine behavior only, never actual sandbox isolation or academic correctness. The physical evaluator did not reach numeric PASS. This reviewer did not rerun the full prior backend regression suite, lint/mypy, browser tests, or frontend tests; parent/author receipts for those remain separate evidence tied to their stated SHAs. No claim of complete product, publication, or release acceptance.
