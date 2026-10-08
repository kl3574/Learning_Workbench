# Independent evidence readback

PASS for the scoped completed legacy backup-test package, without rerunning software.

- Original fixed bd3b single test: 1 FAIL, exit 1, reviewer-null expectation; retained.
- Incorrect fixed-commit invocation: NOT_RUN before pytest launch; retained.
- Fixed b51 revised single: 1 PASS, exit 0.
- Fixed b51 seven-file regression: 65 PASS, 2 warnings, exit 0; counts 7/4/4/42/1/3/4. The separate single PASS is already included in these 65, not a 66th unique case.
- Changed-file Ruff: exit 0. All four executed stages bind the saved runner and log hashes.
- All 1381 nonprogress inputs in each before/after map independently match the exact bd3b/b51 Git object bytes, modes and hashes; maps are equal. The source difference is only the expected legacy test file. Ignored installed dependencies are outside this input proof.
- RAW_MANIFEST: all 23 originals match. SAFE_SHARE: all 24 candidates equal exact $HOME -> $HOME transformation. PUBLIC_OUTER_ALLOWLIST: all four explicitly listed unchanged payloads match. SHA256SUMS is correct. Do not copy unlisted runtime files or the whole folder.
- Original RAW_SCAN remains FAIL with eight home-prefix findings; the separate candidate scan is PASS. Independent stricter home/header/sensitive-JSON checks also passed for the listed candidates/outer payloads.
- The earlier independent static review's 16 raw entries and 16 safe copies remain byte-bound to its sealed manifest.

READBACK.py is the actual read-only verifier; READBACK.json records bindings and limits. It uses only known evidence files and read-only fixed Git objects, never a test/application/backup/Codex runtime, DB, account, credential, external model/network or interrupted diagnostic.

Original complete DCF acceptance remains FAIL (3683 PASS, 1 FAIL, 2 ERROR, 2 environment SKIP), carried forward from the producer report rather than reaudited here. The two setup-error causes remain UNKNOWN. M7 complete restore acceptance remains NOT_RUN. Saved historical input maps/runner/receipts were verified; this is not a fresh execution or a new filesystem observation at the original test times.
