M5.4 DeepSeek V4.1 Responses 最小工程差距（只读，未采纳/未放行）

核查日2026-09-15。依据当前唯一 PRODUCT_DESIGN 3.0.4（SHA 9cc5adbe72edfc993b5d5e99dcb3f9436e475ab2be4dd58e83f72e3104353b9c）§20.5/附录D；B memo仅是官方资料线索。当前 main.py:54–56 已组合真实 Tutor source，但生产 ProofRegistry 仍空，DeepSeek 目前不可调度。没有读key、模型调用、安装、执行tokenizer、运行产品测试或修改注册。

可离线完成的最小步骤：

1. 固定窄请求形状与版本。provider_budget.py:141–165 当前发送 {model,stream,input,max_output_tokens,truncation,store}，不含 reasoning。固定官方 [Responses convert.rs:580–598](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/deepseek-recipe/src/protocol/openai/responses/request/convert.rs#L580) 把 reasoning.effort="none" 转为 thinking=false；缺省取 caller 的 ConversionOptions。因此不能把现请求当“已关闭thinking”。最小候选是受检 DeepSeek Responses profile 显式冻结该字段，版本化请求构造器与证明范围；只收现有 system/user/assistant 字符串，无工具/图像/JSON模式。不得派发前临时补字段。形状变化由同一原 summary/request hash 验证。

2. 补真实供应商身份绑定。provider_budget.py:40–90 的 InputProof 只有adapter/model/version/容量/evidence/check(body)，registry仅按(adapter,model)查；check看不到endpoint。若直接注册deepseek-flash，任意其他配置host上的同名字也会匹配。生产profile准入前须把受信的 scheme/host/port/path、实际模型/别名版本范围、失效条件纳入受检依据和resolve；未知host/version拒绝，不能依靠“摘要里已有base_url”证明该host服从DeepSeek规则。provider_network.py:24、provider_transport.py:24–41 现有TLS/DNS绑定、无redirect/retry须保留。此为生产准入前工程缺口，当前空registry尚未造成放行。

3. 对固定完整转换与tokenizer做离线证明审计。下载与核对精确recipe commit、V4.1 encoder和词表/许可证/依赖锁定后，在隔离环境审计实际canonical request→Responses conversion→Conversation→V41完整prompt→token IDs；不是JSON字节数或逐段正文计数。覆盖当前最多6基础消息+8完整reference消息、总12k字符、历史assistant拼接、role边界/BOS/special-token样式文本、中文/Unicode/换行以及拒绝超形状。保留原正文；以完整冻结body做checker输入，证明材料和checker版本进入InputProof.sha256。当前 tests/provider_protocol_fixture.py:30–57 的“完整JSON每字节一token”仅人工测试模型，绝不可复用成DeepSeek证明。[官方V41词表来源说明](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/static/tokenizers/v41/README.md) 给出预期SHA，但此次没有下载或独立核词表。

4. 用官方格式建立离线协议金样和失败反例。provider_responses.py:32–139 要求seq从0连续、模型精确相等、一个assistant message/output_index=0、内容/终态逐字一致；reasoning/tool/annotation会拒绝。固定官方 [chunk_generator.rs](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/deepseek-recipe/src/protocol/openai/responses/response/chunk_generator.rs) 是可审计金样来源：序号从0递增，并有独立reasoning item。仅在明确none的窄profile内验证现parser是否直接兼容；不把未知reasoning改成答案，不为兼容吞帧。覆盖完整/截断/失败/拒答若该协议真实提供/无终态EOF/纯空白、错model/seq/part/hash、未授权工具、partial保留和usage。官方网页只说seq单调递增，不能据此独断托管API必定完全复制此generator。

5. 冻结容量和资源边界，再跑现有预算/账本负控。InputProof须有实际max_input/max_output/shared_context规则，要求U+输出硬限≤C；现provider_budget.py:98、172已检查已知usage与预算。新profile要验证max_output_tokens与总输出计量（含reasoning若存在）的语义，明确cached input不另加一次。provider_sse.py还限制总流8MiB、单行256KiB、帧1MiB、文本4MiB；不能因供应商宣称384K输出就注册到现流缓冲无法承受的范围。用小范围先验证；满预算/坏proof/超输入/失效授权/错误origin/取消/原ACK/唯一dispatch/部分产物恢复仍用真实SQLite+合成loopback，不需要供应商调用。

仍缺供应商依据、不能由离线测试制造的准入关系：

6. 托管格式等价或严格上界。固定公开转换/完整tokenizer存在；尚未建立 api.deepseek.com 当前deepseek-flash实际部署与固定转换、隐含系统格式、预处理、tokenizer、模型别名版本逐字等价关系，也未取得覆盖差异的严格上界。官方源码 [schema.rs:3–7](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/deepseek-recipe/src/protocol/openai/responses/request/schema.rs#L3) 仍将model resolution等交给caller。这是需要明确官方依据/可审查证明的关系，不是“没有开源编码器”。若不能证成，完成1–5也仍保持生产proof不注册、preview不可批准、零传输；平均误差/安全余量/事后usage匹配不能替代。

7. 明确线上协议事实的剩余验收。官方 [Responses说明](https://api-docs.deepseek.com/guides/responses_api/) 支持max_output_tokens和completed/incomplete/failed；store/truncation参数本身不受支持且未知参数可能忽略，只能引用其固定store=false、超context400的文档语义，不能称发送字段就强制服务端遵守。需核真实API对none、model回显、终态/usage和输出硬限的支持范围。授权小预算调用只能在6的输入准入成立后执行，用来检验真实行为/质量并单独记录；经验成功本身不回填输入证明。若供应商无法给出所需关系，应向root精确报告不满足当前规范，而不是悄悄放宽它。

建议文件边界：Provider owner新增受检模型profile/证明材料与checker，修改provider_budget.py的profile绑定/实际body构造；仅遇真实金样差异时窄改provider_responses.py，保留provider_sse.py安全约束；对应test_provider_budget.py/test_provider_protocol.py/test_provider_dispatch.py增加离线反例。main.py最后才由root按实际证明注册。无需改core54、Tutor持久模型、M6或搜索工具；文本无工具验证通过仍不等于M5.4“真实搜索评测”完成。

本记录中的官方Responses/词表页面由B于同日抓取，D已核原始文件SHA；D另只读访问了固定commit的Responses request convert/schema与response chunk_generator，未执行这些源码。具体访问/当前产品源hash见receipt.json。全部动作是准备性审查，不构成实现/测试/发布成功。
