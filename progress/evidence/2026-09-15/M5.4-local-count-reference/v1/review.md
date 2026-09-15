# M5.4 first bounded offline audit result

Status: acquisition incomplete; official full-request token counting NOT_RUN.
No production files, virtual environment, proof registry, credentials or model APIs were used or modified. This is local preparation, not M5.4 acceptance or hosted InputProof.

The current sole spec is PRODUCT_DESIGN 3.0.5, SHA256 `2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37`. Both live copies were read back with this hash. Fixed official recipe source commit remains `8cadfede7063c896b944e7bae05daa3549ae97ea`; the earlier 83-file acquisition and Git-blob verification are preserved in the sibling m54-v41-offline-audit-material-v1 package. Text conversion, Python entry/bindings, V4.1 renderer and tokenizer entry were reviewed. The full native build/dependency closure was not rebuilt.

## What actually ran

- `rustc --version` and `cargo --version`: executables unavailable. Rust build NOT_RUN. Official pinned Rust manifest was fetched; no toolchain installed.
- Official PyPI metadata for `deepseek-recipe==0.1.1` was fetched and hashed. Required wheel is `deepseek_recipe-0.1.1-cp310-abi3-manylinux_2_28_x86_64.whl`, 11,367,229 bytes, expected SHA256 `7818802935becc76ac9b81af6b4a1e5390ec65355cecefd1fd4790f51845c1c5`.
- Original proxied GET was interrupted at the declared, once-extended total deadline, exit 130, KeyboardInterrupt in SSL response reading. Its exact body count was unavailable because the initial downloader buffered the entire response before returning; `/proc` total read counters must not be called HTTP body counts. This is a downloader observability limitation, retained in download-deadline-receipt.json. The original traceback is in tool session 84244, not an invented disk raw log.
- Explicit direct GET of the same official URL returned HTTP 200, received 655,360 bytes, then the per-chunk total-deadline check raised TimeoutError at 81 seconds. Partial bytes and each chunk observation are retained. The script process exited 0 while its receipt records failure; exit 0 is not download success.
- Last attempt requested 16 exact ranges from the same URL with Content-Range/length checks and a 180-second bound. Nine ranges completed, seven failed (two TLS handshake timeouts and five body-read timeouts). Total received across ranges: 7,475,846 bytes. The aggregate script exited 0 but records FAIL because all 16 ranges were not complete. Partial ranges are not a valid wheel; no binary SHA or wheel/source build equivalence is claimed.
- A separate authored narrow renderer ran in `bwrap --unshare-all --clearenv` with readonly public audit/source/Python mounts and one writable output directory. Actual namespace showed only loopback, zero traffic, no `/home`; no credential directory was mounted. It rendered 13 synthetic requests, rejected 15 audit-admission counterexamples, and checked three explicit Unicode/adjacent-user vectors. The 32 authored input files were identical before/after. This execution did NOT import the official wheel, execute Rust, or count tokens.

## Replayable audit entry

`cases-manifest.json` froze 28 raw synthetic JSON bodies before any attempted encoder invocation. `audit.py` is the prepared full count harness; `run_audit.py` is its reviewed sandbox launcher. They have not run, because a complete hash-verified wheel is missing. `narrow.py`/`run_narrow.py` and `narrow-01` are the separate actually executed source-derived fallback. The two entry points must not be conflated.

Once a complete wheel is available, the required next steps are: verify total fixed SHA, extract with the recorded path/size rules, read WHEEL/METADATA/RECORD and Python entry bytes, inspect ELF NEEDED/RPATH via readelf, record native SHA and actual dependencies, then run the frozen full harness under the same isolated mount/clearenv policy. Check V4.1 and Responses APIs actually exist; no fallback to an older model. No new download route is attempted in this first result. Existing valid ranges may be reused only after full final SHA verification in a separately authorized continuation.

## Seven boundary groups

1. Complete conversion, template overhead and stable token IDs: prepared 13 positive bodies including system/user/history and 6 base + 8 reference messages; official conversion/count NOT_RUN. Counts are null, not zero.
2. Unicode, NFC/non-NFC, whitespace, CRLF, mathematical text: raw bodies and source-derived prompts preserved; three narrow manual vectors passed. Official tokenizer behavior still NOT_RUN.
3. Message, history and reference boundaries: source-derived adjacent assistant/user normalization and V4.1 mid-system handling are explicit. The audit's 14-message/12,000-codepoint caps are coarse audit limits, not proof of the production Context owner contract.
4. Closed request shape: 15 malformed/unsupported bodies actually rejected by this audit's own admission function. This is not a production Provider admission test. Missing `reasoning.effort=none`, tools, image/typed content, unknown fields, duplicate keys, nonfinite/bool counts and over-budget shapes are included.
5. Tokenizer/template pins: official tokenizer SHA `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99` is fixed. Missing/wrong tokenizer, V4-vs-V4.1 template and permissive-converter controls are prepared but NOT_RUN against the unavailable wheel.
6. Capacity, exact endpoint and registry invalidation: NOT_RUN here; these are the separate product-owner task. No arbitrary capacity or fixed margin is called a bound.
7. Hosted alias/deployment/template equivalence: UNPROVEN. Neither locally successful counts nor a PyPI version would establish that `deepseek-flash` at an actual endpoint uses the identical deployed request conversion/tokenizer. No vendor request, usage comparison, model weight or key was used.

The wheel is an official project distribution linked by the pinned project's installation instructions, but reproducible binary equivalence to the fixed 83-source snapshot would remain unproved even after download. Root and tokenizer MIT notices and the Python third-party license notice are retained in the original source bundle; this is not a legal certification.

Official public references (accessed 2026-09-15): [fixed recipe](https://github.com/deepseek-ai/deepseek-recipe/tree/8cadfede7063c896b944e7bae05daa3549ae97ea), [fixed tokenizer documentation](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/docs/tokenizer.md), [V4.1 tokenizer provenance](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/static/tokenizers/README.md), [fixed Python package metadata](https://pypi.org/pypi/deepseek-recipe/0.1.1/json).
