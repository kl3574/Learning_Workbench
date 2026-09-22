# Bounded independent backend review

One blocking finding confirmed by one cache-only reproduction. No product source or tests were edited. No browser, native acceptance ports, remote actions, vendor request, calculator execution, CI rerun, timeout change, or system policy change occurred.

Source: `m61-groups-active`, HEAD `bebf80601b3debf788d446ed2b3abf0847b392bc`, uncommitted group implementation against PRODUCT_DESIGN 3.0.7 SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. The 32 explicitly declared source/test/spec files have identical before/after SHA256 fingerprints. Twelve additional read/dependency files have end-only snapshots; this is not a whole-tree stability claim.

## P1: Group numeric access accepts damaged original Provider history

Primary location: `services/api/app/application/authoring_group_numeric_service.py:23-27`. `_candidate_history` checks the Authoring candidate/source records and frozen Context, but never calls the Provider owner's checked result reader. Protected preview, read and decision all use that incomplete check (lines 54, 95, 106).

The same omission reaches execution admission at `services/api/app/application/authoring_group_numeric_worker.py:78-89`, called immediately before `repo.begin` at lines 163-164. `GroupNumericRepository.candidate` (`services/api/app/infrastructure/authoring_group_numeric_repository.py:79-82`) only verifies Authoring records. `AuthoringGroupContext.verify_group_history` (`services/api/app/application/authoring_group_context.py:168-175`) checks the frozen preparation, not the Provider receipt/artifact.

By comparison, `AuthoringGroupService._history` (`services/api/app/application/authoring_group.py:29-59`) calls `provider.read_result` and checks the real receipt, outcome, usage and original output. The Provider owner checks actual artifact bytes; the numeric path never reaches it.

Spec evidence: PRODUCT_DESIGN lines 1148 and 1156 require actual Provider linkage and fail-closed history rather than self-consistent new hashes. Lines 1922 and 2944 require real owner history checks for group numeric and every protected read. The original approved group, member, frozen numeric plan and current author session can all be correct while the original Provider artifact is damaged; this case must not gain new numeric admission.

### Reproduction and exact observed result

`probe_provider_history.py` imports the existing `generated_group` helper (`tests/integration/test_authoring_group_numeric_service.py:81-108`). This creates a real SQLite workspace, one explicitly approved complete-byte test-only HTTP response on an ephemeral loopback port, and a completed lesson group. The helper asserts exactly one local Provider request. It uses `LedgerRuntime`, which cannot execute a calculator.

Only in `probe-data`, the reproduction drops the Provider artifact immutability trigger and changes the synthetic artifact bytes, leaving its recorded original SHA, receipt, Authoring raw answer, plan, candidate and approved source history untouched. This deliberately models damaged history; it is not an HTTP exploit or a change to product migrations/system policy.

Observed sequence, preserved in `probe.log` and `probe-result.json`:

1. Original protected draft read succeeds.
2. After the isolated artifact damage, protected draft read rejects with HTTP-equivalent 503 / `PROVIDER_INTEGRITY_INVALID`.
3. Numeric preview for the exact same candidate/member succeeds (`pending`, no Job).
4. Explicit numeric `approve_once` succeeds with a queued Job.
5. Real worker claim, original `_access` and original repository `begin` succeed with `admitted=true`.

The reproduction stops at admission. It does not call `process` or `run_checked`, and proves no calculator execution. Runtime counters are one prepare and one check. The full result captures the original source Job, candidate hash and original Provider artifact hash, but no raw answer, session or request body.

Command executed once, exit 0:

```sh
env HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy= NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost <HOME>/.cache/learning-workbench-acceptance/m61-groups-active/.venv/bin/python -B <HOME>/.cache/learning-workbench-acceptance/m61-group-backend-independent-review-v1/probe_provider_history.py
```

Stdout/stderr were retained in `probe.log`. The one Starlette deprecation warning is retained. The script intentionally refuses reuse of its existing private database directory; a repeat should use a fresh cache base and must not erase this evidence. This is one focused diagnostic, not a test-suite or native acceptance result.

Recommended minimal correction: provide a typed protected group-history port that verifies the actual Provider receipt/artifact through its owner, and invoke it for numeric preview/read/decision and worker admission/ongoing guard. Preserve the separate safe Jobs discovery/cancel path without reading academic payload under a Policy lock. Do not add Provider SQL to the numeric owner. A regression should verify damaged receipt/artifact rejection before runtime prepare/new numeric Job/start permission, plus preserve safe cancellation and the valid-history path. No correction was implemented in this review.

## Remaining reviewed boundaries

No additional blocking finding in this static scope:

- Source/context: exact ordered Content-owned target metadata, full user envelope and source evidence measurement; original checked outbound consent/lease route, current author/Policy checks and no implicit target expansion.
- Identity: original author session reload at execution; group versus old immutable input versions in source routing, workers, Jobs and HTTP read routing. No ID-prefix dispatch or old-schema projection found.
- Group persistence: one checked Provider response, plan preservation on invalid draft, full private-inclusive candidate/member binding, separate protected private solution projection, candidate and terminal Job transaction.
- Numeric persistence/runtime: target selects the exact member or its bound private numeric plan; operation and result hash the full versioned group input. Separate explicit approval, admission and terminal records; start-history recovery blocks unknown execution rather than repeating it. Runtime callback guards before subprocess start and during execution; no automatic fallback or extra Provider dispatch found.
- Composition: main service/worker construction and lifecycle, shared Jobs control, strict group routes and unchanged old wire branch were read.

These are bounded static observations, not proof of runtime acceptance, race freedom, numeric PASS, semantic quality, or complete M6.1 delivery. Native fixtures and frontend tests are outside this task.

## Evidence handling

`inputs-before.json`, `inputs-after.json`, `source-before/`, `source-additional/`, the probe source, result and raw log remain in this independent cache base. `probe-data/` contains the isolated database and synthetic local fixture credentials; it is private diagnostic state and must not be imported or published. This directory is not a public evidence pack. Import only explicitly reviewed source/metadata/log derivatives, with HOME redaction as required, and preserve original SHA bindings.
