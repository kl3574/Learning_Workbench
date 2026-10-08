# Ordinary worker lease / fixture diagnosis — ad494

No production defect is established by this bounded diagnosis. No production/test/spec source was changed or committed. The isolated tree remains clean at `ad49490e78c21174349595da8090c6c2b445bce9`; all 1,340 tracked non-progress input files match that Git commit. The backup fix b634 is absent. This does not clear either original gate ERROR.

## Original facts retained

- Root full Python gate: **3633 PASS, 2 actual-numeric ENV skips, 1 setup ERROR, 2 warnings**. Original case is `test_review_numeric_observations.py::test_original_numeric_ledger_loss_or_tampering_is_rejected[group-preview_command]`, failing before its damage operation at `test_authoring_group_numeric_service.py:101`: `running != completed`, error code `None`.
- Exact failed synthetic DB `test_original_numeric_ledger_l7/data/workspace.sqlite3` was opened read-only/immutable; bytes stayed SHA256 `34655efe9776b737b279a8fb8d832a135e522dafc9b98f897df364840b9b0364`. Parameter collection order is separately retained. Only schema names/counts and safe job/event/receipt metadata were exported; the Group DB has no WAL, and the Import WAL is empty; no database, request body, output body, token, locator value, or credential was copied into the share candidates.
- Job claim event: `2026-10-03T10:34:40.277163Z`; last persisted expiry: `10:35:10.674575Z`; Provider terminal recorded: `11:20:01.332231Z`. Original terminal: `type=error`, `error_code=OUTBOUND_SOURCE_UNAVAILABLE`, `provider_outcome=completed`, `output_state=partial`. Three original events only, revision 3, cancel false, no candidate. This is evidence of a terminal recorded beyond the persisted lease, not evidence of 45 minutes of real elapsed work.
- Original runner start/end UTC: `09:46:13.390188` / `11:27:18.867669`; recorded duration `2280.374s`, pytest `2279.52s`. UTC subtraction is `6065.477481s`. Preserve both clocks: these records do **not** identify suspension versus host wall-clock adjustment or a different host timing cause.
- Separate b634 backup-owner regression gate remains **221 PASS + 1 setup ERROR**. Exact import fixture DB SHA256 `33bdebfad10284a82ff99dd19b913496792d07f67aa8c83f32e20d5f9c3541d0` is unchanged. It has revision 2 / running / parsing, cancel false, only queued/running events, claim `11:35:05.799505Z`, expiry `11:36:35.799624Z`. There is no persisted attempted-finish time. Do not claim that this historical Import ERROR has the same physical cause merely because its symptom matches.

## Red-capable feedback loop

All runs use the unchanged ad494 worker implementations, locked existing dependencies via `uv run --frozen --no-sync`, dedicated private pytest basetemp (controlled/recovery runs additionally set TMPDIR explicitly), real SQLite, actual isolated import parser, and a synthetic loopback-only Provider. No vendor or actual numerical execution evidence is claimed.

| Evidence | Actual outcome | Meaning |
|---|---|---|
| 01-original-cases | 2 PASS / 4.70s | Both exact original cases pass once in isolation; no original ERROR erased. |
| 05-clock-boundary | 1 collection ERROR | External pytest file initially missed repository pythonpath; preserved. |
| 06-clock-boundary | 2 FAIL + 4 PASS / 7.24s | Original assertion RED for each injected expiry; two valid controls and two recovery contracts PASS. |
| 09-provider-error | 1 PASS / 1.52s | Exact original Provider error-field tuple recovered safely. |
| 10-repeat | 2 FAIL + 5 PASS / 6.81s | Final probe same bytes; both original assertion REDs repeat, all controls/recovery PASS. |
| 11-existing-recovery | 5 PASS / 7.30s | Existing three-root Provider recovery, Import expired-owner/no duplicate, and stop-before-parser-consumption contracts. |

The private probe changes only the `datetime` class references used by this process's `utc_now` and `expires_after`. It advances local UTC by 120 seconds at a precise seam: after genuine Group Provider work before `_finish`, or after the actual import parser returns before `complete_preview`. It does not change system time, sleep, increase any timeout/lease, or poll until an assertion passes. The negative oracle calls the **unmodified original fixture** and preserves its original assertion. RED therefore demonstrates that `run_once() == True` does not guarantee a completed fixture when its lease has expired.

For the Group error case a second seam advances that same local clock at the real Provider guard after a usage fact is recorded. Real checked transport/decoder produces exactly `OUTBOUND_SOURCE_UNAVAILABLE / completed / partial`; the original fixture again reaches `running != completed`. This is a controlled clock fault, not a recreation or diagnosis of the original host pause.

Recovery checks explicitly call a **fresh owner once**, then verify its result (and one idle call). These are separate recovery-contract tests, not polling added to the original fixture. Group recovery preserves the receipt digest, has exactly one durable dispatch, and replaces the dispatch method with an assertion that would fail on any second dispatch attempt. A checked completed result becomes one completed candidate; an original error result becomes failed with the original error/output and **no candidate**. Import's local deterministic parser may rerun on a fresh lease and reaches preview_ready without publishing content.

## Falsifiable hypotheses and conclusion

1. Lease expiry before adoption: **supported** by the Group original metadata and both deterministic original-assertion REDs. Invalid old ownership correctly refuses adoption.
2. Wall-clock discontinuity versus real long scheduling delay: timing domains are inconsistent; **underlying host mechanism UNKNOWN**, no system probe performed. Import original expiry at attempted finish is unrecorded.
3. Another worker took ownership or cancelled: **not supported** by either original event/revision/cancel history. Both controlled reproductions have one original worker and no owner replacement before failure.
4. Valid-lease finalization was omitted: **not reproduced** by the valid controls; controlled recovery converges. This is bounded evidence, not a proof against every possible race.

The observed shared state is consistent with lawful lease loss, not a confirmed shared watchdog/finalization bug. Do not weaken ownership checks, finish through an expired lease, prolong leases, add fixture polling, or reinterpret bool True as terminal success. A later full gate remains necessary to replace a failed gate status; these diagnostics cannot do so. A separate permanent lease-boundary regression could retain this contract if desired, but no product repair is justified by this result.

## Exact specification/code basis

- `PRODUCT_DESIGN.md:406,448,732,744`: durable single worker/leases; atomic terminal + artifact; expired lease reclaimed; local side effects idempotent.
- `PRODUCT_DESIGN.md:1039,1061,1063`: current lease separately checked; dispatch-start remains immutable; external request cannot auto-replay; recovery may adopt known persisted results or end the local task.
- `authoring_job_repository.py:221–241`: claim / owned / renew. `authoring_group_worker.py:104–109` refuses stale `_finish`; `:220–223` adopts a persisted result; `:247–270` joins watcher, calls finish, returns work bool.
- `import_worker.py:135–138,202–209`: ownership check and stale preview refusal; `:287–328` run_once and stopped/error outcomes; `:110–133` reclaim of expired local work.
- Existing recovery tests: `test_authoring_group_recovery.py:50`, `test_import_repository.py:148`, `test_import_parser_exit_race.py:104`. Original failing fixture seams: `test_authoring_group_numeric_service.py:101`, `test_assessment_attempts.py:38`.

## Preservation / sharing

`SOURCE.json`, `INPUTS.json`, original safe metadata, private probes, all actual logs including FAIL/collection ERROR, and synthetic temporary fixtures are retained. An exploratory metadata reader initially used `datetime.UTC` under system Python 3.10 and raised AttributeError; it was corrected to `datetime.timezone.utc`, with no production change or original database write. An rg lookup used a nonexistent migration directory; it did not affect execution.

`RAW_MANIFEST.json` is a private integrity inventory, **not an upload list**: it includes synthetic DBs and synthetic credential fixtures. Only exact files enumerated in `SAFE_SHARE.json`, under `safe-share/`, are candidates. Their only transformation is the exact `$HOME` prefix to `$HOME`; raw and derived SHA256 are retained. Publication scanner plus authentication-header checks apply to those explicit candidates only. No user checkout, root progress, remote, real database, secrets, external model, system-security probe, or native UI was accessed or modified.
