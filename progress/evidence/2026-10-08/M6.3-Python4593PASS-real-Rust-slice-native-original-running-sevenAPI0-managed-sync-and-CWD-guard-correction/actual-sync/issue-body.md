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
M6.3 当前实现与验收仍未完成；真实模型 Agent / AC-21 未接受，M7保持todo。

本地工程2fcc7b18新增可复验 Codex HTTP 门控工具，最新进度提交c92fdf22；公开源仍4ca。仅新增scripts/codex-turn六个文件，原唯一规范v3.0.15与全部旧进度保留。平台完整运行源仍固定93c的1565个文件；新增工程工具独立验，不冒称1571文件完整门禁通过。

原完整 Python 在锁定工具链和task-private TMPDIR下单次取得实际终态0：4593PASS、2数值ENVskip、3warnings，4595collected/3081.36s。Root独立核66私有成员、完整日志摘要/两skip原文与源码行、all1565 Git/index/live前后exact。两项真实sealed calculator/Restore仍BLOCKED_ENVIRONMENT，不算数值PASS。原2090P500F2004E、4587P6F与旧59677无终态中断全部保留；原make setup后6PASS仅局部结果。

Python终态后原完整浏览器make test-e2e已单次独立后台运行：133case、1worker、原30s、retry0、只task-private短TMPDIR，当前真实ownedwrapper/make身份核对RUNNING，最终退出码/计数未知。case15在原5000ms completed poll收到running失败；后时间只读fixture记录Provider error=TIMEOUT但不能解释原deadline根因。实际Chat stop字段即可产生provider_outcome=completed，不证明完整SSE或durable结果；本地DB等待也可用同TIMEOUT代码。原因UNKNOWN，不放宽断言或自动重试。原native65P68F/exit2保持。

真实固定上游a956835d的HTTP切片已实际编码编译并纳入可运行工程补丁：原EncodedJson/into_prepared bytes与allocation冻结、实际send前不可退回单次claim，限制HTTPS Responses POST/正整数输出硬限/disabled truncation，排除重定向、重试、代理、晚注入headers及caller framing。专门8PASS/0FAIL；完整库114PASS/6FAIL/exit101保持，未改基线106PASS/同6FAIL，不能推定纯环境根因。旧02的7个拒绝负例真实RED保留。新replay实际prepare-only两Git0/零Cargo，默认lockedoffline8PASS/0FAIL/112filtered0；安全解包/既有输出拒绝、publisher/diff/Ruff均过，独立Spec/Standards0P1P2。

此切片尚未接实际AppServer完整producer、持久permit、真实输入/容量计量及完整运行资源/DNS连接边界，生产仍NOT_ADMITTED/defaultproof空/executorNone。下一共享同步producer正在独立源码副本编码；没有CLI/模型调用。已有Key和费用测试授权有效，本阶段模型0；不读取或上传Key，不把缺实现写成缺许可。

公开4ca的原push整体FAILURE(browser132PASS1FAIL)，原PR整体SUCCESS(browser133PASS)，各integration2525PASS/2数值ENVskip；12原job终态与日志保留，运行期输入图未捕获，旧CI原因UNKNOWN。当前draft PR仍open/unmerged；本次只更新管理正文，不sourcepush/merge/release/deploy。

本地证据尚未推送：progress/evidence/2026-10-08/M6.3-fixed93c-original-complete-Python4593PASS-two-numeric-ENV-skips-detached-terminal-and-native-original-running/REPORT.json；progress/evidence/2026-10-08/M6.3-actual-upstream-HTTP-gate-eightPASS-full114P6F-baseline106P6F-sevenRED-and-runnable-bundle2fcc/REPORT.json。
<!-- engineering_progress:end -->
