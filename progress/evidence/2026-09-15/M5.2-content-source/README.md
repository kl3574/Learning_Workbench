# M5.2 Content owner bounded implementation evidence

This is a local development evidence package, not the full M5.2 platform acceptance.
The current repository PRODUCT_DESIGN.md remains the sole product specification.

The final run is 67 PASS (21 new Content retrieval, 11 existing provenance, 35 existing Content),
with two dependency deprecation warnings. Final owned source, commands, exit codes and
captured before/after hashes are in summary.json and each receipt.

All earlier failures are retained and classified separately: pre-test harness error,
fixture count error, internal strict-ref counterexample, and initial mypy diagnostics.
The mypy RED has no independent timed/input receipt; it is not represented as one.

Source catalog payloads preserve exact original source bytes with a .txt archive suffix.
source-index.json maps each captured run/repository path to its full SHA and catalog file.
Only identical byte content is deduplicated. This does not imply all repo sources were frozen.

Only exact repository/cache absolute paths in non-source diagnostics are normalized.
Synthetic identity strings, assertions, outcomes, source files and hashes are retained.
Each manifest entry records original/public SHA, size and actual transformations.
No DB/WAL, private originals, credentials or screenshots are included. The local execution
helper stays in private cache; all executed commands and receipts are retained.

Manifest aggregate: SHA256 of UTF-8 json.dumps([{'path': e['path'], 'sha256': e['public_sha256']}
for e in entries sorted by path], sort_keys=True, separators=(',', ':'), ensure_ascii=True),
with no trailing newline. The aggregate covers payloads, not manifest.json itself.
