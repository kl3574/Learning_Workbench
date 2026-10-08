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
本地固定组合：`ad49490e78c21174349595da8090c6c2b445bce9`（尚未推送 M6.3 源码）
验证：固定94be修复Unix/SysV命名IPC、FIFO配置阻塞、深JSON安全分类；68定向PASS/Ruff/mypy241及实际控制CLI/HTTP回读通过，原FAIL完整保留。独立静态delta未见新增阻断；独立10HTTP/6UI/strict通过。组合ad494完整Web984/strict/build841/Ruff/mypy241/规范检查PASS，1340nonprogress同Git；完整Python与native运行中。扩展系统级安全审查被自动检查中止，NOT_RUN，不转派重试，不宣称整体安全完成或M6.3完成。
范围：只有受检隔离 Broker 控制读取；三个产品能力仍 false。session/turn/审批/产物回导未实现。
原执行 HEAD1ab 与后来固定94be exact-input归因分开记录，不伪称当时运行HEAD94be。
公开证据：`progress/evidence/2026-10-03/M6.3-capabilities-start/REPORT.json`；修复/独审/当前门禁证据先在本地封存，待公开对象检查后推送。
下一动作：等待固定ad494完整Python/native结果，封存原件并独立读回，再按窄控制读取切片检查公开对象并发布draftPR；session/turn/审批/产物回导仍待后续实施。
<!-- engineering_progress:end -->
