# Independent static review: six-migration legacy fixture compatibility

Result: **no blocking finding** in commit `6e0954add5573bc0d8c84c856712abb6565d5410`, parent `88daa0a23dab0e69f7009b9af670671c45f90924`. The reviewed worktree is clean and contains exactly the two expected test-file changes. No application, migration, grade/evidence implementation, or product assertion was weakened. This review did not run tests/application code, open a database or secret store, use any user API key, or send network requests. Only this independent report cache was created.

- `test_learning_evidence.py:254-302`: the historical fixture still creates real storage from migrations 0001–0006 and uses original Import, submit, grading worker and signed review flows. The new registration override is scoped within the existing `monkeypatch.context()` at lines 281–295. Before doing nothing it asserts exactly six applied migrations, no candidate identity table, and owner/source_kind both Import (273–279). It cannot silently mask registration against current storage. The context exits before immutable grade/submission snapshots and real `new_database.initialize()` upgrade (296–301).
- The preexisting evidence-hook overrides are unchanged. Grade, manual-review, audit, submission bytes, legacy qualification, recovery, post-upgrade submission, and foreign-key assertions remain at lines 305–337. The corrupt-grade quarantine and later safe import still execute the real worker and retain the previous evidence failure/non-starvation assertions at lines 340–365.
- New lines 352–361 additionally require the actual post-upgrade preview to be nonempty and use the unpatched `DraftCandidateRepository.lookup(workspace, draft_id, 1)` for every preview candidate. This proves actual registration is restored after the historical fixture scope. It is a low-level registration/readback check, not a claim that catalog data itself proves owner authorization.
- `test_evidence_independent_review.py:154-156` changes only the explanatory comment. Its late-binding-failure trigger, full evidence rollback, safe import progress, original grade-row comparison, and foreign-key checks are unchanged (153–192).

## Existing execution evidence verified read-only

The RED log preserves the real missing-table failure at `draft_candidate_repository.py:71` while constructing the six-migration fixture. It records **1 failed / 0.98s**. The original two test source inputs match the parent commit bytes.

The final candidate records **3 focused PASS / 3.16s**, **22 related PASS / 12.54s**, and **Ruff PASS**. For all four runs, actual log byte lengths/SHA256 match receipts and all 949 before/after input entries are identical. All GREEN source inputs exactly match the committed candidate bytes, although those pre-commit execution receipts correctly retain parent HEAD `88daa0a`.

I independently mapped every one of the 949 committed input paths to commit `6e0954a`'s Git tree and read the actual Git blob bytes with `git cat-file --batch`, recomputing each byte length and SHA256. All 949 match `committed-inputs.json`; this is not reliance solely on its recorded `git_matches` booleans. `verification.json` contains the comparisons; copied raw receipts/logs/manifests are under `evidence/`.

The focused repair evidence does not establish full Python-suite success, a production schema fallback, broader M6.2 completion, or an explanation of either historical CI failure. Root owns the integrated full-suite run.

## Final source SHA256

- `tests/integration/test_evidence_independent_review.py`: `f3b00d86fe443d1073d5c5e5cef52af82805571bd4cf11370293c43aa340e2a6`
- `tests/integration/test_learning_evidence.py`: `492505d0a7d526e2e65a249b3d4d39b6acdbdc7324b985caf15374ced1f44bb1`

Exact committed/parent source copies and the inspected diff are retained as `source/`, `parent-source/`, and `reviewed.patch`; `source-pins.json` also records the Git blob IDs.
