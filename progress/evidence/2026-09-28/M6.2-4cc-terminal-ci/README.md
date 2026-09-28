# 4cc terminal CI evidence

Both actual workflows completed **FAILURE solely in browser**, attempt 1. This package preserves that failure; it does not represent a rerun or fix.

| Source | Run | Actual checkout | Tree |
| --- | --- | --- | --- |
| push | 36386011041 | 4cc4fd5c24fe135186147dfb86d3f071b26f4fb7 | 7014f0f0abfe5f692141415752403922624e10f9 |
| pull_request | 36386016520 | 538bf74da04fac1cdea69cc70e1416d54c5643cd | 7014f0f0abfe5f692141415752403922624e10f9 |

Each source: backend 731 PASS / 2 warnings; integration 1570 PASS / 1 numeric environment SKIP / 2 warnings; frontend 538 PASS in 91 files; spec-contracts 604 PASS / 2 warnings; security scan 12983 files PASS; browser 106 PASS / 1 FAIL. These job scopes overlap; do not sum them into a unique total. Integration took 1703.53 s on push and 898.92 s on PR. The original numeric skip explicitly retains the real sealed-runtime FAIL; it is not a successful numeric execution.

All six fixed APT installations succeeded independently of product tests. Exact dpkg lines bind bubblewrap 0.11.1-1ubuntu0.3, apparmor/libapparmor1 5.0.2-0ubuntu1~26.04.1, libseccomp2 2.6.0-2ubuntu5.

The sole browser failure is the original `tutor.spec.ts:148` case, `:195` completed heading with the original 5000 ms assertion. Both 4cc browser freezes include response 200 and validated/applied answer_delta seq4, with no observed completed event. Original a944 freezes instead had no response on their last SSE requests. Provider/API post-assertion snapshots and Node/browser clocks remain separate. Root cause is **UNKNOWN**; neither the older a944 failures nor three local 4cc synthetic passes supersede these remote failures.

The package includes all 12 complete job-log derivatives, terminal API metadata and acquisition receipts, exact checkout/tree bindings, the retained local finalizer error and correction, bounded failure timeline/report, and all 16 original artifact members including two unchanged PNGs. Both PNGs were inspected during this packaging step and show synthetic original textbook/loopback proposal metadata, with no visible credentials. This was privacy review, not causal or UI acceptance. Earlier copied diagnosis reports retain their original not-yet-viewed / push-in-progress scope; the fresh terminal records supersede only those later-known facts.

The two original ZIP containers are private and hash-bound, with exact GitHub digest and ZIP/member replay. Duplicate older captures, diagnostic helpers and source copies are also explicitly hash-bound exclusions; the complete frozen private originals remain intact. This is not a claim that every private original byte is public. Source pins identify actual public 4cc Git blobs; the terminal package does not retest or invent product implementation.

Included text changes are exact filesystem-path aliases and selected GitHub account attribution string spans only. The 12 job logs keep every original line and use path substitutions only. Raw/public bytes, hashes, offsets, original-span hashes and replacements are in `manifest.json`; all artifact members remain byte-identical. No broad line deletion, image editing or scanner exception is used. The unchanged repository scanner and bounded supplemental identity/CSRF/auth checks cover the public files; provenance review remains necessary for arbitrary prose.

Offline public verification:

```sh
python verify.py
```

Strict original replay, when the private named cache is available under `CACHE_PARENT`:

```sh
python verify.py --raw-base CACHE_PARENT
```

Both commands run no network or product tests. This handoff was prepared locally; it does not by itself prove publication of a later head.
