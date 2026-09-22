# Independent backend review: frozen pre-fix public evidence

One blocking history-verification gap was confirmed in the uncommitted M6.1 group backend at HEAD `bebf80601b3debf788d446ed2b3abf0847b392bc`, PRODUCT_DESIGN 3.0.7 SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`. This package preserves the reviewed pre-fix files, not a later worktree or a completed fix.

Read [REVIEW.md](REVIEW.md) for the concrete finding and bounded static review. [probe-result.json](probe-result.json) and [probe.log](probe.log) show that a deliberately damaged original synthetic Provider artifact makes protected draft read fail, while exact-member numeric preview, explicit approval and original worker admission still succeed. The single reproduction stopped at admission; no calculator was executed. It used one complete-byte test-only HTTP response on an ephemeral loopback port. There was no vendor, browser, CI, remote write, timeout change or product-source edit.

The allowlist contains all 32 declared before/after file snapshots, plus 12 end-only read/dependency snapshots. One end-only file duplicates a declared source; the categories and original fingerprints are retained exactly. The 32-file equality is not a whole-tree stability claim, and end-only files are not asserted stable before the reproduction. This package does not provide the complete transitive runtime dependency environment or new test-suite acceptance.

`inputs-before.json` and `inputs-after.json` record the original SHA values. `source-before/` and `source-end-only/` contain source derivatives. `raw-origin-map.json` binds every derived file to its exact original relative path, SHA, size and HOME substitution count. `original-review-manifest.json` is the frozen private review receipt, preserved as provenance. Its statement that the original directory was not public still describes that original directory; this explicit allowlist is the public derivative.

The only content transformation is the local HOME prefix to `<HOME>`. No actual sensitive value was found in the selected source/result/log allowlist, so zero sensitive-value redactions were applied. Literal synthetic fixture keys remain test source, not live credentials. All `probe-data/`, SQLite/DB state, session state and credential-store files are excluded and were not opened by the exporter or verifier. No private state should be copied when importing this package. The probe source is a review artifact: restore the local root prefix only in a separate cache copy before any separately authorized reproduction, and use a fresh evidence directory. Verification itself never executes it.

Public integrity verification:

```sh
python3 -B verify.py
```

The holder of the original private evidence may additionally verify every original fingerprint and exact HOME-only derivation, without opening excluded state:

```sh
python3 -B verify.py --raw-base "${HOME}/.cache/learning-workbench-acceptance/m61-group-backend-independent-review-v1" --raw-home "${HOME}"
```

`manifest.json` hashes every public payload file and declares their exact set; its own SHA is reported by the verifier and supplied separately at handoff. The aggregate is SHA256 of sorted `sha256 + two spaces + relative path + newline` entries. Strict verification rejects unlisted/missing files, symlinks, raw HOME prefixes and database/archive payload extensions, and checks the 32/12 source claims, original review receipt and diagnostic result. The source fingerprints and diagnostic result are provenance evidence; they do not establish native acceptance, race freedom, numerical PASS, model quality, CI causality or complete M6.1 delivery.
