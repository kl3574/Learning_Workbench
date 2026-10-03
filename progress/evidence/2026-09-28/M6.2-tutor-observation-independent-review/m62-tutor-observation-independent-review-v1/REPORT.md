# Independent Tutor observation review

Result: no blocking finding in the reviewed change. Candidate `ab11b811867bb1c30166491279ada5ae20934886`, compared with `416b53261dafa0ddbdec3adf4ef2deab058b866b`, is suitable for integration and the next combined gate. This is a bounded, read-only source and existing-evidence review, not an independent rerun of its tests or a verdict that the historical CI timeout is fixed.

Reviewer: `/root/quality_repository_finish`. Sole product/engineering specification: `PRODUCT_DESIGN.md` 3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. The reviewer read the specification and all 14 changed files, using full diffs plus surrounding source for existing files. The candidate worktree was clean before and after this review. No product or test source was edited. No provider, credentials, publication, or push operation was performed.

## Code and specification findings

- Browser observation is explicitly opt-in. Ordinary client reads and generated SSE consumption retain their original path; enabled observation labels accompany existing GETs. Metadata uses bounded, closed primitive fields and validates stage, Run, epoch, request span, cursor and counters. No answer, prompt, caller DTO, exception text, cookie or credential header is recorded by the new recorder. One unresolved sink cannot create an unbounded delivery queue.
- Hook records respect the existing operation/scope guards. Accepted read snapshots and applied validated events receive exact source tokens, carried to the current DOM projection. Source matching requires a unique epoch/ordinal plus equal Run, sequence, revision and status; duplicates and absent observations do not become evidence of progress.
- Browser, API and Node clocks are explicitly separate. The diagnostic freezes only metadata already delivered to Node when the original assertion returns. Later Run/API/browser snapshots are separately labeled; they cannot establish state at the earlier assertion deadline. The original failure object is rethrown even if collection fails.
- The API observer is composed only in the isolated test factory. It binds the actual first successfully started Run and rejects pre-bind records. Request UUID and validated nonauthoritative correlation label remain distinct. Owner wrappers preserve their underlying return/exception behavior; ASGI frame metadata says a send returned, without claiming browser consumption. It never decodes or retains frame data.
- The optional TutorWorker observer defaults to None and is called after the terminal transaction exits successfully. Early return, failed transaction and rollback do not emit a terminal committed signal. Callback exceptions are contained outside the completed transaction. Existing auth, Policy, consent, ACK, Jobs and persistence owners remain in place.
- The original native test, Playwright configuration, generated SSE codec, generated API client and CI workflow are byte-identical to the base. The original completion assertion keeps its 5000 ms expectation and the recorded original run used `--retries=0`.

## Evidence independently checked

`verify.py` recomputed all 965 engineering source entries against actual candidate Git blobs and the clean working tree. All seven final stage before/after manifests match those blobs. It checked all 1,433 raw-index entries, every one of the 44 stage log/receipt pairs and each saved source file against its stage manifest. Historical intermediate source is checked against its own recorded manifest, not falsely represented as final-source coverage.

Existing author-run outcomes, whose logs and exact source bindings were reviewed:

| Stage | Actual result | Scope |
|---|---|---|
| 37 | 6 passed, 2 dependency warnings | Real SQLite/HTTP/controlled loopback observer cases after the pre-bind repair |
| 39 | Ruff passed | Four changed Python files |
| 40 | 22 passed in four files | Focused browser-client/hook/state unit cases |
| 41 | Passed | Web TypeScript lint/unused checks |
| 42 | Passed | Native strict TypeScript using a private alias to the installed Playwright declaration |
| 43 | Passed | TutorWorker mypy, one source file |
| 44 | 57 passed, 2 dependency warnings, 15.26 s | Five Tutor integration/contract test files |

The original native stage 31 passed its one unmodified case once, with six production files exactly equal to the final candidate. Its artifact SHA-256 is `5571d63ddb42851828a7c1d15533465f26f53746170337f48d10bf104f4000f9`. Independent recalculation confirmed 33 browser source records, 248 Node events and 10 exact DOM/source matches were delivered before the assertion freeze; a completed DOM projection has seq 6 and Jobs revision 6. This source matching was recomputed rather than trusting the saved `matched_source` booleans.

Stage 31's post-assertion API mechanism component is **failed/rejected**, because the old test recorder admitted pre-bind records. It is not a successful API timing observation. The later recorder repair has HTTP RED/GREEN coverage, but the original browser case was not rerun after that repair. Stage 35 is a controlled `setContent` diagnostic test and logged Vite port 5173 already in use; it is not proof of a clean application startup. Stage 38 exited 4 with zero tests because the requested path did not exist; the corrected command is separately preserved as stage 44. All these records remain unchanged.

## Limits and next task

No historical CI failure mechanism has been reproduced or resolved by this review. No new exact-head CI, full platform gate, real vendor invocation, independent content-quality approval or final M6.2 acceptance is claimed. Private raw evidence contains local paths and synthetic test session/CSRF representations; it is not cleared for publication.

Next task: integrate the reviewed candidate, then run the complete native gate once at the parent-specified combined commit using the unchanged configuration, preserving raw failures and original/produced screenshot bytes. This review artifact itself does not execute that gate.

Evidence: `source-pins.json`, `evidence-verification.json`, `source/`, `verify.py`, and `manifest.json`. Author originals remain in the adjacent `m62-tutor-ci-observation-development-v1` directory.
