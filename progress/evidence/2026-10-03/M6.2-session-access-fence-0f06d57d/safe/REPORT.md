# M6.2 same-page access-transition Session fence

Fixed commit: `0f06d57d25353867493168a5e693f150c3cee535` (clean isolated branch `fix/m62-evidence-applicability-role-race-oct02`). Base: `60fa2b8c18bbd3bbd4122df81bb798fd6d0a3dab`. Worktree: `$HOME/.cache/learning-workbench-acceptance/m62-evidence-applicability-role-race-oct02`.

Sole specification: PRODUCT_DESIGN.md v3.0.13, SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`. Existing Policy/payload restrictions and §20.11 role/Policy acceptance apply; no new contract or routes. §20.10.1's cross-page Editor-only replay permission is unchanged.

## Finding and bounded causal claim

The original full native run at 60fa finished 121 PASS / 1 FAIL in 16.9 minutes. `evidence-applicability.spec.ts:75` immediately counted the original `current_basis_sha256` in the DOM after a learner role click, close, and reopen; expected0, observed1. That assertion is a direct count, not a polling5-second assertion. Original assertions, default timeouts, fixture, and retry count remain unchanged. No failure-time role/session/network trace exists for that historic failure, so this report does not identify its unique historical cause or assert persistent exposure after a confirmed learner response.

The independently controlled reproduction proves an existing compatible mechanism. The client emitted an access-generation notification when POST role began, but allowed new GET session reads while the write was still in flight. A new applicability owner could read the still-author server session, load its protected journal, and become ready. The pending-memory hint is visible even when not ready and is not evidence of learner authorization.

The v4 actual-browser probe holds the genuine role POST at one of two boundaries, issues a separate genuine server GET session, records only safe role/status/time/DOM counts, then releases the original POST. It uses the original real Assessment/grade/evidence/IDB fixture. Concept revisions use the fixture's existing ContentService helper; no event/evidence/grade SQL injection, model call, or invented route.

| Exact v4 probe | Old60fa | Fixed0f06 production bytes |
| --- | --- | --- |
| Before actual role commit | GET still author; knowledge entry enabled; protected basis count1; RED | GET still author; knowledge entry disabled during unknown transition; count0; PASS |
| Server committed learner, response delivery held | GET learner; count0; PASS | GET learner; knowledge entry disabled until settle; count0; PASS |
| After releasing either original POST | Genuine learner response and count0 | Genuine learner response and count0; retained-memory hint remains |

The probe observes DOM every animation frame for a bounded400ms while the POST is held. This is an additional causal exposure observation, not an extension of the original case's assertion timeout. Probe SHA256 is identical across the final RED/GREEN runs: `4fd8278e462d9f4e84e2b1dff55a6b6aa32e79cace79070e7671ad4a50de50a7`.

## Minimal implementation and permanent regressions

Only three files changed:

- `apps/web/src/api/client.ts:6,20–36`: count existing access-changing POSTs before their start notification; defer only new GET `/api/v1/session` dispatch while any such same-page mutation remains; release in fetch `finally`, including network/abort/HTTP failures. Recheck the count after waking. No extra await is inserted when the count is zero. Role writes, bootstrap, safe Jobs reads/cancel, and unrelated endpoints are not fenced.
- `apps/web/src/api/sessionAccess.test.ts`: eight transport cases cover both role directions, two concurrent mutations, safe Job control, three failure modes, initial session/CSRF acquisition and first role write, and bootstrap with a simultaneous fresh session read.
- `apps/web/src/features/evidenceApplicability/sessionTransition.test.tsx`: two actual-hook/client cases cover mounted and newly opened owners, original ACK memory retention/save-only recovery with one decision POST, and an already-dispatched old author response arriving after learner completion. No production applicability owner code changed here.

This is a page-local pending count. Existing cross-page BroadcastChannel notifications still communicate only generation changes; cross-page in-flight exclusion is NOT claimed. Already dispatched GETs are still rejected by the owners' existing generation checks, not by retroactively cancelling their HTTP requests. A never-settling role write keeps new subject authorization reads unknown; no timeout silently re-authorizes it. Safe control endpoints remain available.

The independently committed late-ACK repair `93bc2ed5b64dd1bcc311e303dff76fd29575f659` is a distinct defect and is not included in this commit or these full-Web results. Static mutual review found no interaction blocker: this fence waits only before GET session; it does not block an already sent decision's ACK. That repair strictly validates the ACK, retains it under the captured original session, then requires the existing valid guard before persistence/display. It does not expand replay permissions. Combined full gates remain root-owned and NOT_RUN by this report.

## Actual verification

Every command, cwd, exit, start/end time, log SHA, and before/after input inventory is retained in its stage receipt. Tests were run before commit; `final-source.json` verifies every one of the1277 final tracked non-progress files exactly matches all six final gate inputs. Each gate had1278 unchanged inputs because it also included the private v4 native probe. That byte-identical probe was archived and removed from the engineering tree before commit; no other engineering bytes changed.

| Stage | Actual result |
| --- | --- |
| original-case-02 (old source; one bounded original rerun) | 1 PASS26.1s; not reproduced in that schedule |
| final-regressions-red-02 | 8 FAIL /2 PASS on old client, exact final test bytes |
| final-regressions-green-02 | 10 PASS /2 files604ms on final client |
| controlled-role-red-04 | 1 FAIL /1 PASS28.7s on old client; expected count1 failure |
| controlled-role-green-02 | 2 PASS37.4s on final client; same v4 probe bytes |
| original-case-fixed-01 | Unchanged original complete case1 PASS24.5s; actual role isolation, original ACK save, correction/restart and protected grade/private-pin assertions |
| full-web-01 | 929 PASS /134 files10.24s |
| strict-types-01 | PASS, `tsc --noEmit --noUnusedLocals --noUnusedParameters` |
| build-01 | PASS, tsc plus Vite841 modules; existing large-chunk advisory retained |
| git diff --cached --check | PASS before commit |

Independent peer review of fixed0f06 reported no new blocker and independently reran the8 transport+2 owner cases:10 PASS. This is separate from our own gate receipts and does not imply full-native closure.

Earlier failures remain intact: original-case-01 was a private-config ESM setup failure with no browser execution; controlled-role-01 had the expected before-commit exposure plus an incorrect probe-only learner text expectation; the corrected after-commit control passed. Initial strict TS failure was a test fixture missing required JobCancelRequest.expected_revision, corrected before final test freeze. controlled-role-green-01's old probe attempted to click the now correctly disabled knowledge entry; it failed before exposure observation, and finally teardown caused a route.fetch reset. v4 explicitly observes either disabled navigation or an opened owner, then releases and completes recovery; it was rerun on old source first, where it still failed count1. No failure was overwritten or reclassified as PASS.

The original full-gate receipt records `unchanged:false` because that suite generated five tracked docs/ui screenshots/metrics. Those root-owned outputs and its single failure are not erased by this local work. Our final stage inventories are all unchanged.

## Evidence handling and safe transfer

Private originals: `$HOME/.cache/learning-workbench-acceptance/m62-evidence-applicability-role-race-evidence-oct02`.

Use only the explicit `safe-share/` allowlist for later packaging; never glob the private directory. The first post-fix probe's route.fetch teardown error automatically wrote two temporary runtime credential header lines. The original remains private. `safe-share-transformations.json` records its raw SHA, derived SHA, removed line numbers, operation, and original-line hashes without recording the values. Each removed whole line is replaced with a fixed omission marker; other selected files are identity copies. This transformation is additional to, and must not be described as, exact-home-prefix normalization. All final accepted stage logs and role timelines contain no credential values. Console excerpts after discovery use the same bounded header-line omission.

No remote writes, provider/model calls, environment enumeration, specification/generated/progress edits, timeout changes, or writes to root/frozen acceptance trees were performed. Only this isolated three-file repair was committed. No full Python or complete native suite was rerun; root owns integrated acceptance after both separate fixes.
