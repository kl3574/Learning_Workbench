# Exact-source GitHub CI readback

Source head SHA: `1db509f9bf4c296eb6fb7f3d99d94b5f243d2e7c`. This package contains read-only GitHub API responses, actual job logs, job step metadata, bounded timestamped check readbacks and the final PR state. Original API/log files remain unchanged in the home cache. Public copies replace home directory prefixes only; the manifest records exact original/public hashes and transformations.

Final check outcomes: `{"success": 12}`. All 12 checks are terminal. A completed check is not necessarily a successful check. Each event has six jobs. The detailed receipt keeps workflow conclusion separately from job conclusions.

| Workflow event | Run | Conclusion | Start | Last workflow update |
| --- | --- | --- | --- | --- |
| pull_request | [34928693774](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774) | success | 2026-09-15T04:24:17Z | 2026-09-15T04:36:07Z |
| push | [34928691591](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591) | success | 2026-09-15T04:24:15Z | 2026-09-15T04:36:32Z |

Actual job start/completion times and original line-numbered test/check excerpts are in `final-ci-receipt.json`. Complete job logs and their metadata are included, so the excerpts do not replace original evidence. PR workflows can check out a synthetic merge commit: each job reports the actual checkout hash found in its log separately from GitHub workflow head_sha. The package does not call a PR merge checkout an exact direct source checkout.

| Event | Job | Conclusion | Started | Completed |
| --- | --- | --- | --- | --- |
| pull_request | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774/job/104252160070) | success | 2026-09-15T04:24:21Z | 2026-09-15T04:27:51Z |
| pull_request | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774/job/104252159808) | success | 2026-09-15T04:24:22Z | 2026-09-15T04:25:10Z |
| pull_request | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774/job/104252159719) | success | 2026-09-15T04:24:21Z | 2026-09-15T04:26:15Z |
| pull_request | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774/job/104252159694) | success | 2026-09-15T04:24:20Z | 2026-09-15T04:24:38Z |
| pull_request | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774/job/104252159691) | success | 2026-09-15T04:24:21Z | 2026-09-15T04:36:06Z |
| pull_request | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34928693774/job/104252159597) | success | 2026-09-15T04:24:21Z | 2026-09-15T04:25:06Z |
| push | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591/job/104252153447) | success | 2026-09-15T04:24:17Z | 2026-09-15T04:24:35Z |
| push | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591/job/104252153441) | success | 2026-09-15T04:24:17Z | 2026-09-15T04:24:57Z |
| push | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591/job/104252153433) | success | 2026-09-15T04:24:18Z | 2026-09-15T04:26:47Z |
| push | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591/job/104252153405) | success | 2026-09-15T04:24:18Z | 2026-09-15T04:25:04Z |
| push | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591/job/104252153399) | success | 2026-09-15T04:24:19Z | 2026-09-15T04:36:31Z |
| push | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34928691591/job/104252153195) | success | 2026-09-15T04:24:18Z | 2026-09-15T04:30:09Z |

PR 48 final API read: state `open`, draft `True`, merged `False`, head `1db509f9bf4c296eb6fb7f3d99d94b5f243d2e7c`. Head matches this checked source: `True`. The current PR head may have advanced while an older source run was being archived; its state is not substituted for the original checked SHA.

No rerun, cancellation, merge, PR mutation or repository write was performed by this collector. Cancelled jobs establish only observed cancellation and any actual partial log output; they do not establish a completed browser suite or a hypothetical pass/failure result. This package is CI evidence only, not a statement that a milestone has been accepted, a deployment happened, or unrun/provider/learning-effectiveness tests passed.

The bounded public scan checks home-path strings and recognizable GitHub/provider token and private-key patterns. It is not a universal secret or rights/provenance certification.
