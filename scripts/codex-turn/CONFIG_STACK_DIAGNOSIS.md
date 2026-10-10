# Config stack diagnosis

This independent workflow binds the exact source, lock, tools and bounded profile of failure head `10ccea200815ba15448d07253f0ed6fc58f9e30c`. The original Config152 runner, source manifest, patch and workflow remain unchanged. Diagnostic source guards cover both complete 8797-row SDK graphs before and after Cargo.

The recorded failure is run 38030198967, job 114149335638, attempt 1. Seven scopes completed with 85 passing tests. The original36 scope launched 36 tests and printed 24 individual `ok` lines before the named recorder test overflowed its stack; no complete footer exists for that scope. Those lines do not establish 36 passing tests.

The new workflow is restricted to `fix/M6.3-config-stack-diagnosis`. It uses the original prepare, official Rust1.95 provision and locked dependency fetch. It then:

1. Collects the exact failing test with `--exact --list`, requiring its one actual nonzero name.
2. Runs that exact test twice in two explicit Cargo commands using the unchanged profile. The second trial runs even if the first reproduces the overflow.
3. If neither completed trial reproduces the actual stack-overflow signature, collects the unchanged original36 selection and runs it once.

Each command retains its own argv, exit, stdout and stderr. A reproduced overflow reports `RED_REPRODUCED` and fails this diagnostic job. A successful declared diagnostic scope reports `NO_RED_IN_DECLARED_SCOPE`; it does not turn the original Config152 gate into PASS. Compiler, collection and unrelated runtime failures retain their own observations.

The runner refuses an inherited `RUST_MIN_STACK` override and never changes stack size, SDK source, test assets, original selection manifests or the build profile. There is no automatic trial beyond the declared two singles and conditional group. The separate 3b comparison is not included.

All new diagnostic execution is **NOT_RUN** in this source candidate. Full Config152, Clippy, native producer, complete InputProof and production admission are outside this diagnostic scope. Default executor remains absent and registration remains false. Runtime receipts are private CI artifacts; their runner paths must be redacted before any later public progress report.
