# Independent 690 numeric artifact readback

READBACK_PASS for four actual GitHub artifacts and six JSON members from push run `37170415116` and PR run `37170416801`, source `69029bc1ab355efdbb6e0fdb8a86204c59cea71a`. PR checkout `6692d62db971b9b46cbf118efe6f26b4e0fd3b8c` has the same tree `09c22a9a18b064c36a84e05f091e37cf3e76e5cd`. Both CI runs completed successfully; all 12 root-collected actual job log checkout bytes were independently checked against their receipt hashes. No application or numerical computation was executed by this collection.

| Run | Artifact | Archive bytes | Actual content |
| --- | --- | --- | --- |
| push | 11291717091 | 2826 | Single JSON |
| push | 11291407336 | 5927 | Restore JSON and matching publication projection |
| PR | 11291472698 | 2827 | Single JSON |
| PR | 11291288003 | 5930 | Restore JSON and matching publication projection |

Each archive digest and byte size matches fresh artifact metadata, and each artifact ID and digest appears in its actual browser upload log. Strict archive inspection permits only the three specified JSON basenames, rejects duplicate, absolute, parent-traversal, encrypted and nonregular members, and enforces compressed/uncompressed budgets. Four bounded archive GETs were decoded only in memory; no ZIP was saved. Raw JSON bytes and their hashes were preserved. This collection reused the earlier 4ecc collector method, not its artifact data. Four fresh run/artifact metadata GETs bind the new runs and source.

All four numeric Jobs are failed with `environment_unavailable`, `BLOCKED`, exit 1, zero assertions, and null output SHA. Job IDs and operation SHA bind the numeric ACK to the actual result. All four publication responses are `409 PUBLISH_NUMERIC_REQUIRED`. Restore's shorter JSON exactly equals the corresponding fields of its full outcome. Both Single artifacts have `closed_chain`, no published ref, unchanged draft state, no publication command captured, zero external model calls and one controlled loopback provider call. Error arrays are empty. The checked test source retains the BLOCKED outcome and refusal; there is no replacement synthetic PASS in these observed records. This is not a universal absence-of-fallback proof.

CI success therefore proves neither physical numeric PASS nor academic/source/teaching approval, actual Codex turn capability, full M6.3 completion or release. The test human decisions and provider input are synthetic software fixtures. Prior failures, including the root's empty-log collector failure and earlier source CI failures, remain unchanged. No CI rerun, remote mutation, credential/config/environment read, real account call or system probe occurred.

Public candidates are exclusively the entries in SAFE_SHARE.json plus PUBLIC_OUTER_ALLOWLIST.json. Raw API metadata, inherited logs, DBs, archives, keys and arbitrary directory files are excluded. Candidate transformation is exact local-home-prefix substitution only; synthetic JSON payloads are byte-identical unless that precise prefix occurs. Safe scanning is a publication check, not a claim that every product security property was proved.
