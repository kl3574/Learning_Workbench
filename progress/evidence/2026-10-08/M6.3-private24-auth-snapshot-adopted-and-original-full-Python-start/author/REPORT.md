# Private Codex credential snapshot slice

**Bounded implementation and tests PASS; production FinalAuth/bridge INCOMPLETE; independent review PENDING.** This packet preserves actual RED/GREEN receipts and an unpublished source-only patch. It does not register a production capability or claim a real authenticated Rust request.

The fixed platform base is `cad77366ad0ffc139b12b33e0a17d3ae4efb2213`. Only `provider_codex_consents.py`, `codex_turn_worker.py` and the original dispatch integration file change. The sole specification remains PRODUCT_DESIGN v3.0.15 (`b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`), particularly §20.5 and §20.17.1.1. The reviewed read-only source audit is hash-bound in `EXTERNAL-READONLY-REFERENCES.json`.

The existing `CodexConsentsService` now obtains the actual `SecretStore.read(locator)` value in `_claim`'s existing `BEGIN IMMEDIATE` transaction, after current source/actor/consent/proof admission and before Jobs claim and `record_start`. Its private frozen, slotted, repr-disabled snapshot retains the raw value, exact immutable private locator, workspace, turn, dispatch, provider revision and config binding. Public summary hashes are factual bindings; they are not credentials or authority. Availability still performs its normal precheck, but no longer substitutes for an explicit retained value.

`run_once` retains that same snapshot in its private send-guard closure. The guard preserves existing permission, owner, lease, cancellation and deadline checks, reloads the named current configuration and private locator, then compares the actual value with the frozen value. It refuses rotation or mismatch. It does not replace the snapshot, refresh authentication, issue a new request handle or refund a start. No actual Authorization header or Rust handle is created by this Python slice. The executor Protocol, all public DTOs/generated schemas, ordinary dispatch, default empty ProofRegistry and `codex_executor=None` remain unchanged.

Actual retained checks:

| Receipt | Native result | Evidence boundary |
| --- | --- | --- |
| `final-auth-read-failure-RED-01` | exit 1, 1 FAIL | Availability explicitly True; direct read raises checked secret-unavailable; old claim returned admitted material instead of refusing. Retained old source binds that returned claim to its existing committed start path. |
| `final-auth-read-failure-GREEN-01` | exit 0, 1 PASS | Same fixture: normal refusal, direct named read, no started event, zero possible-send consumption and zero transport. |
| `final-auth-changed-value-RED-02` | exit 1, 1 FAIL | Capture-only implementation with old guard: same locator but artificial changed value yielded completed execution. |
| `final-auth-changed-value-GREEN-02` | exit 0, 1 PASS | Same fixture: failed secret-unavailable, zero actual requests, durable possible-send count 1, no retry/refund. |
| `final-auth-positive-and-rotation-03` | exit 0, 2 PASS | Snapshot already exists at real record_start; actual artificial value and owner/version/locator match; object retained, immutable, excluded from public ACK/ledger/repr. A genuine local synthetic secret-version rotation also refuses with zero send and retained start. |
| `dispatch-full-regression-04` | exit 0, 38 PASS | All 34 original parameterized dispatch cases plus 4 additions. Crash/recovery, transaction rollback, parallel workers, unknown no retry, permission loss, missing proof and existing assertions remain intact. |
| affected Ruff / Mypy / diff | all exit 0 | Three-file lint, two implementation-file type check, whitespace check only. |
| fresh private patch check/apply | both exit 0 | Applied to three fresh exact-base files; resulting bytes equal the tested candidate. |

`SOURCE-READBACK.json` proves the original dispatch AST, imports, fixtures and assertions remain unchanged after excluding only the four new test functions. It also binds unchanged neighboring owner/SecretStore/ledger/database/main/DTO/spec files and verifies canonical API source still equals the fixed base during that readback. The observed later canonical HEAD is only a readback fact; this agent performed no canonical mutation.

The private `_claim` result adds one retained snapshot; `_guard` takes it explicitly. `DIRECT-PRIVATE-CALLER-READBACK.json` and actual rg receipt enumerate every direct call in services/api and tests. Existing external fixtures use truthiness or first-three-plus-starred unpack; no exact six-element unpack or external old Codex guard call was found. The ordinary CheckedDispatch guard keeps its existing four arguments. The two external direct fixtures were read statically and are **NOT_RUN**, not claimed regression PASS.

Every execution has its actual argv, cwd, timestamps, exit, full stdout/stderr and hashes. From the second RED onward receipts also record exact before/after source hashes. The first RED has a prior retained three-file source snapshot; the first GREEN has an immediate post-run snapshot and no concurrent source edit, rather than a fabricated pre-run hash. Both failures remain visible. Source stages, private patch, final status and finite manifest are separately retained.

Full platform Python/native suites, CLI/AppServer/models, host-security probes and real user credential reads are **NOT_RUN**. The genuine Python-to-Rust request/frozen-handle bridge, qualified auth-dependent B03 facts, full production InputProof/capacity and runtime/DNS/address/TLS/resource qualification are **NOT_IMPLEMENTED** here. A private snapshot and synthetic transport test cannot establish those properties. No commit, merge, push, remote operation or progress write was performed.
