# Fixed native run 03 supplemental readback

Source `29e864a6157f3bb23c6ced5d1a2f34f77bf3b875`, sole PRODUCT_DESIGN v3.0.15. Original command `make test-e2e`: **130 PASS, exit 0, 1210.772 seconds**.

The original outer runner **exit 1** remains unchanged: its list included six literal screenshot/metrics destinations but omitted four pre-existing interpolated widths at workbench.spec.ts:90-96. Two omitted destinations changed, so the original closed input check failed. This report is a separate readback, not a rewritten gate result.

The complete 1433-file before/after maps retain all differences. Exactly five tracked outputs changed: 1440 PNG, 1920 PNG, 390 Agent PNG, native zoom metrics and session conflict PNG. All 1428 other tracked files are byte-identical; excluding all ten existing generated destinations leaves 1423 source/runtime inputs unchanged and matched to fixed Git. Canonical itself remains clean and all 1433 files match the initial map. Nothing was restored, erased or copied back.

The five selected screenshots were visually read and contain the original synthetic UI only. Full successful native.log was manually read: test names/outcomes, loopback service lifecycle and dependency warnings; no auth or secret text observed. The selected maps have closed source-path/hash/blob fields, exact fixed Git membership, and no runtime storage payloads.

Original run 01 remains 130 FAIL / make exit 2, with observed first-two Chrome socket pathname errors. Run 02 remains 8 PASS / 1 INTERRUPTED / 121 NOT_RUN, deliberately stopped before canonical screenshot writes. Neither is upgraded by run 03.

Actual Restore and single-publication numeric receipts both report environment_unavailable/BLOCKED, numeric exit 1 and HTTP 409 PUBLISH_NUMERIC_REQUIRED. Thus native software behavior PASS is not arithmetic success. No real remote provider, actual Codex CLI/model, paid model call or academic/source/pedagogy acceptance is established.

Only explicit publication-candidates/allowlist.json entries are candidate shares; no publication performed. All other browser profiles, databases, ZIPs, caches, keys, traces, result payloads and prior raw failure logs remain private.
