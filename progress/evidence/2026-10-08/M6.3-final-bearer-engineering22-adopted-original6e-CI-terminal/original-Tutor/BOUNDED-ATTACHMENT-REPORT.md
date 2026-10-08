# Original push Tutor attachment — bounded observation

Original push `37732562289`, attempt 1, browser job `113164785800`, source `6e6748b758436b5c71ff9b63282b583190038a0b`: **FAIL retained; cause UNKNOWN**. Reviewer tests NOT_RUN.

The five-second completion assertion froze at Node 19448.466778 ms. The last matched DOM delivery before this boundary was queued, seq 5/revision 4 (Node 19274.410294 ms). The frozen 26 browser deliveries and eight DOM projections contain no completed delivery. Reported omitted/invalid deliveries are zero; absence from the captured ring still does not prove absence in the entire system.

The failure-triggered read started at Node 19448.484942 ms and ended at 19643.706396 ms. It returned completed, seq 6/revision 6, consent/answer/provider-receipt presence, and one received/validated fixture request. This observation follows the assertion failure. API source_ns and browser source_ms have independent epochs and cannot be subtracted from the Node assertion clock. The attachment cannot establish a pre-deadline provider/database commit or a unique UI/backend cause.

The error-context locates the unchanged `tutorCompletion.ts:5` predicate and the original 5000 ms budget. Assertions, retries, original CI, source, and runtime were not modified or rerun.

The exact 304122-byte original ZIP (SHA `fe11691d7f045602e38e5c5ea0777f0f18b29cd9960e190802ebbb7d252a5bd4`) contains a PNG. The PNG was not extracted/viewed. Only the target Tutor diagnostic JSON and error-context were extracted; artifact metadata and ZIP each have one actual GET exit0 receipt. The initial whitelist missed the canonical JSON basename; the second extraction used the same retained ZIP without network.
