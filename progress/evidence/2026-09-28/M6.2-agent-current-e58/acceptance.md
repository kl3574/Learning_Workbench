# M6.2 当前 Agent 功能核验

固定代码为 `e58abaaf4baa5b06d27bd1db1f06c8a13c1c730a`，唯一规范为 `PRODUCT_DESIGN.md` v3.0.7，SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`。原命令、原日志 SHA、公开日志 SHA、四个精确测试源 SHA 与实际输出见 `receipt.json` 和 `pytest.log`。四组受控 Tutor/Provider 集成及安全测试实际为 **53 PASS、2 条依赖弃用警告、13.87 秒**。测试覆盖本地 Run/读取/SSE/取消/幂等、受控 loopback 单次派发和证明失效阻断；它没有使用用户密钥，也不是托管 DeepSeek 模型质量或平台端到端验收。

当前生产装配在 `services/api/app/main.py:69-91` 使用 `RequestPreparer(ProofRegistry())`，无已登记的托管模型证明。`provider_budget.py:120-129,169-183` 对缺证明的配置关闭 chat/streaming 并拒绝准备；`consents.py:70-105` 只有在准备验证成功后才建立可批准提案；`provider_dispatch.py:184-199,211-218` 在派发前再次核验。测试专用人工字节 token 模型（`tests/provider_protocol_fixture.py:1-7,27-58`）不能外推为生产 DeepSeek 证明。

唯一规范 `PRODUCT_DESIGN.md:1027-1045` 要求实际完整请求在外发前具有绑定端点、模型/版本、格式、完整输入形状及失效条件的 `local_exact` 或有证 `local_upper_bound`。DeepSeek [官方 token 说明](https://api-docs.deepseek.com/quick_start/token_usage/)把离线计数称为估算，实际用量由响应返回；现有本地参考格式审计没有证明托管服务的完整输入等价。故真实平台 DeepSeek Tutor dispatch 为 **NOT_RUN**，不能为了试用密钥绕过预览准入。进度文件记有以前直接供应商 GET models/单次 Chat 的结果，但没有找到可独立复核的原始 HTTP 回执；该记录不算本轮平台实测。

下一项真实平台验收依赖一个可审计、可失效且可由当前 checker 验证的托管完整输入证明。M6.2 本地编辑、发布及影响复核工作不依赖它，可继续推进。
