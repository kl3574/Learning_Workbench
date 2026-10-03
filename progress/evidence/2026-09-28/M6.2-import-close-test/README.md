# Review Import close: bounded test repair and independent reviews

This package binds the one-test-file candidate `36b501cf8da071909fbb5628b7354de70d5d1825`, based on public `a944ebfbdb835a731393977a606db5b473846e98`. It includes the owner's complete eight-stage diagnosis plus independent Standards and root Spec records. Reviewers did not rerun the product tests. No production close guard, timeout, retry setting, generated contract, provider or API behavior changed.

The unchanged original case passed once locally (01); the remote push failure remains an actual failure. A real publication-ledger load barrier caused the original immediate disabled discard click to be ignored and the original null assertion to fail (02). Moving the one click after the same button became enabled passed (03). This is a supported mechanism, not a proven unique explanation of the remote run, which has no click-time disabled-state trace.

Stage 04 is a different, preserved 2 PASS / 1 FAIL: its new no-dirty probe closed before a confirmation appeared. It did not enter a reason or issue a write. A parent notification window is plausible, but its internal ordering was not traced; loss of unpersisted data was not demonstrated. The later dirty-form regression does not fix or settle that observation. Neither independent review treats it as resolved.

The final original test waits for an editable reason and enabled discard before its single explicit click, keeping all reason/close/no-write assertions. The new regression uses real Shell/Import/Review/Publication and the production ledger implementation over fake-indexeddb; the gated load delegates to the original method and its spy is restored. It preserves an actual dirty reason through disabled click, load completion without auto-close, then a new explicit enabled click. This is component/persistence coverage with synthetic HTTP fixtures, not a real browser or HTTP end-to-end claim.

All stages remain present: 01 original PASS, 02 controlled RED, 03 control PASS, 04 distinct-scope FAIL, 05 strict check on that source, 06 dirty guard 3 PASS, 07 final related 49 PASS / 9 files and 08 final strict TypeScript PASS. Final stages each bind 1,040 exact inputs. The original a944 CI frontend log is included completely with only exact path aliases, independently replayable even when also present in the separate a944 CI package. No later PASS reclassifies the historical CI failure.

Every member of the owner's 1,089-member manifest and the independent Standards 24-member manifest, both manifests, and the root standalone Spec JSON is mapped. `input-map.json` reconstructs every original before/after JSON exactly; `source-map.json` binds every source-pool byte to known public a944 Git or an included unchanged historical CAS variant. The final candidate need not be published to reconstruct tested bytes. Actual recorded Git match/mismatch claims are also verified against that fixed base and the exact final changed-file override.

Only exact local/CI filesystem path spans are substituted in captured evidence. Source CAS bytes and complete failure assertions are not rewritten. Captured diff containers use `*.diff.log` so required context whitespace is retained. Raw hashes in original receipts still name raw originals; the outer manifest binds derivatives and deduplicated paths. No original manifest member or log line is excluded. Temporary diagnostic source is retained as evidence, not added to product source.

Replay public hashes and input reconstruction:

```sh
python verify.py
```

With the fixed public base in a repository and private caches available, verify all original hashes/spans, source bytes and recorded Git claims:

```sh
python verify.py --git-repo /path/to/repository --raw-base /path/to/private/cache-parent
```

The unchanged publication scanner and supplemental session/CSRF/authentication checks apply without exceptions. Packaging performs no product rerun, network action, main/progress/remote edit or secret handling. Parent final staging/history checks and publication remain separate.
