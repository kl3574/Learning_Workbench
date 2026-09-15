# Independent M5.2 retrieval ledger review

The bounded review found five concrete issues; all recorded cases pass on the final captured source.
Final actual result: 12 PASS in 1.54 seconds, with 13 captured input files unchanged.
Production repairs were made by the parent; this reviewer changed only the new integrity test.

Original REDs, source snapshots and controls are preserved. The initial scheduler expected
completed incorrectly: ordinary import parsing reaches awaiting_approval / preview_ready.
The corrected same-body fault-off/fault-on test was then run against an explicitly derived
old-source mirror: normal control PASS, corrupt queue FAIL. On repaired source both PASS.
The folder scheduler-red-02 contains actual GREEN output; its name is not a result.
The external fault-off-01 attempt is a collection/configuration harness error.

Source bytes are deduplicated by SHA only and archived as .txt, unchanged. source-index.json
maps each run/path to a catalog payload. The derived mirror also uses exact files from the
pinned public base f0b4ce2; mirror-source-index.json binds every one of its 457 files either
to that commit/blob or an included catalog payload. This is a documented reconstruction,
not an original full checkout snapshot from the first RED. Original cache remains unchanged.

Non-source diagnostics normalize only task-owned absolute paths. No assertion, outcome,
source code, synthetic identity or hash is redacted. Manifest gives original/public size,
SHA and transformations for each file. No database, secret or private original is included.

See final-review.json for concrete findings, repair readback, exact results and limitations.
This is not full M5.2 acceptance, a Recall benchmark, native validation or a performance claim.

Aggregate = SHA256 UTF-8 json.dumps([{'path':e['path'],'sha256':e['public_sha256']} for e in
entries sorted by path],sort_keys=True,separators=(',',':'),ensure_ascii=True), no trailing newline.
Only payloads are covered; manifest.json does not hash itself.
