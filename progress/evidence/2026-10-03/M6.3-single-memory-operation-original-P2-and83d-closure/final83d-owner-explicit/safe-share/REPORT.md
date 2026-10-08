# M6.3 memory operation closure repair

Final clean source `83d7b9164968e314261a3d12f5fb3fc75d2e8c6d`, base `9d3ffb0cebd6df099376ee4de37026e210891b02`. Sole PRODUCT_DESIGN v3.0.15 §20.17.4. Original 9d 209-PASS package remains unchanged. Two production paths changed: codex_operation_profile.py and codex_operation_execution.py; five regression/fixture paths changed. No HTTP/core/DTO/migration or original 351 request profile/execution bytes changed.

## Result and exact scope

- Final related gate: **226 PASS, 2 warnings, 236.32 seconds** (runner 238.537812412 seconds), 14 files. Final focused gate: **55 PASS, 2 warnings, 70.08 seconds**, six files. These overlap and are not additive.
- Final Ruff, mypy (275 source files), generated-contract check (82 artifacts), specification check (54 core models / 147 declared routes / 129 runtime routes), generated TypeScript strict check and committed whitespace check all exit 0.
- All final 1434 tracked nonprogress inputs exactly matched fixed Git before and after. Complete maps are retained. No complete Python/Web/browser gate is claimed by this slice.
- Independent peer static review of 83d7 marked the original P2 CLOSED_STATIC, report SHA256 `e1b7ec2ad6add7e853c0d3880a54b4ee2ed0189fac59772c8c2c0063393d0a46`. That is separate from the author-executed tests here.

## What is now frozen and checked

The opt-in synthetic profile is v2. It binds actual loaded prepare/projection/execute/receipt and JSON/hash function code, nested code objects, defaults and complete strict model schemas. It additionally follows each project's function **own defining-module globals**, rather than a same-named import in the profile module. Actual compiled Pydantic validator and serializer reductions supply their captured project callable, configuration and functools.partial function/arguments/keywords. Captured `_path`, `_nonblank`, `unicode_scalars`→`_unicode`, `unique_files`→`_distinct` and serialization's actual canonical dependency are included. Compiler reference address suffixes are normalized while their qualified reference identity remains.

Python/stdlib and Pydantic/core internals remain explicit trusted runtime libraries with version bindings. This is not arbitrary hostile-Python integrity, OS isolation, shell/file/network approval, or an actual upstream accept implementation. The production registry remains empty. The bounded synthetic memory interpreter did run in the tests. No actual CLI, remote model/account/network, or host tool action was run.

The old v1 profile remains strictly decodable and byte-preserving for historical projection, but cannot become current or be executed by registration. A profile/instance-wrapper change after approval is rejected before a new start/debit. The original checked bound execution callable is retained in the claim transaction. If code changes after the durable claim, that original function refuses the changed profile and the original operation becomes unknown without calling a newly substituted wrapper; its permit/result cannot be erased or replayed.

The old immutable event models/repository/bootstrap ACK decoder are unchanged. The exact old v1 profile/closure/projection/result fixture was produced by the original clean 9d in-memory interpreter and is parsed, reserialized, compared byte-for-byte, projected identically and denied current execution. **This fixture is not a full old database, HTTP ACK capture or OS restart proof.** Existing owner regressions separately verify original ACK, app reconstruction, unknown recovery, concurrent decision, shared tool budget, completed result, late actor loss and no second model request under controlled synthetic peers.

## Preserved failure and gate history

- `closure-red`, 09454f8b: **5 FAIL / 1 PASS**, 1432 exact. Three unit wrapper-change counterexamples and class/instance real HTTP approval→start counterexamples failed the safe expected behavior. Escaped-surrogate handling already passed; no surrogate defect is claimed.
- `closure-green`, 2038d0d8: **16 PASS**, 1432 exact. Original two new RED test files are whole-file byte-identical at this first GREEN.
- `boundary-green`, 63dfdef3: **34 PASS**, but the after-map caught concurrent test additions. **NOT a fixed-source gate.** Full raw maps/receipt/log remain. The later fixed gates repeat applicable cases; they do not overwrite this limitation.
- `final-related`, a9369911: **221 PASS / 1 FAIL**, 1433 exact. The new legacy oracle passed nested BaseModel objects to a JSON-only dictionary serializer. Test-only 3120 explicitly dumps the models before the unchanged exact-byte assertion.
- `final-related-02`, 3120e06c: **222 PASS**, six static checks PASS, 1433 exact. The dependency portion of P2 was still OPEN.
- `dependency-red`, e7f61fdb: **4 FAIL**, 1434 exact. Actual serialization globals, DTO helpers and Pydantic's captured path validator were not yet frozen. This exact test file is unchanged at the final GREEN.
- `dependency-green`, 6e5da6a2: **54 FAIL / 1 PASS**, 1434 exact. The closed walker rejected Pydantic's real max-length-validator partial. 83d7 binds that partial's exact function and arguments; it does not ignore unknown callables.
- Final `dependency-green-02` and `final-related-03`: results above. All failures remain present. Nonformal WIP mypy failures are separately recorded and do not acquire formal source provenance.

The old boundary test file is **not** a whole-file same-byte reversal. Its execute monkeypatch spies/fault replacements themselves changed the newly frozen runtime. Tests now observe only the exact current-thread function call/return, restore the observer in finally, and verify durable start/actual receipt/owner facts. The permitted ordinary test observer is not a host/runtime isolation proof or revival of any earlier interrupted system diagnosis.

## Sharing and verification

Only SAFE_SHARE.json entries are permitted derivative candidates. The sole transformation is the exact ASCII home prefix to `$HOME`. Failed output and the WIP mypy error log remain private with hashes. No database, temporary fixture tree, credential/header, provider configuration or unrelated file is a candidate. PUBLIC_OUTER_ALLOWLIST.json separately enumerates package metadata. VERIFY.py reads fixed Git/evidence only; it runs no product, CLI, DB or remote operation.
