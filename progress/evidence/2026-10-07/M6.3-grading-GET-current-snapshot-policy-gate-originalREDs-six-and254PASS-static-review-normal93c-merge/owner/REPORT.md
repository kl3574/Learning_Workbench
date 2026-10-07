# Grading result read snapshot: finite local candidate

Candidate **e8aa970f8df66ecb89aaaf8bf1542aa40cbb377a**, parent **46eface069616a313aa2300654414189ba901f4d**, branch `fix/grading-result-read-snapshot-oct08`. Owned worktree clean. This owner did not change canonical source/index/progress or remotes. Sole spec PRODUCT_DESIGN.md v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

Baseline result completed a SELECT-only integrity/history/material projection inside default BEGIN IMMEDIATE. A controlled pause after its real projection blocked actual GradingWorker.run_once() on another connection: **SQLite code 5 / SQLITE_BUSY** at its BEGIN IMMEDIATE. Reader trace was BEGIN IMMEDIATE, COMMIT; worker trace BEGIN IMMEDIATE. This original RED proves writer reservation, without a timing threshold. Transitive read-chain zero business DML was statically checked, including frozen help/tutor metadata; no models ran.

Final result completes all original assignment/submission/basis/history/grade/material checks in one BEGIN consistent WAL snapshot. After closing it, a short fresh default BEGIN IMMEDIATE rechecks current attempt_read, current attempt load, subject_read/current_review_policy per-question practice_hint, and solution_read for every prepared non-null solution. Queued outer and nested previous-result current_review_policy are refreshed together. Grade/history/job facts remain the original consistent snapshot. Read connections deny business DML and assert total_changes zero. AST outside result, including worker recovery/claim/compute/finish, is unchanged.

The deliberately incomplete DEFERRED-only version was actually rejected: lock regression passed, but new independent and different-reference same-exposure-group open_book/assisted attempts each let prepared private answers escape (**3 FAIL / 1 PASS**). Temporary source and original failures remain private. Final gate refuses those old outputs and new GETs with existing policy codes. Another test finishes actual worker then starts independent while old queued history is prepared; the final gate refuses that material-bearing output too. Initial no-grade queued read has no phantom grade/history and no DML.

Delivery permission linearizes at the final policy transaction. Subsequent serialization/network keeps the baseline boundary; no protection-through-last-byte claim. Fresh current policy intentionally may differ in time from preserved immutable grading/history facts, and DTO consistency is explicitly checked.

| Original evidence prefix | Actual result |
|---|---|
| 01-worktree | normal owned branch/worktree create exit 0 |
| 02-uv-locked-offline-copy | frozen offline copy install exit 0; tests NOT_RUN at setup |
| 03-original-recorder-setup-failure | host Python datetime.UTC wrapper failure exit 1; test subprocess NOT_RUN |
| 04-baseline-lock-red | original product: 1 FAIL, exit 1; SQLITE_BUSY code 5 |
| 05-naive-deferred-policy-red | incomplete candidate: 3 FAIL / 1 PASS, exit 1 |
| 06-delivery-gate-green | 4 PASS, exit 0 |
| 07-expanded-snapshot-green | 6 PASS, exit 0 |
| 08-related-grading-evidence-queue-gate | 11 files, 254 PASS in 118.33s, exit 0 |
| 09-ruff | All checks passed, exit 0 |
| 10-mypy | no issues in 295 source files, exit 0 |
| 11-verify-spec | PASS, exit 0, M0_structural_baseline_only |
| 12-stage / 13-staged-diff-check / 14-commit / 15-frozen-readback | all actual exit 0 |

All commands preserve argv, UTC start/end, actual exit, private stdout/stderr size/SHA and engineering before/after maps. Tests use independently installed owned locked dependencies with no HOME/CODEX_HOME override. All handles terminal. Safe error/footer facts have raw line/byte/hash bindings. Two footer selector failures, one initial reconstruction mismatch and report Git/full-permission-mode guard failure remain separately retained; none reran tests or changed source.

Only grading.py and new test_grading_result_snapshot.py differ from base. Original grading SHA256 **924ed26dddbec9beb0aac1230c2b826ebddacfc2b7e56118e8b307cdbc10df60**; final **15fb4e05bedf5116b28d2d95b08ec73e2a26769a14e0c77f572286fbb797b404**. Final test SHA256 **7b6442d770d365ecadc27656d72fe8d8a8e29318d550d6dc41883807ac29afae**. Exact diff SHA256 **5e5fcf7f8d0eae930bcbd1551cfb28bd21125b3b6c82ac8f9eaa2ee14e55f345**.

Every original test/static phase maps all1564 tracked engineering paths excluding only literal progress/: Git tree/index exactbase, live normalized Git executable mode/size/SHA exact except explicitly bound grading candidate; newtest SHA separately bound. Each phase before/after map is identical. Original RED and first GREEN lock-test function AST are identical. Later six-test version strengthens old DTO comparison excluding only mutable currentpolicy, refresh/DTO assertions, and adds two branches. Initial test source was reconstructed from owned captured source/patch history and admitted only after exact original pretest SHA match; original mismatch retained.

Final committed1565-path map verifies every Git/index/live normalized mode/blob/byte equality. SHA256 **49bc8e042a3164473210b31bbb5a48677ef66c461d49e855d7ad163ee76b300a**. Stage/commit map changes are expected metadata/source-registration changes, with unchanged frozen source bytes. Full live permission bits are recorded separately and not equated with Git executable mode.

Production DB timeout10000ms, worker lease90s, native30000ms/oneworker/retryzero, Policy, HTTP, DTO, workflow, existing helper/assertion control flow remain unchanged. Test-only worker busy_timeout0 is nonwaiting lock observation. Test-owned Events/10s waits and joins are scheduling/cleanup bounds. Reader errors return explicitly; every started reader releases before bounded join in finally. Real worker/grade/audit/history and signed synthetic review are used; no grades, provider proof, eligibility or real learning qualification are fabricated.

Independent reviewer `grading_observer_static_review` bound final e8aa970 in sibling `m63-grading-result-read-snapshot-independent-review-oct08/final-candidate-e8aa970/`, manifestSHA **b14a84e372385937e948d5e0ce990a75bf1879d8d49d00308e7fc9645b71b01d**. No actionable P1/P2 within its bounded static scope; all reviewer tests/runtime NOT_RUN. Its review does not replace owner actual tests or root admission.

Full dependency-file/runtime hostENV maps NOT_CAPTURED; independent locked offline copy setup is bounded provenance. Full native, new CI, push/merge, production models, keys, network/host/profile probes NOT_RUN. Original CI cause **UNKNOWN**. This independent local contention repair does not establish CI latency cure, M6.3/AC21/realAgent acceptance or learning efficacy. Generic Codex producer-port suggestion is only a future adapter internal-interface prerequisite, not a demonstrated current defect or new acceptance condition.

Raw logs/temp source/complete maps stay private. Only report/structured READBACK/manifest/closed safe source-continuity/line bindings are publication candidates after root independent admission. Prior original CI packets and all original failure records remain unchanged.
