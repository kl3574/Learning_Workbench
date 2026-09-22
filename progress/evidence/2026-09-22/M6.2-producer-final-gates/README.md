# M6.2 final fixed-source local gates

Code `75b0ca5f83d809816b338c2d70cc5bfb9f1a3f83`; sole specification PRODUCT_DESIGN.md 3.0.7, SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.

New complete Python run: `2293 passed, 1 skipped, 2 warnings in 579.40s (0:09:39)`. Ruff and structural specification checks pass. Every run retains 949 before/after inputs matching the committed Git bytes; the final inventory was independently read from actual Git blobs during packaging. The one numeric-environment skip remains a skip, not an arithmetic success. The prior complete Python failure (3 FAIL / 2290 PASS / 1 environment SKIP) is preserved in its separate original gate package.

Only two historical fixture test files changed since `88daa0a23dab0e69f7009b9af670671c45f90924`. The previous 12-case native gate and mypy 180-file check remain attributed to that commit. `inherited-gate-binding.json` documents 947 unchanged engineering inputs, including all product code, native tests and configuration; no new native or mypy execution is asserted. Full frontend/native suites, real DeepSeek platform E2E, sealed arithmetic success, human content approval and teaching effectiveness are not established by this package. Remote CI must be read separately for its exact head.

Run `python verify.py` for public integrity; optional `--raw-base`, `--raw-home`, `--ci-home` replay exact raw hashes and recorded literal path substitutions. Identical input manifests share one public payload through manifest aliases. This verifier checks retained bytes, not product functionality.
