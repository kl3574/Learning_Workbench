# 知径 Learning Workbench：完整产品设计与工程实施规范

**版本：3.0.6｜日期：2026-09-16｜规范文件：`PRODUCT_DESIGN.md`｜目标：从零构建、公开代码仓库、可追踪实施**

**本文件（含文末附录）是唯一产品与工程规范。** 将它放入空目录即可开始；不需要旧版设计包、旧 Demo、之前聊天、私有 GitHub 仓库或另一份提示词说明需求。正文定义产品，附录内嵌数据模型、HTTP 字段、数据库设计、模块接口、样例和验收用例。构建 Agent 根据本文生成实现文件、OpenAPI、测试和进度记录；这些是派生产物，不是第二套产品需求。

**当前交付状态：SPEC_READY / IMPLEMENTATION_NOT_STARTED / REMOTE_REPOSITORY_NOT_CREATED。** 本文的模型和 SQL 可做结构验证，但不代表正式软件、真实模型或教学效果已验收。后续实际进度写入 `progress/state.json` 和 GitHub Issues；不要反向修改本文中的初始事实。本文给出的技术阈值和视觉参数是本项目的设计决策，并非竞品内部实现或已证明的学习效果。

**仓库目标：`kl3574/Learning_Workbench`，公开、独立新仓库，不复用或修改已有学习系统仓库。** 建仓、发布允许公开的本项目内容及维护 Issues 已获本任务授权；私有教材、笔记、学习记录、密钥、付费调用和公网部署不在此授权内。仓库尚未建立时不能使用占位 URL 冒充已经发布。

### 文档导航

- 第 0—6 章：产品目标、需求、课程平台式左栏、阅读/练习/测试/Agent 流程。
- 第 7—15 章：模块、技术选型、数据、文件、接口、Agent、评分、权限和恢复。
- 第 16—17 章：验收门槛、从零工程结构和 M0—M7。
- 第 18—22 章：公开 GitHub 工作流、实施纪律、初始进度、运维和参考来源。
- 附录 A—G：内嵌 HTTP 契约、核心类型、存储 DDL、模块端口、可生成样例、验收场景和建仓流程。

优先遵守正文的业务、安全和验收不变量；附录与正文发生冲突必须在同一变更中修正并增加回归测试。实现者不得挑选更宽松的一处绕过要求。必要的技术细化可以新增 ADR，但新产品行为必须同步写入本文。所有稳定需求 ID 保留，新增要求追加编号。

### 规范版本记录

| 版本 | 规范变化 | 不代表的事实 |
|---|---|---|
| 3.0.0 | 初始完整产品/工程规范与核心模型、基线 DDL、学习包 | 不代表工程或远端已完成 |
| 3.0.1 | 推荐严格应用 DTO、只读投影、真实来源与决定历史/CAS | 不改初始事实、54 core 或学习包 3.0.0 |
| 3.0.2 | M5.1 配置/秘密、服务端冻结授权、单次受控派发、完整输入计量证明、内部终态与安全备份边界 | 不代表生产模型已支持、真实外发已批准或 M5.2/M5.3 已实现；54 core、学习包及数据 schema_version 3.0.0 不变 |
| 3.0.3 | M5.2 显式精确scope、未审材料标识、Content材料/来源、只读scope状态/CAS、离线词法代际/Jobs、资源和原创基准 | 不代表检索或基准已运行/通过，不开放自动扩范围、embedding或真实外发；54 core、基线DDL、学习包3.0.0不变 |
| 3.0.4 | M5.3 真实 Thread/Run/Jobs、上下文身份、授权衔接、受检输出、严格 SSE 与取消恢复 | 不代表生产模型可调度或已授权费用测试；54 core、基线 DDL、学习包 3.0.0 不变 |
| 3.0.5 | M5.4 完整输入证明的精确目的地、模型/格式/有效性绑定及显式无思考 Responses 请求 | 不代表托管完整计量证明、真实模型/搜索或教学验收已通过；54 core、基线 DDL、学习包 3.0.0 不变 |
| 3.0.6 | M6.1 首个 worked_example 的授权前准备、生成候选身份及单独批准的隔离算术复算 | 仅首个纵向切片，不代表全部 M6.1、M6.2 发布、M6.3 Codex、托管 InputProof 或数学/来源审核完成；54 core、基线 DDL、学习包 3.0.0 不变 |

## 0. 执行摘要与不可变决策

平台定位为**本机优先、以学习对象为中心、由 Agent 辅助的自主学习工作台**。学习者可以管理自己的资料、教材、路线、笔记和进度，阅读 LaTeX 数学内容，完成习题与独立测试，并借助联网与大模型问答加深理解。

核心布局固定为：**左侧导航 → 中央学习内容 → 右侧 Agent**。左侧主导航严格按 **学习路线 → 教材 → 习题 → 测试题** 排列；栏目说明表达“教材含例题、习题含解答”，不把冗长括号塞进每个导航行。设置、导入、知识画像、创作、备份、连接器都是辅助工具，不插入这四个主入口。Agent 不是第五个需要跳转的主页面。

核心流程为“明确目标 → 阅读教材与例题 → 尝试习题 → 独立测试 → 根据证据补弱 → 继续学习”，但它不是强制线性流程：已有基础的用户可以先测试，也可以跳读教材。系统提醒先修缺口，不默认锁课。

以下规则不能因实现方便而改变：

1. 例题属于教材；自学习题的答案默认折叠且按请求下发；测试答案提交前不由正式版服务端下发。
2. 独立测试时右侧 Agent 仍存在，但只提供操作说明。交卷后按策略恢复学科解释、答案复盘和补弱推荐。
3. 阅读完成、自报基础、练习参与、独立作答证据分别记录，不能互相冒充。
4. 模型生成的内容先进入草稿；没有显式审核与发布动作，不覆盖正式教材。
5. 用户知识画像可解释、可纠正；有限样本启发式分数不能宣传为“真实掌握概率”。
6. 对话上下文绑定对象、修订和发送时快照；切换标签不应把回复放进错误章节。
7. 密钥仅在服务端或系统安全存储中；导入资料、网页、教材内指令都是不可信数据。
8. 模拟提供商通过、真实模型通过、独立学习效果通过分别验收。

**从零构建默认栈：React + TypeScript + Vite、FastAPI + Pydantic、SQLite、MathJax、显式 Agent 状态机。** 不要求开发者复制 VS Code 源代码，不先采用 Electron、不先建设微服务，也不引入没有明确职责的多 Agent 团队。已有 Next.js 工程可通过适配层承载同样的 Workbench 模块，但不是从零主线的前置依赖。

## 1. 用户、问题、范围与成功标准

### 1.1 用户角色

首期是单用户本机应用。一个人兼任学习者和教材作者，但两个角色的**操作权限上下文**不同。学习者可以阅读、练习、测试、记笔记；作者可以编辑草稿和审核发布。服务端必须仍区分 `learner` 与 `author` 操作，特别是在独立测试会话中，不因同一个人拥有作者身份就向该测试界面返回答案。

这不是抵御本机系统管理员的保密考试系统。拥有本机文件访问权的用户可以查看自己的数据库；本产品提供的是学习工作流隔离、可追溯证据和降低无意泄题的机制，不宣称监考或防作弊认证。

### 1.2 目标问题

资料可能来自用户上传、已有 HTML 教材、论文、网页、Codex 或普通 LLM。单纯“文件列表 + 聊天”无法清楚表达先修关系、当前学到哪里、练习与测试区别，也难以让 Agent 获得准确上下文。本产品需要同时解决内容组织、学习过程、生成审核与证据追踪，而不是只优化一个聊天输入框。

### 1.3 必需功能与边界

首个完整个人版必须覆盖：教材与路线导入；Markdown/LaTeX 阅读；例题、习题、测试分离；笔记与进度持久化；基于证据的推荐；真实 LLM 及联网提供商；教材/题目生成与审核；Codex 受控创作通道；备份、恢复与错误反馈。

不属于首期：收费课程市场、机构组织、直播课、学分认证、多人实时协同、公共互联网多租户、远程桌面控制、自动执行教材任意代码、任意证明题完全自动终审。

Zotero、博客增量同步是连接器扩展。它们应有明确端口和里程碑，但不成为离线阅读、做题和本机记录的运行前提。

### 1.4 成功标准

产品成功不是“用户在页面停留更久”。首批观察指标包括：用户能否无说明完成一轮学习；是否能分清例题、习题和测试；能否定位当前 Agent 的上下文；切换页面后是否丢草稿；测试错误能否回到准确教材位置；恢复备份是否保留对象版本；用户是否能说明推荐理由并拒绝不合适推荐。

学习收益必须在真实学习者、独立题目和预先确定的评测中验证。功能测试或模型自评不能替代这项验证。

## 2. 需求清单与追踪关系

`P0` 为首个完整个人版必需；`P1` 为明确设计的扩展。里程碑 M0—M7 的详细定义见第 17 章。以下编号是开发任务和验收的永久引用，不得按章节顺序重新编号。

| ID | 要求 | 优先级 | 所属模块 | 验收要点 |
|---|---|---|---|---|
| R-01 | 左侧四项固定顺序，学习路线默认首页 | P0 | Workbench | 四个入口可由键盘操作；顺序断言 |
| R-02 | 中央学习，右侧常驻 Agent | P0 | Workbench | 八类中央视图都保留 Agent |
| R-03 | 可调整宽度、折叠侧栏、专注模式、标签页 | P0 | Workbench | 布局恢复、标签草稿不丢失 |
| R-04 | 教材层级、章节定位、例题锚点 | P0 | Content | 深链接可回到精确修订与块 |
| R-05 | 手动添加/导入路线，任务重排、完成记录 | P0 | Route | 引用校验、环检测、撤销/冲突处理 |
| R-06 | 文件导入暂存、预览、警告、确认入库 | P0 | Ingestion | 未确认无正式内容变更 |
| R-07 | Markdown/TXT/安全 HTML/学习包 | P0 | Ingestion | 脚本不执行，文件哈希可复核 |
| R-08 | 文本型 PDF/DOCX 提取及低保真提示 | P0 | Ingestion | 表格、公式失败不默认为正确 |
| R-09 | LaTeX 公式、代码、表格、来源定位 | P0 | Reader | 数学源文保留，长公式局部滚动 |
| R-10 | 例题展示完整推导、计算与条件 | P0 | Content | 例题是教材内容块，不是测试实例 |
| R-11 | 习题及默认折叠解答、提示、草稿 | P0 | Practice | 查看解答记暴露事件，刷新可恢复 |
| R-12 | 单选、填空、计算题及评分 | P0 | Assessment | 题面/答案分离，容差与单位明确 |
| R-13 | 独立/辅助/开卷模式不可混记 | P0 | Assessment | 策略快照绑定 attempt，不能事后升级 |
| R-14 | 测试期 Agent 操作帮助、交卷后复盘 | P0 | Policy/Tutor | 服务端检查，跨标签不能绕过 |
| R-15 | 问答、提示、推导、拓展四种教学意图 | P0 | Tutor | 意图与工具权限分别建模 |
| R-16 | 当前对象、选文、来源的上下文预览 | P0 | Context | 发送快照与界面可读摘要一致 |
| R-17 | 真实模型提供商及显式数据发送授权 | P0 | Provider | 未授权不调用，能力不支持则报错 |
| R-18 | 联网搜索、引用、实际执行状态 | P0 | Search | 未执行不能显示“已联网核查” |
| R-19 | 学习状态持久化、笔记、阅读定位 | P0 | Learning | 服务端为正式记录权威源 |
| R-20 | 学习画像与补弱/先修/复习推荐 | P0 | Recommendation | 每条推荐列证据及可拒绝理由 |
| R-21 | 教材生成、修改提案、审核、发布、回滚 | P0 | Authoring | 新修订不可变；旧记录不覆盖 |
| R-22 | 例题/习题/测试题生成并验证 | P0 | Authoring | 生成者不能自行授予审核通过 |
| R-23 | Codex 会话、工具审批、产物回导 | P0 | CodexBroker | 不以导出 prompt 冒充集成 |
| R-24 | 数学与来源审校分离、数值例可复算 | P0 | Quality | 校验器通过不等于数学正确 |
| R-25 | 私有答案不进入普通 RAG 与测试提示 | P0 | Retrieval/Policy | 检索和上下文组装双层阻断 |
| R-26 | 备份、恢复、迁移、删除、反馈导出 | P0 | Workspace | 文件完整性、事务、回滚验证 |
| R-27 | 任务取消、重试、断线回读、费用控制 | P0 | Jobs | 幂等、终态唯一、预算可见 |
| R-28 | 无障碍、缩放、窄屏抽屉、错误空态 | P0 | Workbench | 390/900/1440/1920px 验收 |
| R-29 | 可重复测试、日志与真实模型评估边界 | P0 | Quality | 三种 PASS 独立、证据可回读 |
| R-30 | Zotero 笔记/参考文献连接 | P1 | Connector | 写入预览、授权、版本检查 |
| R-31 | 网页/博客增量更新与索引失效 | P1 | Connector | 幂等同步、保留旧内容版本 |
| R-32 | 标准题库/课程平台互操作 | P1 | Export | QTI/LTI 适配，未经测试不称兼容 |
| R-33 | Open edX 课程内页式左栏与统一浅色设计系统 | P0 | Workbench | 真实多层目录、长标题、折叠、高亮、完成标记；运行截图复核 |
| R-34 | 仅凭本文件可从零启动，无历史规范包依赖 | P0 | Engineering | 在只含此文件的新目录抽取模型、生成样例并启动工程 |
| R-35 | 新公开仓库、Issues、里程碑和下一任务可追踪 | P0 | Engineering | 远端回读仓库、提交、Issue；状态与测试证据一致 |
| R-36 | 公开发布前敏感内容与第三方权利检查 | P0 | Security | 无真实密钥/个人学习数据/未获许可教材；初始不擅自授权开源许可证 |
| R-37 | 自报先修、学习目标、跨已导入教材推荐 | P0 | Learning | 用户可修正自报；推荐带理由和来源，不把自报当测验成绩 |
| R-38 | UI 会话/提供商设置/归档删除/审校决定可闭环操作 | P0 | Workspace/Quality | 类型接口、保存冲突、测试期权限与删除影响预览 |


## 3. 对外部产品和规范的借鉴

### 3.1 采用哪些公开机制

VS Code 官方文档把主要区域区分为 Primary Side Bar、Editor、Secondary Side Bar、Activity Bar、Status Bar 和 Panel，其中 Secondary Side Bar 默认容纳 Chat，并支持布局与标签状态。这支持本项目采用三栏工作台的交互组织；不意味着需要使用 VS Code 的内部技术栈。[S1][S2]

Open edX 官方课程单位说明与 Redwood 侧栏说明公开展示了章节/小节/单元层级、折叠导航、当前单元高亮及线性/非线性跳转。[S20][S21] 本项目采用这一已公开的课程内页排版，不宣称 Redwood 是当前最新版。Coursera 对 Coach 的公开介绍强调课程内的学习辅助与练习反馈。本项目借鉴“课程结构”和“学习上下文中的助教”，但不推测它们未公开的数据库、推荐算法或模型架构。[S3][S4]

W3C APG 给出了可聚焦分隔条、键盘移动、可访问名称和当前值等语义。正式版须按实际组件能力实现这些交互；不能只添加 `role=tree` 而不支持对应键盘行为。APG 的 Window Splitter 页面同时注明示例/模式评审仍有未完成部分，因此这里把它作为实现指导，而非直接宣称获得无障碍认证。[S5][S6]

### 3.2 不采用哪些表面模仿

不复制 IDE 的所有复杂性：默认不显示终端，不显示 Git 分支列表，不把教材当源码目录要求读者理解。只有作者模式需要源码编辑、差异比较和受控的代码验证。

也不把课程目录变成四份互不关联的清单。四个导航是对同一学习领域的**四种视图**：路线回答“学什么、先学什么”；教材回答“为什么、怎么做”；习题回答“我能不能试做”；测试回答“我独立完成到什么程度”。

## 4. 信息架构与交互规范

### 4.1 视觉方向与三栏骨架

**唯一主视觉方向：Open edX 的课程内页排版＋VS Code 的区域分工。** 不做课程商城、不做管理后台，也不复制暗色代码编辑器。左栏的信息层级与课程目录参照官方课程截图；中央提供长篇阅读和作答；右侧是常驻上下文助教。不使用 Coursera/Open edX 的 Logo、商标或课程内容冒充合作产品。

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 知径 / 工作区                   全局搜索             导入 · 工具 · 布局 │
├───────────────────┬─────────────────────────────┬───────────────────────┤
│ 课程切换 ▾        │ 标签：当前章节 / 已固定对象 │ Agent                 │
│ 课程完整中文名称  │ 面包屑：课程 > 章 > 小节    │ 当前章节/选文/模式    │
│ 内容完成 3/12     │                             │                       │
│ 继续学习          │ 章节标题                    │ 对话、推导、引用      │
│───────────────────│ 目标与逻辑链                │                       │
│ 学习路线          │ 连续正文 / 公式 / 例题      │                       │
│ 教材  ← 当前入口  │ 或习题作答 / 测试 / 复盘    │                       │
│ 习题              │                             │                       │
│ 测试题            │                             │                       │
│───────────────────│                             │───────────────────────│
│ 当前教材目录 搜索 │                             │ 输入问题              │
│ ▾ 第1章 观测模型  │                             │ 附加上下文 · 联网授权 │
│   ✓ 1.1 模型      │                             │ 发送 / 取消           │
│   ● 1.2 残差      │ 上一节              下一节 │                       │
│ ▸ 第2章 最小二乘  │                             │                       │
│───────────────────│                             │                       │
│ 笔记 · 创作 · 设置│                             │                       │
├───────────────────┴─────────────────────────────┴───────────────────────┤
│ 已保存 / 离线待同步        当前内容修订        正常学习 / 独立测试        │
└─────────────────────────────────────────────────────────────────────────┘
```

不额外设置一条只有图标的 Activity Bar 占据左边宽度。顶栏约 52px、状态栏约 26px，细节以真实中文排版调整。三个区域各自滚动；中央与 Agent 均使用 `min-width:0; min-height:0`，不能让长公式或长消息撑大 CSS Grid。

默认视口宽度 ≥1280px 时三栏同时可见：左栏 300px（可调 260–360）、右侧 368px（可调 320–480）、中间自适应且尽量不少于 480px；拖动导致中央低于最小宽度时限制拖动。820–1279px 默认保留左栏、Agent 转右抽屉；小于 820px 两侧按需抽屉、中央优先。200% 缩放按实际 CSS 宽度重排，而不是依据设备分辨率硬保留三栏。用户可主动折叠或使用专注模式，状态按工作区保存。

### 4.2 左栏信息层级、设计 tokens 与交互

**从上到下只有四层：课程摘要 → 四项入口 → 一个上下文目录 → 低权重辅助工具。** 课程摘要含课程切换、可换行标题、真实内容完成数和继续学习。内容完成与知识掌握分开：有阅读记录、无测试证据时，应允许同时显示“已阅读”和“未诊断”。不显示无来源的学习时长、百分比或推荐。

四项入口文字固定为：学习路线、教材、习题、测试题；使用紧凑纵向导航行，图标一致，文字是主要识别方式。栏目说明可显示“含例题”“含解答”。不得做成四张大卡片、彩色胶囊或大面积按钮。Agent 不成为第五项入口。

入口下方只有一个目录区域，按当前入口替换：

| 入口 | 目录层级 | 选择后的中央任务 |
|---|---|---|
| 学习路线 | 阶段 → typed 学习任务 | 学习目标、顺序、任务和先修提醒 |
| 教材 | 章 → 小节 → 可选例题/定理锚点 | 连续教材阅读 |
| 习题 | 章节/题组 → 题目 | 草稿、提示、默认折叠解答 |
| 测试题 | 试卷/阶段测验 → 入口与作答记录 | 测试或交卷复盘；测试中按策略显示题号 |

章节行约 40–44px；小节最低 40px、标题多行时自然增高；每层缩进 16px。长中文标题最多先显示三行，仍有完整可访问名称与展开方式，不截断到无法识别。折叠按钮与进入章节的链接分别可聚焦，点击折叠不误打开内容。当前小节使用低饱和背景、左边细强调条、`aria-current=page`；完成状态有图标和文字/可访问名称，不仅使用颜色。

目录只自动展开当前项祖先；保存课程+入口级展开集合、滚动位置和最后阅读位置。搜索结果带所属章；清除搜索恢复之前目录。空课程提示导入/创建，空习题显示“尚无已审核习题”，不能换成别的课程示例题。

首期使用语义化 `nav`、嵌套列表、链接与带 `aria-expanded` 的 disclosure 按钮；无需强行设置 `role=tree`。若换成 Tree View，必须同时实现其完整键盘与焦点模式。[S6] 分隔条可聚焦、箭头按 16px 调整，Home/End 到边界，Enter 折叠/恢复；有名称、方向、当前值与上下限。[S5]

设计 tokens 初始值（工程可在视觉验收中微调，但统一修改，不逐页临时覆盖）：

```css
:root {
  --bg-app: #f6f7f9;
  --bg-surface: #ffffff;
  --bg-selected: #edf3ff;
  --fg-primary: #17212f;
  --fg-secondary: #4b5563;
  --border-subtle: #dde2e8;
  --accent: #2456b8;
  --focus-ring: #2456b8;
  --success: #176941;
  --danger: #a1262d;
  --font-ui: system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-reader: var(--font-ui);
  --font-nav: 15px;
  --font-body: 17px;
  --line-reader: 1.75;
  --space-unit: 4px;
  --radius-control: 6px;
  --radius-panel: 8px;
  --nav-default: 300px;
  --agent-default: 368px;
  --reader-max: 48rem;
}
```

正文左右 padding 在 20–48px 自适应，舒适行宽约 38–48 个中文字符；标题、正文、注释有明确等级。章节不是由几十张独立卡片拼成，定义/定理/证明用细规则、标题与留白区分，例题采用统一组件。避免渐变、玻璃效果、重阴影、过多圆角和彩色徽章。正文与 UI 保持浅色，深色模式是后续主题，不影响首期验收。

右侧上下文摘要可展开查看发送范围；输入区固定于面板底部，消息区独立滚动；模式入口不超过四个，工具授权在输入区旁显示实际状态。未配置模型应明确说明，默认不以模板伪装真实回答。

**M1 视觉交付是运行中的真实界面，而非概念图。** 用显式加载的合成示例课程覆盖至少 8 章、每章 4–8 个小节、长中文标题、未读/已读/当前/过期状态；首次真实工作区保持空态。1440×900、1920×1080、900×900、390×844 与 200% 缩放均保存截图，检查目录密度、标题换行、数学溢出、焦点、对齐、留白和两个面板挤压。至少进行一轮截图修正和复查，保留差异证据；不编造美观评分或用户满意度。参考截图中用于文档注解的红框等不能复制进产品。


### 4.3 中央标签与对象身份

每个标签以 `view_kind + object_id + revision + mode` 作为身份，而非仅以标题或数组下标作为身份。同名章节不合并；旧修订与新修订可以并存。

单击预览不覆盖有脏草稿的标签。双击或明确操作固定标签。关闭带未同步改动的标签必须先保存、放弃或取消；不允许只因组件卸载而丢数据。每个标签保存滚动位置、展开状态、选中文本、题目草稿和焦点位置。浏览器刷新后恢复已确认的 UI 会话与草稿，未保存部分明确提示。

中央每种内容都保留所属关系：本节来自哪本教材；习题对应哪些概念；测试覆盖哪些目标；错误反馈可以打开教材的具体块，而不是仅回到首页。

### 4.4 中央与右侧的联动

| 中央视图 | Agent 默认上下文 | 可执行的帮助 | 不允许自动发生 |
|---|---|---|---|
| 学习路线 | 目标、阶段、先修、能力证据摘要 | 拆目标、解释顺序、提出路线调整 | 直接重排用户正式路线 |
| 教材/例题 | 当前块、必要相邻块、修订、选文 | 概念解释、推导、反例、拓展 | 自动发送整个资料库 |
| 习题 | 题干、用户尝试、已获提示 | 分级提示、解释条件、在授权后讲解答案 | 把辅助练习当独立测试 |
| 独立测试进行中 | 仅测试操作状态 | 保存/交卷/时间等操作帮助 | 调模型解题、搜索、读取答案 |
| 测试已提交 | 本次试题、作答、评分、解答、相关教材 | 找错因、回教材、生成复习提案 | 修改原始提交记录 |
| 创作/修订 | 草稿、修改要求、审核意见 | 生成或修改草稿、输出差异 | 未经确认发布 |
| 设置/备份 | 操作说明，不含秘密值 | 解释配置、排错建议 | 把密钥写入聊天 |

**发送时冻结上下文。** 在课 A 发出请求后切到课 B，回复仍写入 A 的线程，并提示“该回复对应另一标签”；不能因为全局 `activeLesson` 已变更而挂到 B。请求期间改变引用范围，必须影响下一次请求而非悄悄改变已在运行的请求。

默认会话按对象分组。用户可以显式建立跨对象讨论；跨对象线程必须逐项显示附加材料，并受同样的权限与测试策略约束。

### 4.5 必须存在的状态

加载、空内容、导入警告、保存中、保存失败、版本冲突、来源缺失、过期引用、请求取消、模型不可用、检索无证据、问题需人工复核都必须有可读界面。空状态不能显示伪造内容；错误不能吞掉后显示绿色成功。

命令面板至少覆盖打开对象、导入、创建路线、开始练习、打开测试记录、切换侧栏、导出备份。快捷键必须可以查看，不能覆盖浏览器基础功能而不给等价入口。

## 5. 学习对象与逻辑关系

### 5.1 一个领域，不是四份副本

```text
LearningRoute --steps--> Lesson / PracticeSet / Assessment
                           │          │             │
Course --ordered refs--> Lesson       │             │
                           └--> ContentBlock        │
                                 ├ concept          │
                                 ├ theorem/proof    │
                                 └ worked_example   │
                                      │             │
Concept <---- skill_tags -------- QuestionRevision <-┘
                                      │
                              SolutionRevision（私有）
                                      │
Attempt / Exposure / LearningEvent → Evidence → Recommendation
```

例题是 `ContentBlock(kind=worked_example)`；习题和测试都引用 `QuestionRevision`，但发布到练习集和测试蓝图时使用不同的投放策略。若同一道题已经向用户展示过答案，再放进测试，必须记录此前暴露，不把它当“未见独立题”。题目可复用，证据不能无条件复用。

### 5.2 内容对象

课程 `Course` 保存目标、概念集合、有序小节引用以及 sections（章ID/标题/所属lesson_ids）；sections对lesson_refs做互斥完整分组，小节按refs排序。章节/小节 `Lesson` 保存先修、目标和有序内容块引用。`ContentBlock` 的类型至少包含 orientation、text、definition、theorem、proof、intuition、worked_example、boundary、summary、code、figure。例题正文包含题设、条件、步骤、结果、检查，但不需要强行拆成互动测试。

教材正文每个稳定块单独保存 Markdown，元数据保存 `id/revision/kind/source_refs/concept_ids/body_path/body_sha256`。章级页面由这些块合成。**正式版不能靠正则表达式“看到自学练习四个字就移走一段正文”。** 旧 HTML 只有经人工确认边界后才能转换成正式结构。

### 5.3 题目与答案

公开题面包含：题目身份、版本、题型、目标概念、题干、选项/输入规范、所需单位、分值、来源和内容修订引用。私有答案包含：标准答案、同义文本、数值容差、评分规则、分级提示、完整解答与审核记录。

`QuestionPublic` 的 Schema 不允许 `answer`、`solution`、`rubric_private` 等秘密字段。后端不是“读取整对象后删几个字段”，而是投影成受限输出模型并进行序列化测试。

公开评分说明可以告诉用户单位和允差；完整标准答案不能在独立测试前进入响应、页面 HTML、预取缓存、日志或普通向量索引。

### 5.4 学习证据

至少区分 `read_confirmed`、`practice_submitted`、`hint_requested`、`solution_revealed`、`test_submitted`、`graded`、`reviewed`、`note_created`。行为由服务端确认，客户端可提交动作，但不能自行提交“我已被认证掌握”。导入旧进度以 `origin=imported_user_claim` 保存，不升级为服务端验证证据。

知识状态首先按“概念 × 能力维度”组织；能力维度包括理解、计算、推导、迁移。单选题答对不能自动证明推导能力。少量数据时只显示“暂无证据/初步证据/需要补强”，不伪造高置信精细画像。

## 6. 端到端业务流程

### 6.1 导入资料并开始学习

用户选择文件 → 服务端检查大小和类型 → 保存不可变原件 → 创建解析任务 → 提取正文/元数据/警告 → 预览章节与公式 → 用户确认映射与用途 → 事务写入规范内容 → 显示在教材目录 → 生成或绑定路线 → 开始阅读。

取消导入必须清理暂存或标记待清理，不产生半本教材。相同文件哈希重复导入要提示“已有原件”；相同内容可以在不同课程中引用，不重复存储原始字节。解析质量差时允许把原文作为只读附件阅读，不能自动把它当作准确 RAG 真值。

### 6.2 阅读与问答

打开章节 → 载入准确修订 → 公式渲染 → 选中段落/公式 → 显示右侧上下文摘要 → 用户发送问题 → 服务端重新检查引用及授权 → 检索补充证据 → 调用模型或离线提供商 → 展示回答、引用、工具状态 → 用户追问/存笔记。

按“提示”意图提问时，先提供小步骤或检查方向；用户明确要求完整解答后可以在练习场景逐步开放。不能以“启发式教学”为理由永久拒绝用户明确要求的完整推导。

### 6.3 自学习题

打开习题 → 先写思路 → 自动保存草稿 → 请求提示（记录辅助） → 提交尝试 → 查看确定性反馈或 `needs_review` → 主动展开答案（记录暴露） → 保存错因笔记 → 选择继续练习或独立测试。

展开答案和请求提示是有益学习活动，不是“作弊”标签；只是它们不能混入独立测试证据。

### 6.4 独立测试

查看范围、题型、策略与是否见过题 → 确认开始 → 服务端建立 attempt 和题目快照 → 锁定本次策略 → 仅返回公开题面 → 自动保存作答 → 提交并冻结答案 → 确定性评分/人工复核 → 释放解答 → 解释错误 → 推荐教材块和后续练习。

存在活动独立 attempt 时，同工作区所有浏览器标签都应受服务端策略约束。访问旧答案、请求 Authoring 自动讲解该题、直接调用 Tutor API 都不能绕过限制。用户始终可以放弃测试；放弃记录不是 0 分独立测试。

浏览器关闭不应偷偷交卷。无时间限制测试可恢复；有时间限制测试以服务端截止时间为准，不依赖客户端时钟。M3 可先实现无时限；若界面显示计时选项，必须实际启用服务端截止时间与超时提交。M7 需支持可选时限，自动提交任务保留 deadline 原因且不依赖客户端时钟。

### 6.5 更新教材

编辑/生成新草稿 → 对比旧修订 → 结构校验 → 数学/来源审校 → 用户批准发布 → 新修订生效 → 产生失效事件 → 重新索引受影响内容 → 标记旧笔记、题目和证据的适用状态。

标点修正不必抹掉阅读进度；修改定理条件、定义、答案、数值例时必须触发影响分析。旧作答永远保留原题面及旧答案版本。回滚不是覆盖历史，而是把旧内容发布成更高修订。

### 6.6 用 Codex 生成教材

用户给主题、先修、目标和证明策略 → Authoring 建立受控任务 → CodexBroker 准备隔离工作目录 → 启动/恢复会话 → 转译工具审批 → 产生 Markdown、题包、计算验证产物 → 验收内容和来源 → 导入草稿 → 人工审阅 → 发布。

普通 LLM 的结构化草稿生成和 Codex 的工具型文件生成是两个适配器，不共享“任意执行权限”。未安装或未授权 Codex 时，提供明确的任务导出/文件回导降级通道，并标注“未连接 Codex”。

## 7. 模块架构与写入权限

采用模块化单体；模块间调用 application ports，不直接访问另一个模块的 ORM 表。后台任务是独立 worker，不改变领域边界。

| 模块 | 输入/命令 | 查询/输出 | 独占写入对象 | 禁止职责 |
|---|---|---|---|---|
| Workbench | 打开、关闭、布局、焦点 | ViewContext、导航选择 | UI session、草稿缓存 | 计算最终成绩 |
| Ingestion | 文件/网址、解析策略、导入确认 | ImportPreview、警告、Job | 原件、暂存导入 | 自动发布教材 |
| Content | 草稿保存、发布提案 | Course/Lesson/Block 精确修订 | 不可变内容修订 | 修改学习成绩 |
| Route | 创建/重排/绑定目标 | Route、先修提醒 | 路线修订、人工完成动作 | 推断“读完=掌握” |
| Practice | 创建会话、保存尝试、请求提示/解答 | 题面、允许的提示、练习反馈 | practice attempt、exposure | 发布测试分数 |
| Assessment | 开始/保存/提交/放弃 | 题面、结果、策略 | test attempt、grades | 调整历史原始答案 |
| Learning | 可信事件摄入、笔记写入 | 进度、证据、画像 | events、notes、evidence | 接受客户端认证成绩 |
| Recommendation | 目标、证据、内容可用性 | 排序提案、原因、置信标识 | 推荐快照/接受拒绝记录 | 强制改变路线 |
| Retrieval | query、授权 scope、修订约束 | RankedEvidence | 派生索引、检索日志 | 越权读取解答 |
| Context/Policy | 会话、对象引用、选文、授权 | 不可变 ContextSnapshot、受检准备材料 | 请求快照、审计；通过真实来源 owner 核验准备材料 | 把教材指令当系统指令、替未知任务伪造正文 |
| Tutor | question、intent、context、web flag | Run、回答、引用、建议动作 | 对话、Agent run | 未确认改教材/分数 |
| Authoring/Quality | 生成要求、审核、发布请求 | Draft、ChangeProposal、Review | 草稿、审校记录 | 自我授予独立教学通过 |
| Provider/CodexBroker | 受控生成/搜索/工具请求 | 真实能力、冻结授权摘要、受检事件和产物 | 提供商配置/秘密引用、授权/派发/用量账本与自有终态回执；不代写 consumer Job/Run | 向前端暴露密钥/任意路径、凭任意 consent ID 直接外发 |
| Workspace/Jobs | 备份、恢复、任务控制 | 快照、任务状态、反馈 | 工作区配置、队列、备份 | 默认公开监听或自动联网 |
| Connector | 同步/外部写入提案 | Zotero/博客候选与结果 | 外部关联、同步游标 | 未授权改外部资料 |

领域关系示意：

```text
React Workbench
  └── typed API client
       └── FastAPI application services
            ├── Policy + ContextSnapshot
            ├── Content / Route / Practice / Assessment / Learning
            ├── Recommendation / Retrieval
            └── Tutor / Authoring → durable Jobs → Provider / CodexBroker
                                          │
                              Approval / Budget / Audit
Storage: SQLite（业务与队列） + 本机文件库（不可变原件/正文）
Derived: FTS/向量索引（可重建、不作为原始数据权威源）
```

## 8. 技术选型与明确取舍

| 层 | 主线选择 | 理由 | 不选/延后 |
|---|---|---|---|
| 前端宿主 | React + TypeScript + Vite SPA | 三栏、标签、抽屉和复杂局部状态可组件化；本机学习不需要 SEO/SSR | 从零不引入 Next.js SSR；已有 Next.js 可作宿主 |
| 前端状态 | React 局部状态 + 集中 Workbench store；TanStack Query 管服务端缓存 | UI 状态与业务权威数据分开；避免复制整套数据库到多个 store | 不以 localStorage 存真实成绩权威副本 |
| Markdown | unified/remark AST + 明确受限 HTML 投影 | 按内容块渲染、可追踪公式与来源；禁用任意 MDX 执行 | 不执行用户导入的 JS/React 组件 |
| 源码编辑 | CodeMirror 6，仅创作视图 | 读取界面不需要代码编辑器；作者需要 Markdown/LaTeX 编辑与差异视图 | Monaco/Electron 非首期必需 |
| 数学渲染 | 本地 MathJax TeX→SVG，宏白名单 | 本项目复杂数学内容较多；保留 LaTeX 源文，可离线渲染 | 不承诺完整桌面 TeX 宏包兼容 |
| 后端 | Python 3.12 系列 + FastAPI + Pydantic 2 | 数学/文件工具生态与类型契约，生成 OpenAPI | 不在前端保存密钥或独立评分权威结果 |
| 运行时 | Node.js 24 LTS；实际依赖精确锁定 | 这是本项目起始版本选择；在 M0 核对官方维护状态、Vite engine 要求和依赖兼容性并锁定补丁版本 | 不写不经核验的“永远最新版” |
| 数据库 | SQLite WAL + foreign_keys=ON + 迁移脚本 | 首期单用户、本机事务与备份足够；运行成本小 | 多用户部署再迁 PostgreSQL |
| 检索 | FTS5 + 中文预分词 + 可选向量检索 | 先建立有基准的词法检索，再验证向量增益 | 不默认 FAISS 或向量服务就是高质量 RAG |
| 队列 | SQLite jobs/outbox + 单 worker + 租约 | 首期可持久化、恢复、幂等，无额外 Redis | 不用进程内 fire-and-forget 承诺可靠完成 |
| 流式交互 | HTTP 创建任务 + SSE 读事件 + HTTP 取消/审批 | 单向流易审计、断线可回放 | 只有双向工具协议内部确有需要时才用 WebSocket |
| 大模型 | 自有 ProviderPort + 官方/兼容适配器 | 权限、工具、结构化输出能力差异显式呈现 | 不以兼容聊天 API 冒充支持搜索 |
| Codex | 独立 Broker 适配 App Server | 支持会话事件和审批；不把进程细节耦合进前端 | 不让浏览器直接调用 shell |
| 测试 | pytest、契约测试、前端单测、Playwright | 领域/权限/浏览器/真实提供商分层 | 不只看截图，不把 mock 成功写成线上通过 |

以上是产品决策。React 官方文档说明状态与组件在树中的位置/身份有关，因此中央标签和线程需有稳定键，不依赖偶然挂载行为；FastAPI 官方说明其类型校验及 OpenAPI 支持；JSON Schema 2020-12 用作文件契约基础。[S7][S8][S9]

SQLite 外键需要按连接启用并验证，不能因 SQL 写了 FOREIGN KEY 就假设运行中已生效。FTS 的 tokenizer 行为也必须测试，尤其是中文、公式符号和中英混合检索。[S10][S11]

MathJax 只支持其定义的 TeX/LaTeX 输入范围，不是完整 TeX 排版系统。导入时建立公式能力报告；不能显示的宏保留源文并标错，不自动“改写成看起来差不多的公式”。[S12]

## 9. 数据模型、版本与一致性

### 9.1 通用规则

标识符使用不可变 ASCII ID（推荐实体前缀 + UUID）；显示名称可中文、可修改，不参与身份识别。所有可引用教材对象有整数 `revision >= 1`。对外文件有独立 `schema_version=3.0.0`，内容修订不能替代格式版本。审校对象用 DraftCandidate 而非未发布的 ContentRef。ContextSnapshot.snapshot_sha256 的计算排除 snapshot_sha256 自身字段，request_sha256 对原请求规范JSON计算；两者算法与版本单独记录。

时间统一 RFC 3339 UTC；展示层本地化。内容文件统一 UTF-8、LF，哈希计算原始存储字节。元数据哈希采用项目固定的规范 JSON 序列化：排序键、无多余空白、UTF-8、不允许 NaN/Infinity，并记录算法版本；这不自称遵守其他未实现的规范化标准。

正式对象只能引用相同工作区可访问的精确修订。版本 `latest` 可作为查询意图，但一旦打开测试、生成笔记或发送请求，必须解析并冻结成具体 revision/hash。

### 9.2 核心关系表

| 对象/表 | 主键与关联 | 最重要字段/约束 |
|---|---|---|
| workspace | id | 单用户配置，不含返回前端的密钥 |
| sources | id | 原始文件 sha256、MIME、local path、rights、parser_version |
| objects | id | kind、workspace_id、current_revision；当前指针可变 |
| revisions | object_id + revision | metadata JSON、sha256、status、created_at；发布后不可变 |
| content_blobs | sha256 | 相对路径、size；先原子写文件再引用 |
| concept_edges | course_revision + prerequisite + dependent | DAG 语义校验，不允许自环 |
| routes / route_steps | route_revision + step_id | typed target refs、依赖、完成策略；内容与进度分离 |
| solutions | question_id + question_revision + solution_revision | 标准答案/私有评分信息，严格访问控制 |
| attempts | id | mode、policy_snapshot、question_refs、status、owner/workspace |
| responses | attempt_id + question_id | answer、steps、draft_revision、updated_at |
| grades | attempt_id + grading_revision | 规则版本、结果、review_status；不覆盖旧评分 |
| exposures | learner + question/exposure_group + event_id | hint/solution/prior attempt 等，去重 |
| learning_events | event_id | actor、origin、entity_ref、occurred_at；不可覆写 |
| evidence | id | attempt/grade 引用、skill、eligibility、invalid_reason |
| notes | id + revision | quote selector、content_ref、user Markdown |
| threads / messages | thread_id/message_id | scope、ContextSnapshot、provider、status、citations |
| jobs / job_events | job_id/seq | 状态、租约、输入哈希、重试、取消、终态 |
| proposals / reviews | id + target_revision | 变更、内容哈希、批准人与独立审校状态 |
| idempotency | actor + route + key | request_hash、result_ref、过期策略 |

附录 B 的内嵌 Python 模型定义核心交换对象；附录 A 给出全部业务 HTTP 输入/输出字段；附录 C 给出关系表、约束与存储映射。M0 从这些内容生成工程内 Schema、OpenAPI 和迁移文件，不需下载任何配套文件。正式实现还要为业务不变量增加应用事务与迁移，不应误认为 JSON 类型校验可以证明引用无环、用户有权限或数学内容正确。

### 9.3 事务与文件一致性

原始文件先写到随机暂存名、计算哈希、完成 fsync/原子 rename，再在数据库事务中建立引用。失败产生未引用 blob，后台按安全保留期清理；绝不能先提交引用再任由文件写入失败。

章节发布、当前指针更新、依赖失效事件和 outbox 入队在同一数据库事务中完成。索引构建在事务外进行，成功后切换索引清单；索引未就绪时标明状态，不能用旧内容冒充新修订。

M5.2 每个已登记显式scope有独立代际；Content的失效意图不清除其他owner的影响复核信号。GET/query只读，不创建scope/任务。新重建由显式POST登记真实Job，worker仅恢复已有任务；其冻结/构建/原子切换和旧scope语义见§20.7及附录A/D。

后端正式权威源与浏览器离线草稿分开。离线草稿是待同步命令，不是已经入库的事实。每次恢复检查基准 revision，冲突时显示三方比较，不静默覆盖。

## 10. 文件格式与学习包规范

### 10.1 支持矩阵

| 输入 | 导入行为 | 保真边界 |
|---|---|---|
| `.md` / `.markdown` | 解析标题、公式、代码、引用；预览后转换成块 | 扩展 HTML 只允许白名单 |
| `.txt` | UTF-8 文本作为一个未结构化块 | 不猜测所有数学语义 |
| `.html` | 移除脚本/事件属性/主动外链资源；提取安全正文与 TeX | 只有 SVG/图片的公式不自动恢复 LaTeX |
| `.pdf` | 用受限进程提取文本和页码；原件可阅读 | 公式、双栏、表格错序要警告；扫描版默认不 OCR |
| `.docx` | 提取段落/表格/标题；原件保留 | OMML、浮动图片和复杂版式不能直接当作准确 TeX |
| `.learnpack.zip` | 严格清单、哈希、权限与语义检查后导入 | 不能执行包内代码或接受外部文件路径 |
| 路线/阅读记录 JSON | 精确 ID 映射、确认后导入 | 无法匹配对象时保持 unresolved，不按相似标题强猜 |

单原件初始限制 50 MiB；文本块 400,000 字符；学习包解压总量 200 MiB、文件数 2,000、压缩比上限 100。这些是可配置安全预算，不是文件格式的固有限制。超限可经显式配置扩大，不允许“部分读完却宣称完整导入”。

### 10.2 学习包目录

```text
course.learnpack.zip
├── manifest.json
├── course.json
├── concepts.json
├── symbols.json
├── lessons/
│   └── lesson_ols.r1.json
├── blocks/
│   ├── block_definition.r1.json
│   └── block_example.r1.json
├── content/
│   ├── block_definition.r1.md
│   └── block_example.r1.md
├── practice/
│   └── practice_ols.r1.json
├── assessments/
│   └── test_stage1.r1.json
├── questions/
│   └── public.jsonl
├── private/
│   └── solutions.jsonl          # 仅作者包含；学习者包必须实际排除
├── sources/
│   └── citations.json
├── assets/                     # 经确认的被动资源
└── checks/
    └── quality-receipt.json
```

每个 `.jsonl` 行为一个完整 JSON 对象，末尾 LF，不允许多行对象。`content/` 中的 Markdown 是正文权威源；元数据只引用它，不复制第二份可独立修改的正文。`course.json` 等文件引用精确对象修订；跨文件引用必须做语义校验。

`manifest.json` 必须列出每个 payload 文件的相对路径、字节大小、SHA-256、媒体类型及 visibility。它不把自身放进自己的哈希清单。包内不能出现未声明文件、绝对路径、`..`、反斜杠歧义、符号链接、设备文件或重复规范化路径。manifest 外的整体包哈希放在导入/导出回执中。

visibility 取 `learner` 或 `author_private`。导出学习者包不是 CSS 隐藏 private/，而是**不写入私有文件**，并重新生成 manifest。包含了答案的作者包导入后仍只在服务端私有库中可见，不能直接挂成整个静态目录。

### 10.3 正文规范

公式使用 `$...$` / `$$...$$` 或 `\(...\)` / `\[...\]`，同一发布 profile 固定一种主要风格。正文不能用 Unicode 外观相似符号偷偷替代变量。声明全书符号：名称、TeX、定义域、维度、首次定义块；不同含义的同符号必须明确作用域。

章首提供学习目标和逻辑链，节内至少考虑定义/条件、推导、直觉、算例、边界与小结。用户要求严格证明时，不能由平台或生成 Agent 自动降低 proof_policy。内容质量与排版质量分别记录。

图片、代码和数值输出必须有来源/生成方式和绑定对象。代码默认为文本；只有用户明确批准的验证任务才在隔离 worker 中运行。运行产物有输入、种子、软件版本、输出哈希和退出码。

### 10.4 笔记、学习记录和兼容迁移

笔记使用 Markdown + JSON 元数据，anchor 采用 `ref + exact_quote + prefix + suffix + start_codepoint/end_codepoint`。偏移按 Unicode code point 定义，不混用 UTF-8 字节和 JavaScript UTF-16 单元。修订不变时精确定位；修订变化先标记 stale，再尝试候选映射并由用户确认。

事件导出使用 JSONL，包含 event_id、origin、时间、实体引用和最小 payload。外部导入的阅读/答题记录标记为用户提供，不认证成绩。完整工作区备份可以含用户自己的提交后答案，须明确敏感性；它与无答案学习者包不是同一种导出。

历史格式导入采用受限 LegacyAdapter：只有本文件第 21 章规定的可识别轮廓可自动迁移，未知字段保存在隔离原件中并提示，不静默删除。旧 Demo 不是开发依赖；不能为推测私有旧格式而访问其他仓库。保留原始 ID 映射、修订、警告和原备份；不支持的旧文件可作为参考附件保存，但不得显示“完整迁移成功”。

## 11. API 与模块端口规范

### 11.1 基础协议

生产目标前缀 `/api/v1`，JSON 请求/响应使用 UTF-8。本文件定义交换语义；由本文生成并核对的 OpenAPI 3.1 与 JSON Schema 是运行接口的机器投影。前端类型从契约生成，不复制手工“差不多”的 DTO。

读取提供分页；默认 limit=20、最大100；大正文通过精确对象接口按需取，不让列表接口下发整库。写入要求 CSRF/本机会话校验；领域创建命令带 `Idempotency-Key`，修改带 `If-Match` 或显式 `expected_revision`。版本过期返回 412，业务状态冲突返回 409。

列表响应形状：`{items, next_cursor, total_hint}`。total_hint 可省略，不为计算总数扫描所有大文件。成功创建长任务返回 202 和 job/run 引用，不能返回“已发布”而任务仍未完成。

### 11.2 主要接口目录

| 模块 | 目标接口 | 请求/响应要点 |
|---|---|---|
| Workspace | GET `/workspace`；PUT `/workspace/preferences` | UI/学习偏好与 revision，不返回密钥 |
| Import | POST `/imports`；GET `/imports/{id}`；POST `/imports/{id}/commit`；POST `/imports/{id}/cancel` | 原件上传、预览任务、确认与幂等 |
| Content | GET `/courses`；GET `/courses/{id}`；GET `/lessons/{id}?revision=`；GET `/blocks/{id}?revision=` | 列表轻量；精确修订正文 |
| Draft | POST `/drafts`；PATCH `/drafts/{id}`；POST `/drafts/{id}/review`；POST `/drafts/{id}/publish` | 基准修订、变更、审核回执、发布 |
| Route | GET/POST `/routes`；PUT `/routes/{id}`；POST `/routes/{id}/steps/{step_id}/complete` | typed refs、依赖、版本与人工标记 |
| Practice | POST `/practice/sessions`；PUT `/practice/sessions/{id}/responses`；POST `/practice/sessions/{id}/submit` | 题集、草稿版本、反馈 |
| Practice reveal | POST `/practice/sessions/{id}/hints`；POST `/practice/sessions/{id}/solutions` | policy 检查、暴露事件与解答 |
| Assessment | GET `/assessments`；POST `/assessments/{id}/attempts` | 蓝图与公开题面；冻结策略 |
| Attempt | GET `/attempts/{id}`；PUT `/attempts/{id}/responses`；POST `/attempts/{id}/submit`；POST `/attempts/{id}/abandon`；GET `/attempts/{id}/result` | 活动态不返回私有解答 |
| Tutor | POST `/threads`；GET `/threads`；GET `/threads/{id}/messages`；POST `/tutor/runs` | 严格应用 DTO、真实任务/上下文身份，不信任客户端全文 |
| Run | GET `/runs/{id}`；GET `/runs/{id}/events`；POST `/runs/{id}/cancel` | 快照、SSE、取消 |
| Retrieval | POST `/retrieval/query` | query、scope、revision；role从服务端会话取得 |
| Learning | GET `/learning/progress`；POST `/learning/actions`；GET `/learning/evidence` | 动作与可信事件分离 |
| Notes | GET/POST `/notes`；PATCH `/notes/{id}` | anchor、Markdown、expected_revision |
| Recommendation | GET `/recommendations`；POST `/recommendations/{id}/decision` | 原因/证据与用户接受拒绝 |
| Provider | GET `/providers/capabilities`；配置/秘密；POST `/consents/preview`；POST `/consents`；GET `/consents`；POST `/consents/{id}/revoke` | 附录 A 的十个精确操作；本机配置、服务端冻结、明确批准、当前/历史回读、撤回 |
| Authoring generation | POST/GET `/authoring/jobs`；GET `/authoring/jobs/{id}`；GET `/authoring/drafts/{id}`；候选数值检查预览/决定/读取；GET `/jobs/{id}`；POST `/jobs/{id}/cancel` | 首个例题授权前准备、真实候选与独立数值执行批准，精确路由见附录 A |
| Approval | POST `/approvals/{id}/decision` | 绑定任务、操作哈希、单次/范围审批 |
| Codex | POST `/codex/sessions`；POST `/codex/sessions/{id}/turns`；POST `/codex/sessions/{id}/interrupt` | Broker 转译、产物限沙盒目录 |
| Export | POST `/exports`；GET `/exports/{id}`；POST `/backups/restore-preview`；POST `/backups/restore-commit` | profile、清单、确认与回滚 |
| Feedback | POST `/feedback` | 描述、复现、期待，不默认附私密正文 |
| Connector | GET `/connectors`；POST `/connectors/{id}/preview`；POST `/connectors/{id}/apply` | 同步提案与批准操作分开 |

本表是入口索引，附录 A 的路由与完整字段表是全量 HTTP 目录；附录 B 是核心共用类型，附录 D 是模块端口。所有页面操作都必须能对应附录 A 的命令/查询；各模块在进入实现前生成其强类型 DTO、OpenAPI 和契约测试，不允许 `{data:any}` 或空端点充数。ContentRef、QuestionPublic、AttemptPublic、RunEvent 等字段名固定。

### 11.3 向 Tutor 发送请求的示例

```json
{
  "request": {
    "thread_id": "thread_ols",
    "workspace_id": "workspace_local",
    "message": "为什么 A 必须大于零？",
    "intent": "derive",
    "context": {
      "view_kind": "lesson",
      "active_ref": {
        "entity": "lesson", "id": "lesson_ols", "revision": 1,
        "sha256": "由服务端已读取对象提供的64位小写十六进制哈希"
      },
      "attached_refs": [], "selection": null, "attempt_id": null
    },
    "web_search": false,
    "consent_id": null
  },
  "expected_thread_revision": 1,
  "binding": {"practice": null, "assessment": null}
}
```

这是附录 A 的 TutorRunCreate 应用请求；内层 TutorRequest 保持原 core 形状。哈希说明文本不是生产值；附录 E 仍生成合法核心请求样例。真实线程由 POST threads 创建/GET threads 回读，revision 不照抄示例。首次创建只建立本地任务，consent_id 必须 null；后续以实际 Run/Job ID 和当前 revision 使用现有授权预览/批准接口，不能改 body 再 POST 原 Run。后端按 refs 和 owner 身份读取、校验工作区、权限、版本与 hash，不能借 lesson 类型读取未释放答案。

### 11.4 事件协议与错误

SSE 每个事件包含 `run_id`、递增 `seq`、`type`、UTC 时间和受约束 payload。类型至少包括 queued、context_ready、retrieval_completed、answer_delta、citation、approval_required、usage、completed、failed、cancelled。终态只能出现一次；消费端按 `(run_id, seq)` 去重。

重连用 `Last-Event-ID` 或 `after_seq` 回读；读事件不重新启动模型生成，不重复计费。保存最终回答和来源之后才能发 completed。M5.3 严格字段、持久化、游标与安全回读以附录 A 为准，流不能伪装成 JSON 响应。网络中断时显示“连接中断，任务状态未知”，查询快照后再决定恢复，不自动从头请求。

错误形状：`{error:{code,message,request_id,retryable,details}}`，不含密钥、绝对私有路径、原始请求全文。常见 code：SCHEMA_INVALID、REFERENCE_MISSING、REVISION_MISMATCH、POLICY_DENIED、ASSESSMENT_ACTIVE、PROVIDER_UNCONFIGURED、CAPABILITY_UNSUPPORTED、BUDGET_EXCEEDED、SOURCE_UNVERIFIED、INDEX_STALE、JOB_CANCELLED。

## 12. Agent、检索、搜索与生成边界

### 12.1 明确的状态机

```text
created → policy_checked → context_frozen → retrieving（可选）
        → awaiting_approval（需要工具/外发授权时）
        → generating → output_validating → completed
        ↘ failed / cancelled
```

动作提案与动作执行分开。Tutor 可以提出“生成三道习题”或“修订这段解释”，但这只是 `ProposedAction`；用户确认后才由 Authoring 建立任务。Tutor 无权直接调用发布接口、改成绩或改用户知识画像。

四种教学意图不是四个独立的全权限 Agent。首期用一条可观测编排链，通过输入约束与输出目标区别讲解、提示、推导、拓展。只有代码验证、结构检查等确有独立输入输出的任务才拆 worker。

### 12.2 上下文预算

先校验权限定范围，再检索和排序；不能先用全库搜索把答案找出来，最后靠提示词让模型“别用”。默认优先：用户主动选文 → 当前内容块 → 必要定义和先修 → 已批准的本教材相关块 → 用户明确允许的外部来源。

M5.2 的明确选择、未审公开材料与自动补足边界以 §20.7 为准：仅在显式 course/lesson/block 精确范围内做本地词法检索，每hit保留未审/来源事实；当前阶段不实现缺乏批准owner的自动相关扩展，也不把这条优先链当作扩大范围或联网许可。

Context 消费端的初始工程预算：上下文最多 12,000 中文/混合字符、最多 8 个内容块、最多 6 条最近对话摘录、最多 5 个外部来源。M5.2 检索整块返回采用 §20.7 的独立字节预算，不套用这里的8块/12,000字符上限。实际 Token 上限由提供商 tokenizer/模型上下文能力约束。字符数不是 Token 数；截断必须保留块边界，不能把定理条件截掉只留结论。

回复包含证据类别：教材已给出的陈述、外部来源陈述、模型自行推导、暂时无法核验。对缺证据的问题可以明确说明不足并给推导尝试，不能伪造文献或把缺证据回答伪装成已有教材引用。

M5.3 全部生成回答/拒答原文明确标为“模型输出／推导尝试，未逐项核验”，单列本次实际输入的精确 ref、正文/摘录 SHA 与未审事实。材料只证明输入了什么，不证明答案、相邻论断或推导受其支持。四类证据中，教材栏只列真实输入原文，外部栏明确“未检索/无受检外部来源”，模型输出与不能核验明确展示；不能用图例假称每段已分类。模型自报链接/引文/标记及原未审 Citation 不自动升级为已核引用。此阶段不要求额外包装语言、文本区间或评分器；无受检来源时 citations=[]，原模型文字仍保留。

Context 仅用当前精确对象与显式 attached_refs，经 Content/Route/Practice/Assessment owner 取得真实材料；不自动补先修/相关范围，不偷偷重建 missing/stale 索引。选文先按原 block/正文 SHA 与 codepoint 核验，优先其所属完整块，其次当前块，再按显式范围的既定顺序/检索结果纳入完整块；不能截选文前提或块正文。route/practice/assessment 非 block 材料由 owner 冻结为完整有界单位，不信任客户端显示文本。原作答、已获提示、已释放反馈按真实 session/attempt/question/评分版本读取，未释放标准答案不得纳入。

12,000 字符按最终 messages 内容总和计，包括系统模板、当前问题、真实历史、题目/作答/反馈及每项完整 `<reference>\n{规范JSON的ref、locator、text}\n</reference>` 包装，与 Provider RequestPreparer 同算法，以 Unicode codepoint 计数，绝非 token 证明。保留 material.messages≤6，系统模板与本次问题占两条，因此历史最多四条（也满足本节最多六条上限）；evidence≤8。历史只取本线程已完成轮次的真实 user/answer 消息，按时间顺序冻结 ID/字节；拒答/失败部分输出不自动当教学历史。可选块/历史只能整项省略并明示理由；系统、本次问题、当前交互必需的完整题目/作答等本身超预算时明确 TUTOR_CONTEXT_BUDGET_EXCEEDED，不裁条件或返回虚假空成功。材料是数据角色，无系统指令权；模板意图/版本冻结。§20.5 完整输入证明与零外发边界不变。

### 12.3 联网搜索

ProviderCapabilities 明确 chat、structured_output、web_search、streaming、tool_calls。官方 Responses 的搜索工具提供搜索调用和引用结果；是否真的调用工具必须从响应事实确定。通用 OpenAI-compatible 聊天协议不能自动视为支持搜索。[S13] M5.1 仅开放已核模型/输入形状的文本 chat/streaming；search、tool、structured_output 为 false。配置或秘密引用存在不等于可调度，缺少 §20.5 的完整输入证明时 chat/streaming 也必须为 false；不自动联网探测能力。后续阶段增加能力须同时明确许可、预算与实际协议验证。

需要独立搜索服务时，通过 SearchPort 接入，并保留 query、抓取时间、页面标题、URL、摘要与定位。对授权文件内容发到哪个服务、发多少内容，要在授权摘要中清楚列出。即使用户开启联网，也不代表同意自动把整个私有资料库发给搜索引擎。

### 12.4 结构化生成与校验

结构化输出可以约束对象形状；它不能证明公式正确、来源真实或题目无歧义。[S14]

流程固定为：生成内容计划 → 生成草稿 → Schema 校验 → 引用与版本校验 → 符号一致性检查 → 数值例复算 → 数学/来源审校 → 用户审核 → 发布。失败产物仍可供用户检查，但状态必须为 rejected/needs_review，不可改成 published。

题目质量检查至少覆盖：唯一答案/可接受答案集合、干扰项合理性、题干条件充分、单位、允许精度、解答与评分一致、题目目标与教材目标匹配、未使用尚未讲授且未注明的知识。

### 12.5 Codex Broker

官方 App Server 有 thread/turn/item 事件及审批交互；本项目 Broker 应据固定版本适配，而不是把事件名和进程控制逻辑散落到 React 组件。[S15]

Broker 的最小职责：探测可用性与授权状态；维护产品 session 到 Codex thread 的映射；仅在隔离工作目录运行；转译命令/文件/网络审批；中断与清理；扫描产物；返回受控路径的文件引用；保留费用/状态证据。涉及权限提高、网络和文件变更要展示操作范围，不因工具名字叫“生成教材”就默认批准所有 shell 命令。

用户拒绝审批后，任务记录为 declined/cancelled；不能自动换一条更高权限路径继续。产物中的外部链接、脚本和提示仍按不可信导入处理。

## 13. 评分、证据与推荐规则

### 13.1 评分分层

| 题型 | 自动评分 | 需要记录 | 不得声称 |
|---|---|---|---|
| 单选 | 选项 ID 精确匹配 | 题目修订、选项快照、首答 | 猜对等于理解 |
| 文本填空 | 规范化后的允许集合 | 大小写/空格/同义规则 | 任意语义等价都被支持 |
| 数值填空/计算 | 有限数值 + 指定容差 + 单位换算 | 输入、解析值、容差、单位 | 最终数值正确等于步骤正确 |
| 符号表达式 | 受限 AST、条件域检查、受控等价检查 | 变量域、规则与超时 | 少量随机点一致就是证明 |
| 推导/证明 | rubric 辅助与人工复核 | 每项依据、review_status | LLM 一次打分就是可靠终审 |

数值比较规则：`abs(user - expected) <= atol + rtol * abs(expected)`，不使用不透明的四舍五入字符串比较。输入禁止 eval/任意 Python；限制字符长度、表达式深度、运算节点和执行时间。评分程序版本写入 grading_revision。

### 13.2 证据资格

系统先判断能否作为独立证据，再计算得分。必要条件至少包括：本次模式是 independent；提交前没有提示/答案获取；标准答案已经审核；评分状态 resolved；题目/概念映射有效；没有被判定为重复或已暴露同一解答模板的未见题证据；数据来自可信服务端事件而非用户导入声明。

不符合者保留为学习记录，并明确 exclusion reason，而不是删除。已看过题仍可用于复习保持情况，但不能再宣传成首次迁移表现。需要区分“独立完成”“之前未见”“延迟复习”这三个不同属性。

### 13.3 推荐第一版

首期采用可解释规则，不训练一个缺少数据却声称个性化准确的模型。候选项先过滤权限/审核状态/课程可用性，再处理先修和目标。审核状态过滤按用途进行：未审教材或习题可作为阅读、练习或来源查看候选，但每项 explanation 和页面 warning 必须明确其实际未审状态，不承诺评分、独立证据资格或已验证补弱效果。用于补足独立证据的 test 候选必须实际可用、概念/技能映射完整、固定答案已审核且当前全工作区 prior-seen/暴露资格满足；没有合适测试就报告真实缺口，不能把普通可启动但未具资格的测验冒充诊断。

默认顺序：存在确定性错题时推荐其依赖概念；先修缺证据时提供诊断或基础材料；已读但未练时推荐习题；有基础练习但缺独立证据时推荐合适测试；有既有证据且到复习时间时推荐复习；否则按用户目标和路线推进。用户可以跳过，并写入 skip_reason，不自动降低能力分。

推荐输出包含：target_ref、action、reason_codes、evidence_refs、prerequisite_gaps、estimated_minutes、rule_version、generated_at、staleness。新结果到来后失效旧推荐，不能把昨日依据当作实时事实。

推荐由 Recommendation 模块在源变更事务中登记失效意图，并由本地持久 worker 的启动恢复或后台维护生成及切换冻结投影。GET 只读取既有投影和只读核验当前依据，不生成、写 stale、排队刷新或调用外部服务。新学习结果、画像/路线/内容可用性变化或复习时点到达后，旧依据不再标为 current；计算失败保留旧快照及明确诊断，不改学习事实。推荐不能把自己消费了失效意图等同于 Content 已完成影响复核，不得清除其他模块仍需要的待复核信号。

具体 HTTP 字段使用附录 A 的 RecommendationView/RecommendationPage；附录 B 的 Recommendation 保留原交换形状，不作为该端点的解码类型。原因有限枚举明确区分 read_without_practice 与 practice_without_independent，不给没有目标、路线或先修关系的参与活动伪造相应原因。Evidence 引用不是 ContentRef.Entity，评分来源引用必须保留真实 Evidence、作答、评分版本及精确内容身份。推荐的确定性错误依据须由 Assessment 核验该题在所选评分版本中的实际判分来源；人工重评后的低分或保留下来的旧确定性 trace 不自动变成当前确定性错题。

接受、拒绝或显式更正决定/理由只改变推荐自己的决定历史，不改变路线、学习事件、成绩或能力状态；接受不自动打开付费工具、联网、重排或标记完成。实际打开材料仍走该精确对象的正常权限与读取流程。文档版本 3.0.1 的本次推荐 HTTP 更正不改变学习包及附录 B 核心模型的 schema_version=3.0.0，也不重写既有历史回执。


**自报与跨教材推荐。** 用户通过设置中的“学习目标与基础”填写目标、每周时间、语言、概念自评（未学/接触过/能独立使用）和偏好难度；每项标记 self_report，独立保留来源与时间。候选范围默认当前工作区已导入且可访问的全部教材，不限当前一本；排序依次考虑目标概念覆盖、先修缺口、最近可信错题、内容审核等级和阅读成本。没有合适本地内容时给“缺少对应教材”的理由，可提出联网查找候选，但只有授权后才调用搜索。外部推荐返回候选标题、来源、定位及待导入状态，不伪造已拥有该教材。无授权时依然能运行本地规则。推荐的 estimated_minutes 未有实测来源时返回 null，不生成虚构数字。

初始“3 天提醒复习”等参数只是可配置默认值，应标记为未校准。后续引入记忆调度、BKT/IRT 等模型要有不同能力维度、题目质量和校准实验，不能把数学模型名称当作有效性证明。

## 14. 安全、隐私、费用与可靠性

本机默认只监听 127.0.0.1/::1；限制 Host 与 Origin，写请求验证会话和 CSRF。配置外部监听地址时启动失败并提示公共部署尚未提供，而不是静默开放。

数据库、上传文件、聊天、答案和密钥不进 Git；`.env.example` 只放占位符。日志默认只记录 request_id、对象 ID、状态、时长和计量，不记录教材全文、提示词全文或秘密。用户可单独批准诊断快照，导出前预览和脱敏。

文件读取与 Web 抓取要防路径穿越、Zip bomb、SSRF、自动跳转到内网、可执行 HTML、超大公式/宏和代码注入。URL 抓取每次重定向重新检查 scheme、域名/IP、端口和响应大小；远程资源不因为被教材链接就默认可信。

Prompt injection 不能靠一句“忽略恶意指令”解决。工具最小权限、私有答案隔离、上下文白名单、用户审批和结果验证共同限制影响；把网页内容视为指令会破坏权限边界。[S16]

每个请求有最大输入/输出 Token、搜索次数、工具次数、时长和可选费用预算。价格来自可更新的提供商配置，不在源代码中永久写死。计费不确定时显示 estimated；取消不保证服务商撤销已发生费用，应在 UI 明确说明。

## 15. 状态机、失败恢复和更新影响

### 15.1 唯一状态字典与事务边界

以下是 HTTP、数据库与 UI 共同使用的唯一状态；内部步骤不是第二套公开状态名。

```text
Draft: draft → in_review → approved → published
                   ↘ needs_changes → draft
       draft / needs_changes → cancelled
Attempt: active → submitted → grading → graded
             ↘ abandoned         ↘ needs_review → grading → graded
Job / Run: queued → running ↔ awaiting_approval → completed
               ↘ failed / cancelled
```

Published revision 不可原位修改；归档发生在对象的 `lifecycle=archived`，不更改已发布 revision。草稿的 `published` 表示已生成不可变 revision。`cancel_requested` 是布尔请求字段、`next_retry_at` 是调度字段，不能当作另一个不一致的公共 status。状态转换使用事务比较当前 revision。

attempt 开始时同时冻结题目修订、私有答案修订、策略、题序、开始时间、可选截止时间；公开投影禁止携带私有答案引用。作答草稿保存只允许 active。submitted 后提交快照不可改写；评分任务用固定答案版本，重评增加 grading_revision 并保留旧结果。needs_review 不算零分、不自动产生错题证据。`abandoned` 不生成独立成绩。

completed/failed/cancelled 三个 job 终态互斥，完成事件和最终产物同一事务提交。租约超时重试需要幂等副作用保护；已付费的外部请求不能仅因客户端断线就自动重放。取消外部调用不保证费用回滚。

### 15.2 版本失效传播

内容块改变 → 查找引用它的章节 → 查找引用该章节/块的题目与路线 → 标记教材阅读定位/笔记锚点需要复核 → 使对应检索分片和推荐快照失效。对影响不确定的对象采用 needs_review，而非直接删掉全部学习进度。

传播是可追踪任务，报告 affected_ids、reason、old_ref、new_ref。重新验证后按对象清除 stale。审校批准必须绑定内容哈希；批准后的正文再变更，会自动使旧批准失效。

### 15.3 断线和多标签

作答草稿自动保存采用基准修订；两个标签同时编辑同一 response 返回冲突而非最后写入获胜。独立测试策略由服务端的活动 attempt 查询决定，不由前端布尔变量决定。

导入与导出中断可凭 job_id 回读。Worker 崩溃后超过租约的任务重新领取，但应用副作用依靠幂等键避免重复发布/重复同步。宣称“恰好一次”必须谨慎：实际设计是可重试投递 + 幂等领域副作用。

## 16. 验收和质量门禁

### 16.1 分层验收

第一层契约：Schema、引用、权限、状态机、错误、幂等与迁移。第二层业务：导入—阅读—习题—测试—证据—推荐闭环。第三层浏览器：真实鼠标/键盘、公式、滚动、保存、焦点、窄屏。第四层真实提供商：授权、搜索调用、引用、限额、取消、断线与错误。第五层内容/教学：数学正确性、来源、数值例和真实学习者表现。

不能用其中一层 PASS 代替另一层。执行 Agent 的最终报告必须包含 PASS、FAIL、BLOCKED_ENVIRONMENT、NOT_RUN 的实际分布和原始证据位置。

### 16.2 发布阻断条件

任何已知答案泄漏、未授权外发、学习记录丢失、错误评分未标注、关键公式无法显示、发布覆盖旧版本、未实现却可点击“成功”的假功能，均为发布阻断。真实提供商不能测试时，可交付明确的离线演示版，但不能把完整个人版所有需求标绿。

### 16.3 关键验收场景

- 从空工作区导入教材，按四个导航入口完成学习，界面关系不依赖演示数据硬编码。
- 在章节 A 提问后切到 B，A 的响应不会进入 B；不同对象草稿互不覆盖。
- 习题展开答案记录 exposure；独立测试服务端不返回答案或旧消息。
- 直接请求接口、打开第二标签、调用创作助手都不能绕过活动独立测试策略。
- 网络断开后草稿仍存在；重连不重复交卷、不重复启动付费请求。
- 导入恶意 HTML、损坏 ZIP、含重复 ID 的课程包时，失败原因明确且不污染正式工作区。
- 修改题目后旧 attempt 仍可回放原题；数学条件变更后相关对象显示待复核。
- 选择题、数值题、单位、无效表达式、符号域、待人工题按规则处理。
- 没有证据时不显示百分比；已读和已看答案不自动成为独立掌握证据。
- 学习者导出包内确实不存在私有答案；完整个人备份能校验、预览、恢复与回滚。

附录 F 内嵌 Gherkin 目标场景；第 2 章是需求追踪起点。开发 Agent 必须实现 step definitions 后才能把它们作为产品自动化验收，文字场景存在本身不算通过。性能预算初值：已缓存视图切换 p95 <200ms；本机普通 API p95 <300ms；1 MiB Markdown 首屏 <2s。所有数字是待测目标，报告必须固定硬件、数据规模、冷/热缓存和样本数，不把网络模型耗时混入本机性能结论。

## 17. 从零实施计划与 Agent 工作约束

### 17.1 工程目录

```text
learning-workbench/
├── AGENTS.md
├── apps/web/src/
│   ├── workbench/              # shell, tabs, layout, commands, context bridge
│   ├── features/              # routes, reader, practice, assessment, tutor...
│   ├── api/                   # generated client + adapters
│   └── shared/                # passive UI components, markdown/math
├── services/api/app/
│   ├── domain/                # entities, value objects, state machines
│   ├── application/           # commands/queries/ports/policies
│   ├── infrastructure/        # db, blobs, parsers, providers, codex
│   └── interfaces/http/       # routers, schemas, auth, errors
├── services/worker/
├── packages/contracts/
├── migrations/
├── tests/{unit,contract,integration,e2e,security,provider}/
├── fixtures/                  # synthetic and licence-safe fixtures only
├── docs/{adr,requirements,reports}/
├── scripts/
├── .env.example
└── Makefile
```

锁定依赖、数据库迁移、测试 fixture 和代码版本。生成的 API client 不手改。禁止把业务服务写进一个巨大的 React 组件，禁止模块跨表写入。

### 17.2 里程碑和完成定义

| 里程碑 | 交付范围 | 依赖 | 完成门槛 |
|---|---|---|---|
| M0 工程与契约 | 空项目、工具链、CI、统一错误、Schema/类型、需求追踪 | 无 | 可安装/启动，锁文件和基线测试通过 |
| M1 三栏工作台 | 四入口、标签、布局、ContextBridge、空态和辅助工具 | M0 | 桌面/窄屏/键盘；不得依赖假成绩 |
| M2 内容与持久化 | DB/blob、导入预览、章节/块/LaTeX、笔记、精确版本 | M0–M1 | 实际文件导入与刷新恢复、坏文件不污染 |
| M3 习题与测试 | 公开/私有模型、自动保存、评分、暴露、服务端测试策略 | M2 | 直接 API/多标签泄题测试与评分基准通过 |
| M4 学习证据 | 进度、路线完成、画像、推荐和补弱深链接 | M3 | 无证据/辅助/重复/过期记录不误记 |
| M5 真实 Agent | ProviderPort、权限、RAG、联网、SSE、费用和失败恢复 | M2–M4 | mock 与真实调用分开；无授权零外发 |
| M6 创作闭环 | 教材/题目生成、审核、发布、影响分析、CodexBroker | M3/M5 | 草稿不越权发布，拒绝审批不执行工具 |
| M7 个人版验收 | 备份/恢复、故障、可访问性、内容审校、真实用户试用 | M0–M6 | 全部 P0 软件功能有证据；真实学习效果另列 NOT_RUN/PASS/FAIL，不将未安排的研究试验伪作软件失败 |
| E1 扩展 | Zotero/博客同步、QTI/LTI、后续多人部署评估 | M7 | 每个连接器独立授权和回归测试 |

M4 可形成一个不依赖付费模型的内部 MVP；但它没有完成真实问答和 Codex 主需求，不得称完整平台。M7 才是首个完整个人版目标，且仍不包含公共多租户或保密考试。

### 17.3 每个任务的输出模板

每个开发任务必须写：需求 ID；修改模块/文件；新增/更新契约；实现说明；测试命令和实际输出；数据迁移影响；安全影响；截图/日志位置；未运行项；下一任务的准确依赖。任务完成依据是可回读证据，而不是开发 Agent 的口头承诺。

开发可使用模拟提供商验证流程，但模拟身份必须可见。没有 API 凭据时只将真实提供商验收标 NOT_RUN，不伪造响应，也不为了绕过测试而自动使用外部服务。

### 17.4 从零开始的第一条任务

先完成 M0，并交付可打开的 M1 空壳作为验证：默认学习路线；四入口固定顺序；中央空态；右侧 Agent 说明未配置；两个侧栏可折叠；有类型化 ViewContext 和单元测试。不得在第一步引入多 Agent、远程数据库、复杂知识图谱或几十种未使用连接器。

之后按里程碑继续实现真实业务。用户已经明确授权构建平台，不需要每改一个组件都重新询问；但外部付费调用、权限提升、破坏性数据迁移和公网部署仍需单独授权。对本文指定的新公开仓库，建仓与白名单内容发布已获本任务授权，按第 18 章执行；不得据此公开本机其他项目或私有材料。



## 18. 公开 GitHub 仓库与进度治理

### 18.1 单一规范，多个事实记录

**唯一需求来源始终是根目录 `PRODUCT_DESIGN.md`。** README 只是入口和启动说明；AGENTS.md（若生成）只写“读取 PRODUCT_DESIGN.md 并按其流程执行”，不放新需求。进度记录是工程事实，不是第二份设计。未来修改需求时在本文同一 PR 中改动并提高文档版本，禁止在 Issue 评论中悄悄改变产品行为。

目标仓库：owner=`kl3574`，name=`Learning_Workbench`，visibility=`public`，默认分支=`main`，启用 Issues，wiki 不需要。新仓库与其他已有项目隔离。存在同名仓库时先核对 owner、description、根目录文档和项目身份；不是本项目时不要覆盖、改为公开或自动另造近似仓库，应报告名称冲突等待用户明确选择。GitHub 返回 404 也可能意味着权限不足，不能单凭 404 覆盖或断言绝对不存在。

建仓前用本机已授权 GitHub CLI 检查登录身份；不读取或打印 token，不搜索其他目录的凭据。身份不是 kl3574 或未登录时报告 `BLOCKED_GITHUB_AUTH`，继续本地可执行工作。需要登录时由用户通过官方登录流程完成，不要求把 token 发到聊天。GitHub CLI 官方支持 `gh repo create --public --source --push`；实际以返回值与远端回读为准。[S22]

初始发布只含本文、导航 README、忽略规则和已核对的初始进度；不得把旧 Demo 复制进来然后报正式版已实现。初始不自动选择 MIT/Apache/CC 许可证：公开仓库与授予开源/内容再许可不是同一决策。README 明确“许可证待所有者选择”，随后作为非功能治理项记录；第三方代码/字体/图片按各自许可，不能把本机字体或受版权保护教材上传。

### 18.2 可公开的仓库结构

```text
Learning_Workbench/
├── PRODUCT_DESIGN.md       # 唯一规范，必须保留本文件完整附录
├── README.md               # 入口、当前阶段摘要、启动与运行边界；不另写需求
├── .gitignore
├── .env.example            # 占位符，不能含真实 key
├── apps/ services/ packages/ migrations/ scripts/ tests/ fixtures/
├── progress/
│   ├── state.json          # 机器可读工程进度，生成 Markdown 摘要的源
│   ├── CURRENT.md          # 从 state.json 生成，当前状态、阻塞、下一条任务
│   └── evidence/           # 脱敏后的命令、返回码、测试/截图摘要
├── docs/
│   ├── adr/               # 技术决定，不得与唯一规范冲突
│   └── ui/                # 公开参考来源、仅合成内容的运行截图
└── .github/
    ├── ISSUE_TEMPLATE/    # bug、feature、milestone-task、research-evaluation
    ├── pull_request_template.md
    └── workflows/ci.yml
```

开发产生的 OpenAPI/Schema、DTO、测试都属于本文的派生实现；不能要求新用户先下载另一个“真正的规范包”。安装和继续开发不依赖历史聊天。

### 18.3 GitHub Milestones、Issues 与进度字段

使用 M0—M7 八个里程碑对应第 17 章；E1 扩展单独排队。每个里程碑创建一个总 Issue，下挂第 19 章的可执行任务。Issue 标题含稳定 task_id，例如 `[M1.1] 课程平台式三栏工作台与目录`，正文至少包含：spec_version、spec_sha256、需求 ID、目标、依赖任务、修改范围、验收清单、预期证据和未包含项。远端 Issue 数字是系统生成，不能预先假定 #1/#2。

建议 labels：`type:milestone`、`type:task`、`type:bug`、`priority:p0`、`priority:p1`、`status:ready`、`status:in-progress`、`status:blocked`、`status:review`、`status:done`、`area:ui`、`area:api`、`area:agent`、`area:security`。同一任务只保留一个 status label。创建时按 task_id 查找所有 open/closed Issues 防重复，不能每轮会话都新建整套。

GitHub Milestones 显示关联 Issues 的完成情况；该比例是任务闭合比例，不是产品功能真实完成度或投入工时比例。[S23] GitHub Projects 支持表格/看板/路线图，可作为可选可视化层；没有 Projects 权限时保留 Issues＋Milestones，不阻塞开发或虚报已建看板。[S24]

`progress/state.json` 必须包含以下字段；不存在的远端 ID、SHA、时间和测试结果用 null/NOT_RUN，不填说明性假值：

```json
{
  "schema_version": "1.0.0",
  "project": "Learning_Workbench",
  "spec_version": "3.0.0",
  "spec_sha256": null,
  "updated_at": null,
  "repository": {"expected": "kl3574/Learning_Workbench", "url": null, "visibility": null, "publication": "NOT_CREATED", "readback_at": null},
  "overall": "SPEC_READY",
  "implementation": "NOT_STARTED",
  "active_task_id": null,
  "next_task_id": "M0.1",
  "milestones": [],
  "tasks": [],
  "blockers": [],
  "next_action": "校验本文件，建立工程与依赖锁，生成接口和验收追踪基线",
  "verification": {"spec_checks": "NOT_RUN", "unit": "NOT_RUN", "contract": "NOT_RUN", "integration": "NOT_RUN", "browser_native": "NOT_RUN", "real_provider": "NOT_RUN", "real_codex": "NOT_RUN", "learning_effectiveness": "NOT_RUN"}
}
```

初始化时计算实际文件 SHA-256、实际 UTC 和全部任务列表，不把示例中的 null 机械保留。每个 task 对象：`{id,milestone_id,title,requirement_ids,depends_on,status,issue_number,branch,implementation_commit,verification,evidence_paths,blockers,next_action}`。status 仅取 `todo|ready|in_progress|blocked|review|done`。把依赖全部为 done 的任务标 ready，其他仍为 todo。任务选择：安全/数据丢失阻断优先，其次最早里程碑中可执行的 P0；同时 active 的主要实施任务最多一个。并行子任务必须明确文件边界。

进度每轮会话开始读取，结束和关键状态转换后更新。`implementation_commit` 指已验证的代码提交，不试图把“当前进度文件提交自身的 SHA”写回自身造成无限循环。报告检验的是哪一代码 SHA、哪一 spec SHA 和哪一组命令。

### 18.4 分支、提交、PR 和完成门槛

初始规范提交可写 main。实现任务使用 `feat/<task-id>-<slug>` 或 `fix/<task-id>-<slug>` 分支；小粒度提交包含 task_id；PR 关联 Issue 并列出测试回执、截图、迁移和剩余限制。不得 force-push、不删远端历史、不绕过失败检查；有未提交的用户更改先保留并做不冲突修改。

每完成一个可验证阶段，更新进度、推送分支并开 PR。默认不自动合并实施 PR；用户/指定审查者批准且必需检查通过后合并，Issue 才进入 done/关闭。下一阶段确需此前代码时可以继续在已验证本地基线上开发并清楚注明依赖 PR，不能把未合并状态写成 main 已有。有限权限下保存本地状态和待同步操作队列，不丢失工作；恢复后幂等同步。

`done` 必须同时满足：需求实现、对应机器契约覆盖、测试证据可回读、已知安全阻断修复、真实调用边界正确、审查/合并状态符合流程。写完文档、创建接口桩、测试使用 mock 通过都不能单独关闭真实集成任务。无需真实模型的 M0/M1 等不会因为没有 API key 而错误标为失败；M5.4/M6.3 的真实验收应单独 blocked/NOT_RUN。

CI 建议 job：`spec-contracts`、`backend`、`frontend`、`integration`、`browser`、`security-publication`。只在实际实现对应测试后报告其结果；初始文件扫描 workflow 不能叫“全平台验收”。真实付费 Provider/Codex 不在公开 PR CI 自动运行，避免 fork 提取凭据。发布前检查 git 已暂存文件及 diff，不使用无审查的 `git add .`。如果 CI 未运行，显示 NOT_RUN 而不是绿色手写徽章。

### 18.5 公开与私有边界

允许公开：本设计文档、原创源代码、合成/有授权的样例、锁文件、无秘密配置示例、脱敏测试报告与合成课程截图。默认忽略：`.env*`（除 `.env.example`）、`.local_data/`、数据库/WAL、导入原件、个人笔记、对话、备份、token、密钥、任何真实学习者记录和未取得许可的教材/PDF。

敏感扫描不能仅靠文件后缀：检查暂存 diff 中的 key/token 模式、绝对个人路径、个人正文、授权范围和 fixture 来源。发现疑似秘密立即停止发布，不自动删除日志后假装无事发生。不得为上传而启用 GitHub Pages、公网端口或 Actions 中的额外外发。公开源码不等于公开本机学习服务。

## 19. 从单文档启动的执行规程与任务分解

### 19.1 第一轮与后续轮次

第一轮：完整读取本文并记录 spec hash → 检查工作目录/已有用户文件 → 从附录抽取核心模型、DDL、样例和目标用例 → 运行规范自检 → 按第 18 章建立公开仓库和初始进度 → M0 → M1 → 后续里程碑。GitHub 授权阻塞只阻塞远端动作，本地规范/工程/测试继续。

若只有本文件，创建同级 `Learning_Workbench/` 并将它原样复制到根目录；若当前已是该项目工作树，直接续做，不重复嵌套。Codex 执行时依赖文件实际内容和验收标准，而不是聊天记忆；官方提示指南支持明确任务上下文与验证要求，本文将这些要求固化为版本化规范。[S25]

只在权限、付费、不可逆数据变更、核心产品语义冲突时确认。普通实现细节通过短 ADR 选择保守方案并继续。不创建另一套需求文档；详细任务计划属于可更新实施记录。单次执行资源不足时保存准确检查点，下一次从 next_task_id 开始，不宣称未来后台仍在运行。

### 19.2 可执行任务表

| 阶段 | 实施任务 | 必须交付的证据 |
|---|---|---|
| M0.1 | 空工程、依赖锁、启动脚本、lint/typecheck/test/CI | 新目录可安装启动，无真实 API key |
| M0.2 | 迁入目标模型，生成 schema/client，API 错误、CSRF/host/幂等接口 | 无效模型拒绝、编译、错误脱敏测试 |
| M0.3 | 需求追踪与 ADR，内容哈希规范、迁移机制 | 38 项追踪完整，旧数据 fixtures |
| M1.1 | 课程内页式三栏 Shell、紧凑四入口、上下文目录、状态条、标签 | 1440/1920/900/390px 运行截图、至少一次视觉修正与行为测试 |
| M1.2 | 可访问分隔条、折叠、焦点、快捷键、命令面板 | 鼠标和键盘均可调整；缩放无页面溢出 |
| M1.3 | ViewContext/ContextBridge、按对象保存草稿与会话 | 发送后切标签不串回复、草稿不丢 |
| M2.1 | SQLite/blob、精确版本、原子文件、对象读取 | 外键、回滚、文件失败、旧引用可读 |
| M2.2 | MD/TXT/HTML/learnpack 导入暂存和确认 | 恶意 HTML/zip、哈希错、取消不污染 |
| M2.3 | PDFtext/DOCX 提取隔离、低保真诊断 | 失败可见、原件保留、不伪造 TeX |
| M2.4 | Reader/LaTeX、例题锚点、笔记、阅读位置 | 实际浏览器刷新与重启回读；长公式滚动 |
| M3.1 | 题面/私有答案库、练习/提示/暴露记录 | 公开 API/包/检索中无私有解答 |
| M3.2 | 独立/辅助/开卷 policy snapshot，自动保存、并发版本 | 多标签直调 API 不能绕过独立测试限制 |
| M3.3 | 单选、文本填空、数值/计算容差、人工复核 | 正反评分样例、空答、单位、非有限数、重复交卷 |
| M3.4 | 交卷/评分/复盘闭环，评分版本与 evidence | 评分更新不覆盖旧成绩，未审推导不标正确 |
| M4.1 | 学习事件、概念/技能证据、路线完成 | 自报/阅读/辅助/独立/重复证据分离 |
| M4.2 | 先修/补弱/复习/下一步推荐，接受/拒绝 | 每条推荐有引用，空数据不伪造画像 |
| M5.1 | ProviderPort/能力协商/服务端冻结授权/受控预算/秘密与脱敏 | 本地控制面、真实持久授权与受控 HTTP 协议分层验收；无授权或无完整输入证明则零外发；不冒充生产模型贯通或 search |
| M5.2 | 显式范围/Content材料、中文FTS、来源和修订哈希、scope状态/CAS与持久重建 | 私解/Policy双层阻断、cold与资源诊断、旧scope/损坏hash、Jobs恢复、附录F.1冻结原创基准R@5及真实浏览器 |
| M5.3 | Tutor 状态机、真实 Thread/Run/Jobs、冻结上下文/授权、SSE/取消/重连 | 终态唯一、恢复不重外发、切标签不串内容；本地/受控适配器/真实费用验证分别记录 |
| M5.4 | 真实模型与搜索评测 | 显式授权小预算调用；引用回查；无凭据 NOT_RUN |
| M6.1 | 教材/例题/题目生成 schema + 数值验证 | 教学约束保留，缺来源不伪造，结果只入草稿 |
| M6.2 | 审校/发布/版本对比/影响分析/恢复旧内容 | 旧笔记标 stale，旧题/成绩不覆盖 |
| M6.3 | CodexBroker/App Server、操作审批、产物清单 | 拒绝操作零执行，路径逃逸阻断，成果预览回导 |
| M7.1 | 全备份/学习者包/作者包/恢复预览和事务 | 故障中断可恢复、无密钥、全部哈希复核 |
| M7.2 | 安全/可访问性/性能/故障注入 | 按固定硬件数据记录，不编造 p95 |
| M7.3 | 独立内容审校、真实用户试用、交付说明 | 三层结论分开，全部 P0 有证据或明示未达成 |
| E1 | Zotero、博客增量、QTI/LTI、部署评估 | 单独权限、预览确认、独立协议兼容测试 |


任务补充：M0.3 同时实现公开 GitHub 初始化与 progress/state.json 追踪；M1.3 包含实际会话保存 API；M2.4 包含学材目录检索与笔记删除；M4.1 包含自报知识与学习目标；M4.2 覆盖跨已导入教材的候选排序；M6.2 包含明确的人类审核决定接口；M7.1 包含归档、彻底删除影响预览与引用保留策略。

### 19.3 最小任务回执

每次记录 `task_id / requirement_ids / spec_sha256 / implementation_commit / changed_paths / commands / exit_codes / test_summary / screenshot_paths / migrations / security_review / not_run / blockers / next_task_id`。无需编造工期和完成百分比。优先提交真实执行证据，不把一段“应该通过”的描述代替命令输出。


## 20. 确定性业务规则、运维与交付约定

### 20.1 接口与模块补全规则

附录 B 的共享模型不是完整应用源码；附录 A 的所有路由都必须生成对应严格 DTO 和路由契约测试。正文、附录 A、B、C 的共同约束为需求，不要求在文档阶段重复展开数十万字可机械生成的 OpenAPI JSON。开发 Agent 可以生成代码，但不得自行定义冲突的业务语义、删接口或以 `unknown/any` 作为真实 DTO。附录 D 的泛型 DTOMap 是接口连接约束，具体实现必须绑定附录 B 或由附录 A 生成的类型。

所有可执行生成块在附录使用 `BEGIN FILE` / `END FILE` 标识，允许机械抽取。抽取器必须只写规范相对路径，已有文件不同则失败，不覆盖用户更改。工程内派生文件顶部标记源文件版本/哈希；自检应从磁盘重读本文件而不是验证缓存副本。

`ContentRef.sha256` 对应元数据规范 JSON 的字节哈希；正文另有 body_sha256。规范 JSON 定义：UTF-8、键按 Unicode 码点排序、紧凑分隔、禁止非有限数；整型与浮点的区别按发布对象固定字段类型稳定化。内容生成器和后端采用同一个规范化实现，不能混用 Python/JavaScript 浮点字符串并假定哈希一定一致。外部 JSON 对象先经模型验证转换到规范对象再计算引用哈希；清单文件哈希始终校验原始字节。正文 UTF-8/LF 不在读取时悄悄规范化，否则要成为新 revision。

引用关系必须是可生成的有向无环“内容元数据依赖图”。为避免互含哈希形成循环，**Lesson 不嵌入 PracticeSet 引用**；PracticeSet 单向引用所属 Lesson，中央通过反向查询显示本章习题。Course 仅引用 lessons/concepts；路线独立引用目标；笔记/证据/测试引用内容，不被原教材反向引用。概念先修图另外检查 DAG；路线路径可以跨课程，但 requires_steps 图必须无环。

对象 current_revision 指针只指向已发布修订；第一次建对象先 current=null，写不可变修订后原子设置指针。draft 的审批绑定 `{draft_id,draft_revision,candidate_entity,candidate_sha256}`，不是用未存在的发布 ContentRef 冒充审核目标。发布候选修订和引用在一次事务中校验，审批签名/决定与内容 hash 不匹配即失败。

### 20.2 测试策略矩阵与答案生命周期

| 模式 | 教材/笔记 | 学科 Agent | 联网 | 标准答案 | 证据标签 |
|---|---|---|---|---|---|
| independent | 进行中通过应用接口阻断 | 仅固定操作帮助，不调用模型 | 禁止 | 交卷且完成必要评分后释放 | 可满足独立条件，仍需检查之前暴露 |
| open_book | 允许已授权教材/笔记 | 仅操作帮助 | 禁止 | 交卷后 | open_book，不视为闭卷独立 |
| assisted | 允许 | 可调用已授权学科模型 | 经授权可用 | 交卷前不自动释放标准答案 | assisted |
| practice | 允许 | 提示或完整解释按请求 | 经授权可用 | 用户主动请求即记录暴露后释放 | practice，记录帮助等级 |

M5.3 练习中的真实模型帮助由 Practice 所有者单独记录：仅在本次 Run 首个实际持久化且含非空白文字的 answer_delta 与 Tutor 写入的同一事务中，建立幂等的 model 来源帮助事实、可信 hint_revealed 学习事件及通用 hint exposure；仅排队、授权、空白或拒答不算已获帮助。记录表示回答已在服务器持久化可供读取，不冒称浏览器已展示或内容已核验。取消或不完整输出不抹除已经发生的帮助。它不是 rules 提示级别、不是标准答案释放，不写原 practice_exposures 的 level，不推进作答 revision、不改变本 Run 已冻结输入。恢复时若 Provider 原终态已保存而 Tutor 尚无 delta，在恢复该原回答的同一事务建立同一事实，不重新外发。GET 与原 SSE 回放只读，不补写学习事件。

本地学习者/作者是操作角色，不是安全上不同自然人。进入 independent 前，服务端以 workspace 级 guard 排他锁检查是否有活跃学科 Tutor/Authoring/Codex/导出任务：存在则返回 409，要求等待或显式取消；之后每次外发、流事件读取、下载和解答读取再次检查 guard，避免“先启动流，再开始测试”的竞态泄露。活动独立测试最多一个，不能在另一个标签用作者角色、旧对话、笔记、索引或下载链接绕过。应用之外的本机文件/其他工具无法由本产品封锁，文档与 UI 不宣传监考。

M5.3 学科准备、授权预览/批准、派发及 Thread/Run/SSE 正文读取使用明确学科操作权限：活动 independent 或 open_book 均拒绝，open_book 普通材料仍按原规则可读；固定操作帮助不调用模型。assisted 仅允许本工作区真实 question/attempt 绑定和当前已释放材料，不能据此放宽通用 private_artifact。Provider 源专属结果回读同时核实际 Tutor source、job、dispatch/receipt 和当前输出许可，不接受任意 artifact 旁路。既有 independent 启动排他不变；任务中策略变化在下一准备/外发/输出边界再核，不声称已撤回此前内容。

纯取消/撤销授权及不含正文的任务控制回读按工作区归属允许，不能被学科读取锁卡死；其返回不含 thread scope、问题、回答、引用、上下文摘要或原错误全文。GET 不执行取消/写 failed；worker 负责停止与唯一终态。客户端策略未知停止新学科读取/显示，跨 workspace/session/上下文变化废弃旧异步结果。

评分固定私有 solution_revision，不从“最新答案”临时读取。提交与最后草稿快照、submitted_at、评分 outbox 同一事务；关闭页面不隐式提交。timed attempt 由服务端 deadline job 提交最后已保存草稿，UI 清楚显示截止时间和剩余值；时间到的网络迟到写入拒绝并保留客户端待恢复副本。重复提交同键同载荷返回原回执，不触发第二计分；同键不同载荷409。

知识证据只使用已解决的评分项；GradeItem score≤max_score，未知项 score=null，不能以0替代。人工评分通过签名人类审阅记录，学习者不能通过普通 actions API 写 grade_finalized。历史解答暴露按 exposure_group 跨题目修订追踪，参数相似题只换随机数字不得默认成为“全新迁移题”。

### 20.3 内容导入、阅读和生成的质量等级

内容可作为“参考材料”进入库，不意味着内容被认证。导入时用户确认的是解析预览，不自动获得数学 APPROVED。Reader 显示 source/user_supplied/review 等状态。正式 AI 生成教材发布需要结构检查及所有适用的数学/来源审批；不含数学的内容可标 NOT_APPLICABLE，并写原因；不允许用 NOT_APPLICABLE 绕过包含定理/公式的审核。独立教学评测可以 NOT_RUN，不阻止软件交付，但阻止宣称“教学效果已验证”。

“所有定理证明完整”的作者约束属于题材范围内的内容要求：声明先修、变量域/维度、假设、定理/证明/例题/练习关联，完整证明策略不被模型降级。需要外部定理时把证明加入或由用户显式改 proof_policy，不能隐式以“工具定理”跳过。例题真正执行数值验证；代码默认仅文本，只有用户批准的隔离数值校验才运行。

导入的 HTML、PDF、DOCX 不等于完整教材主稿。解析低保真时保留原件与片段级警告，原件预览也受本机策略保护。文本 PDF 不自动恢复数学 TeX，扫描件默认无 OCR；用户可另行授权 OCR，但结果仍需确认。中文编码优先 UTF-8，遇到无效字节返回编码选择预览，不静默替换乱码。

### 20.4 安装与运行入口

目标开发机为 Linux/Ubuntu 桌面，Python 3.12、Node 24 起始系列；Mac/Windows 暂非必需验收平台但不硬编码个人绝对路径。M0 核对维护状态、依赖 engine 和工具许可，写入 lockfiles。默认数据在工作区外的用户数据目录，可通过 `LEARNING_DATA_DIR` 显式配置，不能写进项目根目录后提交。

必须实现以下稳定命令：`make setup`（锁定依赖安装）、`make dev`（前后端本机开发）、`make build`、`make start`（单同源生产服务）、`make lint`、`make typecheck`、`make test`、`make test-e2e`、`make verify-spec`、`make backup`。README 从实际命令生成运行说明，不列不存在脚本。测试不依赖真实 API key，真实提供商另用显式 opt-in 命令。

生产端由 FastAPI 同源托管编译后静态页面及 `/api/v1`；开发端 Vite 通过代理访问，不开放任意 Origin。固定健康检查 `/health` 不返回敏感数据；`/api/v1/readiness` 返回 schema_version、迁移状态、worker状态、提供商是否配置（不验证密钥）。迁移前在线备份，worker和API启动前检查 schema兼容；不自动破坏性降级。SQLite WAL 模式备份用 online backup API 或等价一致性快照，不直接复制活跃 .db 忽略 WAL。

首次本机访问使用 launcher 生成的一次性随机 bootstrap code，经浏览器 fragment 交给同源 POST `/api/v1/session/bootstrap`，成功后建立 HttpOnly、SameSite=Strict 会话 cookie，并清除 fragment。code 不在访问日志、URL query或公库中，过期/重复使用拒绝。Host/Origin 限制与 CSRF 同时生效；默认不让远程网页访问 localhost 启动会话。所有配置和许可操作使用可信 SessionIdentity 的 workspace/actor/role，客户端不能自报权限。应用模块导入、factory 和 OpenAPI 生成不创建数据库、秘密文件、后台任务，不读取凭据或探测外网；仅显式运行生命周期初始化本机存储。

提供商配置、秘密和能力设置在现有辅助“设置”入口。learner/author 两种已认证本机会话均可管理本工作区的提供商控制配置；内容作者权限不因此扩散到学科读取/生成。配置/秘密控制、能力诊断与仅减权 revoke 不返回学科正文，独立测试时仍保留停止入口；proposal/consent 的学科摘要读取、批准、派发与流消费每次核当前 Policy。界面能打开设置不代表可以显示受保护授权摘要。设置读取、保存配置/秘密、能力查询和创建授权预览均不进行远端连接、鉴权或计数。

配置与秘密引用共用一个单调 revision；首次 config expected_revision=0 仅创建未占用的合法 ID，r1 起始，跨工作区记录不可读写。普通配置命令与秘密替换成功推进一次；秘密已无引用且匹配当前基准的删除不推进。config_sha256 对 `{version:"provider-config-v1",workspace_id,id,revision,adapter,base_url,model,embedding_model,endpoint_policy,pricing,secret_present}` 的项目规范 JSON 计算；不含秘密、秘密摘要或 locator。secret_present 表示该修订已提交的秘密引用存在性，不等于秘密介质当前可读取、密钥有效或提供商可调度；实体缺失/损坏时保持原历史，拒绝派发并报告安全诊断，GET 不写新版本或重算成另一配置。配置/秘密轮换改变 revision，从而使旧提案不能授权新请求。历史 ACK 保留当时值，UI 必须另 GET 当前配置。

key 只经专用 write-only 端点进入 Provider 的 SecretStore，优先系统安全存储，fallback 使用公开与备份目录之外的受限文件（目录 0700、文件 0600，防符号链接/路径逃逸，原子写入）。M5.1 不自动扫描或导入环境凭据；将来若接启动环境变量，须走同一秘密版本绑定与安全日志边界。GET、错误、日志、任务输入、config_json、content_blobs、HTTP 回执、浏览器 DraftStore/IDB/localStorage/WorkbenchSession 与公开证据永不包含秘密或其可公开比对的摘要，不能把可逆编码当作加密。locator 只在 Provider 私有存储，不返回浏览器或进入导出备份（仍含敏感个人数据，不得公开）。

秘密写先存不可变版本，再在事务内 CAS 切换引用与配置 revision 并保存安全 ACK；存储失败/DB 回滚不能声称已保存，孤立版本须可恢复清理。删除先使当前引用不可再调度，再清理秘密版本；不承诺介质级擦除或撤回已发生外发。幂等比较使用服务端专用秘密的 HMAC 指纹，指纹与指纹密钥不进 API、日志或导出备份（仍含敏感个人数据，不得公开）；不得将 raw secret 或普通 SHA 作为通用幂等 payload。六个写操作均校验同一完整命令实例：workspace、actor、route、原 key、全部字段及版本条件。相同 key 不同命令 409，同命令回原安全 ACK；secret 丢 ACK 后只凭 secret_present 不能确认“刚输入的 key 已保存”，原命令字节在内存仍有时可原 key 回放，刷新后不能从浏览器持久层恢复秘密。

Provider-owned 备份降权端口仅修改独立备份副本：排除所有秘密字节、HMAC 私密材料和物理 locator，使其中授权不可派发，并保持自有配置 SHA、不可变原历史与降权后的当前投影一致。不得只把 consents.status 改 revoked/locator 改空却留下不一致 hash 或绕过不可变历史。保留历史原事实，通过自有可校验的备份安全投影/降权记录表达不可调度；恢复时不能复活旧许可或把历史 secret_present 当成实际秘密。数据库在线迁移前备份是受限的本机恢复原件；导出备份（仍含敏感个人数据，不得公开）另外经过本端口净化，二者不能混称。此要求不提前实现 M7 完整恢复流程。

目的地策略 public_https 仅允许 HTTPS 公网；explicit_loopback 必须在该配置明确选择，仅允许 localhost/127.0.0.1/::1 的确切端口和 base path，可用 HTTP，不开放 LAN。拒绝 URL userinfo/query/fragment/未支持 scheme；本机 allowed_origins 不是提供商许可。保存时只做本地语法校验。出站在许可与预算准入后才解析并固定地址，检查实际连接 IP、TLS 主机、端口/路径，防 DNS 重绑定；不自动跟随重定向或继承环境代理，不把 3xx 改址后继续外发。每次实际 HTTP 尝试都受同一额度与取消约束。

### 20.5 上下文、搜索与资源预算

每个外发任务绑定 provider、模型、目的、具体精确引用与正文摘录、联网许可、token/调用次数/时间上限、到期时间；批准只覆盖服务端冻结输入，新增来源、模板、目的地、模型或范围需要新许可。Context/Policy 与真实 source owner 先从已持久任务读取和核验准备材料，形成无假 consent 的私有快照；用户批准服务端提案后才构造带实际 consent_id 的核心 GenerationInput。正文与准备材料不直接下发普通浏览器 API 或公开日志。Provider 持有许可/派发/用量与自有终态；source owner 持有 Job/Run/回答，外部事件不能自行建立本机 completed/approval。

**服务端准备 → 预览 → 批准 → 派发。** HTTP preview 只接已存在 job/provider 的 ID/预览基准版本、预算与到期时间。registered source owner 核真实 workspace、不可变 job input、ContextSnapshot、精确 refs/正文 hash、当前 Policy 和可批准阶段，再冻结真实 messages/evidence、转换版本和请求体；未知 source 返回 OUTBOUND_SOURCE_UNAVAILABLE，不能把 import/grading 冒充生成任务，也不新增任意 prompt 的测试产品入口。source_job_revision 是预览 CAS/审计事实，授权稳定身份是 job ID+原 input hash+准备材料/请求体/上下文 hash；正常 lease/status revision 推进不自动使同输入失效，当前 lease 仍必须单独验证。

input_sha256 使用 `{version:"prepared-outbound-v1",workspace_id,job_id,source_input_sha256,purpose,context_snapshot,messages,evidence,preparation_version}` 的规范 JSON，不含 consent_id。request_body_sha256 对适配器已冻结且实际发送的完整规范 JSON 请求字节计算，排除 Authorization 等秘密头；这些字节须原样发送，不能在检查后追加 instructions、工具/schema、历史或默认参数。proposal_sha256 对 `{version:"outbound-proposal-v1",workspace_id,id,summary}` 计算，summary 为附录 A 的完整不可变 FrozenOutboundSummary；动态 validity/warnings/consent_id 不进原 hash。摘要只给真实安全标题/定位、角色、长度与服务端 hash，不泄漏正文、秘密路径或原始工具日志。locator 不得伪装成包含全文的“定位”。全部冻结字节和 hash 需回读核验。

POST consents 只批准原 proposal ID+SHA。事务内核当前 Policy/归属、自有历史、到期、provider revision 和 source 仍一致且允许批准；每个 proposal 至多一份 consent，每个 consent 至多一个 dispatch 实例。不同 key 重复批准同提案 409 CONSENT_ALREADY_GRANTED；更换输入或撤销后再次授权必须新预览、再明确批准。grant 通过 source owner 的事务端口绑定真实 consent，不跨模块改 Tutor/Authoring 状态。原相同命令 ACK 回放先核本工作区/当前允许访问范围和自有历史，不因当前无关材料损坏、provider 已换或 consent 已撤销重新执行；只有新操作才核新业务前置。旧 active ACK 不是当前 active。

M5.1 仅实现一份许可内 `max_provider_calls=1`、`max_search_calls=0`、`max_tool_calls=0`、allow_web=false 的受限文本能力。一次调用失败、连接中断或重启不重置额度；派发开始许可一经持久保留即保守消耗，无法证明未开始也不能释放为第二次调用。远程计数不采用：计数请求本身外发完整内容，也需满足每请求输入硬上限，不能靠事后计数或第二份许可绕过外发前准入。search/codex 目的、工具/结构化输出及未知模型组合在本阶段无实现能力时明确 CAPABILITY_UNSUPPORTED，零传输；品牌与兼容接口名称不能证明能力。

**完整输入准入只允许 local_exact 或有证明的 local_upper_bound。** 两者均绑定固定 model、adapter/checker 版本、完整允许输入形状及实际 request_body_sha256。proof_sha256 对应本机不可变、可核验的依据记录及其证明材料：实际模型/版本、格式开销、适用输入范围、计数方法、上下文/输出能力和失效依据必须明确；不能只填一串 hash 宣称有证明。对 exact 取 U=input_tokens，对 upper_bound 取 U=input_tokens_upper_bound，要求实际完整输入 token≤U≤用户 max_input_tokens。上界不是实际计量；裸文本 tokenizer、固定安全余量、平均误差、字符换算或仅固定模型名都不足以证明完整格式开销。未知/失效/不匹配证明、未注册 model、超出输入形状或不能施加输出限制的组合拒绝可批准预览和派发，不能填 0 或先发再看。安全能力诊断可用 MODEL_NOT_REGISTERED、INPUT_BOUND_UNAVAILABLE、REQUEST_SHAPE_UNSUPPORTED、OUTPUT_LIMIT_UNSUPPORTED；HTTP 使用 CAPABILITY_UNSUPPORTED。官方完整计数范围见 [S26]。

生产证明还必须绑定受信目的地，不能仅按 `(adapter, model)` 匹配。使用与实际传输相同的本地 URL 解析规则取得 `endpoint_policy、scheme、host、effective_port、base_path`，并与该 adapter/请求格式版本生成的最终请求路径一起精确核验；默认端口、主机大小写与尾斜杠只能按同一既定规范化处理，不进行 DNS/联网探测。另一 host、端口、路径或 endpoint_policy 不得继承同名模型证明，禁止通配 host/后缀域名/任意端口或代理转发推定；多个已核目的地须逐项明确登记。§20.4 的 DNS 固定、实际连接 IP/TLS/Host/路径检查和禁止自动重定向继续独立执行，URL 安全可连接不等于已证明模型能力。

证明的可信本机不可变依据必须明确实际模型版本；使用 API 别名时，须有依据列出该目的地下被覆盖的实际版本范围及别名变化的失效条件，不能用某次返回名、usage 或本地配置中的字符串代替。请求格式/profile、tokenizer或完整计数方法、checker、容量规则、目的地绑定和失效依据全部进入 proof_sha256；不是只把这些条件写成未执行的说明。能力、预览、批准与派发重核当前配置和当前有效证明；目的地/模型映射/格式/证明版本不符，已确认供应商改变，或超过依据明确的有效期限时，按现有 CAPABILITY_UNSUPPORTED 拒绝新准入。未能覆盖别名可能对应的实际格式时本就不得登记，任意自行设置的短有效期不能替代证明。失效不得修改原 proof/提案/许可/终态字节；原 ACK 和已持久结果按原身份、完整历史及当前读取权限回放，不把证明失效当成重新外发或抹去已发生事实的理由。

同时按固定模型的真实容量规则验证输入/输出限制；若共享上下文容量为 C，须验证 U+max_output_tokens≤C，不能假定所有模型的容量定义相同。输出硬上限落实到已验证协议参数：Responses 为 max_output_tokens，支持该参数的 Chat 为 max_completion_tokens；字段不支持则拒绝，不能移除限制重试。truncation 不得自动删减已冻结输入。字符预算仍执行 §12.2 的 12,000 字符、8 块、6 条最近对话、5 个外部来源，保留完整块边界；字符上限不能替代 token 证明。[S27][S28]

M5.4 首个生产文本-only Responses profile 明确关闭 thinking：服务端构造的实际完整请求必须包含 `reasoning: {effort: "none"}`，与 model、input、stream、max_output_tokens、truncation、store 一起在本地检查前冻结并纳入 request_body_sha256 和证明适用形状。不得依赖供应商默认值、在检查后补字段，或把未识别的 reasoning 当作 answer。该模型/目的地必须有此设置及输出硬限的支持依据；若设置不支持或可能被忽略而无法证明实际行为，则该窄 profile 不准入。请求格式变化推进 adapter/profile 版本，旧证明和旧冻结请求不能静默套用新形状，必须重新准备、预览和明确批准；正常原回执读取仍保留。此条不授予 Chat max_tokens 别名、工具、图像、思考链展示或搜索能力，也不宣称已取得任何生产模型证明。

价格由配置提供并冻结 pricing_sha256（`{version:"provider-pricing-v1",provider_id,provider_revision,pricing}` 的规范 JSON）。pricing=null 为 unknown/price_unknown，绝不写 0；已知时以 U 与最大输出计算 maximum_estimated_cost，仅表示该本机价格下估计，显示 estimate_not_guaranteed，上界不能显示成实际输入费用。设置 max_cost_usd 且已知估计超额时拒绝；未知价格明确金额无硬保证，仍执行 token/次数/时间硬约束。终态 input/output usage 来自提供商累计报告，缺失为 null，cached/reasoning 等组成项不重复累加。rate×tokens 只能 estimated；actual 只在提供商给出可核验实际费用事实时使用，不把估算称账单。真实 usage 超过冻结输入证明 U、用户输入/输出上限或与已记用量矛盾时，记录 OUTBOUND_BUDGET_EXCEEDED/PROVIDER_USAGE_INCONSISTENT 安全错误和原始已核计量，不回写旧证明或隐藏超限为预算成功；远端是否已完成另按事实保留。

工程初始超时：DB 查询 10 秒、文件解析 60 秒、模型任务 180 秒、Codex turn 300 秒可按任务配置。模型 timeout_seconds 从实际 dispatch 开始按单调钟计算，总截止时间不能被每段网络 timeout 重置；排队不消耗运行时长。到期、revoke、取消可以更早停止。GET 只读派生 expired/validity，不写过期状态、排队或幂等行；revoke 保留实际时间和 r+1，已撤销且当前基准一致返回 MutationAck.applied=false，过期许可仍可显式撤销。revoked 优先于派生 expired。

派发事务内核 source 当前 lease/owner、不可变输入/实际请求体、provider/秘密版本、许可未撤销/未过期、Policy、取消和额度，持久记录唯一 dispatch-start 与额度保留；它是与 revoke/轮换竞争的本机线性化边界。撤销先成功则新请求不能启动；开始许可先成功则按在途处理，请求取消并明确可能已外发/计费。网络连接前与接收流时继续复核实时约束，但不能把 SQLite 提交与物理网络动作宣称为原子。不得在长期写事务内等远端；worker 停止、取消与其他队列必须仍可推进，不能靠无限阻塞掩盖恢复。

所有生产传输层关闭自动请求重试、自动工具递归与自动重定向；HTTP 建连、错误状态、流消费、worker 恢复各层均受约束。dispatch-start 后崩溃/超时/未知结果保留原实例、已消耗额度及 PROVIDER_OUTCOME_UNKNOWN，禁止自动重生成；只能回读已知持久结果或结束本机任务。客户端幂等键不等于远端去重，取消/关闭流不证明服务商未执行或退费。只有可证明尚未获得开始许可的本地准备才能重试；不能拿 import 的过期租约恢复规则重放模型。[S31]

Provider 内部采用附录 D 的 delta/usage/finished/error 四类严格事件，保留 answer/refusal、complete/refused/incomplete、部分输出与未知计量。Responses text.done 不是请求结束；Chat choice finish_reason 后继续消费 usage 和 [DONE]；EOF 不是成功。远端终态及当前实际收到的计量一致性核验后，自有终态回执与私有部分产物原子登记，方可投影粗粒度核心事件。core ProviderEvent 保持不变：仅内部 complete 可投影 finished，refused/incomplete 以 PROVIDER_REFUSAL/PROVIDER_INCOMPLETE 错误投影，完整事实仍保存在自有回执；不把 JSON 偷塞进 text/error_code。consumer 读取该回执并完成自己的结果校验/事务后才有本机 completed。Run SSE 与 Tutor 状态机在 M5.3 实现。[S29][S30]

活跃真实 source job 在 queued/running/awaiting_approval 均参加 workspace 独立测试排他；Provider 子步骤不豁免。M5.1 可独立实现并逐项验收本机配置/秘密/严格授权历史、无授权或无证明零传输、测试专属真实 SQLite source 和有明确计量规则的受控 HTTP 流协议。测试 source/model/proof/服务不得进入生产注册表，人工计量规则不能证明真实供应商隐藏开销。无生产 source 时设置显示没有可授权任务；无模型证明时 chat/streaming 显示不可调度。现 core AuthoringRequest 的 consent_id 必填，仍不作为首次未授权 job 的创建输入，不使用假 consent 或其他任务许可。M6.1 首个例题的授权前路径由 §20.8 与附录 A/D 的独立应用 DTO 定义；M5.1 本身不据此追认 Authoring 已贯通，后续注册真实 source 也不豁免完整输入证明。配置存在、受控协议 PASS 或本地预算 PASS 不能合并为生产生成贯通、模型质量、真实搜索或整个 M5 完成；真实 Provider/Codex 费用测试仍须另外显式授权，未执行为 NOT_RUN，真实模型评测在 M5.4。

推荐与联网事实分开：本地材料可精确引用；搜索候选未抓取或未核查时标 unverified；模型推导无来源可以清晰标“推导尝试”，不能配伪造外部引用。后续已实现搜索默认最多 3 次/请求、5 个来源、抓取 10 MiB/页面、5 次重定向，并逐步重新核权限与预算；这些上限不授予 M5.1 搜索能力。M5.2 来源/current descriptor变化按§20.7使代际待复核；无当前匹配代际时只返回明确状态与空hits，不用旧正文冒充新目标。显式旧scope可重新构建并返回原旧ref的真实正文，不静默迁移到最新版。

### 20.6 删除、隐私和恢复

软归档保留可追溯版本；彻底删除是单独的 preview→confirm 工作流，显示课程、笔记、个人事件、备份和引用影响。用户有权删除个人数据；append-only、不可变触发器是常规写入保护，不是永久阻止数据删除。purge仅在维护事务/新工作区重建中执行，留不含原文的删除回执；误删恢复仅从用户保留的独立备份进行。完整备份 profile 与 learner/course包不同，包含必要对象、题解与个人数据，但不含密钥；导出前提示敏感性，不能直接推GitHub。

备份包含数据库一致性快照、blob清单与字节hash、schema_version、对象数量、UTC时间和不含secret的配置。恢复先校验内容与版本并预览，默认 abort冲突，显式选择恢复到新工作区。原工作区不被覆盖；中断后能识别未完成恢复并清理或继续。

### 20.7 精确范围的本地词法检索（M5.2）

**范围和未审事实。** M5.2 只检索用户显式选择的、本工作区可访问的已发布公开教材块。scope_refs 非空且仅接受 course、lesson、block 的完整 ContentRef：block 仅自身；lesson 仅该精确修订的 block_refs；course 仅该精确修订的 lesson_refs 再展开各自 block_refs。每条边核 entity/id/revision/sha256，展开按完整 ref 去重；不能通过同名、concept、depends_on、当前指针、模型建议或相似度补进其他材料。明确选中课程/小节表示允许本次搜索其固定子引用集合，不表示 UI 可以把“当前块”静默换成整门课程。

显式范围可包含未审核的公开教材，每个命中 material_review=unreviewed，带 MATERIAL_UNREVIEWED 提示“来自所选未审材料，不代表内容已核验”。导入确认、发布、可读正文、来源关联 hash 和高检索分数都不授予专家审核通过。§12.2 的“已批准的本教材相关块”是自动补足的独立门槛；目前没有可核验的教材批准 owner，因此 M5.2 不实现自动补足范围，不借用题解审校状态，不把先修/兄弟块改称显式选择。没有获准额外证据时明确没有补充材料。后续开放自动补足须由 Content owner 提供绑定精确 ref/body hash 的真实批准事实，并同步本文。

R-25 在建索引/检索与 Context 组装分别执行。SolutionPrivate、私有提示/评分规则、私有答案 pin、作答/成绩 trace、作者私有导入原件、Provider 准备或产物均不进入普通语料，author 会话也不豁免。公开 worked_example、proof 等块可以有推导和结果，不按“答案/解答”字样删正文。所有资料内命令都是文本，不能改变权限、读取文件或触发工具。先由 Content owner 在当前 Policy 下确定完整允许范围，再在该范围内匹配和排序；禁止全库 topK 后过滤。索引命中不代替真实正文核验，后续 Context 仍重新核当前 Policy/refs/material。

**三条路由和冷启动。** 保留 POST /retrieval/query、POST /index/rebuild、GET /index/status 三条路由；没有新增 scope 签发端点。GET status 的单个 scope_refs 查询参数是 URL 编码的严格 JSON ContentRef 数组，存在时只允许这个参数；缺少它时只允许 overview 的 cursor/limit。空字符串、[]、重复同名参数、重复 JSON 键、未知参数、混用两种模式均拒绝。有 scope 时只读核当前目标描述并返回 kind=scope，即使没有任何索引/任务也返回真实 corpus_sha256、missing、null index_version/indexed_corpus_sha256/last_built_at。未注册 scope 的 GET/query 不创建登记、Job、outbox 或索引。

无 scope 的 GET 返回 kind=overview 和分页的已登记 scope 摘要；登记只能来自真实已受理的 rebuild 命令。只读枚举这些持久记录和自己的最近代际/Job，不展开任意全工作区语料或读取全库正文。overview 没有全局 ready/stale、没有可用于任意 scope 的目标 corpus SHA；每条冻结代际的 hash 只是该条自己的事实。cursor 由服务器签发、绑定工作区/limit/分页顺序，默认 limit20、范围1..100；以 scope_sha256 升序作稳定 keyset，cursor 无效或过期明确拒绝，重启可要求重取第一页。概况仍属于学科读取，受当前 workspace Policy 限制，不采用提供商设置控制面的豁免。

**三个 hash 域。** 规范化 roots 先拒绝相同 entity/id/revision 的不同 SHA，再按完整 ref 去重、按 entity/id/revision/sha256 排序。scope_sha256=SHA256(本文规范 JSON `{version:"retrieval-scope-v1",workspace_id,scope_refs}`)。corpus_sha256 对附录 D 的完整 RetrievalCorpusDescriptor 计算，代表这个 scope 的当前元数据目标：固定图和 body 登记 hash/size、每个图节点的真实 current_ref/lifecycle、Content 返回的来源 descriptor、显式范围父链和固定词法版本均参与。不含观察时间、Job 状态、秘密或绝对路径。indexed_corpus_sha256 仅指已提交代际自己的冻结 descriptor hash。三者不得互用。

status 为轻量只读元数据目标核验，不宣称已读取每个物理正文文件。ContentRef.sha256 是元数据 hash；body_sha256 是原正文 UTF-8 字节 hash；RetainedSource.sha256 是导入原容器 hash；Citation.source_sha256 可指另一外部被引来源且可为 null，四者不能混同。实际构建和命中返回前必须经 Content owner 读取登记的 public body bytes、核 size/hash 和 UTF-8/LF；文件缺失/改写/逃逸不能因 descriptor SHA 相同而通过。坏元数据、来源快照、索引清单或 chunk hash 是完整性错误，不伪装成 stale/no_match。

ProvenanceSource 关联仅从绑定完整 block ref 的冻结记录取得；不能全局按 citation ID 取第一个来源。有快照叫 frozen，仍保留 Citation.verification 的真实 verified/unverified/user_supplied 值及原 warnings，不升级外部核验或数学审校；没有快照叫 unresolved，original=null、citations=[]、保留 unresolved_citation_ids 和 PROVENANCE_UNRESOLVED，即使原 citation 列表为空也不假称 frozen。读取只用安全来源描述，不读取/下载原件，不返回物理路径；来源 locator 是不可信声明而非文件读取指令。来源 descriptor hash 对完整 RetrievalProvenance 规范 JSON 计算；它不包含会话相关的原件下载权限，不证明原件现在仍可物理读取。

**旧范围与状态。** 显式旧 refs 保持原精确正文；active/archived 对象的已发布旧修订均可在当前 Policy 允许时读取，hit 明示 current_ref 和 lifecycle。任何参与 scope 图的当前指针、生命周期或来源 descriptor 改变都使旧 corpus descriptor 不再匹配，先显示 stale/真实 building；不会自动把 roots 更新为 latest。用户可重建同一旧 scope，冻结新的当前描述而继续索引原旧正文，成功后正常 ready。归档不删旧版本，不把“需重新核验索引”误报成“原文已消失”。

状态优先级：存在完整可核验且匹配当前 corpus 的已提交代际为 ready（冗余重建 Job 仍单独显示）；否则存在为当前 corpus 真正登记且非终态的重建 Job 为 building；否则有旧已提交代际为 stale；否则 missing。building 不表示 worker 正在 CPU 执行，也不能由旧目标的 Job 冒充。失败/取消通过真实 Job 表达并保留旧代际；没有代际时 version/time 为 null。查询仅在 ready 时匹配当前代际，其他状态返回 hits=[]、matched_count=null 和 not_ready；旧代际 version 仍可作为诊断事实返回，但不返回它的正文冒充当前目标。显式历史 scope 重建后 ready 与这种 stale 不矛盾。

**工程预算 retrieval-resource-v1。** roots 输入1..16项（先计输入再去重），最多512个不同展开 block；这些 block 登记 body size 合计最多16 MiB。为避免重复父链绕过去重预算，读取的不同精确公开元数据及不同来源descriptor的规范 JSON 合计最多16 MiB、显式范围路径总数最多8192；元数据按完整ref、来源按descriptor SHA去重计数，路径按完整链身份计数，不靠循环访问制造重复。除上述独立预算外，完整 RetrievalCorpusDescriptor 的实际规范 JSON UTF-8 编码不得超过16 MiB；graph、来源、父链、每次重复出现的标题及全部字段均计入，不能按共享对象或去重后大小代替。范围展开和规范编码须累计计量并有界停止，不能先构造超大对象再事后计算，也不能截断descriptor或父链。超出任一 scope 预算整次拒绝 SCOPE_BUDGET_EXCEEDED（413），不静默漏子块/父链后宣称范围完整。查询原文为有效 Unicode、1..512码点，不能全空白；规范化后1..64个不同派生 term，零 term 为 QUERY_NO_TERMS（422），超过为 QUERY_TERM_BUDGET_EXCEEDED（422），不静默取前64个。字符串不得有孤立 surrogate，JSON 写命令未知字段拒绝。

query limit 必填整数1..20，最多返回 limit 个完整块。所有返回 text 的真实 UTF-8 字节合计≤2 MiB，整个实际 HTTP JSON 编码≤8 MiB（包括来源/父链/warnings，不以未转义字符数冒充字节数）。按已声明排名顺序选择完整块；某块会超过正文或 JSON 预算时整块遗漏并继续考虑后续块，不截断条件/结论、不截来源和父链。资源 omissions 按 result_limit/text_byte_budget/json_byte_budget 分别计数，合计=matched_count−len(hits)；最终实际编码若仍超8 MiB，从已选末位整块撤下并计 json_byte_budget，直至符合。超过 limit 的剩余匹配以 result_limit 计；在到达 limit 前实际因资源跳过的块计对应资源原因，text 预算优先于 JSON 预算。完整响应预算不能导致一个明显过大的诊断本身被无声丢弃。

每条 text 是真实完整 body 解码结果；whole-block-v1 码点定位固定 start_cp=0、end_cp=len(text)，locator 精确为 `block:{id}@r{revision};body:{body_sha256};cp:0-{end_cp}`，不拼私有路径，不含全文。ready 且索引中没有任何词法 term 时 result_state=indexed_empty；索引有 term 但匹配数0为 no_match；有匹配且返回至少一块为 matched；有匹配但全因预算遗漏为 resource_omitted。这些情况与 not_ready 分开。§12.2 的8块/12,000字符和对话/外部来源预算只用于 M5.3 Context 消费端；不挪作 M5.2 query 限制。Context 若不能容纳完整块，应另报材料未纳入，不改变这里的正文或定位。

**固定词法算法 lexical-han-gram-v1。** 原正文/hash/定位不做规范化；仅派生 term 使用 Unicode 15.0.0 NFC，字符分类和 casefold 版本固定为 Unicode 15.0.0，不匹配的运行时拒绝构建并报 TOKENIZER_VERSION_UNAVAILABLE。按下列优先级从左至右扫描，分支消费过的字符不再进入后续分支：

1. 反斜杠后紧邻一个或多个 ASCII 字母时，消费完整 TeX 控制词，term 为 `t` 加其包含反斜杠的原 UTF-8 小写十六进制；保留控制词大小写，`\Gamma` 与 `\gamma` 不等同，不执行 TeX。
2. Han 区间固定为 U+3400..4DBF、4E00..9FFF、F900..FAFF、20000..2FA1F、30000..323AF；每个连续区间串输出各单字 `h`+UTF8hex，及每一对相邻字符 `g`+二字UTF8hex。这里只定义词法范围，不宣称区间内每个位置都有已分配字符；不跨非Han字符拼二元词。
3. Unicode15中 category 为 Letter 且名称含 LATIN 的连续字母（允许跟随 combining mark）组成 Latin 词；以该词的 Unicode15 casefold 再 NFC 结果形成 `w`+UTF8hex。连续 ASCII 数字另成词，term同为 `w`+原数字UTF8hex；字母与数字边界分词，因此 FTS5 与 FTS 5 具有相同这两项 term。
4. 数学符号集合 `+-*/=<>≤≥≠≈±×÷∑∏√∞∂∇∈∉⊂⊆∪∩∀∃¬∧∨→↔^_%|!` 中每个字符为 `m`+UTF8hex。其他 Unicode15 Letter/Number 单码点为 `u`+UTF8hex，保留大小写和精确码点。其余标点、空白及未消费的反斜杠作为分隔符，不成为 term；不执行或保留用户 MATCH 控制语法。

每块 term 去重后按 ASCII 排序，FTS tokens 为单空格拼接；query 用同样算法去重。所有 term 仅含安全 ASCII 前缀和十六进制，使用参数化 FTS5 MATCH 的文字 OR 集合，不把原 query 拼为 MATCH/SQL。只对已授权 scope/current generation 的文档匹配。score 固定为 `|Q∩T(block)| / |Q|`，范围(0,1]且有限；按 score 降序、block完整(entity,id,revision,sha256)升序稳定排序，不使用范围外文档频率/全库 topK。FTS5 是词法候选机制，不把共享表的全局 bm25 统计冒充 scope 内统计。词法/排序/定位及资源版本和真实派生 term/chunk hash 进入代际清单。该简单覆盖率不是语义置信度、来源核验率或学习效果，不自动把 α/\alpha、≤/\le 或任何数学别名等同。

**持久重建与消费所有权。** rebuild 使用 Idempotency-Key、会话/CSRF和当前Policy，expected_corpus_sha256 是同一显式 scope 的 server 目标强CAS；新命令不匹配返回412。provider_id/consent_id必须显式null，非null返回CAPABILITY_UNSUPPORTED且零外发，不注册Provider source、不做embedding/远程分词。原同key完整命令回原JobRef，不创建第二任务；同key不同规范命令409；原ACK与当前Job状态分别回读。新任务原子登记scope/冻结descriptor和Jobs输入，Job kind=retrieval_index，由真实Retrieval job owner支持既有GET /jobs/{id}和POST /jobs/{id}/cancel，不能只插一种未知kind。

worker在短事务领取可恢复租约；在事务外逐块读取/核真实正文和派生词法数据，循环中有界检查停止/取消；最后短事务重新核owner租约、取消、当前Policy和完整corpus descriptor，再将清单/chunk集合/当前代际指针、唯一完成事件及Job终态原子提交。新输入/版本不匹配则安全失败 INDEX_INPUT_CHANGED，保留原代际；不能在旧任务中换scope/material后冒称原命令成功。queued/running取消和lease丢失不发布部分代际；恢复只重试未完成的本地确定性工作，不涉及外部请求。Index job的result_refs是实际索引的ContentRef集合（≤512），不造ContentRef来冒充索引ID；实际index_version和scope/corpus hash保存于自己的Job结果账本并由status/overview回读。

Content发布/current pointer/生命周期或来源descriptor变化在owner事务中登记依赖失效意图，已登记scope保留原roots。M5.2不因GET/query或stale状态自动新建任务；只有显式rebuild命令创建新Job，worker启动恢复已经登记的未终态任务。维护可标记自己的旧代际/消费进度，但不能追加未选择的scope，不能替Content/Learning清除共享依赖复核信号。有效性读回仍重算当前descriptor，不能只信dirty标记。所有queued/running/awaiting_approval学科任务参与现有独立测试排他；索引不豁免。worker调度给索引、导入、评分、推荐有界轮次，不能用长期写锁、无界循环或只做fire-and-forget宣称可靠构建。

**基准与验收。** 附录F.1的原创冻结词法语料/gold是M5.2工程基准，实际数据、全部精确ContentRef/body SHA、算法/Unicode/SQLite版本、硬件、规模、冷暖条件、测试命令和逐case排名必须记录；先冻结再运行，不能按结果改gold或删除失败例。正向集合平均 Recall@5≥0.90，Recall@5按每个case的gold完整ref集合中进入前5的比例再算术平均；无匹配、安全与别名诊断单列，不加入该均值凑分。私解/越权scope/旧ref错贴/语法执行/Policy切换/损坏字节与Jobs恢复全部安全断言必须PASS。前端/native需至少真实query冷态→显式rebuild→job完成→准确命中/无结果/资源遗漏及旧scope重建回读，截图和范围说明不冒充真实模型、专家审校或整个M5验收。阈值是本项目首轮工程门槛，不是已测结果或通用RAG质量保证。

### 20.8 M6.1 首个例题生成与数值检查切片

本切片只生成一个新 `worked_example` 候选块，不修改既有内容、不生成整课/习题集/测验，不执行 M6.2 审核发布或 M6.3 Codex。它是 M6.1 的第一项可独立验证的实现，不能据此关闭整个 M6.1。作者在“创作”辅助入口明确填写主题、先修、目标、证明策略、provider 和零至八个精确公开 block 引用；无来源允许准备，但清楚显示“无已选教材来源”，不伪造引用。其他 output_kind、question/私有答案/历史作答源、自动扩范围、网络搜索和任意代码执行在本切片不开放。

**准备与生成。** POST `/authoring/jobs` 只接附录 A 的 AuthoringPrepareWrite，不接 consent_id、客户端上下文全文或 hash。服务端在 author 会话、工作区/Policy 和源引用核验后，同事务保存真实 `jobs.kind=authoring`、不可变输入与准备快照、原创建命令回执；初始 awaiting_approval，无 Provider 请求。所选 block 由 Content owner 读取精确元数据与真实正文 bytes/SHA，冻结原来源/未审事实；按用户引用顺序去重（重复输入拒绝），不从 current 指针改用新版，不从引用推定审核通过。仅两条基础 message（版本化 system 模板、原教学约束规范 JSON）及所选完整块 evidence，最终包装后仍须≤12,000 codepoints、evidence≤8；任何已选材料或必要约束超限均明确拒绝准备，不静默省略。source_refs=[] 时不调用要求非空 scope 的 Content 端口。模板把材料作为不可信数据，保留 full/declared_dependencies 原约束；保留约束不代表模型已经满足证明要求。

作者从同一实际 Job 的当前 id/revision 发起已有 Provider preview/grant。purpose=authoring，原 Job+input/context/prepared/request-body SHA 与真实 proposal/consent 一一绑定；不能再次 POST 改带 consent 的 body 来“继续”。批准回调经 Authoring owner 同事务使同 Job 可调度；撤回/过期后不自动重批，若尚未 dispatch 可在同一未终态 Job 当前阶段重新明确预览，已有开始许可则只恢复原实例。Provider 实际使用普通文本 chat/streaming，提示返回一个严格 JSON 对象不等于供应商 structured_output 能力；不增加 response_format、tools 或搜索能力。仅实际受检 complete、无 refusal 的完整 answer 可尝试解析，禁止剥代码围栏、截取局部 JSON、猜字段或用修复请求暗增第二次调用。解析失败/拒答/不完整保留原输出与受检终态，Job failed 或按取消事实 cancelled，不造候选成功。

通过结构/引用检查时，Authoring 同事务建立唯一不可变 DraftCandidate、检查记录及 completed Job 结果；completed 只表示候选已持久，数值复算及人类数学/来源审校仍未运行。candidate.entity=block，draft_revision 首版为1，candidate_sha256 对完整候选 payload 的规范 JSON，不是尚不存在的 ContentRef；其中 body_sha256 对原 body_markdown UTF-8 字节，正文不悄悄规范化。Job.result_refs 永远不塞入草稿/检查 ID，首切片为 []；生成结果从专用读口回读。原模型输出保留且标未核验，即使文本自称 APPROVED 也不授予审核。机器可检查 schema、声明引用是否来自本次材料、声明符号是否重名、算术计划能否解析；不能自动证明 Markdown 的公式/条件/推导或数字与计划等价。

**草稿归属。** 首切片 Authoring 用自己的不可变候选/修订表和命令账本，GET `/authoring/drafts/{id}` 返回 authoring 判别字段及专用 payload；既有 GET `/drafts/{id}` 保持 Import owner 的 ImportDraftSnapshot，不替换成宽 union、不让 import_id 解析生成候选。两个 owner 只读自己真实记录，未知/其他 owner ID 返回404，不能根据 ID 前缀授予权限，也不跨 owner SQL 猜归属。首切片不往原 Import drafts 写假 import_id；M6.2 接入通用审核/发布前须用所属迁移/端口统一真实候选身份与 reviews 外键，不能拿本切片名义提前开放发布。原第15.1节 Draft 状态不新增 rejected/needs_review：本切片合法候选始终 draft，数值失败仍为 draft；§12.4 的 rejected/needs_review 是检查结论或待审提示，不是新 Draft 状态。坏 JSON 仅保留生成失败产物，没有合法 DraftCandidate。

**独立的数值批准。** 候选里的 numeric_plan 是待检查建议、默认不执行。作者显式 POST 候选的 numeric-checks 预览后，服务端冻结精确 DraftCandidate、整个计划、固定 evaluator/runtime SHA、资源界限与操作 SHA；浏览器展示所有变量/单位、表达式、期望值和容差及仅本机执行范围。只有另外的 approve_once 才创建实际 `jobs.kind=authoring_numeric_check` 并允许隔离 worker 执行；Provider consent 不批准本机执行，生成完成/打开预览/GET 不运行检查。decline 不建 Job、零执行；过期批准拒绝，原决定 ACK 按完整命令/当前允许范围回放。每个预览最多一个实际检查 Job，其他 key 重复决定409；首切片每个候选最多100份数值预览（包含已过期/拒绝/完成者），达到上限时仅拒绝新预览为413 NUMERIC_PREVIEW_LIMIT，不删除旧记录腾位，不阻断原100份读取、原ACK、已批准Job取消。这个初始资源边界可由后续明确的分页/配额改进替代，不代表永久能力上限。用户需要再次复算时显式建新预览/批准，保留两次事实，不把旧批准挪给新版候选/计划/runtime。

首个 evaluator 为 `finite-arithmetic-v1`：表达式只允许有限十进制常量、已声明变量、括号、一元 +/-、二元 + - * / **；无函数调用、属性、下标、字符串、布尔、复数、赋值、import、文件或网络。先有界解析后解释 AST，不调用 eval/exec/compile 执行表达式，不运行模型代码。每式≤512 codepoints、128 AST节点、深度16；幂指数求值后必须为 -16..16 的整数，所有常量、中间值、结果为有限 binary64，变量和检查分别最多32，每个 NumericAssertion.unit 同时标注该条 actual/expected 的数值，变量 unit 仅展示；本 evaluator 不推导表达式单位、不验证维度相容，也不实施单位换算，不能宣称已通过维度检查。比较用 §13 的 atol+rtol 规则；差值、容差乘积/和等比较中间值同样须有限，溢出为真实 NUMERIC_NONFINITE，不能因阈值变Infinity而通过。随机数不支持，seed 显式 null。受限语言之外的任务明确 NUMERIC_PLAN_UNSUPPORTED，不换 shell/Python/Codex 通道。

预览中的 evaluator_sha256/runtime_manifest_sha256 必须由受信数值 owner 对实际将用的本机文件取得，不接受调用者或模型提交。受信部署清单列出完整执行闭包：evaluator入口、启动/限制规则、Python可执行文件及实际允许加载的标准库/动态库、sandbox可执行文件和配置；每项含无个人路径的逻辑相对路径、实际bytes大小和SHA，另记录版本与清单格式。preview实际逐文件安全打开并核bytes后计算规范清单SHA，不能只读一串缓存SHA当已核runtime；执行前再次核全部成员、路径/非symlink/大小/SHA与原清单，建立同批经核验的只读固定文件/描述符挂载，不能先核后切到另一可变路径执行。未声明依赖不得从宿主Python环境/用户site-packages/环境搜索路径补入；闭包无法核实则不可批准或执行。更换任一成员/版本/限制规则使原预览不可用于新执行，须新预览/明确批准，不改原操作/ACK。隔离检查和数值计算的实际运行由用户该次单独批准；preview只读文件/本机元数据，不通过执行模型代码或联网“探测”环境。

执行必须用真实隔离子进程，禁止网络与读取工作区、用户HOME、环境秘密、Provider密钥；只只读挂载批准输入和受信 evaluator/runtime，临时输出隔离，非 root/无额外权限。初始预算 wall=5s、CPU=2s、内存=256MiB、输出=64KiB、进程数=1；启动程序可有受控sandbox supervisor但计算器不能派生子进程。缺可靠隔离或资源限制为 BLOCKED_ENVIRONMENT，零非隔离fallback。批准后执行前重核候选/操作/实际runtime SHA、Policy、租约与取消；不在数据库写事务内等待进程。执行开始事实先持久，再启动；终态/结构化输出清单与哈希同事务提交。启动后崩溃无法核实结果时记录 outcome_unknown、不自动再运行；只有能证明尚未取得开始许可的准备可安全重试。取消/超时杀整个子进程组并保留已发生事实，不声称未执行。

数值 PASS 仅指本次完整计划在记录的输入、binary64、单位标签及容差下全部通过；模型同时编造表达式和期望值仍可能自洽错误，正文与计划关联未经数学核验。FAIL 保存实际不符/算术错误；超时/环境/资源/取消/未知运行状态保留真实边界而非PASS。每次结果有原输入和计划 SHA、软件/可执行文件/沙箱版本清单 SHA、seed、实际开始/结束、退出码（未取得则null）、结构化输出及其SHA。无运行/无输出不得填0退出码或空成功。任何数值或 Schema PASS 都不改变 mathematical/sources=NOT_RUN、independent_pedagogy=NOT_RUN，不生成 APPROVED ReviewReceipt，不发布 Content，不更新学习证据/成绩。

准备、学科详情/草稿/原输出/数值结果读取、批准、派发与执行前均要求 author 且受当前工作区 Policy；首切片不接 attempt/question 上下文，用原 private_artifact 防护保守阻断尚受答案保护的测验（含 assisted），另显式阻断活动 open_book/independent，不能从 Authoring 绕过 Tutor 的绑定规则。普通材料读取不因此改权限。所有非终态 Authoring/数值 Jobs 参加既有 independent 启动排他。GET `/authoring/jobs` 控制分页、GET `/jobs/{id}` 和原 cancel 是不含学科正文的控制入口：所属工作区 learner/author 在角色降低/策略锁后仍能回读状态或取消，不返回题设/源标题/正文/原错误详情/候选payload。GET 不修状态；worker负责唯一终态。所有领域写校验会话、Origin/CSRF及完整 route/actor/workspace/key/body/CAS；原 ACK 和当前投影分别回读，412保留本页候选，新key不用于偷重试未知结果。

创作辅助入口须能进入安全控制面板：已确认工作区会话下，即使角色为learner、策略未知或活动测试限制学科读取，仍可发现上述安全Job列表并取消；不因Shell的学科入口总锁而把所有控制藏起来。此时清空/阻断主题、源材料、候选、数值输入/输出等学科payload，准备/详情/批准不可用，不借控制入口恢复旧缓存正文；workspace/session变化废弃旧异步，保留既有未保存关闭保护。恢复正常author及当前Policy后再显式读取受保护详情，不自动批准或执行。四个主导航不变。

首切片验收须分开真实 SQLite/受控 Provider/隔离进程链、浏览器授权/候选/批准/拒绝/恢复、真正托管 Provider 的完整证明和本次费用授权。缺托管证明时继续可验证的本地工作，生产外发仍零传输且 NOT_RUN；受控本机模型、固定合成例题或数值 PASS 不代表真实模型、所有生成类型或数学/来源审校完成。

## 21. 旧格式兼容与确定的范围边界

旧 Demo 不是依赖。仅保证以下可识别的迁移轮廓：

- `learning-course@1.0.0`：具有 title、chapters/lessons 数组，章节至少含 id/title 和 markdown/content 文本；单章节导入为 text块，原始结构作为 source保留；不从正文正则推断可靠试题边界。
- `learning-route@1.0.0`：title、goal、steps 数组，任务至少含 label/title 与可识别目标；无法映射精确课程/章节时标 unresolved，由用户确认，不凭同名合并。
- `learning-workspace@1.0.0`：能识别 courses/notes/progress 的部分分项预览；未知键保留原件并报告未迁移，禁止宣称完整恢复。原始对象版本不丢失，原有测验得分只作 user_supplied_import。

本轮从零软件P0不要求所有历史私人格式精确兼容；UI必须对不支持字段/文件明确报错。新增兼容依据合法样例、解析器版本与回归测试进入本文，不让 Agent猜测未知数据。

没有公共多租户、学分、支付、监考、课程市场、任意代码自动执行或复杂证明全自动终审。E1 的Zotero/博客/QTI/LTI均为扩展，主界面可见能力状态但不能出现点完就假成功的按钮。后续需求要追加稳定ID并变更规范，不将“其它必要功能”无限扩张为无法验证的承诺。


## 22. 参考来源与事实边界

以下为一手产品文档、标准与官方说明；本轮重点重新核对工作台布局、Open edX课程侧栏、Codex、GitHub建仓/进度能力、数据与公式技术文档。版本相关实现必须在 M0/M5/M6 重新固定依赖版本，不能以文档链接代替运行测试。引用只支持其公开机制或接口，不支持竞品内部实现、教学收益因果结论或本产品已经通过验收的说法。

| 编号 | 来源 | 用于支持 |
|---|---|---|
| S1 | [VS Code — User Interface](https://code.visualstudio.com/docs/editing/getting-started/userinterface) | 主/副侧栏、编辑区、标签、状态栏 |
| S2 | [VS Code — Custom Layout](https://code.visualstudio.com/docs/configure/custom-layout) | 布局调整与显示策略 |
| S3 | [Open edX — 官方教育者文档入口](https://docs.openedx.org/en/latest/) | 课程结构与内容组织；具体版本在实施时固定 |
| S4 | [Coursera Coach 官方介绍](https://blog.coursera.org/coursera-coach-leveraging-genai-to-empower-learners/) | 课程内辅助学习的公开产品机制；历史介绍非现时可用性保证 |
| S5 | [W3C APG — Window Splitter](https://www.w3.org/WAI/ARIA/apg/patterns/windowsplitter/) | 分隔条语义和键盘行为；页面注明尚有评审工作 |
| S6 | [W3C APG — Tree View](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/) | 树形导航键盘与焦点语义 |
| S7 | [React — Preserving and Resetting State](https://react.dev/learn/preserving-and-resetting-state) | 组件身份与状态保留 |
| S8 | [FastAPI — Features](https://fastapi.tiangolo.com/features/) | 类型校验、OpenAPI 与接口文档能力 |
| S9 | [JSON Schema — Draft 2020-12](https://json-schema.org/draft/2020-12) | 交换格式约束基础 |
| S10 | [SQLite — Foreign Key Support](https://www.sqlite.org/foreignkeys.html) | 外键启用与约束 |
| S11 | [SQLite — FTS5](https://www.sqlite.org/fts5.html) | 词法索引与 tokenizer |
| S12 | [MathJax — TeX and LaTeX Support](https://docs.mathjax.org/en/latest/input/tex/index.html) | 公式输入能力边界 |
| S13 | [OpenAI — Web Search](https://developers.openai.com/api/docs/guides/tools-web-search) | 搜索工具调用与引用 |
| S14 | [OpenAI — Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | 输出形状约束，而非语义正确性保证 |
| S15 | [OpenAI — Codex App Server](https://developers.openai.com/codex/app-server/) | 会话、事件和工具审批；可能重定向到新的官方文档宿主 |
| S16 | [OWASP — LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | 不可信来源、工具权限与注入风险 |
| S17 | [1EdTech — QTI](https://www.1edtech.org/standards/qti) | 题目/测试互操作扩展的标准边界 |
| S18 | [Vite — Getting Started](https://vite.dev/guide/) | 前端工具链与运行要求 |
| S19 | [Node.js 24 LTS 官方发布说明](https://nodejs.org/en/blog/release/v24.11.0) | 选用 24 LTS 系列的版本基础 |

| S20 | [Open edX — About Course Units](https://docs.openedx.org/en/latest/educators/concepts/open_edx_platform/about_course_units.html) | 学习者左侧折叠导航与当前单元高亮 |
| S21 | [Open edX — Sidebar Navigation, Redwood](https://docs.openedx.org/en/latest/community/release_notes/redwood/sidebar_nav.html) | 已公开课程内页侧栏排版；历史发布非“当前最新版” |
| S22 | [GitHub CLI — gh repo create](https://cli.github.com/manual/gh_repo_create) | 指定公开仓库、source与push；运行需已授权身份 |
| S23 | [GitHub — About milestones](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones) | 跟踪里程碑下Issues/PR的闭合情况 |
| S24 | [GitHub — About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) | 可选表格/看板/路线图；不是已创建事实 |
| S25 | [OpenAI — Codex prompting](https://developers.openai.com/codex/prompting/) | 上下文、任务边界与验证说明，可能重定向官方新地址 |
| S26 | [OpenAI — Token Counting](https://developers.openai.com/api/docs/guides/token-counting) | 完整输入包含消息/格式开销；不是通用本地精确计数证明 |
| S27 | [OpenAI — Responses Create](https://developers.openai.com/api/reference/python/resources/responses/methods/create) | 输入、max_output_tokens、truncation 与实际 usage 字段 |
| S28 | [OpenAI — Chat Completions Create](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create) | 受支持模型的 max_completion_tokens、stream_options.include_usage；非任意兼容端点保证 |
| S29 | [OpenAI — Responses Streaming Events](https://developers.openai.com/api/reference/resources/responses/streaming-events) | 文本部分与请求级终态、拒答/失败/不完整事件 |
| S30 | [OpenAI — Chat Completions Streaming Events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) | choice/usage 流事实与缺失计量边界 |
| S31 | [OpenAI — Python Library](https://developers.openai.com/api/reference/python) | SDK默认重试/超时需显式收窄；实际采用依赖另行固定 |

外部资料是设计依据与API参考；产品行为由本文件自包含地规定。不需要阅读这些网页才知道本平台要构建什么。参考可访问性改变时应记录，不复制封闭产品未公开实现，不用竞品宣传证明本产品教学效果。

**最终交付原则：可以交付有边界的原型、部分里程碑或待验收功能，但不得用“接口已定义”“模板响应成功”“Schema 通过”替代实际功能、模型质量或学习效果已经验证。**


# 附录 A：全量 HTTP 字段与错误语义

这是本文件的一部分，不是另外要下载的契约文件。M0登记全部路由；后续在对应阶段把内联字段生成强类型DTO与实际handler，最终做路由—OpenAPI—测试的双向覆盖。

## HTTP 完整业务字段目录

所有路径除 /health 外使用 /api/v1 前缀。本目录列出全部 P0/P1 路由语义；类型名由附录 B 定义，未出现为 Python 类的内联 DTO 必须在所属里程碑生成强类型模型。未知请求字段拒绝。页内字段语法 T? 表示可选，T|null 表示允许空值。写命令执行权限、CSRF、幂等与并发检查；GET只读，不产生付费调用。

### 通用封装

`Page<T>={items:T[],next_cursor:string|null,total_hint?:integer>=0}`；查询 `limit` 默认20、最大100，`cursor` 为服务端签发游标，不接受客户端 SQL 片段。

`JobRef={id:Id,status:queued|running|awaiting_approval|completed|failed|cancelled}`。

`JobSnapshot={id,workspace_id,kind,status,revision,created_at,updated_at,progress:{completed:integer,total:integer|null,label:string},result_refs:ContentRef[],warnings:Warning[],error:ErrorDetail|null}`。progress不是完成承诺；状态 completed 才能发布成果引用。

`Warning={code:string,message:string,locator:string|null,severity:info|warning|error}`，不含绝对私有路径。`MutationAck={id:Id,revision:integer>=1,applied:boolean}`。`DownloadArtifact={artifact_id:Id,filename:string,size:integer,sha256:Sha256,media_type:string,download_path:string}`；download_path 只指当前同源受权限控制端点，禁止返回任意文件路径。所有非GET写操作校验本机会话和 CSRF。创建/状态转换用 Idempotency-Key；更新同时有基准 revision；错误规范统一。

### Workspace / 导入 / 导出

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| GET `/workspace` | 无 | `{id,title,revision,preferences:{language,reader_font_size,default_learning_minutes,auto_attach_current_lesson},layout:{nav_width,agent_width,nav_collapsed,agent_collapsed},data_schema_version}`。不返回密钥或全库正文 |
| PUT `/workspace/preferences` | `{expected_revision,preferences:{language?,reader_font_size?,default_learning_minutes?,auto_attach_current_lesson?}}` | MutationAck；读取字体范围14–28、每天分钟1–600；禁止通过此接口修改 provider secret |
| POST `/imports` | multipart `file`，`kind:auto|markdown|text|html|pdf|docx|learnpack`，`target_course_id?`；最大字节数按正文 | 202 `{import_id,job:JobRef,input_sha256}`。仅暂存，不改正式课程 |
| GET `/imports/{id}` | 无 | `{id,status:staged|parsing|preview_ready|committed|cancelled|failed,input_sha256,warnings:Warning[],candidate_summary:{course_title,lesson_count,block_count,unresolved_refs},preview_refs:Id[]}`。预览标识不是已发布 ContentRef |
| POST `/imports/{id}/commit` | `{expected_input_sha256,accepted_warning_codes:string[],id_mapping:{old_id,new_id}[]}` | `{course_refs:ContentRef[],migration_receipt_id}`；新哈希不一致409；error级警告不可绕过 |
| POST `/imports/{id}/cancel` | `{expected_input_sha256}` | `{id,status:cancelled}`；已提交409，不以取消接口删除正式内容 |
| POST `/exports` | `{profile:learner|author|full_backup,course_refs:ContentRef[],include_personal_notes:boolean}` | 202 JobRef。learner profile严格剔除私有解答；完整备份允许用户自身敏感学习记录但提示 |
| GET `/exports/{id}` | 无 | `{job:JobSnapshot,artifact:DownloadArtifact|null}`。只有完成才提供文件 |
| POST `/backups/restore-preview` | multipart `file`；同导入安全预算 | 202 `{proposal_id,job:JobRef,backup_sha256}`。结果列冲突、版本、所需迁移和影响 |
| POST `/backups/restore-commit` | `{proposal_id,expected_backup_sha256,expected_workspace_revision,conflict_strategy:abort|restore_as_new_workspace}` | 202 JobRef；默认abort，不允许默认全量覆盖；执行前做可恢复快照 |

### 内容 / 路线 / 草稿

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| GET `/courses` | `q?`, `cursor?`, `limit?` | Page<{ref:ContentRef,title,language,lesson_count,review_state}>；没有正文 |
| GET `/courses/{id}` | `revision` 必需 | Course；文件里不含自己的hash，响应头ETag为该对象hash；正式服务可另设 resolve-current 查询，不把latest写入证据 |
| GET `/lessons/{id}` | `revision` 必需 | Lesson；按引用读取各块，不默认整库下发 |
| GET `/blocks/{id}` | `revision` 必需 | ContentBlock；Markdown body 由 GET `/blocks/{id}/body?revision=` 返回 `text/markdown`，ETag=body_sha256，并有同样权限检查 |
| POST `/drafts` | `{kind:course|lesson|block|question|practice_set|assessment,base_ref:ContentRef|null,title:string}` | 201 `{draft_id,revision,base_ref,state:draft}`；不是发布对象 |
| PATCH `/drafts/{id}` | `{expected_revision,patches:{field:string,value:JSON}[]}` | `{draft_id,revision,validation_warnings}`。field 必须属于对应kind白名单；拒绝改对象id/基准hash/审核结论 |
| POST `/drafts/{id}/review` | `{expected_revision,checks:[structure|sources|mathematics|numerical_examples],reviewer_note:string}` | 202 JobRef；结构可自动，数学/来源未独立执行则 NOT_RUN，不自行批准 |
| POST `/drafts/{id}/publish` | `{expected_revision,expected_content_sha256,review_receipt_id,acknowledged_warning_codes:string[]}` | 201 ContentRef；角色author；禁止活跃独立测试用此路获取答案；审核与hash绑定 |
| GET `/routes` | `cursor?`,`limit?` | Page<Route>；路线内容与用户完成记录分开 |
| POST `/routes` | Route | 201 ContentRef；检查步骤ID、引用、DAG |
| PUT `/routes/{id}` | Route；If-Match | ContentRef；生成新路线revision，旧完成记录引用旧步 |
| POST `/routes/{id}/steps/{step_id}/complete` | `{route_revision,expected_progress_revision,completed:boolean,origin:manual}` | `{progress_revision,event_id}`；手动完成不授予掌握证据 |

通用草稿 patch 的 JSON 值由 kind 专用模型二次校验，不可用通用字段绕过严格 schema。此做法只用于编辑协议，发布产物仍是强类型对象。

### 习题 / 测试

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| POST `/practice/sessions` | `{practice_ref:ContentRef}` | 201 `{id,revision,practice_ref,questions:QuestionPublic[],responses:ResponseDraft[],status:active}`；没有答案 |
| PUT `/practice/sessions/{id}/responses` | ResponsesWrite | `{id,revision,saved_at}`；刷新GET session可恢复，不能静默覆盖过期草稿 |
| GET `/practice/sessions/{id}` | 无 | `{id,revision,practice_ref,questions,responses,status,exposure_event_ids}`；已请求解答可按策略重新获取 |
| POST `/practice/sessions/{id}/submit` | `{expected_revision}` | `{id,revision,results:ItemGrade[],evidence_label:practice}`；查看解答/提示发生过则明确辅助，不充独立测试 |
| POST `/practice/sessions/{id}/hints` | `{question_id,expected_revision,level:1|2|3}` | `{markdown,exposure_event_id,revision}`；按规则或生成任务返回；生成需另有有效 consent |
| POST `/practice/sessions/{id}/solutions` | `{question_id,expected_revision}` | `{solution_markdown,exposure_event_id,revision}`；在同一事务建立暴露事件，再下发答案 |
| GET `/assessments` | `course_id?`,`cursor?`,`limit?` | Page<{ref,title,question_count,allowed_modes,time_limit_seconds}>；不含抽题随机种子和答案 |
| POST `/assessments/{id}/attempts` | AttemptCreate | AttemptPublic；路径与assessment_ref.id必须相同，冻结题版本/策略 |
| GET `/attempts/{id}` | 无 | AttemptPublic；草稿读取使用 GET `/attempts/{id}/responses` 返回 `{revision,responses,saved_at}`；仅所有者 |
| PUT `/attempts/{id}/responses` | ResponsesWrite | AttemptPublic；active且revision匹配；题目必须属于本次分配 |
| POST `/attempts/{id}/submit` | AttemptSubmit | 202 AttemptPublic；持久化submitted后排评分任务，不能重复计分 |
| POST `/attempts/{id}/abandon` | AttemptSubmit | AttemptPublic；active可弃；已交卷则409 |
| GET `/attempts/{id}/result` | 无 | GradingResult；未交卷409；尚未完成评分可返回202 JobRef；needs_review保留不确定项 |

PracticeAssistanceView = {question_id:Id, highest_hint_level:0|1|2|3, solution_revealed:boolean, model_help_received?:boolean=false}。PracticeSession 与 PracticeSubmitted 的 assistance 使用此应用投影；省略 model_help_received 仅兼容真实旧回执，新投影总显式返回该严格布尔值。assisted 同时纳入真实模型帮助，UI 明示“已获 AI 帮助”，不改变 rules 级别或声称已展开标准答案。原持久 PracticeAssistance、StoredSubmission、评分审核和原提交 JSON/hash 保持；当时的 exposure_event_ids/assisted 不由后来的帮助重写。原提交回读仅按原事件集合投影 model_help_received；当前 session 可以反映提交后实际新帮助。

独立测试跨标签限制按服务端workspace+owner状态判定，不能信任body里的view_kind。业务限制不等于抵御本机管理员。旧成绩重新评分使用新的grading_revision，不覆盖旧结果。

### Thread / Tutor / RAG / 学习画像

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| POST `/threads` | TutorThreadCreate；Idempotency-Key | 201 TutorThreadView；核实际 scope/binding，只建立本地线程 |
| GET `/threads` | TutorPageQuery | TutorThreadPage；本工作区真实列表，恢复本机映射，不猜当前线程 |
| GET `/threads/{id}/messages` | TutorPageQuery | TutorMessagePage；真实顺序/通道/状态，当前学科 Policy 先行 |
| POST `/tutor/runs` | TutorRunCreate；Idempotency-Key | 202 TutorRunView；原 key 回原创建回执，GET 回当前 |
| GET `/runs/{id}` | 无 | TutorRunView；只读，核归属、当前输出权限、自有历史 |
| GET `/runs/{id}/events` | TutorEventsQuery；Last-Event-ID? | text/event-stream；标准 SSE + 严格 TutorSSEEvent |
| POST `/runs/{id}/cancel` | TutorRunCancel；Idempotency-Key | TutorRunControlView；取消请求不等于远端已停，终态取消 no-op |
| POST `/retrieval/query` | RetrievalQueryWrite；会话/Origin/CSRF；不要求写命令幂等键 | RetrievalQueryView；只读精确scope，含scope/corpus hash和missing；完整块/资源遗漏/来源与未审事实明确，零排队/零外发 |
| GET `/learning/progress` | `course_id?` | `{revision,readings:{ref,read,read_at}[],route_steps:{route_ref,step_id,completed}[]}`；无掌握概率 |
| POST `/learning/actions` | `{kind:read_marked|bookmark_set,ref,expected_revision,value:boolean}` | `{event_id,progress_revision}`；客户端不能上传native grade_finalized事件 |
| GET `/learning/evidence` | `concept_id?`,`skill?`,`cursor?`,`limit?` | Page<Evidence>；区分有效、过期、辅助、重复和未知 |
| GET `/recommendations` | `course_id?`,`recommendation_id?`,`cursor?`,`limit?`，默认全工作区，limit 默认20、最大100 | RecommendationPage；仅回读已持久化推荐投影并校验当前依据，不生成/写入/排队刷新；每条有真实原因与来源，空态/缺材料/更新状态显式返回 |
| POST `/recommendations/{id}/decision` | RecommendationDecisionWrite，即 `{decision:accepted|dismissed,reason:string|null}`；Idempotency-Key；If-Match 为所读 RecommendationView.decision_sha256 的带引号强标签 | MutationAck；revision 是该推荐决定版本，applied 表示原命令是否真正改变决定；接受/拒绝不改变路线、成绩、学习事件或能力状态 |
| GET `/notes` | `ref_id?`,`cursor?`,`limit?` | Page<Note>；anchor状态可为stale，不静默迁移到最新版本 |
| POST `/notes` | Note | 201 ContentRef；quote/codepoint与正文校验 |
| PATCH `/notes/{id}` | Note + If-Match | ContentRef；id一致、revision按新版本处理，冲突412 |

### Tutor 应用 DTO、真实上下文与事件恢复（M5.3）

本组是独立严格应用 DTO，不扩54 core，不改变原粗粒度核心端口。对象闭合、拒未知字段；除 query 明确 `?` 外字段 required，nullable 显式null；整数拒bool，数字有限，字符串合法Unicode。Id/Revision/Sha256/UTC/ContentRef/Citation/Warning/ViewContext/TutorRequest/RunSnapshot/ContextSnapshot/ReferenceSummary/UsageSnapshot 沿本文定义。标题/错误文案 nonblank，正文/delta 原样保留空白；嵌套 core 请求同样严格校验类型/关联，不能因core默认值省略本表要求字段。

```text
TutorPracticeBinding = {session_id: Id, session_revision: Revision, question_ref: ContentRef}
TutorAssessmentBinding = {
  attempt_revision: Revision, question_ref: ContentRef, grading_revision: Revision|null
}
TutorContextBinding = {practice: TutorPracticeBinding|null, assessment: TutorAssessmentBinding|null}
TutorThreadCreate = {scope: ViewContext, binding: TutorContextBinding, title: nonblank string[1,200]}
TutorThreadView = {
  id: Id, scope: ViewContext, binding: TutorContextBinding, title: nonblank string[1,200],
  revision: Revision, created_at: UTC
}
TutorPageQuery = {cursor?: nonblank string, limit?: integer[1,100]}
TutorThreadPage = {items: TutorThreadView[], next_cursor: string|null}
TutorMessage = {
  id: Id, seq: integer>=1, run_id: Id, role: user|assistant,
  channel: answer|refusal|null, status: stored|completed|failed|cancelled,
  content_markdown: string, context_snapshot_id: Id|null,
  citations: Citation[], created_at: UTC
}
TutorMessagePage = {thread: TutorThreadView, items: TutorMessage[], next_cursor: string|null}
TutorRunCreate = {
  request: TutorRequest, expected_thread_revision: Revision, binding: TutorContextBinding
}
TutorInputMaterial = {
  reference: ReferenceSummary, body_sha256: Sha256|null,
  material_review: unreviewed|not_applicable
}
TutorContextOmission = {
  ref: ContentRef|null,
  reason: character_budget|block_budget|history_budget|adapter_shape|
    index_missing|index_stale|index_building|no_match|not_released|unavailable,
  message: nonblank safe string
}
TutorContextSummary = {
  snapshot: ContextSnapshot, included: TutorInputMaterial[],
  history_message_ids: Id[0..4], omissions: TutorContextOmission[], warnings: Warning[]
}
TutorFailureCode = ProviderFailureCode | POLICY_DENIED | ASSESSMENT_ACTIVE |
  TUTOR_CONTEXT_INVALID | TUTOR_CONTEXT_CHANGED | TUTOR_CONTEXT_UNAVAILABLE |
  TUTOR_CONTEXT_BUDGET_EXCEEDED | TUTOR_OUTPUT_INVALID | TUTOR_OUTPUT_EMPTY |
  TUTOR_INTEGRITY_ERROR | TUTOR_OUTCOME_UNKNOWN
TutorProviderResult = {
  receipt_id: Id, receipt_sha256: Sha256,
  outcome: complete|refused|incomplete|error,
  provider_outcome: completed|failed|incomplete|cancelled|unknown,
  output_state: none|partial|complete
}
TutorResultSummary = {
  refusal_markdown: string, usage: UsageSnapshot,
  provider: TutorProviderResult|null, error_code: TutorFailureCode|null
}
TutorRunView = {
  run: RunSnapshot, job_revision: Revision, thread_revision: Revision,
  context: TutorContextSummary|null, latest_proposal_id: Id|null,
  consent_id: Id|null, result: TutorResultSummary
}
TutorRunCancel = {expected_revision: Revision}
TutorRunControlView = {
  id: Id, status: queued|running|awaiting_approval|completed|failed|cancelled,
  job_revision: Revision, cancel_requested: boolean
}
TutorEventsQuery = {after_seq?: integer>=0}
```

Thread.scope 与每次 Run.request.context 的会话根身份为 view_kind、完整 active_ref、attempt_id、真实 practice.session_id；必须一致，不按同对象ID暗换 revision/hash。selection、attached_refs、本次 question 与 session/attempt/评分基准可随显式新轮次变化，每次重核 owner。practice 要求 active_ref 是所属 practice_set、practice 非null、assessment/attempt_id 为null，question_ref 是该真实session的精确question。assessment_help/review 要求所属 assessment、attempt_id/assessment 非null、practice=null；help 仅真实 assisted 活动attempt且grading_revision=null，review要求本人可复盘attempt和实际grading_revision。route 对应 route，lesson 对应精确 lesson 或当前 block（block 仅自身，不静默提升父小节），worked_example 对应实际例题 block，两个binding与attempt_id均null；worked_example 核真实block类型。authoring 上下文留M6，本阶段422 TUTOR_CONTEXT_INVALID，不能猜假任务。不可解析绑定拒绝，不从practice_set/最近attempt/浏览器文字猜会话。

Run.id 就是同工作区实际 Jobs.id，kind=tutor；job_revision为真实Jobs版本，事件seq不是该revision。线程revision从1开始，成功接纳新user轮次与最终assistant结果事务各前进一次。同线程至多一个未终态Run，新命令遇其存在409 THREAD_RUN_ACTIVE。先核身份/当前允许操作/自有历史，再同key原载荷回放；新命令核expected_thread_revision，不符412 REVISION_MISMATCH；线程根不符409 TUTOR_THREAD_SCOPE_MISMATCH。workspace_id必须等于会话；web_search必须false、consent_id必须null，当前上下文字段显式提交。四intent可用，research不隐式联网。同key不同载荷409，不借旧ACK重新生成或代替当前GET。

列表/消息分页只读，默认limit20；签名cursor绑定workspace、会话身份、具体列表/线程、limit和首次高水位，稳定无重漏，后续新轮次不混旧页。未知/重复query、不合法cursor400，越权先拒。ThreadPage按created_at/id，MessagePage按线程不可变连续seq；返回thread为当次当前版本，items仍遵原高水位。user消息channel=null/status=stored/citations=[]；assistant为answer或refusal、status为Run真实终态，两通道不合并。真实线程/消息必须可从服务器恢复，不依赖浏览器唯一映射。

Context未冻结时context和run.context_snapshot_id均null，冻结后ID相等。included与actual evidence一一对应，完整ref/locator/字符数/摘录SHA一致。block的body_sha256非null且为完整正文SHA（不同于ContentRef元数据SHA），material_review=unreviewed；其他owner完整交互单位body_sha256=null、material_review=not_applicable，excerpt_sha256仍绑定其实际字节，不能称已审教材。snapshot.resolved_refs按实际解析对象冻结；history_message_ids只含实际纳入项。summary不返回完整私有准备prompt、未释放解答或秘密；omissions.ref=null可表示整体历史/资源遗漏，不能造材料缺口。

创建事务建立user消息、Run、tutor Job、不可变输入与原命令回执。本地worker冻结Context后awaiting_approval。以实际run.id/job_revision调用现有consent preview；Provider成功持久proposal的同一事务经source记录latest_proposal_id和approval_required（approval_id=真实proposal，不是consent或伪Approvals）。该记录不改变冻结Jobs revision，避免使proposal自己失效；未有真实proposal时不造事件。预览失败不造授权/重准备/外发。grant经source同事务核原输入、绑定唯一真实consent，恢复同一Run可调度状态；不能另POST Run或把第二授权替换到原已授权Run。历史approval事件/旧grant ACK不是当前可批准证明，UI回读current validity和同Run状态。无完整生产InputProof时如实验收本地prepare、不可授权诊断和cancel，不能称真实模型贯通。

answer_delta只接Provider answer通道逐字累计，refusal单独保留。result.provider来自实际回执：finished的complete/refused/incomplete映射同名outcome，error映射error；provider_outcome真实保留（complete/refused→completed，incomplete→incomplete，error沿原字段）。终态回执尚无时provider=null，不造receipt/usage。usage是实际累计快照，null表未知，已知不倒退/被null擦除。Run completed须完整非拒答Provider终态+非空经本机结构校验answer；不代表数学/事实已核验。refused/incomplete/空输出/本机校验失败保留原文与远端事实，Run failed给对应有限error_code。失败/取消保留已有answer、refusal、usage和回执；远端已completed不能因本机失败/取消被改写。

最终原answer/refusal、actual citations（本阶段为空）、受检receipt关联、消息、Run snapshot/last_seq、唯一terminal event与Jobs终态在owner协作同一事务提交。Provider终态后崩溃只回读原产物/ledger，不二次派发；缺失/重复/顺序损坏明确完整性失败，不伪造修复。取消持久化真实请求；非终态新命令expected_revision不符412，同key回原控制ACK；已终态取消no-op，即使带旧合法revision也不追加事件。外发已开始时保留真实dispatch/lease，等待受检停止/恢复；cancel_requested=true不是远端cancelled/退款证明。GET jobs的tutor控制投影及通用cancel回执不含正文、引用和敏感错误，但状态/revision仍来自真实Jobs owner。

TutorSSEEvent是闭合判别union，各分支共有{run_id:Id,seq:integer>=1,type,occurred_at:UTC}，只允许对应额外字段：
- queued、completed、cancelled：无payload。
- context_ready：context_snapshot_id:Id。
- retrieval_completed：无payload，只在实际本地检索已执行后产生；missing/stale/未执行明示在summary，不声称找到来源。
- answer_delta：text:string，长度≥1，纯空格/换行原样保留。
- citation：citation:Citation，只允许受检来源owner；本阶段无该能力不产生。
- approval_required：approval_id:Id，为上述真实proposal。
- usage：input_tokens:integer>=0|null、output_tokens:integer>=0|null，至少一项真实计数，累计规则同上。
- failed：error_code:TutorFailureCode。
由真实应用模型/OpenAPI生成严格decoder，不能直接以宽core RunEvent的可空字段袋代替；无关payload字段禁止。

GET events是真正text/event-stream，每帧 `id: {run_id}:{seq}`、`event: {type}`、单行 `data: {规范JSON TutorSSEEvent}`、空行分隔；JSON转义换行但不改解码原文，可发无data注释心跳。after_seq缺省0，URL只接受无符号/小数/指数的十进制非负整数；Last-Event-ID为当前run_id:十进制seq，两者均给不一致400，未知/重复参数400。先核当前归属/学科权限/完整自有历史，再核游标；未来seq409 CURSOR_AHEAD。客户端核framing/type/run_id/连续seq并去重，解析错误不当completed，旧事件不改变当前workspace内容。

seq从1连续，持久snapshot.last_seq覆盖所有已提交事件及对应累计answer/usage；可同事务合并连续同通道delta，但拼接字节文本相同，不跨其他事件/终态换序。GET/重连/心跳零写、零排队、零模型调用，每批输出及连接中权限变化再核，失权停止。初期无自动修剪，水位0；§20.6明确删除后404，缺失/损坏不伪称逾期。只有未来真实受检checkpoint水位才对较旧cursor返回410 CURSOR_EXPIRED并GET完整snapshot恢复，不为模拟逾期先造GC。断线只断观察；先GET当前快照，再从last_seq续读；创建/批准/取消丢ACK先原key回放，禁止自动二次生成/重授权。

### 精确范围词法检索与索引应用 DTO（M5.2）

这些闭合应用类型独立于附录 B 的54 core及原粗粒度 RetrievalHit/Port。所有对象拒未知字段；除 GET query 中明确 `?` 外所有字段 required，`|null` 不可省略。整数拒bool，number拒非有限值；Id/ContentRef/Sha256/UTC/Citation/Warning/JobRef沿用core。全部字符串是有效Unicode，无孤立surrogate；ref不接受latest或客户端author字段。正文、来源摘要和诊断受§20.7资源预算，安全错误不得带正文、秘密或绝对路径。

```text
RetrievalScopeRefs = ContentRef[1..16]  // 输入实体仅course|lesson|block
RetrievalIndexState = ready | stale | building | missing
RetrievalResultState = matched | no_match | indexed_empty | resource_omitted | not_ready
RetrievalQueryWrite = {
  query: string[1..512 Unicode codepoints],
  scope_refs: RetrievalScopeRefs, limit: integer[1,20]
}
RetrievalIndexRebuildWrite = {
  scope_refs: RetrievalScopeRefs, expected_corpus_sha256: Sha256,
  provider_id: Id|null, consent_id: Id|null
}
RetrievalIndexScopeQuery = {scope_refs: string}
RetrievalIndexOverviewQuery = {cursor?: string, limit?: integer[1,100]}
RetrievalIndexStatusQuery = RetrievalIndexScopeQuery | RetrievalIndexOverviewQuery
RetrievalWholeBlockLocation = {
  version: whole-block-v1, unit: unicode_codepoint,
  start_cp: integer=0, end_cp: integer>=0
}
RetrievalScopePath = {
  root_ref: ContentRef, course_ref: ContentRef|null, course_title: string|null,
  lesson_ref: ContentRef|null, lesson_title: string|null, block_ref: ContentRef
}
RetrievalRetainedSource = {
  id: Id, media_type: string, size: integer>=0, sha256: Sha256,
  rights: string, parser_version: string|null
}
RetrievalProvenance = {
  state: frozen | unresolved, original: RetrievalRetainedSource|null,
  citations: Citation[], unresolved_citation_ids: Id[], warnings: Warning[]
}
RetrievalHitView = {
  ref: ContentRef, title: string, text: string,
  locator: string, score: finite number >0 and <=1,
  body_sha256: Sha256, location: RetrievalWholeBlockLocation,
  current_ref: ContentRef, lifecycle: active | archived,
  material_review: unreviewed, provenance: RetrievalProvenance,
  parent_paths: RetrievalScopePath[1..8192], warnings: Warning[]
}
RetrievalOmissionCounts = {
  result_limit: integer[0,512], text_byte_budget: integer[0,512],
  json_byte_budget: integer[0,512]
}
RetrievalQueryView = {
  scope_sha256: Sha256, scope_refs: RetrievalScopeRefs,
  corpus_sha256: Sha256, indexed_corpus_sha256: Sha256|null,
  index_version: Id|null, index_state: RetrievalIndexState,
  result_state: RetrievalResultState, matched_count: integer[0,512]|null,
  hits: RetrievalHitView[0..20], omissions: RetrievalOmissionCounts,
  warnings: Warning[]
}
RetrievalJobSummary = {
  job: JobRef, target_corpus_sha256: Sha256,
  error: {code: string, message: string, retryable: boolean}|null
}
RetrievalCommittedIndex = {
  index_version: Id, corpus_sha256: Sha256, built_at: UTC,
  block_count: integer[1,512], term_count: integer>=0
}
RetrievalIndexScopeStatus = {
  kind: scope, scope_sha256: Sha256, scope_refs: RetrievalScopeRefs,
  corpus_sha256: Sha256, state: RetrievalIndexState,
  indexed_corpus_sha256: Sha256|null, index_version: Id|null,
  last_built_at: UTC|null, latest_job: RetrievalJobSummary|null
}
RetrievalRegisteredScope = {
  scope_sha256: Sha256, scope_refs: RetrievalScopeRefs,
  latest_index: RetrievalCommittedIndex|null,
  latest_job: RetrievalJobSummary|null
}
RetrievalIndexOverview = {
  kind: overview, items: RetrievalRegisteredScope[0..100], next_cursor: string|null
}
RetrievalIndexStatusView = RetrievalIndexScopeStatus | RetrievalIndexOverview
```

RetrievalIndexScopeQuery.scope_refs 只是一层传输编码，严格JSON解码后必须验证RetrievalScopeRefs；不能接受多个同名值或其它参数。overview 默认limit20，无scope_refs字段，不把[]当省略。规范化后的scope_refs回读按§20.7排序去重；scope_sha256与workspace、这些roots一致。任何query/rebuild都有相同的实体、512块/16MiB正文登记、16MiB元数据/来源descriptor和8192路径上限，另有完整实际规范JSON descriptor的16MiB累计上限；status并非绕开scope预算的接口。

每条Hit.ref为block，current_ref的entity/id与ref相同但revision/hash可以不同；lifecycle是该对象读取时的事实。text必须是该完整block的实际body，UTF8(text)的SHA等于body_sha256；location.end_cp=len(text)，start_cp=0，locator逐字满足§20.7格式。score使用固定覆盖率，不从客户端提供。title/当前ref/lifecycle/正文/来源/路径须同一受检目标描述与当前Policy一致；不能把元数据正确当成正文已核验。

路径仅描述显式roots里的真实链：root为block时block_ref=root且course/lesson及各title均null；root为lesson时lesson_ref=root、course字段均null，block在该精确lesson；root为course时course_ref=root、lesson_ref非null，按两个完整引用边到block。所有非null course/lesson/block refs实体必须正确，相应title必须实际读取且与null同步；block_ref必须等于Hit.ref，root_ref必须在回读scope_refs中。每个合法命中至少有其一个显式root路径，所有真实不同路径都保留、按(root/course/lesson/block完整ref)排序去重；标题不参与去重身份。直接block路径不是伪造父课程；打开父路径需要明确选择，当前课程/其它历史父链不自动补入。导航必须使用选中的完整ref链，旧hit回读/点击后仍核当前Policy与引用，不把只读点击变为重建或联网。

provenance.state=frozen时original非null、unresolved_citation_ids=[]，citations/warnings保持精确冻结来源事实；空citations可合法，不能凭此称外部核验。state=unresolved时original=null、citations=[]，unresolved_citation_ids等于block原声明citation IDs（可为空），必须有PROVENANCE_UNRESOLVED warning。Citation.verification绝不因state=frozen而改写。每个hit.warnings至少有MATERIAL_UNREVIEWED；旧current_ref不同附HISTORICAL_REVISION，archived附CONTENT_ARCHIVED，信息必须与对应字段一致。以上警告并不授予新版或原件访问。

query ready时index_version/indexed_corpus_sha256非null且后者等于corpus_sha256，matched_count是这个完整scope内实际文字匹配数；hits≤请求limit，总完整text≤2MiB、实际JSON≤8MiB，omissions合计=matched_count−len(hits)。matched要求hits非空；resource_omitted要求matched_count>0且hits为空；no_match要求有已索引term、matched_count=0；indexed_empty要求代际term_count=0、matched_count=0，二者hits为空且omissions全0。非ready仅not_ready、matched_count=null、hits=[]、omissions全0；缺代际时index_version/indexed_corpus_sha256同时null。query顶层warnings在not_ready时使用INDEX_MISSING/INDEX_BUILDING/INDEX_STALE，在资源遗漏时使用RETRIEVAL_RESOURCE_OMITTED，不把未查询当作“没有证据”。

ScopeStatus的index_version/indexed_corpus_sha256/last_built_at必须同时null或同时为对应已提交代际事实；ready要求hash匹配。building需要latest_job是真实非终态Job且target_corpus_sha256等于当前corpus；同scope同时最多一个非终态Job，新增请求不能绕开该约束。failed JobSummary.error必须有实际安全诊断；其它status.error=null。未知/损坏Job关联不造completed或忽略。overview只包含已登记scope，latest_index/latest_job至少一项非null；其最新任务/代际时间不由GET生成。overview没有target corpus_sha256字段，不能从latest_index的旧hash推断当前ready。

IndexRebuildWrite的provider_id/consent_id required；解析为非null合法Id时返回CAPABILITY_UNSUPPORTED，不能悄悄忽略。词法重建无需Provider授权、不创建Provider proposal/grant。请求幂等hash对固定route与规范化roots后的完整body规范JSON计算；语义等价根顺序/完整重复ref不产生第二命令，输入数量限制仍在归一化之前执行。当前Policy、归属与自有历史先于原ACK回放；原key合法回放返当时JobRef，其status不是当前任务读回。新命令stale基准412，same key不同规范命令409。一般字段/schema错误422；资源scope错误413；独立测试409 ASSESSMENT_ACTIVE；损坏Content/索引是安全完整性错误，不用成功空数组掩盖。

### 推荐应用 DTO、只读投影和决定版本

下列类型是推荐端点的闭合应用契约，独立于附录 B 的 Recommendation；未知字段拒绝。未标 `?` 的字段必须出现，`|null` 只允许空值、不表示可省略。Id、Revision、Sha256、UTC、ContentRef、Evidence、SelfAssessment、Warning、MutationAck 沿用附录 B。新 View 只使用正文的 target_ref/reason_codes/evidence_refs，不额外返回 target/reason_code/evidence_ids 别名；不宣称原 Recommendation 严格解码器兼容。

```text
RecommendationReason = prerequisite_gap | assessment_error | review_due |
  next_route_step | user_goal | read_without_practice | practice_without_independent
RecommendationAction = read | practice | test | review | inspect_source
RecommendationDecisionWrite = {decision:accepted|dismissed,reason:string|null}
RecommendationEvidenceRef = {
  evidence:Evidence,
  question_ref:ContentRef, concept_ref:ContentRef, assessment_ref:ContentRef,
  attempt_id:Id, grading_revision:Revision, submitted_at:UTC,
  applicability:usable|pending_review|confirmed_stale,
  grading_origin:deterministic|human_review|unknown
}
RecommendationActivityRef = {
  kind:read_marked|practice_submitted|test_submitted,
  event_id:Id, target_ref:ContentRef, source_id:Id|null, occurred_at:UTC
}
RecommendationProfileBasis = {
  revision:Revision, goal_concept_ids:Id[], goals:string[],
  self_assessments:SelfAssessment[]
}
RecommendationRouteBasis = {route_ref:ContentRef,step_id:Id,source_event_ids:Id[]}
RecommendationNavigation =
  {kind:reader,course_ref:ContentRef,lesson_ref:ContentRef,block_ref:ContentRef|null} |
  {kind:practice,course_ref:ContentRef,lesson_ref:ContentRef,practice_ref:ContentRef} |
  {kind:assessment,assessment_ref:ContentRef,course_ref:ContentRef|null}
RecommendationView = {
  id:Id, target_ref:ContentRef, target_title:string,
  action:RecommendationAction, reason_codes:RecommendationReason[], explanation:string,
  evidence_refs:RecommendationEvidenceRef[], activity_refs:RecommendationActivityRef[],
  profile_basis:RecommendationProfileBasis|null, route_basis:RecommendationRouteBasis|null,
  prerequisite_gaps:ContentRef[], navigation_options:RecommendationNavigation[],
  estimated_minutes:integer>0|null, rule_version:string, generated_at:UTC,
  staleness:current|stale,
  decision:pending|accepted|dismissed, decision_revision:Revision,
  decision_sha256:Sha256, decision_reason:string|null
}
RecommendationPage = {
  items:RecommendationView[], next_cursor:string|null, total_hint?:integer>=0,
  projection_state:missing|pending_refresh|ready|stale|failed,
  warnings:Warning[], snapshot_id:Id|null, generated_at:UTC|null,
  rule_version:string,
  rule_parameters:{review_after_days:integer>0,calibration:uncalibrated}
}
```

RecommendationView.reason_codes 非空、去重、第一项是主原因；七种原因必须逐项有真实依据。target_title、explanation、rule_version 非空。target_ref 仅引用真实可执行的 lesson/block/practice_set/assessment；read/inspect_source 指向教材 lesson/block，practice 指向 practice_set，test 指向 assessment，review 可指向以上已存在材料。prerequisite_gaps 中每个精确 ref 的 entity=concept，去重；尚无法解析的缺口放在 warning，不能造 ref。规则先验证所有引用的工作区、entity、revision/hash、实际父链与可用性，再排序，不用 latest 替换被推荐的原精确对象。

navigation_options 非空、去重，每项严格指向 target_ref。Reader 的 course→lesson→block、Practice 的 course→lesson→practice 关系逐项存在；Assessment 保留实际概念/课程关联，无父课程时允许 course_ref=null。多个真实父链保留选项供用户选择，不能猜唯一教材归属；缺少必要父链的对象不能伪造可点击推荐。导航 refs 不是客户端授权凭据，正常读取仍重新校验权限。

每个 RecommendationEvidenceRef 的 question_ref/concept_ref/assessment_ref 分别为 question/concept/assessment；concept_ref.id 必须等于 evidence.concept_id。evidence.event_id、attempt_id、grading_revision 绑定原成功评分和原 grade_finalized，submitted_at 为原提交时间，evidence.id 不重复。它不包含答案、用户作答、PrivateGradeTrace、私有答案 pin 或签名秘密。deterministic 判分来源必须由 Assessment 所有者验证；若当前评分的人工复核覆盖该题，grading_origin=human_review，不能因为仍保留旧自动 trace 而标 deterministic。未知来源明确 unknown。applicability=confirmed_stale 只用于 Content 实际已确认的结果，pending_review 不冒充已确认失效或可用独立证据。

RecommendationActivityRef 保留原事件 kind/id/time/精确 target；read_marked 只列最后仍为 true 的可信阅读记录，source_id=null；practice_submitted/test_submitted 的 source_id 分别为原 practice session/attempt。hint/solution 获取、会话分配、单纯测试提交不冒充独立成绩。没有评分的参与/目标/路线推荐允许 evidence_refs=[]，必须用真实 activity/profile/route basis 解释，不能合成 grade/Evidence 填满数组。ProfileBasis 保留原自报的 origin/time；没有 profile 行时 revision=1 是默认投影，不表示已保存。RouteBasis 的 route_ref.entity=route，step_id 属于该精确修订，source_event_ids 只引用真实完成/撤销来源。列表内概念目标、自报概念、来源事件均去重。

RecommendationPage 是通用分页外壳的明确应用扩展。未给 recommendation_id 时默认返回当前推荐批次，保留该批次所有 pending/accepted/dismissed 状态；给 recommendation_id 时按真实推荐 ID 精确读取原历史快照与当前决定，最多返回一项，不能因已被新批次替代而隐藏。recommendation_id 与 course_id/cursor 互斥，冲突请求422；未知/不可访问 ID404。所有列表和历史读取模式先核当前 Policy、工作区归属、冻结快照及决定历史/hash，不以历史 ID 绕过活动独立测试。旧目标已不可用时保留真实 stale 元数据；原导航记录不承诺现在可打开，实际导航按当前权限和可用性拒绝，不触发重算或恢复为 current。服务端签发 cursor，绑定工作区、course_id、limit、冻结批次和位置；不能跨范围、伪造或在旧游标下混入新排序，批次不可继续时返回明确游标过期。无快照时 snapshot_id/generated_at=null、items=[]，不能制造尚未落库的 snapshot id。missing 表示尚无可读快照且没有登记的刷新；pending_refresh 表示真实已登记但尚未完成的刷新，也可保留旧 stale 快照；ready 表示当前依据已核验、批次可读；stale 表示精确回读的历史批次依据已过期，不暗示已经为它登记刷新；failed 表示实际投影处理失败，可保留旧 stale 快照及安全诊断。pending_refresh 不等于 worker 此刻正在运行；没有实际执行记录不显示“正在生成”。非 ready 页中的旧 item 必须为 stale；页面 generated_at/rule_version/rule_parameters 绑定返回的实际批次，不能拿当前时钟/新参数冒充旧批次来源。

warnings 使用闭合 Warning，至少区分 NO_LOCAL_MATERIAL、NO_REVIEWED_ASSESSMENT、UNREVIEWED_MATERIAL_ONLY、EXACT_MAPPING_UNRESOLVED、RECOMMENDATIONS_PENDING_REFRESH，locator 仅含安全对象标识或定位，不含私有路径。缺材料 warning 只能来自实际目标、路线或可信学习活动形成的具体需求；真实空工作区且没有目标时不编造缺口或画像。初版不增加未声明的 unresolved_needs 字段。未实测的 estimated_minutes=null；review_after_days 为实际后端可配置参数，初值3，calibration 固定 uncalibrated。

新推荐的决定为 pending、decision_revision=1、decision_reason=null。用户可显式接受、拒绝或更正自己的决定/理由；每次实际变更追加不可变历史且版本加一，不允许客户端写 pending。完全相同的决定和理由、且基准仍当前时返回 applied=false、版本不变。decision_sha256 使用项目规范 JSON，对 `{version:"recommendation-decision-v1",workspace_id,recommendation_id,snapshot_sha256,revision,decision,reason}` 计算 SHA-256，排除 hash 本身；它不是教材 target 的 ETag。If-Match 只接受带引号的单个64位小写sha256强标签，拒绝弱标签、星号、多值或重复关键 header；缺少/格式错使用统一400，过期版本412。

决定写事务先校验当前身份/CSRF/workspace Policy、推荐归属、冻结快照和全部决定历史/hash，再核幂等回执；活动独立测试期间旧 key 也不能绕过策略。请求指纹绑定严格 body 与解析后的 If-Match。回执绑定 actor、完整 route+推荐id、key、request hash、实际幂等实例 created_at、原决定版本/hash 和原 MutationAck。真正同实例重放返回原 revision/applied，不先拿历史 If-Match 与最新版本比较；后来决定被更正或原依据 stale 不抹去已成功命令，当前无权/坏历史仍拒绝。新命令在强 CAS 后核当前依据，stale 返回明确409，不把旧推荐静默改成新推荐再接受。幂等实例到期后的同 key 是新命令，不借旧实例回执通过校验；旧历史保留。首次副作用、决定历史、当前投影与回执同事务提交或回滚。

推荐刷新使用自有 dirty generation/恢复记录；源模块通过 application port 在同一成功事务登记，后台在发布结果前比较所冻结输入仍当前。GET 可只读派生 stale，不能写 stale、刷新状态、队列、outbox 或幂等行。重启/失败/重复处理不能丢 dirty、重复创建同依据推荐或丢用户决定；不能清除共享 Content 待复核信号来冒充已完成影响分析。所有本地推荐读写/后台计算受独立测试 guard，不调用 Provider/Search，也不将接受本地建议视为外发 consent。

### 提供商配置、冻结授权与回读（M5.1）

以下十个操作均使用可信本机会话；写操作同时核 Origin/CSRF。GET 绝对只读，不调用网络/秘密鉴权/计数，不写派生过期状态。配置/秘密控制与减权撤销适用 §20.4 的控制权限；学科摘要、批准和派发适用 §20.5 的实时 Policy。

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| GET `/providers/capabilities` | 无；拒未知/重复 query | ProviderCapabilitiesResponse；仅本工作区真实注册配置/可调度能力；零外发 |
| GET `/providers/{id}/config` | 无；拒未知/重复 query | ProviderConfigView；404 不存在/不可访问；零写 |
| PUT `/providers/{id}/config` | ProviderConfigWrite；Idempotency-Key | ProviderConfigAck；expected_revision=0 仅创建，成功 r1；更新强 CAS；零外发 |
| POST `/providers/{id}/secret` | ProviderSecretWrite；Idempotency-Key；write-only 敏感 body | ProviderSecretAck；成功 secret_present=true；空 secret 不覆盖旧值 |
| DELETE `/providers/{id}/secret` | 单个强 If-Match 与 Idempotency-Key；无 JSON body | ProviderSecretAck；成功 secret_present=false；引用删除不撤回已有请求 |
| POST `/consents/preview` | ConsentPreviewWrite；Idempotency-Key | 201 ConsentProposalView；服务端从真实持久 source 冻结提案；无真实来源/模型证明则安全拒绝，零外发 |
| GET `/consents/preview/{id}` | 无；拒未知/重复 query | ConsentProposalView；原不可变摘要及只读当前诊断 |
| POST `/consents` | ConsentCreate；Idempotency-Key | 201 ConsentCreateAck；只批准原提案，不同步调用模型 |
| GET `/consents` | ConsentQuery；普通列表 limit 默认20、最大100 | ConsentPage；按原 ID 或稳定创建位置分页回读 |
| POST `/consents/{id}/revoke` | ConsentRevoke；Idempotency-Key | MutationAck；仅安全控制回执，撤销后拒新派发；在途请求取消但不保证撤回/退款 |

**严格应用 DTO（独立于 54 core）：** Id/Sha256/UTC/ContentRef 使用附录 B；Revision 为严格整数 >=1，ExpectedRevision 为严格整数 >=0；数字拒 bool/非有限数。下列对象均禁止额外字段，除明确 `?` 外字段 required，`|null` 必须显式给出。nonempty string 不接受空白字符串；字符串/数组同时受本机请求/响应安全大小预算约束。safe string 不得包含秘密、完整学科正文或个人绝对路径。ProviderCapabilities 使用原 core 模型，version_evidence 给已固定适配/模型/计量能力依据或安全不可调用原因，configured 不代表联通；chat/streaming 只表示当前配置/秘密可用且有模型计量依据的已实现适配范围，不代表已有生产 source 或该具体请求已获许可。所有枚举为封闭集合。

```text
ProviderAdapter = official_responses | compatible_chat
EndpointPolicy = public_https | explicit_loopback
ProviderPricing = {
  input_usd_per_million: finite number >=0,
  output_usd_per_million: finite number >=0,
  source_note: nonempty safe string
}
ProviderCapabilitiesResponse = {items: ProviderCapabilities[]}
ProviderConfigWrite = {
  expected_revision: ExpectedRevision, adapter: ProviderAdapter,
  base_url: nonempty string, model: nonempty string,
  embedding_model: nonempty string|null, endpoint_policy: EndpointPolicy,
  pricing: ProviderPricing|null
}
ProviderConfigView = {
  id: Id, revision: Revision, config_sha256: Sha256,
  adapter: ProviderAdapter, base_url: string, model: string,
  embedding_model: string|null, endpoint_policy: EndpointPolicy,
  pricing: ProviderPricing|null, configured: true, secret_present: boolean
}
ProviderConfigAck = {
  id: Id, revision: Revision, config_sha256: Sha256,
  configured: true, secret_present: boolean
}
ProviderSecretWrite = {expected_revision: Revision, secret: nonempty string}
ProviderSecretAck = {
  id: Id, revision: Revision, config_sha256: Sha256, secret_present: boolean
}
OutboundPurpose = tutor | search | authoring | codex
OutboundBudget = {
  max_input_tokens: positive integer, max_output_tokens: positive integer,
  max_provider_calls: 1, max_search_calls: 0, max_tool_calls: 0,
  timeout_seconds?: positive integer = 180,
  max_cost_usd: finite number >=0|null
}
FrozenOutboundBudget = {
  max_input_tokens: positive integer, max_output_tokens: positive integer,
  max_provider_calls: 1, max_search_calls: 0, max_tool_calls: 0,
  timeout_seconds: positive integer, max_cost_usd: finite number >=0|null
}
ConsentPreviewWrite = {
  job_id: Id, expected_job_revision: Revision,
  provider_id: Id, expected_provider_revision: Revision,
  budget: OutboundBudget, expires_at: UTC
}
ReferenceSummary = {
  ref: ContentRef, title: nonempty safe string, locator: nonempty safe string,
  character_count: integer >=0, excerpt_sha256: Sha256
}
MessageSummary = {
  role: system | user | assistant,
  character_count: integer >=0, content_sha256: Sha256
}
InputTokenAssurance =
  {kind: local_exact, input_tokens: integer >=0,
   checker_version: nonempty string, proof_sha256: Sha256,
   request_body_sha256: Sha256}
  | {kind: local_upper_bound, input_tokens_upper_bound: integer >=0,
     checker_version: nonempty string, proof_sha256: Sha256,
     request_body_sha256: Sha256}
CostEstimate =
  {kind: unknown, currency: USD}
  | {kind: estimated, currency: USD,
     maximum_estimated_cost: finite number >=0, pricing_sha256: Sha256}
FrozenOutboundSummary = {
  job_id: Id, source_job_revision: Revision, source_input_sha256: Sha256,
  purpose: OutboundPurpose,
  provider_id: Id, provider_revision: Revision, config_sha256: Sha256,
  adapter: ProviderAdapter, adapter_version: nonempty string,
  base_url: string, endpoint_policy: EndpointPolicy, model: string,
  context_snapshot_id: Id, context_snapshot_sha256: Sha256,
  input_sha256: Sha256, messages: MessageSummary[], references: ReferenceSummary[],
  input_character_count: integer >=0, input_token_assurance: InputTokenAssurance,
  allow_web: false, budget: FrozenOutboundBudget, cost_estimate: CostEstimate,
  created_at: UTC, expires_at: UTC
}
ProposalWarningCode = price_unknown | estimate_not_guaranteed | provider_changed
  | source_changed | source_unavailable | job_unavailable | proposal_expired
  | capability_unavailable
ProposalWarning = {code: ProposalWarningCode, message: nonempty safe string}
ConsentProposalView = {
  id: Id, proposal_sha256: Sha256, summary: FrozenOutboundSummary,
  validity: current | stale | expired | unavailable,
  consent_id: Id|null, warnings: ProposalWarning[]
}
ConsentCreate = {proposal_id: Id, proposal_sha256: Sha256}
ConsentCreateAck = {
  id: Id, revision: 1, status: active, proposal_id: Id, proposal_sha256: Sha256,
  summary: FrozenOutboundSummary
}
ConsentRevoke = {expected_revision: Revision}
ProviderFailureCode = CAPABILITY_UNSUPPORTED | PROVIDER_CONFIGURATION_CHANGED
  | PROVIDER_SECRET_UNAVAILABLE | OUTBOUND_SOURCE_CHANGED | OUTBOUND_SOURCE_UNAVAILABLE
  | CONSENT_REQUIRED | CONSENT_REVOKED | CONSENT_EXPIRED | OUTBOUND_BUDGET_EXCEEDED
  | PROVIDER_TIMEOUT | PROVIDER_CANCELLED | PROVIDER_TRANSPORT_ERROR
  | PROVIDER_PROTOCOL_ERROR | PROVIDER_OUTCOME_UNKNOWN | PROVIDER_USAGE_INCONSISTENT
  | PROVIDER_REFUSAL | PROVIDER_INCOMPLETE
UsageCost =
  {kind: unknown, currency: USD}
  | {kind: estimated, currency: USD, amount: finite number >=0, pricing_sha256: Sha256}
  | {kind: actual, currency: USD, amount: finite number >=0, source: provider_reported}
ProviderUsageView = {
  consumed_provider_calls: integer 0..1, search_calls: 0, tool_calls: 0,
  input_tokens: integer >=0|null, output_tokens: integer >=0|null,
  elapsed_ms: integer >=0|null, cost: UsageCost
}
ConsentDispatchView = {
  id: Id, job: JobRef, started_at: UTC|null, finished_at: UTC|null,
  usage: ProviderUsageView, error_code: ProviderFailureCode|null
}
ConsentView = {
  id: Id, revision: Revision, status: active | revoked | expired,
  proposal_id: Id, proposal_sha256: Sha256, summary: FrozenOutboundSummary,
  created_at: UTC, expires_at: UTC, revoked_at: UTC|null,
  dispatch: ConsentDispatchView|null
}
ConsentQuery = {consent_id: Id} | {cursor?: nonempty string, limit?: integer 1..100}
ConsentPage = {items: ConsentView[], next_cursor: string|null, total_hint?: integer >=0}
```

timeout_seconds 只在 preview 写入 DTO 可省略，服务端规范化为 180 后参与完整命令身份；持久摘要字段全部显式。 预览创建时 expires_at 必须严格晚于服务端当前 UTC，已到期不能生成新的可批准提案；ConsentView.expires_at 与冻结摘要相同，revoked_at 仅在实际撤销后为非 null，正常状态变更不改写原 summary。预算/证明版本、模型和 endpoint 必须对应同一实际请求字节，upper_bound 不得同时给 exact 字段。ReferenceSummary/MessageSummary 的顺序与长度/hash 对应真实准备材料；input_character_count 按最终请求中实际发送的消息/证据文本出现次数计算 Unicode 码点数，同段实际发送两次就计两次；它不计算 JSON 转义字符或替代 token。M5.1 purpose 字典沿用已有四种，但 search/codex 和未注册来源不可批准，不以扩枚举新增假 consumer。

preview 版本条件不匹配或 grant 的原 proposal SHA 不符为 412；无效 schema/未知 query 为 422；Idempotency-Key 必须是单个 `[A-Za-z0-9_-]{1,128}`，缺少/格式错为 400。secret DELETE 的 If-Match 必须是单个带引号的64位小写 config_sha256，拒弱标签/星号/列表/重复，缺少/格式错400，过期412。所有路由拒重复身份/内容关键 header；不反射原 body/SDK headers。provider/consent/proposal 不存在或跨 workspace 为统一404；配置创建不能占用他工作区同 ID。Provider 自有持久命令历史不能只依赖24小时通用回执过期后重做；原完整命令与原 ACK 保留校验，查询不会新建回执。

GET /consents 的 consent_id 与显式 cursor/limit 互斥，最多一项，未知/不可访问 ID 404。普通列表按创建时间+ID 稳定降序；server-issued cursor 签名绑定 workspace、limit 和创建排序位置，不允许跨 workspace/篡改/改 limit 续页。列表不声称当前状态被冻结为全库快照，新 consent 在新首屏出现，旧行的到期/撤销按读取时刻派生。全部模式先核当前 Policy/归属和冻结自有历史；当前 provider/source 改变可使原提案 stale/unavailable，不改写摘要；自身历史/冻结字节损坏则安全错误，不能用 stale 掩盖。validity 顺序为 expired、已确认 provider/source 改变 stale、能力/来源阶段不可用 unavailable、否则 current；已有 consent_id 即使 current 也不可再次批准。当前 source 完整性不能可靠核验时拒绝读取/批准，不以缺失事实放行。

consumed_provider_calls 是本机保守消耗额度，不声称服务商实际执行次数。未知 token/费用保留 null/unknown。ConsentDispatchView 从 Provider 账本和 source owner 的真实 JobRef 投影；未终结 finished_at=null；受检 refused/incomplete 分别显示 PROVIDER_REFUSAL/PROVIDER_INCOMPLETE，自有完整终态事实见附录 D，不把它们称正常回答成功。原 grant/revoke/config/secret ACK 与当前读模型分开；UI 遇412保留候选做显式比较，丢ACK先回放原key/原命令，不自动发新命令。secret只保临时输入，不能混入其他草稿恢复。

### 创作 / Codex / 外部连接

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| POST `/authoring/jobs` | AuthoringPrepareWrite；Idempotency-Key | 202 JobRef，真实 authoring Job，初始 awaiting_approval；无外发 |
| GET `/authoring/jobs` | `cursor?`,`limit?`；默认20、最大100，拒未知/重复/null参数 | AuthoringJobPage；工作区内 authoring/authoring_numeric_check 两种真实Job的安全控制分页，learner/author均可；冻结创建序列，不下发正文/原标题/候选/父级学科关联 |
| GET `/authoring/jobs/{id}` | 无 | AuthoringJobView；真实准备/许可/原生成结果，作者及当前学科读取许可 |
| GET `/authoring/drafts/{id}` | 无 | AuthoringDraftView；精确 DraftCandidate 与 immutable payload，非 ContentRef；不与 Import `/drafts/{id}` 争用 |
| POST `/authoring/drafts/{id}/numeric-checks` | NumericCheckPreviewWrite；Idempotency-Key | 201 NumericCheckView，冻结完整操作、有效10分钟；不创建执行Job、不运行 |
| GET `/authoring/numeric-checks/{id}` | 无 | NumericCheckView；原预览/决定/真实Job与结果，GET零写 |
| POST `/authoring/numeric-checks/{id}/decision` | ApprovalDecision；Idempotency-Key | NumericCheckDecisionAck；approve_once后202真实检查Job，decline后200且job=null；expected_revision强CAS，操作SHA必须完全一致 |
| GET `/jobs/{id}` | 无 | JobSnapshot；敏感日志不下发原始完整请求 |
| POST `/jobs/{id}/cancel` | `{expected_revision}` | JobSnapshot；按任务终态约束 |
| POST `/approvals/{id}/decision` | ApprovalDecision | RunSnapshot；actor、操作hash、任务版本及过期时间校验 |
| POST `/codex/sessions` | `{sandbox_root_id,consent_id,allowed_actions:[read|write_proposal|execute_approved]}` | 201 `{id,revision,status,capabilities:{approvals,interrupt,artifacts},adapter_version}`；浏览器不得传任意绝对沙盒路径 |
| POST `/codex/sessions/{id}/turns` | `{message,context_refs:ContentRef[],expected_session_revision}` | 202 `{turn_id,session_revision,job:JobRef}`；文件/命令审批通过Broker事件传递 |
| POST `/codex/sessions/{id}/interrupt` | `{turn_id,expected_session_revision}` | `{id,turn_id,status:interrupt_requested|already_terminal}`；中断不证明已完成外部副作用全部撤销 |
| POST `/codex/sessions/{id}/artifacts/import` | `{turn_id,artifact_ids:Id[],expected_manifest_sha256}` | 202 JobRef；白名单路径、哈希、大小、审查后进入草稿 |
| POST `/feedback` | `{module,severity:suggestion|minor|major|blocker,description,expected,steps:string[],include_diagnostics:boolean}` | 201 `{id,created_at}`；诊断不自动附私密正文或密钥 |
| GET `/connectors` | 无 | `{items:{id,name,configured,read_capabilities:string[],write_capabilities:string[],last_sync:UTC|null}[]}` |
| POST `/connectors/{id}/preview` | `{scope_ref_ids:Id[],direction:pull|push}` | 202 `{proposal_id,job:JobRef}`；连接不可用明示，预览不写远端 |
| POST `/connectors/{id}/apply` | `{proposal_id,operation_sha256,consent_id,expected_remote_version:string|null}` | 202 JobRef；授权、版本和幂等检查；不支持的标准能力拒绝 |

**M6.1 首切片严格应用字段：** 下列全部对象闭合，未标 optional 的字段 required，nullable 显式 null；bool 不能冒充 int/number，数值 finite，nonblank string 不接受纯空白。Id/Revision/Sha256/UTC/DraftCandidate/JobRef/ApprovalDecision/Warning/UsageSnapshot 沿既有契约；引用 entity 另按这里限制。正文只在当前 author 学科读口，列表/通用 Jobs 控制不携带正文。nullable 不代表可省略。

```text
AuthoringPrepareWrite = {
  topic: nonblank string[1..4000], prerequisites: array[0..32] of nonblank string[1..2000],
  objectives: array[1..32] of nonblank string[1..2000], proof_policy: full|declared_dependencies,
  output_kind: worked_example, source_refs: ContentRef(entity=block)[0..8], provider_id: Id
}
NumericVariable = {name: ASCII identifier[1..32], value: finite number, unit: nonblank string[1..64]}
NumericAssertion = {
  id: Id, expression: nonblank string[1..512], expected: finite number,
  atol: finite number>=0, rtol: finite number>=0, unit: nonblank string[1..64]
}
NumericPlan = {version: finite-arithmetic-v1, variables: array[0..32] of NumericVariable, assertions: array[1..32] of NumericAssertion, seed: null}
WorkedExamplePayload = {
  version: worked-example-candidate-v1, kind: worked_example,
  title: nonblank string[1..300], body_markdown: nonblank string[1..400000],
  symbols: array[1..64] of {name:nonblank string,tex:nonblank string,domain:nonblank string,dimension:nonblank string},
  declared_source_refs: ContentRef(entity=block)[0..8], numeric_plan: NumericPlan
}
AuthoringInputMaterial = {
  ref: ContentRef(entity=block), title: nonblank string, body_sha256: Sha256,
  body_bytes: integer>=1, material_review: unreviewed, provenance: RetrievalProvenance
}
AuthoringPreparationSummary = {
  context_snapshot_id: Id, snapshot_sha256: Sha256, job_input_sha256: Sha256,
  prepared_input_sha256: Sha256, character_count: integer[1..12000],
  materials: AuthoringInputMaterial[0..8], warnings: Warning[]
}
AuthoringValidation = {
  schema: PASS|FAIL|NOT_RUN, references: PASS|FAIL|NOT_RUN,
  symbol_declarations: PASS|FAIL|NOT_RUN, issues: Warning[],
  mathematical: NOT_RUN, sources: NOT_RUN, independent_pedagogy: NOT_RUN
}
AuthoringJobSummary = {
  id: Id, kind: authoring, job_revision: Revision, status: JobRef.status,
  title: nonblank string, candidate: DraftCandidate|null, created_at: UTC, updated_at: UTC
}
AuthoringJobPage = {items: JobSnapshot[], next_cursor: nonblank string|null, total_hint?:integer>=0}
AuthoringJobView = {
  summary: AuthoringJobSummary, request: AuthoringPrepareWrite,
  preparation: AuthoringPreparationSummary, proposal_id: Id|null, consent_id: Id|null,
  provider_receipt_id: Id|null, provider_outcome: completed|failed|incomplete|cancelled|unknown|null,
  usage: UsageSnapshot, raw_answer: string|null, raw_refusal: string|null,
  validation: AuthoringValidation, error_code: nonblank string|null
}
AuthoringDraftView = {
  owner: authoring, candidate: DraftCandidate(entity=block), source_job_id: Id,
  state: draft, base_ref: null, body_sha256: Sha256,
  payload: WorkedExamplePayload, validation: AuthoringValidation,
  numeric_check_ids: Id[0..100], warnings: Warning[]
}
NumericCheckPreviewWrite = {candidate: DraftCandidate(entity=block)}
NumericRuntimeProfile = {
  evaluator_version: finite-arithmetic-v1, evaluator_sha256: Sha256,
  runtime_manifest_sha256: Sha256, python_version: nonblank string, sandbox_version: nonblank string,
  wall_seconds: 5, cpu_seconds: 2, memory_bytes: 268435456, output_bytes: 65536, evaluator_process_limit: 1
}
NumericAssertionResult = {
  id: Id, actual: finite number|null, passed: boolean,
  error_code: NUMERIC_DOMAIN_ERROR|NUMERIC_NONFINITE|null
}
NumericCheckResult = {
  job_id: Id, input_sha256: Sha256, operation_sha256: Sha256,
  outcome: passed|mismatch|evaluation_error|timeout|resource_limit|cancelled|environment_unavailable|outcome_unknown,
  verdict: PASS|FAIL|BLOCKED, started_at: UTC|null, finished_at: UTC,
  exit_code: integer|null, assertions: NumericAssertionResult[],
  output_sha256: Sha256|null, result_sha256: Sha256
}
NumericCheckView = {
  id: Id, revision: Revision, candidate: DraftCandidate(entity=block),
  plan: NumericPlan, runtime: NumericRuntimeProfile, operation_sha256: Sha256,
  decision: pending|approve_once|decline, created_at: UTC, expires_at: UTC,
  expired: boolean, job: JobRef|null, job_revision: Revision|null,
  result: NumericCheckResult|null, warnings: Warning[]
}
NumericCheckDecisionAck = {
  id: Id, revision: Revision, operation_sha256: Sha256,
  decision: approve_once|decline, applied: true, job: JobRef|null
}
```

AuthoringPrepareWrite 中每条先修/目标≤2000 codepoints，整个真实准备仍受12k约束；来源refs完整去重且不冲突。WorkedExamplePayload 是供应商普通文本需解析的唯一对象，禁止重复JSON键/额外字段/非有限数；它不携带 provider/consent、候选ID/正文SHA、审核批准或任意产物路径，这些只能由owner取得/计算。declared_source_refs只能是本次实际 materials的子集，完整ref比较；未声明真实外部引用不能从文字URL猜来源。symbols名称唯一，numeric变量名称为 `[A-Za-z][A-Za-z0-9_]{0,31}`，变量/assertion IDs各自唯一；每个数值变量必须同名出现在symbols，单位dimension只是声明，不把字符串一致当维度定理。NumericPlan 仅声明可复算的显式算术实例，不证明全文与实例相符。

AuthoringJobSummary.candidate 仅在实际候选完成事务后非null，completed与非null候选及三项结构PASS相互对应。失败输出只通过原 CheckedProviderResult 核验后保存/回读，未知用量为null；refusal/incomplete不能建立候选，JSON/schema/ref失败不隐瞒原受检 provider_outcome=completed。合法候选之后的 numeric结果不改候选SHA、Draft状态或已完成生成Job。新 NumericCheckPreview 同时核 URL id 与完整candidate，revision不符412，hash/entity不符409；每次preview是新独立批准对象。operation_sha256=SHA256(规范JSON `{version:"numeric-operation-v1",workspace_id,check_id,candidate,plan,runtime}`)，全部内容先由server冻结，不接受客户端自报plan/runtime替换。expires_at=创建时间+10分钟，GET expired只读派生；decline可对过期预览执行，approve_once须未过期且当前runtime仍同hash。revision 初版1，唯一决定推进到2，Job后续进展不暗改决定修订；原决定同key回ACK后另GET看当前Job，不把原queued ACK当当前queued。

NumericCheckView 仅批准后 job/job_revision 同时非null；decline为null，pending为null，result只在该实际Job唯一终态后出现。NumericCheckResult passed→PASS，mismatch/evaluation_error→FAIL，其余→BLOCKED；正常完整评估每个assertion必须恰好一项且原序，算术域/非有限错误为actual=null、passed=false及真实error_code，否则actual有限、error_code=null、passed按固定比较规则。完整计划评估即使数值不符也可是Job.completed，其检查verdict仍FAIL；环境/超时/资源/未知为Job.failed，取消为cancelled。非完整执行 assertions只列真实已保存项，不把未执行项补假0。result.input_sha256绑定实际NumericJobInput；output_sha256对实际完整子进程输出原bytes（若无则null），result_sha256对完整result唯一排除自身字段。平台控制错误不能用供应商/计算器任意报文直接填API错误；安全code枚举可沿既有错误契约扩展，原正文/输出仅存在本作用域受保护记录。

控制列表cursor冻结workspace、两种Job kind的固定成员范围、limit、创建序列上界和最后排序位置，按创建序列倒序；不冻结动态job状态，下一页不得重复/漏既定成员，新增任务需刷新。AuthoringJobPage.items严格使用现有具名JobSnapshot且kind只允许authoring/authoring_numeric_check，result_refs=[]、warnings=[]、progress.label为固定非学科阶段标签，error只用受控安全code/固定说明；无原主题、源标题、candidate、check或父级关联。其归属/历史逐项由对应owner核验，learner/author不因学科Policy锁而失去安全发现/取消入口；坏历史不跳过成完整列表。拥有正常作者学科权限时，UI再对authoring类id读取AuthoringJobView/候选；numeric类列表只提供现有Job状态/取消，完整检查仍从所属候选的numeric_check_ids及受保护NumericCheckView进入，不猜外露父级ID。无query的三个id读口不接隐式revision或任意path。全部写先校验当前访问与自有历史，再回放原key；新操作才校验当前业务基准/有效性，完整命令不同409、强CAS旧基准412。安全控制通过原 GET/POST jobs，不新增宽权限学科view。

### 生成与覆盖核对规则

以上所有非核心DTO均须在所属里程碑开始前以Pydantic/JSON Schema显式实现，前端客户端从新schema生成。不能拿一个 `{data:any}` 的统一响应草率宣称所有接口已完成。完整对外发布前，规范目录、OpenAPI paths、路由注册和测试清单必须做双向覆盖核对，缺一项即不通过接口完整性验收。


### 本机运行、布局、内容检索、画像和审核闭环

| 接口 | 请求 | 响应与业务语义 |
|---|---|---|
| GET `/health`（无 /api/v1 前缀） | 无 | `{status:ok,build_version}`；不得泄露配置或路径 |
| GET `/readiness` | 已有本机会话 | `{database_ready:boolean,worker_ready:boolean,data_schema_version:string,migrations_pending:boolean}`；不联网、不测试密钥 |
| POST `/session/bootstrap` | `{one_time_code:string}`，同源且有效Host | `{workspace_id,csrf_token,expires_at}`，设HttpOnly/SameSite cookie；一次性code消耗后禁止重用 |
| POST `/session/logout` | 空对象+CSRF | `{logged_out:true}`；使会话失效，不删除学习数据 |
| GET `/session` | 无 | `{workspace_id,role:learner|author,csrf_token,active_independent_attempt_id:Id|null,active_open_book_attempt_id:Id|null}`；两个活动 ID 来自服务端 Policy，开卷只限制学科 Agent，不锁普通材料或导入 |
| POST `/session/role` | `{role:learner|author}` | 同GET session；切author不绕过active测试策略 |
| GET `/workbench/session` | 无 | WorkbenchSession；对象缺失显示unresolved且不丢原始快照 |
| PUT `/workbench/session` | `{expected_revision,session:WorkbenchSession}` | WorkbenchSession；会话revision由服务端递增，包含布局/展开/滚动/标签，成绩不在其中 |
| GET `/courses/{id}/outline` | `revision`必需 | `{course_ref,sections:[{id,title,lessons:[{ref,title,blocks:[{ref,kind,title}],reading_state}]}]}`；不返回正文；当前活动对象由URL/UI决定 |
| GET `/courses/{id}/directory-search` | `revision`,`q`,`limit`≤50 | `{hits:[{ref,title,ancestors:[{id,title}]}]}`；只找此课目录，不伪造内容 |
| GET `/objects/{id}/current` | 无 | ContentRef；只解析当前指针，后续证据冻结精确ref |
| GET `/objects/{id}/revisions` | 分页 | Page<{ref,created_at,review_state,lifecycle}>；归档旧版仍按权限查询 |
| GET `/practice/sets` | `course_id?`,`lesson_id?`,`cursor?`,`limit?` | Page<{ref,title,lesson_ref,question_count}>；Lesson不反向嵌入题集ref，避免hash循环 |
| GET `/sources/{id}` | 无 | `{id,media_type,size,sha256,rights,parser_version,warnings,artifact:DownloadArtifact}`；权限检查 |
| GET `/artifacts/{id}/download` | 无 | 受权限控制字节流；验证manifest和路径，Content-Disposition attachment；独立测试期禁止学科资料下载 |
| GET `/learner/profile` | 无 | LearnerProfile；自报不修改可信证据 |
| PUT `/learner/profile` | `{expected_revision,goals,goal_concept_ids,weekly_minutes,language,preferred_difficulty,self_assessments:[{concept_id,level}]}` | LearnerProfile；origin与时间由服务端填，自报记录保留修订 |
| GET `/learning/concept-states` | `course_id?` | `{items:[{concept_id,skill,evidence_state:none|preliminary|needs_support|consistent,independent_count,assisted_count,stale_count,self_report:SelfAssessment|null,evidence_ids,rule_version}]}`；不返回伪装校准概率 |
| POST `/imports/progress-preview` | multipart JSON文件，`kind:reading|route|legacy_workspace` | `{proposal_id,warnings,mappings:[{old_id,candidate_ref,confidence:exact|unresolved}]}`；不接受外来graded为native |
| POST `/imports/progress-commit` | `{proposal_id,expected_input_sha256,confirmed_mappings:[{old_id,new_ref}],expected_workspace_revision}` | MutationAck；追加origin=user_supplied_import事件 |
| DELETE `/notes/{id}` | `If-Match` | `{id,deleted:true}`；软删当前视图、保留历史引用；彻底删除另走purge预览 |
| POST `/objects/{id}/archive` | `{expected_revision,archived:boolean}` | MutationAck；变更对象lifecycle，不改旧修订正文 |
| POST `/deletions/preview` | `{target:workspace|course|personal_data,target_id,scope:archive|purge}` | `{proposal_id,operation_sha256,affected_counts,unresolved_dependencies,warnings}` |
| POST `/deletions/commit` | `{proposal_id,operation_sha256,expected_workspace_revision,confirm_purge:boolean}` | 202 JobRef；执行前可恢复备份；purge需要额外明确确认 |
| GET `/drafts/{id}` | 无 | 既有 ImportDraftSnapshot：`{id,kind,revision,base_ref,state,candidate_sha256,payload,warnings}`；Import owner、按kind专用DTO，测试期受限；M6.1 Authoring 只用专属 `/authoring/drafts/{id}`，通用审核整合见§20.8 |
| GET `/reviews/{id}` | 无 | ReviewReceipt；candidate绑定确切草稿版本，不返回未授权答案 |
| POST `/reviews/{id}/decision` | `{expected_revision,candidate_sha256,mathematical:APPROVED|REJECTED|NOT_APPLICABLE,sources:APPROVED|REJECTED|NOT_APPLICABLE,reason,evidence_artifact_ids:Id[]}` | ReviewReceipt；author会话显式人工确认，操作者从会话得出；不允许模型自报人工reviewer |
| POST `/attempts/{id}/regrade` | `{expected_grading_revision,reason,item_reviews:[{question_id,score:finite>=0,feedback_markdown}]}` | 202 JobRef；人工复核已提交项，新grading_revision不改旧结果；score≤max |
| POST `/index/rebuild` | RetrievalIndexRebuildWrite；Idempotency-Key、会话/Origin/CSRF；expected_corpus_sha256强CAS | 202真实JobRef；provider/consent必须显式null，仅离线词法；同scope最多一个非终态Job，原ACK与当前状态分开 |
| GET `/index/status` | RetrievalIndexStatusQuery：单个scope_refs严格JSON字符串，或仅overview cursor/limit；两模式互斥 | RetrievalIndexStatusView；有scope只读算目标SHA/coldmissing，无scope分页已登记摘要，不表示全库ready，不读全库正文/写状态 |

对 `PATCH /notes/{id}` 的 Note body：请求 revision 指新候选 revision，If-Match 对旧hash；服务端生成新修订并核对正好 old+1。草稿 PATCH 允许 field白名单中的 JSON 值，但按kind DTO严格校验后才入库。所有读写例外都不能绕过第20.2节workspace级独立测试guard。

外部材料候选通过已授权 Tutor research/SearchPort输出 SearchSource列表，只有用户明确选择后走正常imports暂存预览；不需要再造自动全网课程抓取服务。E1端点返回能力不支持时是明确422/501，不用假成功占位。


| Codex 配套读取接口 | 请求 | 响应与语义 |
|---|---|---|
| GET `/codex/capabilities` | 无 | `{available,authorized,adapter_version:string|null,sandbox_roots:[{id,label}],capabilities:{approvals,interrupt,artifacts}}`；默认沙盒ID为workspace_default；实际路径仅服务端映射 |
| GET `/codex/sessions/{id}` | 无 | `{id,revision,status,active_turn_id:Id|null,adapter_version,capabilities}`；供expected_session_revision并发校验，不能要求客户端猜版本 |


# 附录 B：核心领域模型（可抽取）

Python/Pydantic约束交换形状；权限、引用hash、DAG、私有数据隔离、题目可评分性与数学正确性仍由应用服务及独立检查保证。初次抽取后生成schema，不手抄一个宽松的前端副本。草稿ReviewReceipt绑定candidate；已发布内容只用精确ContentRef。

<!-- BEGIN FILE: packages/contracts/domain_models.py -->
~~~python
"""Target contracts v3.0.0, not a running product. Python 3.12 / Pydantic 2.
Unknown fields are rejected. Cross-object permissions, references, DAGs and hashes
require semantic validation in application services; JSON shape alone is insufficient.
"""
from __future__ import annotations
from typing import Annotated, Literal
from pathlib import PurePosixPath
from datetime import datetime
from pydantic import AfterValidator
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Id = Annotated[str, StringConstraints(pattern=r'^[A-Za-z][A-Za-z0-9_-]{0,79}$')]
Sha256 = Annotated[str, StringConstraints(pattern=r'^[a-f0-9]{64}$')]
def valid_utc(value: str) -> str:
    datetime.fromisoformat(value[:-1] + '+00:00')
    return value
UTC = Annotated[str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'), AfterValidator(valid_utc)]
Revision = Annotated[int, Field(ge=1)]
Text = Annotated[str, StringConstraints(min_length=1, max_length=400000)]
Entity = Literal['course','lesson','block','concept','route','question','practice_set','assessment','note']
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
class ContentRef(StrictModel):
    entity: Entity
    id: Id
    revision: Revision
    sha256: Sha256
class Header(StrictModel):
    schema_version: Literal['3.0.0'] = '3.0.0'
    id: Id
    revision: Revision
class FileEntry(StrictModel):
    path: str
    size: int = Field(ge=0, le=209715200)
    sha256: Sha256
    media_type: str
    visibility: Literal['learner','author_private']
    @model_validator(mode='after')
    def safe_path(self):
        p=PurePosixPath(self.path)
        if not self.path or '\\' in self.path or p.is_absolute() or '..' in p.parts or str(p)!=self.path or ':' in self.path:
            raise ValueError('payload path must be canonical relative POSIX path')
        if self.path=='manifest.json': raise ValueError('manifest must not hash itself')
        return self
class Manifest(StrictModel):
    schema_version: Literal['3.0.0']='3.0.0'
    format: Literal['learning-package']='learning-package'
    package_id: Id
    profile: Literal['learner','author']
    created_at: UTC
    root_course: str = 'course.json'
    files: list[FileEntry] = Field(min_length=1, max_length=2000)
    @model_validator(mode='after')
    def unique_files(self):
        paths=[f.path for f in self.files]
        if len(set(paths))!=len(paths): raise ValueError('duplicate path')
        if self.root_course not in paths: raise ValueError('missing root_course')
        if self.profile=='learner' and any(f.visibility!='learner' or f.path.startswith('private/') for f in self.files):
            raise ValueError('learner package cannot contain private files')
        return self
class Concept(Header):
    entity: Literal['concept']='concept'
    title: Text
    prerequisite_ids: list[Id]=Field(default_factory=list)
    skill_dimensions: list[Literal['recall','explain','compute','derive','transfer']]=Field(default_factory=list)
class Symbol(StrictModel):
    id: Id
    tex: str
    meaning: str
    domain: str
    dimension: str
    scope: Id
    first_definition: ContentRef
class Citation(StrictModel):
    id: Id
    title: str
    url: str | None = None
    locator: str
    source_sha256: Sha256 | None = None
    verification: Literal['verified','unverified','user_supplied']
class ContentBlock(Header):
    entity: Literal['block']='block'
    kind: Literal['orientation','definition','theorem','proof','intuition','worked_example','boundary','summary','text','code','figure']
    title: Text
    body_path: str
    body_sha256: Sha256
    concepts: list[Id]=Field(default_factory=list)
    citations: list[Id]=Field(default_factory=list)
    depends_on: list[ContentRef]=Field(default_factory=list)
    @model_validator(mode='after')
    def body_path_safe(self):
        p=PurePosixPath(self.body_path)
        if p.is_absolute() or '..' in p.parts or str(p)!=self.body_path or '\\' in self.body_path or ':' in self.body_path:
            raise ValueError('body path must be canonical relative POSIX path')
        return self
class Lesson(Header):
    entity: Literal['lesson']='lesson'
    title: Text
    objectives: list[str]
    prerequisite_ids: list[Id]=Field(default_factory=list)
    block_refs: list[ContentRef]=Field(min_length=1)
    proof_policy: Literal['full','declared_dependencies']='full'
class CourseSection(StrictModel):
    id: Id
    title: Text
    lesson_ids: list[Id]=Field(min_length=1)
class Course(Header):
    entity: Literal['course']='course'
    title: Text
    language: str='zh-CN'
    audience: str
    lesson_refs: list[ContentRef]=Field(min_length=1)
    concept_refs: list[ContentRef]=Field(default_factory=list)
    sections: list[CourseSection]=Field(default_factory=list)
    objectives: list[str]=Field(default_factory=list)
    difficulty: Literal['beginner','intermediate','advanced']='beginner'
    @model_validator(mode='after')
    def sections_cover_lessons(self):
        ids=[r.id for r in self.lesson_refs]
        if len(ids)!=len(set(ids)): raise ValueError('duplicate lesson ref')
        if self.sections:
            members=[i for section in self.sections for i in section.lesson_ids]
            if len(members)!=len(set(members)) or set(members)!=set(ids):
                raise ValueError('sections must partition lesson refs')
            section_ids=[x.id for x in self.sections]
            if len(section_ids)!=len(set(section_ids)): raise ValueError('duplicate section id')
        return self
class RouteStep(StrictModel):
    id: Id
    title: str
    target: ContentRef
    requires_steps: list[Id]=Field(default_factory=list)
    completion_rule: Literal['manual','read','practice_submitted','assessment_submitted']
class Route(Header):
    entity: Literal['route']='route'
    title: str
    goal: str
    steps: list[RouteStep]=Field(min_length=1)
class Choice(StrictModel):
    id: Id
    text_markdown: Text
class QuestionPublic(Header):
    entity: Literal['question']='question'
    kind: Literal['single_choice','text_blank','numeric','expression','calculation']
    stem_markdown: Text
    choices: list[Choice]=Field(default_factory=list)
    concept_ids: list[Id]=Field(min_length=1)
    skill: Literal['recall','explain','compute','derive','transfer']
    exposure_group: Id
    max_score: float=Field(gt=0,le=100,default=1)
    input_instructions: str
    @model_validator(mode='after')
    def choices_match(self):
        ids=[x.id for x in self.choices]
        if len(ids)!=len(set(ids)): raise ValueError('duplicate choice ID')
        if self.kind=='single_choice' and len(ids)<2: raise ValueError('choice question needs options')
        if self.kind!='single_choice' and ids: raise ValueError('non-choice question cannot have options')
        return self
class SolutionPrivate(Header):
    question_ref: ContentRef
    grading_kind: Literal['choice_exact','text_normalized','numeric_tolerance','symbolic_review','rubric_review']
    accepted_answers: list[str]=Field(min_length=1)
    absolute_tolerance: float=Field(default=0,ge=0)
    relative_tolerance: float=Field(default=0,ge=0)
    unit: str | None=None
    domain_assumptions: list[str]=Field(default_factory=list)
    solution_markdown: Text
    rubric_markdown: str=''
    review_status: Literal['draft','needs_review','approved']
class PracticeSet(Header):
    entity: Literal['practice_set']='practice_set'
    title: str
    lesson_ref: ContentRef
    question_refs: list[ContentRef]=Field(min_length=1)
    feedback_policy: Literal['on_submit_or_reveal']='on_submit_or_reveal'
class AssessmentBlueprint(Header):
    entity: Literal['assessment']='assessment'
    title: str
    question_refs: list[ContentRef]=Field(min_length=1)
    allowed_modes: list[Literal['independent','assisted','open_book']]=Field(min_length=1)
    time_limit_seconds: int | None=Field(default=None,gt=0)
class PolicySnapshot(StrictModel):
    policy_version: Literal['1.0.0']='1.0.0'
    mode: Literal['independent','assisted','open_book']
    tutor_scope: Literal['operation_help_only','academic']
    allow_web: bool
    allow_materials: bool
    solution_release: Literal['after_submit']='after_submit'
    @model_validator(mode='after')
    def independent(self):
        if self.mode=='open_book' and (self.tutor_scope!='operation_help_only' or self.allow_web or not self.allow_materials):
            raise ValueError('open-book allows materials, not academic tools')
        if self.mode=='assisted' and (self.tutor_scope!='academic' or not self.allow_materials):
            raise ValueError('assisted must declare academic help and materials')
        if self.mode=='independent' and (self.tutor_scope!='operation_help_only' or self.allow_web or self.allow_materials):
            raise ValueError('independent policy cannot allow academic assistance')
        return self
class AttemptCreate(StrictModel):
    assessment_ref: ContentRef
    mode: Literal['independent','assisted','open_book']
class AttemptPublic(StrictModel):
    id: Id
    workspace_id: Id
    assessment_ref: ContentRef
    status: Literal['active','submitted','grading','graded','needs_review','abandoned']
    policy: PolicySnapshot
    questions: list[QuestionPublic]
    revision: Revision
    created_at: UTC
    deadline_at: UTC | None=None
    submitted_at: UTC | None=None
class ResponseDraft(StrictModel):
    question_id: Id
    answer: str=Field(max_length=4000)
    steps_markdown: str=Field(default='',max_length=20000)
class ResponsesWrite(StrictModel):
    expected_revision: Revision
    responses: list[ResponseDraft]
class AttemptSubmit(StrictModel):
    expected_revision: Revision
class ItemGrade(StrictModel):
    question_ref: ContentRef
    score: float | None=Field(default=None,ge=0)
    max_score: float=Field(gt=0)
    status: Literal['graded','needs_review']
    feedback_markdown: str
    solution_markdown: str | None=None
    @model_validator(mode='after')
    def valid_score(self):
        if self.status=='graded' and self.score is None: raise ValueError('resolved grade needs score')
        if self.status=='needs_review' and self.score is not None: raise ValueError('unresolved score must be null')
        if self.score is not None and self.score>self.max_score: raise ValueError('score exceeds max')
        return self
class GradingResult(StrictModel):
    attempt_id: Id
    grading_revision: Revision
    grading_rules_version: str
    status: Literal['graded','needs_review']
    items: list[ItemGrade]
    finalized_at: UTC
class Selection(StrictModel):
    ref: ContentRef
    exact_quote: str=Field(max_length=12000)
    prefix: str=''
    suffix: str=''
    start_codepoint: int=Field(ge=0)
    end_codepoint: int=Field(ge=0)
    @model_validator(mode='after')
    def range_ok(self):
        if self.end_codepoint<self.start_codepoint: raise ValueError('reversed range')
        return self
class Note(Header):
    entity: Literal['note']='note'
    workspace_id: Id
    anchor: Selection
    markdown: Text
    anchor_state: Literal['exact','stale','unresolved']='exact'
class ViewContext(StrictModel):
    view_kind: Literal['route','lesson','worked_example','practice','assessment_help','assessment_review','authoring']
    active_ref: ContentRef
    attached_refs: list[ContentRef]=Field(default_factory=list,max_length=8)
    selection: Selection | None=None
    attempt_id: Id | None=None
class TutorRequest(StrictModel):
    thread_id: Id
    workspace_id: Id
    message: str=Field(min_length=1,max_length=8000)
    intent: Literal['explain','hint','derive','research']
    context: ViewContext
    web_search: bool=False
    consent_id: Id | None=None
class ContextSnapshot(StrictModel):
    id: Id
    created_at: UTC
    request_sha256: Sha256
    resolved_refs: list[ContentRef]
    policy: Literal['learning','practice','test_help','review','authoring']
    character_count: int=Field(ge=0)
    snapshot_sha256: Sha256
class ProviderCapabilities(StrictModel):
    provider_id: Id
    configured: bool
    chat: bool
    structured_output: bool
    web_search: bool
    streaming: bool
    tool_calls: bool
    version_evidence: str
class RunSnapshot(StrictModel):
    id: Id
    thread_id: Id
    status: Literal['queued','running','awaiting_approval','completed','failed','cancelled']
    context_snapshot_id: Id | None=None
    last_seq: int=Field(ge=0)
    answer_markdown: str=''
    citations: list[Citation]=Field(default_factory=list)
    search_status: Literal['not_requested','not_executed','executed','failed']='not_requested'
class RunEvent(StrictModel):
    run_id: Id
    seq: int=Field(ge=1)
    type: Literal['queued','context_ready','retrieval_completed','answer_delta','citation','approval_required','usage','completed','failed','cancelled']
    occurred_at: UTC
    text: str | None=None
    context_snapshot_id: Id | None=None
    citation: Citation | None=None
    approval_id: Id | None=None
    input_tokens: int | None=Field(default=None,ge=0)
    output_tokens: int | None=Field(default=None,ge=0)
    error_code: str | None=None
    @model_validator(mode='after')
    def payload_matches(self):
        required={'answer_delta':'text','citation':'citation','context_ready':'context_snapshot_id','approval_required':'approval_id','failed':'error_code'}
        if self.type in required and getattr(self,required[self.type]) is None: raise ValueError('missing typed event payload')
        return self
class LearningEvent(StrictModel):
    event_id: Id
    workspace_id: Id
    actor: Literal['learner','server','import']
    origin: Literal['native','user_supplied_import']
    kind: Literal['read_marked','hint_revealed','solution_revealed','practice_submitted','test_submitted','grade_finalized','note_created']
    ref: ContentRef
    occurred_at: UTC
    attempt_id: Id | None=None
class Evidence(StrictModel):
    id: Id
    event_id: Id
    concept_id: Id
    skill: Literal['recall','explain','compute','derive','transfer']
    eligible: bool
    reason: str
    score: float | None=Field(default=None,ge=0,le=1)
    independence: Literal['independent','assisted','unknown']
    freshness: Literal['novel','repeated','unknown']
class Recommendation(StrictModel):
    id: Id
    target: ContentRef
    reason_code: Literal['prerequisite_gap','assessment_error','review_due','next_route_step','user_goal']
    explanation: str
    evidence_ids: list[Id]
    decision: Literal['pending','accepted','dismissed']='pending'
    action: Literal['read','practice','test','review','inspect_source']='read'
    prerequisite_gaps: list[Id]=Field(default_factory=list)
    estimated_minutes: int | None=Field(default=None,gt=0)
    rule_version: str='rules-1.0.0'
    generated_at: UTC
    staleness: Literal['current','stale']='current'
class AuthoringRequest(StrictModel):
    topic: Text
    prerequisites: list[str]
    objectives: list[str]
    proof_policy: Literal['full','declared_dependencies']
    output_kind: Literal['lesson','worked_example','practice_set','assessment']
    source_refs: list[ContentRef]
    provider_id: Id
    consent_id: Id
class DraftCandidate(StrictModel):
    draft_id: Id
    draft_revision: Revision
    entity: Entity
    candidate_sha256: Sha256
class ReviewReceipt(StrictModel):
    id: Id
    revision: Revision=1
    candidate: DraftCandidate
    structural: Literal['PASS','FAIL','NOT_RUN','BLOCKED']
    mathematical: Literal['APPROVED','REJECTED','NOT_RUN','NOT_APPLICABLE']
    sources: Literal['APPROVED','REJECTED','NOT_RUN','NOT_APPLICABLE']
    independent_pedagogy: Literal['PASS','FAIL','NOT_RUN','BLOCKED']
    reviewer: str
    created_at: UTC
    evidence_paths: list[str]
    decision_reason: str
class ApprovalDecision(StrictModel):
    operation_sha256: Sha256
    decision: Literal['approve_once','decline']
    expected_revision: Revision
class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: Id
    retryable: bool
    details: list[str]=Field(default_factory=list)
class ErrorEnvelope(StrictModel):
    error: ErrorDetail

class Warning(StrictModel):
    code: str
    message: str
    locator: str | None=None
    severity: Literal['info','warning','error']
class JobRef(StrictModel):
    id: Id
    status: Literal['queued','running','awaiting_approval','completed','failed','cancelled']
class MutationAck(StrictModel):
    id: Id
    revision: Revision
    applied: bool
class SelfAssessment(StrictModel):
    concept_id: Id
    level: Literal['not_learned','encountered','independent_use']
    origin: Literal['self_report']='self_report'
    updated_at: UTC
class LearnerProfile(StrictModel):
    workspace_id: Id
    revision: Revision
    goals: list[str]=Field(default_factory=list)
    goal_concept_ids: list[Id]=Field(default_factory=list)
    weekly_minutes: int=Field(default=120,ge=1,le=10080)
    language: str='zh-CN'
    preferred_difficulty: Literal['beginner','intermediate','advanced']='beginner'
    self_assessments: list[SelfAssessment]=Field(default_factory=list)
class SavedTab(StrictModel):
    id: Id
    context: ViewContext
    pinned: bool
    scroll_offset: float=Field(default=0,ge=0)
class WorkbenchSession(StrictModel):
    revision: Revision
    course_ref: ContentRef | None=None
    navigation: Literal['route','textbook','practice','assessment']='route'
    tabs: list[SavedTab]=Field(default_factory=list,max_length=100)
    active_tab_id: Id | None=None
    expanded_keys: list[str]=Field(default_factory=list,max_length=10000)
    directory_scroll: float=Field(default=0,ge=0)
    nav_width: int=Field(default=300,ge=260,le=360)
    agent_width: int=Field(default=368,ge=320,le=480)
    nav_collapsed: bool=False
    agent_collapsed: bool=False
class SearchSource(StrictModel):
    id: Id
    title: str
    url: str
    retrieved_at: UTC
    locator: str
    excerpt: str
    verification: Literal['verified','unverified']='unverified'
class EvidenceChunk(StrictModel):
    ref: ContentRef
    locator: str
    text: str=Field(max_length=12000)
class GenerationMessage(StrictModel):
    role: Literal['system','user','assistant']
    content: str
class GenerationInput(StrictModel):
    # Internal only; never returned by general browser/readback endpoints.
    snapshot_id: Id
    snapshot_sha256: Sha256
    messages: list[GenerationMessage]
    evidence: list[EvidenceChunk]
    max_input_tokens: int=Field(gt=0)
    max_output_tokens: int=Field(gt=0)
    consent_id: Id
    web_search: bool=False
class ProviderEvent(StrictModel):
    type: Literal['delta','citation','usage','search_executed','finished','error']
    text: str | None=None
    citation: Citation | None=None
    input_tokens: int | None=Field(default=None,ge=0)
    output_tokens: int | None=Field(default=None,ge=0)
    error_code: str | None=None

CONTRACTS={name: value for name,value in list(globals().items()) if isinstance(value,type) and issubclass(value,StrictModel) and value not in (StrictModel,Header)}
~~~
<!-- END FILE -->


# 附录 C：存储 DDL 与事务补充

下面可在临时SQLite数据库执行以检查关系形状。必须在每次连接打开并验证foreign_keys，WAL由数据库初始化器在文件数据库上设置。FTS内部shadow表不是额外产品模块。JSON列也必须按本文件强类型模型验证，SQL的json_valid只说明JSON可解析，不表示业务有效。正常API不能更新已发布revision/固定题解/提交快照；privacy purge是单独审批后的维护路径。

<!-- BEGIN FILE: migrations/0001_baseline.sql -->
~~~sql
-- PRODUCT_DESIGN v3.0.0 storage contract. SQLite JSON1 + FTS5 required.
-- These tables are a persistence design, not a running service or complete access-control system.
PRAGMA foreign_keys=ON;
CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL, checksum TEXT NOT NULL);
CREATE TABLE workspace(id TEXT PRIMARY KEY,title TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1),preferences_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(preferences_json)),created_at TEXT NOT NULL);
CREATE TABLE bootstrap_codes(code_hash TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),expires_at TEXT NOT NULL,used_at TEXT);
CREATE TABLE local_sessions(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),token_hash TEXT NOT NULL UNIQUE,csrf_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('learner','author')),expires_at TEXT NOT NULL,revoked_at TEXT);
CREATE TABLE content_blobs(sha256 TEXT PRIMARY KEY CHECK(length(sha256)=64),relative_path TEXT NOT NULL UNIQUE,size INTEGER NOT NULL CHECK(size>=0),created_at TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),blob_sha256 TEXT REFERENCES content_blobs(sha256),media_type TEXT NOT NULL,title TEXT NOT NULL,rights TEXT NOT NULL,parser_version TEXT,metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),created_at TEXT NOT NULL);
CREATE TABLE objects(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL CHECK(kind IN ('course','lesson','block','concept','route','question','practice_set','assessment','note')),current_revision INTEGER CHECK(current_revision>=1),lifecycle TEXT NOT NULL DEFAULT 'active' CHECK(lifecycle IN ('active','archived')));
CREATE TABLE revisions(object_id TEXT NOT NULL REFERENCES objects(id),revision INTEGER NOT NULL CHECK(revision>=1),sha256 TEXT NOT NULL CHECK(length(sha256)=64),metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),status TEXT NOT NULL DEFAULT 'published' CHECK(status='published'),created_at TEXT NOT NULL,PRIMARY KEY(object_id,revision),UNIQUE(object_id,revision,sha256));
CREATE TRIGGER revisions_no_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'published revision immutable'); END;
CREATE TRIGGER new_object_no_current BEFORE INSERT ON objects WHEN NEW.current_revision IS NOT NULL BEGIN SELECT RAISE(ABORT,'create object with null pointer before first published revision'); END;
CREATE TRIGGER valid_current_revision BEFORE UPDATE OF current_revision ON objects WHEN NEW.current_revision IS NOT NULL AND NOT EXISTS(SELECT 1 FROM revisions WHERE object_id=NEW.id AND revision=NEW.current_revision) BEGIN SELECT RAISE(ABORT,'current pointer must reference own published revision'); END;
CREATE TABLE object_dependencies(owner_id TEXT NOT NULL,owner_revision INTEGER NOT NULL,target_id TEXT NOT NULL,target_revision INTEGER NOT NULL,relation TEXT NOT NULL,PRIMARY KEY(owner_id,owner_revision,target_id,target_revision,relation),FOREIGN KEY(owner_id,owner_revision) REFERENCES revisions(object_id,revision),FOREIGN KEY(target_id,target_revision) REFERENCES revisions(object_id,revision));
CREATE TABLE block_bodies(block_id TEXT NOT NULL,block_revision INTEGER NOT NULL,body_sha256 TEXT NOT NULL REFERENCES content_blobs(sha256),PRIMARY KEY(block_id,block_revision),FOREIGN KEY(block_id,block_revision) REFERENCES revisions(object_id,revision));
CREATE TABLE concept_edges(course_id TEXT NOT NULL,course_revision INTEGER NOT NULL,prerequisite_id TEXT NOT NULL REFERENCES objects(id),dependent_id TEXT NOT NULL REFERENCES objects(id),CHECK(prerequisite_id<>dependent_id),PRIMARY KEY(course_id,course_revision,prerequisite_id,dependent_id),FOREIGN KEY(course_id,course_revision) REFERENCES revisions(object_id,revision));
CREATE TABLE route_steps(route_id TEXT NOT NULL,route_revision INTEGER NOT NULL,step_id TEXT NOT NULL,position INTEGER NOT NULL CHECK(position>=0),target_id TEXT NOT NULL,target_revision INTEGER NOT NULL,requires_json TEXT NOT NULL CHECK(json_valid(requires_json)),PRIMARY KEY(route_id,route_revision,step_id),UNIQUE(route_id,route_revision,position),FOREIGN KEY(route_id,route_revision) REFERENCES revisions(object_id,revision),FOREIGN KEY(target_id,target_revision) REFERENCES revisions(object_id,revision));
CREATE TABLE drafts(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>=1),base_ref_json TEXT CHECK(base_ref_json IS NULL OR json_valid(base_ref_json)),candidate_json TEXT NOT NULL CHECK(json_valid(candidate_json)),candidate_sha256 TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('draft','in_review','approved','needs_changes','published','cancelled')),updated_at TEXT NOT NULL);
CREATE TABLE reviews(id TEXT PRIMARY KEY,draft_id TEXT NOT NULL REFERENCES drafts(id),draft_revision INTEGER NOT NULL,candidate_sha256 TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>=1),receipt_json TEXT NOT NULL CHECK(json_valid(receipt_json)),reviewer_session_id TEXT REFERENCES local_sessions(id),created_at TEXT NOT NULL);
CREATE TABLE solutions(question_id TEXT NOT NULL,question_revision INTEGER NOT NULL,solution_revision INTEGER NOT NULL CHECK(solution_revision>=1),private_json TEXT NOT NULL CHECK(json_valid(private_json)),sha256 TEXT NOT NULL,review_status TEXT NOT NULL CHECK(review_status IN ('draft','needs_review','approved')),PRIMARY KEY(question_id,question_revision,solution_revision),FOREIGN KEY(question_id,question_revision) REFERENCES revisions(object_id,revision));
CREATE TRIGGER solution_no_update BEFORE UPDATE ON solutions BEGIN SELECT RAISE(ABORT,'create new solution revision'); END;
CREATE TABLE practice_sessions(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),practice_id TEXT NOT NULL,practice_revision INTEGER NOT NULL,question_refs_json TEXT NOT NULL CHECK(json_valid(question_refs_json)),solution_refs_json TEXT NOT NULL CHECK(json_valid(solution_refs_json)),status TEXT NOT NULL CHECK(status IN ('active','submitted','abandoned')),revision INTEGER NOT NULL CHECK(revision>=1),created_at TEXT NOT NULL,FOREIGN KEY(practice_id,practice_revision) REFERENCES revisions(object_id,revision));
CREATE TABLE practice_responses(session_id TEXT NOT NULL REFERENCES practice_sessions(id),question_id TEXT NOT NULL,answer_json TEXT NOT NULL CHECK(json_valid(answer_json)),updated_at TEXT NOT NULL,PRIMARY KEY(session_id,question_id));
CREATE TABLE attempts(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),assessment_id TEXT NOT NULL,assessment_revision INTEGER NOT NULL,mode TEXT NOT NULL CHECK(mode IN ('independent','assisted','open_book')),policy_json TEXT NOT NULL CHECK(json_valid(policy_json)),question_refs_json TEXT NOT NULL CHECK(json_valid(question_refs_json)),solution_refs_private_json TEXT NOT NULL CHECK(json_valid(solution_refs_private_json)),status TEXT NOT NULL CHECK(status IN ('active','submitted','grading','graded','needs_review','abandoned')),revision INTEGER NOT NULL CHECK(revision>=1),created_at TEXT NOT NULL,deadline_at TEXT,submitted_at TEXT,submit_reason TEXT CHECK(submit_reason IN ('user','deadline') OR submit_reason IS NULL),submitted_responses_json TEXT CHECK(submitted_responses_json IS NULL OR json_valid(submitted_responses_json)),FOREIGN KEY(assessment_id,assessment_revision) REFERENCES revisions(object_id,revision));
CREATE UNIQUE INDEX one_active_independent ON attempts(workspace_id) WHERE mode='independent' AND status='active';
CREATE TRIGGER immutable_attempt_policy BEFORE UPDATE OF mode,policy_json,question_refs_json,solution_refs_private_json,deadline_at ON attempts WHEN OLD.mode<>NEW.mode OR OLD.policy_json<>NEW.policy_json OR OLD.question_refs_json<>NEW.question_refs_json OR OLD.solution_refs_private_json<>NEW.solution_refs_private_json OR OLD.deadline_at IS NOT NEW.deadline_at BEGIN SELECT RAISE(ABORT,'assigned questions solutions and policy immutable'); END;
CREATE TRIGGER immutable_submission BEFORE UPDATE OF submitted_responses_json,submitted_at ON attempts WHEN OLD.status<>'active' AND (OLD.submitted_responses_json IS NOT NEW.submitted_responses_json OR OLD.submitted_at IS NOT NEW.submitted_at) BEGIN SELECT RAISE(ABORT,'submitted answers immutable'); END;
CREATE TABLE responses(attempt_id TEXT NOT NULL REFERENCES attempts(id),question_id TEXT NOT NULL,draft_revision INTEGER NOT NULL CHECK(draft_revision>=1),answer_json TEXT NOT NULL CHECK(json_valid(answer_json)),updated_at TEXT NOT NULL,PRIMARY KEY(attempt_id,question_id));
CREATE TRIGGER response_insert_only_active BEFORE INSERT ON responses WHEN NOT EXISTS(SELECT 1 FROM attempts WHERE id=NEW.attempt_id AND status='active') BEGIN SELECT RAISE(ABORT,'attempt not active'); END;
CREATE TRIGGER response_update_only_active BEFORE UPDATE ON responses WHEN NOT EXISTS(SELECT 1 FROM attempts WHERE id=OLD.attempt_id AND status='active') BEGIN SELECT RAISE(ABORT,'attempt not active'); END;
CREATE TABLE grades(attempt_id TEXT NOT NULL REFERENCES attempts(id),grading_revision INTEGER NOT NULL CHECK(grading_revision>=1),result_json TEXT NOT NULL CHECK(json_valid(result_json)),created_at TEXT NOT NULL,PRIMARY KEY(attempt_id,grading_revision));
CREATE TRIGGER grade_no_update BEFORE UPDATE ON grades BEGIN SELECT RAISE(ABORT,'create new grading revision'); END;
CREATE TABLE learning_events(event_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,origin TEXT NOT NULL CHECK(origin IN ('native','user_supplied_import')),payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),occurred_at TEXT NOT NULL);
CREATE TRIGGER event_no_update BEFORE UPDATE ON learning_events BEGIN SELECT RAISE(ABORT,'events append-only in normal operations'); END;
CREATE TABLE exposures(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),event_id TEXT NOT NULL UNIQUE REFERENCES learning_events(event_id),exposure_group TEXT NOT NULL,question_ref_json TEXT NOT NULL CHECK(json_valid(question_ref_json)),kind TEXT NOT NULL CHECK(kind IN ('hint','solution','prior_attempt','imported_claim')),occurred_at TEXT NOT NULL);
CREATE INDEX exposure_lookup ON exposures(workspace_id,exposure_group,occurred_at);
CREATE TABLE evidence(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),event_id TEXT NOT NULL REFERENCES learning_events(event_id),attempt_id TEXT REFERENCES attempts(id),grading_revision INTEGER,evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),freshness TEXT NOT NULL,UNIQUE(event_id,id),FOREIGN KEY(attempt_id,grading_revision) REFERENCES grades(attempt_id,grading_revision));
CREATE TABLE learning_progress(workspace_id TEXT PRIMARY KEY REFERENCES workspace(id),revision INTEGER NOT NULL CHECK(revision>=1),projection_json TEXT NOT NULL CHECK(json_valid(projection_json)),last_event_id TEXT REFERENCES learning_events(event_id));
CREATE TABLE learner_profiles(workspace_id TEXT PRIMARY KEY REFERENCES workspace(id),revision INTEGER NOT NULL CHECK(revision>=1),profile_json TEXT NOT NULL CHECK(json_valid(profile_json)),updated_at TEXT NOT NULL);
CREATE TABLE notes_index(note_id TEXT NOT NULL,note_revision INTEGER NOT NULL,workspace_id TEXT NOT NULL REFERENCES workspace(id),anchor_id TEXT NOT NULL,anchor_revision INTEGER NOT NULL,anchor_state TEXT NOT NULL CHECK(anchor_state IN ('exact','stale','unresolved')),PRIMARY KEY(note_id,note_revision),FOREIGN KEY(note_id,note_revision) REFERENCES revisions(object_id,revision),FOREIGN KEY(anchor_id,anchor_revision) REFERENCES revisions(object_id,revision));
CREATE TABLE recommendations(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),rule_version TEXT NOT NULL,snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),decision TEXT NOT NULL CHECK(decision IN ('pending','accepted','dismissed')),stale INTEGER NOT NULL DEFAULT 0 CHECK(stale IN (0,1)),created_at TEXT NOT NULL);
CREATE TABLE workbench_sessions(workspace_id TEXT PRIMARY KEY REFERENCES workspace(id),revision INTEGER NOT NULL CHECK(revision>=1),session_json TEXT NOT NULL CHECK(json_valid(session_json)),updated_at TEXT NOT NULL);
CREATE TABLE threads(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),scope_json TEXT NOT NULL CHECK(json_valid(scope_json)),title TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE context_snapshots(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),snapshot_sha256 TEXT NOT NULL,envelope_json TEXT NOT NULL CHECK(json_valid(envelope_json)),private_input_blob_sha256 TEXT REFERENCES content_blobs(sha256),created_at TEXT NOT NULL);
CREATE TABLE jobs(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('queued','running','awaiting_approval','completed','failed','cancelled')),revision INTEGER NOT NULL CHECK(revision>=1),input_sha256 TEXT NOT NULL,input_json TEXT NOT NULL CHECK(json_valid(input_json)),result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)),cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),retry_count INTEGER NOT NULL DEFAULT 0 CHECK(retry_count>=0),next_retry_at TEXT,lease_owner TEXT,lease_until TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE runs(id TEXT PRIMARY KEY REFERENCES jobs(id),thread_id TEXT NOT NULL REFERENCES threads(id),context_snapshot_id TEXT REFERENCES context_snapshots(id),snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)));
CREATE TABLE messages(id TEXT PRIMARY KEY,thread_id TEXT NOT NULL REFERENCES threads(id),role TEXT NOT NULL CHECK(role IN ('user','assistant')),context_snapshot_id TEXT REFERENCES context_snapshots(id),run_id TEXT REFERENCES runs(id),content_markdown TEXT NOT NULL,citations_json TEXT NOT NULL CHECK(json_valid(citations_json)),status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE job_events(job_id TEXT NOT NULL REFERENCES jobs(id),seq INTEGER NOT NULL CHECK(seq>0),type TEXT NOT NULL,payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),occurred_at TEXT NOT NULL,PRIMARY KEY(job_id,seq));
CREATE UNIQUE INDEX one_terminal_per_job ON job_events(job_id) WHERE type IN ('completed','failed','cancelled');
CREATE TABLE provider_configs(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),revision INTEGER NOT NULL CHECK(revision>=1),config_json TEXT NOT NULL CHECK(json_valid(config_json)),secret_store_locator TEXT,updated_at TEXT NOT NULL);
CREATE TABLE consents(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),provider_id TEXT NOT NULL REFERENCES provider_configs(id),revision INTEGER NOT NULL CHECK(revision>=1),scope_json TEXT NOT NULL CHECK(json_valid(scope_json)),status TEXT NOT NULL CHECK(status IN ('active','revoked','expired')),expires_at TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE approvals(id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),revision INTEGER NOT NULL CHECK(revision>=1),operation_sha256 TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','approved','declined','expired')),scope_json TEXT NOT NULL CHECK(json_valid(scope_json)),actor_session_id TEXT REFERENCES local_sessions(id),expires_at TEXT NOT NULL);
CREATE TABLE usage_records(id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),provider_id TEXT NOT NULL REFERENCES provider_configs(id),input_tokens INTEGER CHECK(input_tokens>=0),output_tokens INTEGER CHECK(output_tokens>=0),search_count INTEGER NOT NULL DEFAULT 0 CHECK(search_count>=0),estimated_cost TEXT,actual_cost TEXT,currency TEXT,created_at TEXT NOT NULL);
CREATE TABLE ingestion_imports(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),source_id TEXT NOT NULL REFERENCES sources(id),job_id TEXT NOT NULL REFERENCES jobs(id),input_sha256 TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('staged','parsing','preview_ready','committed','cancelled','failed')),preview_json TEXT CHECK(preview_json IS NULL OR json_valid(preview_json)),created_at TEXT NOT NULL);
CREATE TABLE artifacts(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),job_id TEXT REFERENCES jobs(id),blob_sha256 TEXT NOT NULL REFERENCES content_blobs(sha256),profile TEXT NOT NULL,manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),visibility TEXT NOT NULL CHECK(visibility IN ('learner','author_private','personal_private')),created_at TEXT NOT NULL);
CREATE TABLE proposals(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,operation_sha256 TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>=1),proposal_json TEXT NOT NULL CHECK(json_valid(proposal_json)),status TEXT NOT NULL CHECK(status IN ('preview','approved','applied','cancelled','failed')),created_at TEXT NOT NULL);
CREATE TABLE codex_sessions(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),revision INTEGER NOT NULL CHECK(revision>=1),sandbox_root_id TEXT NOT NULL,external_thread_id TEXT,adapter_version TEXT NOT NULL,status TEXT NOT NULL,metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)));
CREATE TABLE connectors(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),config_json TEXT NOT NULL CHECK(json_valid(config_json)),sync_cursor_json TEXT CHECK(sync_cursor_json IS NULL OR json_valid(sync_cursor_json)),last_sync TEXT);
CREATE TABLE feedback(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),created_at TEXT NOT NULL);
CREATE TABLE outbox(id TEXT PRIMARY KEY,event_type TEXT NOT NULL,payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),delivered_at TEXT,attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE idempotency(actor TEXT NOT NULL,route TEXT NOT NULL,key TEXT NOT NULL,request_sha256 TEXT NOT NULL,result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)),created_at TEXT NOT NULL,expires_at TEXT,PRIMARY KEY(actor,route,key));
CREATE TABLE indexes(id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL REFERENCES workspace(id),corpus_sha256 TEXT NOT NULL,index_version TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('ready','stale','building','missing')),manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),created_at TEXT NOT NULL);
CREATE VIRTUAL TABLE fts_chunks USING fts5(object_id UNINDEXED,revision UNINDEXED,workspace_id UNINDEXED,chunk_id UNINDEXED,tokens,body,tokenize='unicode61');
-- FTS tokens are application-presegmented Chinese; private solutions never enter this table.
-- Courses, lessons, concepts, routes and notes have one canonical metadata source in revisions;
-- projection/index tables must be rebuilt from that source, not become a second editable copy.
-- Application services additionally check workspace ownership, exact hashes, graph acyclicity,
-- reference entity kinds, assigned response question IDs, deadlines, policy, leases and consent.
-- Privacy purge is an explicit maintenance workflow; ordinary API routes cannot mass-delete rows.
~~~
<!-- END FILE -->


M5.1 以新的 forward migration 补 Provider 自有不可变配置/提案/授权与命令历史、私有准备绑定、唯一 dispatch/额度保留和严格终态回执。上面的原 baseline DDL 字节保持不变，不假装现有几列已经提供这些行为，也不修改已应用迁移。Provider 通过 source/Jobs/Policy/备份公开端口协调，不跨 owner SQL 写任务或学科内容。学习包与数据 schema_version 继续为3.0.0。

# 附录 D：模块端口

M5.3 Practice 模型帮助内部口：Tutor-owned read_answer_fact(transaction, workspace_id, run_id) 只返回受检元数据，不返回回答正文。闭合 TutorAnswerFact={workspace_id:Id,run_id:Id,context_snapshot_id:Id,practice:TutorPracticeBinding,event_seq:Revision,event_sha256:Sha256,text_sha256:Sha256,occurred_at:UTC}；event_seq 定位该 Run 首个 text.strip() 非空的持久 answer_delta，event_sha256 对该完整事件规范 JSON，text_sha256 对该段原文 UTF-8，occurred_at 为该原事件时间。非练习或未发生该事件返回 null；原 Run/Jobs/Thread/messages/事件关联与 hash 必须重新核验。

Practice-owned record_model_help(transaction, identity, run_id) 经上口、当前 Policy、真实 session/question 分配建立唯一 Run 帮助关联。闭合 ModelHelpReceipt={version:practice-model-help-v1,source:model,answer:TutorAnswerFact,event_id:Id,exposure_id:Id,exposure_group:Id,occurred_at:UTC}，最后时间为本次 exposure 持久化时间，与原 delta 时间分别保留。读回须同时核 Learning、exposure、Practice 分配与原 Tutor 事实；坏关联不能被忽略成 unassisted。旧独立证据帮助读取口须识别这一真实 model 来源，不将其猜为 ruleslevel；内部 level=0 仅指无 rules 级别。所有变更仍由所属模块事务口执行，失败回滚 Tutor 回答、帮助、事件与终态的同批写入。

本段规定依赖方向。AuthContext只能由可信会话构造；WriteContext不是用户可任意自报的角色。ProviderPort的输入包含正文摘录而不只是ref；外部ProviderEvent经应用映射为RunEvent，只有服务端可以建立终态和审批事件。泛型DTOMap的unknown用于约束适配器类型映射，不是允许HTTP运行接口返回任意unknown。

<!-- BEGIN FILE: packages/contracts/module-ports.ts -->
~~~typescript
/** Target dependency ports, not implemented adapters. Transport DTOs are generated
 * from generated JSON Schema during M0; here DTO maps are generic parameters
 * to avoid maintaining a second hand-written version of every domain type. */
export type Entity = 'course'|'lesson'|'block'|'concept'|'route'|'question'|'practice_set'|'assessment'|'note';
export interface ContentRef {entity: Entity; id: string; revision: number; sha256: string}
export interface AuthContext {workspaceId: string; actorId: string; role: 'learner'|'author'; sessionId: string}
export interface WriteContext extends AuthContext {idempotencyKey: string; expectedRevision?: number}
export interface DTOMap {
 Course: unknown; Lesson: unknown; ContentBlock: unknown; Route: unknown;
 QuestionPublic: unknown; PracticeSet: unknown; AttemptCreate: unknown; AttemptPublic: unknown;
 ResponsesWrite: unknown; GradingResult: unknown; TutorRequest: unknown; ContextSnapshot: unknown;
 RunSnapshot: unknown; RunEvent: unknown; Note: unknown; Evidence: unknown;
 Recommendation: unknown; AuthoringRequest: unknown; ReviewReceipt: unknown;
 GenerationInput: unknown; ProviderEvent: unknown; LearnerProfile: unknown; WorkbenchSession: unknown;
 ProviderCapabilities: unknown; ApprovalDecision: unknown; LearningEvent: unknown;
}
export interface Page<T> {items: T[]; next_cursor: string|null; total_hint?: number}
export interface JobRef {id: string; status: 'queued'|'running'|'awaiting_approval'|'completed'|'failed'|'cancelled'}
export interface ProposedAction {id: string; kind: 'generate'|'revise'|'export'; summary: string; operation_sha256: string}
export interface PolicyPort {
 check(context: AuthContext, action: string, refs: readonly ContentRef[]): Promise<void>;
 activeAssessment(context: AuthContext): Promise<{attemptId:string; mode:'independent'|'assisted'|'open_book'}|null>;
}
export interface IngestionPort {
 stage(ctx: WriteContext, file: {name:string; bytes:Uint8Array; mediaType:string}): Promise<JobRef>;
 preview(ctx: AuthContext, importId: string): Promise<{warnings: string[]; candidateIds: string[]; inputSha256:string}>;
 commit(ctx: WriteContext, importId: string, expectedInputSha256:string): Promise<ContentRef[]>;
}
export interface ContentPort<D extends DTOMap> {
 getCourse(ctx:AuthContext, ref:ContentRef):Promise<D['Course']>;
 getLesson(ctx:AuthContext, ref:ContentRef):Promise<D['Lesson']>;
 getBlock(ctx:AuthContext, ref:ContentRef):Promise<D['ContentBlock']>;
 createDraft(ctx:WriteContext, base:ContentRef|null):Promise<{draftId:string;revision:number}>;
 publish(ctx:WriteContext, candidate:DraftCandidate, receiptId:string):Promise<ContentRef>;
}
export interface RoutePort<D extends DTOMap> {
 save(ctx:WriteContext, route:D['Route']):Promise<ContentRef>;
 completeStep(ctx:WriteContext, route:ContentRef, stepId:string):Promise<void>;
}
export interface PracticePort<D extends DTOMap> {
 start(ctx:WriteContext, ref:ContentRef):Promise<{id:string;questions:D['QuestionPublic'][]}>;
 save(ctx:WriteContext, id:string, responses:D['ResponsesWrite']):Promise<number>;
 reveal(ctx:WriteContext, id:string, questionId:string, kind:'hint'|'solution'):Promise<{markdown:string;exposureEventId:string}>;
}
export interface AssessmentPort<D extends DTOMap> {
 start(ctx:WriteContext, request:D['AttemptCreate']):Promise<D['AttemptPublic']>;
 save(ctx:WriteContext, attemptId:string, responses:D['ResponsesWrite']):Promise<number>;
 submit(ctx:WriteContext, attemptId:string):Promise<D['AttemptPublic']>;
 result(ctx:AuthContext, attemptId:string):Promise<D['GradingResult']>;
}
export interface RetrievalHit {ref:ContentRef; text:string; locator:string; score:number}
export interface RetrievalPort {query(ctx:AuthContext, q:string, scope:ContentRef[], limit:number):Promise<RetrievalHit[]>}
export interface RetrievalApplicationDTOMap {
 RetrievalQueryWrite: unknown; RetrievalQueryView: unknown;
 RetrievalIndexRebuildWrite: unknown; RetrievalIndexStatusQuery: unknown;
 RetrievalIndexStatusView: unknown;
}
export interface RetrievalApplicationPort<R extends RetrievalApplicationDTOMap> {
 query(ctx:AuthContext, request:R['RetrievalQueryWrite']):Promise<R['RetrievalQueryView']>;
 indexStatus(ctx:AuthContext, request:R['RetrievalIndexStatusQuery']):Promise<R['RetrievalIndexStatusView']>;
 rebuild(ctx:WriteContext, request:R['RetrievalIndexRebuildWrite']):Promise<JobRef>;
}
export interface ContentRetrievalDTOMap {
 RetrievalScopeSnapshot: unknown; RetrievalBlockMaterial: unknown;
}
export interface ContentRetrievalPort<C extends ContentRetrievalDTOMap, Transaction> {
 resolveScope(transaction:Transaction, ctx:AuthContext, scope:readonly ContentRef[]):Promise<C['RetrievalScopeSnapshot']>;
 readMaterial(transaction:Transaction, ctx:AuthContext, scope:C['RetrievalScopeSnapshot'], ref:ContentRef):Promise<C['RetrievalBlockMaterial']>;
 revalidateScope(transaction:Transaction, ctx:AuthContext, scope:C['RetrievalScopeSnapshot']):Promise<void>;
}
export interface ContextPort<D extends DTOMap> {freeze(ctx:AuthContext, request:D['TutorRequest']):Promise<D['ContextSnapshot']>}
export interface TutorPort<D extends DTOMap> {
 start(ctx:WriteContext, request:D['TutorRequest']):Promise<D['RunSnapshot']>;
 events(ctx:AuthContext, runId:string, afterSeq:number, signal:AbortSignal):AsyncIterable<D['RunEvent']>;
 cancel(ctx:WriteContext, runId:string):Promise<D['RunSnapshot']>;
}
export interface TutorApplicationDTOMap {
 TutorThreadCreate: unknown; TutorThreadView: unknown; TutorPageQuery: unknown;
 TutorThreadPage: unknown; TutorMessagePage: unknown; TutorRunCreate: unknown;
 TutorRunView: unknown; TutorRunCancel: unknown; TutorRunControlView: unknown;
 TutorEventsQuery: unknown; TutorSSEEvent: unknown;
}
export interface TutorApplicationPort<T extends TutorApplicationDTOMap> {
 createThread(ctx:WriteContext, request:T['TutorThreadCreate']):Promise<T['TutorThreadView']>;
 threads(ctx:AuthContext, query:T['TutorPageQuery']):Promise<T['TutorThreadPage']>;
 messages(ctx:AuthContext, threadId:string, query:T['TutorPageQuery']):Promise<T['TutorMessagePage']>;
 start(ctx:WriteContext, request:T['TutorRunCreate']):Promise<T['TutorRunView']>;
 read(ctx:AuthContext, runId:string):Promise<T['TutorRunView']>;
 events(ctx:AuthContext, runId:string, query:T['TutorEventsQuery'], signal:AbortSignal):AsyncIterable<T['TutorSSEEvent']>;
 cancel(ctx:WriteContext, runId:string, request:T['TutorRunCancel']):Promise<T['TutorRunControlView']>;
}

export interface ProviderPort<D extends DTOMap> {
 capabilities():Promise<D['ProviderCapabilities']>;
 generate(input:D['GenerationInput'],signal:AbortSignal):AsyncIterable<D['ProviderEvent']>;
}
export interface ProviderApplicationDTOMap {
 ProviderCapabilitiesResponse: unknown; ProviderConfigWrite: unknown; ProviderConfigView: unknown;
 ProviderConfigAck: unknown; ProviderSecretWrite: unknown; ProviderSecretAck: unknown;
 ConsentPreviewWrite: unknown; ConsentProposalView: unknown; ConsentCreate: unknown;
 ConsentCreateAck: unknown; ConsentRevoke: unknown; ConsentPage: unknown; MutationAck: unknown;
}
export type ProviderConsentQuery = {consent_id:string;cursor?:never;limit?:never}
 | {consent_id?:never;cursor?:string;limit?:number};
export interface ProviderApplicationPort<P extends ProviderApplicationDTOMap> {
 capabilities(ctx:AuthContext):Promise<P['ProviderCapabilitiesResponse']>;
 readConfig(ctx:AuthContext, providerId:string):Promise<P['ProviderConfigView']>;
 saveConfig(ctx:WriteContext, providerId:string, request:P['ProviderConfigWrite']):Promise<P['ProviderConfigAck']>;
 saveSecret(ctx:WriteContext, providerId:string, request:P['ProviderSecretWrite']):Promise<P['ProviderSecretAck']>;
 deleteSecret(ctx:WriteContext, providerId:string, expectedConfigSha256:string):Promise<P['ProviderSecretAck']>;
 preview(ctx:WriteContext, request:P['ConsentPreviewWrite']):Promise<P['ConsentProposalView']>;
 proposal(ctx:AuthContext, proposalId:string):Promise<P['ConsentProposalView']>;
 grant(ctx:WriteContext, request:P['ConsentCreate']):Promise<P['ConsentCreateAck']>;
 consents(ctx:AuthContext, query:ProviderConsentQuery):Promise<P['ConsentPage']>;
 revoke(ctx:WriteContext, consentId:string, request:P['ConsentRevoke']):Promise<P['MutationAck']>;
}
export interface LearningPort<D extends DTOMap> {
 recordUserAction(ctx:WriteContext, action:'read_marked'|'note_created', ref:ContentRef):Promise<void>;
 evidence(ctx:AuthContext, conceptId:string):Promise<D['Evidence'][]>;
}
export interface RecommendationDTOMap {
 RecommendationPage: unknown; RecommendationDecisionWrite: unknown; MutationAck: unknown;
}
export interface RecommendationPort<R extends RecommendationDTOMap> {
 read(ctx:AuthContext, query:{courseId?:string;recommendationId?:string;cursor?:string;limit?:number}):Promise<R['RecommendationPage']>;
 decide(ctx:WriteContext, id:string, request:R['RecommendationDecisionWrite'], expectedDecisionSha256:string):Promise<R['MutationAck']>;
}
export interface NotesPort<D extends DTOMap> {save(ctx:WriteContext, note:D['Note']):Promise<ContentRef>}
export interface DraftCandidate {draft_id:string;draft_revision:number;entity:Entity;candidate_sha256:string}
export interface AuthoringApplicationDTOMap {
 AuthoringPrepareWrite:unknown; AuthoringJobPage:unknown; AuthoringJobView:unknown;
 AuthoringDraftView:unknown; NumericCheckPreviewWrite:unknown; NumericCheckView:unknown;
 NumericCheckDecisionAck:unknown; ApprovalDecision:unknown;
}
export interface AuthoringApplicationPort<A extends AuthoringApplicationDTOMap> {
 prepareJob(ctx:WriteContext,request:A['AuthoringPrepareWrite']):Promise<JobRef>;
 listJobs(ctx:AuthContext,query:{cursor?:string;limit?:number}):Promise<A['AuthoringJobPage']>;
 readJob(ctx:AuthContext,id:string):Promise<A['AuthoringJobView']>;
 readDraft(ctx:AuthContext,id:string):Promise<A['AuthoringDraftView']>;
 previewNumeric(ctx:WriteContext,draftId:string,request:A['NumericCheckPreviewWrite']):Promise<A['NumericCheckView']>;
 readNumeric(ctx:AuthContext,id:string):Promise<A['NumericCheckView']>;
 decideNumeric(ctx:WriteContext,id:string,request:A['ApprovalDecision']):Promise<A['NumericCheckDecisionAck']>;
}
export interface AuthoringPort<D extends DTOMap> {
 generate(ctx:WriteContext, request:D['AuthoringRequest']):Promise<JobRef>;
 review(ctx:WriteContext, candidate:DraftCandidate):Promise<D['ReviewReceipt']>;
}
export interface CodexBrokerPort<D extends DTOMap> {
 start(ctx:WriteContext, sandboxRootId:string):Promise<{sessionId:string}>;
 turn(ctx:WriteContext, sessionId:string, prompt:string):Promise<JobRef>;
 decide(ctx:WriteContext, approvalId:string, decision:D['ApprovalDecision']):Promise<void>;
 importArtifacts(ctx:WriteContext, jobId:string, approvedPaths:string[]):Promise<JobRef>;
}
export interface WorkspacePort {
 export(ctx:WriteContext, profile:'learner'|'author'|'full_backup'):Promise<JobRef>;
 restorePreview(ctx:WriteContext, backupSha256:string):Promise<{proposalId:string;warnings:string[]}>;
 restoreCommit(ctx:WriteContext, proposalId:string):Promise<JobRef>;
}
export interface ConnectorPort {
 preview(ctx:AuthContext):Promise<ProposedAction[]>;
 apply(ctx:WriteContext, approvedActionId:string, operationSha256:string):Promise<JobRef>;
}

export interface SearchPort {search(ctx:WriteContext, request:{query:string;consentId:string;maxSources:number}, signal:AbortSignal):Promise<{executed:boolean;sources:{id:string;url:string;title:string;retrievedAt:string;excerpt:string}[]}>}
export interface ProfilePort<D extends DTOMap> {read(ctx:AuthContext):Promise<D['LearnerProfile']>;save(ctx:WriteContext, profile:D['LearnerProfile']):Promise<D['LearnerProfile']>}
export interface WorkbenchSessionPort<D extends DTOMap> {read(ctx:AuthContext):Promise<D['WorkbenchSession']>;save(ctx:WriteContext, snapshot:D['WorkbenchSession']):Promise<D['WorkbenchSession']>}
~~~
<!-- END FILE -->



ProviderApplicationDTOMap 是独立应用映射，原 DTOMap/ProviderPort 不增删核心字段。每项绑定附录 A 的实际严格 Pydantic/OpenAPI DTO，运行生成类型使用单独 ProviderRuntimeDTOMap 名称。ConsentQuery 是严格 URL 参数组合，ProviderConsentQuery 连接实际已声明的标量 query 契约；它不假冒未注册的 OpenAPI body component，服务端仍需拒未知/重复字段并校验互斥。其余 map 项绑定真实命名请求/响应 schema；未注册 handler 不能产生虚假的运行 binding 或以 unknown/any 满足业务返回值。原 ProviderPort 是粗粒度兼容投影，不能绕过下面的 checked dispatch；GenerationInput 不是前端创建许可的 DTO。

RetrievalApplicationDTOMap/ContentRetrievalDTOMap 是M5.2独立应用映射，运行绑定使用实际命名DTO；原RetrievalPort/Hit保持粗粒度目标，不足以承载cold/资源/来源状态，不作为HTTP严格解码器。ContentRetrievalPort的Transaction在后端是调用方真实受控SQLite connection，AuthContext映射可信SessionIdentity，不接受浏览器事务ID或客户端角色。完整内部材料模型如下；真实handler注册后再生成绑定，不能以unknown/any伪装完成。

**M5.2 内部 Content 材料与索引代际（不是 HTTP 全文/文件入口）：** 以下闭合模型同样 required/拒额外字段。bytes只在受控本机内部传递，repr=False，不能写入普通日志或通过status/overview返回；Retrieval不直接读写Content/Provenance/Policy/Jobs所属SQL，调用其真实owner端口。

```text
RetrievalAlgorithmVersions = {
  resource: retrieval-resource-v1, normalization: nfc-v1,
  tokenizer: lexical-han-gram-v1, unicode: "15.0.0",
  ranking: scope-coverage-v1, locator: whole-block-v1
}
RetrievalRefState = {
  ref: ContentRef, current_ref: ContentRef, lifecycle: active | archived
}
RetrievalBlockDescriptor = {
  ref: ContentRef, title: string, body_sha256: Sha256,
  body_bytes: integer[0,16777216],
  provenance: RetrievalProvenance, source_descriptor_sha256: Sha256,
  parent_paths: RetrievalScopePath[1..8192]
}
RetrievalCorpusDescriptor = {
  version: retrieval-corpus-v1, workspace_id: Id,
  scope_sha256: Sha256, scope_refs: RetrievalScopeRefs,
  graph: RetrievalRefState[], blocks: RetrievalBlockDescriptor[1..512],
  versions: RetrievalAlgorithmVersions
}
RetrievalScopeSnapshot = {
  descriptor: RetrievalCorpusDescriptor, corpus_sha256: Sha256
}
RetrievalBlockMaterial = {
  scope_sha256: Sha256, corpus_sha256: Sha256,
  ref: ContentRef, body_sha256: Sha256, body: bytes
}
RetrievalIndexedBlock = {
  ref: ContentRef, body_sha256: Sha256, body_bytes: integer>=0,
  body_codepoints: integer>=0, chunk_id: Id,
  terms_sha256: Sha256, term_count: integer>=0
}
RetrievalIndexManifest = {
  version: retrieval-index-v1, index_version: Id,
  scope_sha256: Sha256, corpus_sha256: Sha256,
  descriptor: RetrievalCorpusDescriptor, built_at: UTC,
  blocks: RetrievalIndexedBlock[1..512]
}
RetrievalIndexJobInput = {
  version: retrieval-index-job-v1, workspace_id: Id,
  request_sha256: Sha256, scope_sha256: Sha256,
  expected_corpus_sha256: Sha256, descriptor: RetrievalCorpusDescriptor
}
RetrievalIndexJobResult = {
  scope_sha256: Sha256, corpus_sha256: Sha256,
  index_version: Id, manifest_sha256: Sha256,
  indexed_block_count: integer[1,512], indexed_term_count: integer>=0,
  built_at: UTC
}
```

corpus_sha256=SHA256(规范JSON descriptor)，scope_sha256依§20.7；source_descriptor_sha256=SHA256(规范JSON provenance)。graph包含roots、显式展开的全部中间lesson和block，按完整ref排序且无重复；每项current_ref和ref同entity/id，current pointer指向的元数据也通过Content完整性核验。blocks与graph中的block集合完全相同，body_bytes为登记size且总和≤16MiB；parent_paths完整、不跨roots，总数≤8192；公开元数据及provenance描述总预算依§20.7；完整descriptor实际规范JSON UTF-8还须≤16MiB，包括重复标题/来源/路径，展开和编码累计有界检查，超限整scope为413 SCOPE_BUDGET_EXCEEDED，不先无界构造再计数。归档/旧ref保留，不从current_ref再展开新子节点。descriptor使用的current_ref/lifecycle是当次读取事实，不能按块发布时旧值硬编码。

ContentRetrievalPort.resolveScope使用调用方真实活动SQLite事务，在当前身份/Policy下核精确图与安全来源描述后返回snapshot，无写入。readMaterial再次核scope及block成员身份，从public block-body登记经安全BlobStore读实际bytes/hash/size并返回绑定snapshot的材料；单有调用方组装的snapshot/hash不是权限。revalidateScope重算完整descriptor并核原hash；body实际核验另外由readMaterial承担，不把metadata CAS冒充字节验证。跨事务工作必须在最终交付/代际切换前重新核当前Policy与完整descriptor。

IndexManifest不把manifest_sha256包含在自身哈希输入；自有ledger存SHA256(规范JSON manifest)并严格回读校验。manifest.blocks与descriptor.blocks精确一一对应，无缺块/多块；body字段与实际owner材料相同，body_codepoints为严格UTF8解码长度。每个block只有一个完整块chunk；terms_sha256是词法算法生成、去重ASCII排序、单空格连接、无末尾空白的UTF8字节SHA。FTS和派生tokens/chunk必须与这份清单绑定，不以rowid或object_id/revision猜代际；chunk_id不是内容ref或访问令牌。terms为空仍保留该block的已核记录，成功代际indexed_term_count=各block.term_count之和；这个和为0叫indexed_empty，并非scope为空。scope非空/公开graph合法时不生成虚构零block成功代际。

Job input和result由真实Retrieval/Jobs owner同事务记录：input绑定完整规范命令、workspace、原scope/corpus与descriptor；result只在实际完整代际原子提交后出现，精确引用该index_version/manifest hash，不通过通用result_refs偷塞索引ID。租约、status revision、取消及唯一终态沿Jobs规则；相同scope同时最多一个未终态重建Job，新key请求在该scope已有未终态任务时409 INDEX_REBUILD_ACTIVE（原key合法回放先执行），不在旧Job里换输入。任务回读/cancel基准revision仍使用原GET/POST jobs契约。

生产实现用独立应用DTO生成绑定，不扩54 core；可新增所属模块迁移/自有清单与消费ledger，不改基线DDL或学习包3.0.0。Content publication通过Retrieval的自有失效意图接口在同事务通知，或提供逐消费者owner读取；Retrieval只修改自己的派生状态，不直接标其他模块事件“影响复核已完成”。正常查询/overview不新建材料/任务或修补坏历史。测试fixture可明确注入损坏/归档场景，不能把直接SQL fixture声称已实现正式归档/审核产品入口。


**内部准备、事件与持久回执（不作为普通 HTTP 请求/全文返回）：** 以下对象同样闭合且字段 required，nullable 显式 null，金额/计数采用附录 A 规则；GenerationMessage/EvidenceChunk/ContextSnapshot 是原 core 类型。

```text
PreparedOutboundMaterial = {
  job_id: Id, job_revision: Revision, job_input_sha256: Sha256,
  purpose: OutboundPurpose, context_snapshot: ContextSnapshot,
  messages: GenerationMessage[], evidence: EvidenceChunk[],
  preparation_version: nonempty string, prepared_input_sha256: Sha256
}
DispatchLease = {owner_id: Id, job_revision: Revision, expires_at: UTC}
UsageSnapshot = {input_tokens: integer >=0|null, output_tokens: integer >=0|null}
CheckedProviderDelta = {type: delta, channel: answer | refusal, text: nonempty raw string}
CheckedProviderUsage = {type: usage, input_tokens: integer >=0|null, output_tokens: integer >=0|null}
CheckedProviderFinished = {
  type: finished, outcome: complete | refused | incomplete,
  reason: output_limit | content_filter | provider_incomplete | null,
  output_state: none | partial | complete, usage: UsageSnapshot
}
CheckedProviderError = {
  type: error, error_code: ProviderFailureCode,
  provider_outcome: completed | failed | incomplete | cancelled | unknown,
  output_state: none | partial, usage: UsageSnapshot
}
CheckedProviderEvent = CheckedProviderDelta | CheckedProviderUsage
  | CheckedProviderFinished | CheckedProviderError
ProviderTerminalReceipt = {
  id: Id, workspace_id: Id, dispatch_id: Id, job_id: Id, consent_id: Id,
  proposal_id: Id, request_body_sha256: Sha256,
  terminal: CheckedProviderFinished | CheckedProviderError,
  answer_artifact_id: Id|null, refusal_artifact_id: Id|null,
  recorded_at: UTC, receipt_sha256: Sha256
}
```

PreparedOutboundMaterial.prepared_input_sha256 对应 §20.5 input_sha256。source owner 的 `read_prepared(transaction, AuthContext, job_id, expected_job_revision)`、`verify_prepared(transaction, AuthContext, material)`、`bind_authorization(transaction, WriteContext, job_id, prepared_input_sha256, consent_id)` 使用调用方真实活动数据库事务；后端 transaction 为现有受控 SQLite connection，不是浏览器自报 ID。read/verify 核源任务、当前可批准/运行阶段、完整准备输入、权限与精确 refs；bind 在该 owner 的表关联原输入与实际 consent。未知 source 不实现默认假材料。Job/Run 租约与业务终态由源 owner 控制；Provider 不直接写其表。

`CheckedDispatchPort.dispatch(AuthContext, job_id, consent_id, DispatchLease, AbortSignal)` 只收持久身份，不接 consumer 临时拼造的 GenerationInput；从自有冻结记录、source/Policy/Jobs 受检端口和秘密存储核实后才准备网络 envelope 与调用。它返回 CheckedProviderEvent 的异步序列；另有受权限约束的 `terminal(AuthContext, dispatch_id) -> ProviderTerminalReceipt|null` 回读自有原终态。内部 envelope 非授权凭证，任意手工构造类型不能跳过事务和账本核验。计数/协议 profile 注册仅接受实际校验过的完整输入证明，测试注册与生产隔离。

本机 InputProof/registry 是内部可信工程端口，不是配置或 HTTP 可提交的新授权 DTO。注册时对目的地绑定和 §20.5 的模型/格式/有效性依据作严格校验；`resolve(config)` 必须在无网络/秘密读取的情况下匹配规范化目的地、adapter、模型及当前有效 profile，`prepare/verify` 仍校验完整实际请求字节与冻结 proof SHA。不新增浏览器自报“可信 endpoint/模型版本/proof”的字段。测试专属任意端口服务只能在建立受控本机服务后，将其确切 endpoint 与人工模型规则显式注入测试工厂；该便利不能成为生产通配注册或环境变量准入开关。内部字段和实现可以细化，但不能遗漏这些实际匹配与失效判定。

ProviderTerminalReceipt.receipt_sha256 对 `{version:"provider-terminal-v1",...receipt_without_receipt_sha256}` 的项目规范 JSON 计算。receipt 绑定唯一 dispatch/原 proposal/request 字节，终态与私有 answer/refusal 部分产物引用在同一事务登记；产物字节先原子存储并核 hash，孤立文件可恢复清理。没有该通道文本时对应 artifact_id=null；有文本时 artifact 引用必须存在、完整且受当前 Policy 保护，不能因错误丢弃部分输出事实。原终态不更新/重复创建；正常运行之外的授权隐私删除走 §20.6。

CheckedProviderDelta.text 是原始文本片段，唯一的字符串长度要求是 >=1；纯空格、换行等合法非空片段必须原样保留，不 trim，不套用配置/摘要的 nonblank 规则。空字符串及 role-only 帧不生成 delta。此例外不改变其他 nonempty string 的非空白约束。

四类事件必要关联规则：usage 至少有一个真实非负数，代表本次累计快照；重复值不二次累加，已知字段不倒退、不被 null 擦除；终态 usage 始终存在并与最后已接受快照一致，缺失为 null，不虚构0。delta 的 answer/refusal 分通道；refusal 不混成普通核心 delta。complete 只用于已确认完整且非拒答的正常终态，reason=null，output_state=none或complete；refused 不代表正常回答成功，完整拒答可为complete，reason=null；incomplete 必须有非null reason，已有文本为partial、无文本为none，不能为complete。error 保留有协议事实支持的 provider_outcome，事实不足为unknown；本机取消不等于远端cancelled。远端completed后发现usage矛盾时，error仍保留provider_outcome=completed及partial文本，不伪改为远端failed。

Responses output_text.delta/Chat delta.content 映射 answer；合法空/role-only 帧不造空delta。明确 refusal 分通道；Responses completed/Chat stop且完整流结束结合拒答判断complete/refused；Responses incomplete/Chat length或content_filter以output_limit/content_filter/provider_incomplete结束；Responses failed为受检error。错实例/异常索引、未授权工具/引用/搜索结构、损坏JSON、未终态EOF、超时/取消等拒绝成功投影，不把链接文本当已验证引用。Chat记录choice结束后仍读usage和[DONE]；Responses text.done不等于整个请求完成。实际已收到的冲突在提交前判错。一次实例至多一个本地终结事件；终结后停止消费，不再发第二个finished/error；若能观察到额外帧，只记录安全协议违规并拒绝接纳，不改已提交终态，也不声称核验了未来未收数据。

自有终态持久化后，只有内部complete可投影核心finished；refused/incomplete投影核心error（PROVIDER_REFUSAL/PROVIDER_INCOMPLETE），其详细终态/partial/usage从受检回执读取，不能塞进text/error_code。消费方即使收到核心finished也要核自有回执并完成自己结果事务，才能设置本机completed。Provider-owned备份降权端口按§20.4在副本中保留可校验历史、移除秘密/locator并使许可不可派发；Workspace通过端口使用，不直接篡改Provider不可变账本。

**M5.3 owner协作与受检结果：** 原DTOMap/ContextPort/TutorPort和54 core不变；HTTP用新增TutorApplicationDTOMap/Port。仅真实handler注册后生成runtime binding及SSE transport，不能把未注册DTO冒充OpenAPI能力。以下内部模型同样闭合：

```text
TutorFrozenHistoryItem = {
  message_id: Id, source_run_id: Id, role: user|assistant,
  content_markdown: string, content_sha256: Sha256
}
TutorJobInput = {
  version: tutor-job-v1, workspace_id: Id, run_id: Id,
  request: TutorRunCreate, history: TutorFrozenHistoryItem[0..4]
}
PreparedTutorContext = {
  version: tutor-context-v1, run_id: Id, snapshot: ContextSnapshot,
  binding: TutorContextBinding, template_version: nonblank string,
  messages: GenerationMessage[2..6], evidence: EvidenceChunk[0..8],
  included: TutorInputMaterial[], history_message_ids: Id[0..4],
  omissions: TutorContextOmission[], warnings: Warning[]
}
CheckedProviderArtifact = {
  id: Id, channel: answer|refusal, text: nonempty raw string,
  utf8_bytes: integer>=1, sha256: Sha256
}
CheckedProviderResult = {
  receipt: ProviderTerminalReceipt,
  answer: CheckedProviderArtifact|null, refusal: CheckedProviderArtifact|null
}
```

TutorJobInput是Jobs不可变输入，规范JSON SHA即job_input_sha256；history由owner创建事务从真实已完成消息冻结，不信任浏览器历史，content_sha256为原UTF-8字节SHA。Context的 `prepare(transaction, AuthContext, TutorJobInput) -> PreparedTutorContext` 和 `verify(transaction, AuthContext, PreparedTutorContext) -> None` 使用调用方真实SQLite事务；Context写/核自有冻结记录，经owner端口读材料，不跨表读私题解。snapshot.request_sha256=SHA256(规范JSON TutorRunCreate)；snapshot.snapshot_sha256=SHA256(规范JSON PreparedTutorContext，唯一排除snapshot.snapshot_sha256字段)。调用方自报hash不能代替真实持久记录/Policy/材料核验。PreparedOutboundMaterial取同一Context/messages/evidence、实际job input SHA与当前revision；prepared_input_sha256仍依§20.5。变化/损坏明确拒绝或另建新任务/授权，不在原授权里暗换文本。

OutboundSourcePort新增 `record_proposal(transaction, AuthContext, job_id, prepared_input_sha256, proposal_id) -> None`，由Provider preview成功事务调用，源owner核真实绑定并记录，同proposal不重事件。原bind_authorization负责同源同输入衔接，verify_dispatch继续核实际租约/Policy。新增 `verify_output(transaction, AuthContext, job_id, dispatch_id) -> None` 核真实源上下文与当前输出许可，不要求历史lease活动或consent仍active，不因无关provider配置改变丢原结果。仅Provider在核真实job/consent/dispatch后调用，非任意artifact许可，不放宽通用private_artifact。

Provider-owned `read_result(transaction, AuthContext, job_id, consent_id) -> CheckedProviderResult|null` 定位真实源/唯一dispatch，先核归属、自有历史、源verify_output，再核receipt SHA、原请求/授权关联、artifact membership/通道/实际UTF-8字节/size/SHA。null仅确无终态；已登记产物缺失/损坏拒绝，不造空答案。零外发/零重复dispatch，不接文件/URL/任意artifact，不向浏览器暴露路径。原terminal对已注册source使用同一源专属输出许可，其他private_artifact保护不变。Provider只写自己的dispatch/receipt/artifact，Tutor只经此端口消费原answer/refusal，不从粗粒度finished或恢复流猜正文。 内部停止/恢复另可用 `read_control_result(transaction, AuthContext, job_id, consent_id) -> ProviderTerminalReceipt|null`：核真实工作区、Jobs、许可/dispatch/receipt关联，仅返回已核终态元数据、不返回artifact正文；学科失权时仍可保留实际远端事实并结束本机任务。该口不向浏览器新增接口、不解除正文读取权限。

Tutor/Jobs owner管claim/lease/cancel/唯一终态/命令回执；Context/Provider各经自己端口参与调用方事务。新增所属迁移，不改0001。租约公平性、事件读取批量/合并的普通工程细节用ADR，不另造规范。验收分开真实SQLite/受控适配器完整链、浏览器恢复/权限/停止、生产proof/费用调用是否实跑；缺生产证明/本次费用授权标NOT_RUN，不把测试注册当生产能力。

**M6.1 首切片内部协作：** AuthoringApplicationDTOMap 绑定附录 A 的实际命名应用DTO，运行生成独立 AuthoringRuntimeDTOMap；旧 AuthoringPort.generate(core AuthoringRequest) 只是已授权的粗粒度目标，不作为首次HTTP创建或绕过新source准入。review/publish 的未发布输入纠正为 DraftCandidate，不再用尚不存在的ContentRef；这是已有§20.1语义的对齐，M6.2未实现时仍不得注册假handler。ImportDraftSnapshot 保持原绑定，新增 Authoring 读取不冒充旧Import读口。54 core与0001字节不改。

```text
AuthoringJobInput = {version:authoring-job-v1,workspace_id:Id,job_id:Id,request:AuthoringPrepareWrite}
PreparedAuthoringContext = {
  version:authoring-context-v1,job_id:Id,snapshot:ContextSnapshot,
  template_version:nonblank string,messages:GenerationMessage[2],evidence:EvidenceChunk[0..8],
  materials:AuthoringInputMaterial[0..8],warnings:Warning[]
}
AuthoringCandidateRecord = {
  version:authoring-candidate-v1,workspace_id:Id,candidate:DraftCandidate(entity=block),
  source_job_id:Id,provider_receipt_id:Id,payload:WorkedExamplePayload,
  body_sha256:Sha256,validation:AuthoringValidation,created_at:UTC
}
NumericJobInput = {
  version:authoring-numeric-job-v1,workspace_id:Id,job_id:Id,check_id:Id,
  operation_sha256:Sha256,candidate:DraftCandidate(entity=block),plan:NumericPlan,runtime:NumericRuntimeProfile
}
```

以上内部对象仍全部required/闭合，messages/evidence/正文禁止普通repr/log。Job input SHA对实际规范JSON；准备 snapshot.policy=authoring，request_sha256对原 AuthoringPrepareWrite，snapshot_sha256对完整PreparedAuthoringContext唯一排除snapshot.snapshot_sha256；character_count与Provider包装后实际计数相同。prepared_input_sha256仍依§20.5，不能套用Tutor完整context哈希或仅哈希core snapshot。candidate_sha256对WorkedExamplePayload；AuthoringCandidateRecord另保存完整记录SHA并核其所有关联。numeric Job input、批准操作和结果完整关联，不凭自洽JSON+新SHA替代真实历史核验。

Authoring owner 的 prepare_context/verify_context/read_context 使用调用方真实SQLite事务，在自己的准备表保存/核验；Content经现有ContentRetrievalSource.resolve_scope/read_material/revalidate_scope的public块端口提供真实refs/bytes/provenance，无需先建检索索引、无访问私题解。其source实现已有OutboundSourcePort的全部真实方法（含reference_summaries/record_proposal/bind_authorization/verify_dispatch/verify_output），只注册Jobs.kind=authoring；numeric_check不是外发source。Provider按原checked dispatch/read_result/read_control_result读口交付自身受检终态/产物，Authoring不直接查Provider SQL或读取任意artifact文件。新source结果许可必须核作者来源/同job/context/current Policy，不能普遍放宽private_artifact。

Jobs-owned适配器提供两种kind的真实JobSnapshot和原cancel，所有命令回执绑定原route/body/key/actor/workspace，cancel终态no-op和旧ACK规则沿现有Jobs契约。生成完整候选事务与数值检查终态事务各自原子，不把数值等待挂在已完成生成Job上。新迁移只改所属新表/注册，不改0001和已有import记录。隔离runner为Quality/数值owner的 typed run(NumericJobInput, cancellation)->受检执行结果；实际runtime清单与operation一致、stdin/输出有界、进程启动与结束证据由该owner取得，不信任模型自报退出码。数值审批/开始/终态/结果与候选membership全回读校验；出现损坏failclosed，无GET修复。工具链固定与资源限制实现、lease公平性、错误分类等工程细化可写ADR，不扩大本节语言能力或改变审核语义。

# 附录 E：确定性样例生成器

从前面的核心模型生成作者/学习者两类learnpack、路线路径与TutorRequest。样例只含合成数据，使用固定日期以保证复现；真实时间和学习记录不得照抄。质量回执和题解初始needs_review/NOT_RUN不是假造审核；要投放给真实学习者评分，必须经过正常审核。相同题已在练习出现会被识别为暴露，不能用于声称新颖独立迁移。

先抽取附录B和本脚本，再运行 `python scripts/generate_fixtures.py`。预期输出在 fixtures/synthetic；脚本不联网、不读凭据、不访问旧仓库。

<!-- BEGIN FILE: scripts/generate_fixtures.py -->
~~~python
"""Generate synthetic, hash-valid author/learner packages from the embedded contracts.
Run after extracting domain_models.py to packages/contracts/. Does not access network.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages'/'contracts'))
import domain_models as dm
NOW='2026-09-14T00:00:00Z' # deterministic fixture timestamp, not a claim about user activity

def canonical(value):
    if hasattr(value,'model_dump'): value=value.model_dump(mode='json')
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(data): return hashlib.sha256(data).hexdigest()
def safe_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data: raise RuntimeError(f'fixture differs, refusing overwrite: {path}')
    path.write_bytes(data)
def generate(destination:Path):
    # Models, not handwritten hash placeholders, produce the frozen object identities.
    payloads={}
    def text(path,value):
        data=value.encode('utf-8');payloads[path]=data;return sha(data)
    def put(path,obj):
        data=canonical(obj);payloads[path]=data
        return dm.ContentRef(entity=obj.entity,id=obj.id,revision=obj.revision,sha256=sha(data))
    concept=dm.Concept(id='concept_ols',revision=1,title='一维最小二乘',skill_dimensions=['compute','derive'])
    cref=dm.ContentRef(entity='concept',id=concept.id,revision=concept.revision,sha256=sha(canonical(concept)))
    body=r'''# 一维最小二乘的完整小例题

目标：在 $y_i=h_i\theta+e_i$ 中由已知 $h_i,y_i$ 估计实参数 $\theta$。
给定 $h=(1,2)$、$y=(2,4)$，使用损失 $L(\theta)=\sum_{i=1}^{2}(y_i-h_i\theta)^2$。
展开：$L(\theta)=(2-\theta)^2+(4-2\theta)^2=20-20\theta+5\theta^2$。
配方：$L(\theta)=5(\theta-2)^2$，因为实数平方非负，最小值在 $\hat\theta=2$ 唯一达到。
检查：$A=\sum h_i^2=5>0$，$B=\sum h_i y_i=10$，$B/A=2$。
边界：若所有 $h_i=0$，则损失与 $\theta$ 无关，不能宣称唯一估计。
小结：正的 $A$ 保证这个二次目标有唯一最小点；这不自动证明任意噪声下统计最优。
'''
    bh=text('content/block_ols.r1.md',body)
    block=dm.ContentBlock(id='block_ols',revision=1,kind='worked_example',title='含观测模型、逐步计算与边界检查的例题',body_path='content/block_ols.r1.md',body_sha256=bh,concepts=['concept_ols'])
    bref=put('blocks/block_ols.r1.json',block)
    lesson=dm.Lesson(id='lesson_ols',revision=1,title='从观测模型到最小二乘：一维参数的计算与唯一性',objectives=['逐步计算A、B和参数估计','检查唯一性条件'],block_refs=[bref])
    lref=put('lessons/lesson_ols.r1.json',lesson)
    qs=[dm.QuestionPublic(id='question_choice',revision=1,kind='single_choice',stem_markdown='以上例题中A是多少？',choices=[dm.Choice(id='opt_a',text_markdown='3'),dm.Choice(id='opt_b',text_markdown='5')],concept_ids=['concept_ols'],skill='compute',exposure_group='group_ols_A',input_instructions='选择一个选项'),
        dm.QuestionPublic(id='question_numeric',revision=1,kind='numeric',stem_markdown='以上例题中的B是多少？',concept_ids=['concept_ols'],skill='compute',exposure_group='group_ols_B',input_instructions='填写有限实数，无单位'),
        dm.QuestionPublic(id='question_calculation',revision=1,kind='calculation',stem_markdown='计算以上例题的参数估计并写出配方步骤。',concept_ids=['concept_ols'],skill='compute',exposure_group='group_ols_theta',input_instructions='填写最终值，步骤另存；本fixture自动评分仅对应最终数值')]
    qrefs=[dm.ContentRef(entity='question',id=q.id,revision=q.revision,sha256=sha(canonical(q))) for q in qs]
    payloads['questions/public.jsonl']=b''.join(canonical(q)+b'\n' for q in qs)
    solutions=[]
    for i,(qref,answer) in enumerate(zip(qrefs,['opt_b','10','2'])):
        sol=dm.SolutionPrivate(id=f'solution_{i}',revision=1,question_ref=qref,grading_kind='choice_exact' if i==0 else 'numeric_tolerance',accepted_answers=[answer],absolute_tolerance=0.0,relative_tolerance=0.0,solution_markdown='请参照本节逐步计算；此为合成测试材料，不代表已经人工审校。',review_status='needs_review')
        solutions.append(sol)
    payloads['private/solutions.jsonl']=b''.join(canonical(s)+b'\n' for s in solutions)
    practice=dm.PracticeSet(id='practice_ols',revision=1,title='A、B与参数估计练习',lesson_ref=lref,question_refs=qrefs)
    pref=put('practice/practice_ols.r1.json',practice)
    assessment=dm.AssessmentBlueprint(id='assessment_ols',revision=1,title='计算诊断（合成样例）',question_refs=qrefs,allowed_modes=['independent','assisted','open_book'])
    aref=put('assessments/assessment_ols.r1.json',assessment)
    course=dm.Course(id='course_ols',revision=1,title='一维含噪声参数估计：公式、计算、先修关系与独立作答',audience='自学者',lesson_refs=[lref],concept_refs=[cref],sections=[dm.CourseSection(id='section_one',title='第1章 观测与最小二乘',lesson_ids=[lesson.id])],objectives=['理解目标函数','完成确定性计算'])
    course_ref=put('course.json',course)
    payloads['concepts.json']=canonical([concept.model_dump(mode='json')])
    symbol=dm.Symbol(id='symbol_theta',tex=r'\theta',meaning='待估计标量参数',domain=r'\mathbb{R}',dimension='1',scope=course.id,first_definition=bref)
    payloads['symbols.json']=canonical([symbol.model_dump(mode='json')])
    payloads['sources/citations.json']=canonical([])
    payloads['checks/quality-receipt.json']=canonical({'schema_version':'3.0.0','fixture_only':True,'mathematical':'NOT_RUN','sources':'NOT_RUN','independent_pedagogy':'NOT_RUN','note':'Schema验证不是内容审核；禁止把本回执当作发布批准'})
    route=dm.Route(id='route_ols',revision=1,title='计算入门路线',goal='阅读、练习、自测',steps=[dm.RouteStep(id='step_read',title='阅读例题',target=lref,completion_rule='read'),dm.RouteStep(id='step_practice',title='练习',target=pref,requires_steps=['step_read'],completion_rule='practice_submitted'),dm.RouteStep(id='step_test',title='诊断',target=aref,requires_steps=['step_practice'],completion_rule='assessment_submitted')])
    safe_write(destination/'route.json',canonical(route))
    for profile in ['author','learner']:
        selected={k:v for k,v in payloads.items() if profile=='author' or not k.startswith('private/')}
        folder=destination/f'course-{profile}'
        entries=[]
        for path,data in sorted(selected.items()):
            media='text/markdown' if path.endswith('.md') else 'application/x-ndjson' if path.endswith('.jsonl') else 'application/json'
            entry=dm.FileEntry(path=path,size=len(data),sha256=sha(data),media_type=media,visibility='author_private' if path.startswith('private/') else 'learner')
            entries.append(entry);safe_write(folder/path,data)
        manifest=dm.Manifest(package_id=f'package_{profile}',profile=profile,created_at=NOW,files=entries)
        safe_write(folder/'manifest.json',canonical(manifest))
        # Files have deterministic bytes; ZIP header timestamps are also deterministic.
        zpath=destination/f'course-{profile}.learnpack.zip'
        if zpath.exists(): zpath.unlink() # only synthetic generated archive under destination
        with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(folder.rglob('*')):
                if f.is_file():
                    info=zipfile.ZipInfo(str(f.relative_to(folder)),date_time=(2026,9,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    z.writestr(info,f.read_bytes())
    request=dm.TutorRequest(thread_id='thread_ols',workspace_id='workspace_local',message='为什么A必须严格大于零？',intent='derive',context=dm.ViewContext(view_kind='lesson',active_ref=lref),web_search=False)
    safe_write(destination/'tutor-request.json',canonical(request))
    safe_write(destination/'fixture-summary.json',canonical({'course_ref':course_ref.model_dump(mode='json'),'question_count':len(qs),'fixture_only':True}))
    return destination
if __name__=='__main__':
    print(generate(ROOT/'fixtures'/'synthetic'))
~~~
<!-- END FILE -->


# 附录 F：目标验收场景

这些是未来产品的目标，不是本文件发布时已经执行通过的测试。所有场景需要step definitions和对应真实业务实现；Gherkin语法存在不能标记软件PASS。R-01—R-38由第2章追踪，M0生成可机读映射并检查每个需求至少关联一个验收场景。

<!-- BEGIN FILE: tests/acceptance/core.feature -->
~~~gherkin
# language: zh-CN
# Target scenarios. Step definitions must be implemented; these are NOT executed product tests.
功能: Learning Workbench 正式版端到端验收

  @AC-01 @M1 @R-01 @R-02 @R-03
  场景: 三栏和固定导航
    假如 新工作区且桌面宽度 1440
    当 打开平台并依次切换四个学习入口
    那么 左侧顺序为学习路线、教材、习题、测试题；中央显示内容且右侧始终有 Agent

  @AC-02 @M1 @R-03 @R-28
  场景: 键盘与窄屏
    假如 桌面分隔条获得键盘焦点
    当 按左右箭头、折叠恢复并在 390/900/1440/1920px 打开
    那么 宽度有界可调整、焦点可达、无页面横向溢出、抽屉可关闭

  @AC-03 @M1 @R-16
  场景: 异步回复不串章
    假如 章节 A 请求已发送而尚未响应
    当 切到章节 B 并输入草稿后 A 请求完成
    那么 回复只归 A 的 thread 和发送快照；B 草稿和当前上下文不变

  @AC-04 @M2 @R-06 @R-07
  场景: 导入必须确认
    假如 一个包含 script、事件属性和外部主动资源的 HTML
    当 导入、预览、取消
    那么 脚本不执行；警告可见；正式库没有新增教材

  @AC-05 @M2 @R-07 @R-26
  场景: 学习包完整性
    假如 作者包和学习者包的确定性 fixture
    当 导入含 ../、重复路径、哈希错或 private 文件的学习者包
    那么 逐个拒绝并保留原有数据库；合法包完成全部哈希复核

  @AC-06 @M2 @R-08 @R-09
  场景: 低保真文件不静默通过
    假如 包含图片公式和双栏文本的 PDF/DOCX fixture
    当 执行文本解析
    那么 原件保留；无法恢复 LaTeX 的区域显示诊断而不是编造公式

  @AC-07 @M2 @R-04 @R-09 @R-10
  场景: 例题归教材
    假如 一个定义、证明和例题块均有精确引用的章节
    当 打开例题深链接并渲染长 LaTeX 公式
    那么 中央仍为教材阅读；定位到例题块；公式局部可滚动

  @AC-08 @M2 @R-19 @R-26
  场景: 原生持久化回读
    假如 服务端已保存笔记、阅读位置和版本
    当 关闭浏览器、重启后端，再重新打开
    那么 使用原生数据库和浏览器回读相同引用；无内存替身

  @AC-09 @M3 @R-11 @R-25
  场景: 练习默认折叠与暴露
    假如 习题会话尚未查看答案
    当 先保存草稿，刷新，再点击解答
    那么 草稿恢复；答案默认不展开；显示答案同时记录 solution_revealed 事件

  @AC-10 @M3 @R-12
  场景: 确定性评分
    假如 选择、文本填空、数值与单位样例含正反答案
    当 提交标准值、容差边界、NaN、Infinity、超长或代码表达式
    那么 按声明规则判分；非有限数和可执行表达式拒绝；未支持推导为 needs_review

  @AC-11 @M3 @R-13 @R-14 @R-25
  场景: 服务端跨标签测试策略
    假如 工作区有活跃独立测试
    当 从另一个标签或直接 API 请求 Tutor、RAG 或私有解答
    那么 返回 ASSESSMENT_ACTIVE/POLICY_DENIED；只允许操作帮助；无工具调用和泄题

  @AC-12 @M3 @R-12 @R-13
  场景: 测试草稿与交卷幂等
    假如 测试草稿 revision 为 3
    当 旧 revision 写入，然后相同幂等键交卷两次并用同键换载荷
    那么 旧写入 412；重复提交返回同一结果；换载荷 409；评分任务只创建一次

  @AC-13 @M3 @R-14 @R-20
  场景: 交卷后复盘
    假如 独立测试已交卷并产生错误题
    当 打开结果和右侧 Agent
    那么 只在策略允许后返回解答；Agent 恢复学科解释；错题链接指向准确教材修订

  @AC-14 @M4 @R-05 @R-19 @R-20
  场景: 进度不冒充掌握
    假如 用户自报熟悉并读完章节但没有独立作答
    当 刷新学习画像和推荐
    那么 阅读完成与未诊断同时存在；推荐有理由，不显示未经校准的掌握概率

  @AC-15 @M4 @R-13 @R-20
  场景: 同源题与辅助证据
    假如 练习中看过解答，随后测试出现同 exposure_group
    当 完成测试并计算证据
    那么 成绩保留，但该项标记重复/辅助暴露；不能冒充新颖独立迁移证据

  @AC-16 @M5 @R-17 @R-18
  场景: 真实能力与授权
    假如 未授权提供商或只支持 chat 的兼容提供商
    当 请求真实生成或联网搜索
    那么 无授权或无完整输入计量证明均零传输；无搜索能力返回 CAPABILITY_UNSUPPORTED；配置/秘密存在不冒充可调度；不标已联网

  @AC-17 @M5 @R-15 @R-16 @R-25
  场景: 精确上下文与不可信资料
    假如 选文绑定某修订，资料包含要求读取私钥的文本
    当 组装提示与检索
    那么 只读取允许的精确 refs；服务端冻结真实材料、完整请求字节和许可；不执行资料中的命令；隐藏解答不进入上下文

  @AC-18 @M5 @R-18 @R-27
  场景: SSE 重连与取消
    假如 真实或受控模拟 run 已生成事件 seq 1..8
    当 断线后带 Last-Event-ID 重连并取消
    那么 回读缺失事件、不重新生成；只产生一个终态；实际搜索状态可复核

  @AC-19 @M6 @R-21 @R-22 @R-24
  场景: 生成审核与发布
    假如 生成教材或题目完成但数学审校未运行
    当 尝试自动发布并随后人工审核发布新修订
    那么 自动发布拒绝；批准绑定内容哈希；旧修订不覆盖

  @AC-20 @M6 @R-21 @R-24
  场景: 修订影响追踪
    假如 旧教材修订关联笔记、题目、例题输出和来源
    当 发布修改条件或公式的新修订
    那么 受影响对象列出；旧证据不删除；笔记 stale；重新审核不伪造通过

  @AC-21 @M6 @R-23
  场景: Codex 操作批准
    假如 受控 Codex 会话请求命令执行与文件修改
    当 用户拒绝审批或产物路径逃出沙盒
    那么 操作不执行；越界产物不回导；批准合法成果也只进入草稿

  @AC-22 @M7 @R-26 @R-27 @R-29
  场景: 恢复与故障注入
    假如 完整备份含所有必要对象且校验通过
    当 恢复期间模拟崩溃或文件写失败
    那么 原工作区可恢复；不出现已提交数据库引用缺失文件；密钥不进入备份

  @AC-23 @M7 @R-28 @R-29
  场景: 验收分层
    假如 模拟接口全部通过，真实 LLM 或独立学习评测未运行
    当 生成发行回执
    那么 模拟 PASS、真实 NOT_RUN、教学 NOT_RUN 分列，不宣称全功能全质量通过

  @AC-24 @E1 @R-30 @R-31 @R-32
  场景: 连接器与标准扩展
    假如 Zotero/博客/QTI-LTI 尚无真实授权和测试
    当 执行预览或能力检查
    那么 只报告预览/未验收；没有用户批准不远端写入，不宣称标准兼容


  @AC-25 @M1 @R-33
  场景: 课程平台式左栏
    假如 合成课程包含八章和不同长度的中文小节标题
    当 依次选择四项入口、折叠章节、搜索目录、清除搜索并刷新
    那么 课程摘要与四入口保持固定；下方只有一个上下文目录；当前项可定位；标题可读且展开滚动状态恢复

  @AC-26 @M1 @R-33 @R-28
  场景: 真实视觉修正
    假如 已启动实际前后端并载入仅含合成内容的课程
    当 在四种宽度和200%缩放检查截图并修正至少一轮
    那么 修正前后证据可回读；无页面横向溢出；长公式局部滚动；不以概念图代替运行截图

  @AC-27 @M0 @R-34
  场景: 单文档独立启动
    假如 空目录只有PRODUCT_DESIGN.md
    当 从附录抽取类型和DDL并生成合成学习包
    那么 不访问旧版设计包或历史聊天即可验证合法引用和错误输入

  @AC-28 @M0 @R-35 @R-36
  场景: 建仓回读和进度不虚报
    假如 本机已授权GitHub身份为目标owner
    当 建立公开项目仓库、提交规范并初始化任务
    那么 远端visibility和提交可回读；全部实现任务初始非done；同一task_id重跑不重复创建Issue

  @AC-29 @M0 @R-35 @R-36
  场景: 无权限和敏感数据
    假如 GitHub未授权或暂存包含真实key及个人教材
    当 尝试发布
    那么 不发布敏感内容；前者记录授权阻塞且不声称仓库已创建；本地可独立工作继续

  @AC-30 @M4 @R-37
  场景: 自报与跨教材推荐
    假如 两本已导入教材覆盖同一概念且用户自报已接触但尚无独立证据
    当 设置目标并请求推荐
    那么 自报独立保存；候选不局限当前一本；推荐显示具体理由与来源；不显示校准掌握概率

  @AC-31 @M3 @R-14 @R-25
  场景: 活跃生成与独立测试的竞态
    假如 工作区有正在生成的学科Tutor或Codex任务
    当 请求开始独立测试并在另一标签读取旧消息或下载材料
    那么 guard在服务端原子检查；测试开始前要求取消或等待；测试期间所有相关入口不能继续泄露学科内容

  @AC-32 @M6 @R-21 @R-24 @R-38
  场景: 草稿审核绑定候选哈希
    假如 draft revision 3已人工批准
    当 先修改正文生成revision4再拿旧批准发布
    那么 拒绝发布；批准不会误引用尚不存在的Published ContentRef；新候选需重新审核

  @AC-33 @M7 @R-26 @R-38
  场景: 删除与备份的真实边界
    假如 原生数据库含已发布教材、笔记、题目和用户历史
    当 预览彻底删除但取消，再备份、重启并恢复到新工作区
    那么 取消不改变数据；在线备份包含WAL内已提交写入；恢复保留所有必要引用且无密钥
~~~
<!-- END FILE -->


## F.1 M5.2 原创冻结词法基准 lexical-gold-v1

以下完整语料/gold是本规范的工程fixture，不依赖另一设计包或下载文件，不宣称数学/来源已经独立审校。初始事实为SPEC_FIXTURE_NOT_EXECUTED；实际运行结果只写进度/证据，不反改这里的初始事实。30块均为显式范围中的未审公开教材，其中3块是含完整步骤的worked_example。42条字面查询中q01–q38为正向gold，宏平均Recall@5目标≥0.90；q39–q42必须无匹配，单列、不计免费召回分。算法、词面规则、数据/gold、所有精确refs在运行前冻结；不能按实际结果改gold或补同义词使门槛通过。

建立fixture时，每块使用JSON中的block_id/title/kind，revision=1、schema_version=3.0.0、body_path=`content/{block_id}.md`，concepts/citations/depends_on=[]；body为body_markdown经JSON解码后直接UTF-8编码，不加末尾换行。分别核所列body SHA并据完整ContentBlock规范JSON计算ContentRef。Lesson固定id=m52_lexical_lesson、revision=1、title=原创词法基准小节、objectives/prerequisite_ids=[]、proof_policy=full、block_refs按下列blocks顺序列全30个精确ref。Course固定id=m52_lexical_course、revision=1、title=原创词法基准课程、language=zh-CN、audience=工程验收未审材料、difficulty=beginner、objectives/concept_refs/sections=[]、lesson_refs仅含该精确Lesson；schema_version均3.0.0。使用Content公开发布owner建立这个明确受控软件fixture，不冒称普通导入已获专家批准。公开块无冻结provenance时如实unresolved。

请求scope只为这个完整Course ref，limit=5；gold block IDs在发布前按同一确定性模型转成完整refs，并在检索之前存成passport。评判比较完整entity/id/revision/sha256，不只比较ID。q32/q33两副本若score相同，必须按§20.7完整ref规则稳定排序。原样Greek/TeX查询分别测试字面存在：块26正文同时真实写出α和\alpha，不能借两次命中声称算法做了别名映射。跨表示的∑/\sum、≤/\leq、Δt/\Delta t、Aᵀ/转置TeX不在这42条的计分承诺中；未来扩别名必须另定版本/基准，不事后改这里的gold。

下面的body_utf8_sha256是实际输入字节约束。此表中的score/排名尚未运行，不预填任何PASS。真正私解、范围隔离、旧ref/current描述变化、FTS语法安全、错误hash、Policy与Jobs故障注入另按§20.7逐项验收，不用此小基准冒充这些安全测试。

```json
{
  "corpus_version": "m52-original-lexical-v1",
  "status": "SPEC_FIXTURE_NOT_EXECUTED",
  "index_field": "body_markdown",
  "blocks": [
    {
      "block_id": "m52_block_01",
      "kind": "definition",
      "title": "算术平均数",
      "body_markdown": "算术平均数把一组数的总和均分给各项。对 n 个实数 x₁,…,xₙ，样本均值写作 $\\bar{x}=\\frac{1}{n}\\sum_{i=1}^{n}x_i$，其中 n 必须为正整数。极端的大值或小值会影响这个平均数，因此汇报它时还应说明数据范围。",
      "body_utf8_sha256": "d178039d0e51b963c0dfac383d8ba42dadccc5cbcd370161ba8547bbfc31bae1"
    },
    {
      "block_id": "m52_block_02",
      "kind": "definition",
      "title": "中位数",
      "body_markdown": "中位数依据排序后的位置确定。把有限个实数从小到大排列；项数为奇数时取中间一项，项数为偶数时取中间两项的算术平均。例如 1、2、100 的中位数为 2。这个定义要求数据非空。",
      "body_utf8_sha256": "46dbd0b951c7f93eab54d38892c9cdbff1ef691dc384c68ba401c70155cf4c6e"
    },
    {
      "block_id": "m52_block_03",
      "kind": "worked_example",
      "title": "加权平均数例题",
      "body_markdown": "公开例题：一门课的平时成绩为 80 分，期末成绩为 90 分，权重分别为 0.4 和 0.6。加权平均数等于 0.4×80 + 0.6×90 = 86 分。两项权重之和为 1，因此无需再除以权重总和；若采用未归一化权重，应先除以它们的正总和。",
      "body_utf8_sha256": "6379b8dd28ed5edd58de96997aeddd55feaee6f1dc362503d4468964d4db999a"
    },
    {
      "block_id": "m52_block_04",
      "kind": "definition",
      "title": "描述性方差",
      "body_markdown": "描述性方差度量一组实数偏离其平均数的平方幅度。数据非空时，令 $v=\\frac{1}{n}\\sum_{i=1}^{n}(x_i-\\bar{x})^2$。这里分母为 n，描述的是这组数据本身；它不是以 n−1 为分母的无偏估计公式。每项平方非负，所以 v 不小于零。",
      "body_utf8_sha256": "554748c28384de80d2dbb4ff03baf4a7efe786fadeb43f3adff170becefa4959"
    },
    {
      "block_id": "m52_block_05",
      "kind": "definition",
      "title": "标准差与单位",
      "body_markdown": "标准差是方差的非负平方根。若身高以 cm 记录，则方差的单位是 cm²，而标准差仍以 cm 记录。数据全部相等时，方差与标准差都为零；单位不同的数值不能不经换算直接比较离散程度。",
      "body_utf8_sha256": "1574c2c4569ef31b139da75499110f15873096bcadae0ba5b99d1f69da3d60b9"
    },
    {
      "block_id": "m52_block_06",
      "kind": "boundary",
      "title": "概率范围",
      "body_markdown": "概率范围满足 0 ≤ P(A) ≤ 1。这里 A 是给定概率空间中的事件，P(A) 不是观察一次就必然出现的比例。概率为零也不总能解释为逻辑上不可能，例如连续均匀分布在某个指定点上的取值概率为零。",
      "body_utf8_sha256": "e3637d6b59d7eccc9aa1e0595620909246a5a9008f84dea07d27e49a63e42e57"
    },
    {
      "block_id": "m52_block_07",
      "kind": "definition",
      "title": "独立事件",
      "body_markdown": "独立事件 A 与 B 满足 P(A∩B)=P(A)P(B)。判断独立需要结合具体概率模型，不能仅凭两个事件名称不同。若两个事件互斥且概率都大于零，它们就不独立，因为交集概率为零而概率乘积大于零。",
      "body_utf8_sha256": "25b9dbba14b90371787c15bbd7afd6f94037448eefbb3b30e25580973b91ae51"
    },
    {
      "block_id": "m52_block_08",
      "kind": "definition",
      "title": "条件概率",
      "body_markdown": "条件概率以已知事件缩小样本范围。当 P(B)>0 时，定义 P(A|B)=P(A∩B)/P(B)。分母为零时不能直接使用这个比值定义。条件事件应在符号右侧明确写出，不能把 P(A|B) 与 P(B|A) 当成同一个数。",
      "body_utf8_sha256": "24b772780667ba772953dd4d0c187ddf164c78bbc1ef8ac313dea489cf4846a2"
    },
    {
      "block_id": "m52_block_09",
      "kind": "theorem",
      "title": "全概率公式",
      "body_markdown": "全概率公式把目标事件按互不相交的情形分解。若 B₁,…,Bₖ 构成样本空间的有限划分，且每个 P(Bᵢ)>0，则 P(A)=ΣᵢP(A|Bᵢ)P(Bᵢ)。各个划分事件应覆盖整个空间；遗漏某个情形时，直接相加一般不能得到完整的 P(A)。",
      "body_utf8_sha256": "33a6dc1fdf5082dcecf4570f8b2f711bea664f41581fcf76a05a063de7ccfd2e"
    },
    {
      "block_id": "m52_block_10",
      "kind": "theorem",
      "title": "贝叶斯公式",
      "body_markdown": "贝叶斯公式交换已知事件的位置：当 P(B)>0 且 P(A)>0 时，P(A|B)=P(B|A)P(A)/P(B)。先验概率 P(A) 与似然 P(B|A) 各有含义，二者不能互换。该公式本身不提供未知先验的数值。",
      "body_utf8_sha256": "2b35dac86a2c25c1707da1db888f1def42b557a6fa6bda04bba0276b84e087da"
    },
    {
      "block_id": "m52_block_11",
      "kind": "definition",
      "title": "放回抽样",
      "body_markdown": "放回抽样是每次抽出对象、记录后再把它放回。若每次都均匀且独立地抽取，后一次可抽到的对象集合不变。例如从标号 1 到 5 的球中抽两次，同一标号可以重复出现。是否独立还取决于每次抽取规则。",
      "body_utf8_sha256": "2ca25563cc516f100e7379bf3215163f886a9f68caa167770c48cba76405dc83"
    },
    {
      "block_id": "m52_block_12",
      "kind": "definition",
      "title": "不放回抽样",
      "body_markdown": "不放回抽样会把已抽到的对象留在池外。若从 5 个不同标号的球中均匀抽取两次，第二次只剩 4 个对象可选，同一标号不会再次出现。抽样空间随记录变化，不能直接照搬可重复抽取的概率乘积。",
      "body_utf8_sha256": "9e6f64e1f4f86761830977f7d5ff559ce178fea265a71322954bb1eff7b1d357"
    },
    {
      "block_id": "m52_block_13",
      "kind": "definition",
      "title": "函数极限",
      "body_markdown": "函数极限描述自变量趋近某点时函数值的趋势。记号 x→a 表示 x 趋近 a，并不要求 x 等于 a。说 f(x) 在该过程趋近 L，讨论的是邻近点的行为；函数在 a 处未定义也可能存在这个极限。",
      "body_utf8_sha256": "1daf3c64bd9d5bd19ad8d716f1c8a870678b6e34967c9a253af2ce20d0f4d026"
    },
    {
      "block_id": "m52_block_14",
      "kind": "definition",
      "title": "导数与差商",
      "body_markdown": "导数通过差商的极限定义。对实函数，差商为 [f(x+h)−f(x)]/h，其中 h 不等于零；当 h 趋近零且极限存在时，该极限是 f 在 x 处的导数。单个非零步长得到的差商一般不等于精确导数。",
      "body_utf8_sha256": "febfd42a5609822440f2274b150f6739e0c413548ca5b07c58df00e13e7e0651"
    },
    {
      "block_id": "m52_block_15",
      "kind": "boundary",
      "title": "有限差分与步长",
      "body_markdown": "有限差分用离散记录估计变化率。若时间间隔为 Δt，位移变化为 Δx，则差商 Δx/Δt 只在 Δt 不为零时有定义。缩小步长可能减小离散近似误差，但测量噪声会被除以小步长放大，不能据此保证误差一直下降。",
      "body_utf8_sha256": "ba82d40228a195078e1e357f53f136f726f9e664ea3dc077c1378765138537b6"
    },
    {
      "block_id": "m52_block_16",
      "kind": "worked_example",
      "title": "用定积分求路程",
      "body_markdown": "公开例题：物体沿直线运动，在 0 s 到 2 s 内速度 v(t)=3t m/s，其中 t 的数值以秒计。因为这段时间速度非负，路程等于定积分 $\\int_0^2 3t\\,dt=[1.5t^2]_0^2=6$，单位为 m，即 6 m。若速度改变符号，路程应积分速度的绝对值，不能把位移直接当作路程。",
      "body_utf8_sha256": "a85ac1498e575f73289915489f63024b914d6b448d030215495c4187cd20962e"
    },
    {
      "block_id": "m52_block_17",
      "kind": "definition",
      "title": "矩阵乘法",
      "body_markdown": "矩阵乘法要求相邻的内维度相同。若 A 为 m×n 矩阵，B 为 n×p 矩阵，则 AB 为 m×p 矩阵，第 i 行第 j 列等于 A 第 i 行与 B 第 j 列逐项相乘后求和。一般不能交换乘法顺序，甚至 BA 可能没有定义。",
      "body_utf8_sha256": "04bcbed76f5e761bf4e8e75d1d43e03f08625c8204f0272324453a89d0b170b6"
    },
    {
      "block_id": "m52_block_18",
      "kind": "definition",
      "title": "矩阵转置",
      "body_markdown": "矩阵转置交换行与列，记作 Aᵀ。若 A 有 m 行 n 列，则 Aᵀ 有 n 行 m 列，其第 i 行第 j 列等于 A 的第 j 行第 i 列。对复矩阵，单纯转置不包含复共轭，不能把这两种操作混为一谈。",
      "body_utf8_sha256": "6983e048b579afb16fd50d33278aced44f75e09ca645f758648dbd9d9453ecfc"
    },
    {
      "block_id": "m52_block_19",
      "kind": "definition",
      "title": "最小二乘目标",
      "body_markdown": "最小二乘把残差的平方和作为目标。给定观测 yᵢ 与预测值 ŷᵢ，目标写作 $\\sum_{i=1}^{n}(y_i-\\hat{y}_i)^2$。求得目标最小值不自动证明估计无偏，也不保证新数据上的误差最小；这些结论还需要模型与数据条件。",
      "body_utf8_sha256": "af253f7c388fdd961e5b44491a4d58bbb755628cebf3748394050a2a41c74396"
    },
    {
      "block_id": "m52_block_20",
      "kind": "definition",
      "title": "SVD 分解",
      "body_markdown": "SVD 是实矩阵奇异值分解的常用缩写。对实矩阵 A，可写 A=UΣVᵀ，其中 U 与 V 为适当大小的正交矩阵，Σ 的对角元素为非负奇异值。奇异值不是任意方阵的特征值，不能只换名称就把两者等同。",
      "body_utf8_sha256": "0deffc718e25d53476476764dfcec2200f85310f71e3eb6af5d795fe52987cce"
    },
    {
      "block_id": "m52_block_21",
      "kind": "code",
      "title": "Python 列表索引",
      "body_markdown": "Python 列表索引从 0 开始。例如 values = [4, 7, 9] 时，values[0] 得到 4，values[2] 得到 9。此例只读取已有位置；访问 values[3] 会超出列表长度。代码作为教材文本展示，并不授权检索系统执行它。",
      "body_utf8_sha256": "316f03af991b75bf58f8f9e4a2e904d3211fa2f9da761b5d1003a1533334cbc3"
    },
    {
      "block_id": "m52_block_22",
      "kind": "code",
      "title": "SQLite FTS5 词法索引",
      "body_markdown": "SQLite 的 FTS5 用于全文词法索引。应用可把预分词后的文本交给索引，并以 MATCH 表达式检索。词项得分只是排序依据，不验证正文正确性；索引结果仍应回到真实正文与修订引用核对。此段不包含数据库操作授权。",
      "body_utf8_sha256": "60cc7a36f8aa95a4cd413fc62858826810875d6a47799304bd1c4977ea49b255"
    },
    {
      "block_id": "m52_block_23",
      "kind": "code",
      "title": "查询语言中的字面词",
      "body_markdown": "本段讲解查询语言中的字面词：MATCH、OR、NOT 与 NEAR。在普通文字搜索框中输入 OR，应被当作要找的字符词，而不是替用户增加或条件。引号、括号与星号也只是用户文本，不能据此拼接 SQL 或扩大权限。这里没有要执行的查询命令。",
      "body_utf8_sha256": "f80d64b144d2bb3d9bd8c9697ed79dbdfe20eb2b397fbfb03174a0f83361b43e"
    },
    {
      "block_id": "m52_block_24",
      "kind": "definition",
      "title": "对数刻度",
      "body_markdown": "对数刻度让相同的倍率对应相同的距离。以常用对数为例，1、10、100 在刻度上的相邻间隔相同。取实数对数要求真数为正，零和负数不能直接放进这个定义。对数刻度不表示原数值的差相等。",
      "body_utf8_sha256": "519d81ebe1353d7e96391488c409f0bcd73a4a0ca5e45b7182ff8861d9066c45"
    },
    {
      "block_id": "m52_block_25",
      "kind": "boundary",
      "title": "量纲一致与单位换算",
      "body_markdown": "量纲一致是相加和建立物理等式的基本检查。长度 2 m 加上 30 cm，应先进行单位换算，得到 2 m + 0.30 m = 2.30 m。长度不能直接与时间相加；单纯把两个数字相加并不会使单位自动一致。",
      "body_utf8_sha256": "41088195a350968ad5c0cb9f9d79cc6513a0ed2703d7b878b5e45de12e048cfc"
    },
    {
      "block_id": "m52_block_26",
      "kind": "text",
      "title": "希腊参数记号",
      "body_markdown": "希腊字母 α 常被用作参数名；在这份材料里，同一字形的 TeX 源码是 $\\alpha$。这句话显式展示了两个写法，所以按任一原样文字检索都可以找到本段。参数的数学含义由其所在定义决定，不能只凭这个字母断言它一定代表概率。",
      "body_utf8_sha256": "cffd2d64e3f337651ed3f7d7775f12dc53d3ab5a5cf3c4509344c636c0d13c35"
    },
    {
      "block_id": "m52_block_27",
      "kind": "definition",
      "title": "质数与一",
      "body_markdown": "质数是大于 1 且只有 1 与自身两个正因数的整数。2 是质数，也是唯一的偶质数。整数 1 只有一个正因数，因此不属于质数。判定较大的数是否为质数需要计算或证明，不能只凭它是奇数。",
      "body_utf8_sha256": "6c2bb93df6295a5186e975f6d31f6449e52d93a67225371b21701bb197983c10"
    },
    {
      "block_id": "m52_block_28",
      "kind": "worked_example",
      "title": "最大公约数例题",
      "body_markdown": "公开例题：用辗转相除法求 18 与 12 的最大公约数。先算 18=1×12+6，再算 12=2×6+0，因此最后一个非零余数 6 是最大公约数。该过程处理正整数，并使用每步带余除法保持公约数集合不变。",
      "body_utf8_sha256": "a9f1b365ae4c6d5aa9fa7f48594b63d505348039281354a3a93cbf209495651e"
    },
    {
      "block_id": "m52_block_29",
      "kind": "definition",
      "title": "区间中点",
      "body_markdown": "区间中点等于两个有限实数端点的算术平均。对端点 a 与 b，中点为 (a+b)/2；交换端点顺序不会改变结果。本段只给出中点定义，不宣称函数值在中点取得最大值或最小值。",
      "body_utf8_sha256": "fa9390f2b46cfcdd49f25af6ff919f8edf52d384f99e99b1edaea7b577a396e4"
    },
    {
      "block_id": "m52_block_30",
      "kind": "definition",
      "title": "区间中点",
      "body_markdown": "区间中点等于两个有限实数端点的算术平均。对端点 a 与 b，中点为 (a+b)/2；交换端点顺序不会改变结果。本段只给出中点定义，不宣称函数值在中点取得最大值或最小值。",
      "body_utf8_sha256": "fa9390f2b46cfcdd49f25af6ff919f8edf52d384f99e99b1edaea7b577a396e4"
    }
  ],
  "cases": [
    {
      "case_id": "q01",
      "suite": "literal_positive_recall",
      "query": "算术平均数",
      "expected_block_ids": [
        "m52_block_01"
      ],
      "relevance_reason": "给出算术平均数的总和除以项数定义及适用条件。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q02",
      "suite": "literal_positive_recall",
      "query": "样本均值",
      "expected_block_ids": [
        "m52_block_01"
      ],
      "relevance_reason": "正文明确称这个量为样本均值，并给出精确公式。",
      "categories": [
        "chinese_word_boundary"
      ]
    },
    {
      "case_id": "q03",
      "suite": "literal_positive_recall",
      "query": "中位数",
      "expected_block_ids": [
        "m52_block_02"
      ],
      "relevance_reason": "正文同时说明奇数与偶数个数据的中位数定义。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q04",
      "suite": "literal_positive_recall",
      "query": "加权平均数",
      "expected_block_ids": [
        "m52_block_03"
      ],
      "relevance_reason": "公开例题展示权重、逐项计算与归一化条件。",
      "categories": [
        "public_worked_example"
      ]
    },
    {
      "case_id": "q05",
      "suite": "literal_positive_recall",
      "query": "方差",
      "expected_block_ids": [
        "m52_block_04",
        "m52_block_05"
      ],
      "relevance_reason": "块04给描述性方差公式；块05给方差与标准差的关系及单位。",
      "categories": [
        "multi_relevant"
      ]
    },
    {
      "case_id": "q06",
      "suite": "literal_positive_recall",
      "query": "标准差",
      "expected_block_ids": [
        "m52_block_05"
      ],
      "relevance_reason": "正文定义非负平方根并说明单位。",
      "categories": [
        "chinese_word_boundary"
      ]
    },
    {
      "case_id": "q07",
      "suite": "literal_positive_recall",
      "query": "概率范围",
      "expected_block_ids": [
        "m52_block_06"
      ],
      "relevance_reason": "正文给出概率上下界，并避免把概率零解释成逻辑不可能。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q08",
      "suite": "literal_positive_recall",
      "query": "独立事件",
      "expected_block_ids": [
        "m52_block_07"
      ],
      "relevance_reason": "正文给乘积定义及与互斥事件的区别。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q09",
      "suite": "literal_positive_recall",
      "query": "条件概率",
      "expected_block_ids": [
        "m52_block_08"
      ],
      "relevance_reason": "正文给条件概率的非零分母要求和符号顺序。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q10",
      "suite": "literal_positive_recall",
      "query": "全概率公式",
      "expected_block_ids": [
        "m52_block_09"
      ],
      "relevance_reason": "正文给有限划分、正概率条件与完整相加规则。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q11",
      "suite": "literal_positive_recall",
      "query": "贝叶斯公式",
      "expected_block_ids": [
        "m52_block_10"
      ],
      "relevance_reason": "正文直接给该公式及先验和似然不可互换的说明。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q12",
      "suite": "literal_positive_recall",
      "query": "放回抽样",
      "expected_block_ids": [
        "m52_block_11"
      ],
      "relevance_reason": "本意是抽后放回的规则；块12虽含字面子串但定义相反，不列为相关gold。",
      "categories": [
        "chinese_negation_boundary"
      ]
    },
    {
      "case_id": "q13",
      "suite": "literal_positive_recall",
      "query": "不放回抽样",
      "expected_block_ids": [
        "m52_block_12"
      ],
      "relevance_reason": "完整否定词组对应移出已抽对象及候选集合减少。",
      "categories": [
        "chinese_negation_boundary"
      ]
    },
    {
      "case_id": "q14",
      "suite": "literal_positive_recall",
      "query": "函数极限",
      "expected_block_ids": [
        "m52_block_13"
      ],
      "relevance_reason": "正文区分邻近行为与点值。",
      "categories": [
        "chinese_word_boundary"
      ]
    },
    {
      "case_id": "q15",
      "suite": "literal_positive_recall",
      "query": "差商",
      "expected_block_ids": [
        "m52_block_14",
        "m52_block_15"
      ],
      "relevance_reason": "块14用差商定义导数；块15说明非零步长差商及噪声边界。",
      "categories": [
        "multi_relevant"
      ]
    },
    {
      "case_id": "q16",
      "suite": "literal_positive_recall",
      "query": "定积分 路程",
      "expected_block_ids": [
        "m52_block_16"
      ],
      "relevance_reason": "同一公开例题包含定积分求路程的步骤和速度非负条件。",
      "categories": [
        "spaced_terms",
        "public_worked_example"
      ]
    },
    {
      "case_id": "q17",
      "suite": "literal_positive_recall",
      "query": "矩阵乘法",
      "expected_block_ids": [
        "m52_block_17"
      ],
      "relevance_reason": "正文给内维度和行列求和规则。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q18",
      "suite": "literal_positive_recall",
      "query": "矩阵转置",
      "expected_block_ids": [
        "m52_block_18"
      ],
      "relevance_reason": "正文给转置的行列交换与复共轭区别。",
      "categories": [
        "chinese_word_boundary"
      ]
    },
    {
      "case_id": "q19",
      "suite": "literal_positive_recall",
      "query": "最小二乘",
      "expected_block_ids": [
        "m52_block_19"
      ],
      "relevance_reason": "正文给残差平方和目标，并限定可作的推断。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q20",
      "suite": "literal_positive_recall",
      "query": "SVD",
      "expected_block_ids": [
        "m52_block_20"
      ],
      "relevance_reason": "正文原样出现SVD并解释对应分解。",
      "categories": [
        "latin_exact"
      ]
    },
    {
      "case_id": "q21",
      "suite": "literal_positive_recall",
      "query": "svd",
      "expected_block_ids": [
        "m52_block_20"
      ],
      "relevance_reason": "与q20同一缩写的小写检索；需要语料与query一致的已声明大小写规则。",
      "categories": [
        "latin_casefold"
      ]
    },
    {
      "case_id": "q22",
      "suite": "literal_positive_recall",
      "query": "Python",
      "expected_block_ids": [
        "m52_block_21"
      ],
      "relevance_reason": "正文原样包含Python及列表索引例子。",
      "categories": [
        "mixed_latin_chinese"
      ]
    },
    {
      "case_id": "q23",
      "suite": "literal_positive_recall",
      "query": "python 列表索引",
      "expected_block_ids": [
        "m52_block_21"
      ],
      "relevance_reason": "小写语言名与中文词组指向同一具体索引规则。",
      "categories": [
        "latin_casefold",
        "spaced_terms",
        "mixed_latin_chinese"
      ]
    },
    {
      "case_id": "q24",
      "suite": "literal_positive_recall",
      "query": "SQLite FTS5",
      "expected_block_ids": [
        "m52_block_22"
      ],
      "relevance_reason": "正文原样给SQLite与FTS5及其用途。",
      "categories": [
        "mixed_latin_digits",
        "spaced_terms"
      ]
    },
    {
      "case_id": "q25",
      "suite": "literal_positive_recall",
      "query": "MATCH OR NOT NEAR",
      "expected_block_ids": [
        "m52_block_23"
      ],
      "relevance_reason": "四个原样词在本段同时出现；它们是待检索文本，不是可执行MATCH操作。",
      "categories": [
        "match_reserved_words_literal",
        "spaced_terms"
      ]
    },
    {
      "case_id": "q26",
      "suite": "literal_positive_recall",
      "query": "对数刻度",
      "expected_block_ids": [
        "m52_block_24"
      ],
      "relevance_reason": "正文说明相同倍率与正真数边界。",
      "categories": [
        "chinese_word_boundary"
      ]
    },
    {
      "case_id": "q27",
      "suite": "literal_positive_recall",
      "query": "量纲一致",
      "expected_block_ids": [
        "m52_block_25"
      ],
      "relevance_reason": "正文包含量纲检查与单位换算的实际例子。",
      "categories": [
        "chinese_no_spaces"
      ]
    },
    {
      "case_id": "q28",
      "suite": "literal_positive_recall",
      "query": "\\alpha",
      "expected_block_ids": [
        "m52_block_26"
      ],
      "relevance_reason": "原样TeX命令真实存在于正文，不需要推断数学别名。",
      "categories": [
        "latex_raw_literal"
      ]
    },
    {
      "case_id": "q29",
      "suite": "literal_positive_recall",
      "query": "α",
      "expected_block_ids": [
        "m52_block_26"
      ],
      "relevance_reason": "原样Unicode字符真实存在于正文；不据此证明TeX与Unicode已自动归一化。",
      "categories": [
        "unicode_math_raw_literal"
      ]
    },
    {
      "case_id": "q30",
      "suite": "literal_positive_recall",
      "query": "质数",
      "expected_block_ids": [
        "m52_block_27"
      ],
      "relevance_reason": "正文给质数定义并区分1与2。",
      "categories": [
        "chinese_word_boundary"
      ]
    },
    {
      "case_id": "q31",
      "suite": "literal_positive_recall",
      "query": "最大公约数",
      "expected_block_ids": [
        "m52_block_28"
      ],
      "relevance_reason": "公开例题逐步计算18与12的最大公约数。",
      "categories": [
        "public_worked_example"
      ]
    },
    {
      "case_id": "q32",
      "suite": "literal_positive_recall",
      "query": "区间中点",
      "expected_block_ids": [
        "m52_block_29",
        "m52_block_30"
      ],
      "relevance_reason": "两个不同block的公开正文相同且同样相关，不能只把一个副本算gold。",
      "categories": [
        "tie_identical_bodies",
        "multi_relevant"
      ]
    },
    {
      "case_id": "q33",
      "suite": "literal_positive_recall",
      "query": "“区间中点”",
      "expected_block_ids": [
        "m52_block_29",
        "m52_block_30"
      ],
      "relevance_reason": "引用符号包围同一中文文字；需先声明引号处理规则，不执行短语查询语法。",
      "categories": [
        "punctuation_quotes",
        "tie_identical_bodies"
      ]
    },
    {
      "case_id": "q34",
      "suite": "literal_positive_recall",
      "query": "6 m",
      "expected_block_ids": [
        "m52_block_16"
      ],
      "relevance_reason": "正文原样出现6 m，并给该路程数值的完整公开计算。",
      "categories": [
        "digits_units",
        "spaced_terms"
      ]
    },
    {
      "case_id": "q35",
      "suite": "literal_positive_recall",
      "query": "Δt",
      "expected_block_ids": [
        "m52_block_15"
      ],
      "relevance_reason": "有限差分正文原样包含Δt；不是由LaTeX命令推测来的别名。",
      "categories": [
        "unicode_math_raw_literal",
        "mixed_latin_chinese"
      ]
    },
    {
      "case_id": "q36",
      "suite": "literal_positive_recall",
      "query": "0 ≤ P(A) ≤ 1",
      "expected_block_ids": [
        "m52_block_06"
      ],
      "relevance_reason": "原样概率不等式在正文中存在；括号不应获得查询控制权限。",
      "categories": [
        "unicode_math_raw_literal",
        "digits",
        "punctuation_parentheses"
      ]
    },
    {
      "case_id": "q37",
      "suite": "literal_positive_recall",
      "query": "量纲一致，单位换算",
      "expected_block_ids": [
        "m52_block_25"
      ],
      "relevance_reason": "同一块实际讨论两个字面主题；中文逗号是文本分隔规则的用例。",
      "categories": [
        "chinese_punctuation",
        "multi_terms"
      ]
    },
    {
      "case_id": "q38",
      "suite": "literal_positive_recall",
      "query": "OR",
      "expected_block_ids": [
        "m52_block_23"
      ],
      "relevance_reason": "单独保留字本身也是搜索文字；正文23原样展示它，不应解析为缺操作数错误。",
      "categories": [
        "match_reserved_words_literal"
      ]
    },
    {
      "case_id": "q39",
      "suite": "literal_no_result",
      "query": "菠萝榴莲",
      "expected_block_ids": [],
      "relevance_reason": "菠、萝、榴、莲四个汉字在30块正文中逐字均未出现；这是词面无匹配用例，不要求句子整体相等。",
      "categories": [
        "no_result_chinese"
      ]
    },
    {
      "case_id": "q40",
      "suite": "literal_no_result",
      "query": "zzqvnonexistent",
      "expected_block_ids": [],
      "relevance_reason": "此完整ASCII字母词项未在30块正文中出现；不依靠数字子串分词来判空。",
      "categories": [
        "no_result_ascii"
      ]
    },
    {
      "case_id": "q41",
      "suite": "literal_no_result",
      "query": "“麒麟魑魅”",
      "expected_block_ids": [],
      "relevance_reason": "麒、麟、魑、魅四个汉字以及包围引号在正文均未出现；这是带引号的真实词面无匹配用例。",
      "categories": [
        "no_result_chinese",
        "punctuation_quotes"
      ]
    },
    {
      "case_id": "q42",
      "suite": "literal_no_result",
      "query": "jkwzabsent",
      "expected_block_ids": [],
      "relevance_reason": "此完整ASCII字母词项未在当前30块正文中出现。",
      "categories": [
        "no_result_ascii"
      ]
    }
  ]
}
```

# 附录 G：从本文件抽取工程基线与公开发布

## G.1 抽取工具

首次可将下面工具从本文件保存为 scripts/extract_spec.py，再对同一文件运行。只需本文件和Python，不需要另一个压缩包。已有目标文件内容不同时拒绝覆盖，由开发者显式合并；工具不等于产品构建器，也不代替本文件的逐阶段实施要求。

<!-- BEGIN FILE: scripts/extract_spec.py -->
~~~python
"""Extract normative code blocks from PRODUCT_DESIGN.md; refuse overwriting edits.
Usage: python scripts/extract_spec.py PRODUCT_DESIGN.md [destination]
This helper itself can be copied from appendix G; no network or credentials required.
"""
from pathlib import Path, PurePosixPath
import re, sys
PATTERN=re.compile(r'^<!-- BEGIN FILE: ([A-Za-z0-9_./-]+) -->\n~~~[a-zA-Z0-9_-]*\n(.*?)\n~~~\n<!-- END FILE -->',re.M|re.S)
def extract(spec:Path,destination:Path):
    text=spec.read_text(encoding='utf-8');root=destination.resolve();root.mkdir(parents=True,exist_ok=True)
    entries=PATTERN.findall(text)
    if not entries: raise ValueError('no embedded files found')
    seen=set();pending=[]
    for relative,body in entries:
        p=PurePosixPath(relative)
        if p.is_absolute() or '..' in p.parts or str(p)!=relative or relative in seen:
            raise ValueError(f'invalid or duplicate path: {relative}')
        seen.add(relative);target=root/relative
        if not target.resolve().is_relative_to(root): raise ValueError('symlink or path escape')
        data=(body+'\n').encode('utf-8')
        if target.exists() and target.read_bytes()!=data: raise ValueError(f'edited destination: {relative}')
        pending.append((target,data))
    for target,data in pending:
        target.parent.mkdir(parents=True,exist_ok=True)
        # Recheck parents after mkdir, do not follow pre-existing escaping symlinks.
        if not target.resolve().is_relative_to(root): raise ValueError('path changed')
        if not target.exists(): target.write_bytes(data)
    return [str(x.relative_to(root)) for x,_ in pending]
if __name__=='__main__':
    spec=Path(sys.argv[1] if len(sys.argv)>1 else 'PRODUCT_DESIGN.md')
    destination=Path(sys.argv[2]) if len(sys.argv)>2 else spec.parent
    for entry in extract(spec,destination): print(entry)
~~~
<!-- END FILE -->


## G.2 建仓与发布顺序（由执行 Agent 完成，不要求用户逐条操作）

在本文指定的新工作目录执行。先从第18章生成README、忽略规则和真实progress/state.json，填入本文件实际sha256；progress/CURRENT.md从同一JSON生成。README保留“规范就绪、尚未实现/未运行”边界，不能附虚构绿色徽章。下列是确切命令接口；必须先完成本文的身份、路径、内容白名单与冲突检查，不能盲目整段执行。

```bash
# 已登录状态检查；不使用 gh auth token，不打印凭据。
gh auth status
gh api user --jq .login
# 返回身份必须是 kl3574；否则暂停远端操作。

# 检查目标；404还可能是权限问题，不把其他错误当成不存在。
gh repo view kl3574/Learning_Workbench --json nameWithOwner,visibility,url

# 仅在确认新目录不属于其他仓库后初始化；使用现有Git作者身份。
git init -b main
git config user.name
git config user.email
# 逐项查看内容与暂存；此处不提交应用数据、凭据或旧Demo。
git add -- PRODUCT_DESIGN.md README.md .gitignore progress/state.json progress/CURRENT.md
git diff --cached --stat
git diff --cached --check
# 实施Agent还须按第18.5节检查暂存内容的秘密和版权边界。
git commit -m "docs: establish single-source product specification and initial progress"

# 仅适用于确认尚未创建的目标，不执行于同名未知仓库。
gh repo create kl3574/Learning_Workbench --public --source=. --remote=origin --push \
  --description "Local-first agent-assisted learning workbench; specification-driven development" \
  --disable-wiki

# 真实回读，不用预期链接当成功证据。
gh repo view kl3574/Learning_Workbench --json nameWithOwner,visibility,url,defaultBranchRef
git ls-remote --heads origin main
```

仓库存在且确认属于本项目时使用普通fetch/push衔接，禁止force push和重写历史。gh不可用/未登录时写明BLOCKED_GITHUB_AUTH或BLOCKED_GITHUB_CLI，保存本地文件继续M0；创建操作没有成功返回和回读就不能写REMOTE_READY。

之后按第17/19章创建M0—M7 Milestones和任务Issues。创建前查询open/closed，按稳定task_id幂等去重；返回的实际number/url写入state.json。参考命令如下，真正执行时先完成查重：

```bash
gh api 'repos/kl3574/Learning_Workbench/milestones?state=all&per_page=100'
gh api --method POST repos/kl3574/Learning_Workbench/milestones \
  -f title='M0 工程与契约' -f description='PRODUCT_DESIGN.md 第17/19章；不代表已实现'
gh issue list --repo kl3574/Learning_Workbench --state all --limit 1000 --json number,title,body
# 任务正文由本文生成至临时UTF-8文件；不在命令行拼入秘密。
gh issue create --repo kl3574/Learning_Workbench \
  --title '[M0.1] 空工程、依赖锁与基线测试' \
  --body-file progress/issue-M0.1.md --milestone 'M0 工程与契约'
```

一项成功不代表其他事项成功。建仓成功但创建Issue失败：repository.publication=VERIFIED、tasks.sync=BLOCKED；本地任务内容仍保留。模型调用未运行：real_provider=NOT_RUN，不借用旧Demo测试数。每次发布后核对visibility、目标分支HEAD、规范blob和任务链接，更新与推进下一任务。

## G.3 完整性验收与最终交付边界

至少验证：本文件38项需求/目标场景/任务映射一致；全部嵌入文件可抽取且无路径穿越；Python模型可导入并生成JSON Schema；SQL可在临时库执行；样例包所有文件和对象hash可回读；学习者包不存在private文件；目录不依赖旧样例；实际业务实现完成后对附录A的每条P0路由做注册/DTO/测试覆盖核对。

若发现未覆盖的行为，只能记录缺陷、修正规范并增补测试，不能为了得到绿色结果删除要求。规范自检通过只说明检查范围内未发现结构问题；不是软件功能、远端发布、真实模型或教学效果验收。

**给 Codex 的启动指令无需重复需求：完整读取 PRODUCT_DESIGN.md，以它为唯一规范，按其中的建仓、M0—M7、验收与进度规则直接实施；遇到真实授权阻塞记录事实并继续不受影响的本地工作。**
