# Bounded Reader metadata latency readback

The preserved 73d PR browser failure is a real loading-stage failure: at 5,402 ms after navigation, the exact r2 tab and loading text remained present, there was no alert and no Reader article. Session GETs returned quickly. Lesson request 9 and outline request 7, issued at approximately 1,663 ms, had no observed response/finish/failure before capture. These client events cannot distinguish handler admission, dependency/threadpool delay, transaction wait, service computation or response transport. They do not prove a CPU bottleneck or deadlock.

Static owner paths differ. The lesson endpoint loads and checks one Lesson metadata revision. It does not read block bodies or provenance. The outline expands the exact course graph, then revalidates lesson/block references for reading-state projection. Both enter an immediate SQLite transaction and check Policy within it. Those facts establish possible serialization, not the actual original delay.

A new private synthetic database imported the actual native history archive through ImportService.stage, the real ImportWorker parser/preview, and explicit commit. The resulting job is completed and import committed, with 7 objects, 14 revisions, 8 frozen block-provenance rows and 1 import job. No user/CI database, original private files, credentials or provider operation was used. The source inventory contains 785 tracked non-progress files, unchanged before/after and byte-equal to the current c83b1d0 commit.

Final measured call durations (one observation each; instrumented developer machine, not a throughput benchmark):

| Operation | Total ms | BEGIN wait ms |
| --- | ---: | ---: |
| Serial lesson | 1.882 | 0.0064 |
| Serial outline | 3.447 | 0.0062 |
| Concurrent lesson | 3.913 | 0.0114 |
| Concurrent outline | 3.811 | 0.0047 |
| Lesson during actual worker tick | 8.524 | 0.0092 |
| Outline during actual worker tick | 10.491 | 0.0755 |
| Actual post-import worker tick | 54.713 | seven acquisitions, each below 0.011 |

The isolated outline performs 13 load/decode calls and 36 metadata hashes; cumulative decode time was 0.739 ms and hashing 0.561 ms. This repeated validation is measurable but not a seconds-scale hotspot in the matched small fixture. The worker executed actual recovery/recommendation/retrieval/grading/import maintenance, including a changed recommendation projection. Its longest observed transaction held approximately 31.45 ms before commit.

The overlap control has a material limit: readers were launched after observing the worker's first real BEGIN, but both completed before its longer recommendation transaction began. The worker was never paused waiting for them and no delay was inserted. This proves overlap with the maintenance call, not reader waiting on that recommendation transaction, and cannot falsify lock contention under other schedules. Python 3.12's single enabled cProfile captured other reader threads during the worker overlap; its function totals must not be attributed entirely to the worker. Per-call durations and SQL/BEGIN timing use explicit thread-local labels and one monotonic clock.

Two diagnosis harness errors remain raw: the initial script basename shadowed stdlib profile before any database work; the next version attempted simultaneous cProfile instances and stopped after successful serial measurements. The final harness corrects those observation mechanics without changing application services, fixtures, policy or endpoint budgets. Neither harness error is a product RED.

No second-level service delay was reproduced. These results do not justify removing integrity/Policy checks, changing read transaction semantics or raising the original five-second assertion. The original CI cause remains unresolved. A subsequent original-CI run would need safe server-side arrival/dependency/BEGIN/handler-finish timing to distinguish queueing from owner-service work; that instrumentation is a separate decision, not implemented here. No browser or complete test suite was run by this diagnostic task.
