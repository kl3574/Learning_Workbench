# Independent Standards / Spec review: bounded synthetic backup tests at 942fc

**Standards: zero new P1/P2. Spec: zero new P1/P2.** This candidate prepares local coverage of the existing §20.17.7 historical-actor/authority boundary. It neither implements nor accepts M7 restore workflows, background worker recovery, GenericApproval/Import backup coverage or live Codex execution. It remains a local, unmerged test candidate; M7 remains todo and dependent on M6 acceptance.

## Fixed input, authority and method

Reviewer `/root/m63_artifact_final_review_oct04` authored none of this test, its harnesses or original runs. One independent reviewer reports two axes. Review consisted of immutable source, related existing source seams, sole norm and explicitly admitted documentary evidence. No new product/CLI/browser/model/network/host execution, source/canonical edit, old seal overwrite, remote merge or publication occurred.

Fixed source `942fc533ca48e1a561199fb992d80e76622948c1`, base `d6d4d9b98316d7f3790eb60e5d1bb4aca67450d1`, immediate parent `dfd9a77de24c2ca9145466f91299a13d0a2d967b`. Actual parent chain d6d4 → dfd9 → 942fc was verified. Sole PRODUCT_DESIGN v3.0.15 SHA256 remains `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`.

Exactly one new path, tests/integration/test_backup_codex_turn_history.py, **181 additions / 0 removals** relative to base. Final 1523 non-progress Git inputs contain all **1522 base inputs unchanged** in mode/type/blob/size/SHA; production, routes, DTOs, norm, dependencies, native/test configuration and baseline migration are unchanged. Final/original admitted test bytes and the complete base..final patch equal their immutable Git source. Parent→final is solely the temporary-directory isolation change, 4 additions / 4 removals; assertions, original backup helper, timeout and business permissions are retained.

## Standards review

The two tests reuse existing fixture/CLI/hash seams, require nonempty turn and Provider-Codex history, and, in the completed case, nonempty manifest/member/artifact/blob history. Their owner-hash comparisons do not use empty tables as proof of those scopes. GenericApproval/Codex Import tables are expressly asserted empty and are not claimed covered. Whole-table hashing is the existing safe helper; it does not print credential rows. Direct fixture SQL/private owner reads are confined to integration tests, not product owner interfaces.

Source `cli_backup` runs actual make backup against the synthetic fixture, checks source table/file preservation, archive-listed payload sizes/hashes and absence of old authentication material, then manually expands a private temporary database/blob copy. New owned_backup also scans only this known synthetic archive for the fixture peer value and confirms transient answer-output files are not exported. No user/provider key or real private material is embedded in the test. The completed fixture explicitly calls a SyntheticCodexExecutor once before backup; queued dispatch is zero. No real Codex CLI or vendor request is implied.

Originally the fixture data directory and helper scratch directory were the same pytest tmp_path. Existing preservation assertions correctly failed because helper stdout/stderr and a uv lock appeared inside source data. Final uses two independent tmp_path_factory scratch directories. The bounded original excerpt, both failed CLI receipts and immutable 4+/4- source delta support this fixture-layout diagnosis. It is not a manufactured product behavior RED, and the original two failures are retained. No assertion, timeout, retry, source helper or product code was relaxed.

fresh_reader installs fail sentinels on the restored synthetic transport and direct run_once seam and uses a fresh ControlledRuntime. **Its TestClient is not entered as a context manager**; app lifespan/background worker startup does not occur. The sentinel and empty runtime/transport counters prove only the directly exercised GET/rejected-command paths did not invoke those seams. They are not evidence of background convergence, all processes/networks, or restored old-actor execution safety.

No new standards defect was found. Original dependency warnings remain visible; no dependency edits hide them. This review did not rerun the recorded gates.

## Spec review

PRODUCT_DESIGN §20.17.7 requires history/actor/reference retention, authentication noninheritance, nonexecutable old permission and no execution from restored GETs. §20.5 backup sanitization (line1033) does not pre-implement M7; full M7 preview/restore/transaction/recovery requirements at lines1079 and the M7.1/dependency entries remain broader.

This bounded preparation exercises actual CLI backup of two legitimate synthetic cases and readback in a manually expanded copy:

- **Queued/granted turn:** all six named turn and four Provider-Codex tables are nonempty and copied unchanged. Old stored ACK JSON and original grant actor remain the original facts. Control still says queued/not_started/no consumed provider calls. Current proposal becomes unavailable; the historical active grant is not treated as an executable current grant.
- **Completed manifest/blob:** one explicit synthetic dispatch/materializer produces a real checked BlobStore copy. Archive metadata includes the expected 26-byte blob; copied checked manifest HTTP bytes, downloaded blob and answer match the synthetic original. Completed outcome/manifest binding is retained. mathematical/sources/independent_pedagogy stay NOT_RUN.
- **Fresh access and denied takeover:** original cookie is401; fresh bootstrap establishes a different learner actor. Safe turn/session GET is allowed while academic preparation/consent/result/manifest/download GET is403. Only an explicit fresh role switch admits author history/material reads. The fresh actor cannot replay the original turn-start or outbound-grant body/key:403 with unchanged table hashes/owner facts. This is not a GenericApproval approve_once test; no such history exists.
- GET-only blocks compare whole-table hashes before/after. Role-switch/bootstrap writes are intentionally outside those GET baselines. Direct owned-state historical validation uses query_only. Original history and current projection are kept separate; dynamic validity is not incorrectly required to remain the original wire value.

The candidate does not run product restore-preview/restore-commit, old-actor restored worker/dispatch-start, lifespan recovery/convergence, GenericApproval/Import history backup, corruption/rollback/fault recovery for M7 or learner/author export profiles. Those remain NOT_RUN. Therefore zero new Spec findings is for this accurately limited local test preparation, not a claim that §20.17.7 in all execution circumstances or M7 as a whole has been accepted.

## Documentary evidence independently read back

Admitted scope is exactly **56 safe-share candidates** in owner SAFE_SHARE_REVIEW.json plus the two named outer metadata files. Candidate SHA/size and reconstructed original declarations match identity or sole literal home-prefix display transformation. No original whole failure log, DB, ZIP, secret directory, runtime tree, unlisted prior manifest or image was opened. The archive payloads themselves were checked by the existing recorded test, not freshly opened here.

Owner SAFE SHA: `5ae427e1282589d1907d7d21ed7d017df8bab460f19fc2e7aaeaf471861f1c8d`. Outer SHA: `37fa449ee70c338b8e1541f434130342204c1a506608c5492924fb49bb6d9efd`. Admitted report SHA: `681b8574ef6af59d942bd7f92638fe9413e55df68c67ce3fe67d553f98f19955`.

All five stages' **10 original before/after maps / 15230 size+SHA256+Git-blob bindings / 1505 distinct blobs** match actual immutable Git. Each map has1523 inputs and its before/after bytes are equal. Original execution maps did not record file modes; mode/type were separately verified in immutable full source inputs and are not retroactively added to the old maps. Admitted runner/hash-finalizer scripts are documentary and statically read, not executed; old gate receipts do not contain a runner hash, so no run-level runner binding is invented.

| Original source/gate | Actual admitted result | Timing and limit |
|---|---|---|
| dfd9 focused | **2 FAIL**, exit1; bounded original excerpt | pytest5.05s / wrapper5.636s; complete failed log remains private/unread, declared SHA `612a2f77bbc691241318966bba808d94ef45dfed9f5a4950aefbb34836fa6759` |
| 942fc focused | **2 PASS**, exit0 | pytest7.05s / wrapper7.540s; original log SHA `6f2d8bc689f8c6bb6653405e8e3eb988872b70d28b47681f507050905e9b4098` |
| 942fc related six files | **21 PASS**, exit0 | pytest23.56s / wrapper24.077s; original log SHA `225347bd47de98b7f4d5e1b462aaf76f2adbd4cc9b220d88e1ae3678924e294f`; subset is not full-platform gate |
| 942fc Ruff new file | exit0, All checks passed | bounded new-file static gate |
| 942fc diff base..HEAD | exit0 | explicit immutable delta; original empty successful log |

The two pytest PASS logs retain the actual two TestClient/anyio deprecation warnings. Six admitted backup CLI receipts all report actual exit0. The original two report changed source files and lead to failed pytest preservation assertions; the later four report source files and tables unchanged. Thus CLI exit0 alone is never substituted for test success.

Four successful archive-metadata candidates are internally checked: admitted checked_payloads equal manifest.files, expected DB/blob paths/26-byte size agree, sensitive_personal_data=true, consent_dispatch_disabled=true and restore_acceptance=NOT_RUN. Manifest raw bytes are reconstructable using the unchanged backup writer's serialization and their SHA matches. Archive SHA/size and payload verification remain the owner's original documentary declarations/test assertions: the underlying ZIP/DB is not newly read by this reviewer. No metadata-only check is renamed a new pytest or restore acceptance.

The old READBACK candidate_count53 means before adding itself; original allowlist54; final56 adds the two documentary SHA-binding/script files. The explicit appended explanation is retained. Unadmitted old/private manifests are not accessed to force those counts to match.

## Status, next task and safe result

This local candidate can be retained as bounded future coverage. **M7 remains todo, dependent on M6.3 acceptance; product restore and background convergence remain NOT_RUN.** No canonical merge, remote action or release is approved/performed by this review. Once stage dependencies permit M7 work, next coverage must exercise the real restore preview/commit lifecycle and startup/recovery behavior, including nonempty approval/import histories and original-actor/old-grant execution refusal.

Only five independent text candidates are explicitly prepared: REVIEW.md, REVIEW.json, READBACK.json, FIXED_SOURCE_INPUTS.json, VERIFY_READONLY.py; only SAFE_SHARE.json and OUTER_METADATA.json are outer metadata. Literal local-home substitution is the only transform; display-transformed verifier is archival, not promised runnable. Pure bounded inspection of these proposed bytes reports zero findings, not a new product test or final full-history publication audit. Nothing was published.
