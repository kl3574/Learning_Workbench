# M6.2 Evidence applicability checked late-ACK retention

Fixed commit **93bc2ed5b64dd1bcc311e303dff76fd29575f659**, parent `60fa2b8c18bbd3bbd4122df81bb798fd6d0a3dab`; branch `fix/m62-evidence-late-ack-oct02`, tracked and untracked source tree clean. Tree: `$HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-fix-oct02`. Only three files changed: a four-line production delta plus two new regression files. Root integration, fence owner, original user checkout, canonical specification, progress and remote state were not modified.

## Behavior and scope

A valid response can arrive after a role/Policy generation change. Previously useApplicability.ts validated that ACK but returned at the stale-generation check before retaining it; the original durable command stayed ack=null, no memory save entry existed, and old-generation replay was correctly unavailable. This was independently reproduced with the actual Panel/hook/strict client and fake IndexedDB/controlled fetch. It is an adjacent bounded recovery defect, not the cause of the full-native evidence-applicability.spec.ts:75 failure and not server receipt loss or an authorization bypass.

The fix retains the ACK only after `receipt(...)` validates its strict original-command binding, using the **sending operation's captured original session**, then applies the unchanged valid(n) gate. No stale callback may persist or render the ACK; blocked role/Policy sees only the safe pending-memory recovery message. A different current session cannot save the retained receipt. Returning to the original session after a fresh author/Policy read enables explicit save-only recovery, without a second decision POST. Immutable command/key/body/CAS and samePage/access-generation replay restrictions are unchanged. Current GET projection is still independent of the historical ACK.

## Actual verification

- Archived original probe hash `f71e6114d62082f2f02c9e2038c3dc84192a06e166f6b213b9321a826a47a1ca`: two baseline runs each 2 FAIL / 2 PASS at 60fa; the **unchanged bytes** then ran 4 PASS on the production fix (`original-probe-green.log`).
- Initial formal typecheck found that the synthetic Policy notification used abandon with undefined instead of the mandatory AttemptSubmit body. Original `typecheck.log` exit 1 is retained. The sole harness correction adds `{ expected_revision: 1 }`; it does not alter the held ACK, assertions, production behavior or access-notification route.
- Final typed probe hash `f98391309d65b1ce5c6d66f69c4b80bf2d41e431ca0f380f5fad9a8bb17a91df`: copied unchanged to the isolated 60fa tree, actual 2 FAIL / 2 PASS, exit 1 (`typed-probe-baseline-red.log`); identical final bytes on the fix pass in `final-feature-green.log`.
- Final complete Evidence applicability feature group: **22 PASS / 0 FAIL**, 3 files, exit 0. This includes the four original probe cases, two extra isolation cases, and sixteen pre-existing cases; do not sum repeated runs as new cases.
- Extra cases confirm a new current session cannot inherit/save/display the late ACK, the original session can retry an injected IDB save abort without another POST, old-generation replay remains unavailable, and a substituted basis in a late ACK is rejected before retention.
- Final strict TypeScript lint (tsc --noEmit --noUnusedLocals --noUnusedParameters): PASS, exit 0 (`final-lint.log`). git diff --check PASS. No dependency installation or changes.

These are **synthetic controller/component regressions**, not native browser, actual SQLite/HTTP, external Provider, numerical runtime, or combined full-gate acceptance. Production fix GREEN does not change the earlier full-native 121 PASS / 1 FAIL result. Central-fence integration/full gate remains the root's responsibility.

## Reproduction

Use the fixed source and existing frozen dependency/toolchain symlinks. The external configs pin test root, cache and jsdom; dedicated TMPDIR avoids /tmp quota.

```sh
TMPDIR=$HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-fix-evidence-oct02/tmp bash scripts/node.sh node apps/web/node_modules/vitest/vitest.mjs run --config $HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-fix-evidence-oct02/vitest-feature.config.mjs --reporter verbose
TMPDIR=$HOME/.cache/learning-workbench-acceptance/m62-applicability-late-ack-fix-evidence-oct02/tmp bash scripts/node.sh npm --prefix apps/web run lint
```

Earlier direct invocation of the non-executable node wrapper exited 126; this startup failure remains in original-red/probe-first.log, and subsequent invocations correctly used bash. All original failures/logs, exact baseline/final sources, patch and probe byte binding are preserved. Review of the small production delta was requested from the independent fence owner; no claimed independent approval is included here before receipt.
