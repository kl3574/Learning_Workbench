# Independent bounded CI uploader review

Fixed source: `e717165eef2958eba31eff152dcd9285f2426c38`. Compared workflow introductions `64ab9752864c69984090aaf1d67f6ca01059abbc` (Restore receipts) and `4f666c405a54ed179b26185ff2dbaa3902fac7b3` (Review failure diagnostic). Source snapshots and all three scoped diffs are retained here. Read-only; no checkout/root mutation, remote request, credentials or environment enumeration.

## Standards

No blocking finding within the inspected change. The action remains SHA-pinned, keeps retention 3 days, warns for missing files, and excludes hidden files. Single uploader `.github/workflows/ci.yml:121-129` admits only `**/single-publication-actual.json` beneath the dedicated runner-temp e2e output directory. It does not admit arbitrary JSON, DB files, fixture data directories, traces, HARs, or logs. Existing native step (102-105), Restore fixed basenames (109-119), and failure-only allowlist (131-145) are unchanged. The third modified file `authoringTestData.ts` only loses its trailing blank line.

## Spec and disclosure boundary

No blocking finding in the bounded producer/upload path. `always() && (steps.native.outcome == success || failure)` retains numeric facts whether the browser gate passes or fails, and does not run for a skipped native step. It does not turn native failure into success. Failure screenshots/diagnostics retain their narrower `failure() && native.failure` condition.

The early producer at `single-publication.spec.ts:38-41` writes an explicit `numeric_observed_before_review` stage only after observing the actual numeric terminal and checking its outcome/Job association. The final write at 121-126 replaces that same file with `closed_chain` after the browser's Review/publication/readback assertions. An early receipt does not prove later Review or publication; even a closed-chain receipt is not the CI job result, and cleanup still follows in `finally`. The numeric verdict stays actual PASS/BLOCKED; no test result is presented as physical PASS.

Inspected the complete producer, fixture helper, owned runtime, original synthetic fixture payload, and server DTO definitions for the serialized values. The producer serializes candidate IDs/hashes, bounded numeric plan/runtime/result/ACK DTOs and, at the final stage, synthetic Review receipt, response, original generated draft and intercepted publication body plus non-secret idempotency key. That key is not a session credential. There is no serialized SessionResponse, CSRF token, cookie, authorization header, bootstrap capability, provider secret, or raw provider request/config. The fixture's payload and entered human reasons are synthetic; `source_refs/materials` are empty. The runtime creates a fresh data directory/profile with a test-only loopback factory. Its process environment and bootstrap capability are used in memory, not copied into this artifact. Existing full synthetic payloads and non-secret IDs are intentional evidence; this is not a generic sanitizer for arbitrary future producers using the same basename.

## Actual scope and limits

Static review only: three modified files, full `single-publication.spec.ts`, adjacent `authoringTestData.ts`/`authoringRuntime.ts`, original `tests/authoring_native_fixture.py`, and the relevant `authoring_dto.py` shape definitions; source hashes are in scope.json. No new native execution, no actual artifact download, no GitHub uploader/run verification: NOT_RUN in this review. Existing root execution results are not borrowed. An initial source snapshot command guessed an incorrect fixture path (`services/api/tests/...`); it failed read-only before scope creation, then the actual tracked path was located with rg. No product/test source changed.

Standards: 0 blocking findings. Spec/disclosure: 0 blocking findings within the stated static scope.
