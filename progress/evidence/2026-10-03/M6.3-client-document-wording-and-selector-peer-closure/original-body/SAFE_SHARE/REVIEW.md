# Static finding: local download status wording at 196b

This independently confirms the root-reported defect in the immutable 196b6a9a7da9be94a12eaf5d93f63fb6eb041edc snapshot. It reviews the local document template, its unit/native byte oracles and necessary caller/spec context, without executing the application or tests.

## Standards

No separate code-structure finding. No implementation change is proposed beyond accurate operation wording and matching content assertions.

## Spec

P2 — apps/web/src/features/authoring/LocalTaskDocument.tsx:32 writes an unconditional “未连接 Codex” into the downloaded document. The same component's visible explanation at :46 repeats that unconditional state. Its only awaited read (:27-30) verifies current session workspace, original actor, author role and Policy; it does not observe Broker capability or authorization. AuthoringPanel.tsx:43-44 passes localTask whenever the academic form is admitted, while the capability observer is separate (:57). AuthoringForm.tsx:51 directly renders the local download component. Therefore a valid author can download this text while the independent Broker observation is unknown or available/authorized; session admission alone does not establish disconnection.

v3.0.14 §6.6 (:354) attaches the disconnected label to unavailable/unauthorized Codex; §12.5 (:658) assigns capability and authorization observation to Broker. §20.16.5 (:1467) also keeps account authorization independent. A local download may truthfully state that this operation does not call Codex. It must not infer overall connection status from the absence of a Codex call.

The unit oracle (LocalTaskDocument.test.tsx:42) and native oracle (tests/e2e/local-task-document.spec.ts:36) reproduce the original incorrect sentence exactly. The minimal correction is operation-scoped wording in the document and visible paragraph, with the two exact-content oracles updated; no added capability request, permission gate, server task, API or persistent behavior is required. The four user-input bytes, exclusions, GET/session-only behavior and dirty/late-callback guards must remain unchanged.

This is OPEN_AT_196B for the document/body component. The previously sealed 196b footer closure remains valid for its separately reviewed two-file delta and is not rewritten. No application, browser, DB, CLI/model, network, system probe or previously rejected diagnosis was run. No product source was modified. One reviewer applied separate Standards and Spec axes; this is not a full fallback or M6.3 acceptance result.
