受控 turn 合同按唯一规范 v3.0.15 持续实施。诊断候选已正常公开到 4ca，固定 f4 完整 native 133 PASS/19.0m；新原 CI 已实际运行但未推定通过。原 bf push132P1FAIL/PR133P 分开保留。真实 Agent/M6.3 未验收。

M6.3 仍在实施，AC-21 尚未验收，M7 保持 todo。唯一规范为 PRODUCT_DESIGN.md v3.0.15（SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec），包含用户已批准的受控 turn、逐操作审批和产物清单合同。

当前公开分支与草稿 PR56 已实际回读为 `bf5d2df4e7ee5156993169cdd9610fa014bdae4f`，1564工程输入；GitHub tree与本地commit tree一致。正常commit/push均实际0，首次PR head未同步的原readback保留，随后只读回验成功、没有第二次push，具体首读差异原因未确立。完整本地门禁固定源码锚点为101cee47，发布版本只另加确切归档属性与进度；其余1563工程输入相同。原用户b895检出和唯一规范保留；没有GitHub merge、release或部署。079及其原失败属于明确历史证据。

原完整本地 Python 门禁（固定079，一次实际执行）：4583 collected，4580 PASS、1 FAIL、2 数值 BLOCKED_ENVIRONMENT skip、3 warnings，3075.18s；pytest 与 wrapper 均退出1，全1561输入前后严格匹配。唯一失败为历史迁移夹具 forward_guards 的 HTTP503 vs202。原 traceback 没有打印 SQLite 异常；Broker/schema 的解释来自另外的源码与定向诊断。两数值环境 skip 保留原失败/no fallback，不算通过。

原 CI attempt1 两事件都已终态 FAILURE。独立原日志和有限原始行读回已完成，计数分别呈现，绝不相加：

- [push37632652743](https://github.com/kl3574/Learning_Workbench/actions/runs/37632652743)：5 个 job SUCCESS、1 个 integration FAIL。backend1114P/3warn，frontend1421P/167files，spec962P/2warn，publication23175路径且仍需手工来源审核；browser133P/28.6m；integration2518P/1F/2ENVskip/2warn/49m31s。
- [PR37632662238](https://github.com/kl3574/Learning_Workbench/actions/runs/37632662238)：4 个 job SUCCESS、integration 与 browser 两个 FAIL。backend1114P/3warn，frontend1421P/167files，spec962P/2warn，publication23175路径；integration2518P/1F/2ENVskip/2warn/74m57s；browser132P/1F/39.9m。

两组 integration 唯一失败均为上述 forward_guards 夹具。PR browser 的 Review 首用例在 Reader URL 谓词处耗尽整个用例的30s预算，根因仍 UNKNOWN。PR checkout e9eb82 的完整 Git tree 与079 的23175项相同；CI 执行时工作输入 before/after 明确 NOT_CAPTURED。日志下载exit0与测试成功不同，原 FAIL 不因后续局部通过而改写。

四项规范内修复已正常合入本地 `101cee47d8e746dddac81fb6e8829069fcabff09`，1564工程输入，现已随公开bf5d2df正常推送。原进度与用户b895检出、唯一规范均保留。101本身另有两条确切归档规则；完整门禁后本次追加11个确切归档文件规则，不改运行语义。以下是合并前的独立候选证据，不替代新组合完整门禁：

- `90c8cd4`：只修历史夹具的旧 owner 组合；升级前恢复当前 mandatory Broker，保留全部9原断言、另加3条。原同用例1F保留，修改后同用例1P、相关44P/2warn；计数重叠。独立 Standards/Spec 无阻断，生产与迁移均未改。
- `2323558`：只将锁中 source-map-js1.2.1 升至兼容补丁1.2.2。lint/typecheck/build通过，完整 Vitest1421P/167files，原 Reader 用例1P。原 audit exit1（1high/3low）与新 audit exit1（0high/3low）都保留，仍不洁净；当前数学依赖链无兼容的低风险补丁，未强制升级或改渲染语义。最初0用例的选择失败保留。
- `8bd930b`：§20.17.7 的三份备份历史测试，固定候选组合6P/2warn/19.41s，全1564输入前后相同；旧许可执行被拒绝、历史可读、关闭 worker 无伪终态。源码独立审阅与有限原件回读已完成、无阻断；未据此解锁M7。
- `5520255`：只为 Review 增加有限 setup/helper 时间与既有轮询状态码记录。原用例一次1P/19.8s，30s/retry0/worker1与业务断言不变；不记录JSON、query、header、rawURL、身份或表单值。仅诊断记录产出，未证明原PR原因已闭合；独立 Standards/Spec 源审阅无阻断；可选AST因缺本地模块未运行，额外严格E2ETS原失败及辅助声明环境通过分别保留。

已有持久 Broker 控制仍限定受检 synthetic callback、当前线程/租约和可能发送事实；22专项、473相关和Authoring5browser等旧局部证据保留，不替代当前完整门禁。更早27f/公开1e的原失败也保留。

真实 Agent 仍有工程缺口：默认空 ProofRegistry、executor=None；完整最终模型请求字节的可信 producer/checker、受限实际 App Server runtime 与停止回执未完成资格验证。当前0实际外部模型调用，用户密钥未写入源码或上传。Provider、Codex、物理数值、数学来源及教学效果分别未验收。

当前101的原完整浏览器门禁已终态并独立读回：133 PASS/0 FAIL/0 SKIP，20.9m，make与runner原退出0，只执行一次；133项/55files、1worker、retry0，原默认30s及各用例超时均未改。完整159原件、23命令四件组和166条原始行已逐字/哈希核对。4份全1564输入映射的Git/index始终精确；rawafter实际5个原生输出改写，先私有保存，再按固定101精确恢复，其余输入不变。两条证据顺序步骤exit1已保留，新readiness continuation各0，未重跑测试。Review首用例在全套中通过16.8s；旧PR超时原因仍UNKNOWN。

原完整Python `uv run --frozen --offline pytest` 已终态：4589 collected，4587 PASS、0 FAIL、0 ERROR、2 数值 BLOCKED_ENVIRONMENT skip、3 warnings，3172.43s；uv 与 wrapper 均退出0，只启动一次。56原件哈希与13份完整1564项Git/index/live映射经独立读回，最终detached与canonical闭包均在固定101精确。原阶段RESULT中的PENDING_FREEZE保留，后续独立FINAL补充真实闭包。两跳过分别为真实Authoring sealed calculator未执行、Restore evaluator未得numeric PASS；无fallback、不算物理验收。setup使用公开依赖安装网络。新安装仍有3low提示。浏览器前置原lint/typecheck/build/verify-spec回执均0，其原命令环境无HOME/CODEX_HOME覆盖；规范检查只是M0结构。

另一份独立静态捕获的四命令实际0、十份1564映射精确，但其实际覆盖HOME，违反本轮执行约束；原件和明确纠正一并保留，不升格完全合规静态验收。初始Python3.14.4准备exit2亦保留，随后采用实际公共3.12.13。进度归档的默认Git空白检查实际exit2：9份原件尾空行和1份Vite原尾空格。已独立审阅仅匹配11个确切progress归档文件的规则，已在完整门禁与最终闭包封存之后应用：仅.gitattributes改变，其余1563输入逐字与固定101相同。原规则前缀保留，实际Git属性读回证实仅11归档路径改变、所有1564非progress路径的whitespace属性值不变。原日志字节保留，秘密扫描不放宽；两次原暂存空白检查exit2保留（第二次为原diff归档本身的Vite尾空格）；后续原默认暂存检查实际0、原全tracked发布扫描实际0/23933文件，暂存树前后相同。扫描不能替代独立有限来源审核。活动进度残留RUNNING字段已纠正，原状态保存为previous/history；旧staged scope独审最终回执仍未收件，不能称该旧回执PASS。另行新鲜bf进度/源码有限独审已完成：先发现同一P2（7个当前恢复指针仍指079），原报告保留；纠正后20项有限核验PASS、Standards/Spec均0P1/0P2，固定101门禁和bf公开指针分开，所有旧事实明确保留为previous。

公开 bf5d 原始 attempt 1 的两次 CI 均已结束（观察时间 2026-10-07T18:26:27.247297+00:00）：push [37657156244](https://github.com/kl3574/Learning_Workbench/actions/runs/37657156244) 为 FAILURE，5 项 job 成功、browser 失败（132 PASS/1 FAIL/39.1m）；PR [37657163285](https://github.com/kl3574/Learning_Workbench/actions/runs/37657163285) 为 SUCCESS，6 项 job 成功，browser 133 PASS/38.5m。每次 integration 原日志各 2525 PASS/2 skip/2 warnings，push 4432.55s，PR 3103.02s；每次 backend 1114 PASS/3 warnings、Web 1421 PASS/167 files、spec-contracts 962 PASS/2 warnings、security-publication 23933 扫描分别绑定原 job，计数不相加。12 项原日志均只下载一次且 actual exit 0，安全选行已绑定 SHA/行号；完整原日志私有。运行输入前后映射 NOT_CAPTURED，skip 原因没有在这些 CI footer 中打印，不作为物理数值执行 PASS。旧 079 与当前 bf push 的原 FAIL 均保留；没有 rerun、cancel 或 dispatch。

生产 Agent 范围仍未验收：当前注册表为空、executor=None，现有 profile/request/receipt/control 仅支持 synthetic。真实的最终请求构造/checker、独立版本 profile/receipt/executor 及 stop/writer owners 属于仍待完成的本地工程；实际模型完整格式计数依据和可强制隔离/预算/零额外外发边界需要独立资格证据。用户已提供 DeepSeek key 和测试授权，本次根代理动作的实际平台模型请求为 0，未读取或上传 key。[DeepSeek 官方集成文档](https://api-docs.deepseek.com/quick_start/agent_integrations/oh_my_pi/) 声明 max_tokens，而唯一规范 §20.5 采用 Chat max_completion_tokens；这是文档合同差异，尚未修改规范或实发验证，不能宣称已收到 HTTP 拒绝。数值物理 runtime BLOCKED_ENVIRONMENT，真实 Provider/Codex/Broker/host、M6.3/AC21 仍 NOT_ACCEPTED，M7 todo。

当前正常提交和推送已 actual exit 0：4ca05634adac74b59ac6b5d932445158724c4365。公开 visibility、分支 HEAD、完整 Git tree、唯一规范 blob 与 draft PR HEAD 均读回一致；最终默认 diff 检查 actual 0，全部 24412 个冻结暂存/已跟踪文件发布扫描 actual 0，完整 index 前后相同。PR 仍 draft/open/unmerged，未 merge/release/deploy。

工程门禁固定在 f4e41f613800a01a0a0a52ac2dc0f57cec5933ad：原始一次 make test-e2e，133 PASS/19.0m/actual exit 0，原 30s/1worker/retry0/断言保持；1,564 个 Git/index/live 输入在 before/restored 精确一致，raw after 实际 10 个已知 UI 输出变化，原字节私有保存后才守卫恢复。当前公开 4ca 对 f4 的唯一非 progress 差异是 3 条具体归档空白规则，独立 11 项静态审阅通过，不能声称其整个 1,564 map 与 f4 相同。评分诊断仍仅记录有限枚举/状态/时间，原失败根因 UNKNOWN，未宣布生产因果修复；实际 CI artifact 保存仍待新 browser job 结果。固定 101 的 Python4587PASS/2数值ENVskip 仍仅归原 101，未在 4ca 重跑。

进度独立审阅原来发现 4 个旧 active CI/liveness 重复字段未更新的 P2，原 16/17 与完整 P2 报告保留；metadata-only 校正后新鲜 17/17 PASS、0P1/0P2，原记录移为明确 previous。这些是静态限定审阅，不是另一次运行测试。

新 4ca 原始 CI 已实际观察（2026-10-07T19:13:45.165812+00:00）：push 37672456876 in_progress/None；pull_request 37672466270 in_progress/None。每个已发现事件的 jobs 仅按实际 metadata 状态记录，不从状态推定测试计数。owned 82552 只读观察，无 rerun/cancel/dispatch；旧 bf pushFAIL/PRSUCCESS 与旧 079 FAIL 均保持原归属。本次根代理实际平台模型请求0，M6.3/AC21/真实Agent未验收，M7todo。下一任务是读取新原始 CI 终态与原日志/指定安全诊断 artifact，按实际证据处理失败，并继续真实请求证明和物理执行边界工程。
Refs #32
