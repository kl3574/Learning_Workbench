# Restore numeric backend — fixed development evidence

Final backend: `ea3d92ae6a54b4b2b2d9c1e40e6ecb9232fe9ffa`, CLEAN isolated worktree `$HOME/.cache/learning-workbench-acceptance/m62-restore-numeric-backend-oct02`. Approved sole specification is v3.0.12 §20.14, base `50f80c14`, SHA-256 `1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7`.

Implementation commits to integrate: `4a89abb9` then `ea3d92ae`. Their parents contain equivalent cherry-picks of the contract agent's DTO `a9325f48` and transport `34bb546d` (local equivalents `f589d784` and `4956e55b`); do not duplicate those. Later frontend/generated/projection-count commits from the contract agent are deliberately not cherry-picked here, since they depend on its frontend support chain. Root owns combined integration, frontend, final generated route inventory, and full-product gates.

## Implemented boundary

- `application/restore_numeric_models.py:21`: exact original Unicode codepoint spans, JSON-number lexical and finite binary64 value binding; no normalization, automatic extraction, semantic formula approval, arbitrary code or Provider use. Binding SHA includes workspace, actual Restore record/source/body identities, complete material. Out-of-body range is 422; valid-shaped unprovable material is 409.
- `migrations/0025_restore_numeric.sql` and `infrastructure/restore_numeric_repository.py:60`: immutable material, preview/decision/admission/start/end/command event chain, independently checked head/check/command/Job membership; UPDATE/DELETE/REPLACE and secondary unique-key replacement are rejected. Heads advance by strong CAS. Missing/tail-truncated/entire deleted ledger tables and single-sided corruption fail closed; GET never repairs.
- `application/restore_numeric_service.py:38,78,114`: separate preview and one-shot approval. Preview/decline perform no execution. First binding/preview/ACK and approval/Job/ACK are atomic. 100 previews is a lifetime bound. Original-key replay authenticates current permission and original complete history but preserves the original ACK after expiry or base/runtime advancement. New preview/approve/start require the original still-current base and unpublished Restore. Safe Jobs read/list/cancel returns no subject material under learner/Policy restrictions.
- `application/restore_numeric_worker.py:68,129` and Jobs `claimable_numeric`: explicitly registered `restore-numeric-job-v1`, bounded fair scheduling, checked lease/admission, actual start, terminal output bytes, crash recovery without repeated execution. Current changes after actual start preserve the real terminal; publication separately performs CAS. Fixed evaluator and sealed runtime remain fail-closed.
- `application/restore_review_numeric.py:53,96`: distinct `restore-review-numeric-observation-v1`, original Restore/material hashes and full ordered commands/Job input/events/start/end/output facts, with no fabricated generation/Provider identity. Historical observations verify their original prefix; new Review observes the current complete endpoint. Existing v1 observations and receipts remain unchanged.
- `application/review_numeric.py:209`, `publication_admission.py:88,161`, `draft_publication.py:128`: first worked-example publication requires a fresh matching complete ledger endpoint and latest genuine PASS plus new explicit human decision. New pending/decline/FAIL/BLOCKED blocks earlier PASS. New `restore-numeric-publication-admission-v1` directly records material/check/observation hashes, and `restore-numeric-publication-v1` preserves those facts atomically with the normal current+1 Content publication/impact path. Original published ACK verification uses the historical committed observation.

## Actual gates and exact source scope

Every capture directory contains the exact command, start/end, exit code, raw log, and before/after SHA-256 list. Source was unchanged during every gate.

| Stage | Actual result | Source qualification |
|---|---|---|
| `owner-port-final` | **56 PASS**, 56.37 s | Final commit's complete 14,349-file source input set: new Restore service/worker/publication/integrity/migration tests |
| `owner-port-static` | **PASS** Ruff; mypy **234 files**; git diff whitespace | Same exact final input set |
| `owner-port-physical` | **BLOCKED_ENVIRONMENT**, pytest 1 skipped | Same exact final input set; real HTTP + actual sealed launch, no fallback |
| `focused-final` | **90 PASS**, 111.72 s | Prior source phase: 53 new plus 37 existing Restore tests |
| `regression-final` | **274 PASS**, 399.76 s | Same prior source phase: existing Single/Group numeric, Review, Import/Edit publication/admission/ledger/migration tests; test-owned synthetic loopback fixtures only, no configured or external Provider |
| `runtime-regression` | **39 PASS, 1 environment skip**, 1.05 s | Same prior source phase: existing fixed finite arithmetic and runtime tests |

The prior phase differs from final in exactly three files: `application/restore_numeric_worker.py`, `infrastructure/authoring_job_repository.py` (the bounded Jobs-owned scheduling port), and `tests/integration/test_restore_numeric_integrity.py` (three secondary-key REPLACE negatives). `FINAL_READBACK.json` records this distinction; earlier totals are not presented as a second full final-source run. The new scheduling port and entire Restore chain were then tested on final source by the 56-test gate. Runtime runner bytes are unchanged between these two phases.

`SOURCE_BINDING.json` verifies every final working file against its committed Git blob and all three final captures. `FINAL_READBACK.json` verifies CLEAN HEAD, canonical spec, unchanged 0001 and 54-core source bytes. My two backend commits do not change spec, progress, frontend, original migrations or generated contracts.

Meaningful coverage includes competing first materials and one-shot decisions, full 100-preview quota, Unicode/combining/decimal anchors, wrong literal/quote/plan, original ACK versus current read, restart and committed launch recovery, current race before/after actual start, learner safe control, historical actor workspace, corruption/tail/all-delete across all new ledgers, primary and secondary-key REPLACE, wrong full stdout, and atomic rollback after material/Job/Content work. Genuine pre-0025 Restore v1 Review/publication records survive migration byte-for-byte and remain readable through the new composition; failed migration rolls back schema and data. Parent Lesson pin and exact restored body bytes are preserved in the synthetic publication chain.

## Actual sealed execution limitation

`owner-port-physical/physical-probe.json` preserves full versioned input, original 353-member manifest, start/end and stdout/stderr bytes. Actual transport was preview 201, approve 202, worker claim/launch, GET 200. The process actually started and exited **1** with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. The persisted outcome is `environment_unavailable`, verdict `BLOCKED`, failed Job, and no fabricated assertions. There was no fallback. The physical calculator has **not** achieved PASS on this host. Earlier physical stages preserve the same environment boundary separately.

SyntheticExecution tests exercise actual SQLite/HTTP/Jobs/Review/Content protocol with clearly labelled synthetic runtime outputs and synthetic human intent; they are not physical sandbox, academic correctness, source-quality or pedagogy acceptance. Full Python suite, full Web/native gates, and external Provider calls were NOT_RUN in this backend slice. Final route-generation and frontend integration are owned by the contract/root agents; this branch already contains and exercises the three real transport handlers and main composition, not unregistered placeholder routes.

## Preserved red development evidence

- `initial-service`: 14 fixture setup errors because the first fixture omitted strict existing symbol fields/variable unit. Corrected fixture, no contract weakening.
- `service-02`: 14 failures exposed Pydantic subtype equality between structural AuthoringCandidate and core DraftCandidate. Fixed named owner boundaries to compare complete normalized core identity; no ID-only fallback. `service-03`: 14 PASS.
- `integrity-01`: 19 PASS / 1 test assertion failed: physically changing the active actor's workspace safely returned 404, not expected 401/403. The assertion was corrected and a separate true historical numeric actor workspace negative added; final verifies 409 with another valid current author.
- `publication-migration-01`: 15 PASS / 2 fixture setup errors (missing required artifact-reader registration argument). Fixed the fixture and reran genuine legacy migration: 2 PASS.

All original logs, source hashes and exit codes remain intact. Independent contract/HTTP review runs live in the contract agent's separate evidence scope; no unreceived review result is claimed here.
