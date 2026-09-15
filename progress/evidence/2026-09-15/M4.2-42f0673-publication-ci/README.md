# Evidence-publication commit CI readback

Checked evidence commit: `42f06736c98659d4c656de6bce78506b8fe76609`. Previously accepted software source: `1db509f9bf4c296eb6fb7f3d99d94b5f243d2e7c`.

This is the follow-up CI of the evidence publication commit. It neither replaces nor rewrites the accepted source test record. The commit changes 1308 paths under progress; its two backend checks failed at Ruff on 12 newly published Python evidence archives. Those failures remain failures even if a later commit repairs publication.

Actual final check conclusions: `{"failure": 2, "success": 10}`. Both workflow and job metadata are preserved. Backend pytest was not reached after the failed lint step; no hypothetical pytest verdict is inferred.

| Event | Run | Workflow conclusion | Browser job | Actual browser summary |
| --- | --- | --- | --- | --- |
| pull_request | [34930121766](https://github.com/kl3574/Learning_Workbench/actions/runs/34930121766) | failure | 104256409565 | {"passed": 82} |
| push | [34930120233](https://github.com/kl3574/Learning_Workbench/actions/runs/34930120233) | failure | 104256404820 | {"passed": 82} |

The browser readback retains every actually reported case number, marker, source location, duration and final summary. A cancelled job or missing summary establishes only observed partial output. Actual checkout commits are read from each job log; a pull_request checkout may be a synthetic merge commit and is not called an identical direct head checkout.

All original check/run/job JSON and full job logs remain unchanged in the private home cache. This lightweight public packet includes metadata, bounded failure/test excerpts and the exact original JSON/log hash index; it does not duplicate full logs. Public copies redact home prefixes, with original and derived hashes in the manifest.

Final PR API read: state=open, draft=False, merged=False, head=8d4b36f57b3ace950f9d3f0e750c4810fce9b0ec. PR head may have advanced; its actual value does not change the commit checked here.

Collection performed only read-only GitHub GETs and local evidence reads/writes outside the repository. No rerun, cancellation, merge, PR edit, browser start or repository mutation was performed by this collector. This packet does not claim a deployment, milestone acceptance or actual provider call.
