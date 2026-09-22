# M6.1 question/solution structural precheck evidence

This evidence covers a reusable internal structural check and its Import integration. It does not implement question generation or close M6.1.

Sole specification: `PRODUCT_DESIGN.md`, SHA-256 `30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924`; R-22/R-24, sections 5.3, 12.4, 13.1, 20.1 and 20.8. Tested base HEAD: `80986eaed01d4de620cdd4320a7fab8ce01ce959`, with the three uncommitted paths identified in `patch/source-files.json`. This pack is a publication candidate; it does not assert that the patch was committed, merged or published.

## Change and review

The pure helper accepts already validated `QuestionPublic` and `SolutionPrivate` models, checks exact question identity/hash, preserves existing grader compatibility and duplicate rules, checks selected option IDs and finite numeric expected answers, and leaves inputs/review status unchanged. Import already checked exact references and duplicate public identities before the extracted rules; its `PACKAGE_INVALID` behavior is preserved. Multiple accepted answers and historical question/solution revisions remain legal.

The first scoped mypy run failed because a loop variable inferred as `QuestionPublic` was later assigned an optional lookup result. The first loop variable was renamed `supplied_question`; the runtime rule did not change. The original failure log, receipt and source remain under `failures/mypy/`. The final full patch and test source are under `patch/`; the independent static review is recorded separately in `source-review.md`.

No HTTP/DTO/provider/generation-type, database migration, permission, approval, grading, publication or user-interface behavior was added. The helper does not require a solution for every question and is not a generation completeness validator.

## Actual checks on the final source

| Recorded run | Result |
|---|---|
| `pure-and-package-final` | 38 passed in 0.10s: 27 pure cases and 11 actual-package regression cases |
| `import-regressions-final` | 145 passed in 26.19s across six existing Import/package suites; 2 existing dependency warnings |
| `ruff-final` | PASS for all three owned paths |
| `mypy-final` | PASS for the two application source files |
| `diff-check-final` | PASS for the tracked Git diff; untracked files were checked by Ruff |

The 38-case and 145-case selections are reported separately. They are bounded regression evidence, not a full-suite or broader product acceptance result. The original mypy FAIL is retained alongside final PASS; preparing this public derivative did not rerun tests.

The two warnings are the Starlette/httpx test-client deprecation and the AnyIO BlockingPortal alias deprecation. Exact commands, working directories, timestamps, exit codes and original log digests are retained in the receipts. Interpreter hash and installed-package versions are in `shared/environment.json`; this is not a byte-level closure of all installed dependencies.

Every final run observed the same 905 declared repository inputs before and after, including unchanged bytes, modes and timestamps. Scope: all tracked files excluding `progress/`, plus the two new files. Final aggregate: `ae9bf39f2be03ad79f21b3d3533f00002489ac2f108c4db7bd6d38f15fccda02`. Original mypy aggregate: `1df83fe846a814ae5c4211729432d1b0c5eb11bf7346e67260e5f0a5557b7395`. Only the three owned paths differ from the original Git index.

## Exact aliases and redaction

`manifest.json` lists original and public SHA-256, byte counts, per-file fixed HOME replacement counts, and raw relative-path aliases. The only literal redaction replaces the single fixed local HOME prefix with `<LOCAL_HOME>/`; the original prefix is hash-identified in the public manifest, and its exact private rule remains in the private preparation audit. No result, time, command option or original digest was changed.

Receipt `logs` fields still identify the original log bytes. Use `manifest.json` to resolve them to their public derivative and public SHA; a redacted log is not claimed to match its original digest. The same rule applies to the driver hashes recorded in final receipts. All empty streams alias `shared/empty.log`; all six identical environment records alias `shared/environment.json`.

The 12 original before/after snapshots are losslessly represented by `inputs/files-final.json` and `inputs/snapshot-aliases.json`. Each alias preserves its own observation metadata and original/logical SHA and size. Reconstruct its files by taking the 905 base rows in order and replacing rows by path from `file_row_overrides`; only the pre-repair mypy snapshots have one override. Append `files` as the final metadata key, serialize using Python `json.dumps(ensure_ascii=False, indent=2)` plus LF, and require exact equality to the alias's `sanitized_logical_sha256` and byte count. Those snapshots required zero HOME substitutions. The aggregate hashes retain their original scope and were not recomputed over public document formatting.

Manifest `files` inventories every public payload except the manifest itself; the private preparation audit binds the manifest SHA and all intended repository targets. The repository publication scanner was applied to every candidate at its intended path. This bounded pattern scan supplements the explicit synthetic-content/provenance review and does not itself publish or authorize anything.

All pytest temporary directories, databases, profiles, runtime/session/secret data and unrelated history are excluded. Earlier successful pre-repair runs remain private; the actual first mypy failure and final five checks are included.

## Remaining limits

Full Python suite, browser, hosted Provider, numeric isolation, mathematical/source/pedagogical checks: NOT_RUN for this patch. Structural success does not establish mathematical correctness, plausible distractors, sufficient conditions, unit correctness, learning-goal alignment or completeness of answers.

Further Authoring output types still require their explicit prepare/candidate/group/reference/ownership/content-plan contracts and implementation in the sole specification. These checks do not create approvals, publish content, or update learning evidence. M6.1, M6.2 and M6.3 remain separate delivery scopes.
