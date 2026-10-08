# Local interrupt RPC/event pairing slice

Fixed analysis base: 27f549ff5a8fd67b0a601b67a5ba51ef35f6765f. Sole norm: PRODUCT_DESIGN v3.0.15 SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. This is owner analysis, not independent review or final qualification.

## Confirmed source gap

Selected9 provides only `serialize_interrupt` params, not a complete request-ID/method envelope, empty RPC acknowledgement decoder, or exact thread/turn notification pairing. The production ProofRegistry remains empty and executor remains None. No supplied offline schema qualifies a live transport, owned session mapping, hidden model request, resource enforcement, process exit or artifact scan.

§20.17.5 separates the empty TurnInterruptResponse from actual terminal/process/file facts. §20.17.7 requires versioned closed facts and actual owner authority. §20.17.8 allows checked offline originals while requiring fail-closed unknown/unpaired shapes. §20.17.9 allows controlled local protocol progress without declaring M6.3 accepted.

## Proposed and authorized local interfaces

New `codex_interrupt_protocol_models.py` and `codex_interrupt_protocol.py` own private, local input only: `read_interrupt_source`, `verify_interrupt_source`, `prepare_interrupt`, `verify_interrupt_exchange`, `observe_interrupt`. They verify a complete original request and each response/notification against strict models and the exact historical schemas. Observation order is preserved without assuming whether ACK or terminal arrives first. ACK and terminal observations remain different facts. Rejection retains bounded exact raw bytes plus hash and the unchanged prior exchange. In-memory membership count/hash detects deleted/reordered members relative to the supplied original head; it is explicitly not an authoritative owner database head.

The finite terminal subset admits only items=[] and absent/null error, the three terminal schema statuses, and actual optional int64 timing/itemsView shapes. A nonempty item, error object, unknown field/method, RPC error, mismatched ID/thread/turn or duplicate is rejected, not ignored. Missing optional values are not upstream execution receipts. Empty items or notLoaded never proves zero persisted items/artifacts.

## Source provenance and closure

Exactly eight additional files are selected from the same previously generated nonexperimental 314-file receipt. The private original receipt remains unchanged and excluded from source; the packaged source summary is an explicitly manually reviewed projection, not raw-receipt replay or a current CLI check. Eight raw files total 473257 bytes and 655 internal references, fully checked against original receipt bytes/hashes. Full ClientRequest and ServerNotification embedded closures are included so method-to-params mapping is grounded in real source, rather than inferred from a filename. No claim is made for the remaining unselected historical files.

## Necessary bounded behavior checks

Same-test missing implementation RED→GREEN; exact request/reply/event pair; ACK alone not terminal; terminal before ACK; string vs integer request IDs; wrong thread/turn; unsupported nested fields/items/errors; duplicate/unknown/malformed frames preserve prior raw facts; strict int64/false booleans; complete schema/source memberships and typed mutation; bounded source reads without repair; named process/bootstrap/probe/model/owner-write seams zero in the new local phase. Related selected9/v4/DTO regressions and five standard static gates only, no complete backend/Web/native rerun.

## Remaining implementation and evidence gaps

This does not implement all turn/start outputs, any nonempty ThreadItem or TurnError, JSONRPC error details, callbacks/approvals, initialization/resume, streaming timing/framing, owned live process mapping, persistent owner history, production InputProof or fixed runtime. Real CLI/model/transport is NOT_RUN. Current live capability and environment feasibility are not evaluated; no stopped host probe is evidence for an ENV claim. Production remains unavailable. No main/registry/executor/HTTP/bootstrap/old catalog/v4/ACK/schema/dependency/CI bytes may be changed by this slice.
