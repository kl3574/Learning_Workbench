# Review of repeated control-header repair

Fixed range: c825311f82ed1457007505331e47b1d51fb5c28e → bb86417b10dbbd85a22d07a92b8e4c6642df18f1. The test-first intermediate commit is 08f515a79b94ffffe6d4344500545ce9cd9f584d. Exactly two changed files were reviewed. Source was read from actual Git blobs; the worktree was not modified and no test was rerun by either reviewer.

## Spec axis — current_group_ci_diagnosis

No blocking finding. The shared Import router owns the generic Jobs cancellation and artifact-download transport used by Review. Adding the existing `unique_headers` dependency closes the gap through which two raw Idempotency-Key or CSRF fields reached those handlers. The unchanged helper checks raw header multiplicity, rather than trusting the framework's first selected value; it neither requires CSRF/idempotency fields on GET nor changes a valid single field. It also covers the existing Import endpoints consistently.

The change retains current identity and unknown-query checks, write Origin/CSRF validation, owner access checks, idempotency/CAS and no-store attachment responses. It adds no state, endpoint, DTO, domain authorization or side effect. This matches the existing strict session/write boundaries in PRODUCT_DESIGN.md lines 531, 693, 1011 and 1237 and its explicit repeated critical-header rejection rule at 1716. Rejecting ambiguous transport input with the existing 400/SCHEMA_INVALID response does not alter a valid domain command.

The new four real HTTP cases cover cancellation and download × Idempotency-Key and X-CSRF-Token. Actual RED logs show four 200-versus-400 failures. GREEN checks the safe error code and exact all-table hash stability. Related valid Import/Artifacts/Review routes remain included in the 76-case gate. The fixed dependency's imports were also read; no new factory/database/network execution or import cycle is introduced.

This review is limited to the two-file header repair. It does not certify every HTTP route, resolve unrelated duplicate-header behavior, or replace remote CI and product acceptance.

## Standards axis — tutor_observation_finish

Independent peer conclusion, retained without reranking: no blocking finding in the fixed two-file range. The peer read the full diff, Import router dependencies, `tutor_http.unique_headers` and its http/practice dependencies. The existing raw getlist validation is reused at transport level; no HTTP authorization logic is copied into the Quality application or owner repository. Current identity, query rejection and write verification remain. The dependency direction import_http → tutor_http → http/practice_http has no observed return edge to import_http. DTO/core/route signatures, existing error codes and private projections are unchanged. The four parameter combinations cover Review cancel/download, assert 400 SCHEMA_INVALID and full-table stability. The peer did not run tests and does not present the coordinator's 76 PASS as its own execution.

## Independently checked existing evidence

`evidence-verification.json` verifies every receipt's actual log SHA and every before/after source entry against the indicated actual Git blob. Each of the six stages has **991** unchanged Git-bound inputs.

| Original stage | Actual result |
| --- | --- |
| warning-headers-red at 08f515a | 4 FAIL, 2 dependency deprecation warnings; the duplicate requests returned 200 |
| warning-headers-green at bb86417 | 4 PASS, same 2 warnings |
| warning-headers-related at bb86417 | 76 PASS, 2 warnings, 59.45s |
| ruff-safe at bb86417 | PASS |
| mypy-safe at bb86417 | PASS, 196 source files |
| spec-safe at bb86417 | exit 0; original complete log retained |

Related gate log SHA256: b4af32917f709a244754c2f210c589afd43393c9cbf10f02d30592048021096f. Original RED SHA256: 6a9fe0f85c2fa18d31bff1b7ccdd66cbe902ec089e01f34bf639e5871588d140. Exact changed/context sources and the sole specification are pinned in `source-pins.json`; complete original logs/receipts are private copies under `actual-evidence/`.

Disposition: no remaining blocker for this bounded repair; coordinator owns integration and remote publication.
