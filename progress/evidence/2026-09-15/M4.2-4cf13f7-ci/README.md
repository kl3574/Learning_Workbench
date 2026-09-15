# Exact-source GitHub CI readback

Source head SHA: `4cf13f7ed2456d0c7d62a49513055db8b2c8fb20`. This package contains read-only GitHub API responses, actual job logs, job step metadata, bounded timestamped check readbacks and the final PR state. Original API/log files remain unchanged in the home cache. Public copies replace home directory prefixes only; the manifest records exact original/public hashes and transformations.

Final check outcomes: `{"failure": 2, "success": 10}`. All 12 checks are terminal. A completed check is not necessarily a successful check. Each event has six jobs. The detailed receipt keeps workflow conclusion separately from job conclusions.

| Workflow event | Run | Conclusion | Start | Last workflow update |
| --- | --- | --- | --- | --- |
| pull_request | [34925086913](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913) | failure | 2026-09-15T03:28:04Z | 2026-09-15T03:40:58Z |
| push | [34925083230](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230) | failure | 2026-09-15T03:28:01Z | 2026-09-15T03:38:56Z |

Actual job start/completion times and original line-numbered test/check excerpts are in `final-ci-receipt.json`. Complete job logs and their metadata are included, so the excerpts do not replace original evidence. PR workflows can check out a synthetic merge commit: each job reports the actual checkout hash found in its log separately from GitHub workflow head_sha. The package does not call a PR merge checkout an exact direct source checkout.

| Event | Job | Conclusion | Started | Completed |
| --- | --- | --- | --- | --- |
| pull_request | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913/job/104241379015) | success | 2026-09-15T03:28:23Z | 2026-09-15T03:30:31Z |
| pull_request | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913/job/104241378989) | failure | 2026-09-15T03:28:23Z | 2026-09-15T03:40:57Z |
| pull_request | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913/job/104241378960) | success | 2026-09-15T03:28:23Z | 2026-09-15T03:29:14Z |
| pull_request | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913/job/104241378943) | success | 2026-09-15T03:28:24Z | 2026-09-15T03:34:25Z |
| pull_request | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913/job/104241378911) | success | 2026-09-15T03:28:22Z | 2026-09-15T03:28:40Z |
| pull_request | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34925086913/job/104241378782) | success | 2026-09-15T03:28:22Z | 2026-09-15T03:28:58Z |
| push | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230/job/104241368104) | failure | 2026-09-15T03:28:20Z | 2026-09-15T03:38:55Z |
| push | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230/job/104241368047) | success | 2026-09-15T03:28:19Z | 2026-09-15T03:29:07Z |
| push | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230/job/104241368006) | success | 2026-09-15T03:28:19Z | 2026-09-15T03:28:59Z |
| push | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230/job/104241367999) | success | 2026-09-15T03:28:19Z | 2026-09-15T03:28:37Z |
| push | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230/job/104241367996) | success | 2026-09-15T03:28:20Z | 2026-09-15T03:34:04Z |
| push | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34925083230/job/104241367743) | success | 2026-09-15T03:28:20Z | 2026-09-15T03:30:34Z |

PR 48 final API read: state `open`, draft `True`, merged `False`, head `4cf13f7ed2456d0c7d62a49513055db8b2c8fb20`. Head matches this checked source: `True`. The current PR head may have advanced while an older source run was being archived; its state is not substituted for the original checked SHA.

No rerun, cancellation, merge, PR mutation or repository write was performed by this collector. Cancelled jobs establish only observed cancellation and any actual partial log output; they do not establish a completed browser suite or a hypothetical pass/failure result. This package is CI evidence only, not a statement that a milestone has been accepted, a deployment happened, or unrun/provider/learning-effectiveness tests passed.

The bounded public scan checks home-path strings and recognizable GitHub/provider token and private-key patterns. It is not a universal secret or rights/provenance certification.
