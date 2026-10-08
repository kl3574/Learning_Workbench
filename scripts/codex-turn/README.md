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

This HTTP slice does not bind the platform's existing persistent control ledger
to an actual HTTP send. AppServer registration, model/counting proof, complete
resource qualification, actual destination IP/DNS enforcement and production
admission remain incomplete. A caller can still construct
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

## 本地 core producer 与 static bearer 回放

`core-producer.patch` 在同一固定官方 tar 上合并 HTTP04、A+C、B03-r2
及 FinalBearer05 的内部机械冻结机制，仍只改变
20个 Rust 路径。`core-producer-source.json` 绑定每项实际前后 SHA、原锁、
精确 Rust1.95.0 来源和完整源码图：原始8775项，补丁后8781项。文件字节、
权限模式与 symlink 均校验；原 `vendor/bubblewrap/LICENSE -> COPYING`
保留，它属于原 tar，不是补丁新增文件。旧私有 stock 遗漏该 link 及57项
可执行模式的历史限定保留，不能拿旧副本宣称完整 tar 相等。

继承的工程阶段对 B03-r2 四个测试 callsite 增加12处精确 `/*effort*/`、
`/*service_tier*/`、`/*include_internal*/` 参数注释；表达式、断言及实现
不变。当前候选在同一 producer 模块新增 static bearer finalizer 和8项测试，
两源的新 SHA 明确记录在 manifest；其余18项 Rust 源保持原字节。空补丁 context 行采用
无尾空格表示，实际 `git apply --check`、应用及 SHA 核对仍必须成功。

此内部切片将 ordinary core builder 的纯逻辑和纯 late body/header merge
与 live auth、telemetry、recorder、trace 和 contributor callback 效果分开。
受控入口要求显式提供已解析材料，在完整实际 envelope 计算前设置正整数
输出硬限及 disabled truncation，再通过 A+C 共享 API 执行一次真实
EncodedJson 编码。root cache-affinity 的实际 Responses session header 与
logical metadata identity 分开，Internal/SubAgent 保持原 logical header
规则。保留的实际 EncodedJson allocation 交给内部
`finalize_controlled_bearer_request`，只接受已解析 static API-key bearer 模式，
拒绝 unresolved/ChatGPT/signing/refreshing、已有或冲突的 Authorization、
Proxy-Authorization、Cookie 及歧义 bearer。单值 Authorization 标 sensitive
后再交 HTTP04 freeze；原 allocation、URL、method、timeout 和 response cap
保持不变。该 helper 零编码、刷新、callback、transport 构造或 IO。

这只是机械材料校验。可信 owner 必须在 body builder 前解析同一 config/secret
版本的 guardian/access/routing/attestation 等 required facts，后续只能走
HTTP04 `for_frozen_responses_request`，不得进入普通 EndpointSession/AuthProvider
和 retry。真实 Python→Rust request handle、可信 FinalAuth owner/InputProof
与持久账本 send 绑定仍未实现；传入 HeaderValue 或 mode 不会创建权威。

```sh
python3 scripts/codex-turn/replay_core_producer.py \
  --archive /path/to/a956835d.tar.gz \
  --output-dir /path/to/new-private-core-prepare --prepare-only

python3 scripts/codex-turn/replay_core_producer.py \
  --archive /path/to/a956835d.tar.gz \
  --output-dir /path/to/new-private-core-tests \
  --toolchain-dir /path/to/owned-rust195/toolchain \
  --cargo-home /path/to/owned-cargo-cache
```

`--prepare-only` 复用未变的 HTTP 回放准备机制，运行零 Cargo/Rust 命令。
默认只执行三个真实 `codex-core --lib` 过滤选择，均为严格
`--locked --offline -- --test-threads=2`，jobs=2：

- `responses_producer::tests`：19项 producer/拒绝/机械 bearer 测试，含两个自有 loopback sender 用例。
- `websocket_handshake_includes_attestation_for_chatgpt_codex_responses`：2项既存纯 mock header 测试。
- `internal_session_prompt_cache_key_is_scoped_to_parent_thread`：1项既存 cache-key 测试。

三个 filter、编译库总数2684及每项 footer 都固定校验，实际测试名必须精确
匹配 manifest 且非零；只有19+2+1全通过才能报告本次22项 PASS。
无 `--all-lib`、在线依赖补齐或自由 filter
参数，缺缓存保留实际失败。首次失败即停止后续选择，不重试、不删日志。
参数形式与原入口保持一致，旧 HTTP/API 入口及其源码不变。输出、Rustup home
和 target 必须新建；可复用预先准备的任务 Cargo cache，但不会复用或覆盖
已封存阶段的 target/二进制。HOME/CODEX_HOME 不覆盖。

输出保留 original/patched/normalized/final/core-final 完整图，命令及真实
stdout/stderr/exit 在 `receipts/`（补丁）和 `core-tests/receipts/`（版本/测试）。
`report.json` 绑定本次所运行的实际测试二进制 SHA与0.0.0测试元数据身份。
唯一构建元数据调整仍为 workspace.version0.160.0→0.0.0，原锁不变；这
不是原 release binary 或 production profile 等价证明。

历史 B03-r2 是14 selected PASS/core lib check0；B02 相同 session 材料的
真实 RED 为1 PASS/2 FAIL/exit101，旧30项成功并未消除当时的P2。新入口
不重跑旧14二进制；每次默认回放从固定 tar 应用当前补丁，使用新 target 编译
并记录本次实际22结果。FinalBearer05 作者的限定实际结果为 core22/0、
core check0，HTTP gate8/0另列，不算默认core22的一部分。初始排序 RED
为0/1/101，属于 freeze-before-auth 整合排序缺失，不是 HTTP04 安全漏洞；
错误 trait 编译101及 Cookie 拒绝18/1/101保留，后者保持同一19测试源码修复
guard后实际19/0。本入口
不运行完整2684项 core库、guardian测试、API190或HTTP库测试；既有 HTTP
完整114 PASS/6 FAIL保持 **FAIL**。本地源码/测试不能替代生产完整输入证明。

**INCOMPLETE / NOT_ADMITTED**：plain resolved facts 只做机械一致性校验，
不是可信 InputProof 或 owner 权威。Static bearer 机械冻结已实现，完整可信
FinalAuth 资格和 bridge 未完成。平台已有持久 control ledger；
它与真实 final Request/单次 HTTP send 的绑定、Provider/platform bridge、
模型/计量/容量证明、资源/DNS资格和 AppServer 生产接线仍未闭合；
registry/default None、UI和产品 wire 不变。此回放
不执行 CLI/AppServer/真实模型，不声称 Agent 或整个M6.3已完成。原 LICENSE
和 NOTICE 继续适用于上游派生补丁。
