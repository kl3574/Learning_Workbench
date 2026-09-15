# ab6 平台 Agent 与继续实施状态的只读核验

核验对象：ab6c27b417b98e50eb5e2feb469be191d1db4d41 当前代码，唯一 PRODUCT_DESIGN.md 3.0.3（a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8，与外层同字节）及当时本地 progress。未运行应用、测试、模型、网络请求；未读取任何 key、运行数据库或私有 vendor 报告。下述行号均相对当前仓库根。

| 范围 | 实际结论与定位 |
| --- | --- |
| Thread / Tutor / Run HTTP | 六个规范接口尚未注册：POST threads、GET threads/{id}/messages、POST tutor/runs、GET runs/{id}、GET runs/{id}/events、POST runs/{id}/cancel。packages/contracts/generated/runtime-route-coverage.json:8–10、33–35 标为 not_registered；实际生成 openapi 也无对应 method/path；services/api/app/main.py:85–96 只接入现有 routers。这里 NOT_IMPLEMENTED 是产品状态，不是已实现的 HTTP 501 占位响应。services/api/app/interfaces/boundary.py:37–40 先处理本机会话，:91–94 才将路由 HTTP 错误映射为安全错误；本次没有发请求，不能虚报某个实测 status。 |
| 核心模型和建表 | packages/contracts/domain_models.py:264、272、289、298 有 TutorRequest/ContextSnapshot/RunSnapshot/RunEvent；migrations/0001_baseline.sql:44–48 有 threads/context_snapshots/runs/messages 基线表。这些是既有契约/存储骨架，不能当作 Thread owner、Tutor 持久 Run、终态恢复或 SSE 业务实现。 |
| 当前 Tutor UI | apps/web/src/workbench/Tutor.tsx:9、12 的“未配置模型”是静态文案，并非真实 provider 当前配置查询；:13 onSubmit 仅 preventDefault，发送按钮无条件 disabled。问题草稿、冲突恢复和上下文预览存在，尚无创建 Run/订阅事件/取消/恢复对话的前端闭环。配置设置完成也不会使这个按钮可发送。apps/web/src/workbench/Shell.tsx:202 在受限状态切为固定操作帮助；apps/web/src/features/assessment/OperationHelp.tsx:1–2 不调用模型。 |
| 当前生产 source / proof | services/api/app/main.py:44–51 默认创建空 OutboundSourceRegistry 与 RequestPreparer(ProofRegistry())。services/api/app/application/provider_ports.py:87–110 只支持明确注入，缺 owner 返回 OUTBOUND_SOURCE_UNAVAILABLE。services/api/app/application/provider_budget.py:71–90 无默认 proof，缺项 CAPABILITY_UNSUPPORTED；:129–139 使 chat/streaming 不可调度，搜索/工具/结构化固定 false。测试专属依赖注入不是生产注册能力。 |
| 已有 Provider/SSE 层 | services/api/app/main.py:49–59 确有 Provider/Consent/CheckedDispatch 服务以及启动时受控未完成派发恢复；services/api/app/interfaces/provider_http.py:75–137 实现配置、秘密、许可等控制路由；services/api/app/application/provider_dispatch.py:223 起有内部 CheckedProviderEvent 流和终态持久化；services/api/app/infrastructure/provider_transport.py/provider_sse.py 是供应商流传输/解析层。这不等于 GET runs/{id}/events 的浏览器持久 Run SSE。当前唯一启动 worker 是 services/api/app/main.py:62 的 ImportWorker；其 services/api/app/infrastructure/import_worker.py:279–306 调度证据恢复、推荐、检索、评分与导入，没有 TutorWorker。 |
| 配置与 readiness | apps/web/src/features/providers/ProviderSettings.tsx:44–49 明示配置与可调度分开、无真实生成任务；services/api/app/application/runtime.py:15–19 只报告配置存在、数据库/worker等基础就绪。配置存在不是模型请求成功、Tutor 贯通或能力证明。 |
| Agent 验收状态 | progress/state.json:954–977 把 M5.3 记为 todo、implementation_commit=null、PAUSED_NOT_IMPLEMENTED；:980–1000 的 M5.4 为 NOT_RUN。CURRENT.md:8–10、31–33 与之相容。应表述“平台 Tutor/Run/SSE 闭环未实现，平台 Agent 端到端 NOT_RUN”；不能泛化为 Provider 控制面或本地检索从未实现/测试。 |

已存在的独立 vendor 最小调用成功，仅可按进度中已登记的限定事实单列。本次未读取其私有回执，也不重新确认它；它不改变上述平台 NOT_IMPLEMENTED / NOT_RUN。Codex 与真实学习效果仍按 CURRENT.md:50–51 单列 NOT_RUN。

## 规范执行规则

- §18.4，PRODUCT_DESIGN.md:885–889：不得自动合并；用户/指定审查者批准且必需检查通过后合并，Issue 才 done/关闭。下一阶段确需代码时，允许从已验证本地基线上继续，清楚记录依赖 PR，不能声称 main 已有。故 CI 全通过不等于合并，也不要求为了未合并而停止全部本地后续实施。
- §19.1，:903–907：已有工程直接续做；普通实现细节用短 ADR，不重新建项目/第二套需求。单次执行资源不足时保存准确检查点，下次从 next_task_id 继续；不能宣称结束后仍有未来后台任务在运行。此条是保存恢复点的规定，不是已经执行完 M5.3 或整个目标的证明。
- §18.3，:879–881：一个 active 主任务，明确当前代码/spec/证据与下一行动。若 ab6 CI 未终态或失败，检查点必须保留 M5.2 的剩余检查/失败恢复；不能只写 next_task_id=M5.3 便绕过它。若明确保存“当前M5.2等CI/下一M5.3”，恢复时应先核前者是否已解除。

## 新 ab6 CI 若确实全部通过后的建议状态

条件尚待根代理真实远端回读，本报告未查询 GitHub，绝不预填 PASS 或 run/job ID。确认精确发布 head、两 workflow 的实际 jobs/log 及必要 PR 检查均通过后，可写：

“M5.2 本地固定代码 d65 验收通过，发布 head ab6 的实际 CI 已通过，相关原失败及修复边界保留；PR50 等待审查、保持未合并，Issue27 为 review。按 §18.4 在该已验证基线上恢复 M5.3，并明确依赖 PR50；不称 main 已具备此代码。M5.3 首项为按唯一规范闭合 Thread/Tutor Run/Context 与 Provider owner 的应用契约，然后实现持久状态机、唯一终态、SSE 断线回放/取消及跨标签上下文隔离。当前平台 Agent 仍 NOT_IMPLEMENTED，端到端及真实模型/搜索评测仍 NOT_RUN，随后按各实际测试逐项更新。”

对应任务转换：M5.2 in_progress→review；M5.3 todo→in_progress（明确未合并依赖例外），active_task_id=M5.3；更新 next_task_id/next_action 为实际可恢复的首项而不是只给泛称。若仅准备检查点未开始 M5.3，则不提前标已有实现提交。M5.4 的真实模型/搜索验收仍单独执行，不将已有用户授权误说没有授权，但当前未实现链路不能靠独立 vendor 成功替代。

本地 progress 的较早详细说明（state.json:915、948、1212，M5.2-next.md:11）仍有“新修复待发布/新CI NOT_RUN”等旧时态，而顶层 next_action 已写读取 ab6；下次同步应将这些整理为历史事实与当前终态，不抹掉 73d 原失败。这是状态文字待收口，不是新代码阻断。
