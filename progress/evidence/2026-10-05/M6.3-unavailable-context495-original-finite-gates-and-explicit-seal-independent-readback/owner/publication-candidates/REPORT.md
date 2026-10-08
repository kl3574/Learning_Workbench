# M6.3 不可执行准备原件闭包 v4 — 作者交付报告

固定源码 `495e4daddddb64460326659be5af341085654131`，base `6671dd5c924edbac8ca7f479c4f51d4afec14480`；6 路径 587+/20-（5 个生产 Python 路径和一个 439 行 integration test）。唯一规范 PRODUCT_DESIGN v3.0.15 SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`，本切片仅落实 §20.17.1.1、§20.17.1.2、§20.17.7 的已有准备/持久读回/严格原件与失败关闭边界；不补写规范或新 HTTP 合同。

## 实际行为与资格

新的默认不可执行 TurnInput v1 准备使用严格私有 `UnavailablePreparationContext` v4。它冻结真实受检 BootstrapSnapshot（完整描述与原 receipt）及其 digest、当次 ProviderConfigView 非秘密版本事实、当次教材/证据/历史 pair 来源，存入实际 SQLite 事务。通过 bootstrap owner 既有 `checked_owned_sessions` 接口核对原件，Context/Provider 既有 read/verify 对整个 v4 记录与历史 pair 做原件一致性核验。

严格 `implemented=false` 拒绝整数 0、浮点 0.0 和 True。缺项是闭合有序三项：`production_input_proof_unregistered`、`production_turn_protocol_unregistered`、`production_turn_runtime_unregistered`；不填造 turn schema/init/resume/final request/deployment/资源事实，不把准备闭包称完整生产 InputProof 或真正 turn freeze。生产 registry 仍空，executor 仍 None；现有 preview 仍 503/CODEX_INPUT_PROOF_UNAVAILABLE，无 proposal/外发许可/排队/执行。

历史 bootstrap actor 与原 turn actor 按各 owner 原事实比较；不要求当前合法读者等于旧 actor。Provider config/secret 元数据版本或教材 revision 合法推进投影为原有 changed/current 资格，原 ACK、hash、Context 不回写。原件破坏 409 失败关闭，GET 不修复、不新增表写。事务中 Context/Run/command 任一点真实 SQLite abort 均整体回滚，不留下局部准备。

旧 TurnInput/runtime v1、context v1/v2/v3、原事件/ACK decoder、54 core、0001 baseline、Bootstrap/public DTO/路由/依赖/CI预算均保持原字节。旧合成可执行 v2 与旧不可执行 v1/v3不被新准备升级。

## 原始测试与失败记录

首次 test-only 7c1058 实际 1 FAIL：真实 HTTP 准备的内部 context.version 为 v1，期待 v4。实现 de4d 后同一完整 83 行 test 文件、同样命令实际 1 PASS。两固定 Git 原件的文件 mode/type/blob/size/SHA 完全相同；不是替换 oracle 的 RED→GREEN。

`mypy-01` 是一次静态 invocation FAIL，含 3 条 union-attr diagnostics；`ruff-final` 是一次 F401 unused-import FAIL。三个失败的原 command/receipt/full before-after maps/raw log hash 均保留；mypy 与 Ruff 的完整安全日志列入本包。首次 pytest FAIL 的完整 raw fixture repr 日志不列入候选，只选择原始 1-based 行 25–33、45–46，逐行原字节摘录，完整原日志 SHA 为 `0e4ec41712b3d58bde8df982458c02ea515cb85c4a96191c65d6f87eeb89cc68`（3047 bytes）。原私有 full log不变，不称公开摘录为完整原件。

固定最终 495 上实际 finite gates：

| Stage | 实际终态 | 时间/范围 |
|---|---|---|
| focused-final-02 | 30 PASS | pytest 31.16s，wrapper 31.582882s |
| related-final-02 | 334 PASS | 9 个指定相关文件；pytest 181.63s，wrapper 182.173363s |
| ruff-final-02 | exit/wrapper 0 | 新6路径 |
| mypy-final-02 | exit/wrapper 0 | 288 source files |
| spec-final-02 | exit/wrapper 0 | 仅结构/完整性 M0 checker，非产品验收 |
| generated-final-02 | exit/wrapper 0 | checked 82 artifacts |
| diff-final-02 | exit/wrapper 0 | git diff --check |

30 专项覆盖严格 false/封闭缺项和伪造字段拒绝、完整 bootstrap/Provider/context 损坏与成员尾删、重放/GET 失败关闭、原 SQLite 写回滚、新 actor 权限、Provider config/secret 非秘密版本和 Content revision 合法推进、旧 ACK 字节、既有 context v1/v3 codec 原版本、实际 completed pair retained/omitted 原件核验。334 相关回归是 preparation/consent/dispatch/lifecycle/review/events/Provider/DTO 的明确九文件，使用现有受控内存 fixture，非新的全平台完整门禁。

focused-final-01/02 各18条 payload-free case receipts、各162个 named counters 都为0。它们只覆盖被 fence 的新不可执行阶段（bootstrap freeze/validity/execute、Popen、probe、secret read、model executor/transport、tool）。每案准备 fixture 有1次合成 bootstrap；两个历史案在 fence 前分别完成2次内存 protocol peer 调用。不能称全流程/所有30案/主机物理监控为0。其他严格模型与 codec 用例靠其明确 assertions；related fixtures 中的合成调用不改称真实模型或0调用。

restart 测试使用未 enterlifespan 的 TestClient；仅证明持久读回相同原件、GET/preview无写和对应 named seams，不证明 worker 启动、调度、恢复收敛。legacy v1/v3 两个 codec 原件由既有 context factory 构建，不 rewrite 旧记录；手工 pair 只证明 codec，不能当实际 Provider history授权。实际历史全 pair 验证来自另两个 real HTTP + SQLite +明确 synthetic Provider setup 用例。

## 固定输入与显式共享范围

7 固定 Git 全图：10,686 bindings /1,516 distinct blobs；最终1,527输入；1,521旧非重叠输入 mode/type/blob/size/SHA不变。19原阶段、38个完整 before/after图、58,024 bindings全部与相应 immutable Git及原receipt/log SHA一致，前后实际exact；最终工作树clean且逐1,527 tracked bytes与固定Git相同。首RED图1,526，其余stage1,527。

v2 documentary verifier 修正旧脚本命名 selector `migrations/0001_core.sql` 为实际 `migrations/0001_baseline.sql`，另写新 v2 输出；旧 verifier和原输出不动。原全图已包括真正baseline，故不是源码/门禁结果修正。两 verifier sha/selector差异在独立说明文件。

封包 builder 首次仅 documentary 执行因将 Ruff `All checks passed!` 误判为数字 pytest summary 而 TypeError 退出，尚未创建 seal。原 builder 副本与具名失败记录保留；改为精确数字 summary regex 后再次构建。此为封包脚本解析问题，不是产品门禁 FAIL 或测试重跑；所有19原门禁原件及源码不变。

共享仅 `SAFE_CANDIDATES.json` 逐项列出的 publication-candidates 文件及 outer READBACK/SAFE。所有复制为 identity；原RED摘录只有明确原行选择，无隐式日志净化。排除原完整RED raw log、DB、ZIP、secret directories、runtime/profile/temp与所有未列明文件；不递归授权。候选每项含原/复制 size/SHA、来源及转换，固定源码附Git head/blob provenance。作者检查与封存不是独立 review；root 的 source/evidence独审另外进行。

## 未完成与下一步

本切片不注册生产 InputProof checker、production turn protocol/runtime/executor，不建立真实外发模型/工具或host资源资格。真实 CLI/model/tool/network与生产正路径 NOT_RUN；不存在从默认 unavailable 推导的真实 ENV 能力/安全结论。全4,341后端/全Web/native不在本次 finite gate范围；任何旧完整/CI失败、未知根因或stage进度不回填。整体 M6.3 和 M7均未因此验收。

root 独立逐候选读回后可按已有授权 normal本地融合本切片；作者未merge/push/写远端，canonical和旧封包均不改。后续只读核对已有9上游schema及内部ref闭包/来源收据，准确记录可核原件及 production admission缺项；不借synthetic取得生产资格。
