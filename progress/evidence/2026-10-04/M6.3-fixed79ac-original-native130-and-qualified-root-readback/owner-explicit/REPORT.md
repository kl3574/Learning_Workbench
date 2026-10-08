# M6.3 fixed 79ac complete original native gate

The original `make test-e2e` completed **130 PASS**, with native exit 0 and wrapper exit 0, on fixed `79acabc2566318f9ea099da067abd7e9c4f010a2`. This is a new complete-suite execution, independent of the earlier 29e 130-test run and the separate 92c outbound native run.

- Start: `2026-10-04T12:54:01.745990+00:00`.
- Terminal time: `2026-10-04T13:14:39.447471+00:00`.
- Actual command duration: `1237.701` seconds (suite reporter: 20.6 minutes).
- Isolated tree: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-native-formal-79ac-owner-oct04`.
- Private evidence: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-native-formal-79acabc2-oct04`.
- Sole v3.0.15 spec SHA: `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.
- Sealed runner SHA: `74e2760359323795da8d4fa8fd324473c82979ecae1082799e5d3afc44006fa8`.
- Raw native log SHA: `656c0073010bb821e5c0e53cdf9ae297421b4c1e8db47a39afcc8923628cf660`.

All original tests/e2e sources, Makefile, package command, and node entry script were byte-identical to the earlier original suite. This only reuses the original program, not its outcome. Config, per-test budgets, timeouts and retries were unchanged. Dependencies were existing symlinks; there were no installs. The suite used a new short mode-0700 TMPDIR, private data and output directories. No additional system/security probe or manual application request was introduced. PRE_RUN_BINDING retains the historical sealed NOT_RUN state; receipt.json is the actual terminal result.

## Full input and generated-output accounting

Both complete manifests contain all **1465 nonprogress Git inputs**. Before execution every actual blob matched fixed Git and status was clean. The full manifests are not equal afterward: **5 existing generated outputs changed**, while **1460 total inputs remained byte-identical**. Excluding the explicitly enumerated **10 existing generation destinations**, **all 1455 remaining runtime/source inputs stayed byte-identical**. A further independent post-run readback checked all 1465 actual file hashes against the final manifest.

Actual changed paths:

- docs/ui/m1-after-1440.png
- docs/ui/m1-after-1920.png
- docs/ui/m1-after-390-agent.png
- docs/ui/m1-native-zoom-metrics.json
- docs/ui/m1-session-three-way-conflict.png

The complete 10 destinations are in generated-output-paths.json, traced to current workbench.spec.ts lines 91/96/98/99/107/275 and zoom.spec.ts lines 26/27. All 10 before and after originals, plus the actual complete binary Git diff, are retained. The isolated tree is deliberately dirty with these 5 actual outputs. Nothing was reset, restored, staged or copied back to canonical. Canonical application files were not edited by this runner.

Before map SHA: `a2188db41a719f1f01b5b628d759ce82ee5e4280b663094f62935731602433e9`.
After map SHA: `495097c1d7ed62d946ff45699da425a342e7d31aa6d453652cf1e95bd7322cdb`.
Actual binary diff SHA: `cceae0c83237648574eefa62b709093680ee6180286471bfbe5a9f20f7d51d93`.

## Actual boundaries retained

Both actual Restore-numeric and single-publication receipts report `environment_unavailable`, `BLOCKED`, numeric exit 1, and publication HTTP 409 / `PUBLISH_NUMERIC_REQUIRED`. The first records zero new model calls. The second records zero external model calls and one controlled loopback call. Their test PASS verifies honest refusal and preserved facts; it does not establish numerical success. Raw receipts remain private; POST_RUN_AUDIT.json records a clearly authored field-selected summary and binds the raw hashes.

The existing production control-only bootstrap browser case separately reports `real_thread=PASS`, one persisted session/permit/finished record, and the same records after restart/replay. It verifies a real ready mapping and durable readback, not a mocked runtime. Its own fixed receipt explicitly does not independently prove OS isolation or count CLI starts; there is no model turn, login or tool request. Thus this report does not claim zero OS-level CLI processes. Existing capability reads returned available=true, authorized=false, approvals/interrupt/artifacts=false. The wrapper's `actual_codex_cli_model=NOT_RUN` is an acceptance boundary for real Codex model/turn execution, not a measured zero for every CLI control process.

Actual model turn/tool execution, production runtime isolation, paid-provider/model acceptance, academic/source/pedagogy approval, and overall M6.3 remain NOT_RUN. Original bootstrap control facts are not upgraded to those claims. No follow-up environment diagnosis or acceptance rerun was made.

## Manual review and explicit candidates

All nine generated M1 PNGs and two capability PNGs were individually opened. They show the original synthetic fixture, 1440/1920/900/390 layouts, native drawers, long-formula local scrolling, three-way session comparison, and actual 200% browser zoom. No auth code, cookie, CSRF or secret material was seen. The zoom record reports Chrome 154.0.8037.97, width 1440 to 720, DPR 1 to 2, and final scrollWidth 720. Two additionally viewed bootstrap screenshots remain private rather than sharing original command identifiers. This is the author's image inspection; root's independent review remains separate.

The entire native success log was read. It contains the 130 test results, existing synthetic diagnostic messages, normal server metadata and dependency/color warnings; no credential value was found. Complete maps contain only relative tracked filenames and hashes. The exact publication-candidates/allowlist.json is a candidate list, not publication permission or a recursive directory allowance. Text candidates use only `<LOCAL_HOME>` to `<LOCAL_HOME>` and record both hashes/replacement counts; PNG candidates are original bytes. Authored audit/report text is clearly separate from immutable raw receipts.

Databases, browser profiles, temporary contents, keys/cookies, archives, unreviewed result files, raw numeric/command receipts, raw binary diff, and bootstrap screenshots remain private. Earlier 29e evidence and 92c bounded acceptance are unchanged and retain their original separate statuses.
