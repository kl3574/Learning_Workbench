工程回放独立只读复核闭合：标准轴 0 P1 / 0 P2，规范轴 0 P1 / 0 P2；B03-r2 登记的 P3 参数注释问题在本工程副本闭合。旧 B03-r2 的 115 成员 review 包及原 P3、B02 的 P2/FAIL 历史保持。Reviewer 没有运行 runner、测试、模型、CLI/AppServer、网络或宿主安全探测，也没有写 canonical 或远端。

固定工程 commit `be92014f0c6e762da20d757703c25057d0aa3057` 的唯一 parent 为 `cad77366ad0ffc139b12b33e0a17d3ae4efb2213`，只提交 4 个授权路径，commit blob/live/freeze 的 bytes 与 POSIX modes 一致，worktree clean。原 HTTP/shared 入口、规范、许可证和 publication 规则保持原 bytes，README 原文 prefix exact。Author 的 102 个明确有限成员逐项实际 bytes/modes/link target 已独立核对：manifest `a642692d22c877ee98dc4833281b430c29c9c29f87734e8bf5c8f0f6c731008d`，seal `695c6286877b390b16d5a8d99f1556ff25f7c9e96e463c118d303e42db8b0897`。

4 个固定工程源码 SHA：

| 路径（scripts/codex-turn/） | SHA256 |
| --- | --- |
| core-producer-source.json | `1959e7d1667da86040ba83e4be025e16c0d17eb4e0e5fd67eeeb5cdb6803cc85` |
| core-producer.patch | `d2decff37fc925384c3f521137cc42e5fe3fa1be3af0cdbc3df600078bcc4996` |
| replay_core_producer.py | `a548b10c30b9c43fcfb962de03b522afbe5de36767b72776783cd413cb3f063e` |
| README.md | `9e55398a39428bfe1fea786d8a6b10c982dd58017bcc272cddb5c9be00017270` |

入口复用未变化的 `replay_http_gate.execute`，固定 `prepare_only=True`，准备阶段只有 Git apply check/apply。解包使用已审完整 tar 安全机制；原 archive SHA、patch SHA、许可证、全 source graph 都必须匹配。CLI 只有 archive/output/toolchain/cache/prepare-only 5 个参数，没有 online/all-lib/自由 filter。三个 Cargo gates 的 argv 固定 `--locked --offline -- --test-threads=2`，jobs=2；footer 状态、passed/failed/ignored/measured/filtered、完整测试名须与 manifest 一致，0 exit 或零目标不能单独成为 PASS，首次 gate 失败停止后续选择并保留原日志。

output 必须不存在，先 `mkdir0700(exist_ok=False)`，目标已存在时在任何 inner command 前拒绝；实际 owned-output fixture 内 exit1、sentinel unchanged、零 inner commands。Rust 三个 binary 按固定 SHA 校验，版本真实核为 1.95.0；target/Rustup home 属于这次新 output，原全局 cache 被 guard 拒绝。入口没有在线补依赖、全局安装、profile 修改、HOME/CODEX_HOME override 或模型调用。

固定 upstream 是 `a956835d020762cb2b570053af06f643a11c0ecc` / `rust-v0.160.0` 的本地 archive `351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927`。实际 source 图原始 8775、patched/normalized 各 8781，bytes/modes/links 与新 manifest 的 canonical digest 一致；原 LICENSE symlink 保留，并非补丁新增。patch 只变声明的 20 Rust paths，其中 19 项与冻结 B03-r2 exact；唯一 tests 文件添加 4 callsite 的 12 个 `effort/service_tier/include_internal` 注释，反向剥离后逐字回到 `45f1c1c1ddb840f40c1c050e892707d724e9a9320c5947b62280464a408b7799`。新 tests SHA `8c102534ce4eb43b8fdd58ed4bd4f65de456051617e85f0908b9e4a839df26c7`；表达式、实现、断言均未变。raw engineering patch 反向去该 12 comments 精确等于 B03-r2 combined patch；当前 patch 又只把 29 个单空格 blank context 行变为空行，实际 fresh apply 和全 source graph 核对成功。

唯一测试构建元数据变化是 `[workspace.package]` version `0.160.0 → 0.0.0`；原 `Cargo.lock` SHA `5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c` exact。原/normalized/current-final/core-final 图终后吻合，没有原 release binary/profile 等价声明。

原一次 fresh 默认回放 outer actual0（05:02:50→05:09:58 UTC）。7 个嵌套命令是 Git check/apply、Rust/Cargo version、三个 gates，全部 actual0，完整 argv/cwd/stdout/stderr/hash/exit 独核。实际结果：

| 选择 | PASS / FAIL | filtered |
| --- | ---: | ---: |
| controlled-pure | 11 / 0 | 2665 |
| 原 stock WS affinity 两例 | 2 / 0 | 2674 |
| 原 stock internal-cache 一例 | 1 / 0 | 2675 |

三组完整测试名和唯一 footer exact，14 selected PASS；default report SHA `d1fe8ea3c755a32bb7add7654d0703d7a9126fb97e60af087fc129078aff62c2`。新 owned target binary 为 830885120 bytes，实际流式 SHA `7a247d0963eeb3dbf28d99a768a2a7096aa38204733298c7a7d9317b5e3eeddc`。原 B03-r2 target binary 830879912 bytes / `e9e68ca5b8b89785dc9c4d0e7992c80e7ab32cc9eefe8015b258c48e20c495bb` 与旧 seal 仍 exact，没有覆盖复用。

`prepare-only-02` actual0、两 Git 命令、零 Cargo/Rust、tests NOT_RUN；此前 `prepare-only-01` 的 git-check actual1、FAILED patch、当时 source-input/报告/完整 raw logs 保留，并未当成最终 4 源执行。受影响 ruff、rustfmt-comment、staged diff、publication 检查均实际0；owner 的 12 selector 正/反例记录覆盖 exact/zero/wrong-name/double-footer，本 reviewer 只读其结果并审源码，没有复跑。完整 core2676、guardian、API190、HTTP 库、本平台 Agent/native/CI 都不属于本入口实际执行；API190 属历史结果，HTTP114P6F 仍保留 FAIL。

唯一规范 v3.0.15 SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec` 未变。plain facts 只做机械完整性，不能冒充可信 InputProof/FinalAuth/owner authority。平台已有 ledger 的存在与 final Request/单次实际 send 的未接线边界明确区分；bridge/profile、模型/计量/容量/资源/DNS 资格及生产注册仍未完成。README/manifest/report 均标 INCOMPLETE / NOT_ADMITTED，没有扩大本地 14 PASS 为生产或全门禁 PASS。
