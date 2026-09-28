# M6.2 narrow Import text-block publication service — fixed candidate

Implementation `dec1d937523f4596da4c39bcc27750d9132c752c`; baseline `ce42bf8cae734e49166a1472184fd9c3fa875bc7`. Sixteen files, isolated worktree clean at freeze. Sole product/engineering specification `PRODUCT_DESIGN.md` SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`; repository copy equals the user's current-directory file. This is a real application service with actual immutable Content writes; HTTP/UI registration and overall M6.2 acceptance remain outside this slice.

## Implemented outcome and exact boundary

`DraftPublicationService(database, reviews, imports).publish(identity, draft_id, body, key) -> ContentRef` accepts the existing strict four-field `DraftPublishWrite`. The only supported new write is an actual still-pending, learner-visible Import explicitly parsed as markdown/text, with original metadata r1 and an unused original Content object ID, no private solutions, symbols/assets, base revision, concepts or dependencies. It requires a real complete machine Review plus an explicit persisted human mathematical N/A reason and sources APPROVED, exact candidate/material, original owner warnings, current author/session/Policy and actual physical source/report/body bytes. Tests supply explicit synthetic human actions; no model or user approval is invented.

One actual writer transaction adopts the candidate now and records its independent draft→in_review→approved→published lifecycle with server-private CAS. The exact original candidate/review revision/hash and selected human record are frozen. These are current adoption and checks, not fabricated past state changes or a global latest-Review rule. Content's owned port performs absence CAS, actual immutable metadata/body write, current pointer, invalidation/outbox; Provenance freezes the exact original Import/source relation. Producer DTO/state and the existing Import.commit algorithm remain unchanged. Migration 0018 adds only its owned lifecycle, events, permanent command and result tables with immutability/transition triggers.

An original successful actor/route/key command is permanent and rechecks all current access, full current Quality history including recursive attachments, original approval/admission/warnings, actual Import Job/input/source membership, original physical source/body and historical immutable Content before returning the original ACK. Later rejection or Content r2 does not rewrite that ACK. Real Import cancellation or explicitly copy-remapped whole-Import commit also preserves it; a new command is refused. Unmapped original Import.commit still returns its existing ID collision, mapping rehashes its actual parent graph, and the copied block receives no approval by shared body/Import ID. Generic cache-clock advancement to 2200 plus a new service instance exercises cache independence; this is not a 24-hour wall-clock soak test.

Actual two-connection publication races (same/different key), original Import.commit race, and Review rejection race are covered. Five SQLite fault locations prove all owned database tables remain unchanged on failure, followed by real successful retry. Content writes use the existing BlobStore durability implementation; fixtures already staged the body bytes, so these tests do not claim to create or recover new orphan blobs. An actual pre-0018 database holding pending Import/Review/human facts is upgraded with its online backup, original tables/Review preserved, and then published.

## Evidence and failures retained

Final stage 18: 238 related behavior tests passed across 11 named files. Stage 19: 55 database/migration tests passed across 3 files. Stages 16/17: mypy and Ruff passed for the changed code. These are separate focused gates, not a full-suite pass. `final-actual-git-verification.json` proves every one of the 1021 engineering inputs of each final stage equals its before/after manifest and the actual committed Git bytes. `run-ledger.json` verifies all 19 receipts/log hashes and every retained source copy; complete logs and source snapshots remain in each stage directory.

| Stage | Exit | Actual outcome | Complete log SHA256 |
|---|---:|---|---|
| 01-first-publication-red | 1 | 1 failed: requested service absent (module import), initial feature RED | `89718b2390f54874bb69383c4ada2e72be7b14b25d0a0a2d2c0f504db4a2d83e` |
| 02-first-publication | 0 | 1 PASS: real Import/Review/human/service/Content chain | `d33974ff7801e9e757c91ed32fd10a3a51c0ef29ec904180e5b125b8b83189cb` |
| 03-terminal-and-history | 0 | 7 PASS: original command and real terminal histories | `ef42791547c7b081525f63157ca1100803f3726289dcff0aa2a4f64de0c10a41` |
| 04-recorded-admission-red | 1 | 1 failed: TRUE product RED, rehashed result removed original required warning ACK but was accepted | `0a45e2a94bd1ca623068bfd6e0ff2e8d9ca4cd06d74ab9db82304c439e19a571` |
| 05-recorded-admission-green | 0 | 40 PASS: full historical owner/admission revalidation repaired 04 | `44839f715c195f22663b7b73231c75bf7abc50db5da912235ea87bdc713fdcd8` |
| 06-integrity-and-atomic | 1 | 35 PASS / 1 fixture failure: nonexistent provenance Import FK prevented corruption setup, not product RED | `1d32218e456122900d9ded8290eab2fd34940f37f23027d9ac08e66cfc44ac3a` |
| 07-integrity-fixture-corrected | 0 | 36 PASS: fixture now uses a second real staged Import before membership corruption | `879db4c64b8118be56e1d3265536f63abe54d9f61649ef487073b5b3c87cb5f6` |
| 08-first-ruff | 0 | PASS | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 09-first-mypy | 1 | 16 static typing errors in import_publication union narrowing; fixed local payload narrowing | `c5e373f73d3641465fe66e28b5cc2e799d5a5effcc3840c255233b00ba5cb361` |
| 10-owner-scope | 1 | 10 PASS / 1 fixture failure: workspace INSERT used nonexistent name column, not product RED | `77dd8867afca176582f8db3f9a6c10f4ec2cd8667af1ff6dd673bf8bd33cb002` |
| 11-scope-and-cas | 0 | 20 PASS: corrected workspace title/created_at fixture | `f0e0ba11f7b98c4ef368854151616eed549845995876c5daef43aa8c01cd2bde` |
| 12-original-job-binding-red | 1 | 1 failed: TRUE product RED, historical ACK omitted actual Import Job input binding | `2e2523c3e3e28fa1bf15dfcdcd1c830cf0bf335dccb382f5f826fbf521acfab0` |
| 13-original-job-binding-green | 0 | 49 PASS: Jobs owner origin/input/status fact port used on new and historical paths | `b0c2a2e3ba314c374c706e9e44390698be9131393f3fad494d60d6fd2c6e56ff` |
| 14-upgrade-and-later-evidence | 0 | 3 PASS: actual old DB upgrade and both early/late recursive attachment corruption | `05e8e94ae583364f47d17b80a709490712208aa5e55e2690bdb3264a22d7b947` |
| 15-review-race | 0 | 1 PASS: actual concurrent Review rejection and publication serialize safely | `817d17eaecc25df5b125ce6fdef3e0b3cfe45028419eb2a365440c6e3a45e7e1` |
| 16-final-mypy | 0 | PASS: 10 application/repository source files | `14fdf673bd175fe32ef42df34666481bb15e465313f7dbef32d0aea2ba76a26e` |
| 17-final-ruff | 0 | PASS: 10 sources and 4 task tests | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 18-final-related | 0 | 238 PASS / 11 files; 2 existing Starlette/httpx deprecation warnings; 144.45 seconds reported by pytest | `f25bd0b5f7d2115135e19308d98a51c4fed263b6c68edeb547d03373fb9d0970` |
| 19-migration-regression | 0 | 55 PASS / 3 files; 1.38 seconds reported by pytest | `342ceea6015065da850e67e2b343bdd891e44032bd80231b4a29467323564c8d` |

The two reproduced integrity defects are stage 04 (recorded warning admission trusted too much) and stage 12 (original Jobs input identity missing on historical replay). Both have permanent real-owner regressions and green repaired runs, finally included in stage 18. Stages 06/10 were incorrect test setup and stage 09 a typing failure; they remain intact and are not counted as product RED. Stage 01 demonstrated a missing implementation, not an exercised integrity defect. No failed log or fixture error was removed.

## Security, review and pending work

Current workspace/session/role/revocation/expiry are checked again even for stored-command ACK. All three live assessment modes reject the private Quality/publication read while existing safe Job control remains usable. Rehashed records, source and report byte damage, recursive attachments added before or after publication, Review command membership damage, exact original source membership and publication chain/command damage fail closed without repair writes. Protected model instances are revalidated with serializer warnings treated as errors; diagnostics use fixed ApiErrors.

Self-check complete; independent Spec and Standards reviews are requested against this fixed commit and remain pending. No external network, real Provider, real numeric execution, actual user human approval, HTTP registration/test, browser publication UI, global lifecycle GET/needs_changes workflow, mathematical/generated/private-solution/question/group publication, existing-object update publication or full platform suite was performed. Machine math/source/teaching NOT_RUN is retained; the nested read-only admission observation retains publication NOT_RUN because it is not itself a publication receipt.

Next: independent review and any required correction, then root-owned HTTP/main/generated integration and real HTTP contract tests. No push, main-tree edit, credential access or specification edit occurred.
