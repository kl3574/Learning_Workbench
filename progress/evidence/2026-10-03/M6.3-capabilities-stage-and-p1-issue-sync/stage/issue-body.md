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
验证：`固定1ab后台61相关PASS/strict静态与真实隔离CLI控制探测PASS；实际HTTP两次200/同稳定Broker、配置变更503、全业务SQLite零写。组合54fc界面27focused/strict/native-types及真实native1PASS6.7s，1320nonprogress前后同Git；两次生产GET200 available=true/authorized=false、三能力false，重启同DB结果一致。原1ab合同全套731PASS1旧路由计数FAIL保留；test-only8d修111/19并18DTO反例共19PASS。独立代码/安全/HTTP审查及最终含e287组合全量门禁仍待完成。`
实施分支：`feat/M6.3-codex-capabilities`
- 证据：`progress/evidence/2026-10-03/M6.3-capabilities-start/REPORT.json`
下一动作：处理M6.3独立审查实际发现，组合最新e287、固定backend1ab、合同test-only8d与UI/native，完成一次最终全量验收，再同步源码分支与draftPR。仅连接读取，不继承全局CLI授权，未实现线程/生成/审批/中断/产物回导。
<!-- engineering_progress:end -->
