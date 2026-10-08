# M6.3 — bounded Tutor completion test observation

Fixed source: `21877782cc6b7861acb23fc8bc040d22fbf6c225`, parent RED fixture `d34acd3838bd59b55c012aa72f9d373d0c7825f4`, base `1a6473dadcf71623008188f465586495ab28a204`. Branch `feat/M6.3-tutor-completion-observation`, new isolated tree `m63-tutor-completion-observation-oct04`, clean.

The original push CI failure remains **FAIL**. Its independent diagnosis is already sealed separately in `m63-1a-tutor-ci-diagnosis-oct04` (REPORT SHA256 `d86e27b758b07be0857dd160df0c14ea80012da5c267480151a4f20a31245f54`). That report retains the actual push 129 PASS/1 FAIL, PR 130 PASS, isolated original test PASS, two setup failures, and the separate synthetic matcher illustration. The exact original matcher sampling/visibility and the reason for the slower CI execution remain unknown. This test repair does not establish the original CI's unique cause.

## Change

Only three test paths differ from 1a:

- `tests/e2e/tutor.spec.ts`: one helper import and the one completed-state expectation immediately following explicit grant. The original exact region/heading locator, diagnostic wrapper, original grant, final GET, result identity/usage, one request assertion, refresh recovery, and mobile assertions remain intact.
- `tests/e2e/tutorCompletion.ts`: closed five-second expectation using `expect.poll(() => completed.isVisible(), { timeout: 5000, intervals: [25] }).toBe(true)`. It performs read-only DOM visibility queries, never another application request or grant. No catch converts an absent heading to success.
- `tests/e2e/tutor-completion.spec.ts`: three synthetic DOM cases: early appearance, appearance near the deadline at 4900 ms, and the exact completed heading never appearing inside the required region. The negative contains a same-named completed heading outside the region, so it also preserves locator scope.

This does not guarantee detection of every arbitrarily short transient or events after the deadline. It reduces the original matcher's larger polling window while retaining the total 5000 ms budget. No global/shared timeout, application code, backend, protocol, permission, grant, or retry behavior changed.

Mechanically reversing the one import and one assertion gives the exact original `tutor.spec.ts` bytes. All 1464 old nonoverlapping engineering paths are preserved. `SOURCE_BINDING.json` records the exact three-path delta, unchanged specification SHA, and source blobs. The new synthetic test file is byte-identical between the RED and fixed commits.

## Actual validation

| Fixed source / stage | Actual result | Scope |
|---|---|---|
| d34 / `01-old-matcher` | **1 FAIL, 2 PASS**, exit1, 12.6 s Playwright | Old `toBeVisible` helper with the same three new synthetic tests. The 4900 ms positive fails. Early and absent-heading controls pass. Original failure preserved. |
| 218 / `02-fixed-tutor` | **6 PASS**, exit0, 50.9 s Playwright / 51.315 s runner | Three original Tutor application cases plus the same three synthetic DOM cases. One worker, zero retries. |
| 218 / `03-native-types` | PASS, exit0 | Strict/noUnused TypeScript for both changed native test entries and transitive imports. |
| 218 / `04-web-strict` | PASS, exit0 | Existing Web strict/noUnused compiler command. |

The six passing cases are not six application flows: exactly three are the existing Tutor flows, and three are synthetic DOM observations. The original loopback application case still verifies zero requests before explicit grant and exactly one validated synthetic request afterward. The other original cases cover local missing-proof cancellation and lost-ACK/original replay with cross-page Policy boundaries. No actual provider/model/account/CLI was used. `tutor-diagnostic.spec.ts`, the full native suite, full Web tests, Python tests, and remote CI reruns were **NOT_RUN** in this repair.

Each stage captured all **1467 nonprogress tracked inputs**, compared every file to the executed Git commit before and after, and found no changes. Private runner/config hashes are in the receipts; there was no separately captured before-map for private harness files, and none is claimed. The generic receipt `scope` describes the slice; the command and this stage table identify what each stage actually executed.

The private Playwright configuration avoids unrelated global webServers: the original Tutor cases create and close their own existing runtimes. It retains one worker, no retries, and original per-case/expectation budgets. Dependencies were read-only reused without installation; isolated short TMPDIR, HOME, and cache directories were used. No root/canonical/progress files or remote metadata were changed.

## Evidence publication boundary

Only `SAFE_SHARE.json` candidates and `OUTER_METADATA.json` metadata are approved for copying. Raw runtime data, DBs, cookies, profile directories, credential material, archives, and unrestricted artifacts are excluded. Original failure records remain in the raw manifest; they are not rewritten as successful outcomes. All explicit candidate hashes and exact home-prefix-only transformations are verified independently by `VERIFY.py`.
