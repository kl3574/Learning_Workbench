Independent bounded read-only review of Tutor generic Jobs control repair.

No remaining blocking finding in the reviewed generic GET/cancel, original ACK, terminal no-op, safe Policy control and corrupt-timestamp error-mapping scope. This is a static code review plus readback of B-owned original test evidence; D ran no product tests or browser.

Closed findings:
- The real GET/POST generic Jobs HTTP contract is JobSnapshot. Tutor now constructs that safe projection from its checked Jobs row and exact event; no thread/context/answer or provider error text is exposed. Run-specific cancel continues to return TutorRunControlView.
- Generic and Run-specific cancellation use distinct complete route/key command identities. A new command remains subject to current lifecycle/CAS; exact original replay preserves its original event revision/time/status while current GET may show a later terminal state.
- An explicit terminal cancellation is a no-op, including stale expected r-1. Replay checks the actual historical snapshot and command-time relation before accepting a terminal ACK; it no longer incorrectly interprets that no-op as a fresh transition from cancel_requested.
- Changed ACK plus recomputed checksum cannot substitute a later actual snapshot; fixed safe labels and empty result_refs/warnings/error prevent private text substitution. Missing actual user message is rejected through full owned history checks.
- Corrupt persisted command.created_at is caught narrowly as TUTOR_INTEGRITY_ERROR (409); it is not accepted or exposed as raw validation text. The last production change is only ValueError/TypeError conversion around UTC validation.

Evidence boundaries:
- Original generic HTTP 2 failures (500) -> same two cases passed. Terminal no-op separately failed (409) before repair.
- http-controls-green-04 is 34 passed / 1 failed: new test used the wrong tutor_messages primary-key name; original log remains. It is a fixture error, not an ignored product pass.
- http-final-05 is 35 passed (9 generic + 6 prior HTTP + 20 Tutor owner). The later fixture-only alias/wrapper change fixes Ruff F811; all test function ASTs remain identical, and fixture-final-09 reran 9 cases successfully.
- timestamp-red-10 is an actual 500-vs-409 failure. timestamp-green-11 uses the same final complete test bytes and passed all 10 generic cases. Old nine test function ASTs are unchanged. Final Ruff/mypy passed in B's recorded runs. The earlier 35-case result is not relabeled as a rerun on the final UTC-catch source.

Scope is not full Tutor ledger/worker/Context/Provider review, not native UI acceptance, not full-stage success and not production model readiness. The generic safe control intentionally remains available under independent/open-book subject-output restrictions, as demonstrated by the real assessment fixtures; this does not make protected Run output readable.
