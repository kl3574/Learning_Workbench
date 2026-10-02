# Exact historical bootstrap-marker finding: independent manual triage

Verdict: **confirmed synthetic unit-fixture false positive, limited to the exact path and old Git blob below**. The raw history scan remains FAIL; this review is a separate manual disposition, not scanner PASS, and not a general bootstrap/string/path allowlist.

- Path: `apps/web/src/api/sessionAccess.test.ts`
- Historical commits: `0f06d57d25353867493168a5e693f150c3cee535` and root cherry-pick `0b885ec31bafbd6f64a83108b4fc491a8179b28a`.
- Both resolve to Git blob SHA-1 **8313fb6e099915b4833e8b5bf3b3a372a116f9f2**.
- Exact data SHA-256 **8fa06d0473ec716319d4c45a630090f97486bd47817a3e3280ba03f57e8b7a56**, 5086 bytes.
- The fixed scanner reports one suspect match: line 56, zero-based byte interval [4481,4516), bootstrap marker suffix length 24; pattern index 6. No other scanner pattern matches this blob.

The entire fixed blob was read. It imports Vitest and the actual client, and the hit is a fixed string literal passed to jsdom history.replaceState inside the final unit test. Before connectSession or request is invoked, line 57 replaces global fetch with vi.stubGlobal/vi.fn. All bootstrap requests resolve through the test's local deferred Promise<Response>; other paths return a constructed synthetic Response. Line 4 constructs its synthetic role/workspace/CSRF response. There is no real bootstrap generator, server, remote transport, SecretStore/environment read or externally obtained value in this fixture. The literal is not a captured actual bootstrap capability. The test subsequently verifies the URL fragment was cleared, and afterEach restores the stub. Every test that invokes client requests installs its own controlled fetch first.

Root shortening commit `2dbeb7a00d09f75b3143a8a602f4a6cae25373f6` changes only this literal, ten bytes shorter. New blob SHA-1 **b646aa7e630f33f56c471031b5add8a747ae390a**, data SHA-256 **9c2e1c078faa00c3b4b4fbb9508e4e33173ac56c502488d0ca818e26a23fc824**, 5076 bytes. Applying the same fixed scanner inspect function to that one new blob returns no finding. This does not erase or change the old blob result, and does not claim a repository/history scan passed. The root's reported eight transport test PASS were not rerun as part of this triage.

The scanner source was read from the fixed 2db commit, unchanged and archived by hash; its exact pure inspect function produced the stored per-blob findings. No scanner/history/production/progress/remote mutation occurred. Private evidence files include both exact test blobs, scanner source and machine-readable identities/findings. Any manual publication disposition should match **both exact path and original blob/data hashes**, retain the raw FAIL finding and reviewer rationale, and reject substitutions. Other strings, artifacts and raw Playwright headers receive no clearance from this review.

This does not add a v3.0.13 product contract: the two preceding production fixes implement current-role/Policy gating and immutable original receipt recovery inside existing endpoints and DTOs. They add no new actor permission, cross-page replay or route. The marker shortening is test data only.
