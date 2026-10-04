# M6.3 client-only four-input fallback — fixed local result

Fixed head `28c92bdad181fdc0e297c05507f01234d26a86ac`, base `892c7b8d333253e1913e71433bc17621a286698a`, branch `feat/M6.3-local-task-document`. Tree `$HOME/.cache/learning-workbench-acceptance/m63-local-task-document-oct04` is clean. No remote action or canonical-tree change. Sole PRODUCT_DESIGN v3.0.14 SHA256 `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144` is byte-identical to the approved external source; §6.6 lines 350–354 supplies the offline fallback goal. This is the narrow client implementation authorized by the parent; it does not establish the wider R-23 flow or complete M6.3.

The author explicitly downloads only this page's topic, declared prerequisites, objectives and proof policy as `learning-task.md`. The file says 未连接 Codex. The click obtains and strictly checks current SessionResponse, including original actor/workspace, author role and independent/open-book restrictions; pending results are fenced by access generation, workspace, port, input changes, parent busy and unmount. Blob URLs are revoked. Provider/source refs, consent, saved commands/ACKs and credentials are never part of the file. No server write, content read, job, Codex process, account, model, tool, or turn is used by this download path. Existing manual Import remains a separate action. Temporary form dirty status and close protection remain. Switching actor cannot reuse the original temporary form. Existing capabilities text now distinguishes this local document from unavailable controlled Codex export/artifact integration.

Commits: `d973e71f45909722f26d477358aee4d5d7141056` (5-file UI implementation); `5fb3e784e780cd5c65e85d8419422d332818c8e1` (new native case); `28c92bdad181fdc0e297c05507f01234d26a86ac` (exact accessible textbox readback plus static status correction). Total 8 paths, 238 insertions/8 deletions. No backend, schema, generated contract, shared native harness, old test, timeout or retry change. SOURCE_BINDINGS and fixed-source pin all changed files, source.patch pins the complete delta. Existing dependency/toolchain links were read-only; no dependency installation, uv sync, or copied environment/database. DEPENDENCIES records lock equality.

## Executed stages, with original failures retained

| Stage | Source | Result and limit |
|---|---|---|
| 01 | base 892 + test WIP | 1 FAIL: requested download button absent. |
| 02 | base 892 + implementation WIP | 1 PASS. Original test bytes match stage01's recorded SHA. The later preserved `original-test.tsx` is verified against that original input map; it was not captured at the original run time. |
| 03 | base 892 + WIP | 27 PASS / 1 FAIL: new test harness imported a nonexistent setRole helper. |
| 04 | base 892 + WIP | 28 PASS / 5 files after using the real typed role endpoint. |
| 05 | base 892 + WIP | strict FAIL: new role test omitted required typed Idempotency-Key argument. |
| 06 | base 892 + WIP | strict PASS after adding the explicit synthetic test key. |
| 07 | fixed d973 | 28 PASS / 5 files; 16 new local-document cases plus related authoring coverage. 1383 nonprogress inputs, exact Git, unchanged, clean. |
| 08 | fixed 5fb | New native test and imported TS dependencies: strict/noUnused PASS. |
| 09 | fixed 5fb | Native 1 FAIL, default 5s assertion at line46. Real download exact bytes/omissions, one session GET, 1440/390 geometry and close guard had passed. After-return exact getByLabel did not find the filled textarea. Role revocation NOT_RUN; no final success receipt/file copy was produced. |
| 10 | fixed 5fb | Complete Web 1054 PASS / 146 files. This does not override stage09. |
| 11 | fixed 5fb + explicitly archived diagnostic test WIP | Native 1 FAIL on unchanged original value assertion. Safe DOM observations before AND after guard show exact label count0, exact role textbox count1; the SAME original textarea remains connected, with original value; dialog open/modal true and inert false. |
| 12 | fixed 28c | New native 1 PASS, 5.1s case / 8.1s Playwright / 11.8304s monotonic runner, 0 retries. Includes the previously NOT_RUN real role-revocation denial. |
| 13 | fixed 28c | Complete Web 1054 PASS / 146 files, 10.77s Vitest / 12.7264s runner. |
| 14 | fixed 28c | Web strict/noUnused PASS. |
| 15 | fixed 28c | Production build PASS (850 modules). Existing >500kB chunk warning retained. |
| 16 | fixed 28c | New native test and imported TS dependencies: strict/noUnused PASS. |

Stages08–10 and12–16 retain full 1384 nonprogress before/after input maps with exact Git bytes, clean status and unchanged inputs. Stage11 is accurately WIP, not exact fixed-source. All stages preserve UTC endpoints and monotonic duration separately. Runner `run-stage.py` is preserved byte-identical to `run-stage-v1.py`; each receipt records command and exit. No full backend or whole-native gate was run for this client-only change; the existing wider gates remain separate parent-owned evidence.

## Confirmed native selector issue and corrected evidence

`DIAGNOSIS.json` pins the observations and installed locked Playwright1.63 core bundle hash. Its getElementLabels obtains implicit label text through elementText, recursively including the controlled textarea's text node. The accessibility name remains exactly 例题主题. Failure was already present BEFORE opening the close guard; it is not evidence of guard failure, lost input or actor remount. The two new-case assertions now use the exact accessible textbox name. The post-revocation count is stricter: the old label query was already zero while the field existed. No broad selector, sleep, retry, timeout extension or production guard change was used. Both native FAILs and screenshots remain private, hashed in RAW_MANIFEST.

## Actual browser result at fixed 28c

A real synthetic workspace/API/UI/browser downloaded a UTF-8 document of 378 bytes, SHA256 `cdad751cd9f7b66e7cc4930aa5dad371a6751e6a463263663dc0019a75dc37e1`. The complete expected Markdown (including multiline alpha topic and original prerequisite spaces) was compared exactly. Deliberately selected synthetic provider, block ref and its hash are absent. The download interval made only `GET /api/v1/session`. A real explicit setup APIRequest later changed this synthetic session to learner (200); the still-visible button performed another real session GET (200 learner), did not download again, and the protected form was actually removed using the exact role query. Total downloads1, observed page mutation requests0. Authentication and explicit role-control setup POSTs are outside that page-request assertion; this is not a claim that the whole test had zero setup writes.

The close confirmation appeared, return retained the exact original topic, and download did not clear dirty state. 1440px geometry: dialog420..1020, inner598/scroll598; 390px: dialog14..376, inner360/scroll360, document390. Both saved screenshots were visually read: the download explanation, button and result fit without horizontal overflow; the desktop capture shows the corrected capabilities text. `offline-task-actual.json` and the exact synthetic Markdown are archived. No HTTP/CLI mock was used for this native; unit tests separately use controlled transport and fake IDB.

This demonstrates a local document and current author-denial workflow only. Codex execution/authorization/turn/artifact mapping are NOT_RUN here; physical numeric/Provider acceptance and whole-M6.3 completion are not inferred. No old interrupted diagnosis was resumed. Independent d973 static review is a separate single-reviewer report, not independent execution of these tests; later delta review is separately attributed by its reviewer.

## Sharing

Only SAFE_SHARE entries and PUBLIC_OUTER_ALLOWLIST may be copied. Raw logs/metadata and full maps are retained; share candidates use solely exact `$HOME` → `$HOME` replacement. Only the two final synthetic screenshots are candidates; all original failure screenshots/error contexts stay private and hashed. Runtime DBs/profiles/download temp directories are outside this evidence package and are not candidates. Scanner supplements manual provenance review, not a universal absence-of-secrets guarantee. Do not glob-copy this directory. Original FAIL results stay FAIL.
