# Pinned Codex HTTP send gate replay

Status: **INCOMPLETE — production NOT_ADMITTED**. This engineering tool reproduces
the frozen candidate04 change to the actual upstream `codex-http-client` library.
It does not register an AppServer adapter or change Learning Workbench's platform
registry, default `None`, UI, or product request flow. Product requirements remain
in `PRODUCT_DESIGN.md` v3.0.15, especially §20.5 and §20.17.

`source.json` binds the official OpenAI Codex commit
`a956835d020762cb2b570053af06f643a11c0ecc`, its archive SHA256, the original
`Cargo.lock`, before/after hashes of exactly four Rust paths, all 50 resulting
crate files, the locked normal/dev dependency closure, and official Rust 1.95.0
component origins. The patch retains the original `EncodedJson` / `into_prepared`
bytes, checks the actual prepared reqwest request, and shares one irreversible
send claim across clones. The dedicated client disables proxies, redirects,
retries, compression and late tracing/header injection and uses HTTP/1.

The patch has two new modules and changes only `lib.rs` and `transport.rs`.
Five blank patch context lines use an empty line instead of a single trailing
space. The transformed patch must produce the exact frozen Rust file hashes;
the source bytes are not reformatted or edited during replay.

## Prepare and run

Use Python 3.9+ and Git. Acquire the exact local archive separately from the
`source.archive_url` in `source.json`; the program validates its SHA256 before
opening it. It does not download or install software.

For tests, separately provision the official standalone **Rust 1.95.0** components
listed in `source.json` into a task-owned prefix. The x86_64 Linux binary hashes
are checked, then actual `rustc` and `cargo` version commands are recorded.
Provide a task-owned Cargo cache with the original locked dependencies and Git
revisions already fetched. No global Cargo/Rustup directories or shell profiles
are modified. A missing offline dependency fails with its actual receipt.

Each output directory must be new and its parent must already exist. Use a
private task cache outside this checkout. Do not add its archives, source trees,
targets, receipts, or reports to Git.

```sh
python3 scripts/codex-turn/replay_http_gate.py \
  --archive "$TASK_CACHE/a956835d020762cb2b570053af06f643a11c0ecc.tar.gz" \
  --output-dir "$TASK_CACHE/prepare-01" --prepare-only

python3 scripts/codex-turn/replay_http_gate.py \
  --archive "$TASK_CACHE/a956835d020762cb2b570053af06f643a11c0ecc.tar.gz" \
  --toolchain-dir "$TASK_CACHE/rust195/toolchain" \
  --cargo-home "$TASK_CACHE/rust195/cargo-home" \
  --output-dir "$TASK_CACHE/gate-01" --offline
```

`--prepare-only` executes no Cargo or Rust commands. It checks archive paths,
rejects path escape/special files/unsafe links, preserves the complete original
directory, copies it, executes `git apply --check` and `git apply`, verifies that
only the four expected paths changed, then applies the one test metadata change.
The safe original upstream symlink is retained. Full file inventories record the
original, patched, normalized and final source states.

The **only** metadata normalization is the upstream workspace package version
`0.160.0` → `0.0.0`, needed to retain the original upstream lock's local package
versions. External pins, Git references, checksums and `Cargo.lock` stay exact.
This source/test build is not evidence of equivalence to the original release
binary or production profile. Rustfmt is not run by replay.

The default test command is the real library subset:

```text
cargo test -p codex-http-client --lib frozen_responses_request --locked [--offline] -- --test-threads=2
```

`CARGO_BUILD_JOBS=2`, `RUSTC`, `RUSTDOC`, task `CARGO_HOME`, a private
`RUSTUP_HOME` and an output-local target directory are explicit. `HOME` and
`CODEX_HOME` are inherited unchanged. Build wrappers/flags from selected inherited
environment overrides are removed and their names are recorded. The provided
toolchain and dependency cache must be trusted engineering inputs; their local
configuration is not a production sandbox qualification.

Add `--all-lib` to select the complete 120 library tests, without the filter.
Historical actual candidate04 results are **subset PASS 8/0**, **full library
FAIL 114/6**. The unchanged upstream baseline is **FAIL 106/6**, with the same
six failing names; this does not establish an exclusive environment cause.
The old candidate02's seven local rejection cases are **EXPECTED RED 0/7**.
The full library failure remains a failure after subset success. Replay records
the current actual result and never substitutes these historical counts for it.

`report.json` contains the invocation, source state graph, hashes, selected test
scope and actual exit. `receipts/*/command.json`, `stdout.log` and `stderr.log`
retain each executed command, timestamps, task environment, exits and log hashes.
The script returns Cargo's actual nonnegative test exit after source verification;
validation/launch failures return 1, interruption returns 130. It does not retry,
overwrite an existing output, delete failures, run Codex CLI/AppServer, or call a
model. Cargo's normal dependency setup may use network unless `--offline` is set;
the frozen subset uses synthetic requests and one owned closed loopback port.

## Scope and licensing

No persistent authorization ledger, AppServer registration, model/counting proof,
complete resource qualification, actual destination IP/DNS enforcement, or
production admission is implemented by this slice. A caller can still construct
an ordinary transport or refreeze trusted request material. The returned original
request type retains its upstream raw `Debug` behavior, so trusted owners must
avoid logging it. The shared atomic claim covers clones of one frozen allocation;
it is not a durable cross-process authorization capability. No Agent integration
or M6.3 product completion is claimed.

`LICENSE` and `NOTICE` are the original upstream root files, preserved byte for
byte for this upstream-derived patch, including its third-party notice. The
patch modifies the four paths recorded in `source.json`. These bundled upstream
license materials do not select a license for the Learning Workbench repository;
its owner-level licensing decision remains unchanged.
