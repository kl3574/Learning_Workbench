# c2 push CI import-command admission diagnosis and minimal fix

Implementation: `72efe5e23162a1c6551f9570b03b3e2b57414617`, branch `fix/m62-import-policy-entry-oct02`, clean worktree `$HOME/.cache/learning-workbench-acceptance/m62-import-policy-entry-oct02`.

Historical source under diagnosis: `c2f47a2778bb6a78c73237f8bb89fb271dfedcd6`, tree `60f57b19c185f1db5c8f7bbb6c3bc5f5bab8484f`. Sole specification for this historical reproduction is the already fully read v3.0.12 PRODUCT_DESIGN.md, SHA256 `1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7`, unchanged. Current separate v3.0.13 work was not applied to this reproduction. No main/remote/generated/progress/backend changes.

## Finding

Confirmed reproducible product admission gap: the topbar import button uses `subjectLocked`, while the command palette import button was enabled with Policy still unknown. The shared command action closes the command palette, then `openAux` correctly refuses the restricted operation. When Policy later becomes known, it does not replay that rejected click. The import dialog therefore stays absent and the unchanged helper's role assertion fails after its original 5000ms.

The minimum fix adds only `disabled={command.title === '导入' && subjectLocked}` to the command-list button in `apps/web/src/workbench/Shell.tsx:240`. Other commands, the existing Policy guard at line 115, topbar behavior at line 226, session semantics, and all original test timeouts/helper assertions are unchanged. Disabled native mouse activation does not queue a later import; another explicit click is required after real permission recovery.

This is directly evidenced locally and matches the CI entry/stack/absent-dialog/retained-warning pattern. The original CI archive has no complete request timeline, so the exact timing of its initial Policy response cannot be directly reconstructed. This report does not turn the original failed CI run into PASS or claim a rerun of that remote run.

## Original CI evidence, read-only

- Push run `37007482150`, Browser job `110839059627`, actual checkout c2 above.
- Browser terminal result: 116 PASS / 1 FAIL; failure is `grading-recovery.spec.ts:57`, called helper at line 66, failing `practiceTestData.ts:26` role visibility after 5000ms. It has not yet uploaded the fixture or entered the regrade fault/recovery logic.
- Actual click path from original source: `practiceTestData.ts:23–24`, Ctrl+Shift+P → command palette → `/^导入/` button. It is neither the topbar nor a `.first()` selector.
- Failure screenshot/error context show no import dialog, topbar Policy rejection notice, and bottom UI-saved/normal-learning status.
- Artifact `11227451785`, raw ZIP SHA256 `9e053030792471e872ac7c3acbd7f0ab4e6890e26a8e3af6cb370fcaf2a2abb9`, independently read back locally. Producer has verified the archive against metadata.digest.
- Producer originals: `$HOME/.cache/learning-workbench-acceptance/m62-c2-ci-terminal-oct02/37007482150/`; extracted archive has eight files. Relevant subdirectory: `artifact-11227451785-extracted/grading-recovery-a-real-fa-8007b-t-losing-the-old-submission/`.
- Bounded copies of raw Browser log, ZIP, artifact metadata, producer diagnosis and the two relevant source files are preserved under this report's `ci-input/`. Original producer archive was not modified.

## Diagnosing-bugs feedback loop and experiments

The `diagnosing-bugs` workflow was used: establish exact red-capable symptom, preserve and minimise the admission-only path, state competing hypotheses, run controlled one-variable checks, add permanent red regression, then fix and rerun actual original behavior.

### Exact red-capable command

On original c2 product, with `probe-red-02/original-probe.ts` placed as `tests/e2e/import-policy-probe.spec.ts`:

```
TMPDIR=$HOME/.cache/ipr \
LEARNING_E2E_OUTPUT_DIR=$HOME/.cache/learning-workbench-acceptance/m62-import-policy-entry-evidence-oct02/probe-red-02-output \
bash scripts/node.sh node apps/web/node_modules/@playwright/test/cli.js test \
  --config $HOME/.cache/learning-workbench-acceptance/m62-import-policy-entry-evidence-oct02/playwright.config.ts \
  import-policy-probe.spec.ts --workers=1
```

Actual result: FAIL in 7.8s at the unchanged `practiceTestData.ts:26` assertion, same role locator and 5000ms as CI. The harness authenticated an actual private runtime, reloaded, allowed the initial session-auth response, then held one later real 200 Policy response. Response facts were learner / independent=null / open_book=null; no fake Policy was injected. UI saved was visible while topbar import was disabled. The original helper clicked the enabled command entry; the real guard rejected it. The held response was then released before the original role assertion ended: normal Policy/topbar readiness returned, but dialog count stayed zero. Product inputs were unchanged (1239 inputs).

The reproduction is bounded before upload/grading; the original `originalAssessmentPackage('gradingrecover')` and unchanged helper are retained to bind the failing call site. The sole causally necessary delayed boundary is Shell Policy, not grading, worker speed, or fixture content.

### Competing hypotheses and observations

| Hypothesis | Prediction | Actual result |
|---|---|---|
| Command entry lacks Policy readiness protection | Unknown Policy permits a command click which is refused; releasing before a new explicit invocation permits import | Confirmed by exact red probe, permanent disabled regression, and same-runtime fresh original helper success |
| Command action retains a stale locked closure after Policy recovery | A fresh command invocation would still reject after Policy is known | Rejected: the same runtime completed the full unchanged helper on a new explicit invocation after release; command definitions are rebuilt each render |
| ImportWorkflow's own permission read is the source of this absent-dialog symptom | Import dialog would mount but show a paused role/content state | Does not match target reproduction: dialog remains absent after guard rejection; fresh invocation completed actual upload/worker/commit/role reads. The first incorrectly placed probe did show this different state and was excluded |

`policy-controls` deliberately retained the original expected 5s failure, proved no automatic replay, then made a second explicit call to the same original helper. That case PASSed in 10.2s with one held real response and actual import commit. It provides the release-before-next-click comparison without changing source or timeouts.

The other planned `before_click` control in the same group failed during `RestartRuntime.startApi` readiness, before browser/admission behavior. Uvicorn had logged listening but the readiness helper failed; the cause was not determined here. Group status remains **1 PASS / 1 setup FAIL**, not a product-regression verdict and not silently rerun until green. Its original log/error context remain.

## Regression and exact fix

Permanent new `tests/e2e/import-command-admission.spec.ts` has two actual native cases:

1. UI saved while real Policy response is held: topbar and command import must both be disabled. A real mouse click on the disabled button must keep the palette and issue no import POST. Releasing Policy must not automatically admit import. A subsequent explicit invocation through the unchanged full original fixture/helper must upload/preview/commit successfully.
2. An actual UI-created independent attempt: both import entries stay disabled, safe shortcut help stays available, and a native mouse click cannot open import. Only after actual explicit abandon and another command click can the dialog's real role appear. Final actual attempt is abandoned/not_graded.

Before fix, the first permanent regression FAILed in 7.7s: expected disabled, received enabled, with original 5000ms assertion timeout (`regression-red`). The test bytes are preserved as `regression-red/original-test.ts` and are identical to the final test. After the one-condition fix, both cases PASS.

Original fixture/helper assertions remain byte-identical to the CI archived sources:

- `tests/e2e/practiceTestData.ts`: SHA256 `9d9535bc90242fbab8188f8c6d7f3dc9469edfbeed8bc6d7c4216142959d3604`.
- `tests/e2e/grading-recovery.spec.ts`: SHA256 `73d2ab86b39940911ae6197102ec9c3e23131447c5a56d7222c9a23e51e4369e`.

## Final validation

The two-file implementation/test delta was frozen before these gates. `native-fixed`, `focused-fixed`, and `lint-fixed` ran before the commit was created; all captured input bytes match the final Git commit exactly. `fixed-build` ran on clean final commit. `fixed-readback.json` makes this distinction explicit. Each gate captured 1239 inputs before/after, all unchanged; original command, exit, timestamps, HEAD/status and log/source SHA are in the stage receipt.

| Stage | Exact command suffix after capture.py | Result |
|---|---|---|
| native-fixed | `bash scripts/node.sh node apps/web/node_modules/@playwright/test/cli.js test --config <evidence>/playwright.config.ts import-command-admission.spec.ts grading-recovery.spec.ts import-admission.spec.ts:65 --workers=1` | PASS, 4 cases / 31.8s |
| focused-fixed | `bash scripts/node.sh npm --prefix apps/web test -- src/workbench src/features/imports src/features/assessment` | PASS, 107 tests / 16 files |
| lint-fixed | `bash scripts/node.sh npm --prefix apps/web run lint` | PASS, strict TypeScript/no-unused |
| fixed-build | `bash scripts/node.sh npm --prefix apps/web run build` | PASS, TypeScript + Vite, 834 modules |

The native cases were: original unchanged full grading recovery (9.1s), existing actual independent Policy retaining an open import file/selection (10.3s), new unknown-Policy command admission (5.8s), and new independent-attempt command restriction (6.2s). The original grading case's private synthetic DB fault/recovery mechanism was run unchanged; no test-only public endpoint was added.

Native used private short TMPDIR `$HOME/.cache/ipr`, private config `webServer:undefined`, actual RestartRuntime random local ports, private SQLite/browser profiles, and own `npm ci --ignore-scripts` dependencies. No default 5173/8765 use, Provider call, environment enumeration, credential logging, or remote operation. Existing source fixtures only; no new private answers or assessment semantics.

## Preserved unsuccessful stages

- `probe-red`: first probe held the wrong stage (bootstrap already supplied Shell's usable response). Import dialog opened and its own permission read was held; topbar was enabled. The expected Shell rejection was absent. This is a diagnostic-harness mismatch, not target reproduction. Original test, raw log, screenshot/context and facts are retained.
- `probe-red-02`: exact target failure described above, genuine original helper role timeout. Product unchanged.
- `policy-controls`: 1 PASS / 1 pre-browser readiness setup FAIL, retained without converting the group to PASS.
- `regression-red`: precise permanent admission assertion fails on original source, retained unchanged alongside final green case.

Private probes were moved under `private-probes/`, outside collected tests. No production debug instrumentation was added. `source-binding.json`, `change.patch`, and `source.tar` preserve the final two-file delta. `MANIFEST.json` hashes every local evidence file; raw native facts and original grading recovery artifact are under `native-fixed-output/`.

## Handoff and limits

Independent review requested of the one-line Shell admission change and the new native cases. Parent review/integration and a future remote CI rerun are outside these local PASS claims. The separate PR `review-form-memory` failure was not investigated or changed.

The missing prevention was coverage of the alternate command-palette entry: existing actual `import-admission` tests protected the topbar. The new regression covers the alternate call site with real Policy hold/release, rather than waiting longer for a dialog that was never admitted. Other menu behavior is deliberately not inferred or broadened by this fix.
