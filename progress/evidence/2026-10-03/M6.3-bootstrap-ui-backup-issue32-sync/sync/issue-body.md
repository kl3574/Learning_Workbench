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
唯一规范 v3.0.14（所有者已批准）：`bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`；新增本地会话合同仅 allowed_actions=[]、三 flags=false、active_turn_id=null，无模型/turn/tool/教材读取授权。
隔离后端 `366d7b862379b3f3fa27808b04dbbd1b2694a6bc` 已实际注册三准备端点及原两 session 端点；它是中间候选，**NOT_ACCEPTED**。冻结部署闭包、输出预算、并发/恢复与真实受限控制验收仍在实施。独立静态审阅确认一项 P2：准入/原ACK回放前创建未登记 owner 文件，作者 WIP 调整尚待固定复核。
隔离 UI 实现 `356a9ade7b0136f93cad5d3cbd5170afd178c991`，生成传输及完整 Web 固定 `5d07c43851c84e4e1d8df12d7de52500293c1c3b`：**1037 PASS /145 files，strict/noUnused PASS，build849 modules PASS**。root 独立核63原件/白名单及1369前后工程输入逐Git一致。原actor晚到ACK可由同工作区合法读者显式仅本地保存，零POST/零执行权限继承；工作区晚到读取已受控修复。
root 独立组合固定 `c73cbcbb9b95205986373706205dfafcdce709b7`：真实备份 CLI 对四种合成 Codex 历史 **4 PASS**，1374工程输入前后逐Git一致；八张Codex表与原actor保留、源表/文件不变、旧cookie401，新actor不能消费旧许可或决定。无真实Codex进程/thread/model；不是完整M7.1恢复验收。私有DB/ZIP/认证材料未公开。
新的真实 Codex thread 与新 bootstrap native 当前 **NOT_RUN**；capabilities、协议模拟、UI测试及 fake thread ID 都不代替真实上游。ready 只有唯一实际受检映射落盘后才返回；未知结果不得第二次start，不能降低隔离或伪造201。
历史固定 `ad49490e78c21174349595da8090c6c2b445bce9` 完整 Python **3633 PASS、2实际数值ENVIRONMENT SKIP、1setup ERROR、exit1**；native **126 PASS、1 FAIL、exit1**。完整原失败与日志/source绑定保留。受控租约诊断证明既有安全拒绝与fresh-owner一次派发恢复，未确立生产缺陷或历史宿主时序原因；原native初始会话HTTP未保留，具体原因UNKNOWN。
扩展安全审阅和旧native UI诊断因自动安全检查 possible cybersecurity risk 中止，**NOT_RUN**，未重启/转派，不称完整安全审查通过。
本阶段新代码/证据尚未source push；已封存本地进度。GitHub PR55仍draft/open/unmerged、head e2877101；既有M6.2双CI各6/6SUCCESS不代替本M6.3门禁。
物理数值环境BLOCKED；托管完整输入计量ProofRegistry未闭合，真实平台Provider NOT_RUN，非key认证失败。
下一任务：固定并独审后端修订，按已批准范围验真实零模型受限thread；整合UI和备份回归，执行新native及适用完整门禁，再检查公开对象并发布可审draft PR。无merge/release/deploy。
<!-- engineering_progress:end -->
