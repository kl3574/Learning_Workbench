# Independent bounded Tutor observation review

Reviewed fixed source: `21877782cc6b7861acb23fc8bc040d22fbf6c225`; test-only RED: `d34acd3838bd59b55c012aa72f9d373d0c7825f4`; base: `1a6473dadcf71623008188f465586495ab28a204`. Sole norm remains PRODUCT_DESIGN v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. One independent reviewer authored none of this source and reviewed Standards and Spec separately. No two parallel axis reviewers or newly executed product test is claimed.

Standards 0; Spec 0 additional findings. The narrow three-test-path repair is ready for root integration. **The original push CI 129 PASS /1 FAIL remains FAIL; its unique cause remains UNKNOWN.** The bounded synthetic sampling result below is not an original-CI replay or proof of that cause. No canonical integration, remote CI rerun, full native suite or whole M6.3 acceptance is claimed.

## Standards

Zero additional findings. Only `tests/e2e/tutor.spec.ts`, `tests/e2e/tutorCompletion.ts` and `tests/e2e/tutor-completion.spec.ts` differ from1a. The typed helper performs read-only `Locator.isVisible()` observations and a failing boolean expectation. It contains no application request, click, grant, retry of a command or catch that converts absence into success. The three added DOM cases use the same helper as the original Tutor test. Existing module import conventions are preserved.

Removing the one helper import and reversing the one completed expectation reproduces the entire original `tutor.spec.ts` byte-for-byte. All1464 existing nonoverlapping engineering paths are unchanged. No product, backend, DTO, protocol, global configuration or shared timeout source changed. The new synthetic test file is byte-identical between RED and fixed commits.

## Spec

Zero additional findings. The repaired observation remains inside the original exact Tutor region and exact completed heading locator, immediately after the existing explicit grant and within the unchanged diagnostic wrapper. It retains a total5000ms expectation budget, using25ms polling intervals. The helper observes visibility only; the original final GET, Run/thread identity, actual usage/request count, raw answer, source-evidence limits, refresh recovery and mobile assertions remain unchanged. It does not change product authorization or completion semantics.

The DOM cases cover200ms and4900ms appearance and absence inside the required region. The negative intentionally places a same-named completed heading outside that region and still requires rejection. Thus it does not weaken the locator to any completed heading. The bounded observer does not guarantee detection of every arbitrarily short transient or a state after its deadline; no such guarantee is made.

The original CI diagnostic's single approved safe report remains7542bytes with SHA256 `d86e27b758b07be0857dd160df0c14ea80012da5c267480151a4f20a31245f54`. Only that already approved candidate was checked; this review did not reopen the old diagnosis or infer the original CI's sampling/visibility trajectory. Its129 PASS /1 FAIL record is not overwritten by the local result.

## Original actual evidence

The old matcher atd34 runs the same three synthetic DOM cases: **1 FAIL,2 PASS**, exit1,12.6s Playwright /13.047057199990377s runner. Its original log SHA256 is `b7f3e64614959a3175221d77cf7e6f6bd93d15d51f4efc354579d8763c704036`. The near-deadline4900ms case fails; early and absent-heading controls pass. This is a synthetic test-only baseline, not a re-execution of the original CI failure.

At218 the recorded native run has **6 PASS**, exit0,50.9s Playwright: exactly **3 original Tutor business cases plus3 synthetic DOM cases**. Original log SHA256: `6609bfb3dcbc82fd7ebfe729e3766b8b98606419cb69d0b0bc35257d41ba9e83`. The private config uses one worker, zero retries and the original30000ms case budget. The existing Tutor cases start and close their existing local runtimes; their loopback fixture is an explicit synthetic provider, not a real vendor/model/account proof. The original assertions still require zero model requests before explicit grant and one validated synthetic request afterward. That request count is not a global network measurement.

The native strict/noUnused TypeScript command and the existing Web strict/noUnused command each have recorded exit0 at218. Their commands define their actual scope; the generic receipt scope text is not treated as evidence that a type-check command executed business cases. The full native suite, full Web/Python gates, `tutor-diagnostic.spec.ts` and remote CI rerun are not claimed for this repair.

All four stages have exact complete1467 nonprogress Git input maps before/after. Runner/config hashes match the reconstructed original bytes of their approved safe candidates. Those hashes do not provide a separately recorded before-map for private harness files, and none is invented. The safe source diff/binding and actual immutable Git files match.

## Independent safe-only verification

Pure readback completed with exit0. `READBACK.json` SHA256 is `91149d02ad076ea67678fc7893b277ccfe04c5a3ea4a64c263c63c6b931c0081`. It verifies all29 explicitly approved safe candidates and5 outer metadata files, four before/after pairs,5868 Git file bindings, all1467 fixed inputs,1464 preserved old files, exact source reversal, RED/fixed DOM test bytes, recorded runner/config/log hashes and the unchanged approved prior diagnostic.

No excluded raw runtime, DB, cookie, credential, archive or unrestricted artifact was opened. The raw manifest's54 descriptors were read only as approved metadata; this is not a new54-raw-file audit. Original bytes for the29 approved candidates were reconstructed from the declared exact home-prefix transform and matched to their declared original hashes. The archive verifier contains an existing literal replacement marker; its ambiguous inverse was resolved by the declared original SHA, rather than assuming every marker was introduced by transformation. Archived transformed code is not asserted to be runnable equivalence. Review-tool Unicode encoding and inverse-transform assumptions were corrected before the final real pure readback passed; they are not product test results.

No new product test, model, product CLI, network or host probe was run by the reviewer. This report admits only the bounded test observation repair and its recorded slice. It does not turn the original CI into PASS or establish real-provider, physical numeric, mathematical/source/pedagogical or whole M6.3 acceptance.
