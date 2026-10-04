# Original 27f full Python terminal readback

**FAIL**: the original `uv run --frozen --offline pytest` collected 4441 items (run.log:7), then finished **6 failed, 4433 passed, 2 skipped, 3 warnings** in 2917.68s (run.log:600). The original receipt has command exit 1 and wrapper exit 1. No rerun or dependency/source change was performed. Earlier CI/focused evidence does not replace this full-gate FAIL.

The original log is 46360 bytes, SHA-256 `2ccc1174ec2e9252b6ebf8464a990b04b55e907b19a546be34ca2f08d8a51a53`. Runner SHA-256 is `25b718a32b6dd269b6709a914922475409d7046aa1499c9cd1a10ef68c3e8555`. Before and after manifests are identical JSON and bytes: 1541 entries at head `27f549ff5a8fd67b0a601b67a5ba51ef35f6765f`, tree `8921175046cd5b3b414abd1709b354b793d7715c`, SHA-256 `2aa439db5e01044489464d2ed6aa820a6edf1a2f683ac63fc9959d0be6cc39c1`. They retain generated and derived files.

All six unique failures have subprocess return code 1 at an assertion expecting 0, with original stderr `Node 24.21.0 is required; run make setup.` Exact failure IDs, complete failure blocks, assertions, error lines, and original line locators are retained in REPORT.json. This establishes the observed Node-wrapper prerequisite failure; missing executable versus wrong version is not determined without additional environment evidence, which was not read.

- `tests/contract/test_generated_transport.py::test_generated_types_and_executed_transport_preserve_old_calls_and_bind_exact_parameters` (summary line 594; failure block 317-371)
- `tests/contract/test_generated_upload.py::test_multipart_roundtrip_keeps_original_bytes_filename_and_binary_response[binary_schema0]` (summary line 595; failure block 372-416)
- `tests/contract/test_generated_upload.py::test_multipart_roundtrip_keeps_original_bytes_filename_and_binary_response[binary_schema1]` (summary line 596; failure block 417-461)
- `tests/contract/test_recommendation_binding.py::test_emitted_application_binding_and_nested_types_compile_with_no_unknown_escape` (summary line 597; failure block 462-504)
- `tests/contract/test_retrieval_generation.py::test_generated_client_compiles_exact_query_union_and_executes_only_legal_scalar_modes` (summary line 598; failure block 505-546)
- `tests/contract/test_tutor_transport.py::test_emitted_sse_codec_real_typescript_and_stream_execution` (summary line 599; failure block 547-575)

Original skips (run.log:592-593):

- `tests/integration/test_authoring_numeric_runtime.py:46`: BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained
- `tests/integration/test_restore_numeric_actual_runtime.py:42`: BLOCKED_ENVIRONMENT: actual sealed Restore evaluator did not return a numeric PASS; no fallback

Original warnings (run.log:576-590) are FastAPI/httpx TestClient deprecation, deprecated anyio.abc.BlockingPortal alias, and Pydantic serializer warning for `thread_id=True` bool where str was expected, from catalog test parameter `[True]`.

The one authorized frozen source read, `tests/contract/test_tutor_transport.py`, exactly matches the 1541-entry manifest: 10945 bytes, SHA-256 `5400485ff55058383601719dc0de790bd8f3a6f2e50c36b159ee93a9472438e0`. Its fixture builds generated contracts from a synthetic authorization application; the source explicitly says this is not Provider E2E. The observed failure is at the compile invocation before subsequent runtime execution.

No tests, product/probe/API/model, environment/Node/profile/DB access, dependency change, remote write, or original-artifact mutation was performed by this reader. This FAIL and the numeric skip boundaries do not establish physical numeric PASS, whole M6.3 acceptance, or M7 PASS. Reports are new private candidates only; prior preparation and CI packets remain untouched.
