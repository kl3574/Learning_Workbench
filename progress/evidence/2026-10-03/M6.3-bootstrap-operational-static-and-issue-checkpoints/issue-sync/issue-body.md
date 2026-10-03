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
当前实际状态：`in_progress`；M6.3 / AC-21 未完成，Issue 保持 open。
唯一规范 v3.0.14，所有者已批准375e55c0并采纳：`bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`。本地控制切片 allowed_actions=[]、三flags=false、active_turn_id=null；不授予模型、turn、账号登录、工具或学科读取。
后端固定 `df0bc6188745cf96aed4b68e52737dab492758d4`：264相关PASS、Ruff/mypy250/结构80 PASS；107 bootstrap测试包含在264中，不相加。root独立核1365完整非progress工程输入前后逐Git及642原件/140明确候选。五个真实端点、原actor/权限/CAS/完整命令/只读历史、一次消费及owner结束恢复已实施；不是完整后端门禁。
生产固定 `04500f20fd9727d9b15da081e820bbd81a780fad` 真实受限控制：通过实际HTTP prepare→GET→approve→GET→consume取得 **201/r2 ready**；恰1固定CLI，0.963秒；原201 ACK及同数据库应用重建回放逐字一致，零新start。root独立核1364完整Git输入和实际runner绑定。ready仅是已核验本地thread映射，不是模型调用、账号授权、当前进程仍运行或完整Broker完成。这是TestClient/应用重建，尚不是浏览器或API OS重启。
profile-v3保持原三帧请求、受限配置和资源。离线固定CLI schema导出440文件逐hash读回，四个所选schema字节绑定源码；仅补全实际返回metadata与匹配thread/started通知的严格观察，不开新RPC。原三个真实v2 unknown实例未升级/重跑，v3只读回保持全部八张owner表不变。原RED/FAIL、早期WIP不可完整重建限制及脚本错误均保留。
原固定366 owner文件P2由852锁顺序修改静态闭合；31补四终态文件数量检查并由最终264 gate实际执行。它不代表完整运行时安全审计。
UI固定5d07完整Web1037/145files、strict/build PASS；root独立读回63白名单/1369工程输入。新native组合a2d9第一次0retry执行 **FAIL**：首次读取本地记录后未退出初始提示，尚未到prepare/create，浏览器thread **NOT_RUN**。原日志/截图/完整输入保留；新的受控父面板测试复现false→true初始准入取消合法只读响应，小修a480已固定并独立读代码，现按新源码重验同字节新case，不改旧测试/超时或抹掉原FAIL。
root组合 `dcfda8c270dff3e6db75011c50ffa7d6f5826512` 含后端/UI/new-native/root备份4；同提交detached完整Python收集3688项，当前 **RUNNING**，无终态PASS承诺。当前canonical已机械采纳两文件UI修复为 `7b0ee3ae7d94a0d069b873133e69b5aaf3a18c89`，1381非progress输入逐Git不变，Ruff/mypy250/结构80 PASS；后端源仍与dcf相同。
root固定c73真实备份CLI对四种合成Codex历史4PASS，1374工程输入前后逐Git；八张Codex表/原actor保留，旧cookie401，新actor不得继承旧许可/命令。不是实际Codex或完整M7.1恢复验收；私有DB/ZIP未公开。
历史ad494完整Python3633PASS/2实际数值ENVIRONMENT SKIP/1setupERROR/exit1与native126PASS/1FAIL/exit1仍为原失败记录。受控租约诊断不关闭它们。扩展安全审阅和旧native诊断因自动检查 possible cybersecurity risk 中止、NOT_RUN，未重启或转派；不称完整安全审计通过。
新M6.3源码/证据尚未push；本地分支feat/M6.3-local-control-bootstrap。PR55仍draft/open/unmerged、head e2877101，既有M6.2双CI各6/6SUCCESS不替代本阶段门禁。物理数值环境BLOCKED，生产托管Provider完整输入计量ProofRegistry未闭合，真实平台Provider NOT_RUN，非key认证失败。
下一任务：收集修复后新native、完整Web与组合完整Python实际终态，按故障证据修复/验收，再检查公开内容和全部新增对象、发布可审draft PR；无merge/release/deploy。
<!-- engineering_progress:end -->
