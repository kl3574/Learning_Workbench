# Independent final static review: grading result read snapshot

Outcome: no actionable P1/P2 found within the bound supported product paths. Static assessment only; every runtime/test/build qualification by this reviewer remains NOT_RUN. No product repair, publication, release, or original CI causality conclusion is made.

Candidate e8aa970f8df66ecb89aaaf8bf1542aa40cbb377a directly follows 46eface069616a313aa2300654414189ba901f4d; worktree was clean at readback. Exact delta SHA-256: 5e5fcf7f8d0eae930bcbd1551cfb28bd21125b3b6c82ac8f9eaa2ee14e55f345. Product source SHA-256: 15fb4e05bedf5116b28d2d95b08ec73e2a26769a14e0c77f572286fbb797b404. New test source SHA-256: 7b6442d770d365ecadc27656d72fe8d8a8e29318d550d6dc41883807ac29afae. Canonical PRODUCT_DESIGN.md v3.0.15 SHA-256 remains b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. Exact source paths, Git blobs, full hashes, selected original UTF-8 line bytes, byte counts, and hashes are in SOURCE-BINDINGS.json.

## Actual delta

Only GradingService.result, lines 51-89 of services/api/app/application/grading.py, changes in production. Removing that function gives byte-identical grading.py remainder against base. The second changed path is the new integration test. Policy, repositories, _project, current_review_policy, API route, DTO, worker lease, E2E operations/assertions and default 30-second/one-worker/retry configuration are unchanged.

## Correctness and authority

All original submission, outbox, Learning event, frozen prerequisite, full evidence history, grading job, immutable grade/audit, signed manual review, solution pin, exact material, and DTO projection checks remain inside one explicit DEFERRED WAL preparation snapshot. The audited reachable read branches contain SELECT and pure validation/projection rather than grading/evidence recovery or domain DML. Original missing/recovery/integrity errors remain unchanged. Grade, job status, and complete ordered history are prepared from one snapshot, including safe previous results for 202 responses. Concurrent later progress is not grafted onto that old history.

After the snapshot ends, a fresh default IMMEDIATE transaction checks attempt_read, loads the current target record, recomputes current_review_policy using subject_read and practice_hint for all current assigned questions, and repeats solution_read for every actual prepared non-null solution_markdown. The old prepared target cannot escape a new active independent attempt; same-exposure-group open-book or assisted protection reaches the existing solution_read guard. A safe pending-job response also passes current authority rather than inheriting its older snapshot's permission.

The valid fresh policy is copied to both the pending job and its nested previous result, preserving AssessmentGradingJob.checked_previous equality. Only a validated CurrentReviewPolicy is changed; all immutable projection fields and the full history remain intact. The existing HTTP 200/202 selection, no-store header, and complete response byte budget are unchanged.

## Test-source review

The new file defines six parametrized cases: a real separate worker writer completing while an old result projection is paused; stale released solution refusal after new independent, same-group open-book, and same-group assisted attempts; refusal of an older safe pending history after worker completion and a new independent start; and initial queued/no-completed-grade behavior. Reader connections install a domain-write-denying SQLite authorizer and record total_changes; worker lock observation alone uses zero busy timeout. This is test-local scheduling and instrumentation, not a production busy-timeout or lease change.

Every begin_reader call is covered by a try/finally that sets release and joins the thread. Reader BaseException is returned in errors and explicitly asserted by the main test. The 10-second Event/join bounds are scheduling/cleanup failure bounds; the test makes no native 30-second timing, performance, or CI-cause inference. The old completed result is compared in full except current_review_policy, and the refreshed outer/nested policy and detached DTO validation are asserted in the test source. These assertions were read, not executed by this reviewer.

## Limits and residual scope

No actionable P1/P2 remains in the reviewed supported paths. The earlier baseline-risk-v1 P1 was the hypothetical design with deferred-only reads and no fresh gate; the existing baseline IMMEDIATE transaction was not claimed defective, and the actual candidate now contains the necessary gate.

Frozen allocation/submission and published revision immutability remain required product invariants. The gate does not support replacing those bindings in place. If such mutation is added later, old prepared bindings would need explicit rejection rather than rebinding. No such product mutation was added in this delta.

Authority is linearized by the fresh IMMEDIATE policy transaction. The lock ends before model copying and HTTP serialization, just as baseline transaction release preceded HTTP output; this review does not claim writer serialization through the final network byte. The gate still uses the original request identity and existing authorization semantics. Plain DEFERRED is not an SQLite query-only enforcement mode, so the finite call-chain audit and test-source authorizer assertion are the present evidence for absence of domain writes; runtime enforcement was not independently executed.

Runtime, SQLite/WAL execution, RED/GREEN, unit, integration, native browser, build, network/host/profile/resource/model/key probes, remote publication: NOT_RUN by this reviewer. Owner execution reports are separate and are not promoted to independent test qualification here. Original public CI cause remains outside this static result.
