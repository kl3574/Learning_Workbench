# M6.3 Artifact UI — bounded implementation evidence

Final clean source: `8f2c884510aef987b80ae62a018c33c83d89388c`, parent `bc978839e7e28818ae341bb0367c87fe448662ea`, base `4353a05570afd9f2378c904b5594998de21bc474`.
Tree: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-4353-owner-oct04`.
Sole specification: PRODUCT_DESIGN v3.0.15, SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec, §§20.17.6–.7.

Implemented explicit manifest GET, closed generated wire and canonical manifest hash checks, concrete file/failed or unknown source state/three NOT_RUN notices, individually selected supported artifacts, controlled download with byte hash and fresh delivery access, independent complete original actor/key/body/basis journal, explicit exact replay, current aggregate/ordered source-bound Import children, and actual ordinary Import/draft preview navigation. The artifact flow does not automatically commit, Review or publish. A user's later ordinary Import action remains explicit. Separate artifact command/form stores and retained memory do not alter older bootstrap/prepare/outbound journals.

Authoring receives artifact dirty/safe/isolated state. Restore reads current actor/workspace/Policy before and after local material reads and prior to delivery. A later checked ACK is retained under its original actor before a delivery denial. Unknown commands and immutable selection snapshots survive remount. Current GET does not overwrite the original queued 202 ACK.

## Exact scope

15 paths, listed and hash-bound in FINAL_BINDING.json and owner-delta.patch: 11 new artifact source/test files; AuthoringPanel bridge; optional requestedImport bridge in ImportWorkflow; Capabilities statement and its existing test. No backend, contract generation, old bootstrap/prepare/outbound/approval/interrupt journal, SSE, canonical or sealed prior tree edits. 1504 complete non-progress final inputs; 1489 unchanged base inputs. All 8 source heads and 1499 distinct Git blobs were read and hash-checked. Fourteen formal stage before/after maps match exactly.

## Meaningful failures and closure

- d20ba00f: actual generated-client/fetch boundary asserts full original command already exists in real fake-indexeddb DraftStore before POST. 1 FAIL; e1019363 same complete test bytes 1 PASS. This was a new feature TDD admission seam, not a claim that old canonical had an existing implemented endpoint UI defect.
- Root static candidate: a clean hidden old actor preview blocked the current actor's own child. c61da5b7 actual component/GET/DraftStore counterexample: 1 FAIL / 1 PASS. bc978839 production-only fix: same complete test bytes 2 PASS. Final 8f adds actor, workspace, dirty settings retention/explicit discard tests. Old clean preview can be replaced only by an explicit new child action; dirty old preview stays isolated until explicit local discard. Child workflow instances are keyed by workspace/actor/importId.
- Developer-only collection, Blob fixture and hidden-field test-oracle failures remain recorded in QUALIFICATIONS.md. No missing before-map or raw log is invented. They do not establish product failures.

## Final fixed gates

All use source 8f2c8845; no tracked inputs changed during any run.

| Gate | Actual terminal result | Log SHA-256 |
| --- | --- | --- |
| Four artifact tests | 27 PASS, exit 0 | 6d83cc0d5432a80ab86d4454c085cb9189a804d67d19ab8f5e62ec9ffbb9b38e |
| Full Web | 1305 PASS / 161 files, exit 0 | c93cd0454cef9d59251820d8808d2320d092041e28ca178a715d910939db7c97 |
| Strict TS | exit 0 | b9df407f06dd3350bcb5d41df640c2603d5d70f268d57fe256fe1159da11cc68 |
| Build | exit 0; existing >500k chunk advisory retained | 52058809381b785062257d2bce7ea363d949a238726033d918ab41c01128b48b |
| Spec | structural PASS, exit 0 | 66961042a78693834c23a34dc2e1a18ec15d61d1a4c6f56149b9e517969b002d |

Full Web finished 2026-10-04T16:15:44.578974Z (13.477 s). Exact commands, source maps, four captured test sources and runner binding are in the `*-fixed-02` folders. Spec explicitly retains real_provider, real_codex, product_acceptance and learning_effectiveness NOT_RUN. No backend/Python suite is borrowed or claimed for this UI-only delta.

## Limited real Chrome

Final run: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-artifact-ui-native-8f2c-run02-oct05`, exit 0 at 2026-10-04T16:18:30.236335Z. Source before/after/terminal-source maps each cover 1504 exact Git inputs. Harness, command, terminal and receipt are separate from Web tests.

The trusted fixture used existing normal HTTP owners and one explicit synthetic memory response. A real role change after that response caused failed source outcome while retaining its complete answer, then a checked local answer materializer produced the manifest. Chrome read actual manifest, three NOT_RUN notices, downloaded exact SHA bytes, persisted full original command before actual POST, actively lost the actual 202 ACK, reloaded with no automatic artifact POST, explicitly replayed the same key/full body to byte-identical full ACK and saved it, read current aggregate completed/child awaiting_approval separately from original queued ACK, entered actual ordinary Import preview_ready and source/draft GET, and displayed `Synthetic exact answer α`. No automatic commit/Review/publish occurred. Later learner state hid subject UI and actual manifest GET returned 403. Six 1440/390 screenshots were individually visually inspected: content and hashes wrap within the dialog/document, final ordinary preview shows actual rendered synthetic text.

Initial and final fixture transport counters are both 1; synthetic bootstrap count is 1. These are explicit test-peer counters, not universal external-network observations. Browser request list records browser-page API traffic; direct harness HTTP role/status calls and setup HTTP have separate assertions in harness source. Actual remote model, real CLI, tool execution, host isolation, mathematical/source/pedagogical quality, and overall M6.3 acceptance remain NOT_RUN/unestablished.

Historical 422f native exit0 remains LIMITED: its two ordinary preview screenshots still showed lazy Markdown loading, so it did not prove text rendering. The first 8f native is preserved FAIL: a weak locator matched explanatory 'completed' text while actual aggregate GET was still legitimately queued. Its original before map/log/terminal and later named supplemental source map remain intact. The next harness explicitly waits for the real readonly status and then clicks current GET, and waits for rendered text; application source/configuration/runtime budgets did not change.

## Sharing and review

Only explicitly enumerated manually reviewed source, logs, maps, receipts, harness text and six final synthetic screenshots are proposed in publication-candidates/allowlist.json. Text transformation is only `<LOCAL_HOME>` → `<LOCAL_HOME>`; PNG bytes are exact. Screenshots contain synthetic actor/object IDs and synthetic idempotency command identifiers, not authentication credentials. Private cookie fixture, data/DB, provider secret storage, browser profile, download/cache/tmp and original opaque data are excluded. No remote publication performed. Original failure logs remain private originals; explicitly safe raw failures may have home-only candidate copies, always with qualifications.

Root owns independent review and integration. This report does not claim its review result in advance.
