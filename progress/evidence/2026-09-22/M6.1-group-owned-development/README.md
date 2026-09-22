# Four bounded Group Authoring evidence stages

This package covers only the independently owned Content target reads, cancellation plus revoked-author recovery, group numeric service/worker tests, and browser command/hook tests. It does not claim finished group generation, full-system acceptance, model answer quality, publication, or a successful numeric calculation on this host.

The stages retain distinct counts and snapshots:

| Stage | Final observed result | Scope and limitations |
| --- | --- | --- |
| Content targets | 44 focused SQLite PASS; Ruff PASS; normal mypy PASS after real dependencies landed | Exact Content-owned target reads only. Earlier setup errors, implementation/fixture failures and missing-import mypy FAIL remain. |
| Cancel plus Policy | 2 real RED variants, then 4 PASS including 2 existing actor/control cases | Actual controlled loopback dispatch, revoked session, safe cancel, recovery without new dispatch/candidate/plan. No live vendor. |
| Group numeric | 24 PASS, Ruff PASS | Service/worker behavior includes quota, original ACK/CAS and restart ledger checks. Actual runtime started and exited 1 with environment_unavailable / BLOCKED. No numeric PASS. |
| Group browser state | 28 PASS + 2 RED, then 42 PASS = 31 new + 11 existing related cases; typecheck PASS | Real IndexedDB and React hooks with controlled API port, current generated schema, selected DTOs from synthetic SQLite tests. No browser E2E claim. A separate earlier parse failure and runner interpreter failure remain. |

These counts are not added into a broader acceptance total. Later checks do not rewrite earlier scope. In particular, numeric initial/final input inventories record concurrent changes; final had 930 before and 931 after, with only the independently added HTTP test changing. Browser RED and final each recorded 937 unchanged inputs. Cancellation and Content stages have their own actual inventories. The verifier derives changes directly from each selected before/after pair and compares them to the original receipt.

`manifest.json` maps every private raw alias to public bytes/SHA, with per-file applied transformation counts. Private cache roots are named relative to an acceptance-cache directory; no database is needed for verification. Repeated identical input inventories share one `snapshots/<sha>.json`, and all original aliases remain individually mapped. Receipt log hashes and source hashes remain the ORIGINAL hash references; use the manifest to find the corresponding public derivative. Runtime receipts likewise preserve raw hashes even if the manifest text underwent the declared HOME replacement.

Only three transformations are allowed, in order: actual temporary session identifiers become `<REDACTED_TEST_SESSION_ID>`; actual CSRF values become `<REDACTED_TEST_CSRF>` while preserving field text (including pytest's truncated `...srf_token`); then the fixed HOME prefix becomes `<LOCAL_HOME>`. Each positive occurrence is counted per raw alias. All other bytes are preserved. Literal synthetic test session strings are harmless fixtures, not exported authenticated sessions. The exact transformation definitions are in the manifest and reproduced by the verifier. No directory is copied wholesale: the builder explicitly selected receipts, logs, input lists, bounded source snapshots, patches, summaries, and the four existing runtime DTO evidence files plus receipt.

All pytest temporary directories/databases, secret stores, actual session values, mypy/pytest caches, archives, storageState and browser profiles are excluded. The scanner checks every payload for forbidden file types/directories, binary NUL, raw HOME, session IDs, CSRF values (including truncated fields), bearer/vendor token forms and private keys. It additionally checked that all sensitive strings identified in raw selected logs were absent from the public payload.

Run `python3 verify_public.py` from this directory to verify public payloads, all source/log hashes, exact inventory changes and the real BLOCKED runtime record. With the private cache available, run `python3 verify_public.py --raw-base /path/to/acceptance-cache --raw-home /path/to/local-home` to hash each original alias and replay all transformations byte-for-byte. The source snapshot is evidence, not an automatically runnable isolated repository. Original commands and timestamps remain in per-run receipts.

No product/test/worktree or GitHub changes were made during packaging. Root must independently review this candidate before importing it.

The predecessor v1 was rejected by the actual repository publication inspector: 34 of 139 files still contained a HOME-shaped placeholder. v1 bytes are retained privately and its rejection record is included here. This v2 changes the HOME replacement to `<LOCAL_HOME>`; all raw evidence aliases and non-HOME transformations remain identical. Invoke `python3 scan_repo.py --repository /path/to/repository --public .` to apply the actual unchanged repository scanner to every public file.

This successor only parameterizes the private prefix: the public manifest declares `raw_home` without its value, and raw replay requires an explicit `--raw-home`. It never infers a user directory. All original evidence payloads, raw hashes and per-alias transformation counts are unchanged. Earlier verification reports remain historical predecessor evidence; the successor is independently replayed and scanned. Stage outcomes and limitations above are unchanged.
