<!-- task_id: M5-milestone -->
task_id: `M5`

spec_version: `3.0.1`
spec_sha256: `397829f5267248aedfc60faf7cacbb12669966b1c1d636a909b04189e0cc09dd`

唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。

需求 ID：R-15, R-16, R-17, R-18, R-25, R-27, R-29, R-38

目标：ProviderPort、权限、RAG、联网、SSE、费用和失败恢复

依赖：无；总任务按子任务依赖推进。

修改范围：规范对应模块、契约、测试和脱敏工程进度。

验收清单及预期证据：
- [ ] M5.1: 无授权零外发；兼容 chat 不冒充 search
- [ ] M5.2: 私有答案过滤、旧索引、中文检索基准
- [ ] M5.3: 终态唯一、断连不重生成、切标签不串内容
- [ ] M5.4: 显式授权小预算调用；引用回查；无凭据 NOT_RUN


未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。

实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。
经审查/合并后才关闭任务；当前清单不表示已经验收。

<!-- engineering_progress:start -->
当前实际状态：`todo`
规范：`3.0.1` / `397829f5267248aedfc60faf7cacbb12669966b1c1d636a909b04189e0cc09dd`
当前需求关联：
验证代码：`NOT_RUN`
验证：`NOT_RUN`
下一动作：按子任务依赖推进。
<!-- engineering_progress:end -->
