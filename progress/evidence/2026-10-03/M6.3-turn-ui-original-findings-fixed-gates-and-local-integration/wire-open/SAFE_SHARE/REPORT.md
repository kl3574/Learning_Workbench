# Independent static review: cancel JobSnapshot wire

Fixed `94bdbb02298035416aed8bdaa43299ef7aa44847`, parent `db5a6bceaeadf099de9b3a9e6d6a7ce786071db2`. Exact seven-path delta: two production files and five tests/fixtures. One peer, two review axes; no application or test execution.

## Standards

No confirmed Standards finding. The change reuses the generated named `JobSnapshot`, closed wire checker, existing command journal and persistence path. It adds no API or direct fetch workaround. Production changes are limited to `turnClient.ts` and `turnCommands.ts`; hook, original actor/access guards, db5 restore fix, backend and old bootstrap decoder are unchanged.

## Spec

The original reduced `JobRef` mismatch is **CLOSED_STATIC**. `turnClient.ts:76–80,119–122` checks and retains the complete `JobSnapshot`; `turnCommands.ts:12,37` preserves that object and binds workspace, kind and Job ID. The actual route `interfaces/import_http.py:73–75`, internal `CancelCommand.ack`, and sole `PRODUCT_DESIGN.md:2451` all require this full response. Snapshot has no actor field; the unchanged original command and fresh-session checks bind its cancelling actor. A valid same-workspace learner may issue a new cancellation, while replay remains the original actor/key/body.

**P2 OPEN_STATIC — ACK status/revision is not bound to the original cancellation basis.** `turnCommands.ts:37` calls `checkedTurnJob`, which only checks shape/id/kind/workspace. A complete same-owner `awaiting_approval/r1` snapshot is accepted for a not-started, not-yet-cancelled `awaiting_approval/r1` basis, although the owner must produce `cancelled/r2`. A terminal `completed/r5` basis can likewise accept `failed/r4`. Both reach journal persistence as an acknowledged command. These are static counterpaths, not claimed executed tests.

The correct relation is explicit in `AuthoringJobRepository.cancel:244–256` and `verify_cancel_ack:258–282`: terminal observation keeps original status/revision; already-requested running cancellation may keep both; first running cancellation remains running and increments revision; first non-running cancellation becomes cancelled and increments revision. Fixed dispatch 351 retains these rules. A narrow journal check should use the original complete control basis, without forcing every transport ACK to cancelled or reconstructing history from current GET. Producer accepted the finding; later RED/fix belongs to a separate receipt.

## Source and evidence correspondence

Offline readback verifies all six original source hashes in `red-db5/source`. Five production/backend files equal db5 Git objects. The wire test differs from 94b only in synthetic `progress.label`, changing an empty string to `cancelled`; actions/assertions are unchanged. The reviewer's initial whole-file equality assertion failed and is retained in `READBACK_HARNESS_NOTE.json`. No same-byte first-RED-to-fixed-test claim is made. Original log SHA `afa62a4e982c038223de6dd9a01a19016704f7566af60466a59a6e9cd472472b`, recorded exit 1 and one failed case are preserved. No temporary DB or runtime file was read.

The new wire test uses the actual component/client request path with controlled fetch responses and fake IndexedDB: lost ACK, remount without POST, explicit same-key/body replay, full durable ACK, and another remount without POST or current-data reconstruction. It is not real backend HTTP/browser evidence. Other fixed tests reject truncated/wrong-owner snapshots, retain running/terminal snapshots, protect a durable full ACK from a pending writer and reject a later changed snapshot. They omit the basis-state counterexamples above. Producer-reported full gates remain separate and do not discharge this finding.

`readTurnCommand` and `persistTurnCommand` retain the complete admitted ACK and reject conflicting replacements. They do not fabricate missing fields for a previously reduced ACK: such a stored record fails closed and is retained. Current GET stays distinct from the historical response.

## Limits and sharing

The db5 restore closure, original629 OPEN report and withdrawn generation observation are unchanged. This is static source review, not overall UI/M6.3 acceptance. Every non-progress immutable Git blob is inventoried; no reviewer gate ran. Only explicit SAFE_SHARE candidates and listed outer metadata may be copied, with no transformation. No DB/archive/credentials/account/raw headers or runtime responses are included.
