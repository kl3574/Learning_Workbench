# Combined native gate — failed, original evidence retained

At fixed source `1fffd996e9334f7f28dcdeb970430c9aa4052ee3`, the single complete ordinary `make test-e2e` run finished with **92 passed and 9 failed, 101 cases, 10.3 minutes**. The wrapper measured 618.641838438 seconds, from 2026-09-28 00:52:39.925149 UTC to 01:02:58.566983 UTC. `make` returned 2; its log records the internal Playwright command returning Error 1. This is a failed native gate. No failed case or suite was retried.

The sole product/engineering specification remains `PRODUCT_DESIGN.md` 3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. The isolated worktree is `m62-sep28-native-gate-active`. The unmodified ordinary Playwright configuration, all test sources, default retries and original assertion/action/test timeouts were used. The actual collected count is 101, including the added diagnostic case. There was no selected-case filter or timeout override.

## Runtime and exact source

Both required ports, 8765 and 5173, were vacant before the run and vacant after normal shutdown; no unknown process was terminated. The isolated worktree linked the explicitly recorded existing Python environment, Node toolchain and web node_modules. Runtime versions were Node v24.21.0, Python 3.12.13, Google Chrome 154.0.8037.57 and the installed Playwright version recorded in `runtime.json`. The only explicit task environment override was `LEARNING_E2E_OUTPUT_DIR` pointing to this private evidence directory. No provider key was read or passed into the task environment, and the suite uses controlled local fixtures.

Before launch, all **981 engineering inputs** were verified against actual Git blobs, and the worktree was clean. Test code writes tracked UI evidence: all nine possible PNG destinations and the zoom metrics JSON were backed up before launch and separately retained after execution. The raw post-run manifest truthfully contains **five changed paths: four PNGs and the zoom metrics JSON**. The other expected output destinations produced identical bytes. There were no unexpected engineering source changes. Only those exact ten backed-up destinations were restored after the raw post-run manifest and produced bytes were saved. A separate restored snapshot equals the pre-run snapshot, and final Git status is clean. Restoration is not a claim that the raw run left all files unchanged.

## Actual failures

| Test entry | Actual failed operation | Evidence limit |
|---|---|---|
| assessment-restart.spec.ts:43 | Source line 52: exact original Markdown selection text absent; click timed out at 10 s | Failure PNG visibly shows the exact lesson with `暂时无法打开这个对象` and `Failed to fetch`; no request ledger proves an HTTP status or cancellation cause |
| assessment-submit.spec.ts:7 | Source line 16: independent-test radio absent; check timed out at 10 s | Saved failure PNG is blank; it is not a synchronous assertion-deadline snapshot |
| assessments.spec.ts:90 | assessmentTestData.ts:29: switch-to-author button click timed out at 10 s after visible/enabled/stable and scrolling | Saved failure PNG shows the already abandoned open-book test; it does not establish the click's cause |
| assessments.spec.ts:145 | Source line 164: `.practice-comparison` and the expected shared baseline text absent at 5 s | Missing comparison assertion only; no fabricated CAS result |
| authoring-groups.spec.ts:235 | Source line 254: matching POST response for the first numeric group's decline decision absent at 10 s | Two prior 1440/390 group screenshots exist. A response waiter failing does not itself prove no request was sent or that no mutation occurred |
| grading.spec.ts:66 | restartRuntime.ts:22: UI-session-saved text absent at 5 s | The log records navigation completion; it does not determine why the text remained absent |
| imports.spec.ts:111 | helpers.ts:9: UI-session-saved text absent at 5 s | Bootstrap readiness failure; no fabricated successful import |
| imports.spec.ts:311 | Source helper line 93: import-preview-ready text absent at 5 s | The retained page projection shows the ordinary route screen; no final import readiness claim |
| learning-state.spec.ts:30 | Source line 42: independent-test-running text absent at 5 s; source line 40 also raises `Route is already handled!` | Both failures retained; neither is suppressed or treated as a successful Policy proof |

All nine original `error-context.md` files and screenshots remain in `artifacts/`. `failure-details.json` extracts their actual errors and source locators. `cases.json` independently matches the 101 sequential case results. These failures are not dismissed as environmental or resource contention. Their common cause, if any, is unproven.

## Tutor observations from this actual combined run

All three original Tutor native cases passed, at 6.5 s, 14.9 s and 9.6 s. Both controlled diagnostic tests also passed; the diagnostic that deliberately preserves an original five-second assertion failure is an expected negative scenario, not an additional suite failure.

The same-Run original native artifact is `artifacts/tutor-explicit-same-Run-co-e37c7--without-upgrading-evidence/tutor-completion-diagnostic.json`, SHA-256 `b785a1f5dc3c13f141322b01a18589a713228528bdaf55e65d4e0eb506990123`. It contains **33 browser records, 10 DOM projections and an actually complete post-assertion API snapshot with 102 records**. Independent offline recomputation validated every saved DOM/source match, all frozen Node delivery boundaries, nine exact browser-span/API-request joins, and four exact validated-event/frame/send joins. The API ring contains one Provider terminal return and one Tutor terminal committed record. API and browser drop/invalid counters are zero; the API snapshot was not contended.

`tutor-native-mechanism.json` and `tutor-diagnostic-readback.json` retain those calculations and identity joins. Browser source time, API source time and Node delivery time remain separate. The API ring came from a periodic control file read after the assertion; these exact identity joins do not place API events at the earlier browser assertion deadline. This is local controlled loopback evidence, not a real vendor invocation, independent mathematical/content approval, or proof that a historical CI failure is fixed.

## Next task and evidence index

The complete native gate remains blocked by the nine actual failures. Next: triage the preserved original failures, add only evidence needed to discriminate their mechanisms, and repair confirmed defects before authorizing a new fixed-source verification run. No source repair, main-tree write, push, deployment or publication occurred in this task.

Primary evidence: `receipt.json`, `actual-git-inputs.json`, the three `inputs-*.json` manifests, `tracked-output-changes.json`, original/produced assets, `run.log`, `cases.json`, `failure-details.json`, and `artifacts/`. `run.log` SHA-256 is `573bde09580919283cf778bed18e29ff32a321ac78e93eca3151e5ae4fa6ea22` (41,495 bytes). `run.py`, `finalize.py` and `read_tutor.py` preserve the capture and recomputation procedures. `manifest.json` hashes every finalized evidence file except itself. This is a private evidence package; raw originals have not been publication-sanitized.
