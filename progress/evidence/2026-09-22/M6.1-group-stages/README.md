This package preserves bounded, historical group implementation evidence. It is a cache-only publication candidate, not a test rerun or a current-head full-gate result.

The manifest maps every logical raw alias to its content-addressed public file. Repeated snapshots/logs/PNGs are deduplicated by exact public bytes. Raw receipts retain their original raw SHA fields; resolve those fields through the alias map. Public SHA/bytes and every byte-span transformation are separate. Fixed home-prefix replacements are recorded; two synthetic test-credential literals in failure-context source excerpts are explicitly redacted without publishing the original literal in the manifest. No other source/log/error/warning/result content is rewritten.

Evidence by stage:

- Contract/pure: 138 passed (36 group unit, 33 group contract, 11 existing Authoring contract, 58 shared helper). Initial Ruff formatting and mypy inference failures remain alongside repaired passes. These tests do not demonstrate SQLite/HTTP/model/math behavior.
- Numeric development: scoped Ruff/mypy and the original numeric regression (20 passed, 1 actual environment skip, 2 warnings, 21.76 s). The stage summary references another agent's separate 24-case numeric package; that external package is not included or newly validated here.
- HTTP: initial fixture failure retained; final 3 group cases passed with 2 dependency warnings (6.03 s), original 2 HTTP cases passed (2.45 s), scoped Ruff passed. Six group operations, both shared GET variants, permission/revocation and safe Jobs control are bounded synthetic-loopback evidence. New HTTP tests did not execute a calculator.
- Native 01: two actual selector failures retained; no timeout was increased. Native 02: two group cases passed (15.5 s), lesson and practice at 1440/390, lost prepare ACK replay, explicit private read and actual role-change clearing. **The original 02 lesson artifact fields `declined` and `approved` are pending revision-1 preview ACKs, not decision ACKs/readbacks.** Original artifacts are preserved except declared public redaction.
- Native 07: the later lesson-only case passed (10.7 s). Its `first_preview_ack` and `second_preview_ack` are distinct from complete `decline_ack`, actual `decline_readback` GET and complete `approve_ack`. These assert exact check/hash/revision-2 decision/Job binding; decline has no Job or result, approval binds one separate queued Job. Actual numeric outcome remains **BLOCKED/environment_unavailable**, exit 1. Neither BLOCKED nor schema PASS is successful arithmetic.
- Native 03: the unchanged two original single-block cases passed (12.7 s), validating the original default fixture/helper selection. New helper has a closed, test-only group factory option; original case/timeout/lifecycle files retain recorded Git identity. This does not rerun the full native suite.
- Native strict TS checks use a cache-only alias to actual installed Playwright declarations for direct `.mjs` imports; no fake API declarations or runtime-source changes. App TS config does not include native cases. Python fixture Ruff and scoped mypy (`follow-imports=silent`) passed; preexisting imported helper diagnostics are outside that scope.

Each result binds only its declared source map at the original time: 18 contract, 22 numeric, 31 HTTP, 459 native, and 8 native-static input entries. Those maps are not complete installed-binary inventories. Historical tests do not cover later changes, including the separately identified Provider-history integrity fix. Development results are not the later unified gates. No hosted vendor or paid model was called, no real learner data is included, and all candidates remain unreviewed/unpublished with math/source/pedagogy boundaries intact.

Four original tracked PNGs are copied from their exact fixed Git blobs and compared byte for byte against the current files during packaging. `capture/tracked-png-readback.json` records both hashes/sizes and the observation time. This proves current equality; the native drivers did not capture four temporal before/after PNG snapshots, so no such claim is made.

Excluded: databases/WAL, browser profiles, bootstrap/session/CSRF values, real keys, runtime private data, archives/ZIP and other agents' evidence packages. Logs/drivers and error contexts are evidence text, never executed by the verifier. Screenshot/geometry inspection is summarized in visual-review.json. Failed and skipped results remain visible.

Verify public files, exact aliases, aggregates, raw receipt hash resolution, actual decision ACK relationships and every actual publication target with:

    python3 -B verify.py

To also replay each transformation against local raw originals and verify the four Git blobs, supply the existing private paths without copying them into public evidence:

    python3 -B verify.py --raw-cache-base PRIVATE_CACHE_BASE --home-prefix PRIVATE_HOME_PREFIX --repo PRIVATE_CHECKOUT

The home prefix must include its trailing slash. Offline verification explicitly reports raw/Git checks not performed. No tests, browsers, production mutations or network actions occur. The manifest's public aggregate is SHA256 of sorted public_files records using JSON sort_keys=True and separators=(',', ':'); manifest.json itself is the external hash anchor. The separate alias aggregate uses the same canonical encoding. Publication-scan.json and the verifier cover the manifest too; no file silently escapes the inventory.
