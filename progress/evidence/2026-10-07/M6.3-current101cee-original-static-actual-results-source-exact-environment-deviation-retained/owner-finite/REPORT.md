# Current 101cee independent original static acceptance

Fixed source: `101cee47d8e746dddac81fb6e8829069fcabff09` in `$HOME/.cache/learning-workbench-acceptance/m63-integrated-1564-static-source-oct07` (detached clone). No canonical/progress/remote/source mutation was performed.

## Actual original command results

| Original command (one invocation each) | Actual status | Evidence |
|---|---|---|
| `make lint` | PASS / exit 0 | `30-original-make-lint/{command.json,stdout,stderr,receipt.json}` |
| `make typecheck` | PASS / exit 0 | `32-original-make-typecheck/{command.json,stdout,stderr,receipt.json}` |
| `make verify-spec` | PASS / exit 0 | `34-original-make-verify-spec/{command.json,stdout,stderr,receipt.json}` |
| `git diff --check 101cee47d8e746dddac81fb6e8829069fcabff09` | PASS / exit 0 | `36-original-git-diff-check/{command.json,stdout,stderr,receipt.json}` |

Original static distribution: 4 PASS / 0 FAIL / 0 BLOCKED_ENVIRONMENT / 0 NOT_RUN. `make types` was a corrected root-plan alias, NOT_RUN; it was never deliberately invoked. The actual Makefile target is `typecheck`.

The first explicit setup used `/usr/bin/python3` (actual CPython 3.14.4), producing original `uv sync --frozen --offline` exit 2 against the project's `==3.12.*` requirement. This is one preserved setup BLOCKED_ENVIRONMENT, resolved separately; original command/streams/receipt and complete failure-after map `08-AFTER-FAILED-UV-SETUP.json` remain. The successful setup uses owner-named public `$HOME/.local/bin/python3.12` (actual 3.12.13), the explicitly approved public uv cache, and installs 37 locked packages offline. Anonymous locked npm ci installs 257 packages; scripts were disabled for this dependency install. Fresh owned HOME/TMPDIR/npm cache/config and a literal child environment were used; host environ/profile/credentials were never inherited/read. The named public Node archive matched 31890184 bytes and SHA fd8e59d5a511510f6a298afb548f18c7d2b1be404d8b4a27d94fbe49f56cb2d6 before `filter=data` extraction into this clone. Actual Node v24.21.0/npm 11.19.0/uv 0.11.21 were recorded; the initial four-version group has one group exit code, not invented per-version return codes.

## Full source preservation

All 1564 tracked nonprogress inputs, including 82 generated/derived paths, were recorded before setup, after the initial failure, before resume, after both successful setups, before checks, after each original target, and after diffcheck. Every map includes fixed Git mode/blob/size, index mode/blob/stage, live bytes/SHA/blob/mode, and inode/device/mtime. All original map files were saved before assertions. Full strict equality (including stat) across all ten maps: **TRUE**. `40-ALL-SOURCE-MAP-COMPARISONS.json` contains every comparison and all changed-path lists; original maps preserve any unexpected writes instead of normalizing them. Whole Git tree and index metadata also remain equal. Canonical and CI working before/after are NOT_CAPTURED; these are actual isolated local records only.

Mypy actually reports 295 source files; frontend lint/typecheck are the original package scripts. The original verifier calls `generate(root, check=True)` and reports 82 generated artifacts, 54 models, 147 routes, 38 requirements, 33 scenarios, 27 tasks. Its temporary in-memory/synthetic fixture verification is structural. The verifier itself reports `M0_structural_baseline_only`, `product_acceptance=NOT_RUN`, real provider/Codex/learning effectiveness NOT_RUN, publication NOT_CHECKED.

## Acceptance boundary

This finite report proves only the four original local static commands and full isolated source preservation. It does not run pytest, native/browser tests, Vitest, build, model, CLI turn, host probes, or remote operations. Root-owned current-combination complete gates are external to this capture. Prior original079 CI failures are retained; no root-cause closure or CI PASS is claimed. M6.3 NOT_ACCEPTED; M7 NOT_UNLOCKED. The sole norm remains v3.0.15 SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec. See PRODUCT_DESIGN.md:748-756 for independent layers, Makefile:19-25/34-35 for original commands, and scripts/verify_spec.py:74 plus scripts/generate_contracts.py:332-347 for check-only generator behavior.

All eleven original command capture sets were independently read and bound by byte size/SHA to their original receipts (`41-INDEPENDENT-ACTUAL-CAPTURE-BINDINGS.json`). `FINITE-ALLOWLIST.json` names the finite safe original captures, both complete before/final source maps, intermediate-map metadata comparisons, setup failure, environment/software/archive metadata and this review. No raw API, fixture body, ZIP/DB/profile/credential/auth/private form content is included. Owned dependency/cache contents are excluded. `SHA256SUMS` and `SEAL.json` freeze the candidate; original evidence is retained independently.
