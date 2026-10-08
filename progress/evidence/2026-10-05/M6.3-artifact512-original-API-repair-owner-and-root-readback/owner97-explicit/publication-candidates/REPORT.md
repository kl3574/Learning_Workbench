# M6.3 Artifact P2 repair at 51205a75

Fixed source: `51205a75c401911d98d54a42387fbaa43583da7f`; base: `9a2c8d032977411ce94724fd3be33403694c46e1`. Isolated tree: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-owner-oct04`. This previously clean UI preparation tree was explicitly reassigned by root to the two backend P2 repairs. No UI implementation, canonical edit, SSE edit, old profile change, old migration rewrite or remote publication occurred. Sole PRODUCT_DESIGN v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec` remains unchanged.

## Repair and exact scope

Six paths, 258 additions / 4 deletions relative to base:

- `migrations/0035_codex_import_immutable.sql`: nine forward-only guards reject UPDATE, DELETE and conflicting INSERT/REPLACE/UPSERT on the three 0033 source tables. The binding guard covers import_id, source_id, import_job_id and the aggregate_job_id/ordinal pair. Existing 0001..0034 bytes remain exact.
- `services/api/app/application/artifacts.py`: capture the explicitly registered download guard for the checked profile/Job kind in the original transaction, then invoke it after that transaction has exited. Guard registration cannot refer to an unregistered reader.
- `services/api/app/application/codex_artifacts.py`: the Codex owner uses the existing fresh `_deliver(..., subject=True)` transaction for current actor/workspace/author/Policy.
- `services/api/app/main.py`: explicitly registers that guard only for the Codex output profile and codex_turn owner. Ordinary Import reader admission is unchanged.
- `tests/integration/test_codex_artifact_repair_boundaries.py`: 22 actual SQLite/HTTP boundary cases, including nonempty prior-catalog upgrade, all binding conflict identities, real role/logout/independent/open-book changes after original download transaction exit, and ordinary learner download preservation.
- `tests/integration/test_codex_import_owner.py`: only seven explicit trigger removals in intentional corruption fixtures; original readback assertions remain.

## Original RED and repair history

All commits retain M6.3 in their messages. Original raw failures, source copies, commands and complete before/after maps are preserved, never relabeled as PASS.

| Run | Fixed source | Actual outcome |
| --- | --- | --- |
| migration-red-01 | 38685c693d602f98dd8b7cd953dd7844301a8dc5 | 12 failed, exit 1 |
| migration-green-01 | 97785644935f1a9f9d7de858116546f00a6a2b41 | Same migration test source plus existing Import owner tests: 51 passed, exit 0 |
| delivery-red-01 | e8ec33be6e8f0094ebb1136ec0c5547d2fd054f8 | 2 failed, exit 1; learner/logout changed by HTTP, original download still returned 200 |
| delivery-red-02 | 236bf2ef8db02e65f343da1d0d6ab00dff1aab3b | 4 failed, exit 1; adds actual independent/open-book HTTP admission |
| delivery-green-01 | 48346a3feb4bd05d3b5676b33125d869d5d3c372 | Exact red-02 test file: 4 passed, 39 deselected by `-k download`, exit 0 |
| fixed-boundaries-01 | 51205a75c401911d98d54a42387fbaa43583da7f | 22 passed, exit 0, 49.993 s |
| fixed-focused-01 | same fixed 51205a75 | Original 75 plus 3 controls: 78 passed, exit 0, 81.750 s |
| fixed-related-01 | same fixed 51205a75 | Original adjacent gate: 263 passed, exit 0, 408.348 s |

Migration RED is specifically ten statements that did not raise plus two DELETE attempts already rejected by FOREIGN KEY constraints but lacking the required immutable guard. It does not mean all twelve mutations silently changed stored rows. The initial delivery-red-01 test had an unreachable ROLE_REQUIRED error-code expectation behind the failing 200-vs-403/401 assertion; red-02 corrected it to the actual POLICY_DENIED before production repair. Its original source/log remain intact. The migration function and all red-02 test function bodies remain exact in the final file; later additional coverage is recorded by SOURCE_BINDING.json. The three raw RED logs can contain synthetic fixture authentication repr and are excluded from publication; RED_HISTORY.json contains only their original hashes and reviewed failure summaries.

Final six static checks: Ruff, mypy (285 source files), generated contract check (82 artifacts), specification verification, strict generated TypeScript, and git diff --check all exit 0. Counts from overlapping historical runs are not additive and do not represent a full Python/Web/native run. The last product gate finished at `2026-10-04T15:11:09.703389+00:00`.

## Input and evidence binding

All fourteen runs retain command.json, receipt.json, test source copy, raw run.log and complete source-before/source-after maps. All pairs are identical, all listed bytes match their fixed Git blobs, and all runs have a clean tracked tree. The first test-only RED has 1458 nonprogress inputs; the subsequent fixed heads have 1459. The final tree has 1459 inputs, including exactly six changed/new paths and 1453 unchanged prior inputs. SOURCE_BINDING.json binds the exact delta and unchanged historical migrations. FULL_GIT_MANIFESTS.json independently augments the original maps with complete mode/type/blob/size/SHA256 across six fixed heads, checks 1447 distinct Git blob objects, and verifies every current input byte. The original maps are unchanged. The audit command and terminal are recorded separately in AUDIT_RECEIPT.json and audit.log.

Independent reviewer closed the original two P2s statically with no new findings in `m63-artifact-p2-delta-independent-review-oct04/REVIEW.md`, SHA256 `bd85630bf7964a0ebda3e03b1a4bd22908204f16a45087aacba92f1461235473`. That separately sealed review admitted the original five stages and final 22 tests; it still described 78/263 as RUNNING at its intake. Their later actual PASS receipts above are separate later evidence, not retroactive changes to that review. Original 9a OPEN review and original API evidence seal remain unchanged.

## Explicit limits and sharing

These tests use normal local HTTP/SQLite, real Import owner staging/parser, controlled files and a deliberately registered synthetic memory model peer. They do not establish actual Codex CLI/model execution, arbitrary host process isolation, real account costs, UI completion, mathematical/source/pedagogical approval, whole M6.3 acceptance or publication. No model/CLI/network/host security diagnosis was added. UI work remains awaiting root's combined fixed API/UI base.

The explicit candidate allowlist contains only reviewed source, runner, receipts, successful logs, immutable Git maps and selected safe RED summaries. Text candidates permit only the exact `<LOCAL_HOME>` to `<LOCAL_HOME>` substitution; each raw and candidate SHA256 is bound. No raw failed log, DB, cookie, credential/key, cache, tmp contents, browser profile, binary archive or unlisted file is eligible. Candidates are for root's independent readback; this is not remote publication authorization or a publication claim.
