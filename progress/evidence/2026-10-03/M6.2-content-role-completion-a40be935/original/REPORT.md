# Content impacts role-completion diagnosis

Status: controlled sequencing defect REPRODUCED and narrowly corrected. Original complete-gate historical unique cause remains CAUSE_UNRESOLVED; its 121 PASS / 1 FAIL result is preserved. No full-gate rerun is claimed here.

## Fixed source and scope

- Base: `0b885ec31bafbd6f64a83108b4fc491a8179b28a`.
- Fixed: `a40be93575830f7584986af2be23444a31752ed6`, clean independent worktree `m62-content-impacts-native-oct03`.
- Sole spec v3.0.13 SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`; unchanged.
- Only tracked change: `tests/e2e/content-impacts.spec.ts:86`, one exact existing UI role-completion assertion before closing Import. No product source, fixture, original assertion, 5-second timeout, retry, backend, generated contract, progress or remote change.
- Original test SHA256 `1adf6e01c7ebb6b00478486d626356c18e66f7726602b45b037462d29e2d7a79`, identical in 60fa and 0b. `original.spec.ts` retains it. `fixed.spec.ts` retains final test.

## Observed causal chain

The original line 86 awaited a click on the author role button and immediately closed Import. That does not await the asynchronous role request. The original line 87 can then read Content details while another page's role response is still pending, even after the server already committed author. When that role response finally reaches its originating page, shared access notification invalidates the other page's in-flight or previously read Content material. That invalidation is legitimate protection and remains unchanged.

`original-controlled-01` imported the completely unchanged original test through a private external wrapper. The wrapper held the real author response after its server commit and released it during the original line 87 detail GET. The actual GET returned 200 before release; the late access notification invalidated its owner. The exact original line 87 5-second assertion failed. Before runtime browser close the restored page still had dialog=1/open=1/detail=0. This is a detail-read invalidation, not dialog destruction.

The bounded v2 controller (`original-controller-v2.spec.ts`, SHA256 `301652d72c6ba1fb7dfa562e80697e1a5bed6720a85bd72d35162a19d06ad0b2`) is byte-identical across `original-controlled-02` RED and `original-controlled-green-01` GREEN. It observes whether Import closes while the real role response is held. The old test does close, so the controller releases at the old test's actual detail request and reproduces the same line 87 failure. The fixed test keeps Import open while waiting for the exact confirmed role; after a bounded 1000 ms hold, the controller releases the real response and the whole case passes. This timeout belongs only to controlled response scheduling; no product assertion timeout is increased. There is no retry or automatic resubmission. The fixed version's final detail=0 is expected because the original test subsequently starts the independent assessment and asserts the protected detail is hidden.

The exact role UI is not optimistic: `useImportWorkflow.ts:198-206` awaits the role POST, `api/client.ts:25-42` releases the same-page session-read fence and sends the completion access notification, `useImportWorkflow.ts:57-68,103-124` assigns auth from a fresh generation-checked session GET and marks projection readiness, and `ImportWorkflow.tsx:36-43` only renders exact `操作角色：作者` in its current, non-suspended projection. The suspended label explicitly differs by its suffix. The additional test assertion is therefore a real operation-completion boundary.

## Evidence and controls

All listed stages have actual exit codes, command/cwd/timestamp/source before-after manifests and unchanged inputs in their receipt.json.

| Stage | Actual result | Scope |
| --- | --- | --- |
| original-case-01 | 1 PASS, 30.6 s | One unchanged original case run, no controller; not reproduced |
| original-diagnostic-01 | 1 PASS, 30.6 s | Original assertions/fixture plus private safe metadata; actual role cycle and Workbench PUT412/conflict occurred, dialog stayed open |
| pointer-controlled-01 | 2 FAIL in preparation | Probe incorrectly requested author switch while already author; not a product finding; source v1 retained |
| pointer-controlled-02 | 2 PASS, 20.9 s | Stationary click and real role refresh deleting pressed button; deletion produced down(button)/up(p), no click, dialog retained |
| pointer-controlled-03 | 1 FAIL, 15.6 s | Separate adjacent gesture bug: down inside button, move outside, up generates click(dialog) and closes Dialog. Owned separately by scope agent; not a claim about historical gate cause |
| role-completion-01 | 1 PASS / 1 FAIL, 38.0 s | Real role response before read passes; after displayed read invalidates detail. Failure-time and finally markers both dialog=1/open=1/panel=1/detail=0 |
| original-controlled-01 | 1 FAIL, 36.3 s | Completely unchanged original test, exact line87 failure; unbounded-by-time controlled late release at real detail request |
| original-controlled-02 | 1 FAIL, 35.0 s | Same original test, bounded v2 controller; Import closed while actor response held |
| original-controlled-green-01 | 1 PASS, 32.7 s | Same v2 controller, only approved role-completion assertion added; Import remains open pending response |
| fixed-native-01 | 2 PASS, 1.2 min | Clean fixed commit, no controller; full Content impacts file: primary chain 31.4 s, unsubmitted form role-cycle/explicit-discard chain 38.4 s; 1279 tracked inputs unchanged |
| fixed-typecheck-01 | FAIL, harness only | Explicit Playwright index.mjs has no automatic declaration pairing; retained, no project source changed |
| fixed-typecheck-02 | PASS | Strict/no-unused targeted E2E TypeScript, exact installed declaration aliases in private type harness; no any or weakened strictness; 1279 inputs unchanged |
| npm-ci-01 | PASS | Own pinned dependencies; audit 0; no shared mutable node_modules |

## Boundaries and provenance

Original full-gate artifacts are retained in `original-failure/`. Its screenshots/error-context were collected around test teardown and lack failure-time role/pointer/owner traces. They cannot prove the original dialog was already absent at assertion time. The controlled diagnosis is reproducible and justifies the test completion boundary, but cannot establish the historical failure's unique cause.

Only fixed-route categories, timestamps, response status, author/learner enum, page labels, and DOM counts appear in new diagnostic JSON. No request/response headers, cookies, credentials, session identifiers, command bodies, or academic text are emitted into those JSON diagnostics. Actual synthetic Content/Review/human/publish/IDB/restart actions remain the existing fixture; no model or external provider is used and no academic approval is inferred.

Private probe files were moved out of the worktree before commit-bound validation. They remain in `probes/` and versioned private copies. To reproduce a wrapper stage, restore its exact recorded file under `tests/e2e/` in a fresh matching worktree; the stage receipt records the exact command. The fixed native config uses RestartRuntime random ports and webServer undefined, with short private TMPDIR. No default 5173/8765 server or root/frozen worktree was modified.

The adjacent Dialog gesture issue and its future repair have separate sources/evidence and do not replace this diagnosis. Complete native reacceptance after integration is NOT_RUN here. Complete Python, Web, build, provider, mathematical/numeric execution and remote operations are outside this one-test edit's verification scope.
