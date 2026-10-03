# M6.3 / M7 下一本地切片只读核对

结论：下一主要任务选择 M6.3 的真实本机 Codex Broker 能力查询纵向切片，先于 M7.1。现行 v3.0.13 已给完整 GET /codex/capabilities 合同；不需把内部 CLI 版本固定、stdio 翻译或内部受检端口升格成新产品批准。可以从已验证本地基线推进，M6.2 数值/Provider 真实验收及泛型 Draft 继续 open；这不把 M6.2 或 M6.3 标 done。

## 当前状态及依赖

本次代码 HEAD、唯一规范 SHA 和可变 progress/state.json 的独立 SHA 见 SOURCE.json。root 正在封存概念切片；本审不修改这些文件，不将正在暂存的证据误称 HEAD 已有。M6.3、M7.1、M7.2、M7.3 均 todo、implementation_commit=null、verification=NOT_RUN。M7.2 仅有 progress/M7.2-bootstrap-followup.md 的历史有界初始化诊断待办，不是已证明生产缺陷。

§18.3 / PRODUCT_DESIGN.md:900 要求安全/数据损失阻断优先、其次最早可执行 P0，主实施最多一个；§18.4:908 允许在已验证本地基线上继续下一阶段并标依赖 PR，:910 不准用 mock/文档关闭真实集成。因此 progress 的顺序依赖不是“所有先前验收必须先绿才可做任何后续代码”的禁令，但仍须保留原状态与合并事实。最初把 M7.1 备份列为首选的排序已纠正：M6.3 能力查询有可执行合同，不应跳过它。

## 唯一下一任务与验收

实现真实受控本机能力探测 → 已有 GET /codex/capabilities → 创作辅助入口状态显示，完整字段严格使用 PRODUCT_DESIGN.md:2193：available、authorized、adapter_version|null、sandbox_roots[{id,label}]、capabilities{approvals,interrupt,artifacts}；默认 workspace_default 仅服务端映射真实路径。§6.6:353 的未连接提示在这一步可交付；完整任务导出/文件回导降级仍另列未实施，不能因只有提示就称降级全部完成。

已有前置：本机 Session/CSRF/Policy、真实 API/严格客户端/创作辅助入口、Jobs 独立测试排他、标准安全错误；代码 main.py:197–219 当前没有 Broker router；tests/security/test_local_boundary.py:207–208 当前明确 assert capability 路由 404 且不在 OpenAPI，实施后需有意义地更新该期待；provider_dto.py:55 只有 codex purpose 枚举，不代表已注册运行 owner。root 另行报告本机 0.160.0 CLI/stdio 可用，本审未执行或独立核验该运行事实。

本地实施硬前置是可固定的 CLI 协议和能安全取得版本/能力/授权状态的受控只读端口；这属于工程核验。能力未知不能假报支持或假报已授权；进程缺失、版本不支持、读状态失败要有真实有界结果/错误。不得为探测自动登录、创建 thread/turn、提交模型输入、运行工具、读取产品之外密钥、联网计数；账号状态只取官方受控只读投影，不把凭据返回或记录。GET 零业务写，模块导入/factory/OpenAPI 不启动进程或读秘密（§20.4:1021）；具体探测生命周期由实现选择。

最小验收：
1. 固定 CLI/source/spec 来源；真实无 turn 的本机控制协议读回，并与 API 和浏览器显示逐字段一致，不能常量假 available/authorized。
2. 缺 executable、unsupported adapter、unavailable/unauthorized、超时、异常输出均 fail closed；未启动模型/thread/turn/工具执行且没有外发，原错误不泄漏私有路径/凭据。
3. API 会话/跨 workspace/当前 Policy 边界，未知字段/query 的严格校验；无任意浏览器绝对 sandbox 路径；GET/readback 和刷新不造 job/session/approval。
4. 浏览器真实显示已连接与未连接/未授权状态，只有实际支持的能力才显示可用；尚未实现的会话/turn/审批/回导不出现假成功操作。旧 M6.2 路径继续相关回归。
5. 受控 adapter 测试标 synthetic；真实本机无模型控制握手与真实 Codex turn 验收分列，后者仍 NOT_RUN。父级 M6.3 issue 不关闭。

## 完整 M6.3 的后续边界

规范给了产品职责与主要 API，不能将整项称“缺规范无法开始”：§12.5:655–659、A1944–1948、2193–2194、core ApprovalDecision:2575–2578 和 AC-21:3390–3394 都有效。

但完整浏览器人工操作审批还未见闭合读取合同：RunEvent:2500–2516 的 approval_required 只有 approval_id；ApprovalDecision 必须提供 operation_sha256、expected_revision，A1944还要求 actor/expiry/任务版本与范围核验。A2194 session GET 没有待审批操作摘要/原操作 SHA/审批 revision/expiry。可检验反例：浏览器只收到 approval_id 后，无法由任何已列查询取得要批准的命令/文件/网络范围及真实 operation_sha256+expected_revision；不能猜值或把 JSON 偷塞 answer_markdown/text 冒充严格批准 DTO。这不是内部 adapter schema 的缺失，只有做到完整产品审批 UI 时才须补齐。

同理 A1948 import 需要 artifact_ids 与 expected_manifest_sha256，现行 A2193–2194、RunEvent/RunSnapshot 没有严格产物清单读回字段。反例：同 turn 有两个产物，浏览器现有响应不能知道各 ID/受控相对路径/hash/size 和应提交哪份 manifest SHA；内部扫描清单本身仍可工程实现，但浏览器可预览并选择回导需要明确可读投影。不能从笼统 artifacts:boolean 推导新 API/字段。

POST session 的 consent_id 必填（A1945）；§7:373 禁止凭任意 consent 外发，§20.5:1067 禁止借别的任务许可。当前 outbound registry 未有 Codex owner。首次 Codex source job 如何成为既有 consent preview 的真实绑定依据，需要在正向 session/turn 链实施前核通；本审不虚造 consent、不将 Provider codex enum 当完整 owner，也不据此阻塞无外发 capabilities。此项是待明确的源生命周期依赖，不断言需要用户再授权 CLI 安装/适配。

## M7 已有积木与后续顺序

M7.1 可复用 scripts/backup.py:23–106 的在线 SQLite 快照、blob 受控路径/hash、敏感个人全备份清单及 fsync；provider_backup.py:14–58 只作用独立副本，去授权而保留历史；tests/unit/test_backup_command.py:14–59/63以后已有 WAL/secret/路径/Provider 历史回读测试。README.md:58 已明示 make backup 不等于恢复通过。不要重写为新备份器或把 CLI 导出当 M7 完成。

后续 M7.1 full_backup→持久 Job→受控下载→辅助备份 UI 可依 A1448–1449、§20.6:1073–1075、§20.2:995、§15.1:732/§15.3:744 实施；ArtifactsService:37–57 已要求具名注册 owner、真实 blob/hash/current Policy，Jobs:19–27 已把未知活跃 kind 纳入测试排他。完整导出请求同时有 course_refs/include_personal_notes；实现不能无声忽略或自行替字段含义，需要在对应 profile 完整语义下严格处理。恢复预览/新 workspace 事务、learner/author 包与删除影响是仍未实现的独立范围，不随导出切片关闭。M7.2 可继续已授权安全/a11y/固定硬件测量，M7.3 的真实用户和内容审校需要真实参与者/材料证据；均不得替代 M6.2/M6.3 真实验收。

本次仅读源码、规范和状态；未运行产品、未读环境/密钥、未调用外部模型、未创建提案/改代码/改 progress/远端。
