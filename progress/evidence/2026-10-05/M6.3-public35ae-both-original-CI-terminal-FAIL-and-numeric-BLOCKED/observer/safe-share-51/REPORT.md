# Fixed public 35ae CI readback

This is a documentary candidate packet, not publication approval or phase acceptance.

Source: `35aebd3039241abb3393300affd593f4826a4a0c`. Sole norm v3.0.15 SHA-256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.
Push 37226331207 and pull_request 37226334354 are independent original attempt-1 events. Their exact terminal status, jobs, collection UTC, full original log hashes, bounded results, and actual checkouts are in CI_RESULTS.json.

| Event | Run status | Run conclusion | Jobs success / failure / nonterminal |
|---|---|---|---|
| push | completed | failure | 5 / 1 / 0 |
| pull_request | completed | failure | 5 / 1 / 0 |

Each frontend job reports 1399 passing tests in 166 files. Each backend job reports 926 passing tests and 2 warnings, Ruff PASS and mypy PASS in 287 source files. Each spec-contract job reports 962 passing tests and 2 warnings. Each publication job reports 21354 scanned tracked files. These overlapping gate counts are not added into a unique test total.

Both integration jobs actually report 2467 PASS / 2 SKIP / 2 warnings. Push reports 3176.88s (0:52:56), PR 4230.95s (1:10:30). The exact two skip lines are test_authoring_numeric_runtime.py:46 (BLOCKED_ENVIRONMENT; sealed calculator did not execute, original FAIL retained) and test_restore_numeric_actual_runtime.py:42 (BLOCKED_ENVIRONMENT; sealed Restore evaluator did not return numeric PASS, no fallback). Integration job success does not turn these physical numeric branches into PASS.

Each browser job reports 132 PASS / 1 FAIL. The first Review case at review.spec.ts:36 exhausts the unchanged 30000ms total budget. Push fails at line 68 on setViewportSize after the page/context/browser closes; PR fails at line 67 waiting for the history version selector, with element(s) not found and closed target in the call log. The second delayed old Review response case at line 77 actually passes. Push reports 38.4m, PR 38.5m. Root cause remains UNKNOWN; neither an earlier lifecycle closure nor a later local passing run rewrites these original failures.

The permitted first-Review snapshots are inspected privately and hash bound. Push DOM contains two completed versions with revision 1 selected and academic context; PR DOM says grading state is being read, no completed versions and fixed operation help. Both PNGs show Review question 2 original submitted text and fixed operation help. The push DOM and PNG differ in Agent state; their capture instants are not proven equal. These observations cannot establish a unique timing/navigation/performance cause. Source fixture values match the pinned original synthetic case. The archive, PNGs, full error context, unrelated diagnostics and full failure logs are excluded from this candidate packet.

Both events have real Restore and single generated publication numeric outcome receipts. Every observed actual numeric result reports environment_unavailable / BLOCKED / exit_code 1. Publication is rejected with HTTP 409 / PUBLISH_NUMERIC_REQUIRED. Single generated publication has published=null and final draft state=draft, published_ref=null. Each controlled provider fixture records zero external model calls; single generated publication records one loopback call. This exercises numeric BLOCKED rejection; it is not physical numeric PASS, successful publication, lost-ACK publication acceptance, or academic/pedagogical acceptance. Integration skip reasons and counts are taken only from each integration terminal original log; a missing/nonterminal log stays NOT_AVAILABLE.

Actual push checkouts are proven individually by the original job git-log lines. Actual PR checkouts use 13ea4bd0fc6a427321320a23a5bc7950b16a5560. Independent GitHub commit reads prove both trees are eb81aed69308f89c9913bcc4a85cd32c5c05dd1f; PR merge parents are base e2877101d9c2bda0f793a460db63ef496350c6b4 and source35ae. Run head metadata alone is not used as checkout proof.

A fresh final pure GitHub read confirms source branch head35ae, PR56 open/draft/unmerged with head35ae and base e287. Exact observation UTC and original response hashes are in PUBLIC_SOURCE_STATE.json. This later read does not reconstruct the unknown initial source-push postcheck recorder failure or repush the source.

Original logs, API responses, receipts, artifact ZIPs and selected raw synthetic JSON remain separate and preserved in the private evidence root. Bounded text candidates remove ANSI escapes and replace home absolute prefixes with symbolic prefixes, retaining original line numbers and full raw hashes. API candidates project only relevant status and authority-free Git metadata, with exact original response hashes and read-only command receipts. No authentication token/configuration, real database, profile, model request, screenshot or archive is included.

No remote/source/progress/Issue/PR mutation, CI cancellation or rerun was performed. Old source1a push failure37207897702 and original full412 remain independent historical failures; no cause is assigned or rewritten here. PR publication, merge, M6.3 acceptance and M7 unlocking are not established by this observer.

Candidate creation UTC: 2026-10-04T20:11:11.268280+00:00.
