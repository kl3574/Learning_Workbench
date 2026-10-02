# Text edit retained dependency witness: fixed P1 slice

Fixed source `676eb0ed4712793dd9d668b64a072aa6963d6d7d`, parent `316bf693e52f1ca08a675fc7671f4d9cebad3e8b`, isolated tree `m62-text-edit-dependencies-pin-fix-oct02`. Canonical v3.0.13 SHA256 remains `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`. Status: implemented with fixed focused gates PASS; independent review/integration remains root-owned. Original 316 remains NOT_ACCEPTED; its sealed 170 Python / 131 Web results are not relabeled as results for this commit.

The confirmed P1 was a single persisted edge change after edit creation: the base depended on a leaf whose original Concept pin was C:r1; after publishing C:r2, changing only the leaf/r1 concept edge target revision to 2 left the original 316 candidate/base hash unchanged and allowed GET, Review and publication. The original probe, observation and `P1-CONCEPT-PIN-RECEIPT.json` remain untouched in the original evidence directory.

New dependency-bearing bases use internal `draft-base-material-dependencies-v2` with a required Content-owned witness. It freezes full owner/target ContentRefs and relation for the verified bounded dependency closure. The witness enters the existing base-material, candidate, Review and publication hash chain. Read/replay and publication compare the actual closure against that frozen witness; publication also verifies its resulting root, mapping only the original root owner ref to the next revision. Descendant pins and all target refs stay original. Canonical sorting applies only to the internal graph witness: the actual ordered `metadata.depends_on` array remains unchanged and covered by its original metadata/hash.

The existing no-dependency v1 base retains exactly its original fields, defaults and serialization. Unreleased 316 v1 records with dependencies and no witness fail closed. There is no inferred/default witness, old-record rewrite, schema/DTO/API change, migration, new reference-editing permission or additional concept support. All graph/body/pin queries stay in Content; DraftSource calls its named port. GET remains query-only; no damaged edge is repaired.

The distinction between historical facts is permanent-test coverage:

| Changed fact | Checked behavior |
| --- | --- |
| Original base/dependency material or a nested concept pin after freeze | GET, original create/PATCH ACK, Review read/new Review and publication/its ACK refuse the damaged candidate basis without table mutation. |
| Only the later published result r2 root edges; original base r1/candidate intact | Published GET and publication ACK refuse. Original create/PATCH ACK and original Review still return their exact original bytes, because they bind the intact candidate rather than the later result. |
| Source current advances without changing frozen historical material | Exact dependency refs and their order remain original; a changed active base still fails the separate publication CAS. Historical archive/read/ACK and current role/Policy guards retain their existing boundaries. |

Witness integrity starts at the draft freeze. A structurally valid concept pin substitution that happened before the first freeze has no independent earlier pin baseline in this slice. This change does not claim to detect arbitrary pre-freeze substitutions or to migrate all Content integrity history.

## Fixed validation

- `final-python.log`: 180 PASS / 2 existing dependency deprecation warnings, 193.73 s. Command: fixed Python `-m pytest tests/integration/test_draft_edit*.py tests/integration/test_edit_publication*.py tests/contract/test_draft_edit*.py --tb=short --basetemp=<private>/tmp-final-python`. This includes the original edit/publication/HTTP/atomicity/migration regressions, 20 dependency HTTP cases and 7 legacy raw compatibility cases; counts are not added twice.
- `final-ruff.log`: 9 changed Python files PASS. `final-mypy.log`: 236 source files PASS.
- `exact-probe-red.log` / `exact-probe-green.log`: identical private copy of the permanent dependency test source, selected three cases, yields 3 FAIL on untouched fixed 316 and 3 PASS on fixed 676. The original two post-freeze concept-pin variants and the published-root edge variant are all genuine HTTP paths. The latter also proves the intact old Review/create/PATCH boundary.
- `FINAL-INPUTS-BEFORE.json` and `FINAL-INPUTS-AFTER.json`: byte-identical, 1063 tracked inputs matching fixed Git objects and a clean tree. Scope is `apps/ services/ packages/ tests/ scripts/ migrations/` plus root files, excluding `.env*`, `.github/`, `docs/`, `progress/`, other directories, tool environments and ignored outputs. This is neither the original 1045-input set (which included tracked `.env.example`) nor root's larger complete nonprogress set.

## Genuine old bytes

The independent `legacy-capture` package was produced on unchanged fixed 316 using two fresh synthetic `prepared_review_http` fixtures: 2 PASS. It captured exact SQLite owner JSON/stored hashes and actual original-key HTTP ACK bodies, with unchanged table hashes across replay. Its manifest SHA256 is `f4975b5dffc106cfe5d371454cfc2e26a2e700e456b98b5ad48fde0fba28f817`. Only safe raw records/ACKs and their manifests were copied, byte-for-byte, to `tests/fixtures/draft_edit_legacy_v1`; no session headers/tokens or database copies were included.

On the new implementation, five contract cases decode those genuine no-dependency v1 versions/commands/publication, reproduce exact canonical bytes/hashes, preserve base/candidate/parent bindings, and render ACK bodies identical to the captured old HTTP bodies. Two further cases prove the genuine unreleased dependency-bearing v1 records raise the explicit missing-witness integrity error. These two assertions FAIL on original 316 (`legacy-rejection-red.log`) and PASS on new code. This cross-version oracle is decoding/serialization/ACK rendering; it is not a claim that a whole old private database was replayed through a new HTTP server. Current HTTP replay behavior is separately covered by the fixed integration suite.

## Preserved diagnostic boundaries

`original-evidence-preserved.json` verifies the original 316 REPORT, MANIFEST and P1 receipt still have their original hashes and the original tree is clean. Original P1 RED is not overwritten. `pin-red*.log` retain initial post-freeze failures; `pin-green-02.log` is actually 2 PASS / 1 FAIL, exposing the published GET root-edge omission subsequently fixed. `mypy-01.log` preserves the initial Literal annotation error. `python-regression-01.log` was deliberately interrupted during development after that confirmed omission and is not a completed gate; its interrupt traceback remains. The later development 173 PASS run is separate from the final fixed 180 PASS run. Earlier captures did not freeze every development input, so they are not represented as final-source complete gates.

Web, native browser, complete platform Python/Web, remote CI, physical numeric execution, external models and academic/teaching acceptance were NOT_RUN for fixed 676. The separate native followup attempt on another commit failed before browser startup and remains separate; it is not a native PASS. No root integration tree, canonical specification, progress, CI, shared e2e helper or user checkout was modified by this fix.
