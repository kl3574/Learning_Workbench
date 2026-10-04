# M6.3 supported memory-operation approval evidence

Fixed source: `9d3ffb0cebd6df099376ee4de37026e210891b02`, base `fdd3a949fc9bc6edb2d136b912f3d8d1cdba4b81`; branch `feat/M6.3-generic-approval-execution`. This is an isolated local candidate, not a remote publication or whole M6.3 acceptance. The sole v3.0.15 specification is unchanged (SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`). Eleven changed paths, eight production Python paths and three test paths; no route, DTO, generated wire, migration or canonical checkout edits.

## Implemented and bounded

The production operation registry is empty. A trusted synthetic composition can explicitly register a literal-only memory interpreter: one strict canonical JSON command, one string of at most 256 characters, complete two-element argv, empty non-secret environment, no shell, no file reads or writes, no process creation and no network. The actual interpreter returns that exact string. Its actual code-object closure, command schema, logical per-workspace/turn output namespace, profile and full callback are frozen. This is a real bounded in-memory operation, **not** a host command sandbox, app-server approval/accept implementation or physical tool acceptance.

The real existing GenericApproval HTTP owner now supports this explicitly registered complete operation: immutable pending r1; original-actor explicit approval and original key/full-body ACK r2; owned claim r3 committed before invoking the interpreter; checked actual outcome r4. Every start conservatively debits the original turn's finite tool budget. The operation binds the original Provider request/proof/profile, lease and execution owner, workspace/session/turn/Job input and callback identity. No new public execution or registration endpoint exists. Unsupported callbacks remain readable and decline-only.

Generic event v2 and Codex witness v5 coexist with unchanged original v1 Generic/v3 Codex records. V4/0031 remain reserved for the separate interrupt owner. Complete head/event/member/core/command/Run witnesses are checked, including independent debit order and event lifecycle. Original approval ACKs remain immutable; current full/safe GET projection is separate, with fresh subject/identity delivery checks and no DML.

Original author, Policy, turn activity/cancel, fixed interpreter, Provider consent/current proof/source, lease, deadline and remaining tool budget are checked again at actual claim. An approved operation is not continuing authority. Late actual results are persisted through the original integrity-only owner even after role loss; full subject delivery is denied. A committed start without a checked receipt becomes unknown and is never re-executed. Unknown tool facts cannot be elevated to a completed outer turn. The original `351f7afa` request profile and single-request engine remain byte-identical: a tool result cannot authorize a second model request.

## Actual checks

- Final fixed `9d3ffb0c`: **209 PASS, 2 warnings**, eleven related files, pytest 252.02 seconds; runner exit 0, monotonic runner duration 254.18173374800244 seconds. This is a related subset, not full Python/Web/native.
- Final six checks: Ruff, mypy (275 source files), generated contracts check, specification verification (82 generated artifacts / 54 core / 147 declared / 129 runtime), generated TypeScript strict check, and committed-diff whitespace: all exit 0.
- Final test and static runs each retain full **1430 tracked nonprogress input maps**, before/after identical and every byte equal to the fixed Git object. Earlier fixed stages retain their own exact maps, never relabelled as final.
- New direct cases cover exact positive result, original callback/result/ACK replay, no approval/decline, approved but never started, profile withdrawal, role loss, consent revocation, cancellation, expiry, shared tool debit, concurrent same-key approval, two approvals with one budget, same-thread reentry, wrong-thread rejection, start/receipt transaction rollback, unknown no replay, fresh application recovery/readback, complete-history damage and second model-request rejection.
- Application reconstruction is same synthetic database/new application owner, **not** OS process restart or old-binary capture. The recovery fixture leaves a real committed r3 by suppressing final convergence after a controlled missing receipt, then uses a fresh application and controlled expiry; it does not assert that missing actual-start evidence proves nothing ran.

## Preserved failures and provenance

`GATE_HISTORY.json` and `RED_GREEN_BINDINGS.json` are the authoritative per-stage receipts and hashes. The first fixed `e7aab47e` gate was **1 FAIL / 9 PASS** because the original owner still projected unsupported. The exact original HTTP test file then passed under `ece24ebd` (37 total PASS). `213ccb60` added 16 passing authority/consumption cases.

A further fixed `05f74bc8` oracle was **1 FAIL**: Generic r4 unknown was retained but the outer turn incorrectly stayed completed. The smallest worker aggregation fix `5d19ceba` passed the same whole test file with that exact oracle (**1 PASS**). This failure is retained; the earlier passing subsets did not establish terminal correctness. `d6012613` then passed 35 focused cases and six static checks; final `9d3ffb0c` added only concurrency/debit/reentry tests. Two nonformal mypy attempts on WIP had 19 then 1 errors and remain private originals; they have no fixed-source acceptance claim.

One initial evidence-verifier invocation failed before reading any package because a flag was passed as its positional package path; the empty stdout and explicit failure receipt are retained. The corrected invocation supplies both exact paths. This is an evidence harness failure, not a product test.

Failed logs remain private-only even where a scanner might allow them. Successful output is copied only if explicitly admitted in `SAFE_SHARE.json`, with exact `$HOME` prefix replacement by `$HOME`. All original SHA256/byte counts remain in `RAW_MANIFEST.json`; no database, basetemp, TMPDIR, raw credentials, profile directory or arbitrary log glob is a public candidate. `VERIFY.py` reads only this explicit evidence and fixed Git, independently checks all maps/source bindings/hashes/transformations, and does not execute product code, tests, CLI, models or databases.

## Unimplemented / blocked scope

Production operation and model execution registries remain empty. No real Codex CLI, model, account/login, shell, file-change, network, artifact scanning/import, host isolation or actual upstream accept was exercised. These results do not grant runtime capability flags or establish whole GenericApproval/M6.3 completion. No canonical/progress/remote mutation occurred in this slice. Separate peer/root static reviews retain their own attribution and are not included in the author's execution counts.
