# Submit acknowledgement: independent static review

**Final scoped conclusion: no blocking defect found.** The three pinned test files implement a real submission-order synchronization and a regression that retains the server's unsubmitted-409 contract. Two initial Promise failure-path findings were reported and are now closed by inspected source changes. This review ran no tests, used no shared ports and changed no repository file.

Authority: PRODUCT_DESIGN 3.0.7, SHA `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`, lines 1287/1289. Submit returns 202 only after persisting submitted and enqueueing grading; result before submission is 409, and pending grading may return 202. Existing actual owner code matches this division (`assessment.py:271–294`, `grading.py:25–29`, `assessment_http.py:47–61`).

## Final behavior and assertion strength

- `assessmentTestData.ts:22–36` installs the exact POST/path response observer before UI actions. Promise.all observes both response and click failures immediately. The helper requires actual HTTP 202, the same attempt id, and submitted status before returning. A DOM click completing is no longer treated as a server acknowledgement. It does not poll away 409, fabricate a response, or convert API errors into success.
- `grading-recovery.spec.ts:77` replaces only its two submit clicks with the helper. I reconstructed the exact Git baseline by reversing that replacement and the new import; the result is byte-identical. Therefore the original 120000 ms case limit, original result helper, failed regrade setup, original private-answer restoration, distinct commands, later grading revision, old responses, failed Job retention and page-error assertions remain unchanged. No assertion timeout was increased or result status widened.
- `assessment-submit.spec.ts` runs RestartRuntime's real production API composition in an owned temporary data directory and uses the actual import, assessment creation, HTTP reads and grading worker. Its route only holds the exact outgoing submit POST and later calls route.continue; it never fulfills a forged response. APIRequestContext reads remain real server requests, allowing observation while the page's submit is held.
- Before releasing that request, the test requires 409 **ATTEMPT_NOT_SUBMITTED**, an active unchanged-revision attempt and no acknowledged helper result. After release it awaits the checked 202 ACK, requires a newer revision and polls for the real first needs_review grading result with null scores. Only 202 is treated as pending; a post-ACK 409 still fails the 200 assertion. Original response values must remain identical. The emitted JSON is downstream of these assertions and makes no mathematical-approval claim.

This regression establishes the deliberately held outgoing-request boundary. It does not separately prove a lost response after server commit, concurrent user submissions, or every possible network failure. The helper's TypeScript return annotation is not claimed as full runtime DTO validation; the specific acknowledgement fields needed for this synchronization are explicitly asserted.

## Promise and route cleanup review

The first inspected helper could abandon its response Promise when an earlier click threw. Final Promise.all now attaches a rejection handler to both branches before either click can fail. The initial regression awaited only the interception gate, so a pre-POST helper failure could leave it waiting until the overall test timeout. Final Promise.race now propagates that failure and rejects completion without the expected gate. These were failure-reporting and cleanup concerns, not observed false passes; neither is left open in the final patch.

The regression keeps a rejection handler on submitting while making the pre-ACK observations, but still awaits the original submitting Promise after release, so rejection is not converted to a passing result. A race branch also handles its later settlement. The route handler resolves its completion Promise in finally, including route.continue errors. Outer finally releases the gate, joins the encountered route continuation and closes the owned runtime/context. No route remains installed on a reused shared browser. This review does not claim an executed fault-injection test of every teardown branch.

## Existing controlled evidence inspected

| Cache stage | Actual recorded result | Bounded interpretation |
| --- | --- | --- |
| 01-controlled-red | Exit 1, one failure | Real original case with submit held; first result 409 ATTEMPT_NOT_SUBMITTED. |
| 02-controlled-red | Exit 1, one failure | A second recorded controlled occurrence of that same boundary. |
| 03-minimized-red | Exit 1, one failure | Reduced case, same actual unsubmitted error. |
| 04-minimized-green | Exit 0, one pass | Reduced case; submit 202 observed before first result GET (202 pending). |
| 05-original-controlled-green | Exit 0, one pass | Full original controlled case reaches its recovery assertions after ACK ordering. |

Each stored log SHA matches its actual receipt. Each stage's two stored 946-entry source manifests are byte-identical; five pairs do not imply 4730 distinct source files or a broader acceptance matrix. Exact receipts, logs, source variants, manifest pairs and submission-order observations have 30 hash pins in evidence-pins.json. No private database, browser profile, original secret or session state was read or copied. These five executions used the earlier controlled variants, not an independent run of the final extracted helper/new regression. Root's later final focused run is separate evidence and is not predeclared successful here.

Source-before.json retains the initial inspection pins. During review, the helper and new regression actually changed to address the two findings; source-final.json and final-source/ retain the inspected final bytes. The grading-recovery file stayed unchanged during that interval. The report does not rewrite that interval as source-unchanged.

The original CI grading 409 lacked an error body, so this demonstrated local mechanism does **not** prove that CI failed for the same reason. The separate Tutor timeout remains outside this fix. No claim is made that CI, Tutor, M6.1, M5.4 or M6.2 is complete.
