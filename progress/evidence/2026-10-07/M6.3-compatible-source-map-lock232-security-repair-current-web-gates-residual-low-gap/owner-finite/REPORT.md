# M6.3 auxiliary frontend dependency security repair

Status: **READY_FOR_ROOT_SOURCE_INDEPENDENT_REVIEW_WITH_RESIDUAL_LOW_GAP**. This auxiliary task preserves the single main active milestone, product semantics, API, data schema, normative document, progress, and all CI/test budgets.

Frozen source commit: `2323558615803830049a02ddfade49450d3fd77e`, parent `079a008cf88b37e4517cb391503a1e7393ccf374`. Only `apps/web/package-lock.json` changed. PRODUCT_DESIGN v3.0.15 SHA-256 is `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

| Actual command result | Exit | Actual count / qualification |
|---|---:|---|
| Original read-only audit | 1 | 4 affected package entries: 3 low, 1 high; **not clean** |
| Targeted compatible lock update | 0 | Only source-map-js entry 1.2.1 → 1.2.2; direct manifest and every other lock entry unchanged |
| Post-update read-only audit | 1 | 3 low, 0 high, total 3; **still not clean** |
| Locked fresh install | 0 | Lifecycle scripts disabled; patched lock unchanged before/after |
| Original frontend lint | 0 | Original command and source budget |
| Original frontend typecheck | 0 | Original command and source budget |
| Full original Vitest | 0 | **1421 tests / 167 files passed**, actual footer retained |
| Original build | 0 | 879 modules transformed; Vite >500 kB chunk warning retained |
| First native test selection | 1 | **0 tests executed**, No tests found; anchored name selection failure retained |
| Corrected original Reader native test | 0 | **1 passed**, new owned dirs, source timeout/config unchanged |
| Publication scanner | 0 | **23175** staged/tracked files; manual provenance review remains required |

The original and patched audits both ran on fixed Node 24.21.0 under a fresh noncredential environment, two distinct empty owned npm user/global config files, and a new public npm cache. Both original lock-input hashes and the read-only before/after assertions are retained. No existing npmrc, .env, credential, user profile or user DB was opened; HOME was absent and was not repurposed.

The high finding is `source-map-js@1.2.1`, dev-only in the lock, through PostCSS and css-tree, whose parent constraints both permit `^1.2.1`. The [official GHSA](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) identifies patch `1.2.2`; the [upstream release](https://github.com/7rulnik/source-map-js/releases/tag/v1.2.2) confirms the indexed-source-map DoS repair. Official registry version/tarball/integrity metadata and the installed dependency tree are retained. No attacker-controlled indexed-source-map path in the deployed product was established by the audit summary or this limited source inspection.

The 3 low entries `katex`, `micromark-extension-math`, and `remark-math` propagate one [KaTeX upstream advisory](https://github.com/KaTeX/KaTeX/security/advisories/GHSA-238p-pmpm-9mq7). Locked KaTeX is `0.16.47`; fixed `0.18.2` lies outside existing `^0.16.0`. Official registry metadata for latest micromark-extension-math `3.1.0` still has that range. The advisory requires other prototype pollution or renderer-option prototype influence and unsafe use of KaTeX HTML. Inspected project code uses remark-math syntax/AST with custom MathJax SVG, not an identified KaTeX HTML-rendering call. This is an applicability qualification, not proof of general immunity. The residual state is **GAP_NO_COMPATIBLE_PATCH_ON_CURRENT_MATH_CHAIN**. No force repair, suggested remark-math downgrade, unverified override or renderer-semantic change was applied.

The exact original native test is `real imported directory, title search, worked-example link, long formula and frozen original download` in `tests/e2e/reader.spec.ts`. Both attempts have original command/stdout/stderr/receipt records and source bindings. The corrected attempt uses original Playwright configuration, `/usr/bin/google-chrome`, a new short owned TMPDIR, fresh synthetic data/results/browser cache, fresh XDG paths, and disabled Python bytecode writes while reusing the fixed public Python environment. Runtime DB/profile/cache contents are excluded from the finite review allowlist.

All **23175** original tracked files have before/after live SHA-256 maps; after-scanner hashes match the frozen source. Git mode/type/blob maps prove the only changed entry is the lock file; all other **23174** entries and all old progress entries exactly match parent 079a008. The canonical lock still matches the original hash. No canonical copy, existing-tree modification, user b895 modification, remote push, CI dispatch/rerun/cancel, paid or model request occurred.

Original lock SHA-256: `283f10246c2c8a9483257135e4552ec6523eb929caf61d69e73c56a74ec8b672`.

Patched lock SHA-256: `ae43fcb0a0a0eaf2a1981eb5c1c5523d530c80980f15e50fa10380190d05f23d`.

See `REPORT.json`, `ADR-DEPENDENCY-SECURITY.md`, and `REVIEW-ALLOWLIST.json` for finite original evidence, precise lock delta, official-source receipts and maps. All material remains private and unuploaded. Root source-independent review and normal integration are pending. New remote CI, full patched browser/Python suites, actual providers/Codex, product acceptance and learning-effectiveness were not run in this auxiliary scope. This does not accept the whole CI, M6.3, or production model and does not change the earlier CI working-input map status from NOT_CAPTURED.
