# Exact evidence whitespace review

Conclusion: no blocking finding for six literal path-specific `-whitespace` declarations. No wildcard extension, source change, raw-byte trimming, or secret-scanner exception is warranted. This review does not apply the proposed attributes.

Observed source HEAD: `4a5c6de3b74fdc1659389326c746e05ef19ff00b`. The actual staged `git diff --cached --check` exited 2: six files and 25 warnings. The complete original stdout/stderr are retained; stdout SHA256 `d4a574e3e8342ac23568724c941a71e6c1aeed4f9673658791f3cb5f42268f19`. All 683 staged paths were inspected for scope: 680 evidence paths and three progress files; the separate three-file progress check passed. No product source was staged.

| Evidence path | Warnings | Verified format |
| --- | ---: | --- |
| `progress/evidence/2026-09-28/M6.2-authoring-observation/raw/change.patch` | 6 | unified-diff unchanged-empty-line context markers |
| `progress/evidence/2026-09-28/M6.2-import-publication-ui/raw/candidate.patch` | 2 | unified-diff unchanged-empty-line context markers |
| `progress/evidence/2026-09-28/M6.2-publication-combined-gates/m62-publication-combined-gates-v1/supervisor.stdout` | 1 | captured stdout original final blank line |
| `progress/evidence/2026-09-28/M6.2-publication-http/m62-publication-http-development-v1/http-final.diff` | 5 | unified-diff unchanged-empty-line context markers |
| `progress/evidence/2026-09-28/M6.2-publication-http/m62-publication-http-spec-independent-v1/preliminary/reviewed.diff` | 5 | unified-diff unchanged-empty-line context markers |
| `progress/evidence/2026-09-28/M6.2-publication-service/m62-publication-service-spec-independent-v1/reviewed.diff` | 6 | unified-diff unchanged-empty-line context markers |

All five patch/diff files were parsed without application by `git apply --numstat`; all 24 flagged lines were also independently checked inside complete unified-diff hunks as exact hex `20 0a`, representing an unchanged empty line. Removing that context marker would change recorded patch bytes. The stdout final empty line was verified in its private original and its public derivative. Its only existing content transformation is exactly two home-path aliases; this review proposes no new transformation.

Nine original mappings across the six public paths were checked against actual raw size/SHA256, staged public size/SHA256, package mapping, and worktree equality. Shared public bytes legitimately serve multiple owner/reviewer originals. Five patches are byte-identical to their mapped originals. `VERIFY.json` records every mapping and digest.

The current `.gitattributes` only grants the existing evidence/docs log rules. `suggested-exact-attributes.txt` contains the six literal additions, without glob characters, under dated immutable evidence paths. These declarations affect whitespace diagnostics only; no credential scanner logic, product source, index, or original artifact was modified. The real original check failure remains preserved. Root must perform and record the post-change check; no future PASS is claimed here.

Scope: bounded publication-format review only. No product tests, browser execution, CI dispatch, remote write, or product-gate recertification.
