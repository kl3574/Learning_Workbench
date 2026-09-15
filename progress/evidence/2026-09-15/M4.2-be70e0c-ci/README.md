# Exact-source GitHub CI readback

Source head SHA: `be70e0c39fad6bb51529f1bd061efa9809dd0e5c`. This package contains read-only GitHub API responses, actual job logs, job step metadata, bounded timestamped check readbacks and the final PR state. Original API/log files remain unchanged in the home cache. Public copies replace home directory prefixes only; the manifest records exact original/public hashes and transformations.

Final check outcomes: `{"cancelled": 2, "failure": 4, "success": 6}`. All 12 checks are terminal. A completed check is not necessarily a successful check. Each event has six jobs. The detailed receipt keeps workflow conclusion separately from job conclusions.

| Workflow event | Run | Conclusion | Start | Last workflow update |
| --- | --- | --- | --- | --- |
| pull_request | [34924684148](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148) | cancelled | 2026-09-15T03:21:45Z | 2026-09-15T03:28:21Z |
| push | [34924581305](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305) | cancelled | 2026-09-15T03:20:09Z | 2026-09-15T03:28:17Z |

Actual job start/completion times and original line-numbered test/check excerpts are in `final-ci-receipt.json`. Complete job logs and their metadata are included, so the excerpts do not replace original evidence. PR workflows can check out a synthetic merge commit: each job reports the actual checkout hash found in its log separately from GitHub workflow head_sha. The package does not call a PR merge checkout an exact direct source checkout.

| Event | Job | Conclusion | Started | Completed |
| --- | --- | --- | --- | --- |
| pull_request | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148/job/104240120430) | failure | 2026-09-15T03:21:48Z | 2026-09-15T03:27:38Z |
| pull_request | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148/job/104240120372) | success | 2026-09-15T03:21:48Z | 2026-09-15T03:22:35Z |
| pull_request | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148/job/104240120356) | failure | 2026-09-15T03:21:47Z | 2026-09-15T03:23:29Z |
| pull_request | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148/job/104240120319) | success | 2026-09-15T03:21:48Z | 2026-09-15T03:22:22Z |
| pull_request | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148/job/104240120266) | success | 2026-09-15T03:21:48Z | 2026-09-15T03:22:05Z |
| pull_request | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34924684148/job/104240120164) | cancelled | 2026-09-15T03:21:48Z | 2026-09-15T03:28:20Z |
| push | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305/job/104239803482) | success | 2026-09-15T03:20:12Z | 2026-09-15T03:20:51Z |
| push | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305/job/104239803481) | success | 2026-09-15T03:20:12Z | 2026-09-15T03:20:52Z |
| push | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305/job/104239803454) | failure | 2026-09-15T03:20:12Z | 2026-09-15T03:22:12Z |
| push | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305/job/104239803439) | cancelled | 2026-09-15T03:20:12Z | 2026-09-15T03:28:16Z |
| push | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305/job/104239803414) | success | 2026-09-15T03:20:12Z | 2026-09-15T03:20:32Z |
| push | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34924581305/job/104239803213) | failure | 2026-09-15T03:20:12Z | 2026-09-15T03:24:43Z |

PR 48 final API read: state `open`, draft `True`, merged `False`, head `4cf13f7ed2456d0c7d62a49513055db8b2c8fb20`. Head matches this checked source: `False`. The current PR head may have advanced while an older source run was being archived; its state is not substituted for the original checked SHA.

No rerun, cancellation, merge, PR mutation or repository write was performed by this collector. Cancelled jobs establish only observed cancellation and any actual partial log output; they do not establish a completed browser suite or a hypothetical pass/failure result. This package is CI evidence only, not a statement that a milestone has been accepted, a deployment happened, or unrun/provider/learning-effectiveness tests passed.

The bounded public scan checks home-path strings and recognizable GitHub/provider token and private-key patterns. It is not a universal secret or rights/provenance certification.
