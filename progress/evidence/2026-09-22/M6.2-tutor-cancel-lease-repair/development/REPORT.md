# M6.2 integration gate: Tutor cancellation lease assertion

## Observed failures and boundaries

The original local gate ran acb9e220deeaf1da7ee89ec6fda8bae9c21ca918: 1 FAIL, 2376 PASS, 1 environment SKIP, 664.42 s. Its only failure was tests/integration/test_tutor_runs.py::test_cancel_during_actual_http_stops_once_and_preserves_real_dispatch_facts, at the original line 359 lease equality assertion. The raw log SHA-256 is 671d59f2066c3580450f7266cf92181304ee02b42a7a915e9fb9dffff5ad640a; its receipt's byte count and SHA were checked. The before/after TTL values shown by pytest are 2026-09-22T08:23:45.495357Z and 2026-09-22T08:23:45.776621Z.

The separately fetched push CI integration log has actual checkout b70ab4aea36e84ab9ed8d8ef7f5e810ba8effd70, taken from the git log -1 --format=%H command and its following output, not from run head metadata. It reports 1 FAIL, 1041 PASS, 1 SKIP, 849.84 s, at the same test/line/assertion. Raw SHA-256 is 0b42b7f9c64f5e7adbf4a0c3a2cdacd1be2679b6111af60a544c96a2948934b9; the original GET receipt was checked. CI TTL values are 2026-09-22T08:23:49.045971Z and 2026-09-22T08:23:49.361670Z. All ten scoped test/owner/worker/database/spec files have identical actual Git bytes at these two commits.

These original logs show the failure, but contain no complete watcher scheduling trace. The controlled reproduction demonstrates a mechanism producing the exact assertion failure; it does not invent the original CI's unseen schedule. The PR browser Tutor failure and its observer/UI state are separate and were not diagnosed here. Neither original failed full gate is relabeled PASS.

## Mechanism and controlled checks

The old test read a lease in one completed read transaction, invoked service.cancel in a separate BEGIN IMMEDIATE transaction, and then compared a third read to the first. TutorWorker._watch also uses BEGIN IMMEDIATE. Before cancellation, it can legitimately renew the same owner lease without changing the Job revision. Thus the test's earlier snapshot does not isolate cancellation's effect.

The hypotheses were: (1) lawful watch renewal in the read/cancel gap; (2) cancellation itself changes the lease; (3) a watch renews after cancellation commits. The private lease_probe invokes the actual configured worker's _watch between the original test read and the real service.cancel transaction, preserving real loopback HTTP/dispatch and production bytes. It records same owner/revision, actual increasing TTL, and no cancel flag before the watch. This reliably produces the original line 359 failure. No arbitrary sleep or fabricated database mutation is used.

The permanent test obtains the actual worker claim lease, waits for the real HTTP request, and explicitly exercises a lawful watch renewal. It wraps the actual TutorRepository.cancel and takes before/after owner and TTL in that exact writer transaction. Both remain strict equality assertions. A short threading.Event gate holds actual owner finish only until a post-commit check confirms the cancel flag, exact original committed lease, _watch returning false, and unchanged owner/TTL. The gate is released in finally before awaiting worker cleanup, and all original 5-second request/worker waits are preserved. The original real dispatch, one request, one cancellation terminal, checked receipt identity, unknown remote outcome, source error fact and no second dispatch assertions remain unchanged.

Only tests/integration/test_tutor_runs.py changes. No production file, timeout, source/Provider implementation, fixture data approval, or permission behavior changes. Direct repository renew is not claimed to have a new global contract: the tested real worker path performs the existing cancel check and renew within one writer transaction.

## Actual run history

| Stage | Actual result | Scope |
| --- | --- | --- |
| 01-original-case | 1 PASS, 1.84 s | Uncontrolled original case; does not erase the two prior observed failures. |
| 02-controlled-renew-red | 1 FAIL, 1.57 s | Original production and test; actual watch scheduled in the stale-read/cancel gap; exact original equality assertion fails. |
| 03-controlled-renew-green | 1 PASS, 1.71 s | Same private probe with the corrected permanent test. |
| 04-permanent-case-green | 1 PASS, 1.83 s | Corrected case without the private plugin; permanent actual claim/watch/cancel checks. |
| 05-complete-tutor-regressions | 1 FAIL, 115 PASS, 22.29 s | Eight Tutor contract/integration files. Sole failure: the new isolated tree lacked its existing fixed Node toolchain link, so the transport TypeScript subprocess rejected the environment. |
| 06-ruff | PASS | The one changed test file. |
| 07-complete-tutor-green | 116 PASS, 22.41 s | The same eight files after linking the already-installed Node v24.21.0 and web dependencies; includes actual TypeScript/stream execution. |

Pytest reported two existing warnings on each test invocation. Counts overlap and are not added as unique coverage. The setup adjustment installed nothing and did not change system Node or source; exact existing Node and TypeScript bytes and links are pinned in toolchain-link-receipt.json. All seven commands retain actual UTC time, exit, log SHA/bytes, runner/probe bytes, scoped snapshots and all 954 before/after source entries. Each run's input bytes are unchanged within the run. The fixed test source is unchanged across stages 03–07; final Git binding is recorded separately after independent review/commit. Product tests used synthetic local HTTP only, with no user key/vendor call or shared application ports.

All raw failures and sensitive synthetic fixture logs remain private. Temporary fixture databases and runtime data are excluded from the selected evidence manifest. No publication or GitHub action occurs in this task. Future integration of this test correction still requires the parent's fixed combined gate; this targeted PASS is not a retrospective CI rerun.
