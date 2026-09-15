# Recommendation maintenance read-only admission repair

The checked no-work maintenance path now uses a deferred SQLite read transaction. Actual work leaves that snapshot, enters the original writer transaction, and rechecks current Policy, ledger, inputs and publication facts. The complete original writer/catch suffix is byte-identical. Content, Reader and their delivery Policy guards are unchanged by this repair.

This closes a demonstrated independent lock mechanism. The earlier conditional accumulated synthetic database profile observed a real no-work writer transaction holding 169.81 ms and overlapping Content admissions waiting 178.69/228.71 ms. It did not reproduce the original CI five-second timeout or prove its unique cause. This focused repair adds no browser delay, timeout extension, cache or source-validation exemption.

## Actual results and preserved failures

- `red-01`: driver failed before pytest because system Python lacks datetime.UTC. No product execution; initial driver and error retained.
- `red-02`: 3 failures / 15.46 s, observer incorrectly treated Database.connect's context manager as a connection. Actual contender-BEGIN observation was never reached; not a product RED.
- `red-03`: original production, 3 actual lock-mechanism failures / 3.50 s. Actual SQLite trace observed BEGIN IMMEDIATE attempts while real basis_current=True maintenance was held; lesson, outline and source publication could not complete before release.
- `green-04`: 2 pass / 1 fail / 0.41 s. Both GET mechanisms passed, and source publication, dirty preservation and next-tick refresh completed. Only the last test assertion incorrectly expected catalog to omit the old course revision; real catalog retains r1 and r2. Original log/test source retained.
- `focused-05`: 39 pass / 17.75 s: 10 new readiness tests plus 29 unchanged Recommendation integration tests; 2 pre-existing dependency deprecation warnings.
- `same-test-red-06` → `same-test-green-07`: exact final test bytes and same selected 3 cases; original production 3 fail / 3.49 s, repaired production 3 pass / 0.39 s; 7 controls intentionally deselected. Original source restored only inside a bounded counterfactual window, then finally restored to exact repaired hash. The restoration receipt is retained.
- `ruff-08`: the two owned files pass Ruff. `mypy-09`: the owned production file passes mypy. These are static checks, not additional service-test executions (the generic driver scope string is supplemented by these exact command scopes).

The real SQLite controls verify publication of source r3 after classification saw dirty r2, writer-lock ownership at actual publish, another worker finishing between phases without duplicate publication, independent assessment Policy before read and between read/write, read failure retaining the snapshot and recording the existing retry warning, future retry performing checked reads before suppression, expiry recovery retaining original generation time for unchanged basis, and unknown RuntimeError propagation with zero writes. The corruption/retry case deliberately combines a bad sequence with inconsistent retry/failure fields; checked encounters the history fault first. It proves corrupted state cannot bypass checked, not isolation of one fault field. Existing Recommendation tests additionally cover time-triggered work, same-basis decisions, original ACK/CAS, failure recovery and stopping rollback.

The 1-second completion assertion is a bounded lock-independence observation while an Event holds a real checked transaction; it is not a performance SLA or simulation of the CI timeout. Every gate releases in finally. No secrets, Provider credentials or user data were used; test content is synthetic and unreviewed, with no expert-approval claim.

## Limits and risks

A concurrent source change after the read snapshot may cause one no-work return; the test proves dirty state survives and the next tick refreshes it. Genuine work pays an extra read classification, then repeats all original writer-side validation. The read path makes no public subject projection and never clears dirty/failure state. Expected exceptions retain the original guarded failure/retry path; unknown exceptions still propagate. This agent ran no full suite or browser tests for this backend repair; root owns combined acceptance.
