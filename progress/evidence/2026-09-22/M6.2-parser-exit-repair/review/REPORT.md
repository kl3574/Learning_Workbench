# PDF child-exit race: independent bounded review

This review reads the four-line import_worker.py change at baseline 2ab067b9d832c0aa64699a9a56e879d2ab6c6ac5 and existing diagnosis receipts. It does not execute archived helpers, tests, the parser, a Provider, or network requests. The reviewer wrote only this new cache directory. Exact files actually read are preserved under inputs/ and bound by source-pins.json. Catalog implementation was not touched.

## Finding

No blocking defect identified in the four-line change for the demonstrated interleaving. Current worker SHA-256 is 823a9c68eb26b8201cf9847e30ab620eafd8dfe23374289a777b608e797107e1; the RED baseline worker is b0bad1234bfe69f5d7e1b298699cb30e10b18eb4d788d99931fb28ed148bb09c.

At import_worker.py:167-182, the original poll(0.1) can compute False before the child sends and exits. Child liveness observed later does not imply an empty pipe. The added poll(0) tests the actual receive pipe after the child is observed dead; a ready pipe returns to the existing recv/decode branch instead of falsely reporting an empty parser exit. No result/error code is synthesized by the patch.

## Existing evidence and causal boundary

The RED and GREEN runs have identical cached runner and observer hashes. Their 947-source before/after manifests are unchanged within each run; between runs the only changed listed source is import_worker.py. Both test log hashes match the recorded receipts. The observer calls the real original poll first and preserves its False value, then delays the parent by joining the actual spawned parser. It does not replace parser output or pipe values.

- RED 02: actual poll False; same real parser exited with code 0; pipe_ready_now=True; no parent recv event; original HTTP test fails at test_document_http.py:169 because error is IMPORT_PARSE_FAILED.
- GREEN 03: same gap evidence, followed by actual_parent_recv(error, PDF_NO_EXTRACTABLE_TEXT); unchanged original HTTP test passes. The test also asserts OCR warning/locator, one terminal event, no formal content, retained original bytes and restart readback (:158-189).
- Unmodified-observer controls 01 and 04 both pass without the scheduling gate. Recorded Ruff and mypy checks in 05 pass. These are read existing receipts, not new reviewer executions.

This proves a real local race and the fix under the controlled scheduling interleaving. It does not prove that remote CI took this interleaving, does not establish failure frequency, and does not establish full-suite or remote CI success. No same-run remote CI poll/exit ledger was reviewed.

## EOF, stop, timeout and cleanup

- EOF: poll readiness can mean EOF. The next ordinary recv then raises EOFError; finally cleanup runs, and run_once still catches EOFError/OSError at :317-319 and records safe IMPORT_PARSE_FAILED. The patch does not invent a successful empty message.
- Stop: the existing _stop check at :175-176 remains before the new dead-child readiness check. The original precedence of an already-ready initial receive over stop is unchanged.
- Deadline: continue re-enters while monotonic()<deadline. No timeout is extended and no extra blocking wait is added. If the deadline expires between the recheck and next iteration, TIMEOUT remains possible even for buffered data; this is preservation of the existing deadline boundary, not a promise to drain after timeout.
- Cleanup: original terminate/join/kill/close finally path remains intact at :191-199. Empty-pipe dead child still takes generic parse failure. A true EOF does not create a busy loop because recv is attempted next.

## Remaining evidence limitation

The inspected RED/GREEN case exercises a structured parser error from a real scanned PDF. It is not an execution test of separate EOF, stop or deadline boundary cases; their preservation above is a static conclusion. Permanent scheduling-test source was still being prepared at this review point and is not yet included in this report's execution claims. A later static addendum may pin that test without changing these original snapshots.
