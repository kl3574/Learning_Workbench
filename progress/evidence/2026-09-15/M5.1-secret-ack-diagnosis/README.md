# Secret ACK / parent read timing repair evidence

This package is a derived public copy of private synthetic diagnosis artifacts. It is not full M5.1 acceptance. See repair-summary.json for every actual RED/GREEN/HARNESS_ERROR and source/test limitations. Final owner scope: 5 native tests, 35 Provider unit tests, app type/lint; full combined gates belong to root.

Original source and all failed outputs remain immutable in private cache. Four actual runtime cookie/CSRF field occurrences (two fields duplicated in run05 log and error-context) are replaced only here. Synthetic test source constants, config SHA and public idempotency command IDs remain unchanged. No user key, private provider-test folder, database, profile, secret store file, HMAC, bootstrap capability or paid provider response was copied.

Absolute repository/cache/home paths are explicitly normalized to <REPO>, <EVIDENCE_CACHE>, <SYNTHETIC_TMPDIR>, <USER_HOME> and <CI_HOME>. Replay harness imports/commands need those placeholders mapped to a local checkout/cache. Source files without paths or actual runtime credential fields retain exact bytes. ANSI output is preserved; no blanket stdout rewriting. Original/public SHA and sizes plus transformations are recorded for every payload.

Original three native bodies/assertions are unchanged. The two added native RED cases used the old readback label; final cases change only that one label, with hash-proved reconstruction and diff. Original controlled probe body/assertions and observer-v2 remain byte-identical; GREEN adds bounded route-handler cleanup, separately retained. run05 is a harness shutdown error, not a valid negative-control PASS. Actual concurrent peer update in final native still yields 412 and requires explicit new-key correction.

Four PNG files are actual final-run synthetic screenshots individually viewed by the author; no image edits were performed. They cover the existing controls and original-ACK display at 1440/390, not all UI/A11y conditions. The original-ACK image contains a public command identifier, not an authentication secret.

Aggregate algorithm: SHA256 of UTF-8 json.dumps([{'path': item['path'], 'sha256': item['public_sha256']} for item in sorted(entries, key=lambda item:item['path'])], sort_keys=True, separators=(',', ':'), ensure_ascii=True), without a final newline. The aggregate covers payloads; README and manifest are metadata and excluded from that aggregate.
