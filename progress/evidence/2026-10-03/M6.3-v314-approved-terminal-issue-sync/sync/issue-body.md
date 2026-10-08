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
当前实际状态：`in_progress`；M6.3 未完成，Issue 保持 open。
唯一规范已按所有者明确批准采纳 v3.0.14：`bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`；本地提交 `b3f94b38c1f6f518bfca303cd87386fb6477669f`，尚未推送。
已实现控制能力读取：固定受检 Broker、当前账号元数据安全投影、显式 UI；approvals/interrupt/artifacts 全 false，无模型/turn/tool 执行。
历史固定组合 `ad49490e78c21174349595da8090c6c2b445bce9` 完整门禁：Web 984 PASS，strictTS/build841/Ruff/mypy241/spec PASS；Python **3633 PASS、2 实际数值 ENVIRONMENT SKIP、1 setup ERROR、exit1**；native **126 PASS、1 FAIL、exit1**。各执行工程输入与 Git 绑定且前后不变；原失败不被 subset 覆盖。
Python ERROR 是 assessment 生成 fixture 在 worker.run_once 返回后仍 running，tamper 用例正文未执行，原因尚未确立。native FAIL 是 Import 独立策略用例初始会话保存未出现，原始 bootstrap HTTP 未保留，原因 UNKNOWN。
独立扩展安全探针与随后 UI 诊断被自动安全检查中止（possible cybersecurity risk），NOT_RUN；未重启或转派，不称整体安全审查成功。已确认 Unix/SysV IPC、FIFO、深 JSON 缺陷的原 RED/GREEN 和静态复核保留。
批准后的新增范围正在隔离实施：session 准备/只读回读/单次决定、空 actions 冻结许可一次消费、真实控制 thread 映射及 unknown 回读；准备/GET/决定零 CLI。新合同的真实 session 目前 NOT_RUN，不能由 capabilities 或 schema 证明成功。
证据已本地封存，当前 M6.3 代码与新证据尚未公开推送。公开仓库保留既有 M6.2 e287 源码，PR55 draft/open/unmerged；该 head 的两个实际 CI 各6/6 SUCCESS，不替代此 M6.3 失败门禁。
阻塞仍分开：物理数值环境 BLOCKED、托管完整输入计量 ProofRegistry 未闭合而真实平台 Provider NOT_RUN；不是 key 认证失败。
下一任务：推进已批准 v3.0.14 后端/界面/真实受限控制验收；诊断后台完成语义，整合后重跑相关及必要完整门禁，公开对象检查后创建可审阅 draft PR。无合并、release 或公网部署。
<!-- engineering_progress:end -->
