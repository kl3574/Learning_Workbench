Bounded independent source publication check

HEAD `d78c4d159a2831f7d5e1721a9a466ec5b3e66421` against public baseline `1e7ad7a8656c0dc8373d4181fa3002f385ed1847`. Norm: PRODUCT_DESIGN v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`; focus §20.17.1.1/.1.2/.5/.7/.8.

P1: 0. P2: 0. No source publication blocker found in this delegated scope. Production qualification remains unavailable; physical and runtime/source proof remain NOT_RUN.

- **default_registration: PASS** — Normal create_app composition still instantiates an empty ProofRegistry for both ordinary Provider and Codex. ProofRegistry defaults to an empty CodexProofRegistry; text proof registration is separate from Codex. No automatic production/model registration is introduced.
  Evidence: services/api/app/main.py:97-104,113-123,151-166; services/api/app/application/provider_budget.py:88-96,121-124,131-140,176-190; services/api/app/application/provider_codex_profile.py:286-323,325-347.

- **default_executor: PASS** — codex_executor defaults to None and is passed unchanged to CodexTurnWorker. available requires a non-None executor; dispatch rejects unavailable execution. Added Broker methods do not instantiate or replace an executor.
  Evidence: services/api/app/main.py:97-104,164-166; services/api/app/application/codex_turn_worker.py:56-74,185-193,279-284,309-321.

- **closed_live_identity: PASS** — The new callback owner only exposes context for exact SyntheticCodexExecutor. bind and send require the same current callback tuple and thread plus active original owner/lease. BrokerMapping is synthetic_peer_only, production_qualified uses FalseOnly, upstream_turn_id has a synthetic-turn prefix. Normal default composition provides no callback/live transport.
  Evidence: services/api/app/application/codex_turn_worker.py:68-74,279-292,309-321; services/api/app/application/codex_broker_control.py:34-39,60-94,107-126,159-190; services/api/app/application/codex_broker_control_models.py:12-28.

- **schema_and_synthetic_scope: PASS** — Offline interrupt source construction is not used to install a ProofRegistry registration or executor in these blobs. Broker controls preserve observations and control-close facts; empty or paired frames do not establish local terminal proof. Synthetic runtime/proofs explicitly use synthetic protocol/version/model scopes and do not supply production qualification.
  Evidence: services/api/app/application/codex_broker_control.py:1-5,35-39,167-208; services/api/app/application/codex_broker_control_models.py:1-15; services/api/app/application/provider_codex_profile.py:1-11,91-99,172-198,242-273,286-347; services/api/app/application/codex_turn_worker.py:290-305,342-368.

- **capability_service_scope: PASS** — CodexCapabilitiesService remains an authenticated read/model-validation boundary, with no proof registry mutation, executor registration, Broker binding, or upstream dispatch in this service. Main/capabilities/default registry/profile blobs are unchanged according to coordinator cached CHANGED_PATHS. Product flag values inside LocalCodexProbe/DTO are outside this delegated read scope.
  Evidence: services/api/app/application/codex_capabilities.py:1-37; services/api/app/main.py:256-257.

Read manifest

| Fixed path | Commit | Git blob | Bytes | SHA256 |
|---|---|---|---:|---|
| PRODUCT_DESIGN.md | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | a1de002ac8d40f58522121bcc1c8ccc888fe74ff | 520415 | b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec |
| services/api/app/main.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | 7b97e55482db2aa3157194ee6b4e59db6f56c8c2 | 17756 | 2aa687bbefc66aa7b6e917cd8c2c04fd5af950039044b8405601c290120f60ca |
| services/api/app/application/codex_capabilities.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | 6babc689d2646591cafa27797eefa9bf9d262ff5 | 1574 | 060095c35a3df263a2ccb1337abc714894eecf919825c2402670af836d9db9ba |
| services/api/app/application/codex_turn_worker.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | 8d15014cf77447c310990abfe1ed8c2f57737533 | 20740 | 0d8399681b1534522b17b7664864ac7676ffca64f748984b3790d72b23dabfd0 |
| services/api/app/application/codex_broker_control.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | 2aa1e5158bf8de6ce100c98b516394baf5f56559 | 12463 | 9ac8918be47faa874224bcc824a06a7ca4a999f618952a847b6a8915a2ecee36 |
| services/api/app/application/codex_broker_control_models.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | b0e917668de786bba2127aae8958f737aca761b1 | 3266 | eef2af12fabef02ceefa3dd0bcf8ca4a34be6a8113bcfa52b16563b493c2e2ab |
| services/api/app/application/provider_budget.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | b189420bde9329596f6194643383af3c4fc8c7d6 | 14766 | 5e2ab910c41e8cb734677a206abafeb8ef663e7a4c523f6b145edaf34f8236f8 |
| services/api/app/application/provider_codex_profile.py | d78c4d159a2831f7d5e1721a9a466ec5b3e66421 | 9062ee2a86af5c11be768e341d8b44efae5e3e9f | 20658 | 5073e93d7066d7988d1fce0f83fa4b190d06ca7171e5b6c3948ce70d7ff934c4 |
| services/api/app/application/codex_turn_worker.py | 1e7ad7a8656c0dc8373d4181fa3002f385ed1847 | a268ea41b14bea57a644ca3a33c279afc32fd1ca | 19506 | a1f1e467e8c33716bcdecc14d043beaf52e0e149721dd0816f4ed0c0297bf496 |

Scope and missing evidence

- This is an independent bounded source-publication check, not comprehensive M6.3/AC-21 acceptance or a release/publication authorization.
- No tests, application imports/runtime, Codex CLI/model invocation, live upstream ID probe, network/API, environment/credential/DB/ZIP/private profile/payload reads, worktree source reads, git ls-tree repetition, canonical edits, or remote actions were performed.
- Physical binary/deployment closure, actual full model request byte proof, enforced isolation/resources, live response/timing, controlled process-stop/filesystem state, real import/publication acceptance, and source physical identity proof remain NOT_RUN/unavailable in this check.
- LocalCodexProbe, DTO alias definitions, Broker repository, interrupt source reader/decoder, bootstrap implementation, and transport implementation were not reviewed; their correctness cannot be inferred from this report.
- Broker upstream_thread_id is copied from the private original bootstrap outcome and is not constrained to a synthetic-prefixed thread string here. The claim is only that default/exact-synthetic callback gates do not open a normal production live-ID transport; this report is not a real identity proof or proof against arbitrary trusted Python composition.
- No test/synthetic result or schema availability is accepted as production execution/input-proof qualification.
