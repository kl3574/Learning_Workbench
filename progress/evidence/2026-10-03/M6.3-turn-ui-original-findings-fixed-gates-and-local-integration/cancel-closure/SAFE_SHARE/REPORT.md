# Independent static closure: cancellation ACK basis

Fixed `b149fda25f4b007ffb4858a9b327c536a462c065`, parent `94bdbb02298035416aed8bdaa43299ef7aa44847`. One peer reviewed Standards and sole v3.0.15 Spec separately. Exact delta is one production file plus one new test file. No product/test execution.

## Standards

No new confirmed finding. `turnCommands.ts:37–42` adds one local association check after the existing complete `JobSnapshot` schema/id/kind/workspace validation. It reuses the immutable original `CodexTurnControlView` basis; it does not change transport, wire, DTO, backend, bootstrap, hook, persistence algorithm or current GET. The repair stays in the journal which has the required basis.

## Spec

**P2-cancel-ack-state-binding is CLOSED_STATIC.** In `turnCommands.ts:39–41`, terminal or already-requested cancellation is treated as observation: ACK status and revision must remain equal to the original basis. Otherwise, a running basis must return running at revision+1, and a non-running basis must return cancelled at revision+1. The exact status and revision are checked before a decoded ACK can enter memory or durable persistence. This matches actual `AuthoringJobRepository.cancel:244–256` and `verify_cancel_ack:258–282` and the cancel endpoint's JobSnapshot contract (`PRODUCT_DESIGN.md:2451`). It preserves legitimate pending cancellation and historical terminal responses instead of implying that every cancellation has already stopped execution.

The full original response remains in `TurnCommand.ack`; no fields are projected away or rebuilt from later current data. The prior full-shape, Job ID/kind/workspace bindings remain. Same-actor fresh access/replay, original body/key, persistence-before-POST and late-ACK protection are unchanged. A new safe cancellation may belong to a valid current learner; replay does not transfer an old actor's command to that learner.

## Counterexamples and evidence

The new `turnCancelBasis.test.ts:14–21` rejects six cases: unchanged awaiting-approval ACK; missing revision increment; wrong failed outcome; running cancellation falsely reported cancelled; repeated requested cancellation falsely incrementing revision; and a terminal snapshot with changed status and regressed revision. Lines23–29 retain four valid original outcomes: first not-started cancellation, first running request, repeated running request, and terminal observation. Each accepted object preserves the complete supplied snapshot.

Offline readback verifies the original second-RED test byte-for-byte against fixed b149 and all four saved production/backend sources against 94b. The recorded author result is exit1, six failed and four passed, log SHA `2b767c65d232ffe9295c91ff3d7cf9987d4832c635744919b7c76abc0b74739c`. The reviewer did not execute this test or the fixed gate. Author-reported focused/full/static results and root's real browser evidence belong to their separate packages.

## Preserved scope and sharing

Original 94b OPEN static report remains unchanged, as do the initial db5 wire RED and its fixture-label caveat, 94b passing gates, second RED, db5 restore CLOSED_STATIC, original629 OPEN and generation-observation withdrawal. This closure addresses only the fixed source-level ACK association defect and does not independently establish overall UI or M6.3 acceptance.

The entire non-progress immutable Git source is inventoried. Only the explicit SAFE_SHARE candidates and outer allowlist entries may be copied, byte-for-byte with no transform. No DB/archive/credentials/account/raw headers or runtime responses are included.
