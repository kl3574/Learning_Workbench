# Fixed 5a owner peer review

Source: 5a41101e9402a137cfc080fec33d8be8b238739d, compared with its fixed parent 3d1ffabf. Sole PRODUCT_DESIGN v3.0.15 SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. This is static review, not application/HTTP execution. No dirty owner files were read. Standards and Spec were separately assessed by the same peer, as the root requested; this does not claim two independent reviewers.

## Standards

No additional confirmed documented-standard violation. Session/Policy, original bootstrap, Provider configuration and Jobs are reached through named owner seams. Whole-workspace checked history and query_only reads are explicit. The new subclass intentionally reuses Jobs lifecycle with an isolated kind; its directory/class name alone is not evidence of wrong ownership. No purely stylistic smell is reported as a blocker. Tooling results are not counted as this peer's review.

## Spec

1. **P2, new, static confirmed: unbound member sequence controls pagination.** codex_turn_repository.py:167–184 validates member bindings but omits sequence; :196 trusts that value. codex_turn.py:182–207 uses it for ordering and the frozen cursor high/position. With two turns, changing only the first member's sequence can move it beyond an existing cursor's high bound without changing checked event/head/Job/hash facts, causing omission or reordering. This contradicts sole :1674 (frozen creation sequence pagination) and :1832 (complete member/version/sequence integrity). Bind and verify the member sequence, or use the already hash-bound prepared envelope sequence; do not repair corrupt rows during GET.

2. **P2, new delivery race identified statically; independent execution NOT_RUN.** codex_turn.py:108–120 authenticates author/Policy inside one deferred read snapshot, then reads physical source material and returns academic request/summary without a fresh delivery check. database.py:43/:53 uses WAL and BEGIN; boundary.py:63–81 adds headers without rechecking authority. A concurrent writer can downgrade/logout the caller during the material read while the old snapshot still returns academic data. Sole :1816 and :1830 require current delivery authority. Exit the material snapshot and freshly check current access before delivery; retain already committed facts.

Known findings from root are retained, not credited as newly discovered: cancellation only increments session revision once (repository.py:146/:246 versus sole :1647/:1758), and oversized material is omitted before physical body verification (context.py:47–50 versus sole :1629). They remain open for this fixed source.

Observed structure: current access precedes replay, original actor gates new preparation, BEGIN IMMEDIATE groups Job/Run/context/control writes, histories compare heads/events/witnesses/members/commands plus independent Job and thread/Run membership, GET uses query_only, and full academic preparation differs from safe control projections. These observations do not establish concurrency, corruption or zero-write acceptance without execution.

The owner subsequently reported a separate fixed 5a+test probe (0c5fea34) with three actual RED cases for sequence, oversized body and GET downgrade. That is owner-reported evidence and is not a test run by this peer. No CLI, model, account, database, external network, or system probe was executed here. No source was edited. Initial 5a is NOT_ACCEPTED; later fixed-source closure must be a separate record.

Summary: Standards 0 confirmed findings; Spec 1 new statically confirmed P2 plus 1 delivery risk awaiting peer execution/closure, and 2 previously known findings. No overall PASS is claimed.
