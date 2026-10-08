# M6.3 production-profile gap: independent bounded source review

Current production admission is BLOCKED in the inspected composition. The required genuine App Server serializer/checker, private profile/receipt versions and qualified executor are absent local implementations. Separately, their actual-model and physical-boundary qualification inputs remain uninspected. This is not a credential blocker: the user already supplied DeepSeek credentials and authorized agent testing. No renewed account/fee approval is requested here.

Identity: canonical m62-public-safe-oct02; HEAD bf5d2df4e7ee5156993169cdd9610fa014bdae4f; sole norm PRODUCT_DESIGN.md v3.0.15, SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. Sections 20.5 and 20.17 were read fully. Only this new private report directory was written.

## Concrete source boundary

| Inspected code | Finding |
| --- | --- |
| provider_budget.py:88-124 | ProofRegistry defaults empty and exposes separate .codex. Ordinary InputProof binds text-request-v2/text shape (69-70, 110); a Responses/text proof cannot become an App Server proof. |
| provider_codex_profile.py:91-108, 172-215, 286-335 | Runtime/proof versions are synthetic-only; the registry accepts only SyntheticCodexProof, with explicit loopback and synthetic model names. Widening these literals or reinterpreting historical v1 bytes would not implement a production profile. |
| provider_codex_profile.py:242-273, 337-399 | prepare serializes SyntheticCompleteRequest and counts one complete request octet per peer token, or rounds up to eight. This rule applies only to the synthetic peer language. Envelope/resource constants do not prove actual model formatting or physical controls. |
| provider_codex_execution.py:34-79, 89-134, 173-229 | Request/result decoders and consistency rules are synthetic. The gate enforces its exact bytes, destination, output bound and one transport entry. Its own documentation (1-9) disclaims forced wall/CPU/memory/process control of a blocking callable. |
| codex_turn_worker.py:35-73, 171-238, 267-340 | A trusted executor port and durable claim/start/_guard exist. Control callbacks and artifact stop authority require exactly SyntheticCodexExecutor. Injecting another executor alone cannot acquire real control/tool/artifact authority. |
| main.py:97-104, 153-166 | Trusted composition accepts codex_proofs and codex_executor; normal defaults are empty ProofRegistry() and None. HTTP/environment/key data are not proof installation paths. |

Scoped test sources assert empty-registry refusal, changed-byte/config rejection and one synthetic request. They were NOT_RUN in this audit. Any previous synthetic PASS remains confined to its pinned source/commands/peer, and cannot establish actual model input proof, physical limits, CLI decline zero-action or content quality.

## Earliest meaningful local implementation and why it is not selectable yet

The earliest genuine code component is an offline deterministic final-request builder/checker for one fixed reviewed App Server version: freeze_complete_request(frozen messages, selected history, evidence, tools, configuration, runtime closure, output cap) -> immutable raw bytes, and check_complete_request(bytes, model-version basis) -> local_exact/local_upper_bound or a closed rejection. Its implementation must emit the actual final model-request shape rather than turn/start or the synthetic envelope. It can be implemented and tested locally without executing a CLI or model once the fixed genuine request-construction source and model basis are available.

The allowed five implementation files contain no genuine request serializer, no genuine final request shape, and no actual-model full-format count basis. The sole norm expressly says the recorded public schema is insufficient. Therefore this narrow review cannot select a concrete real serializer/checker implementation from its inputs. Inventing a request shape, registering a named object, adding a Protocol, relabeling the synthetic gate or factoring its already-present comparator would be scaffolding or sham proof, not the requested production step. No such step was implemented or counted as progress.

This does not move locally owed code into an external blocker. The following are local implementation debts once the target package is pinned:

- A separately versioned genuine private profile/proof and complete-request serializer/checker, through existing Provider-owned freeze/current/prepare/verify.
- A separately versioned genuine bounded protocol/terminal decoder and immutable receipt; actual provider usage must not inherit synthetic byte-token equality.
- A genuine CodexTurnExecutor implementation routing every actual request through the qualified pre-byte boundary and existing mandatory _guard.
- Actual bound callback/interrupt/operation and reliable stopped-writer/artifact integration through their owners. Those owner implementations are outside this narrow read allowlist.

## Exact missing qualification inputs

1. Fixed genuine request-construction package. Supply the reviewed immutable actual CLI/adapter version and final-request construction source, including every template, selected history item, tool definition, file material, implicit wrapper and default. The bytes must be obtainable offline before sending; resume must exclude unselected history/directory content. A captured first request, turn/start JSON, schema, usage or tokenizer alone is insufficient. No external package locations were searched.

2. Actual-model complete-input proof basis. Supply actual version or explicit alias-version coverage; complete format/tokenizer/counting rules; supported request shape; enforceable maximum output; shared-context/capacity rules; immutable evidence/checker identity; validity and invalidity conditions. Bind endpoint policy, normalized scheme/host/effective port/base path and final path under the same local parsing rules, plus configuration/secret version. An evidence hash, byte count, fixed spare margin or ordinary text proof cannot substitute. The genuine local implementation must execute these checks, not store a checklist.

3. Fixed enforceable runtime/control architecture and qualification package. Supply binary/deployment dependencies, strict complete protocol/reference closure, frozen configuration/environment/directories/session mapping, and actual initialize/resume/turn request definitions, separate from bootstrap. Every possible model request must reach the same immutable-byte comparator before any outgoing byte; direct egress, retry, redirect, hidden auxiliary request and command/tool/file networking must be impossible within the accepted deployment. Actual enforcement is not supplied by the existing trusted Python transport callable. This audit did not rediscover or inspect host security facilities.

4. Complete runtime and operation-stop evidence. The deployed implementation must enforce wall <=300 seconds including human wait, cumulative CPU <=60 seconds, memory <=2 GiB, artifact total and each file <=16 MiB, FD <=128, processes <=16, core=0, and combined stdout/stderr <=16 MiB. It must bind exact callback/instance/operation, permit one precise approve_once action, establish no action on decline/expiry/unsupported callback, issue at most one bound interrupt, and provide reliable stopped-process/writer facts before artifact collection. A declared constant or exit=0 is insufficient. If any limit/boundary cannot be enforced, the whole profile stays unavailable.

Credentials/testing authority do not supply items 1-4. Their existence outside these source files was NOT_INSPECTED; no absence claim about unsearched external artifacts is made. Later actual-model acceptance must remain separate from these proof/runtime checks, synthetic PASS, CI and mathematical/source/teaching review.

## Exact trusted implementation ports after inputs arrive

Provider owns the proof installation. In provider_codex_profile.py, introduce an independently versioned genuine private decoder/registration implementing freeze/current/prepare/verify; retain all synthetic v1 decoders and original hashes/ACK bytes. Neither InputProof's text shape nor the synthetic byte checker is admissible for the genuine profile.

In provider_codex_execution.py, implement genuine raw-request and bounded original-terminal decoding. In codex_turn_worker.py, implement CodexTurnExecutor.available/execute: available is true only for the current qualified package, and execute must bind PreparedCodexRequest.body, endpoint, output cap and receipt to that package. Call existing _guard immediately before the qualified boundary releases those exact bytes. Keep _claim/record_start as the prior durable linearization point; preserve unknown outcomes and forbid retries.

The worker's existing type restrictions are deliberate authority limits: replacing available() or injecting an executor at main.create_app(codex_proofs=..., codex_executor=...) cannot establish callback or stopped-artifact ownership. Those actual owner ports require their own implementation/review. Defaults remain unavailable until all contract requirements are implemented and verified.

## Audit status and exclusions

- PASS_STATIC_ONLY: canonical HEAD/norm verified; requested five implementation files read; fail-closed defaults and synthetic boundaries identified.
- BLOCKED_CURRENT_COMPOSITION: genuine production admission/runtime has no installed source implementation/registration.
- NOT_RUN: tests, CI, actual CLI/App Server/model, network, browser, physical processes/tools, host/resource qualification and content-quality review.
- No rejected host/security/ptrace/process_vm probes were restarted, renamed, delegated or replaced. No host/process/profile/secret scans, DeepSeek key handling, source/index/canonical/GitHub edits, or normative changes occurred. Root owns the original CI watcher and progress evidence.
