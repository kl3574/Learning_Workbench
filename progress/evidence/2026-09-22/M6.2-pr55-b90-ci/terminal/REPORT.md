# PR55 b90 terminal CI snapshot

Read window: **2026-09-22T06:24:56.201686+00:00–2026-09-22T06:25:01.950862+00:00**. PR55 and its branch ref still returned **`b90b4446172b39a3858a9684437920c27eda01ae`**. Both known CI runs are now completed with failure; this report does not substitute the uncommitted submit-ACK test fix for the code executed by these jobs.

| Run | Event | Job results |
| --- | --- | --- |
| 35692894284 | push | 4 succeeded; integration 106633474101 and browser 106633474154 failed. |
| 35692897917 | pull_request | 5 succeeded, including integration; browser 106633484175 failed. |

Actual checkout evidence comes from each downloaded log's `git log -1 --format=%H` command, not workflow head metadata:

| Captured job | Actual checkout SHA | Output line |
| --- | --- | --- |
| Push integration 106633474101 | `b90b4446172b39a3858a9684437920c27eda01ae` | 118 |
| Push browser 106633474154 | `b90b4446172b39a3858a9684437920c27eda01ae` | 120 |
| PR browser 106633484175 | `2e3a0a76ba0fb51f9de83ead1f896cf76ea92437` | 132 |

Push integration finished **954 PASS / 1 FAIL / 1 SKIP / 2 warnings in 954.15 seconds**, exit **1**. The exact failed case is `tests/integration/test_document_http.py::test_failed_documents_report_safe_failure_and_retain_exact_original_without_formal_content[pdf-pdf_scan_fixture-True]`. At line **169**, the test required `job['error']['code'] != 'IMPORT_PARSE_FAILED'`; the actual value was **IMPORT_PARSE_FAILED**. Earlier assertions shown in the same traceback established failed Import status, no preview refs, denied confirmation and an empty result_refs list. The log does not identify the underlying exception that was mapped to this generic error, so its cause remains unknown. The corresponding PR integration job succeeded; its test totals and actual checkout were not read from a success log here.

Both browser jobs finished **98 PASS / 1 FAIL**: push in **16.9m**, PR in **18.0m**, each test step exit **2**. Both fail the case at `tests/e2e/tutor.spec.ts:148:1`, at the unchanged **`:195:91`** assertion waiting **5000 ms** for the visible **真实任务状态：completed** heading under **真实问答线程与任务**. Individual pass/fail rows agree with both summaries. The grading-recovery case passes in both browser logs; these are not the earlier push's grading-result 409 failure.

The two logs mention Tutor diagnostic JSON, screenshot and error-context attachments, but none was downloaded or inspected here. A repeated heading timeout does not establish that these jobs share an underlying cause, nor that the backend Run itself failed. The logs' artifact identifiers are preserved in details.json only as upload-log observations; no archive digest or contents were verified.

All **9 bounded GET subprocesses** exited 0: PR, ref, two runs, two job lists and the three observed failed-job logs. Their raw stdout/stderr hashes were checked against the corresponding receipts. Proxy variables were removed case-insensitively and direct HTTP1 selected with `GODEBUG=http2client=0`. No credential or full environment was serialized. No CI retry, dispatch, polling, wait-for-completion, artifact fetch, test run, source edit or vendor call occurred. These separately timestamped reads are a bounded snapshot, not an atomic view or evidence for later heads.
