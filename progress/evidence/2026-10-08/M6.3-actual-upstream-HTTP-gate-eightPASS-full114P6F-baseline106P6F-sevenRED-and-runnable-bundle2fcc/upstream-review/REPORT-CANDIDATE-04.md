# Independent final review: candidate04

The bounded library slice passes static review. There are no remaining P1/P2 findings in the four frozen changed sources. The complete library test gate FAILS:114 passed,6 failed. Reviewer tests:NOT_RUN. Production profile:NOT_ADMITTED.

Source baseline:a956835d020762cb2b570053af06f643a11c0ecc. Candidate root:test-copy-04. All four owner-frozen SHA256 values, exact original/test Cargo.lock SHA256, and the single test-only manifest version substitution were independently read back. Immutable snapshots and binding are under frozen-candidate-04 and packet/candidate04-binding.json. Product authority is only PRODUCT_DESIGN.md v3.0.15 sections20.5/20.17.

## Standards

No additional manually reviewable P1/P2 standards findings. The new module remains below the upstream size limit, crate API is explicitly exported, tests are in the required sibling test module, and no new trait or forbidden sandbox-flag code was introduced. Compiler/Clippy/Bazel and repository-default just workflows were not executed by this reviewer. Owner command/output receipts are identified separately; successful bounded Cargo commands do not substitute for unrun broader checks.

## Spec

The candidate02 review found2 P1 and3 P2 issues. All five are statically closed on the actual candidate04 bytes:

- R1 (P1) closed: Root non-whitespace byte must be an object opening brace before serde parsing; actual EncodedJson root-array negative case retained. Location:frozen_responses_request.rs153-166; negativecase:frozen_responses_request_tests.rs90-104.
- R2 (P1) closed: Supplied Content-Length, Transfer-Encoding and Host are rejected before capability construction; lower-layer standard Host/framing is derived from the bound URL/body, not caller-specified framing. Location:frozen_responses_request.rs139-145; negativecase:frozen_responses_request_tests.rs138-168.
- R3 (P2) closed: Accept is mandatory explicit frozen header so reqwest default insertion is a no-op. Controlled factory additionally disables all four automatic decompression flags, preventing feature-dependent late Accept-Encoding. Existing client wrapper trace/default injection remains bypassed. Location:frozen_responses_request.rs122-124,146; transport.rs88-98; negativecase:frozen_responses_request_tests.rs170-172.
- R4 (P2) closed: Final built request timeout and original response cap are compared strictly; body pointer and bytes are both bound. A mismatch burns the shared capability before zero send. Location:frozen_responses_request.rs218-225; transport.rs115-138; negativecase:frozen_responses_request_tests.rs229-287.
- R5 (P2) closed: Exactly one prepared Content-Type is required, with exact value application/json; wrong media type and duplicate values are retained negative cases. Location:frozen_responses_request.rs174-186; negativecase:frozen_responses_request_tests.rs157-178.

The same Arc owns one atomic compare_exchange and has no reset path. The final built reqwest request is compared for method, exact normalized URL, complete prepared header map, original encoded body bytes and pointer, timeout and response cap immediately before execution. The controlled fixed client excludes proxy, redirect, reqwest retries, HTTP2 and idle reuse; all automatic decompression negotiation flags are false. It bypasses the wrapper that adds trace headers and disables its own request/response logging.

The frozen capability itself and controlled client Debug are redacted. The public prepared_request getter deliberately returns the existing raw Request type: its inherited Debug contains request bytes and can display a non-sensitive-marked Authorization value. That getter is trusted private material, not a safe public/logging DTO. Public freeze can construct a new capability and ordinary constructors remain unguarded; the owner must share one Arc across all attempts and exclude alternate transports. This slice provides no persistent/global consent authority. These documented owner boundaries are not claimed closed by a unit test.

The final claim is before reqwest/hyper execution. Standard Host and Content-Length derivation still occur in hyper; arbitrary caller Host/CL/TE are now rejected. No every-framing-byte or DNS/IP/TLS boundary proof is inferred. A build error before claim has not begun network sending; after a claim, mismatch or network/HTTP/stream/cancellation failures remain spent.

## Readback of actual owner results

- Candidate03 targeted locked gate:PASS,8 passed,0 failed,112 filtered.
- Candidate04 gate cases inside the integrated all-library run:PASS,8 cases.
- Candidate04 complete locked/offline codex-http-client --lib:FAIL,114 passed,6 failed,0 ignored,0 filtered; exit101. Failed certificate/native-TLS fallback cases are recorded individually in the JSON report and full copied stdout/stderr. An unchanged upstream baseline under identical task toolchain/test metadata/environment reproduces the same six failed names (106 passed,6 failed). This does not establish an exclusively environmental root cause; the complete candidate04 gate remains FAIL.
- Owner rustfmt04 receipt:exit0.
- Reviewer tests/models/CLI/host-security/proc probes/candidate mutations:NOT_RUN/NONE.

Every copied receipt's stdout/stderr size and SHA256 matches the owner command record. Source04 SHA256 values remain fixed. Tests use exactly one separately authorized workspace.package.version0.160.0 ->0.0.0 test metadata substitution; external pins and Cargo.lock remain unchanged. Original release workspace/binary equivalence is NOT_RUN.

No AppServer registration, persistent ledger/restart permit, model/token/capacity proof, complete resource qualification or DNS/actual connection boundary is admitted. The slice remains unregistered for production execution.

Summary:Standards0 remaining findings; Spec0 remaining P1/P2 after closing candidate02 issues. Static slice PASS, integrated library FAIL, reviewer tests NOT_RUN, production NOT_ADMITTED.

## Final supplemental receipt audit

The dedicated candidate04 locked/offline gate also actually completed exit0:8 passed,0 failed,112 filtered. Reviewer readback validated every stdout/stderr hash and size.

The unchanged upstream baseline completed exit101:106 passed,6 failed,0 filtered. All48 baseline crate file hashes match the original upstream source map; Cargo.lock is unchanged and the only manifest change remains test workspace version0.0.0. Task toolchain/environment equals candidate04. Its six failed names are exactly candidate04's six. This supports failure reproduction in the baseline; it does not make the integrated gate PASS or identify an exclusively environmental cause.

The separately authorized old-candidate02 pure rejection harness actually completed exit101:0 passed,7 failed,120 filtered. Old frozen implementation, transport and original tests have the exact candidate02 hashes. Only test harness/module registration/test metadata differ. All seven expected rejections instead returned no error:root array, supplied Content-Length, Host, Transfer-Encoding, wrong Content-Type, duplicate Content-Type, and missing Accept. Source readback confirms the seven harness cases construct no client, claim, DNS/connection or send. These actual RED receipts confirm old admission flaws; runtime wire consequences still rely on the separately hash-pinned reqwest/hyper source inspection. Candidate04 contains permanent corresponding negative cases.

Final statuses remain:bounded static slice PASS; dedicated gate PASS8/0; complete library FAIL114/6; unchanged baseline FAIL106/6; old rejection harness actual FAIL0/7 (expected RED); reviewer tests NOT_RUN; production NOT_ADMITTED.
