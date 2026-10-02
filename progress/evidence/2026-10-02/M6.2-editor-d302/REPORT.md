# M6.2 editor combination gates at d302c07

Source: `d302c075a85c45dc11ff8a4b6a539ef8baed48f3`, approved specification v3.0.9. Scope is the editor read/conflict/recovery slice, not complete M6.2 acceptance.

- Web: 562 tests in 94 files passed.
- Strict TypeScript/lint: passed.
- Production build: passed, 766 modules; original chunk-size warning retained.
- Native: one actual synthetic SQLite/HTTP/IndexedDB browser scenario passed (14.0s test, 14.4s runner report). No retries. Covers 200/412 competing pages, explicit three-way resolution, same-page original-key replay after actual commit/lost response, browser/API restart, IDB write abort, role denial and guarded memory recovery.

All four stages captured 1092 tracked non-progress files before and after. The eight identical input lists are stored once as `inputs.json`; every member was independently checked against the exact Git tree. This does not capture external dependencies, OS, browser executable or runtime state. The native config and stage runner are preserved with exact private path replacements; receipts retain raw log/runner hashes and the manifest maps raw to public bytes. No log lines were removed.

Both native screenshots (1440 and 390 widths) were visually inspected. They depict the three-way conflict checkpoint; at 390 the panes are stacked and require vertical scrolling. The screenshots do not depict later role/memory recovery. The flow JSON is emitted by the real test, not an independent network trace. No server log or browser trace was collected. Fixture text, command/draft IDs and hashes are synthetic, from the local test runtime; no user learning content or credential is included.

Unknown-ACK replay across a new page/access generation remains blocked pending an approved actor-continuity contract. Real DeepSeek and content/teaching quality are NOT_RUN; no provider request is part of these gates. Fresh full Python and final integrated backend acceptance remain pending. The earlier full Python failure is preserved in `../M6.2-resume`.
