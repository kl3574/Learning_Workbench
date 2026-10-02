# M6.2 单块生成例题发布：待采纳的最小合同提案

状态：**PROPOSAL_NOT_ADOPTED / IMPLEMENTATION_NOT_STARTED**。本文件是供所有者审阅的规范改动提议，不是第二份有效需求；未修改根 `PRODUCT_DESIGN.md`，未开放发布能力。

基线：`300b6903fc1507667beacdbced7e648677e65bbf`；唯一规范 v3.0.12，SHA-256 `1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7`。建议采纳后将下述规则写入唯一规范的新版本，再生成和实现合同。

本提案只把一个真实 `authoring_single` 的 `WorkedExamplePayload` 发布为一个新的公开 `ContentBlock(kind=worked_example)`。沿现有 `POST /drafts/{id}/review`、人工决定和 `POST /drafts/{id}/publish`，请求四字段及成功 `201 ContentRef` 保持；不新增路由。Lesson 组、题目、既有对象修改、父 Lesson/Course 的引用调整不在此次采纳范围。

## 为什么需要这一次合同决定

规范已经规定生成真实来源冻结、候选身份、数值执行、人工审核、显式发布和不可变版本；这些直接沿用，不重新请求同一授权。缺少的语义仅为：完整发布字段的来源映射，已发布生成候选的当前读回，以及首次发布选择旧数值观察的时效边界。随机新 ID、逻辑 body_path、内部版本名和迁移实现属于工程细节。

规范 §20.8 的来源是显式所选 block 的完整输入与来源事实（1125 行），`declared_source_refs` 仅允许其子集（1975 行）；这没有把它们定义为 Citation 或 ContentBlock.depends_on。附录 A 的 AuthoringDraftView 仍固定 `state:draft`（1939–1944 行），§20.10 又要求原生成读口保持形状（1177 行）。仅凭 POST 发布 ACK 不能在刷新后用候选 ID 独立发现实际发布结果。

## 建议采纳的单块规则

### 1. 完整 ContentBlock 映射及来源边界

发布 owner 只能读取已登记 `authoring_single`，通过 Authoring 的具名事务读口核原 Job、Provider 受检原输出、完整 candidate/input/context、body bytes 与来源材料。不能构造 Import、Restore、组成员或假 Provider 身份。

每个精确候选至多成功发布一次新对象 r1。发布事务再次核精确 candidate/revision/SHA 和批准，首次写 Content 时以新 ID 的 current 为 null 做强 CAS / require_absent；存在任何已有对象时拒绝，不能据 ID 冲突更新已有对象。并发两命令只有一个发布成功。当前权限与原历史核验后，同 key/同完整命令回原 ACK，同 key/异命令沿现有409 IDEMPOTENCY_CONFLICT；已发布后新 key 沿现有409 DRAFT_ALREADY_PUBLISHED，不产生第二块。候选到新 ID、body_path、完整 ContentBlock 和实际 ContentRef 的分配在首次成功事务内固定并写入不可变发布记录；重启或重放只能回读原分配，不重新分配。事务失败未发生发布，保留原稿且不留下可冒充成功的关联。

| ContentBlock 字段 | 固定映射 |
|---|---|
| schema_version / entity / revision | `3.0.0` / `block` / `1` |
| id | 服务端分配的新稳定 ASCII ID；分配归本次发布，不能取模型提供的 ID |
| kind / title | 原 payload 的 `worked_example` / 原 title，逐字保留 |
| body_path | 服务端为该新 ID 生成的安全逻辑相对路径；不是用户路径、Provider artifact 路径或任意文件入口 |
| body_sha256 / 实际正文 | 原候选 `body_markdown` UTF-8 原始字节的 SHA / 同一原始字节；不加标题、来源脚注或换行，不在发布时改写正文 |
| concepts | `[]`；单块请求没有已选择的 Concept 绑定，不能从先修文字或 source block 自动继承概念 |
| citations | `[]`；此 payload 没有 Citation 记录，不能把 block ID、Provider 名称、文本 URL 或祖先来源的引用 ID 冒充本块 Citation |
| depends_on | **建议明确采用原 payload.declared_source_refs 的完整引用与原顺序**；只表达作者在来源审核中确认的、用于版本影响追踪的显式来源依赖，不证明数学依赖、论断支持或来源正确性。不追加未声明来源、先修、同名对象或 current ref |

最后一项是本提案请求采纳的产品语义，当前规范并未已经给出此映射。人类来源审核须查看全部原输入材料及模型声明的子集，不能仅核 ref 形状就声称完成审校。声明 refs 为空时 depends_on 为空；原实际输入 refs 与它们的完整冻结来源仍保存在原 Authoring 记录及本次发布关联，不能因声明子集而删除原输入事实。

`symbols`、`numeric_plan`、原教学要求及所有源材料继续逐字节保留在原候选/上下文中，发布记录绑定其完整 SHA；不把它们丢弃，不增写 ContentBlock 的未声明字段。ContentRef.sha256 对上述完整 ContentBlock 的规范 JSON 计算，**不得借用**候选 payload SHA；body SHA 继续是另一域。

生成记录不是导入原件。当前 FrozenProvenance 要求真实 retained original/import 关系，不能给生成内容伪造 source/import_id，也不能把某个输入来源的原件称为新生成正文的原件。首切片沿已有 Reader/Retrieval 的 `unresolved` 来源投影，保留 `PROVENANCE_UNRESOLVED` 等实际 warning；author 侧通过原 candidate 与冻结来源查看生成依据。已有来源的 verified/unverified/user_supplied 保留在原输入事实中，不因人审或发布升级。以后若需公开的生成来源专用投影，另定其窄合同，不能靠本次内置记录伪造现有 frozen 语义。

### 2. 发布当前状态的独立 GET 读回

建议只扩展现有 `GET /authoring/drafts/{id}` 的具名 AuthoringDraftView：`state` 允许 `draft|published`，增加必填 `published_ref:ContentRef(entity=block)|null`；`state=published` 当且仅当 published_ref 非null。其余字段及原 payload/validation/source_job_id/base_ref 的含义不变；未发布为 `draft/null`，仅有完整可核验的本候选发布记录时为 `published/实际精确ref`。新公开对象后来产生更高修订时仍返回原候选实际发布的原 ref，不用 current 冒充原发布结果。

这是现有闭合响应的明确合同扩展，**不是旧严格客户端的 wire 向后兼容承诺**：采纳时须同步更新唯一规范、具名模型、OpenAPI、前端生成类型和调用方。当前 v3.0.12 不能在不改闭合字段的情况下同时表达该事实；不另造宽 union、偷偷加字段或把原 GET 改到 Import owner。历史候选、Provider 终态、旧 Numeric/Review/命令 ACK 原字节不改；新增 `published_ref` 是当前 owner 投影，不回填原记录。

GET 每次核当前 author/workspace/学科 Policy、完整候选与发布 owner 历史及实际公开正文，零写、零联网、no-store；存在损坏/丢失关联不得返回 `draft/null` 隐藏已发生发布。学科失权时不返回候选、计划、源标题或 published_ref。通用安全 Jobs 控制规则保持。

首次发布后，不接受该候选新的数值预览或新的 approve_once；拒绝不执行。原预览/决定 ACK、历史数值读取及已有 Job 的安全取消/实际终态回读保留，不把已运行事实改成未运行。发布不重开已完成生成 Job，不改其 result_refs=[]。生成来源 GET /authoring/jobs/{id} 的历史结果字段保持原义。

该 single 候选的**新数值启动许可与首次发布必须在真实 owner 写事务中串行**，不能只在 preview/approve 时查发布态。即使较早检查 A 已批准并排队、较新检查 B 已真实 PASS 且新 Review 允许发布，A 在持久取得新 start 许可前仍须经具名 owner 端口核该精确候选尚未发布；此核验与许可落盘使用同一事务，禁止事务外先读后启动。若发布先提交且 A 尚无持久 start 许可，拒绝授予新许可/新执行，按既有 owner 协议保留可证明的未运行事实及真实终态，不调用 runtime、不改原批准 ACK。若 A 的许可先提交，这就是当前数值账本的新事实，首次发布须按第3节重核端点，旧 Review 不得跨过它。两种顺序均不能修改其他 owner 的准入规则。

已存在的持久 start 许可和 actual_started 事实沿原 §20.8 启动/崩溃恢复协议处理；**actual_started_at 仍为 null 不能单独证明未运行**，因为许可落盘、进程实际启动与实际开始事实回写之间可能崩溃。不能因候选已 published 抹掉许可、实际启动、结果或 Job 终态，也不能把旧许可当作重新执行授权。只有可证明尚未取得开始许可的准备才可按原规则重试；已有许可但无法核实实际执行/结果时保留 outcome_unknown，不自动重跑。原已实际开始的执行仍经原安全取消/终态收集，保存实际结果；后来终态推进不改变成功发布的原 ACK。

### 3. 首次发布的 Review / 数值边界

沿既有完整结构检查、适用数学与来源人工决定、精确候选、warning 确认及强 CAS。worked_example 必须有该候选独立明确批准的完整实际数值 PASS：实际开始、唯一完成 Job、完整输出/输出 SHA、已知0退出码及全部断言通过。数学 NOT_APPLICABLE、人工枚举、任意 artifact 或单元测试结果都不能替代它。

首次发布还必须经真实 single 数值 owner 只读核验所选 Review 的观察端点与**当前完整有序数值账本端点相同**。新增 preview、决定、开始/完成/失败等持久事实均使原观察不足以首次发布，须显式新建 Review 和新的人类决定；不能跳过较新 pending/decline/FAIL/BLOCKED 选择旧 PASS。端点比较排除读取时间及只读派生 expired，使用真实 membership/head、原命令、Job/event/start/end/output 的完整绑定，不用时间戳或重算较小 head 替代历史。

历史 Review 和已成功发布的原 ACK 仍按原冻结观察和完整历史回读。后来状态推进不改旧回执，也不据旧 ACK 授予一次新发布；当前身份失权、原 Provider/候选/来源/Review/发布/真实正文损坏仍 fail closed。原历史验证口不能被新准入口改成必须永远等于当前端点。

## 工程实现与验收边界（采纳后执行）

Authoring/Quality/Content/Publication 各自具名受检端口在调用方真实 SQLite 事务协作：Authoring 持原候选及来源；single 数值 owner 持原批准、开始许可、开始/终态、输出及完整数值清单，Jobs owner 持生命周期和租约，Quality 持 Review 及冻结数值观察；Content 写不可变 r1/正文/current，Publication 经具名受检端口消费准入结果并持 candidate→完整 ContentBlock→新 ContentRef、所选人审/数值观察、命令和状态历史。采用前向所属迁移，不改0001、54 core、包3.0.0，不跨 owner SQL 猜归属。状态/current/发布记录/outbox/ACK 同事务提交；失败完整回滚，未引用 blob 沿现有 GC 边界。未知或坏 owner、不可核验 Provider/source、错误引用和受保护路径保持拒绝。

不写父 Lesson/Course，也不造课程、导航位置或课程已经切换的承诺。该新块通过原精确 block/body 读口可读；需要加入教材路径时另经显式父对象审核发布。它是单块发布闭环，不是整课发布或完整 M6.2 验收。

采纳后的最小验收须覆盖：真实 SQLite 候选与原受检生成记录→单次批准的真实隔离数值结果→新 Review/显式人审→原 POST 发布→独立 GET current publication→精确 Content 元数据与原 bytes→重启同 ref；空来源及带精确声明来源；候选/正文/source/Provider/Review/numeric/output/发布账本单边损坏与尾删；所有旧 owner、未知ID、角色/Policy、原 ACK/异命令、两标签首次发布竞态；新数值事实阻断旧 Review，历史 ACK 不因后来事实失效；Content/current/record/ACK 注入失败原子回滚；父 pin/旧题/私解/attempt/grade/evidence 字节不动。状态发现和 GET 的完整行清单不变。

数值 A/B 竞态验收须明确建立同一 single 候选的较早 A（approve_once/queued，尚无 start 许可）、较新 B（完整真实 PASS）及新 Review/人工决定，用真实事务屏障分别验证：发布先提交时 A 不取得新许可且 runtime 调用数为零，原批准 ACK 与真实未运行终态可回读；A 许可先提交时旧 Review 的发布被当前账本检查拒绝，须重新 Review/人审；在持久许可后、actual_started 回写前注入崩溃/重启时不能仅凭 null 声称未运行，无法证明结果则 outcome_unknown且无第二次执行；在已有许可或实际开始后发生发布时，原取消/完成/未知终态与输出事实不被覆盖，发布原 ACK 保持。每条分别记录许可、Job/start/end/输出、发布顺序与实际 runtime 调用数；合成账本/受控崩溃探针与真实隔离运行分开记证据，不能用合成 B 宣称物理 PASS。

本次仅完成合同审计及合成探针；**真实隔离数值、该新发布实现、浏览器、真实模型、数学/来源独立审校和教学效果均 NOT_RUN**。现有恢复例题 v3.0.12 的运行结果属于另外的冻结验收，不移作本切片成功证据。
