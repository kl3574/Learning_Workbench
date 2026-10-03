# Independent Standards review: exact block revision comparison

No blocking Standards finding was identified in `05aa1af2fd000654b0d7b62e5eae32998c81d43f` versus `833f0a84168638ba5ce421c70cd2f20a71e45e48` (12 files). The root reviewer owns the separate Spec axis. I read the fixed source before owner evidence, changed no product files, and ran no product tests.

The sole authority is PRODUCT_DESIGN.md, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`, especially §§7, 14, 15.2 and 20.1–20.2.

- `compareClient.ts:17–40` uses existing generated GETs, strict shapes, exact identities/strong ETags and separate metadata/body hashes. Canonical equivalence is confined to the closed ContentBlock tree with ASCII keys and safe integer revisions. Decoded-text re-encoding is explicitly not an independent raw-byte download; provenance remains the current authorized server projection.
- `useVersionCompare.ts:10–89` binds results to workspace/block/access/sequence, rechecks role/Policy before and after reads, and clears displayed results on permission-check failure/deadline, focus/visibility invalidation, closure or changed selection. Late results cannot restore an invalidated owner. Cross-profile detection is polling, not instantaneous notification.
- `boundedDiff.ts:6–21` is linear prefix/suffix comparison with bounded marking, preserving complete original text. History uses 20-item pages and the actual Content owner's full-page/terminal-cursor invariant; loading stops at 200. This was source-inspected, not a newly executed 200-revision stress test.
- Reader wiring and plain-text rendering add no domain write, approval, restore, semantic-equivalence or impact-analysis operation. Existing editing actions remain separate.

Independent verification checked all **1076 owner members**, **958 source-pool files**, **21 stages**, 12 changed sources and 17 context pins. Every before/after inventory was unchanged and matched its recorded actual Git relationship; development differences remain explicit. Stages 17–21 each bind 952 inputs, not a broader execution scope.

The owner's **62 Reader tests, build and spec** remain at `b20f4aa`; final `05aa` changes only four native locator lines. Stage 20's 30-second locator failure remains failed. Its DOM and separate synthetic probe support the correction (exact-label 0, exact-role 1). Stage 21 actually passed one native case (4.6 seconds case / 7.0 seconds total), with unchanged product bytes, assertions, timeout and retry behavior. No inline attachment file is invented.

Real integrity/role/current-Policy RED→GREEN source differences are retained alongside all stage hashes. Fixture query-order and TypeScript failures remain distinct. Runtime directories were excluded without reading; screenshots were neither copied nor edited. No additional visual acceptance was performed. Full Web/backend/native suites, real providers, teaching quality, restore/impact propagation and complete M6.2 acceptance are outside this review.
