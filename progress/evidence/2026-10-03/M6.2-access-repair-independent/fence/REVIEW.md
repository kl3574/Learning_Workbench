# Independent access-transition fence review

Source `0f06d57d25353867493168a5e693f150c3cee535`, detached clean tree `$HOME/.cache/learning-workbench-acceptance/m62-access-fence-independent-review-oct02`. Sole PRODUCT_DESIGN v3.0.13. No owner/root/original user checkout changes.

**No new blocking finding in the bounded page-local fix.** Independently executed fixed tests: **10 PASS / 0 FAIL**, exit 0 (eight transport cases, two real owner-hook cases). Native and full Web gates were not independently rerun.

## Production ordering

Only api/client.ts changes production behavior. Access-changing POST increments the page-local counter before start-generation notification. GET /session waits while mutations are pending; the loop rechecks after resumption. Success, network error, abort and HTTP rejection all pass through finally: decrement, generation notification, then release waiters only when the counter reaches zero. Concurrent mutations cannot release the fence prematurely. Actual GET supplies fresh permission truth; old role ACK is not used as current authority. Bootstrap/initial session reads do not deadlock their own request; safe Jobs reads/cancellation are not fenced.

The existing hook rejects already-dispatched old GET responses by owner/access/sequence. useWorkspacePolicy sets known=false during invalidation; Shell locks the subject entry until fresh permission completion. A newly mounted applicability owner starts denied and cannot load old-author journal during a held mutation. Original journal and receipt memory are untouched. Historical ACK and current GET remain separate. The separate late-ACK fix 93bc2ed5 uses a different production file; combined acceptance belongs to root.

The counter is page-local; BroadcastChannel invalidation is unchanged. This patch does not claim shared pending counts across tabs/restarts or proof that an unknown server mutation has stopped after a transport error. These are boundaries of the demonstrated mechanism, not a finding that the controlled same-page fix fails.

## Safe native evidence readback

Only explicitly safe red-04/green-02 JSON timelines and source metadata were inspected/copied. The flagged green-01 raw Playwright log was not read, printed or copied.

- Old before-commit hold: direct server GET author, subject entry enabled, protected DOM hash count 1; after actual POST completion, fresh GET learner and count 0.
- Old after-commit response hold: direct GET learner; entry could open but protected hash count stayed 0.
- Fixed before-commit and after-commit holds: subject entry disabled while pending; protected DOM hash count 0 throughout, including learner after release.

The v4 source really holds before route.fetch or after the server response, separately GETs server role and samples code DOM (including closed details) for 400 ms. It then checks original-command region absence and preserves the safe memory-recovery prompt. It does not substitute screenshot visibility for DOM presence. Identical native probe SHA256 `4fd8278e462d9f4e84e2b1dff55a6b6aa32e79cace79070e7671ad4a50de50a7` is bound to both runs; each before/after source manifest is unchanged. Fixed client SHA256 `f19fef2c82b97e7f503e7fa7017ee397ba6b6a0770dbd42af39ce9355b9ab311` matches the commit.

This establishes the controlled pre-commit readmission defect/fix. The original uncontrolled full-native failure did not capture commit order; its exact network order is not retroactively proven. Its historical 121 PASS / 1 FAIL remains preserved, and this focused acceptance does not substitute for a combined full gate.

## Independent execution

```sh
TMPDIR=$HOME/.cache/learning-workbench-acceptance/m62-access-fence-independent-evidence-oct02/tmp bash scripts/node.sh node apps/web/node_modules/vitest/vitest.mjs run --config $HOME/.cache/learning-workbench-acceptance/m62-access-fence-independent-evidence-oct02/vitest.config.mjs --reporter verbose
```

`focused-independent.log`: 2 files, 10 PASS, exit 0. Frozen dependencies/toolchain reused by symlink; no install/private DB copy. Synthetic controller tests do not prove hosted models or physical arithmetic. Owner-produced native timelines were reviewed, not rerun. No credentials or environment content were read. An initial archive-only wrong Shell.tsx path and failed checksum attempt are recorded in archive-attempt.json; corrected source path is archived, with no source or test change.
