# M6.3 mixed interrupt/operation test static review

Fixed final `6127acdf2964efa27da639f17eccd47779f967a8`; original test `0999696b97324d6d5da95e69deffdb4b3fc68adc`; integration base `ee76a13d22728e31880ef1ac223b5f3572832893`. Sole PRODUCT_DESIGN v3.0.15. One peer, Standards and Spec considered separately. Source object hashes and scope are in SOURCE.json. Only the new 239-line integration test differs from ee76; all 1464 prior nonprogress paths remain byte-identical. No application, tests, CLI, database, browser, network or system probes were executed by this review.

## Standards

No confirmed issue. The five parameter-expanded cases share small fixture helpers and keep lifecycle assertions visible. `run_peer` rethrows assertions that the synthetic adapter could otherwise turn into protocol errors (test:48–62); actual execute call observation uses the existing current-thread code-object hook without replacing the frozen operation implementation (execution_boundaries.py:18–37). The new file performs no SQL mutation to manufacture approval/stop histories. Both commit messages include M6.3.

## Spec

No confirmed issue; oracle correction is appropriate. §20.17.4 distinguishes current Job revision from approval revision and immutable decision ACK (PRODUCT_DESIGN:1742). The actual view derives Job fields from current turn control (codex_approvals.py:63–81). Final changes only substitute current `job` and `job_revision` in the otherwise complete equality comparisons (test:88–91,100–101). Original full HTTP decision ACK bytes still compare exactly before and after finalization (86–87,102–103); approval r4, operation/result hash, decision and timestamps remain unchanged under those whole-dictionary comparisons. Interrupt ACK bytes also remain exact (104–105).

These are meaningful combined-owner paths. Fixtures create preparation, preview, consent and start through actual FastAPI HTTP and read the request through the Provider-owned port; callbacks enter actual worker receive/execute methods (generic_approval_http.py:9–29; new test:69–110). The repository writes v4 interrupt and v5 operation envelopes through its real append paths (codex_turn_repository.py:425–437). Same-session cases exercise completed operation then interrupt; pending/approved-but-unexecuted cancellation; and interrupt or Jobs cancellation followed by a new turn with a new real consent (test:113–151,154–239).

The last pair retains the old terminal control and original stop ACK while a different new turn is active, then verifies that old read/replay does not clear that new active turn (210–226). Each case checks at most one synthetic provider request; operation execution count is exactly one or zero as appropriate (93–94,134–135,228–229). Subsequent worker runs return false, reads/replays leave the complete local DB dump unchanged, and retained answer/result facts survive cancellation (97–110,137–151,230–239).

## Limits and preserved failures

This is static test review, not execution evidence or a renewed review of all merged production. Root reports original 1 FAIL / 4 PASS and final 5 PASS plus adjacent 9 PASS; those results were not rerun here and are not counted as reviewer execution. The original erroneous full-view equality and its failed run remain preserved. The correction does not weaken original ACK equality or execution-count assertions.

The fixture intentionally supplies protocol-only responses and a registered literal memory interpreter; it establishes no real CLI, host tool, resource-isolation, external interrupt or academic-quality claim. It does not add a direct persisted-version-label assertion, concurrent race, or process-restart case. Existing real owner paths select the v4/v5 encoders; this bounded test validates their combined observable lifecycle rather than exhaustively covering every integrity failure.

Disposition: Standards 0; Spec 0 confirmed findings. STATIC_REVIEW_COMPLETE. Runtime gates retain their separately attributed statuses.
