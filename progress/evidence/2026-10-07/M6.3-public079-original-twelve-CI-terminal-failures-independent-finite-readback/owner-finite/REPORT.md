# Original079 attempt1 — independent terminal CI readback

Both original events and all12 original jobs were read from the sole root collector. This report does not replace any original failure with a later local fix or rerun. M6.3 remains **NOT_ACCEPTED**.

Source public head: `079a008cf88b37e4517cb391503a1e7393ccf374`. Original push checkout is that SHA; original PR checkout is `e9eb82d41dd87649be6c8090c35b5052ccb1319c`, independently found in each original job log. The existing root current079 Git readback records whole tree `eea569fec4f6b3fd209ed96eb29e6d052f0e9b1e`,23175 identical entries. This audit reads and hashes that current receipt; it does not perform a fresh Git comparison/fetch and does not borrow the older1e24ff tree.

**CI working tree before: NOT_CAPTURED. CI working tree after: NOT_CAPTURED.** Git object equality does not supply those missing execution-time facts.

Counts are presented separately for each original job within its event. Repeated suites/events are never added into a distinct-test or platform acceptance total.

## push run37632652743 / attempt1

Original API event terminal: `completed/failure`. Within this event only: 5 successful jobs, 1 failed jobs; other conclusions: 0.

| Job / original ID | API conclusion | Original footer / static result | Original bytes / SHA256 |
|---|---|---|---|
| backend / 112830648507 | success | collected 1114 items; 1114 passed, 3 warnings in 77.81s (0:01:17) | 44701 / `2ac062c4bd1f9fd67a574f91c1f25bc29786ab186f3b2d15c85aea6633d8549d` |
| browser / 112830649019 | success | Running 133 tests using 1 worker; 133 passed (28.6m) | 94213 / `8deb687a4976999399c11b57ff07145d00a50f00dffd43370c9ed30a3743aa0f` |
| frontend / 112830648865 | success | Test Files  167 passed (167); Tests  1421 passed (1421) | 60775 / `0c56ddc5306fb2a09b2b54f6352ce67e5a2fd50ff50c61210b195d5aa691ff33` |
| integration / 112830648805 | failure | collected 2521 items; 1 failed, 2518 passed, 2 skipped, 2 warnings in 2971.49s (0:49:31) | 61542 / `1dbd503c24d44e8e5140ef6e2ac3cf6dd6d193220330d3913b54c7bced03e002` |
| security-publication / 112830649006 | success | PASS: scanned 23175 staged/tracked files against path and credential rules. Manual provenance review remains required. | 21008 / `609b50eb746dfa101ec8ebf688ba384d402af4ebbfbdc4dda5b4c3082f28f67e` |
| spec-contracts / 112830648905 | success | collected 962 items; 962 passed, 2 warnings in 576.45s (0:09:36) | 39638 / `de93bb95b1a197d4ab1a17d432790d82ad55b4cb9e58ec11955e3afdba6eaa27` |

## pull_request run37632662238 / attempt1

Original API event terminal: `completed/failure`. Within this event only: 4 successful jobs, 2 failed jobs; other conclusions: 0.

| Job / original ID | API conclusion | Original footer / static result | Original bytes / SHA256 |
|---|---|---|---|
| backend / 112830674907 | success | collected 1114 items; 1114 passed, 3 warnings in 76.66s (0:01:16) | 45258 / `1ed0891a5f9a293d6571d3063c74441393afdf8be90e583c4d6662d9a499af40` |
| browser / 112830674946 | failure | Running 133 tests using 1 worker; 1 failed; 132 passed (39.9m) | 101263 / `efba20a76cf2bb20085f78000115630aae0df2cabf6f4f61d39d5a27050a88ea` |
| frontend / 112830674842 | success | Test Files  167 passed (167); Tests  1421 passed (1421) | 64779 / `a18b5b24de138522e1d348465c80725bdacf50e40343e12ecce63a4c10c1cb87` |
| integration / 112830674741 | failure | collected 2521 items; 1 failed, 2518 passed, 2 skipped, 2 warnings in 4497.52s (1:14:57) | 63380 / `e1e9a4eac717ab53dd0d8ee6da6f232d53b04209534d6ce1274415f08b552d0e` |
| security-publication / 112830674820 | success | PASS: scanned 23175 staged/tracked files against path and credential rules. Manual provenance review remains required. | 22147 / `cefbe0393d0f4ecfc3aad1eb9afefba1ee7543d26e4d27d1bfdb03437cd1ac31` |
| spec-contracts / 112830674580 | success | collected 962 items; 962 passed, 2 warnings in 575.52s (0:09:35) | 40389 / `9abf31e1ed5c26c1c7872d9cbe7b405ebabfbafef701ba21cfecc1d49946473a` |

## Preserved failures, ENV, and cause boundaries

- Original push integration112830648805: the only FAILED footer names `test_forward_guards_preserve_existing_source_rows_rowids_and_original_http_acks`; the assertion is503==202 at shared `tests/integration/test_codex_turn_consent_http.py:91`. This proves the original full gate failed; it does not reveal the503 cause. Cause: **UNRESOLVED**. No later90c8 patch or bounded subset is used to revise this result.
- Original PR integration112830674741: independently captured63380B, SHA256 `e1e9a4eac717ab53dd0d8ee6da6f232d53b04209534d6ce1274415f08b552d0e`;2521 collected;1 FAIL,2518 PASS,2 ENV skips,2 warnings in4497.52s. Its only FAILED footer names the same forwardguards test,503==202 at the same shared fixture:91; original step exit1. Cause: **UNRESOLVED**. Its count remains separate from push integration.
- Original PR browser112830674946: the only failed test is `review.spec.ts:36:1`, with the reader query URL poll at147:75 and original `Test timeout of 30000ms exceeded`. The30000ms belongs to the whole test; this report does not infer a poll-specific timeout, flake classification, or underlying API/navigation cause. Cause: **UNRESOLVED**.
- Integration footer ENV skips are retained as original CI skips, not counted as PASS: authoring actual sealed numeric runtime did not execute the calculator; actual sealed Restore evaluator did not return a numeric PASS. The markers explicitly retain original failure/no-fallback boundaries. Their runtime cause is not independently established by this audit.

All final integration failed-test identifiers, ENV reason lines, original count footers and step exit lines are retained in FINAL-READBACK.json and SAFE_EXCERPTS.txt. If a final job lacks a completed test summary, its API terminal is reported without inferring unobserved test counts.

## Provenance and finite publication candidate

Final producer snapshot: `98-SNAPSHOT.json` at `2026-10-07T15:15:09.212265+00:00`; SHA256 `a36d00653e16c2a9f5a5fe78dda7986d031f97c10a7441bf318e7a9e1f957013`. Final independent readback SHA256 `f09870316359261715e035304353fc367f6c4dbf891de6833502cd4c07d7687a`.

For each of12 jobs, the independent local reader consumed the complete original stdout bytes, checked exact byte length/SHA256 and empty stderr against the original collector receipt, checked attempt/event/job identity and exact retrieval command, and extracted only explicit approved line classes. Log retrieval exit0 is kept distinct from original test-step exit and job conclusion. Full raw logs remain in the private original collector directory.

Public candidate allowlist: explicit original command/version/footer lines with physical line numbers; reviewed safe failed assertion/test locations and named ENV reasons; byte/hash metadata and projected event/job identity. Excluded: AUTH Case repr, fixture bodies, raw API payloads, unselected raw log lines, ZIP/DB/PNG/profile content, older CI results and later fix/patch results. SAFE_EXCERPTS.txt strips only timestamp/ANSI decoration; its line references point to original physical log lines. Bare future failure IDs omit any unreviewed suffix.

The original early8 seal and the separate11-job stage remain unchanged. This independent reader does not fetch, start a watcher, retry/dispatch/cancel CI, operate a model/CLI, run a product test/probe or modify any checkout. NOT_RUN: new local/full CI/product acceptance or production model execution. Independent host/runtime qualification: NOT_CAPTURED. Whole M6.3: NOT_ACCEPTED.

Root may review the finite candidate before copying it into progress evidence. The private root captures are not in the publication allowlist.

