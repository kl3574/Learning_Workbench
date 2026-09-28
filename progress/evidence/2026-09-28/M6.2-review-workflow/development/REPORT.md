# M6.2 Review application, worker and Quality report — private evidence

This is the local application/persistence slice, not complete M6.2 acceptance.

- Sole specification: PRODUCT_DESIGN.md 3.0.7, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. The outer document and worktree copy are byte-identical.
- Actual base: `1391e8c87737d21ed8caf3af773040cfc96b4581`.
- Prerequisite privacy tests/fixes adopted here as `3995eb0` and `fa82a0b`; upstream originals are `70503ede4ec6060fa93d56ca6a9c21ff5db04384` and `0049d4f78d1ab392e0df3f433ac43b420db8572d`.
- Implementation: `e3fd9795c54b901e075015f168b1114ed7cb74e5`; repair/owner-port increment: `f5c80556a48e348cc6dbdebe6482ff54ad822693`. Root should adopt those two implementation commits, without duplicating its already-adopted prerequisite patches.
- Actual implementation tree: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-review-workflow-active`; clean at evidence assembly. No push or main-tree mutation.

## Implemented scope

Real SQLite ReviewService create/read/explicit human decision/cancel, actual Jobs leases and cancellation/unique terminal, Quality machine/human history and original ACKs, and real immutable report blob/complete manifest. Current actor/session/workspace/Policy, exact candidate/material/numeric history, full original history and physical bytes are checked in the same transaction. Original ACK replay still performs full current access/history validation. Safe Jobs control paths retain cancellation access during role downgrade or test locks and return no private subject content.

The worker executes only existing structural checks and preserves existing numeric history observations. It performs no Provider call, numeric runtime execution, mathematical proof checking or source approval. Machine mathematical/source/independent-pedagogy fields remain NOT_RUN. Human approvals and N/A decisions in tests are explicitly synthetic. Plain non-mathematical material permits a current author's explicit N/A and unchanged reason; actual mathematical structures/TeX formula signals block N/A. This is a guarded human judgment, not machine certification that arbitrary prose contains no mathematics.

Quality report hash dependencies are acyclic: report bytes precede artifact binding, receipt, machine record and Jobs result. Final writes share one outer transaction; live lease is checked again after physical write. Rollback may leave an unreferenced immutable blob in restricted local storage, never a successful DB report/receipt/terminal pointer. Registered Import and recursive Quality evidence are authenticated under current Policy and exact original owner/history, with physical byte validation and cycle rejection.

Jobs scheduling and Artifacts manifests are read through their owner repositories. Invalid scheduling IDs/times are excluded from candidates and diagnosed; healthy queued work remains eligible. A corrupt row is never granted a lease or repaired. Quality-specific SQL/blob persistence resides in infrastructure/review_artifact_repository.py; application/review_artifacts.py retains pure report DTO/serialization and `PROFILE='quality_review_report'`. Public constructor/method signatures sent to root remain unchanged.

## Fixed-source validation

The final `24-fixed-final-regressions` ran on actual `f5c80556a48e348cc6dbdebe6482ff54ad822693`:

- 234 passed, 2 existing dependency deprecation warnings, pytest 175.58 seconds; command exit 0.
- Seven files: review_workflow, review_boundary_diagnostics, review_repository, review_job_lifecycle, review_structure_checks, review_numeric_observations, artifact_owners.
- Wrapper UTC interval: 2026-09-28T01:23:53.399913+00:00 through 2026-09-28T01:26:49.377207+00:00; wrapper elapsed 175.977292667 seconds. Do not substitute pytest elapsed for the wrapper time domain.
- Raw run.log SHA256 `f3922ced77a1eecc2fff6c486a4073b8ddc1f8de14bcebdc5231141e53b3f5c4`.
- 982 engineering inputs before/after were identical. `GIT_SOURCE_BINDINGS.json` compares every captured engineering input with its actual Git blob at the stated commit.
- `22-increment-ruff`: seven relevant code/test files, PASS, exit 0. Raw log SHA256 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`.
- `23-increment-mypy`: six production files, PASS, exit 0. Raw log SHA256 `ab35ee42183d4d6d3ba483825ab037d18a5a15622d03be01d82220b1564851ff`.

Earlier `11-fixed-owner-regressions` was 196 passed on actual **e3fd979**, not f5. Its 981 inputs and static stages 12/13 are separately bound to e3; it is not relabeled as the final candidate run.

## Failure history retained

Every numbered stage retains original command, exit, log, input manifests and copied source. `TASK_RECEIPT.json` enumerates all stages without replacing failed outcomes.

| Stage | Actual outcome and interpretation |
|---|---|
| 01 | Missing ReviewService collection error, before implementation; not runtime defect proof. |
| 03 | 40 PASS / 1 FAIL: fixture used unsupported visibility `public`; corrected to actual allowed storage value. |
| 05 | Mypy reported one Literal typing mismatch; implementation annotation repaired. |
| 06 | 41 PASS on an earlier over-restrictive N/A implementation; superseded, not accepted N/A semantics. |
| 07 | 48 PASS after allowing legitimate plain-content human N/A and adopting real owner privacy regression. |
| 08 | 47 PASS / 3 FAIL: formula fixture used nonexistent Import API; fixture corrected to real Import.stage. |
| 09 | Three formula cases passed through real Import parser/owner. |
| 14 → 15 | Actual missing starred equation/align N/A guards: 2 FAIL / 7 PASS → 10 PASS, including legitimate human N/A. |
| 16 → 17 | Actual report artifact created_at binding defect: 1 FAIL → 1 PASS. |
| 18 / 19 | Owner-port subset 8 PASS; additional real owner regressions 2 PASS. |
| 20 → 21 | Actual malformed created_at/id starving healthy queue: 2 FAIL → 3 PASS including prior bad-input isolation case. Stage20's unexecuted diagnostic assertion used an erroneous expected symbolic code; stage21 asserts the existing Jobs code AUTHORING_INTEGRITY_ERROR, and RED failures occur earlier in the real owner scan. |
| 22 / 23 / 24 | Final fixed-source lint/type checks and 234-test gate PASS. |

The four accepted external evidence corruption cases exercise both real Import and recursive Quality report evidence, then damage actual bytes or membership; receipt read, original human ACK, original create ACK and report download all fail closed. Coverage also includes owner-generated single/lesson/practice-set/assessment material; current session changes; active test Policy; transactional failure after writes; lease expiry after blob write; cancellation and lease recovery; exact actor/reason; and frozen prior numeric observations without runtime execution.

## Boundaries and next work

HTTP routes, CSRF, generated bindings, app startup and shared Jobs routing are owned by root's separate composition slice. Draft `in_review`/`approved` state projection is still deferred, alongside publication, version comparison, impact propagation and restoration. No whole-backend/frontend suite, actual browser acceptance, hosted CI, remote deployment, real model call, numeric sandbox run or real content expert approval was performed by this slice. R-21/R-24 and M6.2 are partial, not closed.

Independent reviewer `/root/current_group_ci_diagnosis` completed the fixed-f5 review: Standards 0 open findings (one prior owner-boundary issue closed), Spec 0 open reviewer findings (starred TeX and scheduling isolation closed). They read all eight final files and original five-file implementation, checked actual stages14–24 and compared all final 982 engineering inputs to actual Git blobs; they did not rerun tests. Their separate `m62-review-workflow-independent-v1/REPORT.md` SHA256 is `8548d31de6dfec6dd20ac10377076108d83026389445a54c9e4ebe39bdee9205`, manifest SHA256 `1daedd3eab70ae084c058599dfd40a90fe85c68addf8e7f731825369e5178e5c`. Root owns combined HTTP acceptance and publication.

`TASK_RECEIPT.json` carries the §19.3 fields; `GIT_SOURCE_BINDINGS.json` maps exact tested inputs to actual commits; `PRIVATE_RAW_INDEX.json` hashes all other retained files and excludes itself to avoid a hash cycle. This directory is private evidence and may contain local paths or synthetic fixture trace material; do not publish it without root's sanitization workflow. There are no real vendor credentials or calls in this slice.
