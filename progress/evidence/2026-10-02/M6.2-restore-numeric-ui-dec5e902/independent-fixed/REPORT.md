# Independent Restore numeric UI review — final repair readback

## Conclusion

One demonstrated P2 was found in original UI 2e90c235 integrated at 8acdd2e4051dd22b513fcf79f2c8684ea37b2d78: CRLF textarea selection offsets were used against unnormalized original source. Root repaired it in **06a787b485f115a74e67a61ab6e7e4be4cb8e097**. The exact original red probe and expanded boundary probes now pass. No remaining demonstrated P1/P2 in the reviewed UI scope.

Sole spec: PRODUCT_DESIGN v3.0.12, SHA 1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7; §20.14 and Edit-only §20.10.1 replay boundary. The reviewer changed no product, backend, spec/progress/generated, main or original UI tree. Two detached review trees preserve original and repaired fixed sources separately; only private review tests are untracked. No Provider/remote operation.

## Standards

A separate independent subagent reviewed all 13 original changed files and recovery/journal/Jobs dependencies. No demonstrated standards/engineering-boundary defect. It explicitly distinguished durable unknown cancellation (dirty/unload guard, panel may close with normal confirmation) from a busy/unread control (close blocked). This axis was static, without an independent functional test claim.

## Spec finding and repair

Original `RestoreNumericMaterialEditor.tsx:18` feeds real HTML textarea UTF-16 offsets into `selectedSourceSpan`; textarea CRLF normalization made every prior CRLF shift original positions. Actual DOM selection of `2` in `🧮 原文 é\r\nGiven x=2...` produced `{start:"16",end:"17",quote:"="}` rather than `{start:"17",end:"18",quote:"2"}`. The numeric relation validators reject this bad location, so the issue blocked valid material entry rather than granting execution or publication. Exact original codepoint/quote binding at spec line 1253 requires retaining original line breaks.

Root's repair maps normalized displayed UTF-16 offsets back to original UTF-16 offsets, then computes original Unicode codepoints and quote without mutating body bytes. Static reread found no new issue. Original probe SHA **2424152fdf4934f295b1e2f2c8d724af5c03dfca25f80faadd248cc5fa0850df** is byte-identical before/after. It was 2 PASS / 1 FAIL on 8acdd and is 3 PASS on 06a.

Expanded independent DOM tests cover CRLF, lone CR, mixed line endings, spans across CRLF/lone CR, exact selection of a line break, astral characters, combining pairs and individual combining codepoints, empty selection, half surrogate, and 512-codepoint limit calculated against the original source. **14 PASS**. No source normalization or numeric inference was added.

## Fixed-source evidence

| Source | Actual command/check | Result |
|---|---|---|
| 8acdd original | 156 existing Restore + 9 private recovery probes + 12 NumericCheckPanel/useAuthoring dependencies | 177 PASS, 16 files; focused-02 |
| 8acdd original | CRLF selection three-case real DOM probe | 2 PASS / 1 FAIL; original selection-01 preserved |
| 8acdd original | Actual original restore-numeric.spec.ts with random-port RestartRuntime/private no-webServer config | 1 PASS, 11.9 s; native-02; execution BLOCKED_ENVIRONMENT |
| 06a repaired | All Restore + dependency + 26 private probes | **200 PASS**, 19 files, 2.21 s; focused-fixed |
| 06a repaired | TypeScript strict/noUnused lint | **PASS**; lint-fixed |

Both repaired gate manifests contain **1225 unchanged inputs**; original native gate contains 1220 (including the private recovery probe). Original tracked production source and repaired tracked production source each match their respective commit blobs. `FINAL_READBACK.json` pins the repaired source, probe hashes and untracked-only status; every command, exit code, log hash and before/after input list is retained by capture.py receipts.

Nine independent recovery/permission/control probes confirm exact raw lexical input retention after first IDB abort, combining Unicode/CRLF reason retention, unmount/fresh restore without writes, late permissions after Policy re-lock, actual access-generation mutation discarding a late ACK, old page/actor inability to replay or replace unknown commands, workspace/actor memory isolation, new frozen material conflict preserving raw form, real useAuthoring busy/unknown cancel propagation, and real DOM rejected approve → fresh read → explicit decline with a distinct key. Manual plan entry, separate approve and no automatic numeric POST remain intact.

## Limits and preserved failures

Original native execution actually started at 2026-10-02T12:13:49.469612Z, exited 1 with verdict BLOCKED/outcome environment_unavailable; this is not numeric PASS, human math/source validation, publication acceptance or complete M6.2 delivery. Exactly two original-key preview requests (first ACK intentionally lost) and one independent decision POST were recorded; pageerrors=[]; real JSON and 1440/390 screenshots are retained in original native-output-02. The newer 7023 native Review/publication extension was statically read only; its run belongs to root evidence. Repaired 06a native/full Web/full Python were NOT_RUN by this reviewer; root owns their separate gates.

Original private harness failures remain visible: native-fixed exited before any test because external config needed package type=module; adding only evidence-directory metadata fixed loading. The first combined focused run sampled the private probe's parent dirty callback before React effect delivery (safe=false/closeSafe=false already held); replacing its immediate assertion with waitFor made the probe reliable. Exact v1/v2 probe copies and original captured hash verification are retained; no product change was made for either harness failure.

Original red report/evidence: `$HOME/.cache/learning-workbench-acceptance/m62-restore-numeric-ui-independent-evidence-oct02/PRE_FIX_REPORT.md`. Final repair evidence: this directory. Findings are closed by exact red-to-green evidence rather than by overwriting the original records.
