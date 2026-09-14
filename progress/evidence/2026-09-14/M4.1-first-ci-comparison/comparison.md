# M4.1 fixed-source CI/local failure comparison

Fixed source: `9a803c24a17df8b621370d18dfe528db10d76325`.

All 12 checks are terminal: 10 success, 2 browser failure. Both push/PR browser runs report **55 passed / 17 failed**, versus the original local **47 passed / 25 failed**. PR47 is open, draft and unmerged at readback; its head matches this SHA. No rerun/cancel/merge was performed.

Both remote 17-test failure sets and the extracted first-assertion details match exactly. Every remote failure also belongs to the local 25-test failure set. Local-only failures are listed below; absence from the remote failure set is not a repair claim.

- `tests/e2e/practice-restart.spec.ts:20:1 › same practice tab identity rejects changed frozen parent or child hashes and preserves the original session`
- `tests/e2e/practice.spec.ts:26:1 › five real question kinds save and refresh; hints and solutions require explicit exposure; submit is ungraded`
- `tests/e2e/reader.spec.ts:170:1 › historical course revisions stay in separate exact tabs and hash-mismatched links preserve unresolved reference`
- `tests/e2e/review.spec.ts:35:1 › real history and exact material review preserve original submitted text, null scores and a selected old revision after reload`
- `tests/e2e/workbench.spec.ts:212:1 › UI cache quota failure stays visibly unsaved until the real server acknowledges`
- `tests/e2e/workbench.spec.ts:229:1 › offline UI candidates from two pages remain separate on reload`
- `tests/e2e/workbench.spec.ts:22:1 › real keyboard and mouse resize, native drawers, focus return and restored layout`
- `tests/e2e/workbench.spec.ts:250:1 › quota-only memory candidate with a changed server baseline shows three-way comparison before explicit CAS`

The common first two failures are the missing current-course-directory region in `imports-policy.spec.ts:61`, then the missing initial-learning-goal heading in `imports.spec.ts:111`. CI `workbench.spec.ts:5` reaches the heading assertion; the local test fails earlier on saved-session bootstrap. Subsequent CI synthetic-reader tests generally time out waiting for “浏览合成示例课程” at `helpers.ts:27` (30 seconds), while the local counterparts fail on “✓ UI 会话已保存” at `helpers.ts:24` (5 seconds). CI zoom only records a test timeout, without an attributable locator. These observations do not prove one shared causal bug, and no residual independent attempt is inferred.

`comparison.json` records all exact test names, bounded assertion excerpts, original hashes, workflow events, check polling intervals and PR readback. The separate exact CI manifest retains the 12-check history and downloaded original logs. Raw logs stay private in temporary storage. This is read-only evidence collection, not a full-stage acceptance or a repair test.
