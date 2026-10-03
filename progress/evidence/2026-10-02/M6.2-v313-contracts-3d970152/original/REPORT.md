# Single worked-example publication: strict contract slice

Source commit: `3d9701526f5a586accc74d37b9a38a3a309a3a5c`.
Parent specification commit: `2ea65013140ace31ed4b739f66c6218ce5912ff8`.
Sole specification: PRODUCT_DESIGN.md v3.0.13, SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`.
Independent worktree: `$HOME/.cache/learning-workbench-acceptance/m62-generated-publication-contracts-oct02`, clean after commit.

## Specification adoption review

Read-only comparison of approved proposal `1920edd1ed60aa1b324afd90bc3928075e843f96` against the canonical adoption found no added or removed product semantics. Reviewed the complete v3.0.13 delta against the previously completely read v3.0.12 specification. The publication mapping, unresolved provenance, exact historical ACKs, current GET semantics, transactional launch admission/publication race, unknown-outcome recovery, numerical observation boundary and acceptance scope are preserved. Appendix AuthoringDraftView and §20.10 were updated consistently. No canonical specification edits were made by this agent.

## Implemented scope

- `AuthoringDraftView.state` is strictly `draft|published`; `published_ref` is required `AuthoringBlockRef|null`, with no default. The model enforces `state == published` iff the reference is nonnull. Existing strict block-ref conversion accepts a checked core ContentRef while rejecting non-block entities.
- Existing candidate/payload/body hash checks remain. This current-read projection does not alter persisted candidate, Numeric, Review or command ACK models/bytes.
- `checkedAuthoring` enforces the same state/reference relationship for this one DTO after validating its generated wire shape. Added frontend rejection tests for missing field, inconsistent states, foreign entity, candidate masquerading as ContentRef, extras and boolean revision, without mutating rejected input.
- Updated only two handwritten current-GET frontend fixtures to include explicit null. Historical source/evidence fixtures were not rewritten.
- Regenerated and byte-checked all 78 current contract artifacts, including provenance headers and generated specification locators. The generated OpenAPI paths and all 54 core schemas (excluding source metadata) are unchanged; the sole changed runtime component is AuthoringDraftView. See `schema-diff-audit.json`.
- No backend publication/projection/worker, migration, core-model, canonical specification or root progress files were edited.

## Actual verification

Python interpreter: `$HOME/Desktop/learning/Learning_Workbench/.venv/bin/python`.
Node: repository `scripts/node.sh`; final node_modules points to the complete dependency tree in `m62-public-safe-oct02`.

| Check | Result | Evidence |
|---|---|---|
| Current generated artifacts, explicit private Settings and no initialized storage | PASS, 78 artifacts | generated-check.log |
| Contract tests excluding four storage/transport files | PASS, 609 tests, 149.47s | contracts.log |
| Authoring frontend subset | PASS, 88 tests / 15 files | authoring-web-fixed-deps.log |
| Full frontend suite | PASS, 869 tests / 121 files | web-all.log |
| Full TypeScript check | PASS | typecheck-fixed-deps.log |
| Full web lint | PASS | web-lint.log |
| Ruff on changed Python DTO/tests | PASS, tool stdout `All checks passed!` | execution receipt in agent tool history |
| Mypy on DTO, follow-imports=silent | PASS, 1 source file | dto-mypy.log |
| Whitespace/diff check | PASS | execution receipt in agent tool history |

The contract command used `pytest -q tests/contract --ignore=tests/contract/test_retrieval_http.py --ignore=tests/contract/test_tutor_transport.py --ignore=tests/contract/test_restore_numeric_transport.py --ignore=tests/contract/test_practice_public_projection.py --tb=short` with a private basetemp. In that process, `Settings.from_env` was replaced by an explicit private Settings constructor before pytest collection; the private data path was asserted nonexistent before and after the run. Generation likewise called the actual application factory with explicit private Settings, without entering lifespan or initializing storage. No keys, live environment values, application databases or provider calls were read.

Initial frontend attempts used an older shared node_modules missing CodeMirror. They produced typecheck errors and one frontend import failure (86 other tests passed). Those original failures are retained in `typecheck.log` and `authoring-web.log`. After correcting only the ignored dependency symlink, the corresponding checks and full frontend suite passed. No dependency manifest or lockfile was changed.

## Integration boundary

The production construction at `services/api/app/infrastructure/authoring_repository.py:173` still belongs to the backend publication owner and must supply the true current state/reference. This slice deliberately supplies no implicit null default or fake published implementation. The backend owner was sent this commit/interface. Full backend integration, the four excluded transport/storage contract files, actual HTTP publication, browser acceptance, physical numeric execution and academic/source approval were NOT_RUN by this agent for this slice. Passing model/generated/frontend checks does not establish that publication is implemented.
