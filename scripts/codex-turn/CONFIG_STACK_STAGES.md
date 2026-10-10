# Exact Config152 stack stage diagnosis

The independent branch fix/M6.3-config-stack-stages follows the two actual
single-case stack-overflow failures at e62044e40f45126fd9de73b9a92c30d3ba6d15d3,
run 38032670192, job 114156691390, attempt 1. That minimal RED is not a root cause.

The patch changes only the existing
recorder_refreshes_without_changing_execution_features_or_claiming_missing_history
test in codex-rs/core/src/tools/executed_tool_calls/request_metadata_tests.rs.
It inserts 16 eprintln statements with prefix LW_STACK_STAGE_V1: test entry,
fixture before/after, each refresh and reload before/after, direct and nested
metadata boundaries, repeated refresh, prompt attachment and exit. Stripping
these statements restores the entire original file byte for byte. All
assertions, inputs, loops, test declarations and original data remain.

SDK source changes are declared diagnostic test instrumentation. Original 14
patch assets and their 11 selected applications remain immutable. The original
Config152 manifest, runner, workflow and profile and all four diagnostic-v1
assets retain exact bytes. No boxing, stack override, production repair, 3b
comparison or future owner/materialization candidate is included.

Unchanged parent prepare/provision/locked-fetch stages run first. The diagnosis
checks their actual receipts and original source/normalized 8797-row inventories,
then checks/applies one patch to both trees. Both complete instrumented graphs
and modes must match the new closed manifest; only this test file can differ.
All inherited original135/auth13/Config4 declaration and original-source-pin
checks run before the overlay. Afterward an independent target36 names parser
and the exact 16-statement strip check preserve the complete original target;
the other 8796 source rows remain exact. Inherited original-byte guards are
unchanged and are not applied to the intentionally instrumented file. After
Cargo, both instrumented graphs must remain exact. Full152 and both Clippy
remain NOT_RUN. A diagnostic PASS never upgrades them.

The exact test must independently collect one test. Both single-case trials run
under the original bounded profile even if the first is RED. Only if neither
matches the target stack signature is original36 separately collected and run
once. Running counts, exits, complete footers, individual ok lines and markers
remain separate. A successful instrumented trial requires all 48 dynamic
markers in source order; an aborted trial may retain any valid prefix, including
zero markers. Each trial gets its own command/stdout/stderr receipts.

Markers record observed execution boundaries only. Missing entry cannot
distinguish future construction from first poll. Diagnostics can change frame
layout: no RED with markers is an instrumentation-sensitive observation, not
a fix or causal proof. Cause remains UNDETERMINED. This candidate is NOT_RUN;
production remains NOT_ADMITTED.

Stage candidate v1 was never published or executed. Static review found its
post-overlay call to an inherited original-byte guard would reject the declared
marker changes before Cargo. This v2 corrects the order and uses the independent
post-overlay checks above; it does not change SDK instrumentation or behavior.
