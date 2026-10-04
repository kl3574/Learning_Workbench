# 7cff 合成备份 lifespan：独立 Standards / Spec 审阅

**结论：两轴均零新增 P1/P2。** 这是一项可保留的有界未来覆盖准备；仅验证旧许可不继承、真实后台拒绝/重试、历史保留与零执行。永久禁用副本中的 queued/active turn、后续新调度、一般收敛仍 **OPEN_EVIDENCE**；产品 restore-preview/commit、M7、实际模型/CLI/tool 与全平台验收仍 **NOT_RUN/未验收**。不批准或声称发布、合入 canonical、恢复能力完成。

## 固定输入与独立性

固定 clean head `7cffb5305321c53258f5c5601a4ca7c29b5b4801`，直接父 `816cb38b7285d14fdbf5d00fcdecdced5e1b517d`，base `942fc533ca48e1a561199fb992d80e76622948c1`。相对 base 只有新增 `tests/integration/test_backup_codex_lifespan.py`，213 行/12896 bytes，SHA256 `58c31d9e75af9be61ac1fb42ef8fbdc631a0b26553f54026836102e54ce702ed`。无生产、规范、配置、依赖或旧测试变化；1523 个基础工程输入在 final1524 中逐 mode/type/Git blob/size/SHA 保持。

唯一规范 v3.0.15 SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`。本次针对既定 §20.17.7 的历史 actor/引用/事实保留、认证不继承、许可不可执行、恢复 GET 零重启，以及未开始队列和 durable-started 恢复边界审阅。未提出新规范或新接口。

作者未拥有本次独审产物；独审者未拥有被审源码/测试/运行 harness。本报告由一名独立 reviewer 分开完成 Standards 与 Spec，两轴不冒称两名 reviewer。仅运行文件/Git 哈希与准入文本回读程序；没有运行新产品测试、浏览器、模型、CLI、网络、主机探针或扩展安全调查，没有修改来源、canonical/远端或旧封包。

## Standards 轴：零新增

测试沿现有 create_app、owner fixtures、create_backup、BlobStore/Database 与真实 TestClient context。Archive 的 membership、每项 size/SHA、authentication/consent-disabled 宣告都被断言；只将检查过的 synthetic DB/blob 手工展开到独立目录，保留源 tables/files。没有替代 M7 restore owner 或把手工解包称产品恢复。

`main.py:170–201` 的原 lifespan initialize/recover/start/stop 仍执行。新测试只包住实例的公共 `run_once`，调用原方法，记录异常后裸 `raise`；不替换 `_loop`、stop Event、sleep、recover、claim 或 terminal，也不手动执行一次 worker。`codex_turn_worker.py:94–109` 的原循环捕获真实 ApiError、设置实际 last_error_code 并按原等待重试。断言观察至少两次拒绝和原线程 alive；退出 context 后断言原线程已正常关闭。没有为了 PASS 屏蔽原异常或构造假 terminal。

五个 forbid sentinels 限定 Codex model、普通 Provider stream、literal tool、Popen、fresh bootstrap runtime 的实际应用调用点，发生调用即计数并失败。它们是阻止实际执行的测试 seam，不是主机/网络攻防或全系统监视。finally 在正常 context 退出后写入实际观察，即使主断言失败也保留计数；PASS 后还有实际线程关闭、源表/文件保留断言。

## Spec 轴：零新增；有界证据仍开放

真实备份含非空 Turn/ProviderCodex owner facts，完整旧 start ACK 与 grant ACK 经 query-only checked owner 读口回读，不用当前 projection 改写 ACK。旧 cookie 返回401；新的 learner actor 与旧 actor 不同。safe session/turn/Job GET 可读，academic result 在 learner 下403；显式 role switch 后作者可读历史 consent/result，但原 actor/body/key 以及新 key 都不能转移旧 start/grant 权限，返回403 POLICY_DENIED。完整 GET/rejected-command 前后全表 hash 相等；fresh bootstrap/role 的真实写明确位于这些零写基线之外。

Control/Job queued/r2/not_started/no start 和 session active turn/r4 保留，dispatch 未开始、消耗0、usage/outcome/null、result none/三个 NOT_RUN 保留。原 worker `_claim` 经旧 actor 的实时 author 校验而拒绝；尝试 terminal 写时 ProviderRepository.writable 的 backup-disabled gate 又拒绝，整事务 rollback。原循环捕获这一异常并重试。recover 只选择有 persisted started fact 的 unfinished records；新未开始 queued 不被伪造为 failed/unknown。

§20.17.7 要求认证/旧许可不可继承和 GET 不启动任务，没有声明永久 disabled 副本必须在这项测试中成为 failed 并释放 active turn。本测试因此不能证明恢复后的新调度、一般后台收敛、过期/撤销许可全类别、GenericApproval/Import 历史恢复或 M7 产品恢复工作流。原942 sealed 范围保持不变；新 lifespan 有界证据不追改旧包。

## 原运行回读：没有新测试运行

| 源码 / 阶段 | 原实际结果与本次回读资格 |
|---|---|
| 816 focused-01 | 原 exit1，2 FAIL；仅准入 bounded summary 与精确 receipt，excluded whole failure log 未读。失败在 fresh actor/zero-action assertions 前。 |
| 816 static-01/diff-01 | 原 receipt exit0；原这两日志不在准入列表，本次不声称读过。 |
| 7cff focused-02 | 原完整准入日志 2 PASS/8.40s，receipt exit0/8.908447975991294s；raw log SHA `4589358cb3f614cdaf0315359c408bb3f459ba7e0bd9d15d984a59899a7f49fe`。 |
| 7cff related-01 | 原完整准入日志 7 PASS/15.36s，receipt exit0/15.9033774669806s；raw log SHA `e08974d392687f886f0692cc5a05a527fc33663112094bf9058fb8e78233b5dd`。包括本文件两例、旧 queued permission-loss 四例及 production empty 一例。 |
| 7cff static-02/diff-02 | 原日志/receipt exit0；Ruff原 All checks passed，diff原空日志。 |

**816→7cff 改变了测试 oracle。原两 FAIL 永久保留，不能称产品 bug 已修或同測 RED→GREEN。** 精确 expectation-correction.patch 已与固定 Git diff 一致；没有生产修复。

四份准入 finally observations：focused 的 production-empty/trusted-memory 分别4/5次真实原 ApiError，related分别4/4次；首 prior_loop_error=null，之后均 PROVIDER_BACKUP_DISABLED。每份 entered_lifespan/assertions_completed/alive_before_shutdown 为 true、alive_after_context 为 false，五 seam counters 皆0，fresh bootstrap 与 source model counters0。计数是实际有界观察，不要求精确循环次数、不证明一般收敛或所有 OS/network side effects。它们按明确 stage path、准备脚本与 manifest 绑定，本审没有补造隐藏的每份 observation 运行时 receipt。

## 准入与固定 Git 核验

只读 owner `seal-7cff/publication-candidates/` 的51个明确文本候选，加两个 outer JSON。每项 candidate size/SHA 正确；identity 或唯一可恢复的 literal home-prefix transformation 对应 advertised raw size/SHA。REPORT 与 candidate preparer 内已有 `${HOME}` 字面量保留；本审只对能匹配原 SHA 的 token 子集反向恢复，未误将所有 token 改成真实 home。没有打开任何 raw_path、DB、ZIP、key storage、cache、未列 runtime 或原失败 fixture-repr 日志。

独立核验三完整 Git 图4571 bindings、1506 distinct blob；全部 Git mode/type/blob/size/SHA 与真实 immutable Git 一致。七阶段14份原 before/after maps 共21336 bindings 均固定/clean/exact，commands 与 receipts/STAGE_HISTORY 一致；runner 原 SHA `77bb6a537d05583f88fafba3c3f8b5387fac1fc2931189f6aac596f7fe44c76d` 与所有七 receipt 一致，final1524 live inputs exact。成功日志的实际 bytes 通过唯一准入转换回原 log SHA；excluded old failure raw 不被补读或假称新核验。

**可整合范围**：保留这一 test-only future local coverage 准备及以上有限原结果；不解锁 M7，不借旧完整 gate、真实模型/CLI/tool 或默认 unavailable 证明实际能力。下一产品实现仍是 root 正在另树处理的既定 session interrupt UI；新源与门禁须另独审。
