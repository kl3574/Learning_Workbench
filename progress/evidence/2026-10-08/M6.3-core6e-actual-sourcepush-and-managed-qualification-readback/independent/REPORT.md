# Proposed publication — fixed 14-source read-only review

Conclusion: **no blocking P1/P2 found within this bounded publication review**. Reviewer tests, patch application, model calls and publication are **NOT_RUN**. This is static source/provenance/privacy/claim-scope review, not production admission or a claim that a push succeeded.

## Exact commit and source binding

- Public comparison source: `63403908eabec794aa1113d0d4ed467f22bae7b4`.
- Four-file engineering author commit: `be92014f0c6e762da20d757703c25057d0aa3057`, compared with `cad77366ad0ffc139b12b33e0a17d3ae4efb2213`.
- Canonical pre-adoption: `e38b859df0cee6081f45ccbdf6bf62b3194aa40f`; actual adopted source: `a72f6f292182ddd795052d456605a184d76dc39f`, parent e38.
- Proposed public head: `6e6748b758436b5c71ff9b63282b583190038a0b`, parent a72. Actual Git readbacks show only 22 progress paths added/changed by this final commit; engineering bytes remain exactly a72.
- Actual public634→a72 and public634→6e comparisons contain the same **14 unique non-progress paths**. Each reviewed candidate file's exact bytes and Git mode matched a72. This is 5 prior A+C paths plus 6 UI/test/config paths plus 3 new core tool paths; README overlaps the prior tool group. A patch text file is a tool artifact, not a change to platform Rust source inside this repository.
- `PRODUCT_DESIGN.md`, API source, contracts and bundled upstream LICENSE/NOTICE have empty public634→a72 diff. Sole spec byte SHA directly read at a72 is `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`. Final6e has no engineering diff from a72. No norm, public contract or production registration change is present.

`CANDIDATE-SOURCE-MAP.json`, `A72-SOURCE-BINDING.json` and `FINAL-COMMIT-BINDING.json` provide the exact 14 paths, sizes, hashes, modes and final progress binding. `receipts/` retains the actual read-only Git argv/native exits/full outputs/hashes. No tests, browser, application, Codex CLI or host probe was started.

## Source-only publication/privacy

The fourteen changed source files contain no private absolute username path or credential-literal match in the bounded scan. Remaining auth/secret markers were inspected and classified:

- Rust patch fixtures contain `Bearer local-only-fixture`, `Bearer owned-local-fixture` and `Bearer changed`; these are explicit local synthetic test constants.
- Existing native test source uses `synthetic-group-native-constant-only`; the diagnostic unit fixture's `PRIVATE_GETTER` intentionally throws if an arbitrary object is inspected.
- UI token references are synchronous local admission identities, not model/account credentials. Budget token fields are test/request limits.
- README archive examples identify the fixed **public official source** and task-owned placeholder caches. No source archive, test binary, raw log, screenshot, trace, database, runtime output or model body is among the fourteen committed paths.
- The new diagnostic accepts bounded status/timing scalars only; its generated test attachment is not committed by this change. Original poll assertions/timeouts and runtime cleanup remain visible and unchanged by the diagnostic.

The final22 progress paths include eighteen curated evidence files (a seventeen-member manifest plus that manifest) and four progress documents. The new source-tree/binary/manifest locators use `$HOME` placeholders, not a real username path. They publish metadata references and hashes, not the corresponding private tree/binary/packet. Three novel path-pattern matches are explicitly classified in `PROGRESS-NEW-LINE-PATTERN-HITS.json`; many earlier-history matches in the large state document are not newly introduced content. This bounded review does not replace root's separate all-outgoing-blob/manual provenance inspection.

## Fixed source and bounded test claims

The core manifest pins official commit `a956835d020762cb2b570053af06f643a11c0ecc`, archive SHA `351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927`, original Cargo.lock and exact Rust1.95.0 identities. The script receives an already acquired local archive; it does not download software. Its default commands are exactly three strict locked/offline codex-core library selections, expected 11+2+1 with exact passed names and full footer checks. Empty/partial selections cannot return scoped PASS. Nonzero commands stop subsequent selections; exceptions/interruption remain failures. Prepare-only uses the existing guarded extraction/patch mechanism and executes zero Cargo/Rust commands.

The core patch's twenty Rust paths exactly match the source manifest, and the actual patch SHA matches its manifest. The new test file extracted from its new-file patch has SHA `8c102534ce4eb43b8fdd58ed4bd4f65de456051617e85f0908b9e4a839df26c7`; removing exactly twelve effort/service_tier/include_internal argument comments yields the frozen B03-r2 test bytes SHA `45f1c1c1ddb840f40c1c050e892707d724e9a9320c5947b62280464a408b7799`. No expression or assertion change is hidden in that metadata explanation. This was text comparison only, not patch replay or test execution.

Public README/manifests/progress preserve these distinctions:

| Claim | Published scope preserved |
| --- | --- |
| New core 14 PASS | 11 controlled pure producer + 2 existing mock WS-header + 1 existing cache-key; complete2676/core guardian and API/HTTP reruns NOT_RUN by this entry |
| Historical API190 and HTTP8 | Separate slices; no additive reuse as full core or platform acceptance |
| HTTP full114/6 and baseline106/6 | Both remain FAIL; no exclusive environment cause claimed |
| Original835 native133 PASS | Its fixed source1573; no claim that this is a new source1579 native run |
| Original93c Python4593 PASS + 2ENV skips | Its fixed source1565; two numeric environment skips remain BLOCKED, not numeric PASS or a fresh1579 full suite |
| Original public634 CI | Both original attempt1 events remain FAIL; each integration2531 PASS/2numericENV skips is separate from run conclusion; same whole Git tree correction and UNKNOWN failure causes retained |
| FinalAuth/ledger | Existing persistent control ledger is implemented; retained auth snapshot/auth-dependent facts/real frozen handle-to-ledger/one-shot sender bridge remain incomplete |
| Product qualification | Empty ProofRegistry/default executor None; no production registration, no real model call, Agent/M6.3/AC21 NOT_ACCEPTED; numeric BLOCKED; M7 todo |

The source/version normalization is explicitly **test-only** `workspace.package.version 0.160.0→0.0.0`, preserving the original lock. No normative release-binary or runtime-profile equivalence is claimed. The top CURRENT next-action describes the subsequent ordinary publication work, while the new evidence REPORT explicitly records `source_push=NOT_RUN`/public634 at capture; actual push success must come from root's later native exit/readback, not this review.

## Bounds

No rewrite of the sealed original CI1010 packet, no CI log download, no remote read/write, and no canonical/source mutation occurred. All staged results quoted above are **claim-scope checks** against the supplied public text and fixed code, not reviewer reruns or fresh independent test qualification. Root separately admitted the author/reviewer/real test receipts. Only the finite final curation's published17 members are hash-checked here; this report does not revalidate the author's full source/build/evidence trees.
