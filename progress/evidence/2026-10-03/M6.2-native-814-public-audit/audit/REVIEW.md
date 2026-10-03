# Independent public-copy readback: local native 814cda7f

No confirmed blocking discrepancy in the 25-file package. This is independent artifact/hash readback, not execution of the product gate.

- All 23 raw payload mappings and the new scoped REPORT hash match the exact 25-file outer manifest set. The only payload transformation is exact `$HOME` to `$HOME` (runner-prefix rule also checked).
- Independently recomputed all 1321 before-input hashes from Git 814cda7f73e864af7a499c0486b4fe9bc46fccb9 and compared the restored native worktree. Five actual generated docs/ui changes match preserved originals and archived outputs; all other 1316 were unchanged. Original unchanged=false remains intact.
- Original raw run.log SHA and terminal receipt agree: 126 passed (17.7m), one worker, exit 0. Original command has no retry override; fixed tests/e2e configuration and tests have no retry override; installed Playwright lib/common/index.js:591 defaults retries to zero. This is local 814 evidence, separate from CI 0ede/125.
- Independently recomputed concept complete metadata SHA and exact UTF-8 body SHA, original ordered arrays and five witness edges (only root advances), four current refs at r2, original/replay ACK equality and two API generations. Artifact SHA 238f26c66e576ba0c6756d78245828f28c4aac29895d83cf7cf806e82c0aeee7. Synthetic decisions do not establish academic acceptance.
- Both actual sealed numeric outcomes are environment_unavailable/BLOCKED/exit 1, empty assertions and null output. Each subsequent publication is HTTP 409 PUBLISH_NUMERIC_REQUIRED, external model calls zero. No physical numeric PASS.
- Bounded publication scanner passed all 25 package files. Six PNGs were hash-checked only, not visually reviewed here.

Private audit attempts 01 and 02 failed solely because the reviewer guessed incorrect config paths; their scripts/logs are retained. Attempt 03 passed 2738 explicit checks after locating the real tests/e2e/playwright.config.ts. No product source, package, original receipt, frozen tree or finish.py was changed or run. Initial producer toolchain precondition failure and prior gate failure claims remain unchanged.
