# Bounded PDF parser-exit race diagnosis and fix

The isolated candidate is committed as `d4d018bc33a98328fc8bb2f21ab06adf78364803` (parent `2ab067b9d832c0aa64699a9a56e879d2ab6c6ac5`). Only `services/api/app/infrastructure/import_worker.py` and the new `tests/integration/test_import_parser_exit_race.py` changed; the detached worktree is clean. No root/progress/remote changes were made.

## Observed mechanism and limits

The actual parent `poll(0.1)` returns false. Before the parent checks liveness, its real child sends a complete typed parser envelope and exits normally. The old code immediately raises `IMPORT_PARSE_FAILED`, leaving the ready envelope unread. The four-line fix checks the pipe once after observing the dead child, then returns to the existing receiving/validation branch. It changes neither deadlines nor error DTOs. Stop still wins before this check; EOF/no envelope still fails closed. Publication continues to recheck ownership/Policy in `complete_preview`.

The permanent HTTP regression gates the real spawned parser with an Event, preserving the actual false poll observation. It releases and joins the real parser, whose natural exit and real received `PDF_NO_EXTRACTABLE_TEXT` envelope are asserted. It calls the unchanged original scan-PDF HTTP test, retaining OCR/page locator, original bytes, zero published content and restart assertions. The separate empty-child fault control deliberately produces EOF without a result. The stop control leaves the running lease recoverable and consumes no envelope. These are explicit scheduling/fault controls, not a real CI scheduling trace.

The earlier b90 push CI integration failure (run `35692894284`, job `106633474101`, actual checkout `b90b4446172b39a3858a9684437920c27eda01ae`) failed the same original assertion at `test_document_http.py:169`, but its log lacks pipe and child-exit observations. Its root cause is **not proven** identical. The CI log is retained in the sibling `m62-pr55-b90-terminal-readback-v1/terminal-job-106633474101.log`, SHA-256 `b0fd5e55ea2d60b00098299ffe32e26a9cc4ecd6151f81d3ca8aee775271c225`. No Tutor/grading causality claim is made.

## Actual checks

| Receipt directory | Actual result | Input scope |
| --- | --- | --- |
| `01-original-baseline` | Original exact scan-PDF HTTP case PASS | 947 source files unchanged |
| `02-poll-exit-gap-red` | Original case + actual scheduling probe FAIL at original line 169 | 947 source files unchanged; probe separately pinned |
| `03-poll-exit-gap-green` | Same original case/probe PASS; actual typed error envelope received | 947 source files unchanged; identical probe |
| `04-original-candidate-control` | Original case without scheduling probe PASS | 947 source files unchanged |
| `05-static` | Candidate product Ruff and mypy PASS | 947 source files unchanged |
| `06-permanent-red` | **1 FAIL, 2 PASS** on original production bytes | 948 source files unchanged, new test Git blob null |
| `07-permanent-green` | **3 PASS**, 2 deprecation warnings | Same test bytes; 948 source files unchanged |
| `08-related-document-worker` | **19 PASS**, 2 deprecation warnings | Exact command in receipt; 948 source files unchanged |
| `09-permanent-ruff` | Both changed source files PASS | 948 source files unchanged |
| `10-permanent-mypy` | Product file PASS | 948 source files unchanged |

These are focused checks, not a full backend or CI acceptance claim. Earlier and permanent cases overlap; their totals must not be added as unique acceptance coverage. The original failure logs and source snapshots are retained. No test assertion or product timeout was weakened. Real synthetic private databases and processes were used without shared HTTP ports, credentials or vendor calls.

## Reproduce the permanent behavior

From the isolated worktree with project Python 3.12 dependencies:

```text
python -m pytest -q tests/integration/test_import_parser_exit_race.py -p no:cacheprovider
```

`06-permanent-red/source/` stores the original production file plus this exact test; `07-permanent-green/source/` stores the fixed pair. Each run receipt records its command, timestamps, exit, raw log SHA/bytes and before/after input inventory. `committed-inputs.json` binds all 948 final source files to their actual Git blobs and proves their bytes equal the GREEN input set; original null precommit Git identities were not rewritten. `changes.patch` contains the committed two-file change. Temporary databases, pytest caches and mypy cache are private execution data and are not publication candidates.

Specification: PRODUCT_DESIGN.md 3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.
