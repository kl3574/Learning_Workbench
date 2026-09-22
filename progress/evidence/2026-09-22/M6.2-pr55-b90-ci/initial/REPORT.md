# PR55 b90 head and prior PR run: single CI readback

Snapshot window: **2026-09-22T06:03:54.623056+00:00–2026-09-22T06:04:01.823103+00:00**. PR55 and `refs/heads/feat/M6.2-candidate-review` both returned **`b90b4446172b39a3858a9684437920c27eda01ae`**. The PR is open and draft; its reported merge commit is `2e3a0a76ba0fb51f9de83ead1f896cf76ea92437`. That PR metadata is not evidence of a job's checkout.

| Run | Bound head metadata | Event | Actual snapshot result |
| --- | --- | --- | --- |
| 35690766229 | 89b9d227… | pull_request | Completed, failure. Five jobs succeeded; browser 106627088492 failed. |
| 35692894284 | b90b4446… | push | In progress. security-publication, frontend and backend succeeded; integration, spec-contracts and browser in progress. |
| 35692897917 | b90b4446… | pull_request | In progress. security-publication, frontend and backend succeeded; integration, spec-contracts and browser in progress. |

The prior PR browser job's complete log supplies **actual checkout `41acd316a7b9e6e19e76afa69ee6f9805166be36`** via the `git log -1 --format=%H` command/output at lines 131–132. It finished **98 PASS / 1 FAIL in 17.1m**, test-step exit **2**. The 98 individual pass rows and one fail row independently agree with that printed summary.

Its exact failed case is `tests/e2e/tutor.spec.ts:148:1`, “explicit same-Run consent uses the real loopback protocol and restores raw answer without upgrading evidence”. At **`tutor.spec.ts:195:91`**, the original **5000 ms** assertion could not find the visible heading **真实任务状态：completed** under **真实问答线程与任务**. This is the actual printed assertion failure, not evidence of a backend Run.failed state. The same job's `grading-recovery.spec.ts:57:1` case passed in **12.9s** (line 676); do not substitute the previous push's grading 409 result for this PR run.

The log names the completion diagnostic JSON, screenshot and error-context, and reports upload artifact **10678572097**, `browser-failure-pull_request-35690766229-1`, **283120 bytes** (lines 833–835). No artifact list or ZIP was fetched in this task, so its contents and digest were not inspected. This run's post-assertion probe state, DOM, SSE sequence and underlying cause remain unknown from the captured job log. A matching test/timeout does not establish a matching root cause with another run.

No checkout log was requested for either currently running b90 run. Their actual checkout SHA therefore remains **NOT_OBSERVED**; run.head_sha/job.head_sha are only the returned metadata. This is not a complete current-head CI pass. PR/ref/run/job reads occur at separate instants, so the report preserves their actual individual receipts rather than claiming an atomic status transaction.

There were **9 bounded GET subprocesses**: PR, ref, three runs, three job lists, then the one observed terminal failure's job log. Each ran once with a 35-second limit, direct HTTP1 (`GODEBUG=http2client=0`) and all HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY variable spellings removed case-insensitively. All exited 0; raw stdout/stderr bytes and hashes were rechecked against all nine receipts. No credentials or full environment were serialized.

No polling, retry, dispatch, wait-for-completion, artifact download, test run, source modification, vendor call or diagnosis from historical memory occurred. Later source fixes and later branch heads are outside this snapshot.
