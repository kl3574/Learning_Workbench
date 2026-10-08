# FinalAuth and durable single-request seam — bounded read-only source audit

Status: **implementable bounded engineering slice; production NOT_ADMITTED; reviewer tests NOT_RUN**. The current platform already implements a real persistent Codex dispatch-start ledger and recovery control. The remaining issue is its connection to a genuinely finalized, authenticated Rust request and its restricted sender. Calling this a missing ledger would be inaccurate.

This report does not change the product contract or register a capability. No application, test, model, Codex CLI, AppServer, key read, host/security probe, source mutation or remote mutation was performed. Only fixed source files, retained source manifests and read-only local Git operations were used. Public CI terminal evidence remains separately sealed and was not modified or downloaded again.

## Fixed inputs and exact evidence

- Sole product/engineering norm: `m62-public-safe-oct02/PRODUCT_DESIGN.md`, v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. Relevant full sections §20.5 and §20.17.1.1, plus owner/one-call clauses, are line-numbered in `SPEC-EXCERPTS.txt`.
- Platform source fixed at `cad77366ad0ffc139b12b33e0a17d3ae4efb2213`; current readback was `e38b859df0cee6081f45ccbdf6bf62b3194aa40f`. Actual Git receipts prove API source unchanged between public `63403908eabec794aa1113d0d4ed467f22bae7b4` and cad, and between cad and e38. The latter has only 23 progress paths. Engineering source remains `7d7a37afb89a8b8ce13b2c4a28c5580e4cfda6ed` as parent binding; this audit's direct claim is the recorded fixed API byte comparison.
- Rust B03-r2 source: `$HOME/.cache/learning-workbench-acceptance/m63-core-resolved-producer-oct08-32gthm1b/source-B03-r2`; before manifest `7328c68eac5a325c080da04908b802a2b78d4fbd20a68ca876caa51014a42d7e`, final owner manifest `4c98b69450d5e15f18f8e848d2178d9ad579ede822f3ab9663d261c5ab236771`. Eight directly read Rust source files were independently matched to the frozen B/AC/HTTP04 before-manifest entries or the retained original a956 source. This is not a fresh validation of all 230 owner-manifest members or the entire source graph.
- Fixed upstream commit `a956835d020762cb2b570053af06f643a11c0ecc`, archive SHA256 `351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927`; original Cargo.lock SHA256 directly checked: `5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c`. No release-binary equivalence follows from source version, tests or this audit.
- `SOURCE-READBACK.json` contains the finite source inventory, paths, sizes, hashes, fixed/live matches, eight Rust binding checks and API diff facts. `receipts/` contains 23 actual read-only Git commands with argv, timestamps, native exit status, full stdout/stderr, byte counts and hashes.

## Existing authority and exact call chain

| Existing source/function | What it actually owns | What it does not supply |
| --- | --- | --- |
| `application/provider_codex_consents.py:173` `consume` | Active transaction; current actor/control, original consent, unique queued dispatch, revocation/current proof/source/expiry checks | No real network request or final auth |
| `provider_codex_consents.py:220` `admit_execution` | Historical owned graph plus current execution actor/Policy, no prior finished/start unless explicit guard mode, revocation, proof/current config/material | A returned prepared object is still factual material |
| `provider_codex_consents.py:235` `record_start` | Source lease and expiry; append unique possible-send start tied to the proposal body SHA and real execution owner | It performs no transport and creates no Rust gate |
| `application/codex_turn_worker.py:171` `_claim` | Same `Database.transaction` admits execution, claims Jobs lease, writes Provider start, independent binding and turn claim witness, verifies the owner graph | No retained secret/auth snapshot; no B03/Rust bridge |
| `infrastructure/database.py:51` `transaction` | Default `BEGIN IMMEDIATE`; commits after yielded work succeeds, otherwise rolls back | SQLite commit and physical network release are not atomic |
| `infrastructure/provider_codex_repository.py:160` `_reduce`; `:211` `append` | Reconstructed hash-linked persistent ledger rejects a second start, wrong dispatch/body, finished/revoked/expired permit; events/members/head CAS are persistent SQL writes in that transaction | It is not a physical-send callback and does not bind every independently reconstructed Arc |
| `codex_turn_worker.py:220` `_guard` | Already-started owner/lease/cancel/deadline/current permission recheck | It can run repeatedly; it is a reducing guard, not a new send grant |
| `codex_turn_worker.py:342` `recover` | Expired inactive unfinished starts converge to `CODEX_OUTCOME_UNKNOWN`; no new execution | No refund or retry |

`_claim` returns from inside the transaction context, so commit completes before `run_once:267–286` calls the executor. This is the real existing send-before-commit protection to preserve. The event count exposed by `provider_codex_repository.py:57–63` distinguishes persistent possible-send consumption from a checked receipt's actual transport count. A post-start refusal may correctly have durable count 1 and actual request count 0; neither count should be relabelled or refunded.

## Exact FinalAuth gap and reusable named ports

`CodexConsentsService` already holds `database`, the source owner, `SecretStore` and `ProofRegistry.codex` (`provider_codex_consents.py:38–41`). Its `_current:329–354` checks current provider configuration, real material, the registered proof, the config-revision private locator, backup state and `secrets.available(locator)`. `prepared_request:214–218` returns a `PreparedCodexRequest` containing body/endpoint and frozen accounting facts. It carries no retained credential or authenticated HeaderMap, and its current proof/body shape is explicitly synthetic.

`PrivateFileSecretStore.available:212–217` **does call `read(locator)` internally**. Thus the gap is not an assertion that the current chain never reads storage. Availability discards the value and does not create a stable final-auth snapshot. The final-auth path must explicitly obtain and retain the actual private value from the named `SecretStore.read` port for the same checked version.

`ProviderRepository._locator:198–218` integrity-binds a private locator to workspace, provider id, revision and config SHA. `ProviderService.save_secret:132–164` writes a new immutable secret version and appends a new provider config revision in the normal owner transaction. A proposal already binds that revision/config SHA, and the private reference resolves its secret version; no public key hash or new HTTP-supplied authority is needed. A locator, summary SHA or version label alone is not an Authorization value.

The concrete existing precedent is **ordinary** `CheckedDispatch._start:168–199`: current source/lease/consent/config/proof checks → private `SecretStore.read(locator)` → persistent `ConsentRepository.begin_dispatch` → private `_Started` with `secret` and `body` excluded from repr → commit → transport. Its `_guard:201–222` compares the current private value with the frozen value. Reuse that ownership/order discipline in the Codex owner; do not route Codex through ordinary text-request proofs, ordinary dispatch or a renamed adapter.

The existing Codex executor is synthetic (`provider_codex_execution.py:89–134` validates `SyntheticCompleteRequest`; `codex_turn_worker.py:43–54` supplies `SyntheticCodexExecutor`). Its one-use gate protects its synthetic transport. It cannot be taught production capability merely by receiving another DTO. `main.py:153–164` keeps default `ProofRegistry()` empty and `codex_executor=None`; those defaults must remain unchanged.

## Genuine Rust boundary and the smallest code slice

`core/src/responses_producer.rs:372–510` consumes resolved plain facts, constructs the real core request, resolves all body additions before AC's single `EncodedJson` encoding, and returns the real `codex_client::Request`. B03's `Resolved`, `Requirement`, getter results, expected contributor counts and `Provider` fields are completeness/shape facts. Their values are not authenticated by the helper and are not consent, InputProof or a secret-store authority.

The narrow Rust implementation can be a **private concrete function** beside this producer, for example `finalize_controlled_bearer_request(request: Request, resolved_bearer: HeaderValue, maximum: NonZeroU64) -> Result<Arc<FrozenResponsesRequest>, ...>`. It should consume the genuine already encoded request, support only an explicitly selected static bearer mode, install exactly one sensitive Authorization header, reject pre-existing/duplicate/conflicting auth and unsupported modes, and call HTTP04 `FrozenResponsesRequest::freeze` immediately. It must not reserialize or replace the body, URL, method, timeout, response cap or compression. This function produces frozen request material and a process-local send capability; it does not issue platform authority.

The full owner order is concrete:

1. In the existing Codex owner transaction, reload the proposal/current actor/source/lease/proof/config. Resolve the exact revision's private locator and obtain `SecretStore.read` as a private auth snapshot. Retain the actual value and its owner/version binding; no credential or auth HeaderMap goes to public ACKs or persisted JSON events.
2. Resolve the B03 **auth-dependent** body/header facts from that same qualified auth mode/version before building the body. Guardian credits, access programs, response/routing headers and required attestation cannot be guessed as absent or taken from an unauthenticated getter. An intentionally limited static API-key slice must reject ChatGPT/signing/refresh modes and unresolved required facts.
3. Run the actual B03 producer, finalize auth on its actual `Request`, freeze its real final headers/body, verify the current frozen proposal/proof byte binding, then write the already existing `record_start` and independent turn claim witnesses in the same transaction. Do not start a client, wait for network or send inside the transaction.
4. Only after successful commit, hand **that one frozen handle** to `ReqwestTransport::for_frozen_responses_request`. The existing post-commit guard may refuse on current rotation/revocation/lease/cancel/deadline or compare the private value; it must never refresh or substitute auth into the frozen request. A failure after persistent start does not refund the permit.

The trusted owner must create one shared frozen capability per new durable start. `admit_execution(already_started=True)` is for monitoring only. Refreezing a new Arc from the same already-started permit would escape the Arc-local latch; an internal transport integration must refuse it. Existing recovery already forbids using a started permit to claim a new execution after restart.

**Actual integration prerequisite:** there is currently no Python→B03 in-process bridge returning the real Rust frozen handle. `_claim` cannot make a Python snapshot or a synthetic `PreparedCodexRequest` equivalent to that handle. The Rust finalizer and concrete named-port auth-snapshot slice are independently implementable offline; the “freeze and ledger in the same transaction” integration is closed only once the real in-process bridge joins them. Do not use CLI dryrun/child AppServer preparation or a new empty Protocol to pretend that bridge exists. This is an explicit missing implementation, not evidence that the contract cannot be implemented.

## Why the ordinary post-commit path must be bypassed

- `codex-api/src/auth.rs:51–73`: `resolve_auth_headers` may await credential refresh; `AuthProvider::apply_auth` may mutate or replace the **whole** request. Its default extends headers after preparation.
- `endpoint/session.rs:169–207`: ordinary `stream_prepared_request` clones the prepared request for `run_with_request_telemetry`, applies auth on each attempt, and uses the provider retry policy. It explicitly directs controlled owners to their dedicated frozen transport.
- `core/src/client.rs:924–986`: ordinary client setup awaits provider/auth resolution, potentially rebuilding on credential revision changes. `:1525–1703` builds normal streaming clients and continues after unauthorized recovery. These paths cannot follow controlled finalization.
- HTTP04 `http-client/src/transport.rs:83–106` creates the restricted fresh Direct client (no proxy/redirect/retry/decompression, HTTP1, no idle pooling); `:141–154` checks the actual built reqwest request then executes its inner client without late trace/default-header injection. `FrozenResponsesRequest::claim` is a shared atomic one-use latch; it is not the persistent owner ledger or a DNS/resource/profile qualification.

## Precise old-implementation RED entry and bounded acceptance

No RED/GREEN was run by this reviewer. The following are concrete tests for the implementer, not claimed results.

**First real platform RED:** extend the existing isolated fixture in `tests/integration/test_codex_turn_dispatch_http.py`. Use its actual `queued(consent_case)` and `worker._claim(ExitStack)`. Set `owner.secrets.available` explicitly to `True`, then make the named direct `owner.secrets.read` raise a checked `PROVIDER_SECRET_UNAVAILABLE` for that exact private locator. Expect no persisted `CodexDispatchStarted`, no transport, and a retained normal refusal. The old `_claim` never obtains a final-auth value, so it can append started despite this injected inability to obtain final auth. Merely patching `read` while letting `available` also call it would produce an existing availability refusal and would **not** demonstrate this gap.

Add the matching positive test with an explicitly artificial local credential: at the real `record_start` boundary the auth snapshot must already exist, match the current provider revision/private locator, and be excluded from public ACK/ledger JSON/repr. On transaction failure the start/witness/Jobs changes roll back and no Rust sender runs. Read spies are evidence of snapshot ownership only; they do not prove the Rust request bridge.

**First actual-request Rust RED:** in the B03 producer/finalizer test module, construct the genuine B03 Request with fixed artificial auth material. Before the fix, freezing the unauthenticated request then installing Authorization changes the built header map and HTTP04 `claim` rejects it; this records the required before-freeze ordering, not an auth vulnerability in the already closed gate. A finalizer-specific rejection test must also show that an existing/conflicting or missing required auth value is not silently admitted. The GREEN path finalizes then freezes, preserves the exact original EncodedJson allocation, and validates the built reqwest headers/body without any HTTP/model request. A lower-level claim-only test cannot by itself prove that the full reqwest sender path has zero hidden writes.

The strongest integration fixture, after a real bridge exists, must pass a genuine B03 final-auth request through the actual restricted Rust transport boundary with a bounded local observer: committed start observed before the send boundary; original body allocation and exact final headers; rotation/revoke before release gives zero sends and retained consumption; two workers/clones or a new handle from the same permit cannot produce a second send; recovery never reissues the handle. It must not wrap the synthetic request/transport and call it a production proof.

Existing exact regression entry points to reuse, without weakening their assertions:

- Platform dispatch file: crash/recovery `:247`; coordinated rollback `:276`; parallel start/workers `:357`; unknown no retry `:397`; permission loss after permit with zero actual requests `:450`; production proof missing `:504`.
- `http-client/src/frozen_responses_request_tests.rs`: exact allocation `:57`; concurrent clones one claim `:199`; real transport mutation rejection including Authorization/timeout/response cap/re-encoding `:228`; new sender cannot refund shared capability `:291`; real connection failure no refund `:318`.
- Ordinary `tests/integration/test_provider_dispatch.py:240` covers changed authority/source zero dispatch; it is ownership-test precedent, not Codex qualification.

## Remaining production boundary

No new P1/P2 is asserted against an admitted production implementation, because that implementation is not present or registered. Send-before-commit, ordinary auth/retry after freezing, guessed required auth facts, or fresh capability reuse from an old permit would be blocking defects in a future integration.

Still unimplemented/unqualified: the genuine platform↔core request/handle bridge, complete real InputProof and capacity/token evidence for its whole envelope, actual final config/secret/auth-dependent facts, full AppServer secondary-call/WS/compaction closure, and accepted resource/DNS/actual-address/TLS/isolation executor profile. Fixed source compilation and process-local gate tests do not qualify the normative CLI binary or these runtime conditions. Keep production ProofRegistry empty, executor None, and `CODEX_INPUT_PROOF_UNAVAILABLE`/zero preview-grant-start as required.

Finite evidence-writer failures are preserved separately: a source-map symlink has a target rather than SHA, and the partial semantic source map omits inherited transport so comparing that file to stock was the wrong evidence basis. The successful readback uses the complete B03 before manifest for inherited/new code; no source/test assertion was changed or run.
