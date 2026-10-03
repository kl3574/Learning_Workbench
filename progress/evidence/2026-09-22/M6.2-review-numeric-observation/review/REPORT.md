# Independent review: frozen numeric ledger observations

No remaining definite blocking issue was found in the final eight-file snapshot. The initial P2 owner-boundary finding is closed by the separately pinned Jobs-owner repair. This is static source review plus readback of completed evidence; this reviewer ran no tests, runtime, Provider, network or database operation.

## Source binding

The baseline is e100f1b2ce02ccd0af85e2596b53ba2a24da9cda. Initial seven-file working bytes remain in initial-inputs/initial-pins.json; final eight-file bytes are in fix-inputs/final-pins.json. These pins, not the baseline commit, identify the new code. The initial finding record is INITIAL_REPORT.md and the exact repair delta is fix-delta.patch.log. Subsequent candidate commit identity is recorded separately in git-binding.json; no test-time receipt or untracked Git identity is retroactively rewritten.

Sole authority is PRODUCT_DESIGN.md 3.0.7, SHA-256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d. Supporting source and specification pins are in context-pins.json.

## Standards

**S1 — P2, closed.** The initial review_numeric.py:68-70 directly selected job_events outside the Jobs owner, contrary to PRODUCT_DESIGN.md:349 and Jobs ownership at :2913/:2944. Initial jobs.snapshot already verified the history; this was an owner-boundary violation, not a demonstrated corrupt-history acceptance. The repair introduces frozen AuthoringJobEvent and AuthoringJobRepository.event_prefix in the Jobs adapter. It requires the caller transaction, validates exact workspace/job/revision and complete history through snapshot, then returns only the seq-bounded tuple. The review helper now consumes that port. It neither opens another connection nor writes/repairs history. The original Standards reviewer report is preserved in sibling cache m62-review-numeric-standards-v1; the parent reviewer independently checked this repair. No additional definite standards finding remains.

## Spec and historical correctness

- The catalog facade selects the exact registered owner and revalidates the candidate. Missing registration is not repaired. Generated numeric readers reload current author/session/Policy and call the actual Authoring material owner, which revalidates original checked Provider artifacts, candidate history and exact source material. All reads use the caller's SQLite snapshot; no runtime.prepare/check/run path is added.
- Candidate checks and command histories are taken in actual rowid order; original explicit lists are checked as prefixes after legal later appends. Jobs use explicit original revision/seq prefixes. observed_at controls frozen expiry and rejects future facts; it is not used to infer which rows belonged to a snapshot. The real two-connection WAL test proves that later rows with wall timestamps preceding observed_at do not leak into the caller's older snapshot.
- A later decision does not erase the original preview. Pending observations are reconstructed from the checked original pending projection; approved observations retain the original Job, input, runtime, operation and command ACKs. Old reads never substitute latest results. Full current owner/ledger validation runs before historical prefix comparison.
- Admission, actual-start callback and terminal facts remain distinct. For an old observation, only fields absent at that observation may be omitted from later current facts; present historical fields must still match. Original result data, complete stdout/stderr base64 and output-complete flag are preserved. Numeric/Jobs owners bind candidate, private plan where applicable, runtime manifest bytes/SHA, operation, input, events, start and result. Missing or altered rows/artifacts and changed original output bytes fail closed without GET repair.
- Group question checks use the real private NumericPlan, exact target member and complete immutable group candidate/owner-record SHA. The public question SHA is not treated as a standalone private-solution identity. Private answer body duplication or a new approval identity is not added here; human materials remain owned by the existing material port.
- Required closed observation models inherit safe AuthoringModel and hide repr/validation inputs. Descriptor SHA authenticates only its own bytes. The module explicitly requires a future Review owner to durably authenticate a whole observation before treating it as past review evidence; caller-rehashed DTOs are not proof of when an observation occurred.
- Import reports no_numeric_owner_pipeline with no fabricated ledger. This is not no-mathematics, mathematical/source N/A, numeric PASS or private solution approval. No Review HTTP/UI, review decision persistence, human approval, publication, external Provider proof or new runtime capability is claimed.

## Actual completed evidence

Twelve original stages were read only after each receipt completed. Log hashes/bytes, receipt hashes, before/after inventories and scoped source snapshots were independently recomputed. Original stage01 missing-method failure and stage03 DTO-class equality failure remain in private evidence/. Stage03 was repaired through complete serialized-field comparison without weakening production checks. Source versions across stages differ; all individual before/after inventories match.

| Evidence | Actual result | Source boundary |
| --- | --- | --- |
| 01-owner-red | 1 FAIL, 2 warnings, 1.60 s | 952 inputs |
| 02-owner-green | 2 PASS, 2 warnings, 2.77 s | 954 inputs |
| 03-history-boundaries | 1 FAIL / 28 PASS, 2 warnings, 31.08 s | Earlier test bytes |
| 04/05 | Ruff PASS; mypy 6 product files PASS | Initial product version |
| 06-complete-history-green | 37 PASS, 2 warnings, 41.38 s | Before Jobs-port repair |
| 07-related-numeric-regressions | 56 PASS, 2 warnings, 104.70 s | Before Jobs-port repair |
| 08-final-ruff | PASS, seven files | Before Jobs-port repair |
| 09-jobs-owner-prefix-green | 39 PASS, 2 warnings, 43.71 s | All final eight files match pins |
| 10-owner-history-regressions | 26 PASS, 1 deselected, 2 warnings, 27.82 s | Final; exact original environment test excluded |
| 11/12 | Ruff eight files PASS; mypy seven product files PASS | Final; exact eight-file pins match |

Stages02-12 each retain 954 stable inputs. Counts overlap and are not additive unique coverage. The 56-test regression was not relabeled as a final-version rerun; the final 26-test command explicitly deselected the already completed environment probe. The original group-worker test requires environment_unavailable/BLOCKED, nonzero exit and its exact bwrap EPERM stderr; its passing stage07 result is an environment-block observation, not successful arithmetic. No such runtime was invoked by this review.

The final two added cases (single and group fixture branches) use explicitly synthetic worker callbacks and a synthetic BLOCKED terminal to exercise admitted→callback→terminal observations with nonempty output bytes. They assert that all three old observations remain verifiable, including original absence of actual_started_at. They do not claim that an actual numeric subprocess started or that arithmetic passed. New observation fixtures directly cover single and assessment-question owners; broader old numeric coverage remains separately scoped.

## Limits

This review establishes bounded code/evidence consistency and closes the owner-port finding. It does not authenticate a future ReviewReceipt, independently execute tests, approve mathematics/sources, infer CI success or complete M6.2. The historical descriptor needs future owner-authenticated persistence. No live gate was sampled while running, no secret or runtime database was read, and no main/progress/spec file was changed.

Standards: one initial P2 finding, closed. Spec/history: no remaining definite finding in the final snapshot.
