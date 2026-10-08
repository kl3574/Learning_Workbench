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

## 共享 Responses 构造器 A+C

`shared-responses.patch` 在同一个固定上游提交上包含原 HTTP 门控和真实
Responses API 构造器。普通请求继续共用相同的同步准备路径；受控准备在一次
实际 EncodedJson 编码前设置正整数输出限额及 disabled truncation。有限制的
WebSocket 请求由受支持调用路径在 core 转换前、专用序列化和公开发送入口
检查并拒绝。公开 From 转换及通用 serde 类型本身仅保留字段，不保证拒绝；
普通空字段保留原 wire。

准备器接受已经完整的 typed request。完整 core builder、最终鉴权之后的冻结、
AppServer 接线、持久单次许可、模型输入/容量证明和运行资格仍未实现；这些
脚本不启动 CLI/AppServer/真实模型，也不注册平台生产 profile。

本地准备、应用与源码核对（不运行 Cargo）：

```sh
python3 scripts/codex-turn/replay_shared_responses.py \
  --archive /path/to/a956835d.tar.gz \
  --output-dir /path/to/new-private-ac-replay \
  --prepare-only
```

完整 codex-api 库测试固定为严格 `--locked --offline`，须事先准备独立任务缓存：

```sh
python3 scripts/codex-turn/replay_shared_responses.py \
  --archive /path/to/a956835d.tar.gz \
  --output-dir /path/to/new-private-ac-tests \
  --toolchain-dir /path/to/owned-rust-1.95 \
  --cargo-home /path/to/owned-cargo-cache
```

作者的实际完整 API 结果为190 PASS/0 FAIL/0 ignored/0 filtered；4个准备、
4个WS拒绝及1个普通golden均包含在190内，不能相加。8个原clients集成测试
另行通过，首offline缺Inflector导致的101以及错过滤器选中0项均保留。
本入口不运行clients、core或guardian测试。

原 HTTP 完整库的114 PASS/6 FAIL及未改基线106 PASS/同6 FAIL继续有效，
API190通过不能覆盖它们。唯一测试构建元数据差异仍为 workspace版本
0.160.0→0.0.0；原Cargo.lock不变，原release二进制等价未证明。输出包含
实际命令、日志哈希、退出码以及完整原/patch/normalized/final源码图。
