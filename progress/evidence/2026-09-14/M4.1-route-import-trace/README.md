# M4.1 R-05: importing a route

This package records one synthetic package definition run through the real ImportService, durable ImportWorker, explicit preview-warning acceptance, commit, ContentService exact-reference readback, and a new Database/RouteService instance. It does not record an HTTP or browser test, a complete M4.1 acceptance gate, or a fixed-commit execution. Fifteen relevant source hashes were equal before and after the final successful development-worktree run. The observed HEAD is context only; it does not identify every working-tree byte.

The existing learner and author specification fixtures each contain nine public objects and zero routes. Their existing generic parser/import tests therefore did not directly demonstrate R-05. This additional controlled input contains a block, lesson, course, and a two-step Route with exact hashes and one requires_steps dependency. Stage and preview had zero formal objects/revisions; confirmation produced exactly four. Both target refs and both real navigation chains were read back, commit replay returned the same receipt, and the readback did not create Learning events or Evidence.

## Actual executions

| Raw log / archived script | Exit | Observation |
| --- | --- | --- |
| run.log / probe-initial.py.txt | 1 | Temporary script lacked the Python multiprocessing __main__ guard. |
| run-entry-fixed.log / probe-entry-fixed.py.txt | 1 | Probe incorrectly assumed ImportCommitResponse.status exists. |
| run-green.log / probe-status-name.py.txt | 1 | Misnamed log: probe used completed for ImportPreview, whose actual terminal state is committed. This is a failure. |
| run-final.log / probe.py.txt | 0 | Final real import/readback assertions passed. |

All three early failures are probe defects, not demonstrated product defects. Logs and archived scripts retain those failures. Packaging executed no tests. The original temporary databases were removed and workers stopped; no default-port server was started.

## Hash and archive interpretation

MANIFEST.json records each raw input hash separately from the public hash and names each transformation. Python evidence is archived as .py.txt to prevent discovery as repository code. Embedded hashes in receipt.json and traceability-review.json intentionally continue to identify original raw files, including the original logical name probe.py. Resolve that raw name through MANIFEST.json to the sanitized archive probe.py.txt; do not compare a raw hash with sanitized bytes.

Only exact observed private directory strings and the synthetic CSRF field literal were replaced. The placeholder <TEST_CSRF_01> is consistent across script versions; there was no real HTTP login, cookie, bootstrap code, or session credential in this service-level probe. Synthetic object IDs and full ContentRef hashes are retained. The external private input map contains original filesystem locators and replacement values; it is not part of this public package.

The ZIP itself is omitted from this evidence directory. synthetic-input-inventory.json records the original archive hash and each actual member hash. The script reconstructs the same synthetic logical payload using the hash-pinned test helper; ZIP timestamps may make reconstructed archive bytes differ. The helper's deliberate quality claim is untrusted and was explicitly downgraded by the real import warnings.

To inspect or later rerun the final script, copy probe.py.txt as probe.py into a separate temporary directory, use the relevant repository source/dependencies, and invoke it with uv run --frozen python from the repository directory. A later run is new evidence and must not overwrite these captured receipts.

CHECKS.json verifies payload hashes and scanner results; AGGREGATE.json hashes the package files except itself. The separate packaging review also checks AGGREGATE.json and scans every final file. The scanner supplements manual review and cannot prove absence of arbitrary private prose. Only the known synthetic input and existing captured files were examined; no personal libraries or unrelated files were searched.
