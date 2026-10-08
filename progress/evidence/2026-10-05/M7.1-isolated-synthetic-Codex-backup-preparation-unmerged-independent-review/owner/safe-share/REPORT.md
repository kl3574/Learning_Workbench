# §20.17.7 Codex 合成备份回读证据（局部候选，未合入）

固定 base：`d6d4d9b98316d7f3790eb60e5d1bb4aca67450d1`。
初始测试 source：`dfd9a77de24c2ca9145466f91299a13d0a2d967b`。
最终 source：`942fc533ca48e1a561199fb992d80e76622948c1`。
唯一规范：PRODUCT_DESIGN.md v3.0.15，SHA-256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`，与先前已完整读取的唯一规范相同。

独立工作树 `m71-codex-backup-synthetic-owner-oct05`，branch `feat/M7.1-codex-backup-synthetic-oct05`。仅新增 `tests/integration/test_backup_codex_turn_history.py`（181 行）；规范、产品路由/DTO、生产代码、依赖、测试配置、原用户树和 canonical 均未修改。候选未合入、未推送，M7.1 未改成 active/accepted。

## 实际测试结果

| 固定源码与命令 | 实际终态 | 范围 |
|---|---|---|
| dfd9a77d；两个新增用例 pytest | **2 FAIL**，5.636 s | 新测试 fixture 路径布局错误；原件保留 |
| 942fc533；两个新增用例 pytest | **2 PASS**，7.540 s | queued/granted turn 与 completed/checked manifest 的实际 CLI 合成备份和直接 GET 回读 |
| 942fc533；新增及原有 backup 相关 pytest | **21 PASS**，24.077 s | 新用例2、bootstrap4、Session/Provider/内容/成绩等相关原有用例；不等于全部平台门禁 |
| 942fc533；新增文件 Ruff | **PASS** | 新文件静态检查 |
| 942fc533；base..HEAD diff-check | **PASS** | 差异格式 |

五轮门禁各有1523个工程输入的 before/after 映射，全部不变。两轮 PASS pytest 各有2条锁定依赖 TestClient 弃用提示；未改依赖来隐藏提示。外部模型/真实资料/真实网络请求为0，运行使用受信合成证明与纯内存 synthetic transport。

原始 FAIL 的直接原因：`consent_case` 的 `Settings.data_dir` 由当前测试 `tmp_path` 创建；新用例又把同一 `tmp_path` 作为旧 `cli_backup` helper 的 temporary 目录，导致 helper 将 stdout/stderr 和 uv 临时 lock 写入源目录。既有“source file bytes unchanged”断言正确失败。修复仅将 evidence/readback 使用 `tmp_path_factory.mktemp(...)` 的独立兄弟目录，未删断言/放宽业务权限、预算、timeout 或 retry。此 FAIL 不被标记成产品 backup 缺陷，也不虚构更早的产品 RED。

## 两个新增用例实际证明的范围

1. **queued + grant**：实际创建非空的六类 turn 表、四类 `provider_codex_` 表；CLI 一致备份后保留自有 JSON/hash/head/成员/原 ACK/actor 引用。源表和源文件不变、所有包内登记字节大小/hash可核、旧认证材料和已知合成秘密不进包。恢复副本当前 proposal 为 unavailable，历史 grant 原 active 事实仍保留。fresh actor不能用旧 body/key 接管 start/grant。当前 GET 保持 queued/not_started/未消费调用事实且 whole-table hashes不变。
2. **completed + manifest**：纯内存一次合成 dispatch 产生并登记非空 manifest/member/artifact/blob。实际 CLI 包含登记 blob，回读 manifest 原字节与下载原字节一致，原头/成员/跨 owner/hash/ACK不变；质量标记保持 mathematical/sources/independent_pedagogy=NOT_RUN。fresh actor不能接管旧 start/grant，历史完成结果不改成新执行。

两例均验证旧 cookie失效、建立fresh learner会话后安全 control/session可读而学科 preparation/consent/result/manifest/download拒绝；随后显式切fresh author才读取允许的学科资料。原历史 ACK与动态当前 proposal/validity分开验证；不要求动态 DTO全字节保持当时值，也不将历史active视为可调度许可。

## 必须保留的限制

- 测试通过旧 helper手工展开临时合成备份作读回，**不是产品 restore-preview/restore-commit流程**；这些HTTP操作仍NOT_RUN，M7.1未验收。
- `fresh_reader` 使用未进入context的TestClient，测试的是直接GET路径和显式 `forbidden_worker` 缝。它不执行应用lifespan，不证明后台自动启动/worker恢复/排队收敛安全；这些NOT_RUN。GET过程中restored ControlledRuntime.calls和纯内存transport调用为0，不能升级成所有进程/网络层观测。
- 两例均未创建GenericApproval、Codex Import或普通Import历史；相关空表检查只是明确空白，**这些备份覆盖NOT_RUN**。不以空表hash相同伪称已覆盖。
- queued例没有执行restored worker或直接消费旧执行许可；它证明当前只读状态与fresh actor拒绝旧命令。后台恢复/旧原actor worker准入的实际测试NOT_RUN。
- 无真实Provider/Codex请求、完整生产InputProof、实际Broker/数值环境/模型质量或全阶段接受声明；完整平台门禁NOT_RUN。本候选不绕过M6.3依赖。

## 原件、候选与审核边界

原件位于本 evidence目录的各gate文件夹，包括实际argv/env/UTC/terminal/log与 before/after maps、各临时合成fixture的CLI回执和备份。原始完整FAIL log、数据库、ZIP、秘密材料目录、readback数据库、runtime输出均保持私有，不在safe候选中。

`safe-share` 候选仅含明确列入SAFE_SHARE.json的源码、差异、命令/回执/源映射、两个PASS日志、Ruff/diff日志、有界FAIL摘要、六次合成CLI命令回执/输出及四份成功备份的无正文清单元数据。清单元数据的包字节/hash复核是原 gate后的独立documentary读回，分别记录，不冒充额外pytest或真正restore验收。仅将本机 `$HOME` 路径显示替为 `$HOME`，记录每份原件和候选SHA；候选runner路径文本仅用于审阅，执行应使用已保留且hash固定的本机原件。没有复写原件或修改原测试运行。

SAFE候选仍待独立审阅；固定head、公开证据和M7状态由root处理。本报告没有自动发布或远端同步。
