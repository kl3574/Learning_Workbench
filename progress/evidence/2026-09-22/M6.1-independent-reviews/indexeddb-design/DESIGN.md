# Bounded design advice: revocation during private IndexedDB persistence

Recommendation: use the final PUT request's synchronous success callback to check the original access guard and immediately call `transaction.commit()`. Treat a successful call as the **local authorization admission point**, not persistence success. Only transaction `complete` can settle `DraftStore.save` as saved. This is a proposed local implementation boundary, not a claim that IndexedDB atomically checks server Policy.

## Primary specification basis

IndexedDB makes request success handlers active transaction contexts. `commit()` requires active state and synchronously switches to committing before storage work proceeds. The API `abort()` rejects committing/finished transactions with `InvalidStateError`. Storage failure may still abort a requested commit; successful storage precedes the queued complete event. Consequently, absence of `oncomplete` does not establish rollback capability. The broad lifecycle description is insufficient to override these method steps. [W3C IDBTransaction methods](https://www.w3.org/TR/IndexedDB-3/#dom-idbtransaction-abort), [commit method](https://www.w3.org/TR/IndexedDB-3/#dom-idbtransaction-commit), [commit algorithm](https://www.w3.org/TR/IndexedDB-3/#commit-transaction), [request success algorithm](https://www.w3.org/TR/IndexedDB-3/#fire-a-success-event).

## Present seam

`useAuthoring.ts:145-146` checks current permission then awaits `persistAuthoringCommand`. That helper awaits a separate `store.load` at `authoringCommands.ts:62`, may return an existing ACK at line 67, or invokes `save` at line 69. `DraftStore.ts:102` awaits opening storage, then its readwrite GET callback issues PUT at lines 124/129. None of these asynchronous boundaries currently carries the access guard. The generic store already waits for transaction completion, retains CAS conflicts, and broadcasts only workspace identity; preserve those properties.

## Minimum compatible interface and algorithm

Add an optional final argument to `DraftStore.save`, after the existing resolved conflict IDs: a readonly guard with `allowed: () => boolean` and `signal: AbortSignal`. Keep the existing return union and persisted record/ACK formats. Update the exported save wrapper as well. Unguarded callers, especially safe cancellation, retain the original behavior.

For guarded saves:

1. Check both the signal and the synchronous, side-effect-free predicate before/after opening the database and immediately before creating the readwrite transaction. A false predicate or thrown predicate stops the operation. Do not serialize the predicate/signal into IndexedDB.
2. Install terminal handlers and the abort listener before queuing work, and immediately recheck an already-aborted signal. Before admission, the listener attempts `transaction.abort()`. Set an in-memory scope-cancellation reason, but settle only from the actual abort event. If abort throws `InvalidStateError`, do not assert rollback; await the real terminal event. Prevent uncaught listener exceptions.
3. Recheck at GET success before issuing either normal PUT or conflict-preserving PUT. Both branches can contain private text and must share the same guard.
4. Retain the returned PUT request. In its success handler, recheck the signal/predicate and immediately request commit in the same synchronous callback, without `await`, timers, queued microtasks or user callbacks between the final check and commit. Mark the operation admitted only if commit returns successfully. No further request or private mutation is permitted in this transaction. If the guarded feature requires explicit commit, detect unsupported commit before PUT and fail without a write; do not silently weaken its boundary. No keepalive loop is needed.
5. After commit admission, later revocation cannot cancel that transaction through the API. Ignore that signal for rollback purposes and continue waiting for complete/abort; a genuine storage abort still rejects. Complete resolves the real saved/conflict result and may emit the existing workspace-only notification. Do not recheck at complete and then misreport that a committed write was cancelled. Do not delete or overwrite the already admitted ACK.
6. Remove the listener and release handler references on every terminal/setup-error path. Authorization cancellation should remain an in-memory cancellation error, distinct from a server rejection or an assertion that a possibly committed write was rolled back.

`commit()` makes this boundary explicit and testable. It does not convert the existing ACK into a new server-approved state, change idempotency, guarantee disk flush beyond existing durability settings, or erase the possibility of storage failure.

## Authoring integration

Pass one operation-scoped guard through all iterations of `persistAuthoringCommand`, checking at entry, after each load, before the existing-record early return, before save and before processing/returning a saved private result. A post-save guard failure blocks delivery or another retry; it does not undo an admitted commit. Preserve the original CAS/readback algorithm and four-attempt cap.

Supply this guard for all three non-cancel persistence paths in `useAuthoring.ts`: initial command (132), ACK (146), and rejection (155). The predicate must use current scope, current session generation and original operation identity; a captured `academic=true` is insufficient. Abort the operation's signal permanently on observed revocation, owner/workspace replacement, unmount or invalidation. Session-generation changes should be observed synchronously by the predicate, not solely after an eventual React effect.

The current catch path persists a 409 rejection before `fail()` invalidates academic access. For `POLICY_DENIED`/`ASSESSMENT_ACTIVE`/protected-answer errors, mark the subject scope invalid and abort it before attempting any further private persistence. Otherwise a newly added predicate can still read true after the denial has already been observed. Safe cancel remains unguarded by academic permission.

If revocation wins before admission of an ACK update, the already committed original command/key/body remains unchanged with unknown ACK; later explicit replay uses that same key/body. If commit admission wins first, retain the legitimate ACK but hide it from the revoked UI and stop subsequent subject operations. This does not promise instantaneous synchronization with another tab or an unobserved server Policy change.

## Required focused test boundaries

| Controlled boundary | Expected evidence |
|---|---|
| Revoke while helper load is suspended | No subsequent private save; no private early return; original command remains |
| Revoke while database open is pending, or before GET success | No private PUT/commit; unchanged existing record and conflicts |
| Revoke after PUT request is queued but before final success/admission | Actual abort, unchanged database after a new reader, no save notification |
| Predicate changes without signal delivery before final PUT success | Final predicate check refuses admission |
| Revoke in both saved and CAS-conflict branches before admission | No ACK text introduced in record or conflict array |
| Final guard succeeds, commit returns, then revoke before complete | Commit outcome remains genuine; saved ACK survives if complete fires; no delete, stale UI or false rollback claim |
| Commit storage failure | Reject on actual abort; never saved/notify on PUT success alone |
| Existing committed ACK / original-key replay / safe cancel | No deletion or altered key/body/ACK; control path remains usable |
| Cleanup and repeat invalidation | No leaked listener, duplicate settlement, uncaught abort error or new request |

Use request/event barriers rather than arbitrary sleeps. A post-commit/pre-complete test may wrap the real commit call, return normally, then queue revocation in a microtask and record event ordering. A fake implementation that allows rollback after commit is insufficient evidence for this boundary; inspect the test engine's behavior and retain a native browser check for later authorized verification. Do not synthesize a reentrant revocation inside the native commit call and mistake that impossible JavaScript callback ordering for the production contract. Keep full `DraftStore` CAS/quota/notification tests and cover the hook with the exact original lost-ACK and source identity invariants.

This task performed source reading and primary specification lookup only: no source/test edits, IndexedDB execution, browser/native test, vendor call, local ACK migration or protocol change.
