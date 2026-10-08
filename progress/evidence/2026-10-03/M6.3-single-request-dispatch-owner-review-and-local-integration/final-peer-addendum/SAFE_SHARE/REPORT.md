# Independent static addendum: 351f7afa

Fixed `351f7afa5bd1554696f4a8e3cb1683c24f98deac` versus reviewed `922d498b52b2b792414394a18c9b1d248654f2ee`. Sole v3.0.15 digest is unchanged. This is one peer, Standards and Spec axes; no execution.

The entire delta is one integration-test file (85 additions, 3 deletions). All 17 reviewed production files and 4 generated files are byte-identical; no other non-progress path changes. Original 922 static packet stays unchanged.

No confirmed new Standards or Spec finding. The original dispatch fixture is extracted into `make_dispatch_case` while retaining its transport setup and cleanup. New cases require logout after the request to preserve original output/usage under failed Policy status, allow a new author to read history while rejecting takeover/start, reject real open_book queued dispatch before transport, and reject six damaged owner graphs on current/control/result/start-replay reads with zero mutation. The damage cases address Provider tail, Codex tail, Job event tail, Run snapshot, active lease and context. These assertions add boundaries; they do not remove the existing start/recovery/rollback assertions.

This addendum verifies only source differences and their intended assertions. The author formal gate was RUNNING when the review was requested; no result is adopted here, and no tests, application, database, CLI, model, network or system probes were run. No full-M6.3, host-sandbox or real-upstream acceptance is implied.
