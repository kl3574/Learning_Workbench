# Independent Content impact discovery backend review

Original reviewed commit: `f0181d37a07f04ea8d5b5af36eabfae5955df1a4`.
Base: `5f6c009fd94e0bfdf71dc2319e1097a14cecc399`.
Sole specification: current PRODUCT_DESIGN.md v3.0.11, SHA-256 `35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29`; canonical and checkout copies match. AGENTS.md designates it the sole product/engineering specification. The original specification was read in full in preceding work, all changes to the current approved version were read in full, and sections 20.11/20.13 were reread during this review.

Scope: five changed files for GET /content/impacts and shared current-state calculation. Separate Standards and Spec axes were reviewed by this reviewer; there was no available extra team slot, so no claim of a second independent reviewer. Implementation worktree untouched. Independent detached worktree and out-of-tree probes used. No remote, provider, key, progress, specification or generated-artifact changes.

## Standards

No blocking documented-standard finding in the five-path change. The HTTP adapter is thin, DTOs closed, Content owns list membership and current-state reads, registered Artifacts owner port validates evidence bytes, and the whole read runs under query_only with current session/author/Policy verification. Static checks: Ruff PASS; mypy PASS over 227 files. No speculative Fowler-style smell is elevated to a defect.

## Spec

Two P2 defects reproduced at the original SHA:

1. `services/api/app/application/content_impact_decisions.py:193`: `_current_states` lets `repo.current` propagate 404 for an already-known stored Content target whose current pointer names a missing revision. This is corrupted retained state, not an unknown caller input. Both unfiltered discovery and `changed_object_id=unknown` return 404 REFERENCE_MISSING, contrary to sections 20.11/20.13's safe integrity 409. Both calls remain no-store and zero database writes. Independent probes explicitly bypassed the normal valid_current_revision trigger for disk-corruption simulation; the first unsuccessful injection is retained. Recommended scope: translate only the known stored target's missing current material to integrity 409, preserving real unknown event/target 404.

2. `_target_ids` at lines 108–117: deleting the objects row for ID-only lesson_candidate, while leaving its genuine published Content revision behind, silently removes the candidate before filtering; `changed_object_id=unknown` returns 200 empty. Surviving Content-owned revisions prove an orphaned known Content record rather than an absent arbitrary other-owner ID. Normal FK protection was first verified to reject deletion, then explicitly disabled for this one corruption transaction. Section 20.13 forbids treating corrupt discovered records as no match. Suggested bounded validation: detect surviving Content material when an affected objects row is absent; do not infer every unknown conservative ID is Content, and do not create new snapshot semantics. Coordinated deletion of every original and witness is outside the non-coordinated integrity claim.

Original-SHA independent verification:

- `regression-01`: 110 PASS covering discovery, decisions, impact snapshots, permissions, signed pagination, legacy migration, registered artifacts, immutable records and histories; exit 0.
- `probes-04`: 12 PASS / 3 FAIL; two failures are defect 1's filtered/unfiltered variants, one failure is defect 2. Exit 1 intentionally preserved.
- Independent PASS cases: actual artifact byte corruption blocks a nonmatching list; valid foreign events excluded and contradictory foreign snapshot rejected; complete event+witness removal detected by existing signed prefix; delivery status changes and post-page new events preserve both unfiltered/filtered membership across at least three pages; empty Content target arrays retain Note/Route affected IDs in detail; current target body bytes checked without decisions; closed malformed payload cannot become no match; true pre-0021 database forward migration appears as legacy over actual HTTP and matching detail; both valid and malformed cursors after role downgrade return 403 before cursor handling.
- Full row-hash manifests (all tables via table_hashes) compared around every independent read including errors; no-store asserted.
- `static-ruff`, `static-mypy`: exit 0.

Raw command, exit status, stdout and stderr are retained per run. `original-source-manifest.json` pins all five source files and the final probe bytes (SHA-256 `b8a9949cb301501d7134989f4f83aaf9088452745908d00633eb66dacf8c506d`).

Harness failures retained, not misreported as product failures: probes-01 could not inject the current-pointer fault because the real SQL trigger rejected it; probes-03 used TestClient lifespan and the actual background Recommendation worker changed its own rows during the read-manifest window. The latter was corrected to the same non-lifespan HTTP test harness as the existing author tests; the genuine migration GET then passed. These earlier stdout/stderr and probe source snapshots remain intact.

## Bounded verification

Generated 107/127 contract integration, list/detail UI and native browser Edit→Review→Publish→Discover remain outside this backend-only review and are NOT_RUN here. No mathematical, pedagogical or numeric-quality claim is made. All content, decisions, evidence and storage corruption are synthetic local test data. Linear validation of all fixed-prefix events/history is statically visible; no large-history performance claim is made.

## Repair recheck

Final reviewed commit: `d636fe54d33ac53f0f5710a856db01dca7afd256`, product fix `7c8f5eff` and test formatting `d636fe54`. The repair diff was read: it converts missing current target material to 409 and detects affected IDs with surviving published revision evidence but absent/misowned object rows. It does not invent Content ownership for bare unknown IDs and does not expand DTOs or snapshot semantics.

Original probe file was reused byte-for-byte (SHA-256 `b8a9949cb301501d7134989f4f83aaf9088452745908d00633eb66dacf8c506d`). Results at repaired commit:

- `probes-fixed-01`: 15 PASS, exit 0, 6.46 seconds.
- `regression-fixed-01`: 115 PASS, exit 0, 34.22 seconds.
- `dto-fixed-01`: 18 PASS, exit 0, 1.29 seconds (new strict schema and route assertions).
- `ruff-fixed-01`: PASS; `mypy-fixed-01`: PASS, 227 source files.

All 148 executed tests at the final SHA passed. The two original Spec findings are resolved; current Standards findings: 0; current Spec blocking findings: 0 for this backend slice. Earlier failures remain preserved. Reviewer and implementation trees are clean at readback. No claim of list UI, generated contract integration, native end-to-end or complete M6.2 acceptance is made.
