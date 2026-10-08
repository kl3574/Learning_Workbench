# Fixed turn client 5c static review

Head `5c845a0bb259fe0ccb36c08f62d6999e58f10a37`, base `ff656a2fc360551f872bb0ff4ebe14d8240d82d3`. Sole PRODUCT_DESIGN v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`, previously fully read and unchanged here. Only new `apps/web/src/features/codex/turnClient.ts` and its test changed. Necessary decoder/transport/strict DTO dependencies were read as fixed Git objects. One peer performed both axes separately; no claim of two subagents.

## Standards

No confirmed Standards finding. The helper has one transport/decoder responsibility, named closed DTO types, existing typed endpoints and a bounded relationship validator. The shape checks and server-owned historical truth are explicitly distinguished. No tooling-enforced or purely stylistic finding is counted.

## Spec

**P2 OPEN — terminal newline passes whole-string UTC/identity/hash admission.** `turnClient.ts:17–21` executes an anchored JavaScript UTC regexp but never checks that the matched string is the complete input. JavaScript `$` can match before a final line terminator, so `2026-10-04T00:00:00Z\n` passes its regexp and the later calendar check compares only captured seconds. The shared shape validator (`providerSchema.ts:32`) also uses `RegExp.test`, so its generated UTC pattern does not reject this case first. Similarly `turnClient.ts:74` delegates route identity to `validIdentity` (`providerSchema.ts:58`), whose `$` accepts `turn_test\n`; the generated transport URL-encodes that string instead of validating its ID pattern. Nested actor/Job/ref IDs and SHA fields use the same schema pattern test, so a preparation with an otherwise valid `actor_session_id="actor_test\n"` or `preparation_sha256="a"*64+"\n"` is admitted as a closed DTO. These are static counterexamples, not executed probes. This contradicts spec L424 immutable ASCII identifiers, L426 UTC time, and the strict typed fields in §20.17.2–3. It does not establish server authorization bypass: the server remains authoritative and may reject subsequent requests.

Minimal fix: require a complete regex match for the new helper's patterned primitive values and route IDs, while retaining original valid bytes. Include trailing LF/CR/Unicode line-separator cases for UTC, nested IDs and SHA, plus zero-request invalid path tests. Do not trim or normalize the bad bytes. The shared validator need not be broadened as part of this bounded change if a local named schema check covers all applicable new fields.

Other checks: preparation request Unicode is cloned and kept exactly; materials form an exact ordered subsequence of selected block refs; POST response must bind original request/session; direct reads bind target; pages reject duplicate/mixed-session items and carry the original cursor; cancellation binds the Job and expected revision. Control validation mirrors named DTO relationships for ordered approval membership, consent revision, timestamps, terminal Job mapping and manifest presence. Current session uses the new named projection while bootstrap create retains its old decoder. No page, memory journal, permission flow or whole UI functionality is implemented or attested by this helper review. No additional confirmed Spec finding.

## Evidence boundary

No test, application, CLI, model, DB, browser, network or system probe was run. Root's reported 31 focused/strict development results and ongoing formal gates are not this peer's execution and do not close the counterexample. Original setup NOT_RUN and synthetic fixture failures remain outside this private report unchanged. One attempted dependency locator `bootstrapSchema.ts` did not exist; review then used the actual `bootstrapClient.ts` implementation. This was a read-only inspection error, not a product failure.

Standards 0 confirmed findings; Spec 1 P2 OPEN. Status NOT_ACCEPTED for strict decoding until a fixed source closes the finding. Share only SAFE_SHARE.json entries plus PUBLIC_OUTER_ALLOWLIST.json; no other material is authorized.
