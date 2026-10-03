# M6.2 Content-owned impact snapshot: isolated repair receipt

Source basis: `PRODUCT_DESIGN.md` v3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. This is an internal Content-owner slice only. It does not complete M6.2, create an impact HTTP route, reconcile other owners, approve content, or verify restoration.

The first slice was committed at `00dbe4fadabd259a977cd521dac90559b782eec0` from `e58abaaf4baa5b06d27bd1db1f06c8a13c1c730a`. Its original code and tests remain in Git history. An isolated `git archive` of `00dbe4f` with only the final focused test file copied in produced [red-00dbe4f.txt](red-00dbe4f.txt): three failures for pure concept-ID revision attribution, equal-microsecond historical reconstruction, and a writer crossing a deferred read transaction. This preserves the review's concrete RED counterexamples; the archive was outside the working tree and was not committed.

The repaired tests on the isolated branch produced [green-focused.txt](green-focused.txt): 25 PASS, 2 third-party deprecation warnings. The exact read guards, frozen old/new refs and explicit dependency refs, conservative-only concept candidates, workspace and SHA tamper, missing cited revisions, legacy registration and missing-new-row failure, zero-DML read, historical attempt/grade pins, and note state are exercised there.

The final modified source also passed a wider related Python suite in [green-related.txt](green-related.txt): 505 PASS, 2 third-party deprecation warnings in 151.11 seconds. The command was:

```text
.venv/bin/python -m pytest -q tests/integration/test_content_*.py tests/integration/test_learning_*.py tests/integration/test_notes_learning.py tests/integration/test_recommendation_*.py tests/integration/test_recommendations.py tests/integration/test_assessment_*.py tests/integration/test_grading_queue_isolation.py tests/integration/test_retrieval*.py tests/integration/test_draft_*migration.py tests/unit/test_backend_database.py
```

`.venv/bin/ruff check .` passed. `.venv/bin/mypy` passed on 211 source files. `.venv/bin/python scripts/verify_spec.py` returned structural PASS for v3.0.7, 54 models and 119 routes; its own `product_acceptance` remained `NOT_RUN`. `git diff --check` passed. These checks ran in the isolated worktree without concurrent edit-publication migration `0020`; the eventual combined branch must rerun migration and gates with `0020` followed by this `0021`.

Frozen input SHA-256 values:

| Path | SHA-256 |
| --- | --- |
| `services/api/app/application/content.py` | `807be0c2e481dd0409440fe83f92b608554ff6e15c2f4acd832a74ddabef0479` |
| `services/api/app/application/content_impact.py` | `5a398ca1ce4e5560d156889f4042c5e27ce2caa3d3c2ffc50645fcbf0bc7617` |
| `services/api/app/infrastructure/content_repository.py` | `fd01f981fb87bb61ec67fffdbae0ca0f9967801c9e902b82ebf852210e3d0afb` |
| `migrations/0021_impact_event_snapshots.sql` | `5172b622d0b7440bbdce1958a465e5839f31623a118f9cd38d7b274f42c4fa0a` |
| `tests/integration/test_content_impact_snapshot.py` | `f3972615cd39239946b5764f4518dd89fd1d0172be8949aaf9b67474bcc637b8` |
| `docs/adr/0035-content-impact-event-snapshot.md` | `07657d4f03a2cec33993735edd795252bab2103ad8cf0c40cecebbe01dbc32f2` |
| `red-00dbe4f.txt` | `bc003c6a431ec36a4cf0acb364828bd5259c84594fe1c59f8a4f7bfbdc2afdcf` |
| `green-focused.txt` | `c3c07ce9c9bd5ae7ff945ff1c122c75c3cae0431bb548aacc1ebb2db25c99378` |
| `green-related.txt` | `6dab60b1c641e44026cb712c35515545cd21d6345387de3337b702f147857a45` |

The decision and its limits are in [ADR 0035](../../../../docs/adr/0035-content-impact-event-snapshot.md): `owner_frozen_v1` proves only the transaction-frozen explicit ContentRef closure found through validated rows, not present-day dependency-table integrity or completeness. Pure concept-ID edges are conservative. Pre-migration events remain `legacy_unverified`; an absent new evidence row fails closed. No historical exact edge is manufactured.

Publication preparation on 2026-10-02: the three linked test logs now replace the exact private worktree prefix with `WORKTREE/`; no lines were removed. The table above retains their original raw hashes. Raw/public hashes, byte counts and exact replacement counts are recorded in `../../2026-10-02/M6.2-publication-path-redaction.json`. The original local commits and raw logs remain preserved privately. Only these evidence paths differ between the local and public commit mappings; all product, test and specification bytes are identical. This is a privacy repair, not a test rerun.
