# Independent static review: immutable review material readers

No remaining blocking issue was found within this bounded change. This is an independent static review plus readback of completed receipts; it is not an independent test run or a claim that the wider M6.2 review workflow is implemented.

## Source binding and scope

The six reviewed files are snapshotted in `final-inputs/` and pinned in `final-pins.json`. The implementation was reviewed against baseline `75b0ca5f83d809816b338c2d70cc5bfb9f1a3f83`; the final readback is commit `93130a93be4b6097be8a4aafd23bbf139ba142fb`, whose parent is that baseline. All six files match the specified final SHA-256 values and their committed Git blobs. All 951 entries in the final targeted run's input inventory also match both current file bytes and the committed Git bytes. Original receipts retain their precommit HEAD and null Git identities for then-untracked files; those receipts were not rewritten.

Only these five product files and one new test were reviewed for changes. Supporting owner/context models and PRODUCT_DESIGN.md 3.0.7 were read to check existing boundaries. No source, test, specification, database, process, Provider or network behavior was executed or changed by this reviewer. Cache snapshots and this report are the only review outputs.

## Findings and closure

1. **Closed privacy defect.** The initial four new material models inherited `dm.StrictModel`. Import body text could appear in ordinary `repr`/`str`, and validation error strings could include raw invalid input. This conflicts with PRODUCT_DESIGN.md:2909 and :2915 and the established safe model at `services/api/app/authoring_dto.py:51`. Final `review_material_models.py:23`, :45, :61 and :86 all inherit `AuthoringModel`, which suppresses repr arguments and hides validation inputs. The corrected privacy test at `test_review_materials.py:364` checks both material layers and uses the first actual content line, avoiding false passes caused by escaped newline representation. The final six privacy cases are included in the 45-pass run.
2. **Closed test representation mismatch.** The intermediate full material run had two failures comparing `AuthoringBlockRef` with `ContentRef` instances despite equal full fields. The final assertion at `test_review_materials.py:295` compares complete serialized fields in order. The actual body deletion and read rejection assertions at :296–302 remain intact; no source completeness assertion was removed.
3. **No remaining material-port blocker found.** The checks below remain present in the reviewed final bytes.

## Checked boundaries

- `draft_candidates.py:42–66`: the facade reloads current author execution identity, applies existing access checks, looks up the exact workspace/draft/revision registration, selects its declared owner, and deeply revalidates the returned typed material and registry identity. The reader performs no registration, repair, cross-owner scan, Provider dispatch or numeric execution.
- `authoring.py:35–59` and `authoring_group.py:31–63`: the existing complete owner history verifier remains authoritative. Material reading uses the caller's connection, rechecks the current author, reads the original context and calls the context verifier to re-read actual selected source bytes. Group reading also requires the original validated plan. Original checked Provider artifacts remain required by owner history; missing artifacts are not treated as pass or N/A.
- `review_material_models.py:45–79` and :98–139: descriptors bind original candidate/input/context, exact source order, owner-record SHA and canonical complete descriptor bytes. The group material includes plan, root, ordered members and all private solutions under the existing complete group candidate SHA (`PRODUCT_DESIGN.md:1148–1156`). Source hashes and descriptors record byte identity; they do not establish mathematical, source or pedagogical approval (`PRODUCT_DESIGN.md:1132`).
- `imports.py:112–127` and :329–370: the new reader reuses the original owner resolver and extracted draft snapshot logic on the caller's connection. Block bodies, citations, source/input SHA and warnings are returned after existing integrity checks. Mutable Draft state is omitted from the descriptor. `ImportReviewMaterial.private_solution_coverage` is literally `excluded` (:31); Import metadata SHA does not expand into approval or validation of private solutions. Import private solutions are absent from this material payload, even when present in the original archive. The ordinary Import draft endpoint preserves its original behavior through the extracted helper.
- `test_review_materials.py`: read helpers enforce `PRAGMA query_only`, prevent a second `database.connect`, and verify unchanged table contents and connection writes. Actual owner/Provider fixtures cover access revocation/role/workspace, absent registration with no repair, assessment policy, damaged or absent source/Provider bytes, plan/root/member/private corruption with a recomputed outer storage digest, Import private solution exclusion, caller transaction requirement, and exact revision. Original owner integrity status codes are preserved.

## Completed evidence readback

| Existing run | Actual result | Interpretation |
| --- | --- | --- |
| 07-repr-red | 3 failed, 3 passed | Original repr sentinel included full newline text; preserved as the imperfect first test version. |
| 08-repr-red-corrected | 4 failed, 2 passed | Corrected first-line sentinel exposes actual Import repr failure plus validation-error leakage. |
| 09-material-green | 2 failed, 43 passed | Directory name is not its result; privacy cases passed, two model-class comparison assertions failed. |
| 10-related-regressions | 106 passed, 2 warnings | Existing catalog, owner, Import HTTP and single/group context regression scope. Product bytes match final; the new test still had its pre-comparison-fix hash. |
| 12-final-mypy | PASS, 5 source files | Final five product files; later change was test-only. |
| 13-final-material-green | 45 passed, 2 warnings, 36.86 s | Final six source files; log SHA-256 `40fcc4cddde27af260110114a80aecc1b3a4961ba7109dc359fa9d3a383714c9`. |
| 14-final-test-ruff | PASS, 6 files | Final five product files and final new test. |

Each copied run has a completed receipt; this reviewer independently recomputed its log hash/length and compared all 951 before/after input records. `evidence-readback.json` records the comparisons and copies preserve the original RED and intermediate failures. Warnings are the existing Starlette/httpx and anyio deprecations shown in those logs.

## Limits

This change supplies internal immutable material readers. It does not implement public review endpoints, ReviewReceipt persistence, human decisions, approval/publication state machines or numeric execution. It grants no sources N/A exemption, numeric PASS, private Import solution approval, or whole-M6.2 completion. Synthetic checked Provider fixtures and existing test receipts do not establish external provider behavior or mathematical correctness. This review does not infer either old CI failure's cause.
