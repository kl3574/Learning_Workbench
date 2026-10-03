# Edited Draft title mathematical N/A repair

Fixed `ca788866bb37aae0e783d63c2d36e7bd31994b2f` relative to `2035fc9bf92f1c6b38725b2936898ad49adb4c16`; only Review applicability and its integration test changed. The sole normative source is PRODUCT_DESIGN.md §20.3, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. No main, remote, Provider, numeric executor or real human approval was touched.

The real local Edit Draft/SQLite/Review worker path accepted explicit mathematical NOT_APPLICABLE when the current title contained `$x^2$` or `\(x=1\)` and the body was plain. Stage01 is the exact RED: two decision calls failed to raise MATHEMATICAL_REVIEW_REQUIRED. Its complete stdout, source input map and raw source bytes are retained. The behavior was a bypass at the decision boundary, not a setup error.

The existing signal scanner now includes `title` only for `EditReviewMaterial`, and that material still supplies only its current record.payload. It does not scan the historical frozen base for applicability. Complete original base/history authentication remains unchanged. Import, single and group applicability logic is unchanged. A signal blocks N/A; lack of a signal grants no automatic classification or approval.

Stage02 targeted behavior is **5 passed, 2 warnings**: both title formula forms, existing current-body formula counterexamples, and a nonmath current title/body with historical math in both the frozen base title and body. That positive case preserves exact original base bytes, explicit human reason, candidate identity, NOT_RUN machine report and historical replay; corrupting the old physical base still rejects read/replay. The decisions are explicitly synthetic, not real human reviews.

Stage03 related gate is **136 passed, 6 deselected, 2 warnings** in four integration files. The two deselected generated-owner fixture tests intentionally avoid controlled Provider activity; neither is claimed as passing. Stage04 Ruff on both changed files passed; stage05 mypy on 208 source files passed. Full suite, HTTP/UI, real Provider, real math/source approval and M6.2 acceptance were not run here.

All five commands, complete logs, actual exit codes, actual precommit HEAD and unchanged before/after 1051 engineering inputs are retained. Green and later inputs match the actual final Git tree byte-for-byte; RED has the old implementation. The previous 1063-member repair package was rehashed and remains untouched. Runtime databases and virtual environment are not part of this package. Independent review of this increment remains pending.
