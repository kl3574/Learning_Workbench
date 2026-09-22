# Bounded read-only review of the IndexedDB admission correction

No blocking defect found in the three inspected files. This is static review against the prior W3C-based design, not browser acceptance or a claim that fake-indexeddb is a browser. No source/tests were edited and no test, native browser, IndexedDB experiment or vendor was started by this reviewer.

The review began at HEAD `62d3b1af344c3f43cdfe25815512fff71f79d757`. `inputs-before.json` names each exact original and corrected source SHA; `changes.patch` compares the earlier design snapshots with these corrected files. The previous design and backend review remain historical artifacts, with their own source boundaries.

## Transaction findings

- `DraftStore.ts:107-109` checks the optional guard on both sides of database open. GET success checks again (144), and both normal/CAS-conflict branches call the same guarded PUT helper (127-139, 156, 161). An already-aborted signal is also checked after listener installation (169).
- The PUT success handler performs its last synchronous guard check then calls `commit`, sets the local committing flag and removes the abort listener (132-138). It does not resolve success there. `oncomplete` alone resolves the saved/conflict result (166); genuine abort rejects (167). The existing notification follows the completed save (171).
- `abortWrite` (119-123) records its error only after `transaction.abort()` returns. If a transaction has already entered committing, `InvalidStateError` does not become a false rollback receipt. The real terminal event remains authoritative. Therefore the described test spy that invokes real commit then synchronously reenters revocation before the local flag assignment should not poison `writeError`; this is a robustness observation from the code, not an independently executed test.
- The method retains the existing revision/CAS/conflict algorithm, including preserving conflicting text and removing only explicitly resolved conflict IDs. The optional guard does not alter unguarded callers. Unsupported/throwing commit is caught while the PUT success transaction is still active and attempts abort; there is no automatic successful-write fallback.
- This matches the relevant normative boundary: script abort is unavailable in committing/finished state, commit changes state before asynchronous storage work, and complete follows successful storage. [W3C transaction methods](https://www.w3.org/TR/IndexedDB-3/#dom-idbtransaction-abort), [commit algorithm](https://www.w3.org/TR/IndexedDB-3/#commit-transaction).

## Persistence and hook boundary

`authoringCommands.ts:59-75` checks at entry and each loop, again immediately after load and before any existing-ACK early return. Every save gets the same guard. It truthfully returns an already admitted/completed save; if another CAS iteration is needed, the next loop checks again. This differs from the design's suggested post-save guard placement, but preserves the required fact boundary: the hook checks scope after saving before displaying private state, and the helper does not claim an admitted save was undone.

`useAuthoring.ts` tracks subject-write controllers, invalidates them on observed session changes and cleanup, and uses an operation-bound current-scope predicate. Initial command, ACK and non-Policy rejection writes all pass the guard. Policy denial invalidates subject access before any further private rejection persistence. Cancel operations use no academic guard. The returned UI projections and post-await gates remain current-scope dependent. No deletion, new command key, rewritten body, or changed stored ACK schema was added.

One nonblocking wording caveat was sent to root: `ACCESS_CHANGED` currently says this draft was not written. If an earlier CAS iteration already legitimately committed a conflict and the next iteration is refused, that wording could be too broad. A neutral “current save stopped; earlier committed records retained” message would avoid implying rollback without changing the code/ACK schema or deleting data. No source change was made by this reviewer.

The generic module-level exported save wrapper still has its old signature. The reviewed Authoring path calls its actual DraftStore instances directly and supplies the guard, so this does not leave a bypass in the scoped path or require broad changes to unrelated consumers.

## Verification limits

Source review verifies the control flow and explicit admission point; it does not independently establish native IndexedDB scheduling, storage durability, UI race freedom, current server Policy or cross-tab notification timing. Existing/new tests and pending native work belong to their producing agents. In particular, a commit spy's deliberately reentrant callback is a useful defensive test seam, not a production browser scheduling observation. The main required behavior is preserving the actual terminal fact and preventing subsequent unauthorized writes/display.

The package contains only source/patches and safe metadata. No browser profile, IndexedDB database, session, credentials or private runtime state is included.
