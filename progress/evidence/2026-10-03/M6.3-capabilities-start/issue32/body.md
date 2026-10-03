<!-- task_id: M6.3 -->
task_id: `M6.3`

spec_version: `3.0.0`
spec_sha256: `ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`

唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。

需求 ID：R-23, R-27

目标：CodexBroker/App Server、操作审批、产物清单

依赖：M6.2

修改范围：规范对应模块、契约、测试和脱敏工程进度。

验收清单及预期证据：
- [ ] M6.3: 拒绝操作零执行，路径逃逸阻断，成果预览回导


未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。

实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。
经审查/合并后才关闭任务；当前清单不表示已经验收。

<!-- engineering_progress:start -->
当前实际状态：`in_progress`
规范：`3.0.13` / `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`
当前需求关联：R-23, R-27
验证代码：`NOT_RUN`
验证：`固定本机codex-cli0.160.0离线schema实际生成314文件exit0，非真实模型验收。无turn能力探测/严格GET/真实UI切片开始实施，未声称接口或门禁PASS。`
实施分支：`feat/M6.3-codex-capabilities`
下一动作：按§12.5/A2193实现受检Broker运行上下文的真实能力/授权探测、GET /codex/capabilities与创作入口状态；无安全探测时明确不可用/未知，不假报授权。保留session/审批View/产物manifest待闭合范围，零模型turn。
<!-- engineering_progress:end -->
