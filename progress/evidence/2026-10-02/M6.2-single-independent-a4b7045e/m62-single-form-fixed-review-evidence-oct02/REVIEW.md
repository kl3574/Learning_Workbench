# Independent Single publication form fix verification

Conclusion: the independently reproduced P2 on `4232676b5669592d260f994edd94b4392e003ab6` is fixed by `a4b7045e435e0c4fa7c2b2364ade2407a8cd9afc`; no new blocking finding within this targeted review. This does not claim complete M6.2 or real physical numeric PASS.

Fixed detached review tree: `$HOME/.cache/learning-workbench-acceptance/m62-single-form-fixed-review-oct02`. Its tracked files are unchanged. Only the private additional boundary probe is untracked. Own npm dependencies installed; no root/author tree edits, remote/provider calls, environment enumeration, or credentials. Sole spec v3.0.13 SHA `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`; relevant §4.3 dirty-work protection, §4.4 frozen original operation, §20.10.1 restricted owner/session continuity, §20.15 Single exact publication mapping/ACK versus current.

## Standards

No blocking finding in the focused patch. `singlePublicationMemory.ts:18-57` assigns each nonempty form a monotonic in-memory version and releases only an exactly equal retained record under the original session/workspace. The change remains in the existing owner module, adds no wire/storage field, no new owner alias and no cross-owner access. The module-wide counter does not determine authorization and a new page does not inherit memory. Original page/access/actor command proof and strict journal parsing stay in place.

Read the full resulting `useSinglePublication.ts`, memory, Panel, command persistence and relevant fixture/tests; reviewed the exact `a4b7045e` diff and preceding actor/r1 changes at their dependency boundary. The `8d9` Authoring admission fix was exercised by its tests and checked as a parent integration dependency; this review is not an independent rereview of every Authoring workflow. All four team slots were occupied, so Standards and Spec were separate passes by this reviewer; no claim of two additional subagent reviews.

## Spec and fix behavior

`useSinglePublication.ts:147-165` captures the matching, confirmed original form before the first awaited ledger read. `execute:83-107` only asks to release that captured form; the memory owner compares its full version/session/workspace/basis/value against what is currently held. Later accepted UI changes survive even when the user returns to identical selected/confirmed values. Explicit replay calls `execute` without a submitted form, so replay cannot consume a subsequently prepared form. No busy freeze was used to hide the original counterexample.

On original command IDB-write failure, the original body/key are retained in command memory while the later unsent choices remain independently retained; zero POST occurs. Explicit save persists the exact original command without POST. Only a later explicit replay sends that original body/key once. On ACK IDB-write failure, the original ACK is retained in memory while durable storage still holds the unknown original; explicit save persists that ACK without resending. The added tests assert the full command before/after, not just a UI label or call count. Parent dirty/safe and existing Policy/actor checks remain active; same-page restrictions are not expanded to cross-refresh replay.

## Actual verification

- Original private probe SHA `0b73f3f720e8766b316e31703c19b6ddb87dc418e24767c8fe5784b1e8c065d2` is byte-identical at both fixed sources. Old `423` result: 2 PASS, 1 FAIL (late accepted choices deleted). New `a4b` exact original command: 3 PASS; 1261 source inputs unchanged. The original RED files/reports remain untouched and are referenced with hashes in `original-red-links.json`.
- New independent Panel probe `independentFormFixedReview-v2.test.tsx`, SHA `e40b9cb68f87c84d994c5000281e45df0af211172d0980ef39253af68cb3d762`: three cases cover identical-value newer version; failed original journal write / explicit save / exact original single POST; failed ACK journal write / explicit save with no second POST. DOM checkbox `:disabled` is checked in the first two acceptance windows. UI actions use the actual Panel; fixture wire ports and IndexedDB failure injection are controlled test boundaries, not physical server/numeric evidence.
- Related fixed Single/parent set: 12 files, 60 tests PASS (`focused-single-and-parent-02`). This includes original probes, actor/readback regressions, journal tests, Authoring admission, NumericCheckPanel and ReviewPanel.
- Strict TypeScript / unused checks PASS (`strict-types-02`). Both final gates bind 1262 unchanged inputs; 1261 tracked inputs compare byte-for-byte to Git a4b, plus one private probe. Exact commands, times, exit status, log hashes and before/after input manifests accompany every stage.
- Native browser, full Web, build, backend/Python, physical numeric runtime and remote CI execution: NOT_RUN by this reviewer for this patch. Owner/root results are not borrowed.

## Preserved probe-development failures

The first added ACK probe used the shared memory notice that also appears before original command persistence. It therefore asserted POST=1 prematurely while POST=0, failing standalone and in the already-launched focused batch. Its own helper also used unsupported Testing Library ByRoleOptions.exact, causing strict TypeScript failure. All v1 source/logs remain. The correction waits for the operation error caused by the deliberately rejected ACK write, and removes only that unsupported private helper option; no product, original probe, timeout or assertion boundary was relaxed. The corrected focused batch and strict check are green. Details: `probe-v1-correction.md`.

Standards: 0 new blocking findings. Spec: original P2 fixed; 0 new blocking findings within the stated scope.
