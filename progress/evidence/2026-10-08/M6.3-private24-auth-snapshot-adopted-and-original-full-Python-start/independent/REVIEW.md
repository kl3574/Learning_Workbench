# Private Python auth snapshot — independent Standards/Spec review

Outcome: **0 P1 / 0 P2** for this bounded three-file change. This admits the private snapshot mechanism for normal local source integration; it does not admit production FinalAuth, InputProof or a Rust sender bridge.

Fixed input is the uncommitted private worktree at base `cad77366ad0ffc139b12b33e0a17d3ae4efb2213`, author packet `m63-final-auth-snapshot-private-oct08-21o__q60`. All 97 declared author members were independently read and matched by bytes/hash. The final three files match their live worktree, retained final copies and applied patch copies. The worktree has exactly these three changed paths. Sole normative PRODUCT_DESIGN v3.0.15 remains SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

| Final source | SHA256 |
| --- | --- |
| `services/api/app/application/provider_codex_consents.py` | `179588ad2c9eb759302d5e29b66a7ce56845253bf6f32707c2e41fbfb8404da0` |
| `services/api/app/application/codex_turn_worker.py` | `71bbfb8f22d3226e86d0213323e45086f6147c5f6c554ee2f2bbf06414d56a9b` |
| `tests/integration/test_codex_turn_dispatch_http.py` | `9207dfdc832f24297b129c412879defb558b4a196cb59453704cd095cea3b56d` |

## Standards

The entire three-file diff and affected call chain were reviewed. `_CodexAuthSnapshot` (`provider_codex_consents.py:40–53`) is private, frozen, slotted and excluded from repr. It retains the actual named SecretStore value with workspace, turn, dispatch and provider revision/config/private locator binding. No new DTO, event/schema, JSON serializer or public return consumes it. Original consents service methods, including persistent start/event construction, remain AST-exact. The database, provider repository/ledger, main defaults, public DTO, ordinary dispatch, ports, profile, spec and AGENTS remain byte-exact.

`codex_turn_worker.py:171–219` captures the snapshot at line 190 inside the same original database transaction, before `record_start` at line 212. The unchanged database transaction defaults to BEGIN IMMEDIATE and commits after the claim returns from its body, before executor invocation. Read/config/locator failure follows the existing checked refusal path before a permit or Jobs start. Existing owner/lease/proof/access/cancel/deadline checks remain in place.

The post-start guard calls `verify_auth_snapshot` (`codex_turn_worker.py:240`; `provider_codex_consents.py:274–292`). It checks owner/revision/config/locator binding and compares the current private UTF-8 value with the retained value using `hmac.compare_digest`. It does not refresh the snapshot or substitute credentials. The existing finish/unknown/recovery/consumption paths remain unchanged; refusing release after persistent start does not refund the permit or authorize retry.

## Spec and actual retained results

The change implements the named-port snapshot/order slice described by the prior read-only seam audit and PRODUCT_DESIGN §20.5/§20.17.1.1. The public registry stays empty by default and executor stays None. Synthetic prepared requests, synthetic transport counts and this Python object do not establish a genuine frozen Rust request, complete auth-dependent B03 facts, InputProof, accepted executor profile or production capability.

The reviewer did not run tests. Existing actual command records and complete stdout/stderr were independently hash/size checked. All 17 recorded author commands have actual terminal receipts. The retained exact results are:

| Author command | Actual result and source meaning |
| --- | --- |
| `final-auth-read-failure-RED-01` | exit 1, 1 failed / 34 deselected. `available=True` bypasses the old availability check; actual `_claim` returned an admitted tuple despite direct read failure. Its original implementation bytes equal base. The failure occurs at the claim assertion; subsequent ledger assertions were not reached. |
| `final-auth-read-failure-GREEN-01` | exit 0, 1 passed / 34 deselected. First recorder has no command-level source-before/after map; the prior RED map and immediate retained GREEN-after snapshot provide the accurately limited source binding. |
| `final-auth-changed-value-RED-02` | exit 1, 1 failed / 35 deselected. Capture-only source retained the old guard; same-locator artificial raw value change produced completed instead of failed. Actual pre/post source hashes agree. |
| `final-auth-changed-value-GREEN-02` | exit 0, 1 passed / 35 deselected. Same meaningful test assertion is AST-exact in the final source. |
| `final-auth-positive-and-rotation-03` | exit 0, 2 passed / 36 deselected. Same transaction/read-before-start/private repr/ACK/ledger exclusion and real fixture secret-version rotation are covered. Artificial local credentials only. |
| `dispatch-full-regression-04` | exit 0, **38 passed, 2 warnings in 58.94s**. Original full dispatch-file argv has no filter. All 34 original parameterized cases and module assertions remain AST-exact after removing the four additions. Final three hashes match command pre/post maps. |
| Ruff / Mypy / diff check / patch check and apply | actual exit 0; Mypy covers two changed application modules. Applied private patch copy matches all three final source files. |

Two other private `_claim` fixtures remain unchanged and statically compatible with the added tuple element (truthiness and first-three-plus-starred-remainder). Their actual execution is **NOT_RUN**. The ordinary dispatch `_guard` retains its original four-argument path. This review does not turn AST compatibility into a fixture PASS.

## Findings and scope

No new blocking Standards or Spec finding was identified. The prior `m63-final-auth-ledger-readonly-oct08-4bkzllzy/REPORT.md` (SHA256 `e42bcd358ac299a24faaec9964b941013c580d6ca534df100298e188170a302d`) explicitly records **no new P1/P2 against an admitted production implementation**. Its production gap is an unimplemented boundary, not a P1/P2 declared closed by this slice. Original B02 P2 and B03/engineering P3 packets are unrelated to this Python review and were not altered.

Genuine Python→Rust final request/handle bridge, same-auth qualified B03 required facts, actual final Authorization/body freezing, complete production InputProof/capacity, and resource/DNS/address/TLS/runtime qualification remain **NOT_IMPLEMENTED / NOT_ADMITTED**. Full platform Python/native gates and the two external private fixtures are **NOT_RUN in this slice**. No real key/profile read, model, CLI/AppServer, network, host probe, canonical write or remote write was performed.

The new independent checker initially exited 1 because it assumed every old receipt declared byte counts; the worktree-add receipt only declares hashes. That reviewer metadata error and original checker are retained. The corrected checker hashes every log and computes observed sizes, checks declared sizes when present, and completed actual 0 (`8e9ce2`). This did not change any source or rerun any test. Review ends after this finite seal; no test is currently running for this review.
