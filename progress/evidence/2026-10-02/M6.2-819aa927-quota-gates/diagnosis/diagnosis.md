# Fixed 819 Python retry diagnosis

The confirmed environmental cause is the current user's exhausted block quota on `/tmp`, not a full filesystem or inode exhaustion. The 222 unsuccessful cases have five observable failure mechanisms; no additional independent product failure has been established in this log. Fifteen representative original failures pass with only temporary storage relocated. That sample does not establish all 222 repaired. The full unchanged 3295-case gate is running separately and root owns its session polling.

Fixed source: `819aa927a58bc95ac45ac317b73dd2cb6938ee0e`, `$HOME/.cache/learning-workbench-acceptance/m62-combined-gate-819aa927`.
Original log: `$HOME/.cache/learning-workbench-acceptance/m62-combined-gate-evidence-819aa927/full-python-complete-retry/run.log`.
Original SHA-256 remains `9e7b74a8de55dd4b4d048c47c6d4b73d76ff2347ce26f5e553540e8f8d41cf68` (1,611,256 bytes, 17,105 lines). Original receipt reports 1156 unchanged inputs. Original result remains **130 FAIL / 3072 PASS / 1 SKIP / 92 ERROR**, exit 1, 1274.49 seconds. No files were removed or source files edited for this diagnosis.

## All unsuccessful cases accounted for

`all-222-failure-map.tsv` maps every complete pytest node ID to its exact original log block and terminal line; `failure-blocks.json` retains each block's exception lines. The long parameterized byte cases remain complete in the TSV. Group counts sum to all 222 with no unclassified case.

| Mechanism | FAIL | ERROR | Exact original line evidence | Interpretation and validation |
| --- | ---: | ---: | --- | --- |
| SQLite `disk I/O error` | 43 | 92 | First setup: 48–80, exception 78; following WAL connection: 81–124, exception 122 | One exhaustion event cascades through subsequent fixtures and actual tests. A minimal real `Database.initialize()` probe reproduces `SQLITE_IOERR_WRITE` (extended code 778) on `/tmp` and succeeds on ext4. Representative original Tutor setup passes after relocation. |
| Direct `OSError: [Errno 122] Disk quota exceeded` | 38 | 0 | Static serving fixture 10989–11020, exception 11018; source extraction blocks 16549–16870 | Direct kernel EDQUOT from unrelated file writes, including synthetic sandbox entry scripts and fixture material. Real 4096-byte write reproduces EDQUOT on `/tmp`; identical ext4 write succeeds. |
| Blob storage 503 and downstream expectations | 29 | 0 | Initial raw-byte write 12197–12265, exception 12263; budget assertion 12759–12792; hash mismatch 12857–12879; failed publication flag 13777–13804; race expectation 13805–13837 | Sanitized `BLOB_STORAGE_UNAVAILABLE` masks storage failure. The minimal real BlobStore probe preserves the Python exception context and finds EDQUOT underneath; ext4 succeeds. Samples cover successful round-trip, expected hash classification, post-rename sync state, and three FD child-process variants. |
| Synthetic secret-store 503 and child exit expectations | 17 | 0 | Initialization 15125–15181, exception 15179; early child exits 15763–15797; recovery examples 15798–16235 | Owner code sanitizes OSError to `PROVIDER_SECRET_UNAVAILABLE`; crash-point expectations fail before their intended point. Original synthetic-store initialization and both crash-recovery variants pass after relocation. This is a sampled causal inference for the group, not a claim that all 17 were individually rerun. No user/provider keys were inspected. |
| TLS PEM parsing | 3 | 0 | 11653–11718, exceptions 11672, 11694, 11716 | The six original synthetic certificate/key files have stat size 0. Only stat metadata was inspected; no PEM contents read. All three original TLS variants pass after relocation. The successful openssl process status in the original trace did not establish nonempty output files. |
| **Total** | **130** | **92** | 222 complete block-to-node mappings | Full-gate conclusion remains pending. |

The two warnings (16871–16878) are existing FastAPI/Starlette deprecations, not failures. The one skip at 16882 is the existing sealed numeric-runtime environment branch (`BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained`). No skip rule was changed and no numerical-quality success is inferred.

## Resource proof

`storage-probe.json` records df, inode, mount and read-only `quotactl_fd(Q_GETQUOTA)` observations before the isolated full run. `/tmp` is a tmpfs mounted with `usrquota`:

- User hard and soft block limits: 12,688,844 KiB = **12,993,376,256 bytes**.
- User current charged bytes: **12,993,376,256**, exactly the limit.
- User inode limits: 0 (no quota limit); approximately 784,294 filesystem inodes still free.
- `df` still reports about 3.1 GiB globally free; global free space does not override the user's block quota.
- 4096-byte new write to `/tmp`: errno 122; identical write on the ext4 evidence filesystem: 4096 bytes plus fsync PASS.
- Ext4 reports about 514 GiB free and no active user quota result (Q_GETQUOTA returned ESRCH).

`owner-io-probe.json` records matching real Database and BlobStore failures on `/tmp` and successes on ext4. Generated probe files remain in their dedicated paths. Two invalid external harness attempts are retained: a wrong Settings import failed before any operation; a missing BlobStore root caused ENOENT on both filesystems and was explicitly discarded as a causal comparison. The corrected probe passes an existing root, matching the production contract. These harness failures did not alter repository source.

`quota-diagnosis-end.json` is a second read-only snapshot at 10:36:53 UTC: `/tmp` remains exactly at the same user byte limit while ext4 still has 550,793,670,656 available bytes. The sample succeeded while the original failure condition persisted on `/tmp`.

Root can record the full-run endpoint without touching existing evidence:

```sh
python3 $HOME/.cache/learning-workbench-acceptance/m62-python-retry-diagnosis-oct02/quota_snapshot.py $HOME/.cache/learning-workbench-acceptance/m62-python-retry-diagnosis-oct02/quota-after-full.json
```

The script refuses to overwrite an existing destination and only queries quota/statvfs metadata. It prints no environment or file bytes.

## Isolated sample and full rerun

The sample command is recorded exactly in `sample-invocation.json`; its official capture is `../m62-combined-gate-evidence-819aa927/quota-isolated-sample/`. Result: **15 PASS**, 2.20 seconds, exit 0, **1156 inputs unchanged**. `sample-15-case-map.json` binds all 15 expanded cases to the original failure groups and line ranges. It uses actual existing tests, synthetic fixtures and local loopback only.

The approved full rerun was started through the existing unchanged capture.py as stage `full-python-quota-isolated`, session **17326**. Root now owns all polling. Command:

```sh
env TMPDIR=$HOME/.cache/m62-qf-tmp-1002 uv run --frozen pytest -q --basetemp=$HOME/.cache/learning-workbench-acceptance/m62-combined-gate-evidence-819aa927/full-python-quota-isolated/pytest-tmp
```

Both the short ext4 TMPDIR and the basetemp target were verified absent before launch; no preexisting directory was passed for pytest to clear. The full command changes only TMPDIR and basetemp relative to the original. No selection, source, timeout, dependency or skip changes. The expected fixed-source collection remains 3295; the actual final receipt must settle collection and result.

`temp-helper-scan.json` preserves the complete targeted scan: host helper temporary writes use pytest tmp_path or tempfile, so TMPDIR/basetemp cover them. Backup staging explicitly uses its supplied destination. The remaining literal `/tmp` entries are sandbox-internal directory/tmpfs mounts or log path redaction, not host temporary-write paths. No automatic `/tmp` cleanup is proposed.

## Evidence and boundary

`fixed-tree-status.json` confirms the fixed tree remains clean; `diagnosis-readback.json` verifies the original failure log hash unchanged. `manifest.json` lists only explicit diagnostic reports/scripts/maps and official log/receipt metadata. It deliberately excludes all temporary test directories and generated PEM/private-store files; those files are not read for hashing. Full-rerun logs and its future receipt are separate evolving evidence and are not prematurely frozen into this diagnostic manifest.
