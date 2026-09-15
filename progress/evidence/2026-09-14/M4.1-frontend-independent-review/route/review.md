# RouteEditor known access-change boundary: independent recheck

Only the two frontend-owned permanent tests and the related RouteEditor delta were reviewed. No repository files were edited, no native browser or HTTP server was started, and no default ports were used. This receipt is separate from the earlier Profile ownership review.

## Verified inputs and result

The saved original RouteEditor bytes match the pre-red source hash 27e8d1b9c6ac3e4a257c6accb93a4cb11a7349a2bb35c383415a47e048932226. The current two-test file matches the pre-red recorded hash ee9e8a963ab5f91569f11c46a84633d6898e501f0047473bb65b09053b813c69 exactly. The owner confirmed this test file was unchanged between the supplied red and green executions. The original red log contains two failed tests at the disabled recovery/edit assertions; the owner's subsequent green log contains two passed tests. Those two original executions were read, not rerun by this reviewer, and their logs alone do not independently capture process exit codes.

The reviewer independently ran `./node_modules/.bin/vitest run src/features/routes/RouteEditor.test.tsx` from `apps/web`: exit 0, two passed tests, 882 ms Vitest duration. All eight recorded source/config/spec byte hashes were unchanged before and after the run. The actual RouteEditor hash was 72d863896b5e774cb45a51053bf5ff48a920e77f5a090f6f0d7a11f1de445ed6.

## Minimal delta inspected

1. Changing access identity or paused state advances the operation epoch and releases the abandoned operation's busy state. This makes the original recovery/edit controls usable again.
2. A late successful receipt only updates the durable journal and editor when the live workspace and command ID still match that original command. The second unchanged test asserts the newer B text remains visible and its complete candidate bytes remain in the actual DraftStore record or retained conflicts.
3. Restore, submit, 412 reads, errors, and finally handlers additionally require the captured epoch to remain current. An old finally cannot clear a new operation's busy state following a policy pause/resume even when the workspace/access identity is unchanged. This particular newer-operation-finally property was checked statically; neither of the two tests separately starts a second in-flight request to assert it dynamically.
4. The paused render still hides the editor. A receipt for the same command may acknowledge its local journal while paused; it is not a new network authorization and does not send a replacement command.

## Limits

These are React tests using the real application DraftStore implementation backed by fake-indexeddb, controlled mocked typed transport, and mocked empty route choices. They do not establish real browser disk persistence, HTTP authorization, API CAS or idempotency, full route workflow acceptance, or M4.1 completion. Both original red tests stop at the original permanently-busy behavior, so the red log alone does not separately prove a late-ACK-overwrite failure. No additional probes were added and no new finding remained in this bounded delta.

An initial reviewer receipt-setup command failed before Vitest started because the system Python does not expose datetime.UTC. The setup was corrected to timezone.utc; the setup failure is recorded separately and is not a product or test failure. The existing Profile independent-review artifacts were left unchanged. Later Profile edits reported by the frontend are outside this RouteEditor receipt.
