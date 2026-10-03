# Exact block revision comparison: bounded implementation evidence

This package records candidate `05aa1af2fd000654b0d7b62e5eae32998c81d43f`, based on `833f0a84168638ba5ce421c70cd2f20a71e45e48`, plus both independent reviews. It does not itself claim the candidate was merged or published. The known public reconstruction base is `fb16dcc3857830acc22677f83dbd285701bea202`; every source blob unavailable at that public base is included byte-for-byte in source-cas, including development variants. No unpublished commit is required to reconstruct the tested bytes.

The Reader feature explicitly selects two real historical revisions and checks exact identity/metadata/body hashes using existing GETs. It reports literal field/line differences; it does not infer semantic equivalence, review approval, restore, impact completion or new content publication. The original owner REPORT and TASK_RECEIPT preserve all boundaries. Independent reports remain independent statements; their authors did not rerun the owner's product gates.

All 21 actual stage logs, receipts and input sets are preserved, including missing-feature REDs, the two integrity failures, role/current-Policy failures, query-order/type fixture failures and first native locator failure. The controlled same-DOM locator probe is separate from product acceptance. The final native test passed after four exact-role locator lines changed, with unchanged product source, 30-second timeout, retry=0 and assertions. Fixed Reader 62 PASS/build/spec ran at b20; only the native case ran at final 05aa. This is not the full test suite or real provider/mathematical/teaching acceptance.

`manifest.json` accounts for every member of the three original evidence manifests plus those manifests themselves. File mappings record original hash/size and exact replacement byte spans; only local/CI filesystem path aliases are applied. No log line is omitted. `input-map.json` reconstructs each original before/after input JSON byte-for-byte from one complete baseline and exact per-snapshot changes. `source-map.json` reconstructs all source-pool bytes from known public Git or included unmodified CAS files. Original source copies in owner/reviewer bundles reuse those same byte bindings. Native runtime databases, blobs and secret material were already outside the frozen owner evidence manifest and are never read or included here.

All four original PNGs remain unmodified and hash-bound. The desktop nested-scroll locator capture includes a long unpainted region; it is not evidence of a complete desktop document review. Narrow screenshots and the actual desktop/narrow container assertions have their stated scope. The original first-native failed PNG is also retained. An inline Playwright diagnostic attachment was not persisted by the default reporter; the package does not invent a file for it.

Verify published files and original input reconstruction:

```sh
python verify.py
```

Verify known public Git source bytes too (repository must contain the known public base):

```sh
python verify.py --git-repo /path/to/repository
```

With private original caches available, replay every original byte span and source/input reconstruction:

```sh
python verify.py --git-repo /path/to/repository --raw-base /path/to/private/cache
```

`PUBLICATION_SCAN.json` binds the existing unchanged repository scanner. No scanner exception, rule relaxation or hidden runtime artifact is used. This package is a source/evidence handoff; it does not replace the parent repository's final staged/history publication checks.

Version 2 changes only the public container names of five captured diff logs to `*.diff.log`: implementation, native-locator-only, metadata-integrity, role-change and displayed-policy. Their bytes, including necessary diff context whitespace, are unchanged. Original raw names stay in the mappings; public paths follow the name-only mapping. The frozen version 1 package is unchanged.
