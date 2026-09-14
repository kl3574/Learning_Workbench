# Bootstrap fixture reset race: bounded public evidence

Original source: `63e47868371c64619d579f3be908125dfa86731f`.

The original local run failed in `practice.spec.ts:87 → helpers.ts:20` before the offline scenario began. Its saved-state assertion encountered a real three-way layout conflict: old baseline/local revision17 versus reset server revision18. The corresponding GitHub job also failed at helpers line20; no CI DOM was collected by this review.

A fresh synthetic practice in an isolated actual API/Vite/Chromium runtime reproduced the mechanism. Clearing localStorage while the old Shell was mounted did not stop its late practice response from restoring scroll and writing an old pending layout. The subsequent page correctly retained that pending version as a conflict. The controlled RED keeps the original five-second assertion and fails.

The applied helper fix unloads the old Shell by navigating to the existing same-origin API `/health` document, verifies actual 200 JSON, then performs the unchanged real GET/PUT CAS reset and cache clear in that non-application document. It navigates back to `/` and retains the original saved assertion. The real-health controlled GREEN passes (1 test,6.7s); the unchanged original practice test pair then passes (2 tests,14.1s). Authentication, product code, CAS, timeout and retry behavior are unchanged.

`fixture/` contains the complete helper before/after and full diff. `probes/` contains full executed-harness derivatives and the RED-to-health diff. `ledgers/` contains only narrow elapsed times/status/version/tab-count/offset/call-stack facts. `logs/` contains necessary error or small test output, with process/path material removed. `experiments/unapplied-neutral/` is a preliminary neutral-HTML experiment; it was not applied to the repository.

For replay, replace `<EXACT_REPO>` with an isolated checkout of the source SHA and `<EVIDENCE_DIR>` with a new temporary output directory in the probe/config templates. `<REPO>` denotes the active checkout used by the original-pair runner; replaying that pair requires applying only `fixture/helpers-fix.diff.log`. Use that checkout's locked runtime installation. Do not run against personal data or occupied fixed ports. Raw SHA and published SHA differ where relocation/redaction occurred; the executed raw bytes were preserved privately. These published templates were not executed again during packaging.

The manifest maps every public payload to opaque original input IDs, raw hashes, public hashes and precise transformations. Absolute input-path mapping is retained outside this bundle. Aggregate/readback/scanner files verify bundle integrity. Automatic scanning supplements manual review and cannot guarantee recognition of arbitrary personal text. No DOM, browser profile, database, auth values or full session payloads is included. Final full-stage acceptance remains the parent run's responsibility.
