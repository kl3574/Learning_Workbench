# Fixed-source production turn diagnosis

Date: 2026-10-07. Source commit: `d78c4d159a2831f7d5e1721a9a466ec5b3e66421`.
Isolated worktree: `$HOME/.cache/learning-workbench-acceptance/production-turn-gap-oct07`.
The worktree is clean and no source, specification or progress file was changed. No new implementation commit was created.

Normative source: `$HOME/Desktop/learning/PRODUCT_DESIGN.md` v3.0.15.
SHA256: `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

## Normative requirements and exact fixed implementation

| Requirement | Normative lines | Fixed implementation facts |
| --- | --- | --- |
| Absent production complete-input proof must permit local prepare while rejecting preview/grant/start with zero transmission. | 1509-1513 | `main.py:151-166` constructs an empty `ProofRegistry()` by default and supplies no default turn executor. `codex_turn.py:317-372` saves real Job/context/owner records and returns unavailable when freeze has no registration. `provider_codex_consents.py:297-299` rejects a non-runnable preparation before its secret availability check. |
| Proof must cover complete raw final model request bytes; turn/start JSON, usage notifications and bootstrap schema are insufficient. | 1511-1513 | `provider_codex_profile.py:288-323` only admits `SyntheticCodexProof` and builds `codex-synthetic-runtime-profile-v1`. Its complete request is the synthetic peer language, not an actual App Server model request. The fixed source contains no independently qualified production complete-request producer/checker. |
| Actual turn profile freezes full binary/deployment/schema/configuration/mapping/request/history closure and enforces every resource bound. | 1519-1523 | The default `LocalCodexBootstrapRuntime` is separately constructed at `main.py:151-152`. `codex_bootstrap_runtime.py:238-270` freezes/validates the local-control profile. Its bootstrap facts cannot qualify the distinct turn limits. The production turn runtime is not registered in the fixed factory. |
| Broker must block a second model request before any external bytes and retain the first facts. | 1501-1505 | `codex_turn_worker.py:35-53` exposes a protocol and explicit synthetic executor, with no production executor implementation. Its default availability is false at `56-73`. Controlled synthetic request behavior is not evidence about actual CLI hidden requests. |
| Real control/operation/stop ownership must bind the exact executing process and original mapping. | 1499, 1523, 1861-1866 | Worker control and operation intake at `codex_turn_worker.py:309-340` require exact `SyntheticCodexExecutor` type. Artifact collection at `295-303` likewise has only that process-free stop contract. Injecting an arbitrary executor is not production callback or stopped-writer qualification. |
| Selected offline schemas do not prove hidden input, timing, interception, zero execution, resources or provenance. | 1834-1850 | `codex_turn_protocol_catalog.py:38-50` verifies all nine selected packaged original bytes. `codex_turn_protocol_models.py:1-6,144-160` explicitly marks the selected-source catalog as implemented=false. `v2/ThreadResumeParams.json:1524-1526` describes excludeTurns as response hydration control, not proof that old model input was removed. |

All source paths in the table are relative to `services/api/app/` unless a protocol JSON basename is shown.

## Existing verified boundary

Actual command:

```sh
uv run --frozen --offline pytest tests/unit/test_provider_codex_profile.py tests/unit/test_codex_turn_protocol_catalog.py tests/integration/test_codex_unavailable_preparation_closure.py -q
```

- PASS: 122 tests; 3 existing warnings; pytest elapsed 21.58s; exit 0.
- PASS scope: empty default Codex admission, explicitly synthetic complete-byte rules, fixed selected schema source integrity, real SQLite/HTTP unavailable preparation and readback, original owner binding, pure read/rollback and zero-execution seams.
- FAIL: no new failure from this bounded command; earlier complete-gate failure records are untouched and not superseded.
- NOT_RUN: full integrated gate, real App Server turn, actual model call, production InputProof, actual CLI denial/stop/hidden-request behavior, mathematical/source/pedagogy quality.
- ENV: no new host/runtime qualification was attempted. The absence of independent turn runtime evidence is recorded as an implementation/evidence gap, not a newly observed host failure.

The actual tool output and command receipt are `focused-tests.log` and `receipt.json`. Tool chunk IDs are `b2edfb` (initial) and `e6e1d9` (completion).

## Recommended next product implementation

The next production-oriented step is a distinct trusted App Server complete-request producer/checker plus constrained dispatch adapter, initially with max_tool_calls=0. Its reviewed contract must expose the complete final raw model request before consent preview, prove the local_exact/local_upper_bound count and shared-context/output bound, bind the exact registered destination/configuration/profile, compare the same immutable raw bytes before transmission, and prevent retries, redirects, auxiliary requests and a second model request. It must then compose with the existing Provider owner, unique dispatch ledger and Jobs worker using an independently verified full turn runtime and stopped-process receipt.

The current fixed sources do not supply those final-request or runtime facts. This report does not claim that the normative contract is impossible. No preparation version, static registration, synthetic peer expansion, permission flow or default admission was added. Root may assess further authorized implementation against additional reviewed source facts.
