# Review workflow evidence

Local Review application/worker/report candidate f5c80556a48e348cc6dbdebe6482ff54ad822693.
Seven-file related gate: 234 PASS; Ruff seven files and mypy six files PASS. Independent fixed-source review has no remaining bounded-scope blocker. Earlier e3 196 PASS and all development failures remain distinct. This does not certify HTTP integration, the full suite, publication or complete M6.2.

Development REPORT.md and TASK_RECEIPT.json preserve scope, actual commits, commands, exits, timing and failures. Independent REPORT.md, checkpoint, both Standards reports, verification receipts and fixed e3/f5 source snapshots are included separately.

manifest.json records every original file, its raw hash, public mapping and exact byte replacement spans. All 24 stages retain complete logs/receipts/before-and-after input manifests. Identical bytes are deduplicated; a mapping may reference an earlier identical file. Original hashes in receipts identify raw bytes, which can differ from aliased public logs. No lines, failures, test outcomes, durations or identifiers affecting execution were removed.

Only exact local-home and pytest-root path spans were aliased. No session, CSRF or bootstrap values required transformation in the selected original logs. Every repeated development source snapshot is explicitly excluded with its raw hash/reason; source binding for every tested engineering input and full fixed e3/f5 changed source remain included. No runtime database is included. Read the manifest rather than assuming directory absence means missing evidence.

Run `python verify.py` for public byte verification. Run `python verify.py --raw-base CACHE_PARENT` with the retained private cache parent to recheck every raw file, every exact replacement span, all excluded originals and both complete raw inventories. This replay does not rerun product tests. Publication inspection uses the current repository scripts/check_publication.py inspect function for every file under the recorded logical progress/evidence prefix, with zero exemptions; it supplements manual provenance review.
