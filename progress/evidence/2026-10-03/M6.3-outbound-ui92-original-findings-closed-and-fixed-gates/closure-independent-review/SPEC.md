# Spec axis — 92c8836 delta

CLOSED_STATIC: original result P2 (43 client:58-59 → 92 client:56-61) and original endpoint P2 (43 client:26-30 → 92 client:26-31).

Normative anchors: PRODUCT_DESIGN:1527 strict independent DTO; 1670-1674 result fields; 1688 exact retained output; 1830 post-start fact retention. Current result owner validator: services/api/app/codex_turn_dto.py:533-538. Endpoint owner: its Endpoint validation and CodexFrozenOutboundSummary.frozen_limits; explicit loopback host must remain one of localhost/127.0.0.1/::1. No inference of completed outcome from HTTP200 or output_state remains.

Original grant/start ACK does not drift with later current GET; immutable commands and fresh actor/Policy guards are byte-identical to 43c6. Original broader functionality remains limited to explicit preview/grant/revoke/start/result controls; GenericApproval operation controls, artifacts, runtime proof availability, actual dispatch, physical resources and full acceptance are not established by this review.
