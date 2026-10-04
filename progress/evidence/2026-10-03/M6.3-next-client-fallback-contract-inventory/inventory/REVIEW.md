# M6.3 next-contract inventory — fixed 1843556e

结论：可以直接实施一个尚未交付、无需新 HTTP 合同的最小 M6.3 fallback：**作者当前表单的四项需求 → 明确下载本地 Markdown 需求说明 → 用户自主准备文件 → 现有普通 Import 预览/Review**。§6.6 L350–354 已明确任务导出/文件回导目标；该窄范围只下载用户当页明确输入，不创建服务端任务/许可，不执行 Codex，也不声称导入文件与某个 Codex turn 有受检归属。真正需要补充的产品合同是下面的受控 turn、通用审批、带任务归属产物清单；它们不能阻挡纯客户端 fallback。

输入固定为 `1843556e1c01b48e60082969e78d2a82b3848b45` 的 34 个 Git 文件；唯一完整规范为 `PRODUCT_DESIGN.md` v3.0.14，4445 行，SHA256 `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`，与 canonical 规范全字节相同。当前 root 后续 progress/evidence/精确 attributes 提交不作为业务源码变化。SOURCE_BINDINGS.json 给每个原 blob/SHA256/字节数；本报告没有运行产品、CLI、测试、数据库或网络，没有新提案文件、源代码/规范/进度/远端修改。

## 当前实际边界

- 静态双向核 OpenAPI 与 runtime-route-coverage：六个 Codex 操作已注册；`POST /approvals/{id}/decision`、`POST /codex/sessions/{id}/turns`、`.../interrupt`、`.../artifacts/import` 四个目标操作明确未注册。ROUTE_INVENTORY.json 记录全部计数；注册数不是运行验收。
- `interfaces/codex_http.py:18–28` 与 `interfaces/codex_bootstrap_http.py:22–51` 是实际六路由；`main.py:139–145,222–224` 装配真实本地 runtime 与启动时 owner 恢复。不是占位 `CodexBrokerPort` 已经实现了所有功能。
- `codex_bootstrap_dto.py:42–46,120–133` 强制三 flags=false、active_turn_id=null、initializing/r1 或终态/r2；`application/codex_bootstrap_ports.py:7–24` 仅 freeze/validate/validity/execute/outcome。`infrastructure/codex_bootstrap_runtime.py:89–100` 仅固定 initialize/initialized/thread-start 控制帧；本报告只读代码，不重新评估或执行隔离机制。
- `application/codex_bootstrap_access.py:9–19` 保持当前合法工作区读者的安全 metadata GET，以及 author/无独立或开卷测试的新写权限；bootstrap 原 ACK 不等当前资格。`CodexBootstrapPanel.tsx:31–46` 展示该边界。规范 §20.16 L1370–1374、L1415–1426、L1467–1486 明确不授权模型、工具、正文读取、网络或后续 turn。

## 已有要求、可复用工程与真实缺口

以下 Python 文件相对 `services/api/app/`；规范行号均针对上述完整 bed7 文档。

| 下一目标 | 已有、不能重复索取的合同/端口 | 阻止直接交付的最小语义缺口与可检验反例 |
|---|---|---|
| 一个 Codex turn 及 interrupt | §6.6 L350–354、§12.5 L654–660、附录 A L2074–2075 已有 message/context_refs/expected_session_revision、JobRef、turn_id、interrupt_requested/already_terminal。现有 Session/Policy、Jobs.active_subject_work (`application/jobs.py:19–27`) 及通用幂等/终态/恢复原则可复用。 | 当前 §20.16 SessionView 永远 active_turn_id=null、flags=false，bootstrap consent 已消费且 actions=[]；规范没有把它转换为可发模型/工具请求的许可。须明确新 turn 的授权前冻结/许可与受检输入归属、session/turn 当前状态及 revision/读取关联，才能完成真实 begin→observe→interrupt。反例：拿一个 ready/r2 空动作 session 发 turn，若直接执行就越过原批准；若沿原 SessionView 隐去活跃 turn，浏览器无法核其真实控制基准。CLI frame 翻译、随机 ID、内部 ledger 版本都不是产品审批缺口。 |
| 真实操作审批，含仅 decline 的 UI 路径 | 附录 A L2069、ApprovalDecision L2703–2706 已有操作 hash、expected_revision、approve_once/decline；§12.5 要求显示权限/文件/网络范围，拒绝零执行；Jobs/Run 有 awaiting_approval 和唯一终态。 | 不存在 GenericApprovalView 或等价完整冻结范围的读取/事件形状及其与 Codex turn/Job/RunSnapshot 的公开绑定。core RunEvent 只携 approval_id (L2631–2643)，当前 Tutor 的该 ID 专门是 Provider proposal (L1726、L1738)，不能当任意 Codex 操作。反例：UI 只拿 approval_id/hash 即确认 command 或网络范围，用户实际上无从核批准了什么；自行复用 Provider proposal 或 bootstrap DecisionAck 会改变原响应/许可含义。只保存一条“decline”而没有真实待审操作不是纵向功能。 |
| Codex 产物预览与回导 | 附录 A L2076 已有 turn_id/artifact_ids/expected_manifest_sha256；§12.5、§10.2 L514–516 有沙盒路径、hash、大小、非可信导入约束。现有 ArtifactsService.read_in_transaction (`application/artifacts.py:35–58`) 验实际注册 owner、完整 manifest 与 bytes；Import 正常安全上传/预览已实现。 | 缺可供用户读回/选择的 Codex 产物清单及 artifact↔turn↔冻结文件/审查结果的公开绑定和版本/CAS来源；未定义该回导如何形成真实 Import 候选归属。现有 core Manifest L2375–2388 是必须含 root_course 的 learning-package，不是一个 turn 的多种产物清单；JobSnapshot.result_refs 只有 ContentRef (L1559)，不能塞待选 artifact ID。反例：两个 turn 产出同名 Markdown，单凭路径/裸ID或学习包 hash 无法从现有 wire 证明是用户预览的那一份。 |
| 未连接 Codex 的本地需求下载→人工文件回导 | §6.6 L354 已明确该降级目标；主题/先修/目标/proof_policy 是现成作者输入。附录 A L1569–1572 的普通 Import、GET /session 及现有权限/关闭保护可直接复用。 | **此最小客户端下载本身没有需新增合同的缺口。** 不把它注册为 POST /exports、server Job、GenerationInput 或 AuthoringRequest，不借 provider/consent，不包括 refs/教材正文。若进一步要求服务器冻结任务、自动打包材料或对返回文件建立原任务身份/质量关联，才超出此窄实现，需要具名交换与关联语义。反例：把纯下载称为已启动 Codex 或受检生成结果不成立；用假许可创建任务也不成立，但这些都不是下载按钮的必需步骤。 |

Provider 外发还存在独立工程/证据依赖，不能用 bootstrap ready 抵消：`main.py:101–104` 只注册 tutor/authoring、生产 ProofRegistry 为空；`application/provider_budget.py:181–185` 明确拒绝非 tutor/authoring purpose。§20.5 L1046、L1068 与附录 A L2048 要求真实 source 和完整 InputProof，purpose enum 有 codex 不等已有 consumer。合法模型证明/来源 owner 的内部注册是实现与真实证据工作，不因其登记方式再要求产品授权；本次也没有检查或索取账号/key、外部文档或真实模型证据。

## 可直接实施的精确 scope 与验收

选择 **“未连接 Codex：下载当前输入的需求说明”** 为下一最小本地工作，不重开现有 bootstrap，也不需要产品所有者再批准普通实现选择。

1. 在当前创作作者表单提供显式下载，仅包含本次当页 `topic`、`prerequisites`、`objectives`、`proof_policy` 四项用户输入和静态边界说明。原次序、Unicode、换行和证明策略不得被静默降级。文件名/模板/Blob 下载与撤销 URL 都是普通客户端实现；不是新增运行 DTO，也不增加/变更 API 路由。
2. 不调用 prepare、Provider、capabilities 探测或 bootstrap 来下载；不使用 `AuthoringRequest`、provider_id、consent_id、旧 ACK、后台详情/候选、source refs、概念目标、正文或密钥。当前表单若另选了材料/目标，必须在按钮范围与文件内清楚说“仅四项需求，不含已选材料/其他任务设置”，不能让用户误以为完整输入已备份。它是需求说明，非 LearningPackage、GenerationInput、授权凭证或生成质量回执。
3. 复用真实 typed `AuthoringPort.session()`（`authoringClient.ts:5–8,18–22`）在下载前重核同工作区、当前有效 author、无 independent/open_book。下载捕获当页四项快照和原 admission actor/访问代次；新 session、workspace/access/port/unmount 或权限变化使晚回调失效，不能让旧 actor 的临时文字由新 actor 接管。无需新会话接口或把 actor/许可写进文件。原 `useAuthoring.ts:29–32,70–96,104–117` 提供现成 admission/生命周期语义，增加小型内部只读动作 seam 属工程工作。
4. `AuthoringForm.tsx:7–12,36–49` 已持有这些字段、busy 和 dirty；`AuthoringPanel.tsx:23–32,43–44` 汇总并限制学科表单。下载不调用 submit、不清空表单、不将 `dirty=false`，也不声称写入 DraftStore/服务端；保留 `Shell.tsx:115–117` 既有关闭/路由确认，失败时原输入仍在。未保存保护不升级为“浏览器被强制关闭后一定可恢复”。
5. 返回文件由用户另行显式选择现有 Import；`interfaces/import_http.py:45–67,77–94`、Import DTO/source hash/warnings 与真实 Review/publish 保持原路径。没有自动读下载目录、命令执行、上传、接受来源声明或自动发布；不声称文件由 Codex 产生，也不把 prompt 下载纳入 R-23/AC-21 完成。

有意义验收：新局部测试证明下载字节只来自四项快照（包含换行/Unicode及 full 策略），未填 provider 仍可下载且零 POST；有 source refs/候选/secret-like无关测试字段时均不进入文件；权限未知/learner/测试 active/会话过期/新 actor 与迟到异步均零下载；修改当页输入后旧回调不导出其他快照；取消/失败/完成下载都不清 dirty，原关闭保护仍出现；卸载清理 Blob URL。真实新 browser 用合成四项输入触发一次下载并核字节，再经用户明确选择普通文件走现有 Import 预览（后续 Review 仍原准入），零 CLI/模型/外发调用。此处只列将来验收，本报告没有执行任何一项。

## 仍须规范闭合的较宽范围

若后续要求“受控服务端任务导出/冻结教材材料/返回产物绑定原任务”，不能借现 POST /exports 的 learner/author/full_backup profile（L1573）或强制 provider/consent 的 AuthoringRequest（L2677–2685）假装已有 task 对象。需补的只是该更宽业务对象的输入/读回/材料范围/产物归属语义，非本地 Markdown 模板。真实 turn/session current state、GenericApprovalView 和 Codex artifact manifest 的具体缺口见表格；本报告不提出新规范或新 API。

§11.2 L572 要求产品命令/查询映射到附录 A，不能用未登记 HTTP 假业务；§20.1 L975 允许不冲突的实现细化。四项当前输入的客户端下载不承担新的服务端交换语义，权限查询及后续 Import 都用既有命令；将每次 Blob/文件命名等 UI 操作都视作必须新增 HTTP 路由会把普通客户端实现错误升级为产品审批。

§18.4 L905–913 允许已验证本地依赖下的后续工程，未合并或真实 Provider/数值验收 open 本身不是禁做上述 fallback 的原因。该功能是 §6.6 的有限离线降级交付，不是 Codex App Server 生成集成、通用审批或产物回导完成。

本报告不是运行验收：不重算原 DCF `3683 PASS / 1 FAIL / 2 ERROR / 2 ENV_SKIP`，原两个 setup ERROR 的原因在本 inventory 中仍 UNKNOWN；不替代 root 的固定184完整 Python、新完整 native 或既有 actual45 控制记录。M6.3 整体与 AC-21 仍未完成，M7 全流程未在此运行。

来源与公开边界：34 份固定源码只保存为私有复核输入。公开候选仅 SAFE_SHARE.json 明确列出的本报告、SOURCE_BINDINGS.json、ROUTE_INVENTORY.json、COLLECTION_ATTEMPTS.json、VERIFY.py；不 glob 复制 fixed-source、不含原始运行日志、数据库、凭据、账号输出或用户材料。初次收集器误写文件名下划线导致 Git 读取失败，已在 COLLECTION_ATTEMPTS.json 如实保留；它不是产品运行失败。后续检查脚本只验证静态 Git/文件 hash 并输出 JSON，不改封存文件。
