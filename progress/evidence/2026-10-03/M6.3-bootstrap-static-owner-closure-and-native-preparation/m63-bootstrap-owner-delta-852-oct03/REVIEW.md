# Fixed 852 owner delta — static P2 closure

Source 85293a6ddc074238f4508f50e7e19f7d523ee549, parent 366d7b862379b3f3fa27808b04dbbd1b2694a6bc. Only the already reviewed owner layer is revisited against sole v3.0.14 §20.16; no runtime isolation/response/deployment review, CLI, tests, model, native browser, network or system probe. Original fixed 366 review and finding remain unchanged.

The prior P2 is statically resolved. In application/codex_bootstrap.py:160–178, ExitStack is initially empty. Current identity/Policy and full history are checked at 162; original key/body replay returns or raises at 163–165 before any owner hold. Grant/original actor/consumption/root/current qualification checks finish at 174. Only line177 enters owners.hold. That lock is acquired before the single consumed permit and session transaction commits and remains held through execute, _finish and the final current-permission delivery check (185–198). Runtime execution remains outside the DB transaction. Invalid admission and original replay therefore cannot allocate an unrelated new owner file on this path. No additional owner-layer defect was established from this small delta.

All previously reviewed access/repository/execution-lock implementation/HTTP/main/models/ports/migration files are byte-identical between 366 and 852; SOURCE.json names them. The separate runtime and runtime tests do change and are explicitly NOT_REVIEWED here.

Permanent regression assertions exist in the new HTTP tests, inspected but NOT_RUN by this reviewer:
- test_concurrent_original_command_and_recovery_observe_one_live_instance, lines276–279: capture existing owner file list, same-key initializing replay and different-key refusal, assert the identical file list; lines280–282 verify active-owner recovery does not terminate/start another instance.
- test_derived_current_validity_never_rewrites_original_approval, lines324–346: changed/unavailable/expired new consumption refusal, no runtime calls/DB change and no owner directory.
- Terminal ready/failed/unknown/exception replay at lines165–173 checks original response/ACK bytes or safe error code, runtime calls and database dump, but does not explicitly compare owner file lists. Line286 likewise checks terminal replay 201/call count only. That narrow direct filesystem assertion is still a coverage gap, not evidence that the fixed control path remains wrong; it was reported to root and the backend author. Do not say all four terminal states have directly verified owner-file counts.

Author reports 34 HTTP PASS; that report is not this reviewer's execution evidence. P2 code closure is static. No overall backend/runtime or release PASS is issued.
