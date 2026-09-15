# Exact 0484a4c CI readback

Head: 0484a4ccea8b0dcb17c87743dc512b78e5633dd5. This is publication CI after software commit d65e08e3c3fd896896f7228f6099ef93b9c3362d. Immutable Git comparison records only progress changes between those commits. The older ab6c27b 11-success/1-failure and 73d65af 10-success/2-failure CI are separate historical evidence. Only progress/evidence files changed since ab6c27b, whose software is byte-identical to this head. A successful observation in this run does not establish a product fix, relabel the earlier failures, or prove their unique cause.

Final check conclusions: {"success": 12}. Overall: PASSED. The two workflow runs and all 12 jobs reached natural terminal states. The collector did not rerun, cancel, push, change the PR, execute product tests or launch a browser.

| Event | Job | Conclusion | Actual log summaries |
|---|---|---|---|
| pull_request | backend | success | All checks passed!; Success: no issues found in 133 source files; ======================= 576 passed, 2 warnings in 24.12s ======================= |
| pull_request | browser | success | 88 passed (9.2m) |
| pull_request | frontend | success | Test Files  58 passed (58); Tests  355 passed (355) |
| pull_request | integration | success | ================= 654 passed, 2 warnings in 477.92s (0:07:57) ================== |
| pull_request | security-publication | success | PASS: scanned 6265 staged/tracked files against path and credential rules. Manual provenance review remains required. |
| pull_request | spec-contracts | success | "generated_artifacts": 70,; "models": 54,; "routes": 106,; ================= 456 passed, 2 warnings in 128.72s (0:02:08) ================== |
| push | backend | success | All checks passed!; Success: no issues found in 133 source files; ======================= 576 passed, 2 warnings in 19.21s ======================= |
| push | browser | success | 88 passed (12.5m) |
| push | frontend | success | Test Files  58 passed (58); Tests  355 passed (355) |
| push | integration | success | ================= 654 passed, 2 warnings in 468.32s (0:07:48) ================== |
| push | security-publication | success | PASS: scanned 6265 staged/tracked files against path and credential rules. Manual provenance review remains required. |
| push | spec-contracts | success | "generated_artifacts": 70,; "models": 54,; "routes": 106,; ================= 456 passed, 2 warnings in 195.00s (0:03:15) ================== |

Workflow groups overlap; their Python counts must not be summed as unique full-suite coverage. All original warnings and failure output remain in full logs.

Any failure conclusion is retained with its exact original job log and failure excerpts in final-ci-readback.json; the other event's success never overrides it. No cause is inferred from a DOM/error string alone.

Browser record readback: push: 88 passed / 0 failed, 88 actual unique ordinal records; pull_request: 88 passed / 0 failed, 88 actual unique ordinal records. browser-case-readback.json contains each actual case ordinal, title, duration and original log line; these were cross-checked against the actual summaries. Case duration covers the whole case, not the first five-second assertion alone. A current Reader pass is not proof that the original historical failure was repaired.

Both actual artifacts API responses contain total_count=0. No failure JSON, error context, PNG or trace is claimed or reconstructed for these runs.

Each job's actual git log -1 --format=%H command/result is bound by original log line. Push jobs checked out the exact head; PR jobs actually checked out the synthetic merge commit 833744497a2bee1d30bfa0f0ccbf269c4114d130. GitHub Git commit API records prove every one of the 12 checked-out trees equals the head tree f9156ba8366f27cb453e5eea6a0aab60bbbca8ac. Equal trees do not imply equal commit identities. Only immutable Git blobs/API readbacks were used; current working-tree changes are outside this proof. Source files already published in the repository are not duplicated here.

PR50 state is the timestamped actual API readback in the final receipt. This is a historical observation, not a promise about a future branch/head. The first and final API cycles and all final job logs are included. Intermediate API cycles remain unchanged privately; every observation timestamp is listed in final-ci-readback.json. Actual intervals, rather than an asserted exact polling cadence, are retained. Unfinished observations are not presented as terminal results.

Each raw-derived payload maps to its original path relative to the private CI collection directory and has raw/public SHA-256 and byte counts. Text changes are only fixed literal substitutions of the private-home-prefix and GitHub-runner-home-prefix with neutral placeholders. Private originals are unchanged. Complete public logs retain ANSI and every failure/warning line. Structured summary excerpts explicitly strip ANSI SGR only and retain original line numbers; they are not falsely described as byte-identical ANSI-decorated excerpts. No user credentials or private provider-test files were accessed.

The aggregate is SHA-256 of UTF-8 json.dumps(path-sorted [{path,sha256:public_sha256,size:public_bytes}], sort_keys=True, ensure_ascii=False, separators=(",", ":")), excluding manifest.json. The unchanged repository publication inspector is executed against every proposed public path, including the manifest, with an additional bounded credential/runtime-identity scan. Pattern scanning does not guarantee detection of arbitrary private prose or secrets. This package records actual CI outcomes and does not close a milestone or Issue.
