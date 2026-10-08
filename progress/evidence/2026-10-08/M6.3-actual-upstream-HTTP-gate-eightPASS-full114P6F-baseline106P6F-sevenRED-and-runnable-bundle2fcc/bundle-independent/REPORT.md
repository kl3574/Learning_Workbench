# M6.3 upstream HTTP gate engineering bundle independent static review

结论：**有限静态审查 PASS；Standards 0 P1/P2，Spec 0 P1/P2。** 本报告只支持接纳固定上游库的工程重放工具，不构成 M6.3 完成、完整库通过或生产准入。审查者未执行 replay、导入被审脚本、构建、测试、CLI、AppServer、模型或网络探针，未修改作者 worktree、sealed04 原件或规范。

固定候选：`2fcc7b187314e6a7c9dedbf7c06cb1bd3bbf19cf`，唯一 parent `cfb8ffe22355b8b4acc1ff8ef7ef74fc84fd7693`，分支 `feat/M6.3-upstream-http-send-gate`。当前 worktree clean，commit 仅新增 `scripts/codex-turn/{LICENSE,NOTICE,README.md,http-client-gate.patch,replay_http_gate.py,source.json}` 六文件。适用规则仅根 `AGENTS.md`；唯一规范 `PRODUCT_DESIGN.md` v3.0.15 SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec` 当前仍精确一致。

## Standards

无发现。六个当前文件、冻结声明及 committed source 逐一一致。原 upstream LICENSE/NOTICE 字节与固定原件同，工具位于既有 scripts 根，未变更 publication checker 或产品代码。README 准确交代只读输入、新私有输出、可信 task-owned 工具链/cache 和生产未准入。作者已有 publisher/diff-check 实际 exit0 回执已独立核其记录与完整日志哈希；审查者未重跑。

## Spec

无发现。逐行检查 `replay_http_gate.py` 与 README，并核完整 source.json、补丁及有限真实回执：

- `replay_http_gate.py:73–121` 在写解包文件前验证全部条目，拒绝绝对路径、父路径逃逸、错根、重复规范化路径、硬链接/特殊文件和 symlink 父路径；只允许指向同归档 regular file 的内部 symlink，最后创建 links。文件用 `xb`，输出目录先以新建 0700 且 `exist_ok=False` 创建（311–317），既有输出拒绝后不写 report。作者八种 unsafe tar 与既有输出不变的实际九个拒绝回执读回一致。
- `189–231` 在打开归档前校验固定 archive SHA，校验补丁和 LICENSE/NOTICE，完整复制 original，再实际 `git apply --check`/`git apply`。上游 immutable commit `a956835d020762cb2b570053af06f643a11c0ecc`，原 archive SHA `351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927` 当前文件重新哈希一致。四源 SHA、全部50 crate 文件及182条锁定 SDK 记录与 sealed04 原 map 精确一致。
- 正式补丁与 sealed04 原补丁仅五行空白 context 从单空格变空行；实际 prepare/gate 产物四源码仍与04完全同。固定原 `Cargo.lock` SHA `5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c` 两份 replay original/patched 均一致。
- `166–177` 只在精确 workspace.package section 将 version `0.160.0` 转为 `0.0.0`，校验固定 before/after SHA。实际 inventory 边分别仅4 Rust路径、1 Cargo.toml、0 build后变化；实际原/测试 Cargo.toml 字节比较也仅此转换。此测试元数据归一未称原CLI二进制 build 等价。
- `124–151` 对每个真实 subprocess 保存 command、实际退出码、stdout/stderr 与 SHA；无 shell、无重试。`261–297` 运行真实固定库 filter、严格 `--locked`，本次另带 `--offline`；`300–342` 保留 FAIL/INTERRUPTED，不以历史结果预填当前 PASS。source/lock/inventory build 后再次验证。
- README 与 source.json 明确区分8项子集、完整120项、历史失败、实际旧02 RED、工程编译与生产资格；仅6 source-only files 也证实无 AppServer/registry/default adapter 接线。

## 独立读回的真实工程回执

`prepare-only-01/command.json` exit0：只执行2条 Git命令，Rust/Cargo/tests NOT_RUN。`default-gate-01/command.json` exit0：5条命令含2 Git、rustc/cargo版本及 `cargo test -p codex-http-client --lib frozen_responses_request --locked --offline -- --test-threads=2`；actual stdout **8 PASS / 0 FAIL / 112 filtered**，没有把子集称完整通过。

作者这次 fresh engineering test binary 实际 SHA `4b43836a784a3d818a2dd50ecd90115b901a7417b9283b34a1d3309958610960`、62760296 bytes 当前独立重新哈希一致，只绑定该次工程重放，不补历史04或release binary出处。

完整 library 本轮 NOT_RUN；历史04 **FAIL114/6**、baseline **FAIL106/6**、同六个失败名称及旧02 **RED0/7** 保留，不断言独占环境根因。生产 **INCOMPLETE / NOT_ADMITTED**；持久许可、真实完整producer/InputProof/计量、AppServer送达链及资源/受限网络资格仍欠接线。本工程工具没有缩短这些规范边界。

## 证据定位

作者 packet：`$HOME/.cache/learning-workbench-acceptance/m63-http-gate-engineering-validation-oct08-qbsofna_`。

- `BUNDLE-FROZEN-COMMITTED.json` SHA `7dfee229ad0375250fc8e250756dbdf4f5bceaf1e3bc2c9f9f75836471c9398a`。
- `FINAL-VALIDATION-MANIFEST.json` SHA `b17a040609eb1e92f4077541888bcf7de8ec26cdd025f1e7469cedcf1b74aaca`，70显式证据文件，全部 size/SHA 重新核一致。
- 本独立 `READBACK.json` SHA `4c754c7766e454429bf090a06a6d5b025d4f4fcd78ce282ce1c1c61083f40702`，290有限匹配、0 mismatch，含六源码、archive、两份 original/patched 四源码及50 crate、lock、metadata、graph、inner/outer完整logs与fresh test binary读回。

审查者保存六文件只读副本于本 packet `reviewed-source/`。无新测试结果、无修改或发布。
