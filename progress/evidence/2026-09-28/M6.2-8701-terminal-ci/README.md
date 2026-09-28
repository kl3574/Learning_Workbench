# 8701 terminal CI evidence

Push run **36389800538 SUCCESS**; PR run **36389807970 FAILURE solely browser**. Both are original attempt 1. No rerun, cancellation, product retest, source change or remote mutation was performed.

| Source | Actual checkout | Actual tree |
| --- | --- | --- |
| push | 8701c8a04b654c2462e4311f0128201507ebaf7e | dca622334045f5136345d2f604c4a9e892bf893c |
| PR merge | d8205101aaa035c7f1594f40305ae66b8e239837 | dca622334045f5136345d2f604c4a9e892bf893c |

| Scope | Push | PR |
| --- | --- | --- |
| backend | 731 PASS, 2 warnings | 731 PASS, 2 warnings |
| integration | 1665 PASS, 1 numeric environment SKIP, 2 warnings; 1958.30 s | 1665 PASS, 1 numeric environment SKIP, 2 warnings; 1108.22 s |
| frontend | 538 PASS / 91 files | 538 PASS / 91 files |
| spec-contracts | 608 PASS, 2 warnings | 608 PASS, 2 warnings |
| security | 13456-file scan PASS | 13456-file scan PASS |
| browser | 107 PASS, 14.9 m | 106 PASS / 1 FAIL, 20.0 m |

Scopes overlap; do not sum them. Both numeric skips retain the original sealed-runtime BLOCKED_ENVIRONMENT/FAIL statement, not successful calculator execution. All six fixed APT installations succeeded independently of product results; original dpkg lines bind bubblewrap 0.11.1-1ubuntu0.3, apparmor/libapparmor1 5.0.2-0ubuntu1~26.04.1, libseccomp2 2.6.0-2ubuntu5.

The unchanged original Tutor case passes once in the push log (14.8 s); PR fails its original completed-heading 5000 ms assertion. PR's Node freeze is 14793.909155 ms, after answer_delta seq4 was validated and applied at 14539.48 ms. No completed event is observed. The API snapshot is on a separate clock, read after the assertion, and does not establish final worker state. The post-assertion Run read failed marker does not mean Run.failed: its 400 ms GET and safe projection errors are collapsed to one marker within a 500 ms observation cap, without a recorded error kind.

PR shows the same observed answer-increment-before-freeze pattern as 4cc failures; original a944 freezes had no response on their last SSE. Push has no uploaded successful-run diagnostic artifact, so internal push/PR timing cannot be compared. Historical a944/4cc failures and three local 4cc synthetic passes remain separate. Root cause remains **UNKNOWN**, and no repair is claimed.

This package retains all 12 complete job-log derivatives, every bounded polling/raw acquisition receipt, terminal/checkout/tree metadata, source comparison, and all eight original PR artifact members. The original ZIP has GitHub digest `7c5c0440c62c657a2951f15898107770bf3626ec297f39abbc12c5116fd7c4e9`; its container and the identical early private copy are explicitly hash-bound exclusions, as the unchanged scanner disallows archives outside synthetic fixtures. The eight members include diagnostic JSON, error context and one original PNG; there is no trace file. The PNG was visually inspected for privacy, shows only synthetic textbook/loopback proposal metadata, and is byte-identical. This is not causal or UI acceptance. Early failure copies are retained and match the monitor originals.

Included text changes are exact filesystem aliases and selected GitHub attribution string spans only. All 12 logs preserve every line and have path substitutions only. Raw/public byte counts, hashes, span offsets, original-span hashes and replacements are recorded in `manifest.json`. Artifact members remain unchanged. No scanner exception, broad line deletion or image edit is used. The unchanged repository scanner and bounded supplemental checks cover the public files; arbitrary prose still requires provenance review.

Offline verification:

```sh
python verify.py
python verify.py --raw-base CACHE_PARENT
```

`CACHE_PARENT` contains the private `m62-publication-8701-ci-v1` directory. Both commands make no network request or product test. This local handoff does not itself prove a later publication or full-platform/real-model/teaching acceptance.
