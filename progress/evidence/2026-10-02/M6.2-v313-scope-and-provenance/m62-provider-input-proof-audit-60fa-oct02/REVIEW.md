# Agent / DeepSeek 生产 InputProof 阻塞核查

固定源：Learning_Workbench `60fa2b8c18bbd3bbd4122df81bb798fd6d0a3dab`；唯一规范 PRODUCT_DESIGN.md v3.0.13，SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`。下面行号均指本目录 source/ 中从该提交读取的源文件。

## 结论与责任边界

当前生产 Agent → DeepSeek 真实调用确实被完整 InputProof 缺口阻断，**不是已证实的“用户没有 key / 没有授权 / 没上传教材”**。生产工厂已注册 Tutor 与 Authoring source，却明确构造空 ProofRegistry（services/api/app/main.py:89–98）。即使秘密存在且可用，空 registry 仍使 chat/streaming=false，新的 prepare 返回 CAPABILITY_UNSUPPORTED（application/provider_budget.py:120–130、169–191；tests/unit/test_provider_budget.py:13–26）。这是一项确定的生产工程与证据准入缺口；它不能靠再次索取 key 或口头批准消除。

规范允许工程方在可信 Python composition 中补齐实际受检 proof/checker/registration，不要求用户上传“计量证明”、新增浏览器 DTO/HTTP 路由或环境开关（PRODUCT_DESIGN.md:1047–1055、3052）。现有端口已够承载该工作。用户已有测试授权可用于按原范围推进这一工程工作；真正外发仍须形成该次真实 job 的服务端冻结 proposal 和 consent，不能伪造/跳过原合同。

仓内尚不足以证明目标 DeepSeek 托管端点存在可用的完整本地 exact/upper-bound 依据。第一轮仓内审计不联网（随后官方网页取证见末尾），不能断言供应商永远无法提供依据，也不能断言加一个 tokenizer 就必然完成。精确分类是：**当前实现没有生产证明注册；证明材料及目标协议覆盖仍待工程核实。** 若随后确认供应商隐藏格式无法建立合同要求的上界，那是供应商证据边界，不能用用户同意冒充证明；放宽硬准入则属于另一个需要明确决定的规范变更，本报告不提出默认放宽。

## 缺什么、已有些什么

| 项目 | 当前可确认事实 | 下一步责任 |
|---|---|---|
| 用户 key / 服务端 secret | 用户已提供 key 的授权事实沿会话保留；本次未读 key、环境、秘密目录或用户 DB，未核验是否已在本机 SecretStore 中，也未核验供应商余额/有效性 | 不索取、转抄或上传 key；后续正式平台运行仅走既有本机 Provider owner 与 write-only 机制。配置 secret_present 不能当鉴权成功 |
| 用户教学材料 | Tutor 必须有真实可读 exact active_ref，不能用任意 prompt 假 source；但原创无私密的小段测试材料可走现有导入/公开内容路径，不需要用户交出私人教材 | 用已有可公开测试材料或本地原创材料，附加范围为空；不能用测试工厂直接注入生产 source |
| 真实 source / UI / consent / worker | main.py:92–94 已注册真实 Tutor 与单块/组 Authoring；线程、Run、preview、grant、worker、SSE、结果回读已有 | 不必新造 Agent HTTP 入口；继续用同一个 Run/job 与已存在端口 |
| 生产 InputProof | registry 默认空；唯一具体 InputProof 构造实例在测试专属完整字节模型中（tests/provider_protocol_fixture.py:49–58） | 工程补真实依据、checker、固定注册和独立审查；不得将人工 byte rule 改名 DeepSeek |
| 精确端点/实际模型版本/别名变化 | InputProof 字段与 SHA 绑定已实现（provider_budget.py:45–130），但无目标服务已审核的生产实例 | 固定实际请求 URL、策略、adapter/model、覆盖实际版本范围和失效/withdrawal 依据；通用品牌名或一次 response.model 不够 |
| 全输入与输出能力 | prepare 冻结完整请求后调用 checker，核输入上限、输出上限和共享容量（provider_budget.py:198–227） | 取得完整格式开销/输入范围/计量方法依据，证明实际 token≤U；确认当前 profile 的输出限制与非思考设置真实被支持 |
| 真实验收运行器 | Makefile:1–40 与现有 scripts 无专属生产模型显式 opt-in 命令；native 已有本地拒绝和受控 loopback 路径 | 可补一个只消费既有真实配置/任务/许可的 opt-in 验收入口及私有证据收集；没有生产 proof 前仍拒绝外发，不把新 runner 当证明 |

生产 Responses 当前完整字节是 model/input/stream/max_output_tokens/truncation=disabled/store=false/reasoning={effort:none}；Chat 是 model/messages/stream/max_completion_tokens/n=1/stream_options.include_usage（provider_budget.py:198–205）。不能假定 DeepSeek 某个“兼容”端点支持这些字段。特别是把 max_completion_tokens 偷换成 max_tokens、移除 reasoning 或依赖默认设置，均不在当前证明/规范许可内（PRODUCT_DESIGN.md:1053–1055）。这里列的是待核兼容性条件，不是在未联网时判定 DeepSeek 实际不支持。

## 最短合规真实路径

0. **先补生产准入条件。** 为一个精确目的地、一个明确实际模型范围、一个现有窄文本 profile 做完整证据/checker，按现有内部可信端口注册。先本地证明未知目的地/格式/容量/别名版本/过期或撤回全部拒绝，旧 ACK/已完成结果仍只读。此步不需要读取用户 key。当前 60fa 尚不能越过这一步。
1. 在现有本机工作区与当前允许的会话中，打开一个真实公开测试 block/lesson。若无材料，走现有导入/发布路径创建一句原创说明，例如“本段只用于软件连通测试，不含私人资料”；不要 fake ContentRef。选最小附加范围、web_search=false，不进入 independent/open_book 受限状态。Tutor 允许 lesson 上的 block/lesson 精确 ref（tutor_dto.py:77–103）。
2. 使用现有实际 Provider config（PUT /api/v1/providers/{id}/config；GET 同路径，GET /api/v1/providers/capabilities），由正常 SecretStore 消费既有秘密引用。审计/验收程序不接收或打印 raw key。若既有本机 secret 实际不可用，应报告其独立事实，不把 proof 缺口改写成缺 key。当前核查不执行这些端点。
3. POST /api/v1/threads 得真实线程；POST /api/v1/tutor/runs，绑定原 thread revision、workspace、精确 context，question 可为“请用一句话复述本段用途”，web_search=false、consent_id=null。worker 本地冻结 Context 后 GET /api/v1/runs/{id} 显示 awaiting_approval（tutor_dto.py:213–238；tutor_worker.py:118–131；interfaces/tutor_http.py:140–170）。创建任务本身不外发。
4. POST /api/v1/consents/preview 只给真实 job/provider ID 与当前 revisions、到期、明确预算。用 proof 算出的 U 决定 max_input_tokens，给很小但实际可用的输出上限、max_provider_calls=1、search/tool=0；价格未知如实显示，不伪称费用硬保证。核真实目的地、材料摘要、冻结请求/proof hash、预算后，按现有明确操作 POST /api/v1/consents（proposal_id+proposal_sha256）。既有用户授权不需要再泛问“是否测试”，但此确切实例仍走平台冻结批准流程，不能造 consent。接口定义在 interfaces/provider_http.py:77–152；原事务在 consents.py:50–102、167–208。
5. 同一个 Run/job 的 worker 经 CheckedDispatch 执行恰好一次受控传输。dispatch 在开始前重新 verify 配置/material/proof/lease/consent，才读秘密并保留唯一开始事实（provider_dispatch.py:168–218）。收集 SSE GET /api/v1/runs/{id}/events、GET /runs/{id}、GET /threads/{id}/messages 与 owner 原结果，记录 provider receipt/dispatch/request hash、真实 usage、原终态与拒答/部分输出。刷新/重启只回读，不补发第二次；模型回答正确性、来源和学习效果另验，不要求为首次 Tutor 软件连通测试做 Single publication 或物理数值运行。

在**未经修改的 60fa** 上，合规实际路径只能完成第 1–3 步以及第 4 步的安全拒绝/取消；不存在用已提供 key 就能绕过空生产 registry 的合法操作。不能把 standalone SDK/curl 冒烟接到 Agent 的完成回执上。

## 可检验的本地阻塞与反例

本次只读代码/测试源，**没有重新执行测试，也没有新的 PASS 数字**。以下是固定源码中现成的可运行断言，不是本次实测结果：

- tests/unit/test_provider_budget.py:13：config.configured=true、secret_present=true、secret_available=true，仍 empty registry → CAPABILITY_UNSUPPORTED；caps.chat/streaming=false。直接排除“补 key 就能跑”的解释。
- tests/integration/test_tutor_runs.py:303：真实 SQLite Tutor 准备 + 空 proof，preview 拒绝；Run 保持 awaiting_approval、latest_proposal_id/consent_id=null、不造 approval_required；实际测试服务 connections=0、requests=[]。
- tests/e2e/tutor.spec.ts:19–74：native 真实线程/Run/worker，预览 409 CAPABILITY_UNSUPPORTED、无 proposal/consent/result，可取消后刷新回读。fixture 使用不可调度的合成模型与合成 secret；它验证真实本地拒绝链，不是 DeepSeek 贯通。
- tests/unit/test_provider_proof_binding.py:17–112：另一 host/port/path、另一模型/策略、过期、旧格式、隐式/变更 thinking 均不能继承原 proof；精确规范化不进行 DNS。
- tests/integration/test_provider_proof_admission.py:46–143：模型映射变化/到期/withdrawal 拒绝新 preview/grant/dispatch；原 proposal/ACK/已完成结果保留且不重新联网。
- tests/integration/test_provider_dispatch.py:240–273：proof_missing 等变化使真实测试服务零 connections/requests，且没有 dispatch 行。
- tests/e2e/tutor.spec.ts:160–223：完整一次许可→Provider→Tutor→native UI 的网络服务为 test_only=true 的完整字节模型；其结果明确禁止宣称 production proof/vendor/answer-quality。它可证明链路工程，不能产生托管证明。
- tests/fixtures/provider_recipe_0_1_1/manifest.json:1–11 与 tests/unit/test_provider_reference_events.py:1–37：官方 wheel 的语义事件生成样例使用合成后端 chunks/虚构 usage，binary_source_equivalence=NOT_PROVEN；不是实际 HTTP 模型、计量依据或托管协议等价证明。

既有独立供应商 HTTP 冒烟即使发生过，也最多证明该调用的连接/鉴权/响应。它没有通过当前平台 source→InputProof→proposal→consent→dispatch→Tutor owner 链，本次不读取旧私有凭据/响应档案，也不重申其 PASS 为独立核验事实。

## 现在可继续的本地工作

1. 固定一个生产 profile 所需证据清单和离线 checker 测试向量，逐项对应上述 endpoint/model/完整格式/capacity/失效要求。来源材料不足时写具体“缺该字段的供应商依据”，不要写泛泛“请用户上传证明”。本次仅仓内审计不能替代后续公开供应商依据核查。
2. 在现有 InputProof/ProofRegistry 内实现审过的生产 checker/固定 composition；保留未知/过期/错 endpoint 拒绝、历史 ACK 只读、完整请求字节不追加等测试。依据未到位的注册不得启用。无需新 DTO/route 或自动环境读取。
3. 准备原创非私密 Tutor 测试材料、固定 question/范围、单调用预算和私有 receipt 清单；补显式 opt-in 真实验收入口，读真实非秘密元数据并走同一平台流程，不照抄 loopback proof 或把真实 key 注入测试 fixture。
4. 独立保留与执行本地拒绝、授权/恢复、UI 与既有 M6.2 owner 工作；生产 InputProof 不应阻塞这些无外发可验证工作。真实 DeepSeek 平台验收在 proof/目标 profile 条件满足前记 BLOCKED；该次付费外发尚未执行记 NOT_RUN。

## 第一轮仓内审计操作范围

仅读取 canonical 规范、固定提交代码及测试。没有修改仓库、main/远端/progress/canonical，没有导入应用工厂、运行数据库或测试、读取环境/密钥/用户数据库、网络检索或调用任何外部模型。证据快照仅固定源代码与本报告；未复制依赖或私有运行数据。两次探索命令有路径定位错误（初次猜测 routers/ 目录不存在，实际为 interfaces/）；不是软件失败，已用实际路径完成复核。原 gate/失败日志不受影响。


## 追加：当前官方公开材料取证（2026-10-02）

取证窗口为 **2026-10-02 15:24:56–15:29:16 UTC（北京时间 23:24:56–23:29:16）**。14 个官方资料 URL 已使用无鉴权 GET 实际抓取 HTTP 200；每项开始抓取时间、最终 URL、原始字节数和 SHA256 在 web/fetches.json 与 web/fetches-extra.json，原始 HTML/Markdown/JSON 和便于定位的纯文本均保留。公开搜索/open 曾对数个 DeepSeek 文档返回 timeout，后来直接抓取同一公开文档成功；这些工具超时不作为供应商 API 不可用证据。没有请求 api.deepseek.com 的模型/计数/账户接口，没有读取 key、环境或本机数据库，没有装依赖或执行下载内容。

**本轮结论：已有重要正向资料，但仍不足以据此启用满足 §20.5 的生产注册。** 不能继续泛称“DeepSeek 不支持 Responses/无思考/输出硬限”。它们已有官方文档依据。真正未闭合的是固定公开编码器、完整托管输入处理和可变 API 别名之间的受检计量关系及其有效性。

| 规范所需事实 | 当前官方证据 | 审计判断 |
|---|---|---|
| 实际 HTTP 形状、关闭 thinking、输出上限 | [Responses API](https://api-docs.deepseek.com/api/create-response/) 的 reasoning.effort=none 关闭 thinking，max_output_tokens 约束可见及思考输出总和；[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/) 一致 | 此两点有正向依据，不能列为全无证明。web/responses.txt:416–451、thinking.txt:41–50；抓取 15:26:18 / 15:26:28 UTC |
| 不存储、不静默截断 | [Responses compatibility](https://api-docs.deepseek.com/guides/responses_api/) 把 store、truncation 列为忽略的字段，同时写恒 store:false、超上下文返回 400 | 不能因字段被忽略就声称行为一定违规；当前说明支持所需结果语义，仍需与完整 profile 一起审核。web/responses-guide.txt:493–523；15:26:18 UTC |
| 当前别名实际模型 | [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) 当前列 deepseek-flash→DeepSeek-V4.1-Flash、deepseek-v4-pro→DeepSeek-V4-Pro-0813，官方 OpenAI base URL 为 api.deepseek.com | 当前映射有资料，可作为版本范围审查输入；不是永久固定 hash 的部署承诺。web/pricing.txt:39–59；15:26:18 UTC |
| 别名更替/失效边界 | [Change Log](https://api-docs.deepseek.com/updates/) 明确旧 Flash 别名转到 V4.1，并更新为 9/14 后继续提供 Pro；[9/10 新闻](https://api-docs.deepseek.com/news/news260910/) 仍保留届时 Pro 全量转 Flash 的旧计划 | 新闻计划与当前 changelog/pricing 不一致，应优先当前具体更正且保留矛盾，不能从旧新闻静默注册 Pro→Flash。已有实际变更史支持“变化即撤回重审”，但未提供让本地注册始终覆盖未来路由/格式的机制。抓取均 15:28:38–39 UTC |
| 完整消息转换/编码工具 | 官方 [V4.1 model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) 提供 reference encoding 并链接 recipe；[recipe README](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/README.md) 支持 Responses/Chat→Conversation→V4/V4.1 prompt/token IDs，推理与 HTTP 由调用者实现 | 已有可工程实现的完整格式工具，绝非只有裸文本 tokenizer；但所读官方文件没有声明“这个固定 commit 的转换+tokenizer 就等于 api.deepseek.com 当前服务对本 profile 的全部真实输入计数/上界”，也未给隐藏附加处理的硬上限。这是核心未证实关系。model 15:26:28 UTC；pinned README 15:28:37 UTC |
| tokenizer 的模型/版本来源 | [tokenizer 使用说明](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/docs/tokenizer.md) 要求匹配模型；[v41 provenance](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/static/tokenizers/v41/README.md) 指向修改过 image-token 的 Vision-Exp 比较版本，并保存固定 SHA；[当前 Flash config](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/tokenizer_config.json) 公布特殊 token 与 model_max_length | 可以固定官方公开 artifact 并做离线验证，但 provenance/同系列不能自动成为托管 API 等价证明；特殊 token 字面量、system/assistant 边界、参考材料分隔符也必须在完整允许形状内覆盖。抓取 15:28:37–39 UTC |
| 离线计量的官方承诺 | [Token & Token Usage](https://api-docs.deepseek.com/quick_start/token_usage/) 提供字符经验比例、离线 tokenizer demo，并将实际用量落在响应 usage | 该页未给完整 Responses 请求的逐字段格式上界或隐藏开销上界；不能拿比例、任意 margin、事后 usage 替代外发前证明。页面最后的估算免责声明属于 image 小节，本报告不错误推广成“官方说所有离线文本 tokenizer 都不准”。15:26:18 UTC |

公开模型资料已经足以启动**离线工程核验**：固定 recipe `8cadfede7063c896b944e7bae05daa3549ae97ea` 与相应 tokenizer/模型材料，审当前七字段 Responses profile 的转换、容量与特殊 token 处理，形成拒绝未知字段/不完整转换的 checker 测试向量，并把该已核子集的准确 source/artifact SHA 冻结。但在下列关系闭合前，不给出可启用的生产 registration：

1. **完整计量关系未证实：** 对允许的全部消息/证据文本，官方托管服务的真实完整输入计数必须等于固定 checker 的数值，或有可证明不低估的上界；当前资料展示公开 reference format，没有证明托管附加指令、规范化和特殊 token 处理均被覆盖。本文不通过有限 API 样本推断全输入证明，也不发远端 count 请求。
2. **当前版本与有效性仍需工程绑定：** 已有当前 Flash/Pro 名称映射与变更史，仍需把准入范围限定到上述计量依据实际覆盖的版本，并建立可审的更新撤回/失效操作。只写 valid_until=明天或轮询一个没有部署格式身份的名称，不能补第一项证明。Pro 官方旧新闻冲突需明确处理，不能拿互相矛盾的两个映射任择其一建立宽授权。
3. **尚无平台生产实现：** 即使未来这些依据齐备，60fa 的生产 registry 仍是空的，尚无经过审查的生产 checker/composition 与真实 opt-in 验收入口。这个可实现工程工作不用再索取 key，也不应包装成“等待用户授予 InputProof 权限”。

本报告不以搜索未找到断言官方绝对没有其他材料；结论严格限于已抓取的官方 API、更新日志、官方模型卡和固定 recipe/tokenizer 文档。没有依据足够的 production 注册方案可在本轮启用。真实平台调用保持 BLOCKED（InputProof 未闭合/未注册），外部模型执行仍 NOT_RUN；本地准备/拒绝/取消与其他已授权实现工作可继续。
