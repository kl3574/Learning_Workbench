# brace-expansion dependency patch

Exact source `986f7cf1485dcaa0ef6f39bf461b7cfc74585316` changes one package-lock entry, from 5.0.9 to 5.0.12 within the existing minimatch range. No direct dependency, application behavior or test was edited. CodeMirror was not present in this isolated baseline; its separate installation exposed the preexisting issue.

The public upstream advisories are [nested recursion](https://github.com/advisories/GHSA-qhr7-859c-m2p7), [comma recursion](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p), and [quadratic expansion](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr). Exact registry metadata and both npm audit results are retained.

Actual isolated reproduction: npm ci at the original lock, then the included bounded Node probe (128MB heap, five-second outer deadline) threw RangeError on deep nesting. After npm ci with the patched lock, the identical probe completed and ordinary brace expansion retained its exact expected output. This is a library regression check, not proof of application exposure or a broad security audit.

Before audit: one high-severity affected package, exit1. After audit: zero reported findings, exit0, at this observation time. Full Web562/94files and strict TypeScript/production build766 passed; the preexisting large-chunk warning is preserved. All1123 tracked non-progress source bytes match the finalized commit and were unchanged during both gates. Gate receipts show the parent HEAD with its captured lock-only diff, not a test of unchanged parent source.

Raw outputs remain locally archived; only the exact worktree prefix was replaced with WORKTREE/ in public copies, with hashes/counts and no dropped lines. No real Provider call, mathematical/teaching validation, native browser gate, release or deployment is claimed here.
