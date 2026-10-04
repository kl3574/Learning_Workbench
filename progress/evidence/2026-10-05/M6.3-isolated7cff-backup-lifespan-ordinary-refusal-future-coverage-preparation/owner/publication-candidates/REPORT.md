# M6.3 synthetic Codex backup lifespan — bounded test candidate

Fixed head `7cffb5305321c53258f5c5601a4ca7c29b5b4801`, immediate parent `816cb38b7285d14fdbf5d00fcdecdced5e1b517d`, base `942fc533ca48e1a561199fb992d80e76622948c1`. Exactly one new integration file, `tests/integration/test_backup_codex_lifespan.py` (213 lines), and no production, spec, dependency, configuration or old-test changes. The unique complete PRODUCT_DESIGN v3.0.15 file hashes to `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`; the relevant authority is §20.17.7 historical actor/reference retention, authentication noninheritance, nonexecutable old permission and no execution from restored GETs. M7 remains unaccepted and its dependency gates are not unlocked.

## Actual results and corrected test expectation

| Source / stage | Actual result | UTC finish | Raw log SHA256 |
| --- | --- | --- | --- |
| 816cb38b / focused-01 | 2 FAIL, exit 1; original overstrong terminal/convergence expectation | 2026-10-04T19:15:04.869379Z | c5b7da3a7a42a962c006ef103cb1145a057c19e87435590667f4fb7a2ee29efe |
| 816cb38b / static-01 | new-file Ruff exit 0 | 2026-10-04T19:17:23.972916Z | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| 816cb38b / diff-01 | diff --check exit 0 | 2026-10-04T19:17:23.940166Z | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| 7cffb530 / focused-02 | corrected bounded contract: 2 PASS, exit 0 | 2026-10-04T19:20:45.259858Z | 4589358cb3f614cdaf0315359c408bb3f459ba7e0bd9d15d984a59899a7f49fe |
| 7cffb530 / static-02 | new-file Ruff exit 0 | 2026-10-04T19:21:06.820439Z | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| 7cffb530 / diff-02 | diff --check exit 0 | 2026-10-04T19:21:06.761426Z | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| 7cffb530 / related-01 | 7 PASS, exit 0; new two cases plus existing four queued permission-loss cases and one default no-adapter case | 2026-10-04T19:21:55.963304Z | e08974d392687f886f0692cc5a05a527fc33663112094bf9058fb8e78233b5dd |

Focused command: `uv run --frozen --no-sync python -m pytest tests/integration/test_backup_codex_lifespan.py -q --basetemp <unique-private-stage-directory>`. Related command names the same file plus `test_codex_turn_dispatch_http.py::test_queued_permission_loss_converges_without_actual_request` and `::test_current_production_has_no_dispatch_adapter_and_never_consumes`. Exact commands, UTC timestamps, durations, runner hash and source hashes are in each original receipt. The existing dependency deprecation warnings remain. No install occurred; the isolated tree uses the existing read-only dependency symlink.

**The original two failures and later passes have different test semantics. This is a test expectation correction, not a production fix or same-test RED→GREEN.** The first test demanded a new failed terminal after startup. It actually entered the real lifespan and observed the real worker method raise `PROVIDER_BACKUP_DISABLED`. It failed before the fresh-actor and zero-action assertions; those original-stage assertions remain NOT_RUN. Root's read-only review required the correction: §20.17.7 does not require this permanently disabled backup's unstarted queue item to become failed, and an observer must not fabricate such a terminal. Both original source and complete original failure log remain immutable/private. Failure contents can include fixture representations, so only the raw SHA, original source and bounded summary are candidates.

## The actual production path, without a production change

- `codex_turn_worker.py:94–109` catches ApiError in its real loop, sets last_error_code, then waits on its stop Event for 0.25 seconds before another iteration. A direct run_once exception does not imply that this worker thread exits.
- `recover():323–329` selects only records with a persisted started fact and no finish; this queued item is not selected. The actual startup recovery count was zero.
- `provider_codex_consents.py:227` reloads the original grant actor. `security.py:103–106` denies a revoked/non-author actor. `_claim():186–189` takes the existing safe-refusal path and attempts `_terminal`.
- `_terminal():155–159` updates Jobs and records the Provider terminal within one transaction. `provider_codex_repository.py:211–212` calls `ProviderRepository.writable`, whose backup projection gate at `provider_repository.py:81–85` rejects writes with PROVIDER_BACKUP_DISABLED. `database.py:51–59` rolls the entire transaction back.

This static chain explains the observed method error and unchanged queue. It does not declare a new requirement to permit backup writes. A separate read-only post-failure projection of the two original private copied databases confirmed queued/r2, null lease owner/deadline, and only proposed/granted/queued Provider Codex events. It did not restart the application or measure execution counters. An initial ad hoc read-only query used an incorrect column name and failed; the corrected query used the actual `record_json` schema. That local query error is not a product failure and was not used as evidence of behavior.

## Fixed test behavior actually reached

Both cases create genuine source owner history through the existing synthetic HTTP fixture, explicitly queue one turn, and call the actual existing `create_backup` function. They verify every archive-listed payload's size/hash, membership, session authentication-disabled/consent-disabled declarations and original source preservation, then manually expand only the checked database/blob payloads into a separate private directory. This does not exercise the M7 restore-preview/restore-commit workflow. The previous 942fc tests and their CLI/read-only results are unchanged and remain separately qualified.

The restored app uses a fresh literal ControlledRuntime. One case leaves the production Codex proof/executor registration empty; the other explicitly supplies the existing synthetic proof plus a memory executor whose transport is a forbidden-call sentinel. The test enters `with TestClient(app)` and lets the real lifespan initialize/recover/start its original workers. It wraps only the public run_once method to observe and re-raise each exception unchanged. The real loop handles every error; no method is manually invoked, no terminal or event is inserted, and no exception is suppressed.

A bounded Event waits for at least two real original-method refusals. The second invocation observes the previous loop's error code. The actual focused run recorded 4 and 5 refusals respectively; the related run recorded 4 and 4. Counts are observations, not exact timing requirements. In each case the real Codex worker thread was alive while the context was active and was no longer alive after normal context shutdown. The original 0.25-second worker wait and all production behavior remain unchanged.

Reached assertions verify:

- Original Codex owner tables, Jobs, Run and event-table hashes retain the copied queued facts. The original complete safe control and JobSnapshot are unchanged: queued/r2/not_started/no start, active session turn/r4. No new terminal is invented.
- Old cookie returns401. Fresh bootstrap creates a different learner actor. Safe session/turn/Job reads remain usable; academic result read returns403. An explicit role-switch command then enables author history reads.
- Original consent summary and actor, unstarted dispatch/zero consumed calls/null usage/outcome, empty result and all three NOT_RUN quality fields are retained. The checked owner read validates the original complete start ACK and grant ACK independently of current GET projections.
- Both original and new keys cannot transfer the old actor's turn-start/grant bodies:403 POLICY_DENIED. GET/rejected-command blocks compare every table's hash before/after and remain zero-write, while actual bootstrap/role writes lie outside these baselines.
- Finally records are actually written after the context closes, including counts even on assertion failure. In all four successful case executions, Codex model, ordinary Provider stream, literal tool, subprocess.Popen and fresh bootstrap execution sentinels were each zero; source synthetic model calls were zero. These are the explicitly observed/blocked application seams, not an independent all-network/all-OS monitor. Source synthetic bootstrap initialization occurs only in its explicit controlled fixture and is not a real Codex CLI call.

## Open evidence and scope limits

**OPEN_EVIDENCE:** the restored turn remains queued and the session retains an active turn while the backup is permanently dispatch-disabled. General background convergence, release for new scheduling and any new restored-workspace task are not accepted here. No policy/lease/terminal behavior was loosened to make the test pass. Product restore-preview/commit, M7 rollback/recovery, GenericApproval and artifact-import backup histories, real model/tool/CLI execution and whole-platform acceptance remain NOT_RUN. No actual API key, remote model, CLI network or host-security probe was used. No canonical edit, merge, staging or push occurred.

## Source and safe evidence binding

Three complete immutable Git maps bind base→816→7cff: 4,571 path/object records, 1,506 distinct blob bytes. Seven stages retain all 14 original before/after maps, totaling21,336 bindings. Every stage matches its fixed source and has before=after; all final1,524 engineering inputs match the live clean tree. All1,523 base inputs remain byte-identical, with only the new integration file added. Runner SHA256 is `77bb6a537d05583f88fafba3c3f8b5387fac1fc2931189f6aac596f7fe44c76d`; final new-file SHA256 is `58c31d9e75af9be61ac1fb42ef8fbdc631a0b26553f54026836102e54ce702ed`.

The explicit publication candidate allowlist includes reviewed test source, both patches, fixed Git maps, commands/receipts/maps, successful logs, bounded original-failure summary and four payload-free finally observations. Only literal `${HOME}`→`${HOME}` text substitution is permitted, with both byte hashes recorded. No recursive inclusion of private runtime files occurs. Original failed fixture-repr log, databases, backups/ZIPs, key storage, caches and runtime directories remain private. Independent fixed-delta review is pending; this owner report itself grants no publication or merge.
