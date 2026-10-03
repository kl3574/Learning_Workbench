# M6.2 Review Jobs lifecycle evidence

This package preserves the completed local development and independent review of the internal Review Jobs adapter. It does not establish a Review worker, HTTP route, Quality history repository, human approval, publication, or overall M6.2 completion.

The sole product and engineering specification is PRODUCT_DESIGN 3.0.7, SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`.

| Actual code commit | Preserved evidence |
|---|---|
| `5fefa4e9c5374306a3bd7bfbf8fd5b7e935615c1` | Original 35 new tests PASS, 50 related tests PASS, Ruff PASS, mypy PASS over 186 files. Independent probes subsequently exposed transaction and wrong-consumer write defects. |
| `abab63eaf32a219694384e29362114b0e25fb598` | Permanent regression cases added without the product repair: 7 FAIL, 17 deselected. Full original 111,782-byte failure log is represented with raw/public hashes and precise path transformation counts. |
| `d419562f7ec26c7919e9fa12973b4b8cf30bbac1` | Repair: 7 regression cases GREEN, all 42 new tests PASS, 50 related tests PASS, Ruff PASS, mypy PASS over 186 files. Independent review found no remaining blocker within this internal slice. |

Counts are not additive coverage: the seven GREEN cases are included in the 42 new tests; the earlier 35 and repeated 50-case gates remain historical executions. The two original issues and their failed checks remain visible. Separate independent temporary SQLite probes confirmed both original defects and their repaired behavior, including preserving the caller's surrounding transaction and keeping the old Authoring consumer unchanged. The first independent harness failed during fixture setup because it lacked a multiprocessing main guard; no Review probe ran in that failed attempt. Its record states that raw output was not saved, rather than inventing an artifact.

The source parent of the first implementation is `acb9e220deeaf1da7ee89ec6fda8bae9c21ca918`. This package retains each actual code version's six changed-file snapshots, the complete initial/final diffs and repair diff, and source inventories. All 959 actual non-progress Git blobs were checked at each of the three code commits against the original gate inventories. Their full source body collection is deliberately not duplicated here. A later cherry-pick has a different commit identity and requires its own integration binding; no later root commit or root-wide gate is claimed by this package.

There are exactly ten completed gate stages (four original, one RED, five final) and three retained runners. Every file in those directories is included, together with all 87 entries from the independent review manifest and that original manifest. Identical bytes are stored once with exact alias mappings; follow `manifest.json`, not an assumed filename for a deduplicated artifact. Original `.patch` files are represented as `.patch.log` for evidence browsing; the mapping preserves the original path and hashes.

The raw originals remain private. Every selected raw text file, including the RED log, was checked for synthetic session identifiers/fragments, CSRF values (including truncated field labels), session cookies, Bearer values and secret-field values. No such matches were found; sensitive-value redaction count and exceptions are both zero. The only transforms are ordered substitution of the parameterized local home, CI home and pytest user-root prefix. Original failure text, exits, receipts and counts are not rewritten. Every alias records raw/public bytes, SHA-256, transformation counts and the transformed flag. The repository publication scanner was executed against each actual proposed public target with no exemptions.

`verify.py` verifies every public artifact and the canonical aggregate. Its optional raw replay requires the private evidence base and home-prefix parameters:

```sh
python -B verify.py
python -B verify.py --raw-base "$PRIVATE_EVIDENCE_BASE" --raw-home "$PRIVATE_HOME_PREFIX" --ci-home "$CI_HOME_PREFIX"
```

The second form reopens all private raw files, checks their original hashes, repeats every ordered transformation and compares the exact resulting public bytes and transformation counts. It does not execute archived runners, tests or source files, and performs no network request. `raw-validation.json` records the original manifest, actual Git binding, gate outcomes and scan scope. `raw-inventory.json` lists the 131 selected raw aliases. The public manifest's aggregate covers all alias records and generated-file pins; the manifest itself must be pinned externally to prevent substitution of the entire evidence package.

This internal adapter still requires a future Quality owner to authenticate current session/role/Policy, candidate/material/numeric history, durable commands and receipts. It creates no ReviewReceipt, does not register draft_review in JobService, and does not perform a model call or a numeric runtime execution. No user key is part of this package.
