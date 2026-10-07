# Private bounded grading observation candidate

The candidate adds diagnosis metadata to the original two-profile grading test. It changes no production behavior and does not claim to repair the original public push failure. Runtime lateness cause remains UNKNOWN. Whole CI and M6.3 acceptance are not inferred from these local checks.

## Candidate identity

- Normal local commit: `27bd53cada81965152647887d6bc8d18350a1ba7` on `diag/grading-bounded-observation-oct08`; parent `bf5d2df4e7ee5156993169cdd9610fa014bdae4f`.
- Isolated worktree: `$HOME/.cache/learning-workbench-acceptance/m63-grading-bounded-observation-implementation-oct08`.
- Only tracked delta: tests/e2e/grading.spec.ts. Candidate tracked worktree is clean. Canonical HEAD remains bf; its existing progress/CURRENT.md and progress/state.json changes were preserved.
- Sole specification: canonical PRODUCT_DESIGN.md v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.
- Original source SHA256: `5b4566a109242634d803d0036ec9319ee46c9d620c65c8c43aad9f3894a227d6`.
- Final frozen source SHA256: `938f4afe16073fee38e070b3edfd236037fda31f021b03b5156ed2c519bad506`.
- Exact baseline-to-commit diff SHA256: `e113e0aa19a7c683c95d1743b248b880617a72365dc90c3a6d020089986d5af2`. Both staged/unstaged and committed representations are captured without relying on an empty unstaged diff.

## Why this observer

Original push job 112915059557 fails the original manual grading CAS/three-way-rebase test while awaiting grading revision 3: expected3, sentinel0, whole-test30000ms exceeded. The owned original retained context records accepted manual command plus a last-observed queued task, old completed revision 2 and no version3 label. The corresponding original PR test passes. This evidence narrows the end-state but does not explain why the runtime was late; no worker, timeout or mutation-retry repair is justified.

The sealed independent original diagnosis and safe byte-bound artifact findings are at `$HOME/.cache/learning-workbench-acceptance/m63-publicbf-original-browser-failure-independent-diagnosis-oct08`. They continue to retain the original actual failure and UNKNOWN cause.

## Behavior and preservation

The automatic observer is test-scoped and enabled only for the exact original title `two browser profiles keep a stale manual-review baseline through an actual 412 before explicit three-way rebase`. A WeakMap shares that same observer with the original second page. Other test titles collect no records and write no observer file.

It records fixed phase names with monotonic elapsed time and the existing result GET's fixed caller/route/method, HTTP status and request duration. An existing202 response is read asynchronously without awaiting or adding a request; only its top-level status is projected to the six-value allowlist. No other response field, identifier, URL/query, header, authentication value, answer/reason, DOM or raw response is retained. Invalid/unreadable/skipped observations retain only booleans.

Bounds are256 phases,64 polls,32 total202 status-read attempts and8 concurrent pending reads. Each callback settles once. Save flips the freeze guard before a write-once `wx` JSON write. Late callbacks are ignored. Page-fixture finally freezes before runtime cleanup; automatic fixture-finally provides setup-failure fallback. Write/parse diagnostic errors preserve the original test verdict. Phase timing includes observation/scheduling overhead, starts at observer fixture entry and does not observe server progress between reads.

BODY-BUDGET-CONTINUITY.json proves all three original test bodies are byte-identical after removing only the single metadata sharing call. Original UI seeding, author forms,412 stale request, actual three-way comparison/rebase, grading revision 3,0.25 score and other null scores remain. Existing helper GET count is unchanged;202 still returns the original sentinel0,200 still asserts status and parses its original result, and the original poll's toBe(revision) remains. No test/assertion deadline, setup budget or fixture scope was expanded. Playwright config is byte-identical:30000ms,1 worker, default retry0. No added request, wait, timer, retry or automatic command submission exists.

The existing read-only peer `/root/publicbf_browser_failure_diagnosis_oct08/grading_observer_static_review` reviewed the final frozen source and found no actionable findings. That reviewer did not run tests. Root separately reported manual no-P1/P2 review; root's independent structured receipt admission is separate from this report. Root's first unstaged-diff coordination guard failure is not a candidate source defect or product test failure.

## Actual validation and preserved failures

| Attempt | Actual outcome | Boundary |
|---|---|---|
| New recording-wrapper startup | exit1 | datetime.UTC unsupported on system Python; setup/tests NOT_RUN; original wrapper/failure preserved |
| Owned offline make setup | exit2 | uv installed37 frozen packages with copy links; npm ENOTCACHED; overall setup FAIL, tests NOT_RUN |
| Initial build01 | exit0 | Independently copied package tree; complete copy hash was not captured, so no fresh-install/reproducibility claim |
| Owned npm ci public01 | exit0 | Fresh install against unchanged lock and explicit public registry; earlier copy superseded; no HOME/CODEX_HOME override |
| First scoped CLI selector | exit1 | No tests found;0 tests/product NOT_RUN; original command/error/receipt retained |
| Corrected scoped native02 | exit0 | Original target once: **1 passed (13.0s)**,30s/1worker/retry0 |
| Conditional full grading01 | exit0 | Original three-test file once: **3 passed (33.9s)**, original per-test budgets |
| Fresh build02 | exit0 | Build after fresh owned public locked dependency install |
| git diff --check | exit0 | Static whitespace check only |
| Local normal candidate commit | exit0 | One-file local commit; no remote mutation |

The only correction between the zero-test selector attempt and actual scoped execution removed the leading grep anchor; source SHA remained frozen. No actual failing targeted test was rerun to manufacture PASS. Conditional full-file execution wasseparately authorized after scoped PASS.

Scoped metadata SHA256 `b7adfb4076c813f41a76a18e33f91c95f34863d0dbc27e2f9f81f6888bc028ab` records 34 phases/5 existing polls/3 status reads, pending-at-freeze0, no drops. The ordinary sequence includes actual202 queued→200 for revision 2 and revision 3. Full-file metadata SHA256 `cdd7cae415f9e23df2f463fb45abc502c1729c198dfaeb5b3ea30a7f86cb8f85` records 34 phases/6 existing polls/4 status reads, pending-at-freeze0, no drops. Exactly one observer file exists for the full three-test run; other two titles are disabled. Both JSON records pass finite schema/key/enum/cap/budget readback and remain unchanged at seal.

Raw stdout/stderr, failure context/images and data stay private. SAFE readbacks retain only fixed metadata, counts, exact raw hashes and footer/line byte bindings. No full log, database, profile, auth value, reason/answer or image waspublished or copied into this report. No archived owner script, host/resource/profile scan, live model, CI rerun/dispatch/cancel, remote push/PR/merge was performed.

## Limits and handoff

This is a diagnostic candidate, not a causal repair or release. Cap saturation, write failure, unreadable JSON, setup-fallback and intentionally late-callback fault cases were NOT_RUN; their bounded structure was reviewed, while ordinary202 projection, freeze and successful write were exercised by native tests. Observed local elapsed time is not a performance benchmark or an explanation for the original CI duration.

Existing CI upload whitelist does not retain grading-two-profile-timing.json. Workflow stays unchanged under this one-file scope; retaining this fixed safe record in a future CI run requires a separately reviewed workflow change. No new CI wasdispatched and no original job was rerun or replaced.

Root can review or later admit local commit `27bd53cada81965152647887d6bc8d18350a1ba7` and the exact private receipts. Public publication/merge and broader source gates remain outside this delivered candidate. M6.3 remains NOT_ACCEPTED.
