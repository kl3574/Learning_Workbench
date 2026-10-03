# Tutor snapshot validation work

This change removes repeated validation of the same owned Run within one synchronous repository read. It does not close the historical CI failure or claim its unique cause. Sole specification: PRODUCT_DESIGN.md v3.0.9, SHA-256 `a6832a01966e72e5b9f63ee283ae300119446c38bcccd91beee508331ba57a98`. Implementation base: `1ad328d0d30c67030d7b62c5d712a37e9161a6aa`.

## Original failure and diagnostic boundary

Push run `36981521690`, browser job `110756908917`, had 107 PASS / 1 FAIL: the existing Tutor native case at line 195 did not show `completed` within its original 5000 ms assertion. The parallel PR run `36981528047` passed 108 cases. Artifact `11216825333` has original ZIP SHA-256 `c164d437308264479c7589929d9d32260cc09a1865d9593e1e8c60cbdcbc061d`.

The failed case's frozen browser observation remained queued, with an answer increment and grant ACK. Its separately bounded post-assertion GET returned **running**, sequence 5 / job revision 5, no Provider receipt; the synthetic server had exactly one validated request. The API observation subsequently contained Provider terminal commit return, but no Tutor terminal commit in the captured ring. Separate clock epochs cannot be subtracted. This does not establish the eventual persisted terminal state, nor prove a missed frontend terminal event. The earlier 8701 failure retains its separate UNKNOWN boundary.

The original unmodified native case passed three ordinary local baseline runs and two additional single-CPU runs. Therefore there is no local natural reproduction of the exact CI runner conditions.

## Controlled red/green loop

The private `test_owner_probe.py` runs the real Tutor worker, actual SQLite database and explicit synthetic loopback HTTP Provider, with periodic actual service `events` / `read` calls. It retains the same five-second completion check and method-boundary observations. No provider delay or artificial answer injection was added. The stress variant has eight observers, each waiting 250 ms after its completed pair of reads. These eight observers were **not observed in CI**.

| Controlled scenario | Before | After |
| --- | --- | --- |
| Eight observers, first run | 6.123 s, FAIL | 2.301 s, PASS |
| Eight observers, second run | 6.379 s, FAIL | 1.799 s, PASS |
| One source-state snapshot, actual event-history scans | 4, FAIL | 1, PASS |
| One view snapshot, actual event-history scans | 2, FAIL | 1, PASS |
| One messages snapshot, actual event-history scans | 3, FAIL | 1, PASS |

Zero, one and four observers passed before the change; the four-observer case took 2.637 s. The first eight-observer failure overlapped a separate single-CPU native experiment; the second failure ran after that experiment finished. Timings are local samples, not a CI latency guarantee. The deterministic query-count regression was run before implementation and produced 3 FAIL / 2 PASS. Its original log remains retained.

Ranked hypotheses were reported before the distinguishing measurements: repeated full owner scans; writer/scheduler contention; Provider-to-Tutor terminal tail; frontend terminal observation; diagnostic observer overhead. Reducing only repeated validation removes the controlled timeout. The smaller loop does not contain the browser observer or fixture control-file monitor, so neither is necessary for this controlled failure. Its terminal tail was a minority of the total. Exact CI CPU/lock attribution, observer overhead and frontend delivery timing remain unproven.

## Implementation boundary

Only `TutorRepository.thread`, `messages`, `view` and `source_state` delimit reuse. They are synchronous, contain no await, and finish inside the caller's original transaction. Nested reads share checked Run records only until the outer read returns; `finally` clears them after success or failure. Outside a transaction there is no reuse. A changed SQLite `total_changes` forces a fresh full check after a write on the same connection. Results are never retained across repository calls, requests, transactions or permissions.

Each encountered owned Run still passes the complete original `_load_checked` body at least once in that read. Original command receipts, hashes, events, thread revisions, messages, channels and frozen-history checks remain. AST comparison confirms that the four original read bodies and the former `_load` validation body are unchanged apart from their enclosing scope/name. Current owner authorization and per-delivery authentication remain at their original call sites. Worker, application service, HTTP/SSE, frontend, specification, generated contracts and all timeout values are unchanged.

The added tests cover multiple prior Runs, damaged history, same-connection writes, rollback, reuse of the repository after a new transaction, untransactional reads, and a write during a nested read. Another test uses actual HTTP polling while the real worker completes one synthetic Provider request, then checks exact old Run ACK replay separately from current GET, final SSE replay and zero-write repeated reads.

## Validation

- Final focused Tutor contract/integration gate: **130 PASS**, including original Policy, SSE session-change, cancellation, lease, integrity and replay cases.
- `ruff check .`: **PASS**.
- Full `mypy`: **PASS**, 212 source files.
- Original native completion case after the fix: **3 PASS**; original test bytes and its 5000 ms assertion unchanged.
- The first lint attempt exposed a fixture-import F811 in the new test; corrected before final gates, original failure log retained.
- No new remote CI run, production Provider call, model-quality acceptance or full M6.2 acceptance is claimed. Full repository Python/browser suites were not rerun by this isolated subtask; root integration owns those gates.

The private evidence directory `m62-tutor-ci-completion-evidence-oct02` retains original CI copies and hashes, every command receipt/full log, before/after manifests, exact probe sources and raw before/after measurements. No raw browser profile, database, request headers or credential material is included here.

A deterministic bound on duplicate history work would have exposed this amplification earlier. The regression measures actual SQLite scans while the existing semantic integrity suite continues to verify their contents; it does not substitute a wall-clock threshold for integrity checks.
