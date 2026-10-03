# Blob descriptor regression test repair

Isolated d1bc330611bc5a315957c07f8d3cee266a5a13e8, integrated as 7eb18b1. Production code unchanged. Original combined 72e4e64 Python failure (2519 PASS / 1 FAIL / 1 numeric-environment SKIP) remains separate under the Sep22 storage-initial-gates package. Its process count went from 15 to 14; no identity trace was captured, so no unique historical cause is asserted.

Controlled unrelated closure on unchanged original test really failed, from 14 to 13. The cache injector was not included in the 964 tracked input inventory; its current bytes are independently pinned, not represented as a prior in-run snapshot. Replacement runs twenty real unsafe BlobStore operations in a fresh child and compares descriptor identities. Real leak, foreign closure and same-count replacement all fail with the intended marker; a real parent closure does not disturb the child. All 70 content-store cases and Ruff passed on fixed 965 Git-matched inputs. Independent review reran no tests and found no blocking issue in this test-only scope.

No current combined gate, vendor, numeric subprocess, native or M6.2 review workflow is proven. Source runners, receipts, logs, before/after hashes and independent review are retained. Public verifier checks integrity or exactly replays path-only transformations from raw originals; it does not rerun tests.
