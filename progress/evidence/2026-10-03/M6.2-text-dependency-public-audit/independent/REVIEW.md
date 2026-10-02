# Read-only review of five root public evidence packages

Reviewed root `7d464af6204c9947ed93b21901f3b8ecf817856e`, limited to the five named packages under `progress/evidence/2026-10-03`. Result: no blocking packaging, provenance or scope finding. This is independent review of root's aggregation/public transformation, not a new implementation review or a test rerun. Root, original sealed packages, runtime databases, keys and environment files were not modified or explored. Receipt and audit scripts exist only in this new private directory.

| Package suffix | Physical files | Original mapped files | Raw bytes unchanged | Exact home-prefix transform |
| --- | ---: | ---: | ---: | ---: |
| text-dependency-original-316bf693 | 28 | 26 | 12 | 14 |
| text-dependency-witness-676eb0ed | 52 | 50 | 35 | 15 |
| text-dependency-independent-676eb0ed | 11 | 9 | 5 | 4 |
| text-dependency-native-d49e4540 | 15 | 13 | 9 | 4 |
| combined-7d464af6-static | 27 | 25 | 18 | 7 |

All 133 physical files are exactly the five outer manifest entry sets plus the manifests themselves: 123 source mappings, five new scoped REPORT summaries and five outer manifests. Every `raw_sha256` matches its listed original file; every `published_sha256` matches the public file. Of the 123 mapped files, 79 are byte-identical and 44 differ only by exact `$HOME` to `$HOME` replacement. No unlisted file, duplicate path, symlink or broader text rewrite was found. Before/after public inventories are byte-identical, and every original mapping was rechecked at the end.

Nested owner manifests/SHA256SUMS remain original-source attestations. The outer manifest's `published_sha256` binds transformed public bytes; raw hashes are not silently reinterpreted as hashes of the transformed files. The six combined static gate receipts' 18 original log/before/after hash references also match the outer raw-source mappings.

The bounded sensitive-data checks parsed all JSON and JSON ACK bodies and scanned common authorization/token/secret/PEM patterns. There were no structured sensitive fields, serialized credential candidates or unconverted personal-home prefixes. All 52 `headers=` matches are test-code calls through `command(...)` or `case.headers`, not serialized HTTP header values. The scan artifact records only file paths, field names/line locations and classifications, never candidate values. The two screenshots are the exact previously inspected synthetic native captures; no runtime profile/database directory was packaged. This is a bounded package scan, not an assertion about unlisted private runtime state.

Scope and claim checks passed:

- Original 316 is explicitly `NOT_ACCEPTED_ALONE`; its 170 Python / 131 Web historical pass does not erase the later nested Concept pin P1. The repair is attributed to 676 and the root integration sequence. Original 1045-file inventories match each other; top-level before/after metadata differs (`all_equal_git` versus `unchanged`), which the new summary already states.
- Fixed 676's 180 Python, independent 676's 56 cases and d49's one native case are separate source-bound observations, not summed into a complete gate. Their underlying logs contain the stated results. The 56 comprise the independent review's own ten cases and 46 related cases; no native run is attributed to that review.
- The legacy compatibility oracle came from real fixed-316 synthetic owner/HTTP capture. The seven new contract cases establish decoding, canonical/hash preservation and ACK rendering against those same original bytes. The public report explicitly avoids claiming whole-old-database HTTP migration/replay. Current HTTP replay tests are separately identified.
- Freeze-time integrity and the original-base/descendant versus result-only-r2 boundary remain explicit. Result-only corruption invalidates published GET/publication ACK without rewriting the intact old candidate's Review/create/PATCH history. Pre-freeze arbitrary bare Concept pin substitution is not a new guarantee. Synthetic human decisions and the native software flow are not academic, provider or numeric approval.
- Limited 1063 and 1064 owner input sets remain distinguished from root's 1300 nonprogress inputs. The former exclude additional directories and `.env*`; root's actual input arrays contain 1300 entries, including six `.github` entries and 131 `docs` entries, with zero progress entries. No input file contents were opened merely because their hashes appeared in these inventories.
- The combined package's six completed gates all have exit code 0, fixed root HEAD, unchanged 1300-entry before/after arrays and correct original SHA bindings. Logs support 937 Web tests / 136 files, 841 build modules, Ruff, mypy 236 and verification counts 78 generated / 54 models / 130 routes. These are completed static/Web gates only.
- Full Python remains reported RUNNING, consistent with root's current status message; no unfinished full-Python log was packaged as final. Full native on 7d remains NOT_RUN; the prior 0b complete native 121 PASS / 1 FAIL remains explicitly unreplaced and under diagnosis. The d49 one-case native result does not claim full native acceptance or justify source publication by itself.

No source tests, browser sessions, provider calls or publication actions were performed during this audit. This receipt approves only the declared public packaging and its evidence boundaries; it does not change product/milestone/release acceptance.
