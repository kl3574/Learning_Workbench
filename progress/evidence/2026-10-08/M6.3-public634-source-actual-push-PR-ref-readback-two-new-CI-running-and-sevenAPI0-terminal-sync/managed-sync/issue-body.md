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
M6.3 当前仍在实施，真实 Agent / AC-21 尚未验收，M7保持todo。

公开草稿分支和PR56已实际正常fast-forward推送并读回63403908。新增评分读取修复：完整读使用WAL snapshot，发出受保护结果前在短事务中重新核当前Policy；新增固定上游Codex HTTP门控补丁及复验工具六文件。唯一规范v3.0.15未改。旧工作、失败和未合并PR均保留，未merge/release/deploy。

平台完整门禁运行源固定93c/1565文件，另六个Rust工程工具独立验证；不声称当前1571工程文件经过同一完整运行。原完整Python单次实际exit0：4593PASS/2真实数值ENVskip/3warnings，4595collected/3081.36s，all1565 Git/index/live前后exact。两sealed数值仍BLOCKED_ENVIRONMENT，不算数值通过。原2090P500F2004E与4587P6F、59677无终态中断保留。

原完整浏览器make test-e2e单次133case/1worker/原30000ms/retry0真实终态make2：132PASS/1FAIL/20.2m。唯一case15原5000ms等待completed收到running。截止根因UNKNOWN；之后TIMEOUT既可能涉及本地DB等待也可能总预算，远端stop字段不证明完整SSE/持久完成，不能拿晚记录解释原deadline。5个生成快照先私有冻结再guard恢复，1565源码exact，unknown/index0；223已观察owned PID关闭。原65P68F保留。下一步只增加安全grant/poll阶段观测，不放宽断言或自动重跑。

固定上游a956 HTTP切片实际8PASS/0FAIL；完整库114PASS/6FAIL/101保持，未改基线106PASS/同6FAIL，根因未证明。旧02七个负例真实RED保留。工程工具replay实际prepare-only两Git0、默认严格lockedoffline8PASS/0FAIL；安全解包负例/发布检查/diff/Ruff和独立Spec/Standards已过。当前共享纯Responses producer A+C仍在独立候选实施与验证，尚未纳入公开分支。

生产proof仍空/executorNone；完整AppServer producer、持久单请求许可、模型输入/容量计量及运行资源/DNS边界仍未齐备，NOT_ADMITTED，真实模型Agent/工具/内容质量验收未完成。用户既有Key和费用测试授权有效，本阶段实际模型调用0；不读取或上传Key，不将缺实现记成缺授权。

新634两次CI为实际in_progress：push37723654383、PR37723660353/attempt1，结果未定。原4ca双CI终态pushFAIL(browser132P1F)、PRSUCCESS(browser133P)及12原jobs日志全部保留；各integration2525PASS/2数值ENVskip，不能由PR绿覆盖push红。

公开证据：progress/evidence/2026-10-08/M6.3-fixed93c-original-native132PASS-oneFAIL-case15-actual2-frozen-five-generated-and-restored1565/REPORT.json；progress/evidence/2026-10-08/M6.3-actual-upstream-HTTP-gate-eightPASS-full114P6F-baseline106P6F-sevenRED-and-runnable-bundle2fcc/REPORT.json；progress/evidence/2026-10-08/M6.3-fixed93c-original-complete-Python4593PASS-two-numeric-ENV-skips-detached-terminal-and-native-original-running/REPORT.json。
<!-- engineering_progress:end -->
