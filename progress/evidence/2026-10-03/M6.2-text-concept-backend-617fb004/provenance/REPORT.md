# Explicit backend share membership

This separate derivative directory leaves the sealed 617fb004 backend evidence untouched. All 52 entries in its original SHA256SUMS were checked against actual original bytes: exactly the 51 MANIFEST.files entries plus MANIFEST.json. The original SHA256SUMS hash is recorded separately; it is not silently added as a 53rd payload entry. Nested legacy-v2-capture, temporary databases/caches, runtime files and unlisted diagnostics are excluded.

SAFE_SHARE.json is the explicit 52-file allowlist. Candidate files are under safe-share/ with identical relative paths. Only exact $HOME and $RUNNER_HOME prefixes change, to <LOCAL_HOME> and <RUNNER_HOME>; every raw and candidate SHA/length is recorded. Original nested hash inventories continue to identify original bytes; SAFE_SHARE_MANIFEST.json provides the derivative mapping. No extra evidence or test outcome is invented.

Repository path/credential scan plus anchored header assignment and recursive JSON field-name checks passed on the candidates. Raw personal-prefix findings are retained as FAIL in SCAN.json; only path/rule/field names, not matched values, are recorded. This bounded scan supplements original synthetic provenance; it is not a universal privacy guarantee. Files remain private until root explicitly copies the reviewed allowlist.

Backend source/result boundaries remain those of the unchanged source report: 280 related Python tests, 16 new HTTP and 12 representation cases included, Ruff/mypy PASS; 1318 complete non-progress inputs. Old oracle parse/hash/canonical/ACK rendering is not reopening an old capture DB. Native/UI/independent/full-gate evidence is separately source-bound.
