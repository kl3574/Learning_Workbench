# PR55 initial CI snapshot

Expected head: `89b9d2279364e83c2dbddd1b3418c8c206ec9845`; branch: `feat/M6.2-candidate-review`.
Read window: 2026-09-22T05:36:16.118958+00:00 to 2026-09-22T05:36:18.201924+00:00.
PR and branch both match expected head: True.

| Run | Event | Run status / conclusion from initial list | Jobs from subsequent single GET |
| --- | --- | --- | --- |
| 35690766229 | pull_request | in_progress / none | frontend=completed/success, integration=in_progress/none, backend=completed/success, security-publication=completed/success, browser=in_progress/none, spec-contracts=completed/success |
| 35689944640 | push | completed / failure | spec-contracts=completed/success, backend=completed/success, frontend=completed/success, integration=completed/success, security-publication=completed/success, browser=completed/failure |

This is a bounded snapshot, not an atomic cross-endpoint transaction. Job reads occurred after the run-list read; natural progress may differ between responses. No CI retry, dispatch, wait-for-completion, test run, code change or checkout-log fetch occurred.

The run/head fields bind these observations to the head metadata actually returned. They do not prove the checkout commit executed by a job; a pull-request job may check out a merge commit. Later documentation commits are outside this snapshot. Authentication values and environment contents were not serialized.

Run list total/returned: 2/2; one page only. Read failures: [].
