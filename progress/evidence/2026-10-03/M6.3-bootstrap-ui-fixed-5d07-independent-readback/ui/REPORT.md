# M6.3 approved local bootstrap UI — fixed source receipt

Result: fixed UI source plus registered typed transport passes 1037 Web tests in 145 files, strict TypeScript/noUnused, and production build (849 modules). Real bootstrap native/browser and real CLI thread execution are NOT_RUN by this UI owner. Backend 366 is an intermediate registered source, not an accepted runtime gate. These UI results do not clear earlier M6.3 full-gate failures or automatically interrupted diagnoses.

## Source and scope

- Sole normative PRODUCT_DESIGN.md v3.0.14 SHA256 bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144; approved §20.16.
- Root handoff HEAD de801bacab0e3355b83dbfa2537dd9bf3ccf416f with three WIP files. Exact root WIP copies and hashes retained in handoff-owner-01; they were extended, not discarded.
- UI implementation 356a9ade7b0136f93cad5d3cbd5170afd178c991, 13 paths, preserves the existing Shell guard predicates and default label. New optional label is a closed, static literal, never API text.
- Helper's five registered endpoints/backend 366d7b862379b3f3fa27808b04dbbd1b2694a6bc cherry-picked as 8377c77c; owned by helper, not represented as this UI author's backend acceptance.
- Final generated transport test 5d07c43851c84e4e1d8df12d7de52500293c1c3b, actual HEAD for fixed runs 20–22. Complete 1369 tracked non-progress inputs match Git before/after; clean status; source-receipt.json and before/after manifests bind these runs.
- All earlier 01–15 development tests ran on de801 plus UI WIP. 17–19 ran on registered-router 8377 plus final transport-test WIP. They are development evidence, not runs whose Git HEAD was already 356 or 5d07. Only the exact archived pre-fix 12 source and handoff root WIP are snapshot-bound; no invented intermediate source snapshots.
- No canonical/root worktree, specification, remote, real DB, credential, global Codex configuration, account, model, turn, tool, native old-diagnosis, or system probe touched.

## Runtime behavior and boundaries

The client uses generated endpoints and generated JSONSchema, followed by DTO semantic checks for status/revision/consent/session/closed validity, exactly ten-minute lifetime, genuine UTC calendar values, Unicode safe labels, and false feature flags. It does not cast an unregistered route or bypass typed transport.

Explicit flow is local record read → prepare → separate current preparation GET → approve_once or decline → separate current preparation GET → explicit create. A consumed preparation retains its session ID and reads that safe control state. Original prepare/decision ACKs remain history and never authorize the next action. Ready describes a checked local mapping only; model/tools/network and active turn remain disabled.

Original full command body, basis, actor, and key persist in DraftStore; no cookie or CSRF value persists. Every POST rechecks current session and original actor after command persistence. Unknown results permit explicit original-key replay only. A new preparation leaves old unknown history visible. Workspace, access generation, port/store changes and unmount fence late callbacks and late local reads.

Strictly checked late ACKs are retained under the captured original actor before current permission checks. A current valid reader in that same workspace may explicitly save these already received control facts locally without a POST, preserving the old actor and complete basis; this grants no authority to replay the old actor's command. This handles expired/replaced actors without deleting history or trapping the user forever in unsaved memory. Parent dirty/safe/isolated guards continue to protect unsaved facts.

## Evidence ledger (all prior failures retained)

| Run | Actual result | Interpretation |
| --- | --- | --- |
| root setup-attempt01 | FAIL exit 1 | npm invoked at repository root with no lockfile; source untouched; corrected prefix setup02 PASS |
| 01 client | 13 FAIL, 7 PASS | Generated shape alone admitted invalid semantic states |
| 02 client/provider | 22 PASS | Closed semantic checks added |
| 03 panel | suite FAIL, zero tests | Expected missing component scaffold import, not proof of a production regression |
| 04 panel first | 1 PASS | Controlled full protocol path |
| 05 commands | 5 FAIL, 2 PASS | Original actor/basis/current qualification checks initially missing |
| 06 commands/client/provider | 28 PASS | Command bounds corrected |
| 07 panel | 13 PASS | Permission/recovery controls |
| 08 recovery/parent | 24 PASS | Controlled UI checks |
| 09 parent integration | 1 FAIL, 72 PASS | New test omitted fake-indexeddb global harness; fixed test setup, no timeout increase |
| 10 retained ACK replacement reader | 1 FAIL, 21 selected SKIP | Actor replacement could not save original already-received history |
| 11 reader/parent | 23 PASS | Explicit read-authorized local save; original actor and no-POST properties retained |
| 12 late local read | 1 FAIL, 23 selected SKIP | Old workspace async local read could publish into replacement scope; original pre-fix source archived |
| 13 focused | 112 PASS in 13 files | New and existing Provider/Authoring/Codex tests; separate from transport/full gate |
| 14 strict | FAIL | Five unregistered EndpointKeys plus five test literal inference errors |
| 15 strict | FAIL | Exactly five unregistered endpoints remained; no unsafe transport workaround |
| 16 router integration | PASS | Correct helper fixed commit cherry-picked; prior mistyped SHA produced fatal bad revision without source mutation (no separately captured raw log) |
| 17 strict | FAIL | Two new typed transport test tuple-inference errors |
| 18 strict | PASS | Explicit generated request body type fixed test inference |
| 19 transport/client | 21 PASS | Five actual generated paths/keys/bodies, GET absence of write body/key |
| 20 full Web @ 5d07 | 1037 PASS, 145 files | Fixed-source complete Web gate |
| 21 strict @ 5d07 | PASS | TypeScript and noUnused |
| 22 build @ 5d07 | PASS, 849 modules | Existing large-chunk advisory remains; not a build failure |

Early run 01 used an initially incorrect PATH prefix and its Node version was not captured; do not infer its runtime binary from the final receipts. Fixed runs 20–22 explicitly record Node v24.21.0 and their own UTC/monotonic durations.

## Sharing

RAW_MANIFEST.json inventories private originals. SAFE_SHARE.json is the only copy authority; use its explicit relative entries and raw/public SHA256 bindings. Public candidates replace only exact $HOME with $HOME. No arbitrary home-prefix substitution, raw header, database, environment dump, runtime profile, account output, or secret is included. The repository publication scanner and additional concrete-header scan are bounded checks, not a blanket guarantee of arbitrary prose safety. Synthetic test values remain explicitly synthetic. Earlier failures are preserved, not rewritten to PASS.
