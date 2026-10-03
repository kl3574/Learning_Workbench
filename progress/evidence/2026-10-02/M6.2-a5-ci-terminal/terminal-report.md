# a5 GitHub CI evidence

Observation: 0006. **TERMINAL**.

Published source head: `a5c4ca9d46a740737d29499fb212cdfcd64187f8`. Attempt 1. Push checks out the published head; PR checks out `fa0058d656766356576e518ceb62519e8494e6ff`. GitHub commit API proves that the PR merge has a5 as its second parent and both commits share exact tree `f54531076ad7058a70500a7033de4b8108914d46`.

This report covers only these two CI runs. New local Session, CodeMirror, Edit publication, Learning UI and Content list work is not credited to these runs.

| Event | Run | Status | Conclusion |
|---|---|---|---|
| push | [36988843781](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781) | completed | success |
| pull_request | [36988849056](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056) | completed | failure |

| Event | Job | ID | Result | Test receipt |
|---|---|---|---|---|
| push | security-publication | [110780038582](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781/job/110780038582) | PASS | No test-count claim |
| push | frontend | [110780038660](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781/job/110780038660) | PASS | Test Files  94 passed (94); Tests  562 passed (562) |
| push | backend | [110780038714](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781/job/110780038714) | PASS | Success: no issues found in 227 source files; ======================= 731 passed, 2 warnings in 36.18s ======================= |
| push | spec-contracts | [110780038733](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781/job/110780038733) | PASS | ================= 619 passed, 2 warnings in 295.19s (0:04:55) ================== |
| push | integration | [110780038770](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781/job/110780038770) | PASS | =========== 1890 passed, 1 skipped, 2 warnings in 2437.81s (0:40:37) =========== |
| push | browser | [110780038873](https://github.com/kl3574/Learning_Workbench/actions/runs/36988843781/job/110780038873) | PASS | 108 passed (15.9m) |
| pull_request | security-publication | [110780057050](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056/job/110780057050) | PASS | No test-count claim |
| pull_request | spec-contracts | [110780057223](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056/job/110780057223) | PASS | ================= 619 passed, 2 warnings in 246.87s (0:04:06) ================== |
| pull_request | browser | [110780057263](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056/job/110780057263) | FAIL | 1 failed; 107 passed (20.5m) |
| pull_request | frontend | [110780057279](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056/job/110780057279) | PASS | Test Files  94 passed (94); Tests  562 passed (562) |
| pull_request | backend | [110780057323](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056/job/110780057323) | PASS | Success: no issues found in 227 source files; ======================= 731 passed, 2 warnings in 36.52s ======================= |
| pull_request | integration | [110780057338](https://github.com/kl3574/Learning_Workbench/actions/runs/36988849056/job/110780057338) | PASS | =========== 1890 passed, 1 skipped, 2 warnings in 2326.84s (0:38:46) =========== |

Browser result: push **108 passed**; PR **107 passed, 1 failed**. The PR failure is `tests/e2e/tutor.spec.ts:148`, line 195, waiting for `真实任务状态：completed` to be visible with the unchanged 5000 ms assertion. The last delivered frozen DOM observation was `queued`, answer present; the bounded post-failure GET was `running`, last_seq=5, job_revision=5, provider receipt absent. The loopback runtime recorded one received and validated request. Later reads do not establish state at the assertion boundary; no unique root cause is inferred and the failure is not closed by the passing push run.

Failure artifact `11219786276`: 297582 bytes, 8 members, SHA256 `849eda489378deba96e37b553c7e2a95e49f5b6b15b10521654ed31b0070c7ef`, independently computed and equal to the GitHub API digest. Original ZIP, screenshot, context and metadata are retained privately. The shareable package contains full text logs and metadata diagnostics, with path/auth redactions recorded per file and no evidence lines removed. Binary screenshots and rendered page context stay in the private originals.

All collection used read-only GitHub API calls. No workflow trigger, rerun, cancellation, remote write, main-tree/progress modification, provider call or secret-store access was performed.
