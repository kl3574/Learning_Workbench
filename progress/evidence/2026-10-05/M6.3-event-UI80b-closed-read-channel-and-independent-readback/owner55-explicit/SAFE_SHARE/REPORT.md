# M6.3 Codex read-only event UI — fixed 80b405a9

Source: `80b405a9c859c47bff0d9b74465f1e7370268218`, parent `4353a05570afd9f2378c904b5594998de21bc474`. Sole PRODUCT_DESIGN v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`, especially §11.4 and §20.17.3/.7. Seven changed files: six new Codex event files and six-line integration in CodexTurnPanel. All 1492 existing nonoverlap engineering files retain their original Git blobs. Source is clean; canonical/source publication was not modified.

The typed GET consumer uses the registered generated endpoint and standalone Codex schema. Six closed payloads remain separate from Tutor. It verifies raw Unicode, strict JSON/frame keys, JobID:seq, turn/Job binding, consecutive new sequence, exact duplicate frames, status Job identity, UTC, and terminal closure. The event-only checker preserves whitespace-only nonempty answer deltas; shared Provider/Tutor validators are unchanged. Every explicit connection and protected event delivery fresh-reads current session; actor/workspace/author/Policy, generation, parent admission, port, turn/Job and lifetime changes isolate the display. HTTP denial clears it. Disconnect/EOF never invent a Job outcome; reconnect is explicit from the last admitted in-page cursor. Mount and remount perform no reads. No new POST, command journal or local persistence exists.

Approval and manifest events display IDs and explain the separate explicit details action. This slice does not implement those detail pages or initiate them automatically. Parent controls, original preparation/start/grant/cancel ACKs, command replay, forms and dirty guards are unchanged. Event terminal is an observed historical fact; current controls/results still use existing explicit GET actions.

## Actual fixed gates

| Stage | Actual result | Scope |
|---|---|---|
| fixed-80b405a9/focused | 53 PASS / 2 files; exit 0 | New actual fetch/stream decoder and component/parent tests |
| fixed-80b405a9/web | 1331 PASS / 159 files; exit 0 | Complete web suite, includes the 53 |
| fixed-80b405a9/strict | PASS; exit 0 | tsc noUnusedLocals/noUnusedParameters |
| fixed-80b405a9/build | PASS; exit 0; 867 modules | Existing large-chunk advisory retained |
| native-03-80b405a9 | 1 PASS; exit 0 | First successful bounded browser scenario |
| native-04-80b405a9 | 1 PASS; exit 0; 3.408s command | Same scenario with strengthened all-request remount assertion; final native source |
| native-types-05 | PASS; exit 0 | Exact native-04 test/config with actual Playwright declarations |

Each fixed runner checked all 1499 tracked nonprogress engineering inputs against the fixed Git objects before/after, with equality and clean Git status. Progress is the only tracked-path exclusion. Private native runners also bind each config/test/package/harness input and verify it unchanged. The dependency links are read-only reuse and are not Git input claims. Runners record monotonic command durations and raw log hashes; they did not record separate UTC start/end clocks. Do not infer UTC duration from log times.

The final native case is real Chrome, the production React event component/typed client, Vite same-origin proxy, and a synthetic local HTTP session/SSE server. It checks all six payload types, exact whitespace/newline/non-BMP answer text, explicit after_seq=4 reconnect, reload zero automatic GET, fresh actor denial, GET-only requests, and empty page errors. Screenshots at 390 and 1440 were visually inspected; document widths match viewports. Native-03 and -04 screenshot bytes are identical. The browser mounts the production component in an explicit synthetic harness, not the complete production backend/owner. Native-03/04 are repeated executions of one case; do not sum them as distinct acceptance cases.

## Preserved failures and corrections

- 01-whitespace-red: suite import failed on missing /tmp transform cache, zero tests. This is not the whitespace RED. Its original directory name was provisional. No independent before-map was captured for these initial WIP stages.
- 02-whitespace-private-temp: same WIP source with a dedicated temporary directory actually ran one test and failed on the legal whitespace-only delta. The independent event schema checker resolves it; the original assertion remains in the fixed focused suite.
- 03-panel-development: 46 PASS / 1 new parent-test failure because it edited selection before the existing refresh completed. The fixture now waits for the original completion message. The accompanying strict run recorded three diagnostics, followed by a remaining missing Idempotency-Key diagnostic observed during development; these were test/type corrections, not changes to existing production commands.
- 04-abort-transport-red: 31 PASS / 1 FAIL; pre-aborted consumer still called transport and surfaced its raw error. Fixed consumer returns before GET when aborted and safely classifies transport failures; same assertion passes in the fixed suite.
- native-80b405a9: ESM configuration load failure, zero cases. native-02: 1 FAIL before mounting the component, original 5s locator timeout retained. The exact cause of the second mount failure was not separately captured; using a standard Vite TSX entry produced the successful native-03. No production code or original assertion/timeout changed.
- native-04 native-types: initial direct .mjs declaration lookup failed; the actual browser case passed independently. native-types-05 supplies the same repo-standard .mjs-to-Playwright-type mapping and passes against unchanged native-04 inputs. No any/relaxed strictness was added.

All initial logs and source variants remain in the raw manifest. WIP source copies are identified as WIP, not retrospectively called fixed Git gates. The reported later outcomes do not rewrite earlier failures.

## Limits

Production backend event ownership was read statically, not re-executed here. No real Codex CLI/account/model/tool/network execution, backend DB, full native suite, academic quality approval, or automatic repair was performed. The previously reported root 4353 Web failure and frozen Python gate retain their independent status; this slice's successful Web run does not explain the cause of the earlier failure. Review here is the implementer's self-check, not independent peer acceptance. Root review/integration remains separate.

SAFE_SHARE.json is the exclusive candidate list. Candidate text changes only the exact `<LOCAL_HOME>` prefix to `<LOCAL_HOME>`; binary screenshots are exact. Original failure logs remain private. No DB, ZIP, browser profile, cookie/header/session response, credential, or global CLI configuration is deliverable. Native request evidence contains only synthetic method/path pairs and the synthetic answer string.
