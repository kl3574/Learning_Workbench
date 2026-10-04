# Fixed 366 Codex bootstrap owner review

This is a read-only static review of 366d7b862379b3f3fa27808b04dbbd1b2694a6bc against its parent 6a1977854e4f9344206df6288e692e01626b210a and sole PRODUCT_DESIGN.md v3.0.14 §20.16. The canonical specification SHA256 is bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144, byte-identical to the fixed Git blob. Source file/blob/data hashes are in SOURCE.json.

No tests or executable probes were run. No database, credential, CLI, model, native browser, network or system probe was accessed. Service/repository/HTTP/access/main lifecycle and their ordinary support code were read from fixed Git objects. Runtime validation/execution/isolation is outside this review; only its constructor lines 150–153 were checked for the factory seam. The prior automatic interruption is not resumed and no security PASS is inferred. A separate ordinary Standards agent could not be started because the thread limit was reached: this is one reviewer's two static axes, not two independent reviewers.

## Standards

**S1 / P2 — an unregistered owner file is created before current admission or historical replay.** `application/codex_bootstrap.py:158–166` allocates an owner and enters `owners.hold()` before `_history(write=True)` and `_replay`. `infrastructure/codex_bootstrap_execution.py:21–25` creates the directory/file, and lines 37–40 close without removing that newly allocated file. Thus a valid learner POST with a schema-valid body/current CSRF, or an authorized repeat of a completed original key, creates a new unrelated owner file before rejection or historical ACK return. Repeating it creates further unregistered files. This is a static control-flow finding, not an executed filesystem test. It does not imply a second CLI start or a database write. Admission and replay should precede acquisition of a new registered execution owner, while the lock still spans permit commit through finalization. Sole spec §20.16.3–4 (lines 1441–1447, 1461) requires the current authorized original operation and one registered execution instance.

No additional hard engineering defect was established within this scope. Constructors of the service and execution owner assign references/paths only (`application/codex_bootstrap.py:33–35`, `codex_bootstrap_execution.py:13–14`); `main.py:139–145` constructs the service in factory and explicitly performs recovery in lifespan after database initialization. The inspected runtime constructor only assigns its arguments. This is not a full runtime import/closure verification.

## Spec

**C1 / P2 — same underlying issue as S1.** §20.16.3 requires current author/no active independent or open_book for session writes, and current authority plus complete owned history before original ACK replay. Fixed `create_session` creates a fresh owner artifact before those decisions. The database/current actor and returned-response gates are present; the defect is the earlier filesystem effect, not authorization to execute a thread. Do not double-count S1 and C1 as two bugs.

The following invariants are present in the fixed source; these are static findings, not independently rerun tests:

| Boundary | Fixed code evidence | Assessment |
| --- | --- | --- |
| Current Session / Policy | access:9–19; security:110–124; policy:30–41 | Every service operation checks live actor/workspace membership. Writes require live author and reject independent/open_book. The two control GETs intentionally do not apply academic Policy restrictions. |
| Origin, CSRF, exact key, query/body shape | HTTP:23–48; boundary:28–40; provider_http:34–44; content_http:25–29 | Router plus existing boundary enforces same-origin/current cookie/CSRF for writes, single syntactically valid original key, duplicate control-header rejection, empty queries and no GET body. |
| Full command and original actor | service:37–57,117–141,163–181; models:48–60; repository:104–113,135–149 | Canonical complete validated body and CAS are bound to workspace/original actor/route/target/key. Exact replay returns its event; body mismatch is 409. Decision wrong new r1 CAS is 412; operation mismatch is 409. Another actor cannot decide or consume the original grant. |
| Original ACK vs current GET | service:67–90,117–124,145–154; repository:118–169 | Original prepare r1 and decision r2 ACKs come from immutable events. Current GET derives revision/status/validity and keeps consumed session ID. Terminal success returns original stored ACK; failure/unknown retains its recorded safe code. |
| Atomic preparation/decision/consume | service:94–109,119–142,162–184; database:50–59 | BEGIN IMMEDIATE scopes append and projection together. Prepare rechecks access after file inspection. Decision creates grant in its event transaction. Consume atomically appends permit/command plus initializing projection, then calls runtime outside the DB transaction. |
| Integrity / missing tail | repository:64–117,133–183; migration:2–29 | Complete workspace table sets, independent memberships/head, contiguous event range, hash chain, command references, historical actor, semantic dates, session mapping and checked receipt are compared. Missing rows/tail are refused; GET does not rebuild them. This does not claim resistance to coordinated replacement of every ledger and witness or arbitrary physical database rewriting. |
| Facts after access loss | service:182–208 | `_finish` uses historical ownership without requiring current author, then a separate query-only transaction rechecks current write authority before delivery. A revoked/learner caller cannot obtain 201, while the actual outcome remains stored. |
| Recovery and no duplicate owner | service:219–237; execution:30–40 | Recovery obtains the registered owner's nonblocking lock and skips an active owner. It reloads checked current facts and writes only unknown for an unfinished ended owner. `_finish` verifies the exact consumed event. No runtime execute is called from recovery. |
| GET zero mutation | service:111–115,210–217; repository read path | Both reads explicitly set query_only, validate before projection and invoke no recovery/append/project function. The runtime's read/validation contracts are assumed at this owner seam and are not independently audited here. |

## Existing fixed tests and gaps

The fixed `test_codex_bootstrap_http.py` has 22 parameterized cases by inspection: unavailable prepare/read/decline zero-Popen and logical dump (49–76); four outcome/replay/restart cases (142–179); post-start learner/revoke fact preservation (182–202); seven shape/CAS/header cases (205–235); and eight single-table missing/tail cases (238–252). Its runtime explicitly declares itself synthetic (79–121). The file's contents are evidence of intended coverage, not a new test-run PASS.

Fixed 366 does not provide these executed acceptance results in this review: concurrent same/different key consume, active-owner recovery racing another app, transaction fault injection at consume/result save, current real Policy changes, replacement actor/cross-workspace HTTP, expired/changed validity with raw historical ACK preservation, or real zero-model upstream bootstrap. Those remain NOT_RUN by this reviewer. Runtime response validation/termination and deployment integrity are excluded, so this review cannot authorize release or override the separately reported runtime tail-output issue.

Recovery is a startup lifecycle action (`main.py:144–145`), not a GET side effect or polling repair. No independent test here proves eventual in-process convergence after an already-running owner ends following another app's initial recovery pass. The spec prescribes safe restart recovery, not a polling interval; this is a coverage boundary, not a confirmed missing product contract.

## Owner coordination and fixed-point limits

The backend author confirmed S1 before this report was sealed and reports an uncommitted ExitStack change moving lock acquisition after complete admission/replay and before permit commit. The author also reports 31 expanded synthetic HTTP cases, plus a separate runtime output-tail fix. Those are author-reported WIP results, not independently inspected or executed in this review. No later delta is included in the fixed 366 verdict; it must be separately read and source-bound after commit.

Conclusion: one confirmed P2 control-order finding shared by the Standards and Spec axes; no further confirmed owner-layer defect established. This is scoped static review, not a runtime/safety/complete acceptance PASS.
