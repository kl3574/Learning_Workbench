# Independent static review: current session client

Fixed `40925d27af4ca4e49a444d8c6d2a40dcb2b20769`, base `764090fa7312565955bc7e781f2f279bf40f9d04`; clean at readback. Four files, 85 added / 8 removed lines. Sole PRODUCT_DESIGN v3.0.15, SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. This reviewer authored none of this UI delta. No application, browser, CLI, test or model execution was performed. An attempted parallel Standards reviewer was rejected by the thread limit; this is one independent reviewer covering two axes, not two independent subagents.

## Standards

0 confirmed findings. AGENTS makes the sole spec normative. The narrow independent current-projection type/schema is appropriate to this seam; three production changes and one meaningful regression file do not introduce a material Fowler-smell finding. Generated contract artifacts and shared validator remain unchanged. No tooling-enforced formatting issues are claimed.

## Spec

0 confirmed findings. PRODUCT_DESIGN.md:1432,1645,1647 require original bootstrap ACK bytes/decoder to remain fixed and current session metadata to reflect turn history without granting execution. bootstrapClient.ts:33–59 selects the independent generated CodexCurrentSessionView schema and matches the Python DTO cross-field conditions (codex_turn_dto.py:411–433): ready revision>=2, original r2 null/false, initializing r1 null/false, failed/unknown r2 null/false. Required fields, exact booleans, Id grammar, no extra fields and safe Unicode strings use the unchanged strict validator. The old ACK branch remains unchanged; bootstrapCommands, bootstrapMemory, old Python DTO and old generated schema are byte-identical to base.

bootstrapClient.ts:72 changes only current GET decode. useBootstrap.ts:119–129 still checks exact session ID/adapter binding and the original valid(token) fence before publishing the linked state. Workspace/access/port/store/unmount, actor/Policy and fresh-session write guards at lines12,21–62,65–103 and canReplay remain unchanged. Current flags only reach panel text at CodexBootstrapPanel.tsx:46 and never feed allowed/writable/execute/replay; true flags do not grant permissions (§20.17.3 line1647).

The new regression reads actual GET transport shape with no key/body, rejects damaged current records and widening of old ACK decoders, retains original DraftStore text, and asserts no prepare/decide/create calls when rendering checked current controls. It also statically covers all-true current flags and released slots. These are meaningful test designs, but this review does not independently rerun them or claim the author's 1068-test gate. Narrow delta only; unchanged runtime/bootstrap concerns and broader turn execution remain outside review.

Standards: 0 confirmed findings. Spec: 0 confirmed findings. This is static closure of current-session UI compatibility only, not implementation or end-to-end M6.3 acceptance.
