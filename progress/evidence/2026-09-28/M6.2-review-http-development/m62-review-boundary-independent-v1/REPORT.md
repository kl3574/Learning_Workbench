# Review boundary diagnostics: independent read-only review

No blocking finding in commits 70503ede4ec6060fa93d56ca6a9c21ff5db04384 and 0049d4f78d1ab392e0df3f433ac43b420db8572d. Read all three changed files and the actual recorded failure/pass evidence. No tests were rerun.

The three serialization boundaries now reject warnings before malformed candidate/material/request values can be emitted as warning diagnostics. Existing safe ApiError mappings and `from None` remain. Seven real cases cover Import/single/assessment-group material and candidate inputs plus Review Job input; captured warnings, marker-free exception str/repr and unchanged whole-table hashes form the relevant assertions. The original seven failures are warning-output failures, followed by seven passes; two dependency warnings remain separate.

Both stages have 982 unchanged engineering inputs. Every item was independently matched to actual commit Git blob SHA-1 and SHA-256, and original logs were matched to receipt size/hash. Exact source and evidence pins are in review.json. No migration, API contract or permission change is introduced. This bounded review does not certify the developing Review service/worker or complete platform.
