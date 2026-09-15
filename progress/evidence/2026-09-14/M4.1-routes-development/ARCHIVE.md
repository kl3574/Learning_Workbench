# Archive paths

Python source snapshots and independent probes in this evidence package use a `.py.txt` archival suffix. Their bodies are byte-identical to the previously reviewed public payloads, including any historical formatting or test-fixture diagnostics. `ARCHIVE_PATHS.json` maps every original logical filename to its current archive filename and SHA256.

Original producer manifests, summaries and checks were kept byte-for-byte; they describe the pre-archive layout. Resolve their paths with this explicit map when checking their hashes. All original files remain available. The extra suffix prevents evidence snapshots from becoming current project Python modules. It does not exempt current implementation or permanent tests from any gate. To replay a retained probe, copy its verified bytes to a temporary `.py` file and use the recorded repository/pytest setup. No tests or assertions changed during this archive step.
