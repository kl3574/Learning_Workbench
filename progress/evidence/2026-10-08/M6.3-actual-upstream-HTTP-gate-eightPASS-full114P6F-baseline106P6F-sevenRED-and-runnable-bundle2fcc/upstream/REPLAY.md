# Bounded library replay

This runs only codex-http-client tests. It starts no Codex CLI, AppServer, model, production profile or resource/security probe. Dependency archives already exist in the task-owned cache. The gate includes one owned loopback closed-port connection failure; all other new cases are pure parsing/claim or rejected before DNS/send.

```bash
source $HOME/.cache/learning-workbench-acceptance/m63-owned-rust195-toolchain-oct08/environment.sh
export CARGO_TARGET_DIR=$HOME/.cache/learning-workbench-acceptance/m63-upstream-http-send-gate-oct08-bwzw1653/target
cd $HOME/.cache/learning-workbench-acceptance/m63-upstream-http-send-gate-oct08-bwzw1653/test-copy-04/codex-rs
cargo test -p codex-http-client --lib frozen_responses_request --locked --offline -- --test-threads=2
```

Recorded result: exit0, 8 passed, 0 failed, 112 filtered. Environment fixes CARGO_BUILD_JOBS=2. HOME and CODEX_HOME are not changed. The only test source metadata substitution is workspace.package.version0.160.0→0.0.0, explicitly recorded in TEST-BUILD-METADATA-03.json; original Cargo.lock and every external pin/checksum/Git reference remain unchanged. This is not a release-binary equivalence claim.

The already recorded full library command is `cargo test -p codex-http-client --lib --locked --offline -- --test-threads=2`. Its result remains FAIL114/6. The unchanged upstream baseline under the same environment remains FAIL106/6 with identical six failed names. Repeating these broader runs is unnecessary for replaying the finite passing slice.

The deployable patch is public-candidate/upstream-http-send-gate.patch. It modifies exactly four upstream source paths and was actually checked with `git apply --check` against an unmodified upstream library copy. Source is fixed to a956835d020762cb2b570053af06f643a11c0ecc. Applying the patch does not admit the code into a production profile.
