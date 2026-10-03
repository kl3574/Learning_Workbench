# Independent command, transport and session review

Candidate f07f75cb59b4a33eb3ef7b7726984662a1d74ebb, baseline 82ca2052de914bf8ea53cb36a9b8be2c9b64c7bf. No remaining blocking finding within the assigned command/transport/session and polling scope. This is a scoped independent review, not a second whole-UI review or complete M6.2 acceptance.

## Standards

The client uses existing generated routes and the shared credentials/CSRF transport. Runtime decoding follows generated OpenAPI shapes and additionally checks candidate/review/workspace identity, receipt revision and decision relations. DraftStore preserves immutable full command bytes and conflicts before HTTP writes; access guards retain its real transaction completion boundary. No credentials, CSRF or actor fingerprints enter command persistence. Server owners remain authoritative for actor, current Policy, histories and artifact bytes.

## Spec and actual behavior

Against PRODUCT_DESIGN.md sections 4.3, 8, 20.2–20.3 and Appendix A: original ACK and current GET remain separate; unknown create/decision results cannot silently create another command. Same-page/access-generation replay is explicitly limited and never presented as proof of authenticated identity. Fresh pages preserve unknown old actor commands read-only. Safe control IDs, current Job reads and explicit cancellation remain usable during private-content restrictions. Protected late results and IDB acknowledgement writes are rejected after access/context changes. Report display/download requires receipt membership, actual strong ETag byte equality and a fresh unchanged protected receipt.

Three findings have checked resolutions. Stage12 demonstrated that an old-page unknown cancel blocked a new explicit stop; stage13 and final26 preserve the old command while allowing a new current-Job/CAS cancellation. Stage15 demonstrated actual r3-to-r1 rollback from an older poll; stage16 added request ordering. Stage21 demonstrated an extra GET for the previous selection after selecting another Job, not a second final UI rollback; stage22 and final26 add effect-bound selection generation. The final hook also covers waiting beyond one polling interval and resumption after a failed manual read. Stage18/19 failed fixture initialization and are not product RED evidence.

## Evidence and limits

Verified all 29 actual stage log hashes, receipts, equal before/after manifests and retained source copies. Independently compared all 1005 engineering inputs of each final stage26/27/28/29 with actual Git bytes; pinned all 18 changed files and reviewed context. Implementation-owner results: 144 tests in 27 related files PASS; build and lint PASS; native browser case PASS, 6.4s case / 6.9s runner. Existing chunk warning remains. This reviewer ran no product tests and changed no product source.

Native fixtures use real local Import/Review/Jobs/Artifacts and lost actual responses; explicit synthetic REJECTED decisions are not human content approval. No real provider call, publication, draft-state transition, teaching validation or full-suite success is claimed. Initial review notes remain as historical development observations, superseded by this fixed-candidate conclusion.
