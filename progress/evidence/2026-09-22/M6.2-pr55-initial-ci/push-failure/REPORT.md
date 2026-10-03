# PR55 push browser failure

Run **35689944640**, browser job **106624590630**. Two bounded GETs completed successfully during 2026-09-22T05:37:30.580642+00:00–2026-09-22T05:37:35.054128+00:00.

The log's actual `git log -1 --format=%H` output (lines 119–120) confirms checkout **`89b9d2279364e83c2dbddd1b3418c8c206ec9845`**. This conclusion comes from the job log, not only run/head metadata. It does not cover later local or remote heads.

Native tests finished **98 PASS / 1 FAIL in 13.8m**. The failed step exited **2**. The exact failed case is `tests/e2e/grading-recovery.spec.ts:57:1`: “a real failed regrade survives reload and can recover from the last actual grade without losing the old submission”.

The failure is the result helper's assertion at **`grading-recovery.spec.ts:41:31`**, called by the test at **line 79**. GET `/api/v1/attempts/${id}/result` returned **409**, while `expect(response.status()).toBe(200)` expected **200**. The preceding branch accepts 202 by returning 0 to the polling assertion. The received 409 instead fails at the inner 200 assertion. These facts are printed in log lines 750–766; the log contains neither the 409 response body nor its application error code, so the underlying cause remains unknown.

The Tutor loopback case at `tutor.spec.ts:148:1` **passed in 16.1s** in this run (line 726). This is a different observed failing test from the earlier PR54 Tutor timeout; no shared cause is inferred.

The log references a screenshot and error-context under `grading-recovery-a-real-fa-8007b-t-losing-the-old-submission`. The sole listed artifact is **10677454514**, `browser-failure-push-35689944640-1`, **169963 bytes**, listed SHA256 **5398d56bdbfef2b2aff0ea2a5d55b23415e82fb9fd66fc206d4b567a36ef725a**. It was not downloaded, enumerated or inspected here; the listed digest is GitHub metadata, not an independently verified ZIP hash. These attachments would be the precise next evidence source if further diagnosis is requested; they may still not contain the HTTP error body.

Raw log SHA256: `51b17c4cd4a9941d2f6177e38d2d22c69fc4267143e0015a5309e0829c5195e6` (85426 bytes). Artifact-list SHA256: `4f2a93790cd2929c5dbcb0bb90df9b2ca9ded25416b1b45aeb9523fd51c25a35` (766 bytes). Commands, exact start/end times, exits and stdout/stderr hashes are retained in the corresponding receipts. Proxy environment variables were removed case-insensitively and `GODEBUG=http2client=0` selected direct HTTP1 transport; no credential or environment contents were serialized.

No ZIP download, test rerun, retry, dispatch, wait-for-completion, source edit or vendor call occurred.
