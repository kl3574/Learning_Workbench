# Spec axis — 43c6

Two P2 OPEN_STATIC findings: result outcome/output coupling at turnOutboundClient.ts:58-59; browser-normalized endpoint admission at :26-30. See REVIEW.md for exact counterexamples and impact.

Checked requirements: §20.17.2 strict DTO/Unicode/finite budget; §20.17.2.1 original preparation/Provider/proposal/consent/Job binding and strong comparison; §20.17.3 exact retained output and current control; §20.17.7 actor/workspace/Policy, page/access generation and immutable commands. Important source locators: turnOutboundCommands.ts:20-70,86-124; useCodexOutbound.ts:20-69,82-136,158-180; CodexTurnOutboundPanel.tsx:22-58; turnOutboundForms.ts:8-36; turnOutboundMemory.ts:11-30. Safe revoke reads consent_control rather than protected full consent; fresh checking and no automatic POST remain explicit.

CurrentSessionView intentionally has no actor field; an early consideration of checking current.actor_session_id was discarded after checking the real DTO and is not a finding. Fresh session plus preparation/consent actor bindings are the applicable checks. Cross-refresh explicit original-key replay is allowed; no persistent original-page-generation requirement is invented. Server private proof/hash truth is not recomputed from display summaries.
