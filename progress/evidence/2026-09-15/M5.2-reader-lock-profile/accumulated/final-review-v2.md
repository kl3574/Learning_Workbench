# Accumulated synthetic database: conditional Reader lock profile

One actual RecommendationWorker check on a private copy held its immediate SQLite transaction for 169.81 ms. While that real transaction was held, the exact nativehistory r2 lesson and outline calls attempted BEGIN IMMEDIATE and waited 178.69 ms and 228.71 ms respectively. Both obtained the lock after the worker committed. This confirms a real maintenance-to-GET serialization path on the measured database. It did not reproduce the original CI's seconds-long pending requests and does not establish their unique cause.

The source is deliberately qualified. The parent identified `<SYNTHETIC_RUNTIME_CANDIDATE>` by the launcher prefix and directory mtime matching the local complete 88-native run end. Independent immutable readback found 14 exact nativehistory course/lesson/block refs matching the original r1/r2 fixture, 124 objects, 135 revisions, 21 recommendation snapshots, 27 input events, 26 jobs and no attempts. Policy allowed subject reads. However, a proposed retrieval artifact's random index ID was absent; the first diagnostic stopped at that assertion before creating a database copy or running services. A bounded scan of 31 non-Provider JSON artifacts also found no matching exact import/job/note/route ID scalar. Thus this remains a locally identified accumulated synthetic test-database candidate, not a direct random-instance-bound copy of full-suite state, and never the failing CI database or failure-time state. The initial source-readback description records the parent's identification; this qualification supersedes any stronger interpretation.

The original database was opened with `mode=ro&immutable=1` only after verifying its WAL was empty. An SQLite backup created a new private 0700 directory/0600 database for the experiment. Original database, WAL and SHM hashes, sizes and mtimes remained unchanged. No session/CSRF or Provider credential fields and no body text were selected for diagnostic output. The authorized private SQLite backup necessarily preserves the runtime database state; it is neither a sanitized database nor a public export. No blobs were copied because the measured metadata/Recommendation owner paths made zero observed BlobStore.read calls. The private database copy is not a publication payload.

One completed conditional experiment used current production services, not replaced endpoint behavior:

| Call | Elapsed ms | BEGIN wait ms |
| --- | ---: | ---: |
| Serial exact lesson r2 | 1.369 | 0.0042 |
| Serial exact outline r2 | 2.570 | 0.0047 |
| Real RecommendationWorker.run_once | 173.999 | 0.0072 |
| Lesson launched after actual worker BEGIN | 182.793 | 178.692 |
| Outline launched after actual worker BEGIN | 233.882 | 228.709 |

The worker's return was false: existing generation 27/completed 27 remained current with no failure. Even this no-new-work check verifies retained history and current inputs under the transaction. Its measured SQL trace had 520 SELECT statements. CPU profile includes calls to the full recommendation history check and content catalog; because cProfile in this Python configuration covers concurrent threads, aggregate samples are not assigned entirely to the worker. The contention result instead uses one monotonic clock, thread-local operation labels and recorded BEGIN/COMMIT boundaries. No artificial lock-hold sleep, appended input, body amplification or timeout change was used.

All 785 tracked non-progress source inputs matched before/after. The parent was concurrently running a separate complete native suite, so these are instrumented observations under shared machine load, not an idle-machine benchmark or latency guarantee. Only this service-level copy experiment ran here; no browser/HTTP/full suite and no production modifications.

The evidence supports preserving a concrete candidate explanation for future server-side diagnosis. It does not justify removing Policy or integrity checks, changing transaction semantics without a separate boundary review, or increasing the original Reader assertion timeout. With no seconds-scale local reproduction, further unbounded stress/retries stop here; resolving the original CI path needs actual server request/transaction timing.
