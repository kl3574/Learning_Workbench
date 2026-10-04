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
M6.3 in_progress / AC21 尚未验收；唯一规范 v3.0.15 b140764e，用户批准的受控turn、单次模型、逐操作审批及产物待审回导范围继续实施。

最新本地组合 d6d4d9b98316d7f3790eb60e5d1bb4aca67450d1 尚未推送。已正常整合 Artifact512/SSE95、AA表单notice、Tutor218只读观察、Artifact8f产物界面、Event80b读流、Generic43审批界面和Review69两行测试生命周期修复。13组明确安全证据已保存并本地提交；进度主字段已更新，旧状态/失败/完整原件保持。普通源码merge保存12候选路径以及全部原progress Git字节；1521/1522工程输入与d69相同，唯一例外为5个精确档案的.gitattributes空白规则，不改运行代码。

实际完整门禁：d6d4 Web1399PASS/166files，Ruff/mypy287/生成82/spec/strict/build/diff各exit0；spec结构54core/147declared134implemented13missing不等于平台验收。两次额外错参数静态调用（不存在worker路径、误将--check传给extract）实际FAIL保留，新正确原规范命令分别PASS，无源码改动、不把原件追改为绿。10个实际完整1522工程输入before/after pairs均exact。

独立树固定d69完整make test-e2e实际133PASS/20.1m/exit0且wrapper0，start2026-10-04T17:37:16.347494UTC、end17:57:22.351345UTC，logSHA ad3c0608c6ab60b88071ceaf8a7c9cac95db2df7e82e3f50cb999beb474194f7。原10生成目的地中5个输出实际改变，1512非生成输入不变，无reset/restore/copyback。它是d69执行的原件，结合上述运行输入连续性用于本地组合；不冒称在d6d4重复运行。原412完整132PASS1FAIL/24.1m及route.fulfill alreadyhandled原因UNKNOWN保持FAIL；原4353完整Web1277PASS1FAIL也保留。

4353完整Python原实际4341PASS/2真实numeric BLOCKED_ENVIRONMENT skip/2warnings仍是最新全Python执行；当前所有Python/后端输入与4353保持，本地非Web/e2e仅documentary attributes例外。没有把隔离UI结果或新native数字冒充新全Python重跑；slice和whole counts重叠不相加。

Generic43独审Standards/Spec零新增，SAFE_DECLINE_BLOCKED_BY_PRIOR_APPROVE_COMMAND仅对修复source CLOSED_STATIC：原approve真实403/503被拒或unknown仍保留整条原body/key/ACK，新explicit decline从鲜读safe controls建立新key；approve_once仍受ANY旧command防重和原actor/学科权限。组件同完整测试3FAIL→38focusedPASS；原9e与43实际403的相同3harness字节反例RED→GREEN。限定Chrome/local HTTP owners/SQLite/IndexedDB两明确synthetic memory turn/1纯literal操作（host_actions/provider_requests/files_written=0）通过，不是实际远程模型/CLI/host工具。原9eOPEN四seal和031两wholeFAIL不改。

Review69独审窄source零新增，handler结束时两个hidden断言+server409与actual3subset（2Review+1draft-review）分列。客户端JSON/生成client/hook/React完成的既有证据缺口仍OPEN_EVIDENCE，不由unrouteAll(wait)或完整133绿色关闭；另树正在做精确透明消费观察与因果屏障，首真实Chrome+loopback+actual client机制反例2FAIL已保留，尚未合入或验收。原412完整失败没有时序记录，机制counter不证明原唯一原因。

公开源码仍1a6473，PR56 open/draft/unmerged。原1a push37207897702为5success1browserFAIL/native129P1F，PR37207899600六success/native130；12原joblogs及checkout/tree已核。尚无本次源码push或新CI，不称main发布、GitHubmerge/release/deploy。

边界：本次0真实外部模型请求，用户key未使用/进入仓库/上传。生产完整input proof/Provider/Broker/实际CLI、物理工具和writer停止/资源封闭验收尚未完成；物理numeric仍BLOCKED_ENVIRONMENT，无fallback；来源/数学/教学质量及整体M6.3/AC21/M7仍未验收。原扩展系统探针自动中止保持NOT_RUN、不重启或转派。

下一任务：完成精确客户端消费屏障的实际反例/固定源码/独立复核并保留d69原完整133结果；保存最新组合明确候选与当前主记录，做当前tree及outgoing history审计后正常sourcepush并按实际CI终态回读。M7.1新Codex备份范围仅只读盘点，验收未解锁。
<!-- engineering_progress:end -->
