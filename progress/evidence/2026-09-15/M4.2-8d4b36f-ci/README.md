# Exact-source GitHub CI readback

Source head SHA: `8d4b36f57b3ace950f9d3f0e750c4810fce9b0ec`. This package contains read-only GitHub API responses, actual job logs, job step metadata, bounded timestamped check readbacks and the final PR state. Original API/log files remain unchanged in the home cache. Public copies replace home directory prefixes only; the manifest records exact original/public hashes and transformations.

Final check outcomes: `{"success": 12}`. All 12 checks are terminal. A completed check is not necessarily a successful check. Each event has six jobs. The detailed receipt keeps workflow conclusion separately from job conclusions.

| Workflow event | Run | Conclusion | Start | Last workflow update |
| --- | --- | --- | --- | --- |
| pull_request | [34930949036](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036) | success | 2026-09-15T04:59:35Z | 2026-09-15T05:12:35Z |
| push | [34930946760](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760) | success | 2026-09-15T04:59:33Z | 2026-09-15T05:12:48Z |

Actual job start/completion times and original line-numbered test/check excerpts are in `final-ci-receipt.json`. Complete job logs and their metadata are included, so the excerpts do not replace original evidence. PR workflows can check out a synthetic merge commit: each job reports the actual checkout hash found in its log separately from GitHub workflow head_sha. The package does not call a PR merge checkout an exact direct source checkout.

| Event | Job | Conclusion | Started | Completed |
| --- | --- | --- | --- | --- |
| pull_request | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036/job/104258843855) | success | 2026-09-15T04:59:38Z | 2026-09-15T05:00:00Z |
| pull_request | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036/job/104258843729) | success | 2026-09-15T04:59:38Z | 2026-09-15T05:01:24Z |
| pull_request | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036/job/104258843680) | success | 2026-09-15T04:59:37Z | 2026-09-15T05:00:06Z |
| pull_request | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036/job/104258843671) | success | 2026-09-15T04:59:38Z | 2026-09-15T05:12:34Z |
| pull_request | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036/job/104258843653) | success | 2026-09-15T04:59:38Z | 2026-09-15T05:05:31Z |
| pull_request | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34930949036/job/104258843465) | success | 2026-09-15T04:59:38Z | 2026-09-15T05:00:29Z |
| push | [integration](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760/job/104258837255) | success | 2026-09-15T04:59:36Z | 2026-09-15T05:05:27Z |
| push | [spec-contracts](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760/job/104258837223) | success | 2026-09-15T04:59:37Z | 2026-09-15T05:01:58Z |
| push | [security-publication](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760/job/104258837208) | success | 2026-09-15T04:59:36Z | 2026-09-15T04:59:59Z |
| push | [browser](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760/job/104258837205) | success | 2026-09-15T04:59:36Z | 2026-09-15T05:12:48Z |
| push | [backend](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760/job/104258837183) | success | 2026-09-15T04:59:36Z | 2026-09-15T05:00:26Z |
| push | [frontend](https://github.com/kl3574/Learning_Workbench/actions/runs/34930946760/job/104258837064) | success | 2026-09-15T04:59:36Z | 2026-09-15T05:00:18Z |

PR 48 final API read: state `open`, draft `False`, merged `False`, head `8d4b36f57b3ace950f9d3f0e750c4810fce9b0ec`. Head matches this checked source: `True`. The current PR head may have advanced while an older source run was being archived; its state is not substituted for the original checked SHA.

No rerun, cancellation, merge, PR mutation or repository write was performed by this collector. Cancelled jobs establish only observed cancellation and any actual partial log output; they do not establish a completed browser suite or a hypothetical pass/failure result. This package is CI evidence only, not a statement that a milestone has been accepted, a deployment happened, or unrun/provider/learning-effectiveness tests passed.

The bounded public scan checks home-path strings and recognizable GitHub/provider token and private-key patterns. It is not a universal secret or rights/provenance certification.
