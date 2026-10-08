# Independent P2 delta closure at 51205a75

Fixed source: `51205a75c401911d98d54a42387fbaa43583da7f`; prior reviewed source: `9a2c8d032977411ce94724fd3be33403694c46e1`. The delta is exactly six paths, 258 insertions and 4 deletions. Sole norm remains PRODUCT_DESIGN v3.0.15, SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. This independent reviewer authored none of the source. Standards and Spec were separately evaluated by this one reviewer; no second parallel axis reviewer is claimed.

The original 9a2 report remains unchanged at SHA256 `376a3575d33356776c869931c6d6dce0f408d6f5d758d9f8ffa61a310b6dafda`, with its two P2 findings OPEN at that original source. This new report closes only the pinned repair delta. It does not rewrite the original finding, turn historical failures into PASS, or establish whole M6.3 acceptance.

## Standards

Zero additional findings. The change adds a forward migration rather than editing an applied migration. Its nine triggers protect three specifically identified immutable tables. The registered download-guard map is immutable, rejects guard keys without corresponding readers, and avoids an implicit global author rule. The guard is chosen from the same checked `(profile, kind)` owner binding as the initial read. The normal corruption fixtures now explicitly remove their relevant guard before creating the damaged state; production paths do not disable guards. No unrelated implementation change, public DTO expansion, old decoder change or new remote operation is present.

## Spec

**CODEX_IMPORT_APPEND_ONLY_PROTECTION — CLOSED_STATIC.** New `migrations/0035_codex_import_immutable.sql:2–10` rejects UPDATE and DELETE for batches, bindings and preview receipts. BEFORE INSERT guards reject existing batch/preview primary identities and all four binding conflict identities: import_id, source_id, import_job_id and aggregate_job_id+ordinal. This also stops INSERT OR REPLACE and upsert from evicting immutable rows. 0033 and every existing migration retain their Git bytes. The repair satisfies PRODUCT_DESIGN:1832's new append-only history requirement without rewriting old source facts or changing their schema/version. Tests retain explicit corruption coverage after narrowly dropping the relevant trigger.

**CODEX_ARTIFACT_DOWNLOAD_DELIVERY_ACCESS — CLOSED_STATIC.** `application/artifacts.py:64–75` captures the registered guard in the initial checked read transaction and invokes it after that transaction closes. `codex_artifacts.py:126–129` delegates this Codex-specific delivery check to the existing fresh `_deliver(subject=True)` transaction. `main.py` registers the guard only for `('codex_turn_output_v1', 'codex_turn')`; existing ordinary Import readers retain their original disclosure rule. The fresh check revalidates the original session ID and workspace, expiry/revocation, author role and both active assessment Policies. The change satisfies PRODUCT_DESIGN:1816,1828–1830, including rejection of subject body after loss of access. It does not create a new action or rewrite an original ACK.

Summary: Standards 0 additional findings; Spec 0 additional findings; both original P2s **CLOSED_STATIC at 51205a75**. The separately executed targeted author evidence below was independently read back; this reviewer did not execute product tests.

## Original targeted evidence independently checked

The author ran the final 218-line boundary test at fixed 51205a75: **22 PASS, 2 existing warnings, 49.46s pytest / 49.9934495909838s wrapper, exit0**. Original log SHA256 is `ddd9bccc457ca4c9e6bc72ded1c1424663d7938c76b7373f5483bcc84f168078`. That test includes:

- Twelve true SQLite mutation/replacement refusals across the three tables, with unchanged complete logical DB, exact source/preview readback and original command ACK.
- Four true post-transaction HTTP loss cases: learner role, logout, independent and open-book assessment. The original read connection closes before the real access mutation commits; the fresh delivery returns 403/401/409 and no original body.
- Four binding conflict identities, each checked before later FK validation could mask the actual immutable guard.
- A real pre-0035 migration catalog with normal HTTP-created batch/binding/preview rows; forward upgrade keeps rowids and every source-row byte, passes FK checking, preserves the current HTTP view and original ACK, and enables the new guards.
- A normal user-supplied Import that remains downloadable as the current learner with exact original bytes and no DB change.

The prior original REDs remain separate: migration 12 FAIL at 38685c69; delivery 2 FAIL at e8ec33be; expanded delivery 4 FAIL at 236bf2ef. The expanded four delivery cases pass at 48346a3f with the exact same full test bytes. e8ec33be had an unreachable error-code expectation corrected before the expanded RED: its failures already occurred at status200 versus the expected denial, and the changed error-code oracle is explicitly retained. Final function-by-function source comparisons were independently recomputed; no altered RED function is described as byte-identical.

Independent readback executed only Git/files/hash/AST comparisons, with exit0. `READBACK.json` SHA256 is `9936e7c9d10d5d6a17a56eec936e599ede93da4d7dbda437c47b8dd06535737b`. It binds all five selected original stage before/after maps (7294 Git file bindings), original receipt/log/test hashes, all **1459** final live nonprogress Git inputs, and the exact six-path delta. **1453 prior inputs** and every old migration remain byte-identical. The original 9a2 report/readback hashes also remain unchanged. Failure logs are private hash-only; neither their raw contents nor any DB/basetemp/cookie/secret material is a publication candidate.

At intake, the author's broader focused and related gates were still RUNNING. This report does not claim their result or borrow 9a2/2d6 counts for 512. No model, CLI, network or host probe was run by this reviewer. The verified targeted execution uses an explicit synthetic memory peer, and it does not prove actual production Provider/CLI isolation, physical numeric execution, general writers, content-quality approval, new UI completion or overall platform acceptance.
