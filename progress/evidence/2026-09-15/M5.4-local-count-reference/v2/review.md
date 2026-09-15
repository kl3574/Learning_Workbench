# M5.4 offline full-request count audit, continuation v2

Result: actual isolated reference execution passed within its declared synthetic text scope. This is not a production InputProof, a hosted-API equivalence guarantee, a reproducible build, or M5.4 model evaluation.

The first result m54-local-count-audit-v1 remains unchanged, including its three download failures and NOT_RUN outcome. Root later completed an independently recorded same-URL range continuation. This v2 independently verified the resulting 11,367,229-byte official wheel SHA256 `7818802935becc76ac9b81af6b4a1e5390ec65355cecefd1fd4790f51845c1c5` before extraction or import. No network download occurred in this v2 task.

## Acquisition and entry checks

All ZIP members passed relative-path, duplicate-name, length, total-size, non-symlink and no-.pth checks. All wheel RECORD entries, hashes and byte lengths matched; RECORD itself uses its prescribed blank digest. Metadata declares deepseek-recipe 0.1.1, Python >=3.10, ABI3 cp310 manylinux_2_28_x86_64 and maturin 1.12.6. There are no runtime Python package requirements; pytest is test-extra only.

The extracted __init__.py and _native.pyi match the fixed official source commit `8cadfede7063c896b944e7bae05daa3549ae97ea` byte-for-byte. Wheel LICENSE and THIRD_PARTY_LICENSES also match their fixed source files. MIT and retained third-party notices apply; no broader legal certification is claimed. The embedded CycloneDX 1.5 SBOM lists 323 components with root deepseek-recipe-python 0.1.0. Runtime module __version__ actually reports 0.1.0, matching the Rust crate version; distribution metadata is 0.1.1. These separate version facts are retained, not collapsed into a claim that the binary was reproducibly built from the fixed snapshot.

Native library: `wheel-inspection/deepseek_recipe/_native.abi3.so`, SHA256 `1461bc4895c188d4ad60ca05eb7bd663aa7fa3286f2ecbebca39ecd73c5b0ec1`. Four ELF files were statically inspected with readelf, not executed via ldd. The extension needs bundled OpenCV core/imgproc/imgcodecs and ordinary libstdc++/libgcc/libpthread/libm/libdl/libc/loader libraries. Its RPATH includes `/opt/opencv-min/lib` and `$ORIGIN/../deepseek_recipe.libs`; the sandbox does not mount `/opt`, and the fresh output directory contains no replacement libraries. All bundled library hashes are in wheel-acquisition.json/elf-inspection.json. The interpreter's actual mapped files after import (17 entries) are recorded separately.

## Actual run and unchanged inputs

`run-01`: 2026-09-15 15:30:13.359462–15:30:13.624519 UTC, child exit 0. Original `audit.py`, `run_audit.py`, all 28 raw cases and cases-manifest.json were copied byte-for-byte from frozen v1. No case, expected behavior or renderer was adjusted after observing counts.

The launcher uses bwrap --unshare-all --clearenv, readonly `/python`, `/wheel`, `/materials`, `/audit` and system library mounts, and a single new writable `/output`. Python is the standalone 3.12.13 interpreter, outside the product venv. The actual environment has only PATH/PYTHONPATH/PYTHONDONTWRITEBYTECODE plus runtime PWD/LC_CTYPE, no `/home`, a separate network namespace with loopback only and zero observed traffic. No credentials or production data were supplied. Neither package installation nor model inference occurred.

4,889 declared source, wheel, harness, fixture, interpreter and selected system inputs match before/after, aggregate `5c8bc8febca4c59ca4aa2b07d1391d8b92cdd42e4b76050172a935223b507f79`. Algorithm is sorted absolute path + NUL + lowercase SHA256 + LF. This is the explicit manifest scope, not a claim to observe every possible host file before execution. Runtime mapped-file hashes are post-import observations and are not retroactively called additional before snapshots.

- 13 positive cases executed official Responses conversion → V4.1 full conversation rendering → attached fixed tokenizer. Every prompt exactly matched the separately authored narrow renderer derived from the fixed source. Complete token IDs matched Tokenizer.encode of that full prompt and a second fresh request conversion. Full prompts, token IDs, repeated IDs and response/count hashes are preserved.
- 15 negative cases actually failed the audit's strict shape admission before conversion. They are audit controls, not production Provider tests and not 15 model/tokenizer calls.
- Four controls exercise actual official behavior: no tokenizer raises RuntimeError; omitted wire reasoning defaults to thinking=true with the effort template; the official converter ignores an unknown top-level field (showing why outer admission is needed); V4 and V4.1 differ for the mid-system case. The fifth initial control only compared a mutated tokenizer digest; it was not alone an executed rejection proof.
- `wrong-pin-02` closes that last boundary using the unchanged original entry and only a mounted tokenizer file with one appended LF. Actual child exit 1 at the tokenizer SHA assertion occurred before native import. This expected negative-control failure and its original log are retained. It does not change the successful run-01.

Representative complete-prompt vs bare-content counts: minimal 18 vs 12; Chinese/math 32 vs 27; exact 12,000 content-codepoint case 12,005 vs 12,000; 6 base + 8 reference messages 755 vs 733. Bare counts are diagnostic examples, not a usable bound or a correction formula. NFC and decomposed inputs both count 7 in these specific cases; raw bytes and token IDs remain separately preserved.

## Remaining limits

The fixed tokenizer is SHA256 `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99`. Only local textual Responses with explicit reasoning.effort=none, no tools/images/structured output, and this renderer/tokenizer was exercised. The audit's 14-message/12,000-codepoint outer limits do not prove the production Context ownership or capacity rules. Endpoint binding, proof withdrawal, budget admission, Provider persistence and model quality are separate product tests; none was run here.

Hosted deepseek-flash alias mapping, hidden preprocessing and exact deployed template/tokenizer equivalence remain unproven. No vendor API call or billed request was made. The official wheel and tokenizer successfully count the local reference prompt; that fact alone does not satisfy the sole spec's production local_exact/local_upper_bound proof requirement.

Official provenance (materials accessed 2026-09-15): [fixed source](https://github.com/deepseek-ai/deepseek-recipe/tree/8cadfede7063c896b944e7bae05daa3549ae97ea), [fixed tokenizer entry](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/docs/tokenizer.md), [PyPI 0.1.1 metadata](https://pypi.org/pypi/deepseek-recipe/0.1.1/json).
