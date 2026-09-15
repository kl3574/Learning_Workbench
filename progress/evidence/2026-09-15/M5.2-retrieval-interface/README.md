# M5.2 retrieval HTTP and generation development evidence

Sole specification: PRODUCT_DESIGN.md 3.0.3. This is scoped development evidence, not full stage acceptance, benchmark quality, browser testing or any provider call.

- Same 8 DTO counterexamples: 8 FAIL (missing relationship checks) then 8 PASS after the owner repair. Later expanded DTO set: 28 PASS.
- Same 5 generator tests: 5 FAIL (unsupported actual response union and new binding absent), then 5 PASS. Expanded 19 include actual TypeScript compilation/execution and mutated runtime declarations failing closed.
- HTTP first and second rounds each had 1 FAIL / 19 PASS due to test harness errors: incorrect authenticate argument, then an assumed 422 where CAPABILITY_UNSUPPORTED correctly returned 409. These are not implementation RED evidence. Fixed HTTP: 20 PASS.
- Final selected DTO/generation/HTTP and existing projection/transport/upload regression: 160 PASS, 2 retained dependency deprecation warnings, 64.34 seconds. Its listed 11 source inputs were unchanged before/after.
- Scoped Ruff and mypy passed; generated check passed: 70 artifacts, 73 actual registered handlers; 54 core models unchanged.

GET scope_refs is a scalar strict JSON URL field, exclusive with overview pagination. POST query requires session/CSRF and no idempotency key; rebuild returns 202 with a single original key. Internal Content Pydantic models bind bytes to Uint8Array in separate internal artifacts, not fabricated HTTP components. Main composition only added the retrieval router import/registration.

Only module-ports.ts was extracted. The other five embedded sources were unchanged across immutable parent f0b4ce2 and the live specification. generate_fixtures.py had an existing engineering evolution that was already present in that parent and was preserved.

Limitations: the first two HTTP run receipts omitted the new HTTP test from their source lists; original logs remain, but no contemporaneous complete HTTP test snapshot is claimed for those two rounds. The final HTTP and combined runs capture it. Source archives are .txt and are exact contemporaneous copies apart from any declared private-home prefix replacement. Original evidence remains in private cache. No original record was changed.

The manifest includes each original/public byte count and SHA-256. The payload aggregate is SHA-256 of UTF-8 JSON encoding of the path-sorted array of {path,sha256,size} using sort_keys=True, ensure_ascii=False, separators=(",",":"); it excludes manifest.json. Public scan applies to the complete package and does not inspect private provider credentials or diagnostics.
