# Evidence applicability late ACK: independent bounded probe

Fixed source: Learning_Workbench `60fa2b8c18bbd3bbd4122df81bb798fd6d0a3dab`, sole PRODUCT_DESIGN v3.0.13 (SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`). Separate detached tree: `$HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-probe-oct02`. No tracked production changes. Original user checkout, root integration and owner trees untouched.

## Actual result

The exact same probe bytes ran twice: each **2 PASS / 2 FAIL**, exit 1, ~1 second. These are four distinct synthetic cases, not eight distinct tests. Actual React Panel and hook, strict generated HTTP client, fake IndexedDB and controlled fetch are used. No backend, external server, model, numerical runtime, environment or key reads occur in the probe. Original fixture hashes are deliberately synthetic. This is an adjacent independent recovery finding, **not a diagnosis of the full-native line-75 failure**.

- PASS: one valid ACK received with unchanged access generation is durably saved with exactly one decision POST.
- PASS: an unusable ACK response, with unchanged access generation, preserves the original command and allows an explicit second POST with byte-identical key/body to recover a valid original ACK. This control simulates the server receipt; it does not certify a live backend.
- FAIL: original command sent, actual client role-mutation notifications change generation, fresh session is learner, then the original valid ACK arrives. Durable original remains unchanged with ack=null, protected command DOM is absent, but the received ACK is absent from original-session isolated memory. Returning to the same original author with a fresh permission read presents no save-only entry. Old-generation replay stays correctly disabled. Decision POST count stays one.
- FAIL: equivalent generation change with active independent Policy produces the same result. Policy is controlled synthetic SessionResponse; the client attempt-abandon route only supplies the actual access-notification mechanism, not a real assessment lifecycle simulation.

Both failed cases record: received_ack=true, retained_original_ack=false, pending_after_ack=false, other_session_retained=0, original_role_save_available=false, old_generation_replay_disabled=true, decision_posts_before_save=1. The assertions fail on memory retention, save-only availability and final durable ACK. The non-secret original actor in the synthetic receipt is the same as the original SessionResponse; no real credential is involved.

## Cause and bounds

`useApplicability.ts:66` captures the original page-session binding. Original command persistence succeeds and memory is released at :70–71 before HTTP. The response is strictly validated against the frozen original command at :75. The changed-generation `valid(n)` return at :76 occurs **before** `memory.retain(..., session)` at :77. Therefore the already received valid ACK is discarded before either memory or persistence can preserve it. This matches the first hypothesis. An IDB write failure after retention would leave pending memory; a mismatched restoration identity would also leave pending memory but disallow retrieval. Neither matches the observed pending=false and empty original-session memory. Unchanged-generation controls use the same Panel/client/store and pass.

This is a **frontend recovery loss of an already received ACK**, not proof of server data loss, actor impersonation or authorization bypass. The durable command remains. Backend `EvidenceApplicabilityService.decide` :234–243 checks current access, workspace/actor/key/body history and returns the immutable original receipt; existing HTTP test :48–62 specifies original-key replay through restart, and decision test :124–139 specifies old receipt replay after basis change. Those backend tests were inspected, not rerun here. The current GET history can separately reveal the server decision, but the frontend deliberately does not relabel that GET as this original command ACK. Under this generation transition the UI itself does **not** offer original-key replay (`samePage`, :64,115); saying “the original is recoverable by replay” would therefore overstate the present UI capability. There is no reason to expand old-page/access replay authority to fix received-ACK retention.

## Narrow fix / independent GREEN criteria

Preserve a **strictly validated, already received** ACK under the captured original-session isolation binding before abandoning the stale callback. Leave persistence, protected rendering and all actions subject to the fresh current authorization/generation guard. Do not rebind to the currently active session, alter immutable body/key/CAS or confer cross-page/access replay. Returning to the original session and fresh allowed author Policy must expose explicit save-only recovery; that writes the original ACK to the journal and issues zero additional decision POSTs. A different session cannot save it and blocked role/Policy cannot render protected body.

A production fix is owned by the repair agent, not this reviewer. **Repair GREEN is NOT_RUN / pending a fixed owner SHA**. The two passing controls are not a repaired GREEN. The same archived `independentLateAckProbe.test.tsx` must run unchanged against the eventual fix; original RED logs remain immutable. No P1 or full-gate attribution is claimed. The bounded observed impact is unavailable local receipt recovery after a completed access transition while a valid response is in flight.

## Reproduce and evidence

Probe: `independentLateAckProbe.test.tsx` (copy under the same feature directory in a detached source tree). Dedicated external TMPDIR/config/cache; existing frozen dependency installation and Node toolchain are symlinked, not copied. No install/update was run.

```sh
TMPDIR=$HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-evidence-oct02/tmp bash scripts/node.sh node apps/web/node_modules/vitest/vitest.mjs run --config $HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-evidence-oct02/vitest.config.mjs --reporter verbose
```

Node v24.21.0, Vitest v5.0.0. `probe-red.log` and `probe-repeat-red.log` each exit 1, 2 PASS / 2 FAIL. `probe-first.log` preserves an earlier harness startup failure: invoking the non-executable scripts/node.sh directly exited 126; invoking the same script through bash resolved it. No source chmod/edit was used. All fixed source files and raw logs are bound by manifest and SHA256SUMS. Tracked `git diff --exit-code` succeeded; only this untracked independent probe exists in the review tree.
