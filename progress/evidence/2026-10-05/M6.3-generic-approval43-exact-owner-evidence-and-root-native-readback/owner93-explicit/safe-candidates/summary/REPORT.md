# M6.3 GenericApproval UI — fixed 43c70d66

The isolated source is clean at `43c70d660d98904903bd607a4661b3b95710293e`. Review base is `412abe09c519104d9dbd2b360eed3ff4f897f829`. This owner changes 11 UI/adapter/test paths; 1511 baseline paths are unchanged. All 1522 nonprogress tracked inputs were read and matched their fixed Git objects. `FINAL_BINDING.json` gives exact paths. The sole normative source is PRODUCT_DESIGN.md v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

The slice implements a closed typed approval GET/decision adapter, independent original-command journal and actor-isolated memory, safe turn-ID form recovery, complete operation display, original decision ACK preservation, and a minimal Authoring navigation guard bridge. New commands are saved before POST. Reload sends zero automatic decision POST; only an explicit original-key/body replay repeats an unknown command. Current execution GET and original ACK remain separate. Learner/independent/open_book decline uses the exact safe approval control revision/hash without an academic detail GET. Unsupported operations cannot be approved. No backend, schema, registry, SSE, old turn journal or bootstrap wire is changed by this owner.

The root review's SAFE_DECLINE_BLOCKED_BY_PRIOR_APPROVE_COMMAND defect was reproduced and narrowly repaired. Only the decline path filters prior commands by `decline`; new approval still remains blocked by any prior command. Original approve/replay admission is unchanged. A fresh pending safe control can form a separate explicit decline with a new key, while the complete original approve command/ACK/error remains unchanged. Server CAS still resolves competing decisions.

## Final fixed checks

| Evidence | Source | Actual terminal result |
| --- | --- | --- |
| closure-full-web | 43c70d66 | 1399 PASS / 166 files, exit 0, 2026-10-04T17:07:05.933641Z |
| closure-strict | 43c70d66 | strict TypeScript, exit 0 |
| closure-build | 43c70d66 | exit 0; existing large-chunk advisory retained |
| closure-spec | 43c70d66 | exit 0; structural verification only |
| safe-decline native | 43c70d66 | actual HTTP403 counter GREEN, exit 0, 2026-10-04T17:07:46.545985Z |
| positive native | 43c70d66 | bounded controlled Chrome PASS, exit 0, 2026-10-04T17:08:19.635494Z |

Final full-Web log SHA256 is `f1b44048956562dd34973d229ef09ccfef75477d141b4763757dd090f59c4f5d`. The final positive native log SHA256 is `98a49f73bb37a65f7a2f08e75db497096c80ab1f6e687bebb434c2689eece806`; the fixed counter log is `41728cb0998392c44876ab6575ca22b0bd2852074c28d2c7e5c4481cc44ee044`. Exact commands, source/test hashes, start/terminal times, exit codes and original log hashes are in GATE_BINDINGS.json and NATIVE_BINDINGS.json. All 27 stage before/after maps match; the four native runs' before/terminal maps match, and the three successful runs also have matching after maps. The RED native did not produce an after map or a PASS receipt.

There are 40 owned tests: 24 component, 12 journal, 4 wire tests. They cover generated fetch and IndexedDB ordering, complete ACKs, independent safe controls, full inert operation text, actor/Policy changes, 412 preservation, late ACK isolation/local persistence, unknown restoration, unsupported operations, and the reverse negative that an unknown prior decline does not enable a new approve.

## Original failures and qualifications

All original files remain unchanged. Raw failed logs are private; their SHA256 and exact bounded outcomes are retained in the bindings and this report.

1. Original wire RED at `93320ca4d0414da86d8d06b8a02712a415df1c7e`: the full original command was absent from actual IndexedDB before generated-client POST, 1 FAIL. The complete same test file passed at `ea9b3c02026bb20f5b39c4e31f651c8575cf730b`.
2. Original component RED at `0b3fd676967680bce55066e36b02861b07958725`: actual safe controls rendered but learner decline was absent, 1 FAIL. The complete same test file passed at `447a1851ed28b1101b1bad325315e07a08dec2ad`.
3. Original 031 full-Web run: 1339 PASS / 1 FAIL in the old LocalTaskDocument unknown-Broker notice wait. Original file later passed 18 tests; no unique cause was established.
4. Original 031 second full-Web run: 1339 PASS / 1 FAIL in old CodexTurnPanel late-ACK notice timing. Original file later passed 34 tests. Root supplied the independently reviewed 412 combination including AA's prior race fix; a normal merge produced 9e. This does not identify a single cause for both old failures.
5. Original 9e full1394 and bounded native PASS remain valid only for their original assertions. The later root P2 was outside that coverage. The original `ERRATUM_SAFE_DECLINE.json` remains OPEN_STATIC in its original package; subsequent dynamic closure is documented here instead of rewriting it.
6. New isolated worktree preparation initially yielded while checkout was still running. Premature dependent git commands failed on index.lock; a runner failed before a source snapshot/product invocation because a tracked input was not yet checked out. No lock was removed, and no reset/restore occurred. This is NOT_RUN_PRODUCT, not a product FAIL; no complete map or raw run.log exists for it. PREFLIGHT_FAILURE.json preserves the precise limit.
7. Component counter at `29fcdd0ac2bc86ee21afa54ef966073f226b70c6`: 3 FAIL / 19 PASS, actual disabled safe-decline buttons with retained prior approve under learner/independent/open_book. Log SHA256 `4ec09c1a8a345cbfd399fda7dbc5557a7be6e9a78423060d5b8d59047e55b8ee`. The same complete test file (SHA256 `89c2082821d5ecc41c9124ec6866413e8f1e5c4ee908c3098d02b211670aa73c`) passed at production fix `11a7099d75d866f7e84fb5bafdd431c5058eb2c1`, 38 PASS across three files. Later test-only commits add unknown-approve retention and the reverse negative; final43's whole component file is not claimed byte-equal to29fc.
8. Actual native counter on original9e: real approve POST403, approval still pending/r1, prior record retained, safe decline disabled, exit1. Log SHA256 `4208b1b7e5911aefe9594bf61e837a9975dd81cd8cb0e9d1fecc46c738a41c22`. The identical native.mjs/controlled_api.py/run.py bytes pass on43: safe decline enabled, explicit new key/body from fresh safe control, complete old approve record unchanged, no new academic detail GET. Both execute one explicitly synthetic memory request and zero literal operations.

Intermediate 2d43 gates also passed; they remain separately bound, not substituted for final43. The 031 native harness was NOT_RUN after base alignment. Historical states are in QUALIFICATIONS.json.

## Native scope

The positive final run uses real Chrome, loopback HTTP owners, SQLite and browser IndexedDB. It actively loses an actual200 ACK, reloads with zero automatic decision POST, explicitly replays the original key/full body and saves the complete identical ACK. Independent GET first shows not_started; an explicit private harness release permits one pure literal memory operation, and a later GET shows completed while original ACK stays unchanged. A second turn uses an empty operation registry: approval is disabled, same actor switches to learner, safe-control-only decline is saved, and reload again sends zero decision POST.

Counts are two explicitly synthetic model-protocol memory requests and one pure literal operation. That literal result reports host_actions=0, provider_requests=0, files_written=0. This is not an actual remote Provider, Codex CLI, physical command/file operation or host-sandbox proof. Distinct-actor and independent/open_book permutations are component checks, not claims about this Chrome run. No server restart is tested here. Production registries are unchanged. This is not overall M6.3 acceptance.

Counter replay uses SOURCE_TREE equal to its command receipt cwd and SOURCE_SHA equal to its source_sha. The raw receipt contains these source values but did not separately enumerate the two environment variable names. The three counter harness files are exactly equal across RED and GREEN.

Ten selected PNGs were visually read: final positive six, original counter two, fixed counter two. They show synthetic identifiers/material, no authentication values. Captures show viewport portions of a long panel; mobile captures do not contain the entire command/ACK. DOM assertions verify full operation text and complete durable ACK. Disabled decline in the positive final learner screenshot is after its saved decline; the original counter screenshot is disabled while still pending with only prior approve. Counter GREEN screenshots show the enabled button before its explicit click.

## Evidence and safe-share boundary

The new seal fully read 1517 distinct Git blobs across 12 fixed heads; each object SHA1 and content SHA256 was verified. It also checked every recorded stage's complete input map against the matching fixed tree and the current live1522 input bytes. Source and original evidence were not rewritten. The seal does not collect runtime files.

Only explicit PUBLIC_CANDIDATES.json entries may be considered for sharing. Text candidates permit exactly `<LOCAL_HOME>` to `<LOCAL_HOME>` substitution; PNGs use original bytes. The manifest binds raw and candidate hashes and byte lengths, with full readback. Raw failure logs, private paths/fixtures, cookies, CSRF values, databases, browser profiles, cache, keys, TMPDIR contents and ZIPs are excluded. Paths appearing as text in a reviewed runner/receipt do not authorize copying their contents. Candidates are prepared for independent root review, not remotely published.

An auxiliary reader manually checked the 19 named final-success logs and native text files without reading runtime private directories or running the application. This was a content safe-share check, not independent product acceptance. Final independent Standards/Spec closure remains root-owned.
