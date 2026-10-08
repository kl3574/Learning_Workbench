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

本地工程固定93c44303；canonical 123081fd仅另有进度证据和一条精确归档规则，评分修复尚未推送。原6个评分并发/权限回归与254项相关测试通过，只是局部证据，不替代完整门禁。

当前93c完整Python原两轮失败均保留：初次2090PASS、500FAIL、2004ERROR、1数值ENVskip；任务私有TMPDIR轮4587PASS、6FAIL、2数值ENVskip、3warnings/2946.71s。后者六失败均为原Node24.21 guard；第9%—20%已有六F，此前“未见F/E”是窄观察遗漏填充空格，已明确勘误。原make setup actual0后，同六原case实际6PASS/2warnings/2.43s，源码和断言未改，四份1565输入图一致，锁定Node archive SHA核验通过。

随后完整run59677在turn中断后句柄missing、日志停26%、无终态回执；精确两任务日志未见writer，不记为suitePASS或FAIL。该轮五个原件保留。新完整原pytest已独立后台启动，并实际核验本任务日志writer；launcher0只是启动成功。运行时仅task-private TMPDIR，HOME/CODEX_HOME未覆盖、安装期UV_LINK_MODE copy不进入runtime；无filter/exclusion/retry，不放宽断言或numeric guard。终态计数仍未知；native待完整Python真实0后才单独执行。

原完整native65PASS/68FAIL/exit2保持：首个第二次index/rebuild响应10秒超时原因UNKNOWN，后续32个startup failure sections中31个SQLiteIO、1个provider503；不能把68FAIL都归为同因。独立有限静态核查没有证明首case源码缺陷。

公开branch/PR仍4ca。原push整体FAILURE(browser132PASS1FAIL)，原PR整体SUCCESS(browser133PASS)，各integration2525PASS/2数值ENVskip；全部12原job终态与日志已核。运行期输入映射未捕获，旧CI原因UNKNOWN；历史失败不因局部PASS消失。

生产仍缺真实AppServer发送前完整request生产器/计量证明及受限executor。现有真实网络原语可复用，但未接AppServer最终serializer；零模型bootstrap与synthetic peer不构成生产turn资格。已按官方固定tag取得真实上游a956835d源码并定位真实EncodedJsonBody/into_prepared链；原版缺max_output_tokens，且retry、auth recovery、WS/fallback、compaction均须单次额度门控。实际修改后须另列turn binary/profile与SHA，不能冒称规范旧bootstrap二进制；模型计量与完整资源资格仍欠缺。已有Key/测试授权有效；本阶段没有读取Key或真实模型请求，不上传秘密，没有GitHub merge/release/deploy。

本地证据已保存，尚未推送：progress/evidence/2026-10-07/M6.3-current93c-whole4587P-sixNodeFAIL-twoENVskip-observation-correction-setup0-sixPASS-newfull59677/REPORT.json。历史原证据及旧正文快照保留于进度记录和私有readback，当前管理区仅同步最新状态。
<!-- engineering_progress:end -->
