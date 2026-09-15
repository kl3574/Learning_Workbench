# M5.4 DeepSeek 有界只读准入资料核查

读取日：2026-09-15 UTC。14:13起开始资料读取，中间按根指派暂停以修复 M5.3 Jobs HTTP500，14:28恢复后收束。仅公开官方资料；未读 key、未调用模型、未安装/执行官方代码、未注册生产 proof、未改变规范/产品。M5.3测试与本备忘录互不构成验收替代。

**结论：不能把“V4.1缺少开源编码器”当阻塞理由；V4.1编码和tokenizer材料已公开。但本次没有建立托管API完整输入计量的可注册证明，当前Chat适配器的硬限字段也与官方文档不匹配。缺口是格式/版本及完整计量证明，不是用户权限或缺key。Responses是有官方协议支持的候选，不等于当前实现已经对该生产模型通过准入。**

1. 当前模型身份。直接读取[官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)确认deepseek-flash为DeepSeek-V4.1-Flash，1M上下文、最高384K输出。旧deepseek-v4-flash及vision-exp名字仍接受，但已路由V4.1。该页同时写V4 Pro在9月14日后继续服务；不能把较旧公告的Pro退役计划当今天事实。这是文档当时状态，未调用模型检测返回版本。

2. 完整格式的正向资料。[V4.1官方模型卡的Prompt Encoding](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/README.md)明确没有Jinja模板，提供独立Python encoding参考和生产用deepseek-recipe；短摘录：“the same prompt format”。[固定recipe提交README](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/README.md)和[固定V4.1编码器](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/deepseek-recipe-encoding/src/v4/dsv41.rs)实际包含V4/V4.1请求转换、prompt/token IDs；V4.1首个thinking消息还加入effort模板，不能只逐message正文分词。[tokenizer说明](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/docs/tokenizer.md)要求使用对应tokenizer，并防止重复添加special tokens。此次未下载6MB词表或执行tokenizer。

3. tokenizer来源边界。实际原件[v41 README](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/static/tokenizers/v41/README.md)列出本地词表SHA81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99，并与DeepSeek-V4-Flash-Vision-Exp的6821d6ad3681a4b137b066b76094fa82ebd0a380作比较，仅image token处理不同。此为维护者的文件来源/对应说明，不是本次下载校验的词表结果，更不是托管API对固定模型别名永不改变预处理的承诺。

4. 输入proof仍待完成的具体关系。需固定实际发送JSON、协议转换版本、thinking默认/effort、所有role/boundary/BOS及系统格式、tokenizer SHA及模型版本，再给出整个最终prompt exact count或严格upper bound及最大输入/共享窗口依据。已读资料足以开始离线编码审计，却未提供一份可直接采纳的完整请求计量证书或对所有服务端额外格式的有据上界。公开recipe将推理/HTTP留给调用者；本次未取得明确的托管api.deepseek.com处理链与固定源码逐字等价保证。此为本次证据未闭合，不断言互联网上绝不存在补充材料。粗略字符比例、只计正文、使用旧V4 tokenizer、运行后usage都不能替代规范要求的外发前proof。[官方token usage](https://api-docs.deepseek.com/quick_start/token_usage/)给离线demo入口，但未在该页绑定当前V4.1托管完整请求格式；页面末尾estimate提示位于image小节，不将其扩大引用为所有文本分词均只能估算。

5. Chat输出硬限。当前[Chat API参数](https://api-docs.deepseek.com/api/create-chat-completion/)明确字段max_tokens，范围1..393216，并说明输入加输出受context约束；已保存原页无max_completion_tokens字段。更直接的[官方oh-my-pi集成说明](https://api-docs.deepseek.com/quick_start/agent_integrations/oh_my_pi/)短摘录：“DeepSeek uses max_tokens, not OpenAI's max_completion_tokens.” 固定recipe的[Chat schema](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/deepseek-recipe/src/protocol/openai/chat_completion/request/schema.rs)及[转换代码](https://github.com/deepseek-ai/deepseek-recipe/blob/8cadfede7063c896b944e7bae05daa3549ae97ea/deepseek-recipe/src/protocol/openai/chat_completion/request/convert.rs)也只用max_tokens。故不能给当前本项目兼容Chat发送max_completion_tokens的路径注册DeepSeek“已支持硬限”能力。本次没有请求API证明它实际拒绝或忽略该未知参数，准确结论是官方支持依据相反/不满足现准入。

6. Responses。官方[Responses API](https://api-docs.deepseek.com/guides/responses_api/)明确支持deepseek-flash及max_output_tokens、语义SSE事件和completed/incomplete/failed终态，不使用[DONE]。store不支持但回包固定false；truncation不支持且超context返回400；不支持参数可能静默忽略。因而不能靠发送store:false/truncation:disabled两个字段就宣称服务端遵守字段；只能依赖官方声明的实际无存储/超限错误语义并核对版本。协议还包含thinking/reasoning事件、usage子项，需严格映射而不把未识别思考当答案。这里只确认官方协议可用依据；没有确认本项目当前parser/成本/完整proof对该模型已验收。

建议下一任务：优先对固定V4.1文本-only、无工具的Responses请求做离线完整转换/词表/格式审计，记录可证明的覆盖边界和版本；若要走Chat，先按唯一规范的变更流程明确max_tokens能力映射，不能静默弱化为已支持max_completion_tokens。若托管格式等价/严格上界仍无法证成，保持无生产proof、外发零传输。上述建议不构成新规范或实施授权。

抓取失败保留在sources.json/pinned-sources.json/last-sources.json（rawGitHub timeout、HF raw连接错误）；模型卡通过web读取成功，不能把raw失败写成网页无内容。所有直接获取原件以URL、读取时间、大小和SHA记录。HTML转text仅为本地阅读派生（去标签、HTML解码、合并空白），不替换原件。
