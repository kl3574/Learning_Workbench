# M6.3 old ordinary Import stage oracle

Captured by an actual HTTP POST and exact-key replay on fixed `80d18a93221058f63519d793dbb32d218980afee`, before the new Codex Import port. The only controlled replacement was Import's ID allocator to the declared `*_legacy_oracle` synthetic IDs; actual HTTP routing, parsing of the upload, owner staging, raw source/input JSON and ACK serialization ran normally. Input material is original synthetic text. No database, authorization values, headers or cookies are included.

This is an oracle for original stage metadata, input JSON, source hash and HTTP ACK bytes, not a complete old database backup/reopen or old post-publication receipt oracle. The capture's first external-test invocation lacked repository pytest configuration and failed collection; the same probe with `-c pyproject.toml` passed. Both logs remain in private evidence.
