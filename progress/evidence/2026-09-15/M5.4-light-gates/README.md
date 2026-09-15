# M5.4 five actual static gates

Ruff whole repository, Mypy 148 sources, verify_spec, web lint and web typecheck were each actually run and returned exit 0. All five recorded the same 841 non-progress Git cached/untracked nonignored inputs before and after. No build, web test suite, full Python suite or native suite was run by this driver.

The actual execution HEAD was 70b0278 with these implementation changes not yet committed. The preserved 841 input list later matches checkpoint 1c2a286b byte-for-byte; light-checkpoint-readback.json is a post-run read-only comparison, not a claim that the commands originally ran at 1c or current 64b. Its scope does not include the later parser changes. The ten identical source-before/source-after originals are represented once with ten explicit aliases.

Only literal private-home-prefix normalization is applied, with source-prefix SHA, private mapping-receipt SHA, replacement and occurrence count in the manifest. Original files remain unchanged. Logs retain all outcomes, warnings and any ANSI; this is not redaction of a failure. Raw original SHA/byte count and public SHA/byte count are recorded for every payload. No DB, user material, credentials, third-party source, source-tree mirror or PNG is included.

source-map.json resolves multiple original before/after logical names to exact-byte-identical shared source payloads. Existing receipt hashes always refer to the original raw bytes, even when a path prefix in the receipt was normalized. Private normalized source paths identify provenance; they are not package-relative links. Full source inventories contain hashes and names only.

Aggregate: sort entries by path, project each to {path,sha256:public_sha256}, then SHA256 of UTF-8 json.dumps with sort_keys=True, separators=(',', ':'), default ensure_ascii=True, no newline. manifest.json and publication-scan.json are metadata outside that aggregate. Every file, including those two, passed the repository publication inspector at its proposed public path. Manual provenance scope remains necessary.
