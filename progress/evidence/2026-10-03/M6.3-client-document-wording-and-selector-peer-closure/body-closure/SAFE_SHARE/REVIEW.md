# Static P2 closure and Import-test review: 83daf55c

Fixed comparison: 196b6a9a7da9be94a12eaf5d93f63fb6eb041edc...83daf55c1d536ab018182fc2419f3424faaba1e2. The producer confirmed the fixed clean tree; read-only HEAD/status checks agree. Three changed files were reviewed, with unchanged caller, Import and sole v3.0.14 spec context. No later WIP or producer run output was used.

## Standards

No new finding. The production change replaces two literals in LocalTaskDocument.tsx:32/:46; session/actor/workspace/Policy checks, input snapshot, late-callback guards, dirty behavior and Blob lifecycle have zero diff. LocalTaskDocument.test.tsx:108-121 observes unknown or authorized Broker state before downloading, then rejects the original wording in both document and visible explanation. Existing exact document assertions remain exact and change only the operation-status sentence.

The added native case (tests/e2e/local-task-document.spec.ts:75-130) explicitly chooses the actual browser-download bytes for ordinary Import. It hashes those bytes, verifies staged/preview/source/artifact digests, and compares the downloaded retained original byte-for-byte (:89-125). It checks draft state, user_supplied rights/citation, the unreviewed-preview explanation and a disabled confirmation button. The page mutation list is exactly POST /api/v1/imports (:127); direct APIRequestContext reads in the test are GETs. Authentication/role setup precedes mutation capture and is not claimed as zero mutation. Empty courses is a limited readback, not a whole-database no-write proof. This is static review of test design, not an executed native result.

## Spec

The 196b document/explanation P2 is CLOSED_STATIC. Both literals now describe this local operation as not calling Codex, without asserting overall disconnection. That preserves independently observed capability/account status under §6.6 (:354), §12.5 (:658) and §20.16.5 (:1467). No capability request, authorization gate or backend route is added.

The new test stays within existing ordinary Import §6.1 (:320), §20.3 (:1008) and Appendix A (:1569-1571): explicit file choice, source-hashed staging, unreviewed preview; no commit, publication, Codex generation provenance or quality approval is inferred. Existing imports.py:177-181 assigns user_supplied origin and unverified rights, and DraftPreview.tsx:69 distinguishes staging from publication/review. The test does not claim a controlled Codex task export/artifact-return workflow. All real execution and fixed-source acceptance remain the producer/root's separate responsibility.

The original 196b body OPEN report (SHA256 9006b83ade81e0b909a233dc8c832609590a9835aaf8d5bdbe2a0711984c1bd7) and prior footer closure remain unchanged. This reviewer ran no application, tests, browser, DB, CLI/model, network or system probe, and retried no previously rejected diagnosis. Only evidence hashing/scanning ran; no product source changed. One reviewer applied separate Standards and Spec axes. Whole fallback/M6.3 acceptance is not claimed.
