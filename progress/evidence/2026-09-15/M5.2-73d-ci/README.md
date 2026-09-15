# Exact 73d65af CI readback

Head: 73d65af4bae237e72fb9a0a6294028cfbad62823. This is the diagnostic publication CI after software commit ffd580364aa8d8168fceb5dcd6e5288aa4ce2597. Immutable Git comparison records only progress changes between those commits. It is not the original 3dd75f0 run and does not retroactively explain or pass that earlier failure.

Final check conclusions: {"failure": 2, "success": 10}. Overall: NOT_PASSED. The two workflow runs and all 12 jobs reached natural terminal states. The collector did not rerun, cancel, push, change the PR, execute product tests or launch a browser.

| Event | Job | Conclusion | Actual log summaries |
|---|---|---|---|
| pull_request | backend | success | All checks passed!; Success: no issues found in 133 source files; ======================= 576 passed, 2 warnings in 23.77s ======================= |
| pull_request | browser | failure | 1 failed; 87 passed (13.2m) |
| pull_request | frontend | success | Test Files  57 passed (57); Tests  346 passed (346) |
| pull_request | integration | success | ================= 644 passed, 2 warnings in 471.74s (0:07:51) ================== |
| pull_request | security-publication | success |  |
| pull_request | spec-contracts | success | ================= 456 passed, 2 warnings in 138.56s (0:02:18) ================== |
| push | backend | success | All checks passed!; Success: no issues found in 133 source files; ======================= 576 passed, 2 warnings in 25.14s ======================= |
| push | browser | success | 88 passed (9.6m) |
| push | frontend | failure | ⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯; Test Files  1 failed  /  56 passed (57); Tests  1 failed  /  345 passed (346) |
| push | integration | success | ================= 644 passed, 2 warnings in 462.90s (0:07:42) ================== |
| push | security-publication | success |  |
| push | spec-contracts | success | ================= 456 passed, 2 warnings in 194.43s (0:03:14) ================== |

Workflow groups overlap; their Python counts must not be summed as unique full-suite coverage. All original warnings and failure output remain in full logs.

The push frontend failed in src/features/recommendations/recommendations.test.tsx:33:61, case “opening either real parent chain is explicit, preserves all full refs and does not accept the recommendation”: a navigation callback was expected once with the full reader argument, but had 0 calls. Its actual summary is 1 failed / 345 passed, 346 tests across 57 files. The PR frontend's separate success does not override the push failure. No root cause is inferred merely from the captured DOM or this call-count observation.

Browser record readback: push: 88 passed / 0 failed, 88 actual unique ordinal records; pull_request: 87 passed / 1 failed, 88 actual unique ordinal records. browser-case-readback.json contains each actual case ordinal, title, duration and original log line; these were cross-checked against the actual summaries. Case duration covers the whole case, not the first five-second assertion alone. A current Reader pass is not proof that the original historical failure was repaired.

Actual artifacts were downloaded privately, safely enumerated before extraction, and reviewed before publishing only the allowlisted synthetic diagnostic files. The ZIP originals remain private; their hashes and member identities are preserved in extraction receipts. See artifact-publication-review.json for observations and limits.

The actual PR browser failure is the historical Reader case at reader.spec.ts:181:48: the unchanged 5000 ms .real-reader expectation found no element. Its post-failure diagnostic and screenshot show the precise r2 tab with the main pane still reading the revision/body and the left course directory loading, without an alert. The single observer clock contains 35 events and zero omissions; lesson r2 and outline r2 requests have no recorded response/finished/failed event within that saved observation, and no block revision GET is recorded. These are bounded observations, not proof of a particular server, database, browser or network cause.

Each job's actual git log -1 --format=%H command/result is bound by original log line. Push jobs checked out the exact head; PR jobs actually checked out the synthetic merge commit 757ccd2c67ee5fad9fd44bb29697e05fd9b70d04. GitHub Git commit API records prove every one of the 12 checked-out trees equals the head tree 0b82fadb50088fef86250b746a55e7595cc1ed74. Equal trees do not imply equal commit identities. Only immutable Git blobs/API readbacks were used; current working-tree changes are outside this proof. Source files already published in the repository are not duplicated here.

PR50 state is the timestamped actual API readback in the final receipt. This is a historical observation, not a promise about a future branch/head. The first and final API cycles and all final job logs are included. Intermediate API cycles remain unchanged privately; every observation timestamp is listed in final-ci-readback.json. Actual intervals, rather than an asserted exact polling cadence, are retained. Unfinished observations are not presented as terminal results.

Each raw-derived payload maps to its original path relative to the private CI collection directory and has raw/public SHA-256 and byte counts. Text changes are only fixed literal substitutions of the private-home-prefix and GitHub-runner-home-prefix with neutral placeholders. Private originals are unchanged. Complete public logs retain ANSI and every failure/warning line. Structured summary excerpts explicitly strip ANSI SGR only and retain original line numbers; they are not falsely described as byte-identical ANSI-decorated excerpts. No user credentials or private provider-test files were accessed.

The aggregate is SHA-256 of UTF-8 json.dumps(path-sorted [{path,sha256:public_sha256,size:public_bytes}], sort_keys=True, ensure_ascii=False, separators=(",", ":")), excluding manifest.json. The unchanged repository publication inspector is executed against every proposed public path, including the manifest, with an additional bounded credential/runtime-identity scan. Pattern scanning does not guarantee detection of arbitrary private prose or secrets. This package records actual CI outcomes and does not close a milestone or Issue.
