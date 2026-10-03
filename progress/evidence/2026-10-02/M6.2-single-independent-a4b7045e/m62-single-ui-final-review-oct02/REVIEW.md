# Independent final Single UI recheck

Result: the previously reported actor P1 and original-publication r1 P2 are closed on final UI commit `a4b7045e435e0c4fa7c2b2364ade2407a8cd9afc`, tree `fc5f2269264fe733608cf764c4928540d2aae688`. No remaining confirmed blocker was found within this recheck's actor/replay/ACK and r1/current boundaries. This is independent local evidence, not a claim that native browser or physical numerical acceptance passed.

## Source and isolation

Project: Learning_Workbench. The original checkout, parent integration tree and UI owner's worktree were read only. Execution used detached worktree `$HOME/.cache/learning-workbench-acceptance/m62-single-ui-final-recheck-oct02`. Tracked files remained clean; the only untracked file is the byte-identical original actor eligibility probe. Existing pinned Node v24.21.0 and node_modules were reused through ignored symlinks; the checked source and installed source package-lock SHA256 match. No dependencies, databases or environment/credential values were copied into the repository. Temporary files use this archive's dedicated tmp directory.

The reviewed actor fix is `eeba82315fb761a9dc230a4c327b6335319d473a`; r1 fix is `fd8aa16e98f920e11c7f04185a7cef1fa1d1aa0e`; final a4 also includes exact-form-version consumption. This execution binds final a4, as requested, and is not represented as a separate execution on each intermediate commit. Sole normative source PRODUCT_DESIGN.md v3.0.13 has SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`.

## Actual execution

- Original three probes: 3 files / 3 tests PASS, exit 0. These are the original actor eligibility, actual replay and non-r1 GET rejection probes with unchanged bytes; `probe-byte-identity.json` records all original/executed names and SHA256 values.
- Complete Single feature group on final a4: 10 files / 40 tests PASS, exit 0. This includes the owner's 39 tests plus the independent original actor eligibility probe. The three-probe run is a subset of these 40, not three additional distinct tests.
- Exact commands, worktree/tree/lock/toolchain bindings and status are in `source-binding.json`. Raw output is retained as `original-probes-final.log` and `single-feature-final.log`.
- All three original RED logs and original probe bytes are retained in `original-red/`; no previous failure is removed or reclassified. A metadata lookup initially named a nonexistent root-level package-lock.json; the corrected actual lock path and this non-test error are recorded in source-binding.json.

## Review conclusions

**P1 closed.** `useSinglePublication.ts:44-47` freshly reads and validates the actual actor, workspace, author permission and assessment restrictions. Original replay requires page/access eligibility plus a page-memory proof binding the exact immutable original command to its original actor (`:83-92`, `:209`; `singlePublicationMemory.ts:6-15`). The actor proof is not serialized into IDB or the HTTP command. A persisted command lacking that proof remains read-only, including a same-page/generation-looking journal record after recovery. Existing previous-page and old access-generation refusal is retained.

The fresh actor check happens before original command persistence and again immediately before POST (`useSinglePublication.ts:92`, `:102`). A returned ACK is first retained under the captured original actor (`:87`, `:105`), before current-scope and fresh-actor checks (`:106-109`). Thus a late response after access/actor change is preserved as an original fact and is not relabeled as the new actor's work. Save-only recovery checks the fresh original actor and sends no HTTP (`:128-145`). Exact original body/key and existing immutable ACK conflict checks remain intact. The passing tests exercise unannounced actor replacement, replacement during HTTP, ACK write failure, access-generation change, different-actor recovery rejection and missing actor proof, alongside the original two actor probes. Current permission/assessment checks were also inspected in the shared fresh-session predicate; this report does not claim a newly added permutation test for every session field.

**P2 closed.** `singlePublicationSchema.ts:20` applies `singlePublishedRef` to every non-null Single GET publication reference; that helper rejects revision other than 1. The unchanged original r2 GET probe now passes. The ordinary current reader still uses `publicationRef` (`useSinglePublication.ts:168-177`), while independent GET verifies the original publication association (`:178-186`). The feature test proves later current r2 is accepted separately without changing the original r1 ACK.

The final form-consumption delta captures the exact submitted form version before the first await (`useSinglePublication.ts:152`), only consumes that exact original version (`:94`), and original-command replay does not consume a later unsent form (`singlePublicationMemory.ts:48-57`). The feature group includes the original independent delayed-ledger form probe and the storage-failure/replay variants. No new finding was identified in this bounded delta review.

## Evidence limits

These are controlled Vitest React-hook, strict-schema, fake-IndexedDB and transport tests. Numeric PASS-shaped fixture data is synthetic; no sandboxed numeric program, native browser flow, model service, CI gate or full Python suite ran in this recheck. No stage-wide PASS or physical numeric PASS follows from this report. Parent-owned integrated and native gates remain separate evidence.
