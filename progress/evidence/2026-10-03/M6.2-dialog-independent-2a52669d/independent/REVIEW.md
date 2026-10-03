# Independent review: Dialog gestures and synchronous Content form guard

Verdict: no remaining confirmed blocker within the reviewed three-commit scope. Both Standards and Spec axes were performed by this independent reviewer; this is not a claim of two parallel sub-agent audits. Root explicitly reassigned the potential second reviewer to its evidence audit.

## Source and scope

Independent clean detached tree: `$HOME/.cache/learning-workbench-acceptance/m62-dialog-pointer-independent-oct03`.

- `52121ca4f493ab0e2667d5f228d93ce00ad3c938`: Dialog gesture boundary and component/native tests, parent `0b885ec31bafbd6f64a83108b4fc491a8179b28a`.
- `b3580e975874474ed53b89fb85c60fb868533b29`: native test separates ordinary auxiliary closing from Content owner safety confirmation.
- `2a52669d484562109c19cfa8c4051c8bedcb9409`: Shell synchronously checks the existing Content form owner's pending boolean, plus a permanent controlled native regression.

Read the complete cumulative five-file diff and surrounding Dialog/Shell/AuthoringPanel/ContentImpactsPanel/useContentImpacts/formMemory paths. Sole spec v3.0.13 SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`, unchanged. Relevant preservation rules: PRODUCT_DESIGN.md:247, §20.8 at :1146, §20.13 at :1240. This narrow repair is authorized by the explicit root gesture/unsaved-protection instruction; it adds no DTO, route, replay permission, storage format or quality approval.

## Standards

No documented-standard violation or concrete maintainability blocker found. The gesture state is local to Dialog, retains a pointer identifier and one consumed release flag, and does not replace caller closing decisions. Shell uses an existing named owner boolean (`formsPending`), rather than reading private form contents or duplicating storage semantics. The existing compact Shell guard chain is not expanded into unrelated refactoring. No generated/spec/backend/remote change.

## Spec and state boundaries

The Dialog only requests backdrop close after primary button-0 down and up from the same pointer both target the dialog outside its actual box, followed by the matching click; click consumes the pending gesture once. Content-origin gestures, changed layout under a connected button, cancelled/different/secondary pointers, and an inside-box captured release do not grant backdrop intent. Explicit close button and Escape still use the original callback and parent guard. Focus trap and opener restoration remain unchanged.

The Content owner retains the exact adopted basis synchronously before the form can render. The old close check trusted passive propagation through ContentImpactsPanel -> AuthoringPanel -> Shell, allowing a close while that chain lagged. The final Shell close branch checks `pendingImpactForms(workspaceId)` synchronously in addition to every original dirty/safe guard. That public owner function returns only whether this workspace contains pending form entries; it does not return actor handles, session secrets, words or basis. It therefore remains a safe existence check for another actor, does not make old payload readable, and cannot enable replay. Explicit discard still follows the original explicit confirmation path and clears only that workspace's form owner. Existing busy/ACK/Review protections are retained.

The permanent regression uses actual API/React/native DOM and a one-shot MutationObserver: after the real adopt renders the actual form, it invokes the real close button exactly once before passive state propagation. This is an explicitly labelled programmatic DOM click, not a trusted human pointer claim. It neither patches product scheduling nor adds waits/retries. Returning from the guard retains the exact target ID/SHA, allows editing, and explicit confirmed discard closes and leaves no recoverable form on reopening, with zero Content decision POSTs.

## Actual independent results

| Stage | Actual result | Bound source and meaning |
| --- | --- | --- |
| dependencies | PASS, audit 0 | Own offline pinned node_modules; no shared mutable dependencies |
| focused-521 | 54 PASS / 5 files, 3.06 s | Fixed 521; 12 Dialog component + 42 existing owner cases; 1281 tracked non-progress inputs unchanged |
| native-521 | 1 FAIL, 15.3 s | Fixed 521, original native test; primary layout assertion passed. Later ordinary Content close expected no dialog, but existing confirmation guard appeared. Original log/PNG/context retained |
| native-guard-red-b358 | 1 FAIL, 15.3 s | Independent b358 + exact future regression file; actual form connected, close button found, one programmatic close, guard absent; 1282 inputs unchanged |
| focused-final-2a | 54 PASS / 5 files, 2.86 s | Final clean 2a; 1282 tracked non-progress inputs unchanged |
| strict-final-2a | PASS | Final `tsc --noEmit --noUnusedLocals --noUnusedParameters`; 1282 inputs unchanged |
| native-final-2a | 2 PASS, 21.1 s | Same guard probe 10.3 s, final physical layout/plain closing 10.4 s; 1282 tracked non-progress inputs unchanged |

Guard probe SHA256 is identical in independent RED and GREEN: `fdfb1b45a22f7a109a6a2fa9f4c7dfd48adcb22c6e7661166f3d3ab5fd5d09ff`. The original dependent native FAIL is not changed to PASS: b358 changed only the test's cleanup boundary to respect an observable existing Content guard and moved strict ordinary backdrop/Escape/close checks to an auxiliary command dialog without business-owner guards. The main real-layout assertion, unchanged button-node identity, exact stationary coordinates and actual Content read remain. The separate form regression strictly requires a guard when an adopted form exists.

Existing focused cases also independently passed different-same-workspace actor inability to extract forms, safe existence hints, workspace isolation, component removal retention, explicit discard leaving original commands intact, fresh original-session recovery, Policy pauses and changed-basis preservation (`formRecovery.test.tsx:41-87`). The new synchronous guard does not change these owner operations.

The author's final physical layout probe was separately read against its before/after manifests: `native-controls-boundary-red` and `native-controls-boundary-green` use identical test SHA `3dea8370cff25ac20171f002b36dc48d9cb31042649592d03e3773f03ac652eb`, identical Shell bytes, and only old/new Controls bytes differ. This is an audited author result, separate from this reviewer's actual executions above.

## Limitations and provenance

The adjacent Dialog gesture and form-confirmation defects are separate from the historical Content impacts full-gate failure. This review does not establish that historical failure's unique cause, reinterpret teardown screenshots as failure-time traces, or change the original complete-gate FAIL status. No complete Web/native/Python gate or build is claimed here; root retains combined-gate responsibility. No provider/model/remote action occurred; synthetic software flow is not academic/numeric approval.

The old form guard evidence proves that a panel could unload without the expected confirmation, not that the module-owned form words were deleted. Existing module memory and beforeunload protection remain. Original reviewer native FAIL, old-Shell guard RED, owner early harness failures, and diagnostic timing limits are preserved rather than hidden by reruns.

All reviewer source mutations were limited to adding a byte-identical private regression file in its own review tree for the RED stage, then preserving it privately before fast-forwarding to the final commit where that file is tracked. Author/root/frozen trees were not modified or used as execution directories. Native execution used random RestartRuntime ports, private short TMPDIR, and webServer undefined. New numeric JSON contains only synthetic gesture booleans/counts; no headers or credentials were emitted.
