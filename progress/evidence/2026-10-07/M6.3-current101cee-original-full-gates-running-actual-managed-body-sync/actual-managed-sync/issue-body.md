<!-- task_id: M6.3 -->
task_id: `M6.3`

spec_version: `3.0.0`
spec_sha256: `ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`

唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。

需求 ID：R-23, R-27

目标：CodexBroker/App Server、操作审批、产物清单

依赖：M6.2

修改范围：规范对应模块、契约、测试和脱敏工程进度。

验收清单及预期证据：
- [ ] M6.3: 拒绝操作零执行，路径逃逸阻断，成果预览回导


未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。

实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。
经审查/合并后才关闭任务；当前清单不表示已经验收。

<!-- engineering_progress:start -->
M6.3 仍在实施，AC-21 尚未验收，M7 保持 todo。唯一规范为 PRODUCT_DESIGN.md v3.0.15（SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec），包含用户已批准的受控 turn、逐操作审批和产物清单合同。

当前公开分支与草稿 PR56 已实际回读为 `079a008cf88b37e4517cb391503a1e7393ccf374`，1561 工程输入。运行源码锚点为 `d78c4d159a2831f7d5e1721a9a466ec5b3e66421`；079 的后续变更为进度证据及三个确切归档规则。原用户 b895 检出保留；没有 GitHub merge、release 或部署。

原完整本地 Python 门禁（固定079，一次实际执行）：4583 collected，4580 PASS、1 FAIL、2 数值 BLOCKED_ENVIRONMENT skip、3 warnings，3075.18s；pytest 与 wrapper 均退出1，全1561输入前后严格匹配。唯一失败为历史迁移夹具 forward_guards 的 HTTP503 vs202。原 traceback 没有打印 SQLite 异常；Broker/schema 的解释来自另外的源码与定向诊断。两数值环境 skip 保留原失败/no fallback，不算通过。

原 CI attempt1 两事件都已终态 FAILURE。独立原日志和有限原始行读回已完成，计数分别呈现，绝不相加：

- [push37632652743](https://github.com/kl3574/Learning_Workbench/actions/runs/37632652743)：5 个 job SUCCESS、1 个 integration FAIL。backend1114P/3warn，frontend1421P/167files，spec962P/2warn，publication23175路径且仍需手工来源审核；browser133P/28.6m；integration2518P/1F/2ENVskip/2warn/49m31s。
- [PR37632662238](https://github.com/kl3574/Learning_Workbench/actions/runs/37632662238)：4 个 job SUCCESS、integration 与 browser 两个 FAIL。backend1114P/3warn，frontend1421P/167files，spec962P/2warn，publication23175路径；integration2518P/1F/2ENVskip/2warn/74m57s；browser132P/1F/39.9m。

两组 integration 唯一失败均为上述 forward_guards 夹具。PR browser 的 Review 首用例在 Reader URL 谓词处耗尽整个用例的30s预算，根因仍 UNKNOWN。PR checkout e9eb82 的完整 Git tree 与079 的23175项相同；CI 执行时工作输入 before/after 明确 NOT_CAPTURED。日志下载exit0与测试成功不同，原 FAIL 不因后续局部通过而改写。

四项规范内修复已正常合入本地 `101cee47d8e746dddac81fb6e8829069fcabff09`，1564工程输入；尚未推送。原进度与用户b895检出、唯一规范均保留。另有两条确切的不可变证据空白归档规则，不改运行语义。以下是合并前的独立候选证据，不替代新组合完整门禁：

- `90c8cd4`：只修历史夹具的旧 owner 组合；升级前恢复当前 mandatory Broker，保留全部9原断言、另加3条。原同用例1F保留，修改后同用例1P、相关44P/2warn；计数重叠。独立 Standards/Spec 无阻断，生产与迁移均未改。
- `2323558`：只将锁中 source-map-js1.2.1 升至兼容补丁1.2.2。lint/typecheck/build通过，完整 Vitest1421P/167files，原 Reader 用例1P。原 audit exit1（1high/3low）与新 audit exit1（0high/3low）都保留，仍不洁净；当前数学依赖链无兼容的低风险补丁，未强制升级或改渲染语义。最初0用例的选择失败保留。
- `8bd930b`：§20.17.7 的三份备份历史测试，固定候选组合6P/2warn/19.41s，全1564输入前后相同；旧许可执行被拒绝、历史可读、关闭 worker 无伪终态。源码独立审阅与有限原件回读已完成、无阻断；未据此解锁M7。
- `5520255`：只为 Review 增加有限 setup/helper 时间与既有轮询状态码记录。原用例一次1P/19.8s，30s/retry0/worker1与业务断言不变；不记录JSON、query、header、rawURL、身份或表单值。仅诊断记录产出，未证明原PR原因已闭合；独立 Standards/Spec 源审阅无阻断；可选AST因缺本地模块未运行，额外严格E2ETS原失败及辅助声明环境通过分别保留。

已有持久 Broker 控制仍限定受检 synthetic callback、当前线程/租约和可能发送事实；22专项、473相关和Authoring5browser等旧局部证据保留，不替代当前完整门禁。更早27f/公开1e的原失败也保留。

真实 Agent 仍有工程缺口：默认空 ProofRegistry、executor=None；完整最终模型请求字节的可信 producer/checker、受限实际 App Server runtime 与停止回执未完成资格验证。当前0实际外部模型调用，用户密钥未写入源码或上传。Provider、Codex、物理数值、数学来源及教学效果分别未验收。

当前101的新完整门禁正在运行：原 `uv run --frozen --offline pytest` 实际收集4589项，只执行一次，尚未终态；原 `make test-e2e` 实际启动，全133项/55files、1worker、retry0。用例原超时保留，不推断最终通过数。新安装仍有3low依赖提示。静态检查的初次环境准备因为误用本机Python3.14.4与项目3.12约束冲突退出2，原回执保留，已用实际公共Python3.12.13继续；静态结果另行按原回执记录。

下一任务：等待固定101完整Python、全133浏览器和静态门禁的实际终态，独立读取原件与输入前后映射；根据新证据处理仍可复现的失败。公开分支仍079，当前101未推送。原两CI已结束，此次没有 rerun、cancel 或 dispatch。没有新增被自动审批拒绝的宿主探针，也没有用局部PASS宣称发布或平台验收。

<!-- engineering_progress:end -->
