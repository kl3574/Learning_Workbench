# Static P2 closure: 00cb5ae4

Fixed comparison: db14d96ef03ea1ca7a9a75a9001f6cc0a3282973...00cb5ae4cf9cd157212374bf636f5086f5f6160d (a6f09fd8 then 00cb5ae4). The owner confirmed the fixed candidate; read-only HEAD/status agrees it is clean. Three changed files and necessary router/error-handler/spec context were reviewed.

## Standards

No new blocking finding. WorkbenchStaticMount.matches (interfaces/static.py:6-11) declines only reserved HTTP paths /api, /api/* and /health, using the same scoped get_route_path helper as the pinned Starlette router/static implementation. Other matches delegate to Mount, so ordinary static behavior is retained. main.py:237 registers that specialized root mount in the existing final position. This is a small adapter for the actual matching boundary, not duplicated HTTP routing or a new endpoint. It prevents the later FULL static match from overriding the earlier API PARTIAL method match.

The original P2 is closed at the static implementation level. test_local_boundary.py:14-15 now makes the general fixture explicitly absent-static, and :201-238 independently covers both absent/present directories. The present branch contains an API shadow index, yet retains exact JSON 405 for the unsupported sessions GET, 404 for unimplemented turns and unknown API, POST /health 405, and a readable synthetic homepage. It does not merely pin all tests to the favorable absent-dist environment. The regression tests and root-reported RED/GREEN were not executed by this reviewer; no separate asset, root-path deployment or full security execution is claimed.

## Spec

No new finding. The mount exclusion does not add an API route, session list, turn, permission or Codex operation. Existing registered bootstrap routes remain unchanged; unsupported API paths are handled by the existing router and safe HTTPException mapping rather than static HTML. This preserves §20.16.1 (:1372), §20.16.2 (:1378), and the exact POST/GET session scope (:1434-1435). The former db14 OPEN finding remains sealed separately and its original 823 PASS is not relabeled as covering a built-static environment.

This is a static review, not application or test execution. No application, DB, browser, network, CLI/model, system probe or previously rejected diagnosis was run. Product sources were not changed. One reviewer applied separate Standards and Spec axes; the earlier subagent attempt reached the thread limit, so this does not claim two independent reviewers. Reported producer/root test outcomes are not credited to this reviewer. The sole v3.0.14 PRODUCT_DESIGN.md remains SHA256 bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144. Earlier DCF complete-gate failures and unexplained setup errors are not reclassified here.
