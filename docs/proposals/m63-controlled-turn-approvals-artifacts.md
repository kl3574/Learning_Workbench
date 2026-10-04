# M6.3 受控 turn、逐操作审批与产物回导合同补充提案

状态：**PROPOSED / NOT_APPROVED / NOT_IMPLEMENTED**。本文件不是第二份产品规范，未获批准前不能据此开放模型、工具、网络或改动运行合同。批准后的语义应纳入根 `PRODUCT_DESIGN.md`，本文件保留为提案历史。

## 1. 来源、范围与需要批准的差异

唯一规范是 `PRODUCT_DESIGN.md` v3.0.14，SHA256 `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`，本次已完整读取。源码基准为 `b3bbf8d9c4a1c9065be501497ba9b7117a21acf2`。另核当前仓库内已封的 `progress/evidence/2026-10-03/M6.3-next-client-fallback-contract-inventory/inventory/REVIEW.md`，其旧源码范围不作为当前实现通过的证据。协议依据仅为固定 CLI 0.160.0 已离线生成的 schema；没有运行 CLI、模型、账号、工具、浏览器、数据库或系统探针。

目标仍是 §6.6、§12.5、M6.3、AC-21：明确任务与来源，经真实许可生成，逐操作审批，在受限目录取得可核产物，只回导为待审草稿。客户端下载四项说明不是此集成的替身。M6.2 的审核、数学/来源批准、发布合同保持不变。

| 现行位置（v3.0.14 行号） | 现状 / 缺口 | 本提案请求批准的最小变化 |
|---|---|---|
| §20.16，1364–1486；A，2322 | bootstrap 只准 `allowed_actions=[]`，GET session 的 active_turn_id 恒 null，revision 仅初始化 1 / 终态 2，三个 flags 恒 false | bootstrap 请求、原记录、原 ACK、旧解码器全保留；仅当前 session 投影增加真实 turn 控制修订语义，允许受检的 active_turn_id 与逐项产品能力 |
| A，2074；§20.5，1021–1068 | 原 turn 请求只有 message/refs/session CAS，没有授权前真实 Job 输入与新许可来源 | 新增零执行的 turn 准备，原 POST turns 改为明确消费准备和**新外发许可**；原尚未注册的三字段发送形状不提供兼容执行旁路 |
| §20.5；A，1955–1968 | M5.1 预算固定 provider_calls=1、search_calls=0、tool_calls=0；Codex 未注册，普通文本适配器不能证明 App Server 的完整请求 | 普通 Provider DTO/历史不变；Codex 使用独立具名外发 DTO/账本适配层，仍每份许可至多一次完整模型请求；仅增加有限本地工具额度和逐操作批准，不授予自动模型续调 |
| A，2069；B，2619–2648 / 2703–2706 | 只有 ApprovalDecision、粗 RunSnapshot / approval_id，没有可读取的完整操作与 Job/Run/turn 绑定 | 新增 GenericApprovalView 读口，补决定 ACK、操作执行状态与真实绑定；原未实现的决定响应细化为具名 ACK，54 core 不变 |
| A，2075 | interrupt 请求有 turn/session CAS，缺失权控制、真实交付与未知恢复边界 | 保留请求与响应字段，补一次减权命令、零重启、局部/上游中断事实的区别 |
| A，2076；B，2370–2384 | 回导已有 turn/ids/manifest SHA，但没有清单读取、审查事实、选中文件与 Import 子任务归属；learnpack Manifest 要求 root_course | 新增独立 Codex 产物清单及批量回导读口；复用正常 Import 的 stage/preview，绝不把任意文件硬套为学习包 |
| D，3049–3054 | 粗 BrokerPort 的 prompt/approvedPaths 不足以证明上述身份 | 新增闭合应用/内部 owner 端口；粗端口不能绕过新的持久资格与准入 |

以下全部是待批准的具体选择，不称为 v3.0.14 已有细节。没有 login UI、导入全局 CLI 账号、动态插件/MCP、子 Agent、远端连接器、任意宿主目录权限或自动发布的新目标。真实账号/费用验收仍需独立授权。未知结果不以新 key 自动重试。

当前源码接缝也已逐项静态读回，不能把它们误记为本提案已实现：`interfaces/codex_bootstrap_http.py:22–51` 只注册五个 bootstrap/session 操作；`interfaces/codex_http.py:17–28` 是能力读口；`codex_bootstrap_dto.py:43–46,122–133` 仍为 false-only/null-active-turn 与 r1/r2；`application/codex_bootstrap_access.py:9–19` 已区分安全控制 GET 与 author/Policy 写；`infrastructure/codex_bootstrap_runtime.py:89–101` 只有 initialize/initialized/thread-start 冻结帧。`main.py:102–105` 的真实 source 只有 Tutor/Authoring 且生产 ProofRegistry 为空，`application/provider_budget.py:181–185` 拒绝 codex purpose；`application/jobs.py:125–163` 没有新的 Codex Job owner 分派；`application/artifacts.py:24–56` 的受检 ArtifactReader registry 与 `application/imports.py:153,230` 的真实 stage/preview 是应复用的端口。不存在“现有 Codex 线程一创建便获得这些能力”的实现依据。

## 2. 执行单位：一次模型请求，不是无限 Agent 循环

一个产品 turn 对应一个真实 `kind=codex_turn` 的 Job 和一个 Codex-owned Run；`run_id=job.id`，`turn_id` 是稳定本地 Id，不是外部 thread/turn ID。一个 session 同时最多一个未终态 turn，包括等待外发许可和等待工具审批。外部 ID、进程身份、原始控制帧仅在 Broker 私有记录中，HTTP 不下发。

一次 turn 的模型额度固定 `max_provider_calls=1`，搜索固定 0；工具是单独有限预算，默认 0、显式可选 1..16。工具额度不授权任何具体操作。只有冻结、展示、逐项 approve_once 的本地 command/file_change 可执行；一次批准最多消费一个操作槽，拒绝不消费执行槽，已开始而结果未知保守计一次。固定 turn 总 wall 上限由请求明确给出，1..300 秒，从首次实际受控执行开始按单调钟计时，等待人工批准仍计入；排队不计时。未开始批准对象的独立到期时间不晚于 turn 截止时间。

App Server 若在第一次模型响应后要求下一次模型请求（包括工具结果反馈、重试、补全、压缩总结、隐藏辅助请求），Broker 必须在任何字节离开前阻断；本 turn 保存已发生事实，结束为 `failed`，原因 `CODEX_NEW_OUTBOUND_CONSENT_REQUIRED`，不得把它称为正常完整回答。用户可从已保存事实明确建立**新 turn、新冻结输入、新 proposal、新 consent**；旧 turn/许可不续用。已经受检完成的本地工具产物可按第 7 节独立标明来源 turn 未成功的事实供选择；不因有文件把旧 turn 改成 completed。

这是本提案对首个完整工具链的明确上限。将来若需要一个 turn 内多次模型请求，须另有逐请求完整冻结/批准合同；本提案不授予这种隐式循环。单次模型输出可请求多项工具，仍受 16 次总上限、逐项批准、执行事实和固定截止时间限制。

### 2.1 外发保持 §20.5 的强边界

Codex 外发 owner 必须重用既有 Provider/SecretStore/ProofRegistry 的具名可信端口。HTTP 不能提交可信 proof、SDK config、账号、endpoint 白名单或 CLI 参数。生产注册没有完整证明时，允许保存真实本地准备 Job，但外发 preview/批准/开始均不可成功；显示 `CODEX_INPUT_PROOF_UNAVAILABLE`，实际传输为零。

完整证明绑定真实最终模型请求的**完整原始字节**，包括固定 CLI/adapter 版本、模板、完整所选历史、工具定义、所有文件材料、隐含协议包装、模型/容量/输出约束、目的地和配置/秘密版本。仅 `turn/start` JSON、主题字符数、CLI token usage 通知、普通 tokenizer 或 bootstrap schema 均不构成 InputProof。每次实际请求须能与已冻结字节逐字核验；不能先发出再发现不同。

新 Codex 请求 profile 必须在代码审查过的 registry 中实现可复算 `local_exact` 或 `local_upper_bound`，满足 §20.5 的完整输入与 shared-context 约束，冻结最大输出，并在受控适配器边界强制一次请求、禁止重试、禁止重定向、禁止隐藏额外请求。CLI 不能提供可验证的冻结材料或强制边界，就保持该 profile unavailable；不能以“上游承诺大致相同”或拦截到首包后追认许可替代。

只允许登记的模型目的地。命令进程、文件操作和一般工具仍零网络；网络/权限扩张请求记录为不可批准操作，安全拒绝，不用模型 consent 开放任意域名、浏览器、搜索或 shell 网络。原 `ProviderAdapter` 与旧预算/summary wire 不变；新 Codex adapter 不是把 `official_responses` 字符串贴到不相同的 App Server 请求上。

### 2.2 运行 profile 与 session 复用

新的 turn runtime profile 与 bootstrap profile 分开版本化，冻结二进制及部署闭包、协议 schema 全引用闭包、配置/环境、目录与原 session 映射、实际初始化/resume/turn 请求、完整历史输入、强制网络边界及资源限制。新准入逐项核当前事实；历史按冻结版本解码，不因当前 profile 更新破坏旧 ACK。

首个 profile 资源上限：wall 取批准值≤300 秒，累计 CPU≤60 秒、内存≤2 GiB、允许产物总量≤16 MiB、单文件≤16 MiB、打开 FD≤128、受控进程总数≤16、core=0，协议 stdout/stderr 合计≤16 MiB。实际值显式进入冻结摘要，不能将 bootstrap 的 8 秒控制验收外推为这些新资源均已实现。无法强制的资源项使整个 profile unavailable，不降级到普通宿主执行。

允许在**新 turn 消费提交后**用受检控制协议载入原已确认 session thread；只能核验并恢复本机拥有、无未知未决执行的确切映射及冻结历史，不能自动补建 thread 或启动旧 turn。若上游仍会把所选窗口之外的历史、工具输出、自动摘要或目录内容加入真实模型请求，而适配器不能逐字消除并证明完整实际输入，则拒绝复用；不能只在 UI 隐去这些材料。用户可明确另建全新 bootstrap/session；这不修改旧未知或失败事实。GET 永不调用 thread/read、resume、turn/start 或补记录。原 session bootstrap=failed/unknown 的对象不能因新 turn 请求升级 ready；需要用户另行本地准备/批准新 session。

## 3. 严格 DTO 与路由

下面全部为独立应用 DTO，字段全 required，nullable 显式 null，拒额外字段、重复 JSON 键、孤立 surrogate、bool 冒充数字、非有限数。Id/Revision/Sha256/UTC/JobRef/ContentRef/ApprovalDecision 沿唯一规范。SafeCode 是以下封闭枚举及原 ProviderFailureCode 的具名 union：CODEX_PROTOCOL_INVALID、CODEX_PROFILE_CHANGED、CODEX_RUNTIME_UNAVAILABLE、CODEX_BINDING_INVALID、CODEX_HISTORY_DAMAGED、CODEX_INPUT_PROOF_UNAVAILABLE、CODEX_OPERATION_UNSUPPORTED、CODEX_NEW_OUTBOUND_CONSENT_REQUIRED、CODEX_TIMEOUT、CODEX_RESOURCE_LIMIT、CODEX_CANCELLED、CODEX_OUTCOME_UNKNOWN、CODEX_OPERATION_FAILED、CODEX_ARTIFACT_REJECTED、CODEX_ARTIFACT_MISSING、CODEX_SOURCE_CHANGED、CODEX_SOURCE_UNAVAILABLE、CODEX_APPROVAL_EXPIRED、CODEX_CONSENT_EXPIRED、CODEX_CONSENT_REVOKED、CODEX_BUDGET_EXCEEDED、POLICY_DENIED、ASSESSMENT_ACTIVE；不能装原错误文本。所有数组有界并校验唯一/冲突和原顺序；不通过开放 `any`/dict 建运行合同。

### 3.1 准备、新许可、开始

```text
CodexLocalToolBudget = {
  max_tool_calls: integer[0..16], wall_seconds: integer[1..300]
}
CodexTurnRuntimeSummary = {
  profile_sha256: Sha256, cpu_seconds: 60, memory_bytes: 2147483648,
  file_bytes: 16777216, protocol_output_bytes: 16777216,
  file_descriptors: 128, processes: 16, core_bytes: 0,
  command_network: denied, writable_area: turn_outputs
}
CodexTurnPrepareWrite = {
  message: nonblank string[1..8000], context_refs: ContentRef(entity=block)[0..8],
  expected_session_revision: Revision, provider_id: Id,
  tools: CodexLocalToolBudget
}
CodexTurnPreparationSummary = {
  context_snapshot_id: Id, snapshot_sha256: Sha256, job_input_sha256: Sha256,
  prepared_input_sha256: Sha256, runtime: CodexTurnRuntimeSummary,
  character_count: integer[1..12000],
  materials: ReferenceSummary[0..8], history_turn_ids: Id[0..2],
  tools: CodexLocalToolBudget, warnings: Warning[0..32]
}
CodexTurnPreparationView = {
  id: Id, preparation_sha256: Sha256, actor_session_id: Id,
  session_id: Id, session_revision: Revision, turn_id: Id, job: JobRef,
  request: CodexTurnPrepareWrite, summary: CodexTurnPreparationSummary,
  created_at: UTC, proposal_id: Id|null, consent_id: Id|null,
  validity: current|changed|unavailable|closed
}
CodexOutboundBudgetWrite = {
  max_input_tokens: positive integer, max_output_tokens: positive integer,
  max_provider_calls: 1, max_search_calls: 0,
  max_cost_usd: finite number>=0|null
}
CodexOutboundPreviewWrite = {
  preparation_id: Id, preparation_sha256: Sha256,
  expected_job_revision: Revision, expected_provider_revision: Revision,
  budget: CodexOutboundBudgetWrite, expires_at: UTC
}
CodexFrozenOutboundSummary = {
  version: codex-outbound-summary-v1,
  preparation_id: Id, preparation_sha256: Sha256,
  session_id: Id, turn_id: Id, job_id: Id,
  source_job_revision: Revision, source_input_sha256: Sha256,
  provider_id: Id, provider_revision: Revision, config_sha256: Sha256,
  adapter: codex_app_server, adapter_version: nonblank safe string,
  endpoint: nonblank normalized model endpoint, endpoint_policy: EndpointPolicy,
  model: nonblank safe string,
  context_snapshot_id: Id, context_snapshot_sha256: Sha256,
  input_sha256: Sha256, request_body_sha256: Sha256,
  messages: MessageSummary[2..6], references: ReferenceSummary[0..8],
  input_character_count: integer[1..12000], input_token_assurance: InputTokenAssurance,
  budget: CodexOutboundBudgetWrite, tools: CodexLocalToolBudget,
  runtime: CodexTurnRuntimeSummary, cost_estimate: CostEstimate,
  created_at: UTC, expires_at: UTC
}
CodexConsentProposalView = {
  id: Id, proposal_sha256: Sha256, summary: CodexFrozenOutboundSummary,
  validity: current|stale|expired|unavailable,
  consent_id: Id|null, warnings: ProposalWarning[]
}
CodexConsentCreateWrite = {proposal_id: Id, proposal_sha256: Sha256}
CodexConsentCreateAck = {
  id: Id, revision: 1, status: active, actor_session_id: Id,
  proposal_id: Id, proposal_sha256: Sha256, summary: CodexFrozenOutboundSummary
}
CodexConsentView = {
  id: Id, revision: Revision, status: active|revoked|expired,
  actor_session_id: Id, proposal_id: Id, proposal_sha256: Sha256,
  summary: CodexFrozenOutboundSummary,
  created_at: UTC, expires_at: UTC, revoked_at: UTC|null,
  dispatch: CodexDispatchView|null
}
CodexDispatchView = {
  id: Id, job: JobRef, started_at: UTC|null, finished_at: UTC|null,
  consumed_provider_calls: integer[0..1], input_tokens: integer>=0|null,
  output_tokens: integer>=0|null, elapsed_ms: integer>=0|null, cost: UsageCost,
  outcome: completed|failed|incomplete|cancelled|unknown|null,
  error_code: SafeCode|null
}
CodexTurnStartWrite = {
  preparation_id: Id, preparation_sha256: Sha256, consent_id: Id,
  expected_session_revision: Revision
}
CodexTurnStartAck = {turn_id: Id, session_revision: Revision, job: JobRef}
```

| 操作 | 严格响应 / 语义 |
|---|---|
| **新增** POST `/codex/sessions/{id}/turn-preparations` | 202 CodexTurnPreparationView；建立真实 Job/Run/context、预约 session 的唯一活动 turn；零 CLI/模型/工具/网络 |
| **新增** GET `/codex/turn-preparations/{id}` | CodexTurnPreparationView；当前 GET，零写/执行 |
| **新增** POST `/codex/consent-previews` | 201 CodexConsentProposalView；受检完整输入计量，无 proof 则拒绝；零外发 |
| **新增** GET `/codex/consent-proposals/{id}` | CodexConsentProposalView；纯读派生资格 |
| **新增** POST `/codex/consents` | 201 CodexConsentCreateAck；仅原 actor 明确批准一份冻结 proposal，零执行 |
| **新增** GET `/codex/consents/{id}` | CodexConsentView；原事实与当前资格，纯读 |
| **新增** POST `/codex/consents/{id}/revoke` | 原 `{expected_revision}` → MutationAck；减权控制；不退回已消费额度 |
| **修订** POST `/codex/sessions/{id}/turns` | CodexTurnStartWrite → 202 CodexTurnStartAck；消费已批准新许可，Job 从 awaiting_approval 到 queued；ACK 不证明外部执行或完成 |

单独命名 Codex 许可路由的理由是保持已实施 Provider 十个操作及严格历史 wire 不变。逻辑上仍是同一个 Provider-owned 外发授权/计量 owner，通过独立具名模型与 source adapter 实现，不能另造不检查 ProofRegistry 的“Codex 许可”。普通 Provider consent、bootstrap consent、其他 turn 的 consent 均拒绝；引用同一 provider/secret 也不是可互换的许可。

prepare 的 message 原 Unicode 标量字符串与 refs 原序冻结；refs 只取真实公开 block 精确修订，Content owner 核正文/metadata/provenance。当前正文来源不支持 question/私解/任意文件路径。历史只取该 session 最近至多两条已 completed turn 的完整真实 user/answer，共≤4条消息；失败/未知/拒答/工具原输出不自动成为教学历史，全部纳入需要新明确 message/refs 及新预算。本次 message 与系统模板不可裁；来源/历史只可整项省略并在准备中新增的固定 Warning 说明，不能静默改变条件。完整消息/包装≤12k codepoints 只是 UI/资源上限，仍需完整 token proof。

prepare 在同一事务预约 session：旧 revision 412；已有活动 turn 409。成功使 session revision +1，active_turn_id 指向真实新 turn；返回的 session_revision 是新基准。Job 初始 awaiting_approval。准备本身不在任意时钟到期时自动写关闭；可用原 Jobs cancel 明确结束。proposal 期限由用户给出且晚于当前时间，不得超过创建后10分钟；该上限是本提案新增选择。grant、start、dispatch 各自重新核 actor/Policy/source/profile/provider/secret/proof 以及当前历史；原命令回放先核自身完整历史及当前访问，再按原命令返回原 ACK。

一份准备至多建立一个 proposal、该 proposal 至多一份 consent；不同 key 再建/批准409，原 key 原命令回 ACK。需要改预算、替换失效 profile 或给过期许可重新授权时，先明确取消未开始的原 Job，再建立新准备；不在原 turn 修改冻结材料。GET 的 proposal_id/consent_id 只投影真实已绑定事实，不改变 preparation_sha256。Codex profile 只能引用与实际目的地/协议/模型相符的 Provider 配置；原 compatible_chat/text 请求适配器不能因有同一密钥自动改称 Codex adapter。

consent 初始 r1/active，撤销按强CAS推进 r+1；纯读取过期或 dispatch 进展不改授权 revision。消费在唯一 dispatch/turn ledger 中保守记录，不重发 grant、也不将其重新变为未消费；status=active 不意味着可再次使用。首次实际开始前到期/撤销拒绝；开始后更早停止但真实终态仍保存。grant 的 proposal_sha256 不符沿既有许可强比较语义为412；准备/操作/跨对象绑定错误409，与普通 expected_revision 的412区分。

preparation_sha256 对 `{version:"codex-turn-preparation-v1",workspace_id,actor_session_id,session_id,turn_id,job_id,request,summary,created_at}` 的项目规范 JSON。summary 绑定完整私有 runtime 和实际已持久输入，而不只是 UI 摘要。proposal_sha256 对 `{version:"codex-consent-proposal-v1",workspace_id,actor_session_id,summary}`。不把动态 Job status/revision、derived validity 或后来的执行事实塞回旧 hash。summary.source_job_revision 保留最初依据；普通租约/status 进展单独核验，不用它推翻未改变的输入。

start 同事务绑定唯一许可消费、准备/turn、原完整命令与原 ACK、Job queued、session revision +1；active_turn_id 不变。实际派发另由 Jobs 租约+开始许可与 Provider/Broker 自有 dispatch 唯一记录线性化，开始记录在任何 CLI resume/turn 或外发前提交。实际模型请求额度从可能外发前保守消耗；不能因 worker 未收到 ACK 换新实例再发。已排队许可被撤销/过期时安全终结未执行，不能暗换许可。

## 4. 当前 session/turn、事件与未知恢复

bootstrap 原 create ACK 的 revision=2、flags=false 永不改写。**当前** `CodexSessionView` 字段名称保留，`active_turn_id` 从仅 null 扩为 `Id|null`，`capabilities` 三项从 false-only 扩为 boolean；status 仍只描述原 bootstrap 的 initializing/ready/failed/unknown。没有 turn 历史的旧 session 仍按原 r1/r2 校验；有新 turn 控制历史时 revision 从已确认 ready/r2 单调推进。不能从新代码当前 defaults 给旧 ACK 增字段。

session revision 只在预约 turn、消费开始命令、首次中断请求、turn 唯一终态释放活动槽等持久控制变化时 +1；普通流 delta、工具审批与用量按各自 revision/seq 递增，不暗改 session CAS。终态释放只能清除仍等于该 turn 的槽，不能清新 turn。GET 派生过期/能力不改任何 revision。capabilities 仅反映当前部署真正实现且可核验的产品操作；上游 schema 自报支持、账号 authorized=true 或 bootstrap=ready 均不自动点亮。它们不授予任何 turn/操作许可。

```text
CodexTurnControlView = {
  id: Id, session_id: Id, actor_session_id: Id,
  job: JobRef, job_revision: Revision, run_revision: Revision,
  last_seq: integer>=0, cancel_requested: boolean,
  execution: not_started|active|terminal,
  outcome: completed|failed|incomplete|cancelled|unknown|null,
  approval_ids: Id[0..64], manifest_id: Id|null,
  created_at: UTC, started_at: UTC|null, finished_at: UTC|null,
  error_code: SafeCode|null
}
CodexTurnPage = {items: CodexTurnControlView[0..100], next_cursor: nonblank string|null}
CodexTurnResultView = {
  control: CodexTurnControlView, preparation_id: Id,
  answer_markdown: string[0..400000], output_sha256: Sha256|null,
  output_state: none|partial|complete, usage: UsageSnapshot,
  mathematical: NOT_RUN, sources: NOT_RUN, independent_pedagogy: NOT_RUN
}
```

新增 GET `/codex/sessions/{id}/turns`（cursor/limit 默认20、最大100，拒未知/重复参数）→CodexTurnPage；按冻结创建序列上界和最后位置的 server cursor 回读，不因新 turn 漏/重旧成员；状态是读取时事实。新增 GET `/codex/turns/{id}` →CodexTurnControlView，新增 GET `/codex/turns/{id}/result` →CodexTurnResultView。前两者为有效 learner/author 可读的安全控制面；不含 prompt、标题、ContentRefs、操作正文或文件名。result 为当前 author 且无 independent/open_book 的学科读口；成功正文只是未审输出，不是 ContentRef。

新增 GET `/codex/turns/{id}/events` 仅回放本地事件，query `after_seq` 是可省略的非负整数，省略为0，SSE Last-Event-ID 与其一致性沿 §11.4；严格消息为 `{turn_id:Id,run_id:Id,seq:Revision,occurred_at:UTC,payload}`。payload 是闭合判别 union：`{type:status,job:JobRef,run_revision:Revision}`、`{type:answer_delta,text:raw nonempty string}`、`{type:approval_required,approval_id:Id}`、`{type:usage,usage:UsageSnapshot}`、`{type:manifest_ready,manifest_id:Id,manifest_sha256:Sha256}`、`{type:terminal,outcome:completed|failed|incomplete|cancelled|unknown,error_code:SafeCode|null}`。这是 author/当前学科许可通道，每批交付再核；失权关闭，不下发正文。seq 严格递增，重连只重放、零新执行；一个唯一 terminal，与 Jobs 终态同事务。普通 `/runs/{id}` 及 Tutor SSE 类型不改宽、不承接 Codex ID。

Job/Run queued/running/awaiting_approval 均参加 workspace 独立测试排他。真正 completed 需要完整受检模型终态、所有已开始本地操作有可靠结果、协议与资源检查通过、输出与账本完整；失败/未知不能由文件存在或 process exit=0 升级。outcome=unknown/incomplete 映射 Job.failed；未开始取消或已确认终止映射 cancelled，但仍另记已发生的模型/工具事实与未知费用。`output_sha256` 对实际保留回答 UTF-8 字节，null iff 无文本；流片段原字节不 trim。

恢复只读原 owner 事实：活动 owner/租约存在时不接管；owner 丢失且任何 start 已持久记录时，恢复原 Job 为 failed/unknown、关闭未发送批准、保存部分输出，零 CLI/模型/工具重发。即使缺 start 后完成回执，也不能凭“未找到外部 turn ID”判未执行。全部 GET 零修复。未知 session/turn 只能查看、取消本机等待或另建明确新准备；不通过 GET/重连/start 同键或新 key 恢复外部执行。全新 task 不继承未知旧 task 的同一次操作许可。

## 5. GenericApprovalView、精确操作与单次决定

GenericApprovalView 是 Codex 工具审批；不与 Provider 外发 proposal、Quality 数值审批、人类数学/来源 Review 混为一类。每个对象由可信 Broker 从当前进程实例的严格协议事实建立，本地 id 与原 RPC id、thread/turn/item、callback identity 完整绑定；上游 string ID 不直接当 HTTP Id。

```text
CodexCommandOperation = {
  kind: command, command_text: nonblank string[1..20000],
  cwd: canonical relative sandbox path,
  executable_sha256: Sha256, environment_sha256: Sha256,
  read_files: CodexOperationFile[0..64], writable_area: turn_outputs,
  filesystem_scope_sha256: Sha256, network: denied,
  operation_profile_sha256: Sha256
}
CodexOperationFile = {
  path: canonical relative sandbox path, size: integer[0..16777216], sha256: Sha256
}
CodexFileChange = {
  path: canonical relative sandbox path, action: add|update|delete,
  before_sha256: Sha256|null, after_sha256: Sha256|null,
  before_size: integer[0..16777216]|null, after_size: integer[0..16777216]|null,
  diff: string[0..400000]
}
CodexFileOperation = {
  kind: file_change, files: CodexFileChange[1..32],
  operation_profile_sha256: Sha256
}
CodexDeniedOperation = {
  kind: unsupported, category: network|permission_expansion|unbound_operation|unsupported_tool,
  reason: SafeCode
}
GenericApprovalView = {
  id: Id, revision: Revision, actor_session_id: Id,
  session_id: Id, turn_id: Id, run_id: Id, job: JobRef, job_revision: Revision,
  operation: CodexCommandOperation|CodexFileOperation|CodexDeniedOperation,
  operation_sha256: Sha256, created_at: UTC, expires_at: UTC,
  decision: pending|approve_once|decline,
  validity: current|expired|changed|unavailable|closed,
  execution: not_started|started|completed|failed|unknown,
  decided_at: UTC|null, started_at: UTC|null, finished_at: UTC|null,
  result_sha256: Sha256|null, error_code: SafeCode|null
}
GenericApprovalDecisionAck = {
  id: Id, revision: Revision, actor_session_id: Id,
  operation_sha256: Sha256, decision: approve_once|decline,
  applied: true, session_id: Id, turn_id: Id, run_id: Id, job: JobRef
}
```

新增 GET `/approvals/{id}` →GenericApprovalView；原 POST `/approvals/{id}/decision` 使用原 ApprovalDecision，响应修订为200 GenericApprovalDecisionAck。两者拒 query/body 冲突和跨 owner ID，不能猜到数值 check 的 ID 就转发决定。GET 需当前 author/学科许可，但不因换 actor 改写历史；只有原准备 actor 可发 approve_once。有效同 workspace learner/author 可 decline 作为减权控制，决定另记真实操作者，ACK.actor_session_id 是本次操作者；不能把减权资格转作接管批准。decline 无需读取正文，UI 可从安全 turn control 的 approval_ids 操作；approve_once 必须明确展示当前完整操作。

pending r1；唯一决定 r2；批准后实际开始、结束分别推进 r3/r4（未开始直接关闭也有真实单独事件）；纯 GET 过期不升 revision。expected_revision 核审批对象 revision，412；operation hash/binding 错409；内部还核当前 Job 输入、活跃 turn、租约/取消、原 actor、Policy、未消费工具额度和固定 runtime。Job 动态 revision 不是本审批的 expected_revision，但错误绑定或不允许阶段必须拒绝。原 ACK 是决定事实，approve_once ACK 不称操作已执行；其后独立 GET。

操作 SHA 对 version、workspace、approval、原 actor、session/turn/run/job、完整冻结操作、原 callback/进程实例绑定、资源预算与期限的规范 JSON。私有字段可以参与 SHA，不能仅对前端 display 摘要重算。command_text 是完整实际 shell/argv 解释输入；`commandActions` 是 best-effort 描述，不能代替真实可执行身份。需要 shell 时冻结 shell 字节、实际 argv、非秘密环境完整值、工作目录、读写范围、工具代码闭包；操作不满足可核范围即 unsupported。read_files 枚举本次可读的全部学科输入与先前输出副本，运行库闭包由固定 profile 另列，不把目录通配读取藏在 hash 后；writable_area 的唯一映射是本 turn 输出区。向 UI 展示相对路径及完整命令、文件清单、固定资源/零网络范围，不把真实宿主路径/秘密嵌入文本；无法安全展示而不改原命令时不可批准。

file_change 必须从同一 thread/turn/item 的完整受检变更事实与 owner 实际文件读口取得 before/after 内容、hash/size/完整 diff；add 的 before 两字段为 null，delete 的 after 两字段为 null，update 均非 null。文件集合顺序、重命名等效的 delete+add 全冻结。仅有 `FileChangeRequestApprovalParams.itemId/grantRoot` 不足以批准；没有完整补丁不得猜空 diff，亦不执行后才追认。

安全相对路径规则沿 FileEntry：无绝对路径、反斜杠、`.`/`..`、冒号或非规范表示；还须阻止 symlink/hardlink/device/FIFO、路径碰撞和跨实例映射。工具只在本 turn 私有输出区写，不写宿主工作树、全局配置/秘密、产品数据库、原输入副本或其他 turn 目录。审批不授予 session-wide permission、execpolicy amendment、network policy amendment、grantRoot 或持久缓存授权。固定协议只能使用确切单次 accept；原 callback 重复返回原受检决定，绝不新执行。若上游 accept 不能限制为同一已冻结操作，保持 unavailable。

decline 后对应操作绝不执行，也不改走另一 shell/路径、换工具或自动另起模型调用。对于支持的上游协议优先用 cancel 终止该 turn，持久保存拒绝与受检终止事实；不能把仅已发拒绝误写为远端已取消。unsupported 操作保留 pending 可读对象但只允许 decline，approve_once 返回409 CODEX_OPERATION_UNSUPPORTED；到期/取消后 worker 只发送拒绝/停止，不提供执行 fallback。

决定与执行分开线性化：真实当前准入、原决定和命令 ACK 同事务；对原操作的 started 记录在发送 accept/执行前持久提交，并从工具预算保守扣一次。数据库锁不跨外部执行。收到 late 完成后始终保存真实结果，即使 actor/Policy 已变化；交付前再次核当前权限，不向失权用户返回正文或成功操作详情。已开始后未知不能改回 not_started 或重放 accept；清理仅降权，不能补跑。

## 6. 受控 interrupt 与通用取消

原 POST `/codex/sessions/{id}/interrupt` 请求保持 `{turn_id,expected_session_revision}`，响应保持 `{id,turn_id,status:interrupt_requested|already_terminal}`；必需 Idempotency-Key/Origin/CSRF。有效同 workspace learner/author 在 independent/open_book 下仍可使用，零学科正文。错误 session revision 412，错 turn/session 409，未知/跨工作区404。先回放原完整命令；同 key 异 body409。

首次请求在 Jobs/Codex owner 同事务记录 cancel_requested、session revision +1 和原 ACK。awaiting_approval/queued 且未开始的任务直接安全取消并关闭未执行批准；正在执行时只向当前受检活进程的已绑定 thread/turn 发至多一个 interrupt 请求。不存在可靠活进程映射时不启动 CLI、不 resume、不猜最后 turn；保持请求事实，恢复按 unknown 终结本机任务。重复新 key 不再发送第二个 interrupt；若已有请求但未终态返回 interrupt_requested，若已终态返回 already_terminal。

上游 TurnInterruptResponse 空对象只证明控制回复，不证明所有进程/网络副作用已撤销。唯一终态须结合受检 turn 完成/中断、子进程终止与实际文件状态；无法确认记 unknown。原 `/jobs/{id}/cancel` 对 codex_turn 经同一具名停止端口完成该减权路径；不能由两个 owner 各发一条中断。开始后实际费用与部分产物不清零。

## 7. 产物清单、审查和普通 Import 归属

产物清单由 Broker/Artifact owner 在受控执行停止后、所有受控 writer 已退出且目录可稳定核验时建立；扫描发生在唯一 Job 终态提交前，GET 不启动扫描、复制、补登记或修复。先复制允许的普通文件至内容寻址受控 BlobStore 并核实际 size/SHA，再原子登记完整清单与来源事实、manifest_ready事件和唯一终态，terminal事件在后且不再追加生成事件。以后展示/下载/回导核这份不可变受检副本，不跟随 sandbox 文件后来变化。无法证明 writer 已停或扫描不完整就没有可导入清单。

只收本 turn 输出区内至多32个文件、总量≤16MiB。清单必须记录全部受检候选及排除原因，不把“跳过坏文件”说成原目录全通过；发现越界路径、链接/特殊文件、秘密/配置类文件或来源绑定损坏，整批拒绝并显示固定安全原因，无下载引用。检查范围只称安全/结构审查，不叫数学、来源或独立教学批准。

```text
CodexArtifactEntry = {
  artifact_id: Id, logical_path: canonical relative sandbox path,
  size: integer[0..16777216], sha256: Sha256, media_type: nonblank safe string,
  scan: PASS, import_kind: markdown|html|learnpack|null
}
CodexArtifactExcluded = {entry_id: Id, reason: SafeCode}
CodexArtifactManifest = {
  version: codex-artifact-manifest-v1, id: Id, revision: 1,
  session_id: Id, turn_id: Id, run_id: Id, source_job_id: Id,
  source_outcome: completed|failed|incomplete|cancelled|unknown,
  runtime_profile_sha256: Sha256, terminal_receipt_sha256: Sha256,
  scan_profile_sha256: Sha256, created_at: UTC,
  entries: CodexArtifactEntry[0..32], excluded: CodexArtifactExcluded[0..32],
  total_bytes: integer[0..16777216], mathematical: NOT_RUN,
  sources: NOT_RUN, independent_pedagogy: NOT_RUN
}
CodexArtifactManifestView = {manifest: CodexArtifactManifest, manifest_sha256: Sha256}
CodexArtifactImportWrite = {
  turn_id: Id, artifact_ids: Id[1..32], expected_manifest_sha256: Sha256
}
CodexArtifactImportItem = {
  artifact_id: Id, source_sha256: Sha256, import_id: Id, job: JobRef
}
CodexArtifactImportView = {
  job: JobRef, session_id: Id, turn_id: Id, manifest_sha256: Sha256,
  actor_session_id: Id, items: CodexArtifactImportItem[1..32]
}
```

新增 GET `/codex/sessions/{id}/turns/{turn_id}/artifacts` →CodexArtifactManifestView，确无登记清单404；有登记但损坏安全409，无法读取503，不回空成功。原 POST `/codex/sessions/{id}/artifacts/import` 请求字段保持，响应保持202 JobRef；新增 GET `/codex/artifact-imports/{job_id}` →CodexArtifactImportView，供回读真实 Import 子项。全部 author/当前学科许可；download 复用 `/artifacts/{id}/download`，须注册真实 Codex ArtifactReader、核 owner/membership/实际副本字节，不赋予任意 blob 读权限。

manifest_sha256 对完整 manifest 规范 JSON，自身字段在 view 外；所有项唯一、原序，total_bytes=entries.size之和。HTTP 不接绝对 path、任意 filename、blob locator 或自报 scan PASS。`import_kind` 由版本化白名单按实际内容/MIME核验；只开放既有 Import 真正支持的 Markdown、HTML、learnpack；其他允许保存的安全文件为 null，只可受控下载。learnpack 必须自己满足原 Manifest/root_course/全部字节校验，不能把清单当 learnpack。空清单可表达没有可用产物，但不能发回导。

terminal_receipt_sha256 绑定 Broker 的受检执行终结事实（精确 session/turn/Job、唯一开始、模型 receipt、各实际工具结果、进程停止及输出 hash），该执行 receipt 不反含 manifest SHA；随后清单单向引用它，Job 结果引用两者，避免自指哈希。scan拒绝使本机Job失败并保存安全原因，不篡改已发生的模型completed/usage或工具结果；不能因产物审查失败重跑模型。

用户在当前清单看到具体文件/来源 turn 终态/未审说明后选择并明确回导；该 POST 是本次选择的确认，不产生人工质量 Review。expected_manifest_sha256 不符412，非本清单 artifact、错 turn/session 或重复 ID409；原 key 原完整 body 回原 ACK，同 key 不同选择409。只有 completed/failed/incomplete/cancelled 且已可靠终止并完成扫描的 turn 可回导；source_outcome=unknown 可保留受检清单作诊断，但禁止回导，避免把未封闭副作用当可靠来源。

回导创建一个真实 `kind=codex_artifact_import` 的本地聚合 Job；Import owner 为每个所选 artifact 创建真实 staged Import/source/子 Job。同一事务保存聚合成员与全部 stage 关联；若任一文件准入失败，全批零 stage、零 Job、零清单消费；字节预存失败或事务回滚不留下可被浏览器访问的孤儿。相同文件重复的新 key 需明确新命令，可产生新预览，不能复用他 actor 的已确认命令。聚合 Job 只负责本地准备预览，所有子项成功 preview_ready 才 completed；某项失败时保存各真实状态而不自动 commit。

CodexImportBinding 私有闭合记录绑定 `{version,workspace_id,actor_session_id,session_id,turn_id,source_job_id,terminal_receipt_sha256,manifest_id,manifest_sha256,artifact_id,artifact_sha256,artifact_size,aggregate_job_id,import_id,import_job_id,source_id}`，由所属 owner 端口逐项核验，不能从名称猜“模型产物”。原 Import source/input SHA 必须等于实际选中 artifact 字节，原 GET imports 返回同一预览；source/current/prior ACK 不被后来 sandbox 文件改变。对外 provenance 仍如实标记用户选择回导的未审模型材料，不能称原生人类撰写、已验证引用或新的独立学习证据。现有 import/history 字节不批量补默认字段，新 binding 在所属 forward migration 独立保存。

回导**止于 preview/draft**，随后由用户走原 Import 确认和 M6.2 Review/人工数学来源审校/发布。旧 JobSnapshot.result_refs 不塞 artifact、manifest、import ID；它们只能通过上述具名读口回读。产物取消/拒绝、重新生成、旧结果失效均不删除历史事实，也不替换已审 candidate。

## 8. owner、访问、幂等和持久完整性

| owner | 权威事实与具名协作 |
|---|---|
| Session / Policy | 当前 actor/workspace/角色、independent/open_book 与活动学科任务排他；所有跨阶段交付再核 |
| Authoring/Codex turn application | 原任务输入、prepared context、Run 和 turn/session 控制关联；为 Provider 提供真实 OutboundSourcePort，不跨 owner SQL |
| Jobs | 创建序列、claim/lease、取消、开始许可与唯一终态；控制列表不泄露 payload |
| Provider / SecretStore / ProofRegistry | 新 Codex summary/许可、完整输入证明、真实请求/目的地/配置/秘密、单次外发与用量/私有终态；不写 consumer Job/Run |
| CodexBroker | 原 thread/turn 映射、固定 runtime、实际控制/工具请求、逐操作批准执行/回执、IPC 与进程清理；不假造模型计量 |
| Content / Context | 精确公开材料、原正文/metadata/hash/provenance、冻结上下文与重核；不从 current 替换原 ref |
| Artifacts / Import | 受检字节清单/受控下载、stage/preview及新来源绑定；不授予 publish |

内部至少有受检 `prepare_turn/verify_turn/read_control/read_result`、`read_pending_operation/decide_once/claim_operation/record_outcome`、`read_manifest/read_selected_artifacts/stage_codex_artifacts` 和 `request_interrupt/recover_control` 端口。它们接收调用方真实 SQLite transaction 与可信 SessionIdentity；外部执行不持事务。Broker 自报对象/hash不是授权，端口必须从所属持久原件重核。所有闭合内部模型与版本/schema生成在实施时先固定，不以 Protocol 名称代替实现。

所有新写沿 Origin/CSRF/单个规范 Idempotency-Key。当前访问+完整 owner 历史核验在 replay 前，业务当前性/CAS在识别新命令后；命令包含完整规范 request、actor/workspace/route/目标，永久原 ACK 不受24小时通用回执过期影响。模型/工具动作的精确历史 ACK 可回放，不再次执行；错误 Envelope 的 request_id 可每次变化，不把稳定错误类别强行当全字节 ACK。operation/preparation hash或绑定409；expected_revision、grant proposal SHA、expected_manifest_sha256 的强比较412；schema422、缺/错关键header400、跨工作区/owner未知404、不可核环境503，错误仅安全 code/固定说明。

学科写/读/批准/外发：当前 author、无 independent/open_book；安全控制 GET/list、cancel/interrupt、revoke/decline：有效同 workspace learner/author，无正文。prepare/start/approve 操作者绑定原 actor，换角色或同工作区新会话不能承接旧许可。恢复浏览器命令须 page/access generation 和鲜读 actor/workspace/Policy 连续性证明，原 body/key不从当前输入重建；晚到 ACK归原命令，当前新输入不被删除。跨刷新只读原事实，明确重新批准才产生新命令。

失权在开始前阻止执行；开始后真实 ready/failed/unknown/usage/文件事实仍由 owner 保存，不能回滚或伪称未执行。交付前失权拒绝成功正文/201类学科响应，安全控制 GET 仍可看有限状态。停止/撤销允许更早终止，不能改已发生事实或退款。

新的 append-only owner 历史同时维护权威 head、全成员关系、版本/序列/hash链及跨 owner 关联；要检测尾删、全删、漏成员、错绑定，不仅检查剩余行互相自洽。每个 GET、命令 replay、开始和结果交付都经相应受检读口，坏历史不能重建成默认空状态。旧 bootstrap/Provider/Import/Review 原 JSON/hash/ACK 按旧 decoder 原字节保留；只加所属 forward migration，54 core/0001/学习包3.0.0不改。备份副本保留历史 actor、引用与可校验事实，认证不继承、许可不可执行；恢复后 GET 不重启外部任务。

## 9. 离线协议依据与不能从 schema 得出的保证

固定离线来源 receipt 标记 CLI0.160.0、binary SHA256 `12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad`、生成314个 schema、exit0。此事实仅是先前离线生成的来源，本次只读核对选用文件及完整内嵌 `$ref`，没有再次生成或运行协议。关键文件：

| schema | SHA256 | 对合同的约束 |
|---|---|---|
| v2/TurnStartParams.json | 2dfcf68705896fadc344ccfeb2e9fe5a6bcbbb8b9a90cf449ce232b636daf05a | input/threadId 必需；公开参数没有完整 token/总请求上限；可含多个非文本输入，产品不能全放行 |
| v2/ThreadResumeParams.json | c818e26d830ac4430791eab7d4a872d2384fa6006b14c505d8caf46e7e093527 | resume 独立且可改配置；产品 GET 不映射为此 RPC，实施须冻结完整覆写与历史 |
| v2/TurnInterruptParams.json | 6dff382dae73d1dbc58406ed045605f647e7a49660e2540fbd2c6c24d60c5f2b | threadId+turnId 必需，不可只停止“最后一个” |
| CommandExecutionRequestApprovalParams.json | 16a71816c2d66e319c2c4aa83dd636dfdc43c61e72b6d5475e421ce08d8e6558 | callback可缺command/cwd，commandActions仅best-effort；没有完整可核操作则不准批准 |
| CommandExecutionRequestApprovalResponse.json | 6d0767113e22f311381809b6b236b0dde2b99b01992879c26bf7b1ea0e003cb7 | accept与acceptForSession/持久policy amendment不同；产品只可确切单次accept |
| FileChangeRequestApprovalParams.json | 13848b26814c286ad6425a20d01c1691c86790e1f9e2529399677a8a22fe0d18 | item/thread/turn而无完整patch；grantRoot是扩大未来写权限，不等于本次批准 |
| FileChangeRequestApprovalResponse.json | b95b03ee6be674e25cee2e863cc135a28620e1070addd2f34685aadee27cde08 | 单次accept与acceptForSession不能混用 |
| v2/FileChangePatchUpdatedNotification.json | cfb69d18658610a0510f213e09c6847f70517410ed91cf99cc4713c15a795213 | path/kind/diff必须与同一真实item配对，通知本身不证明磁盘操作未先执行 |
| PermissionsRequestApprovalResponse.json | 23f3f24e9dbf35db3e0b85703f0d934da5a1cff3cbb611fba8bcd41f3b4a04b0 | turn/session permission scope不是逐操作approve_once，默认或nullable不作安全证明 |

公开 schema 只是协议形状，不证明通知时序、拦截点、隐藏模型输入、命令拒绝零执行、资源限制或产物来源。实施使用的实际固定响应可能包含公开非experimental schema未覆盖字段；须离线固定完整 schema/引用闭包并严格解码，不能放宽 additionalProperties 或忽略字段。未知方法、未配对事件、外部账号/路径/原错误不直传客户端；出错保存私有事实、返回受控错误，不“兼容猜测”。

## 10. 实施与最低真实验收

本提案获批仅授权合同实施，不等于取得真实费用/账号授权或证明 CLI 可满足强边界。第一步可完成 strict DTO/生成客户端、真实 SQLite owner/HTTP、受控协议 peer 与 UI，生产 registry 无证明时必须零外发。这不能关闭 M6.3；真实可调度链必须在独立许可和真实完整证明下另验，无法实现就明确 BLOCKED，不偷偷改预算或借普通 Provider 文本调用冒充 App Server 工具链。

最低矩阵（分别绑定固定源码/实际命令/原失败，不混合 PASS）：

1. 合同/读取：全部新 DTO required/closed、关联不变量、OpenAPI双向覆盖；旧54core、bootstrap/Provider/Import真实原JSON/hash/ACK逐字 oracle；当前 session/revision与原ACK区分；所有 GET全表hash不变、零CLI/外发。
2. 准备与许可：真实 HTTP prepare→当前GET→Codex preview/grant→显式start→Job/Run；新actor、错误SHA/revision、跨session/workspace、旧bootstrap/Provider许可、过期/撤销/重复消费均准确拒绝；并发两writer仅一个活动turn/消费，事务失败全回滚。
3. 输入/计量：完整模板/历史/refs/工具定义/配置/目的地/模型/secret/profile各变动拒旧许可；ASCII/中文/Unicode/重复文本计数；隐藏补充、额外模型调用、重试/重定向、无proof/过期proof必须零传输。测试 registry 与生产严格分开。
4. 审批：受控真实子进程或明确协议 peer 产生 command/file请求，先核配对完整操作；approve_once只一个动作，decline/过期/坏base/错callback/unknown零动作。file callback无patch不能批准；sessionwide/permissive选项不可用；控制peer PASS不冒称实际CLI零执行。
5. 生命周期：开始前与开始后撤权/Policy/取消竞态；事实持久保存、交付再核；断线/进程退出/恢复未知永不第二start/accept/modelcall。尾删/全删/membership破坏拒绝；两owner并发、崩溃与提交失败覆盖。
6. interrupt：原actor与同workspace减权新actor、queued与running/awaiting、已终态、旧CAS、两入口并发；最多一次真正interrupt，空ACK不假称远端完全停止，缺liveowner零CLI重启。
7. 产物/Import：真实受控writer的普通文件→停writer→有界扫描/受检副本→manifest GET→明确选择→正常stage/preview；SHA/size/路径/links/特殊文件/已变源负例；多文件事务全成或零stage；result_refs无伪ID，旧source/current/ACK不漂移，无自动commit/Review/publish。
8. UI/native：真实当前session/turn列表、操作完整展示、原actor与page/access/port/unmount晚到保护、原命令恢复、未发输入保护、明确许可/决定/回导；重启同DB只读回原事实，不重启旧动作。真实原生应用与受控上游分列。
9. 真正 App Server 与真实模型：固定binary/profile全闭包、严格完整protocol、实际计量与唯一请求、拒绝实际工具零执行、批准实际受控产物只进草稿、当前权限/重启读回。没有独立账号/费用授权或生产proof时 **NOT_RUN/BLOCKED**；不运行真实模型来“试出”安全默认值。
10. 原完整门禁失败、环境数值BLOCKED、教学质量NOT_RUN与新subset分别保留；只有后续同固定组合完整验收才可改变总体状态。提案/代码/CI/真实模型/实际数学来源审查五种结果不得互相替代。

审批者需要决定的是本文新增的具体会话控制修订、独立 Codex 许可 wire、单模型调用+有限逐项本地工具上限、可读通用审批、产物清单与回导归属。普通实现细节（随机ID、内部函数拆分、锁公平性）不再另造用户授权环节。批准前所有这些新路径仍关闭。
