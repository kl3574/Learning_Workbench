# Independent review — M6.2 review storage

Sole specification: PRODUCT_DESIGN.md 3.0.7; exact SHA is in source-pins.json. Applicable rules reviewed: owner boundaries, Job/Draft state and atomic history, exact candidate approval identity, quality levels, forward migrations and online backups, explicit human review endpoint, ReviewReceipt, baseline SQL JSON/permission caveat and M7 backup boundary. The storage candidate and ADR are engineering choices, not additional product specifications.

Initial reviewed source: `4b0296f3334d580f22fd95a9cede5c8edfcf4a77`. Independently rechecked fix: `e0b30f077cc760b8579f81939182f602cd5e992b`. Both are isolated clean detached worktrees. Four changed files match their actual Git blobs; 0001, 0016 and packages/contracts are unchanged from the authorized base `16f4ae1355c4398a6b419b2fa883ec5211624c3d`. The test runner records all 10,113 tracked-file hashes before/after each invocation and verifies no changes; generated caches are outside this inventory.

## Standards

No open finding. The change is a forward owner storage migration with real SQLite tests. It changes no core contract or applied predecessor migration. SQL fixtures are explicitly synthetic and are not described as application owner, human authority, machine execution or publication proof. No repository/worker/HTTP/Provider implementation is claimed. No production data, system permissions, timeout or source files were changed by this review.

## Spec

One initial relational finding is resolved in the reviewed fix. In original 0017 lines 104–117, command event existence was checked only by a BEFORE INSERT trigger. Existing job_events has no ordinary DELETE/UPDATE guard. A retained cancel command therefore survived deletion or renumbering of either referenced event while PRAGMA foreign_key_check returned no error. A create command could also name initial Job revision 1 after that event had been deleted. This was a gap in persistent command revision identity; it was not evidence that a protected production API had accepted a forged human review.

Independent actual SQLite probes at 4b0296f reproduced all five cases: cancel basis=1/result=2, with no create command sharing its event references, then separately DELETE and UPDATE each endpoint; plus create with missing initial event. Original observations and logs are preserved, never relabeled PASS. The fixed migration adds generated per-kind revision columns and composite foreign keys to Jobs events and retained Review revisions. At e0b30f0 the same five isolated probes all rejected the orphaning operations. Both event rows remained and foreign_key_check stayed empty.

No other open finding within this storage slice. Review Job identity binds actual Jobs id/workspace/draft_review kind and the complete immutable catalog source-kind and candidate identity. Revision predecessors bind the same review, adjacent number and exact retained receipt hash. Artifact bindings use actual artifact id/workspace/blob identity; the REPLACE guard covers ordinal primary key and separate artifact uniqueness even with recursive triggers disabled. Command routes bind the actual object, original actor/key/workspace remain append-only, and create/cancel remain representable before any ReviewReceipt exists. SQL validity and opaque owner labels do not authenticate current permissions, canonical hash correctness, event meaning, ACK shape or human decisions; those remain explicit future checked-port responsibilities.

## Actual verification

- e0b30f0: 99 committed storage/migration tests passed in 2.44 seconds; raw pytest output and command receipt retained.
- Independent relation probes: five original accepted orphans; five fixed rejections.
- Nonempty retained review history plus create/cancel commands survived a real online snapshot followed by NULL reviewer_session_id and DELETE local_sessions on the isolated copy; original receipt bytes/history/commands were unchanged and the live synthetic source still retained its session reference. This checks copy sanitation compatibility, not M7 restore acceptance.
- Committed migration tests independently rerun cover legacy receipt/Job byte preservation, empty newly added tables, 16→17 online backup, schema/index/migration-record rollback after deliberate invalid SQL, and the actual backup script's legacy reviewer cleanup.
- Source and test boundaries did not change during verification. SQLite runtime reported 3.53.1.

Quality application repository/worker/HTTP, real human approval, provider execution, numeric execution, publication and M7 restore acceptance were not run or inferred from this schema acceptance. Full-suite/old-related regression results executed by the implementing parent are not represented as this reviewer's own results. This report does not mark M6.2 complete.

## Final test-only follow-up

Read-only review of `4bf176de1cdf0a76cdf0fa965027ec3a5367551f` against e0b30f0 confirms exactly one changed test file; migration, ADR and migration-test bytes are identical. The permanent relational mutation case now separately targets create event 1, cancel basis 1 and cancel result 2, each with DELETE and UPDATE. The cancel fixture creates only its own command, with distinct basis/result, so the two foreign keys cannot cover for one another. UPDATE moves the selected sequence by 10, avoiding a primary-key collision with the other retained event. No additional finding. The independent 99-case test receipt remains attributed to e0b30f0; the parent's final 101-case run is not claimed as independently executed here. Old-related suites were not rerun by this reviewer.
