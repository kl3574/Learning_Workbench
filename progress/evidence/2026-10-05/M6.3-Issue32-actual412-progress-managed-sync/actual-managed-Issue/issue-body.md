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
M6.3 in_progress / AC21 未完成；唯一规范 v3.0.15 b140764e，已批准受控turn/逐操作审批/产物合同继续实施。

最新本地固定组合412abe09c519104d9dbd2b360eed3ff4f897f829尚未推送。Artifact512及SSE95先在4353融合，再正常无冲突merge四个独审切片：AA表单notice、Tutor218只读观察、Artifact8f界面、Event80b读流。27disjoint路径完整候选Git mode/type/blob/size/SHA同时保留，1512工程输入同Git；1493原输入中1485未变，974个非Web/e2e输入（含564 Python）精确同4353，独审融合Standards/Spec零新增P1/P2。

4353原全Python现在实际终态4341PASS/2actual numeric BLOCKED_ENVIRONMENT SKIP/2warnings，2878.74s；9个原完整1493输入pair均封存。4353完整Web原1277PASS/1FAIL仍是FAIL。AA控制延迟save真实同测1FAIL→1PASS、原ACK仍归原actor；新412完整Web真实1359PASS/163files及七static exit0、8个完整1512输入pair一致，mypy287/生成82。Python明确是4353执行的原件，对未改后端输入引用，不冒称412重跑。新完整native已于2026-10-04T16:48:12UTC在独立412树实际启动，仍RUNNING，不能预报PASS；原配置/预算/重试策略保持，已列10原生生成输出目的地，不restore/copyback。

Artifact8f新界面27focused/1305完整Web/strict/build/spec PASS，实际Chrome+loopback HTTP owners/SQLite/IndexedDB bounded native02 PASS；6张1440/390图实际显示合成正文。完整原key/body/basis在POST前保存、实际202丢ACK后刷新零自动POST、显式同key全ACK回放、原queued与当前completed分开、普通Import预览原SHA/未审，无自动确认/Review/publish。原422f scope P2OPEN与lazy-preview LIMITED、首8f native观察FAIL保留；同scope反例1FAIL1PASS→同测2PASS，最终8f独审P2 CLOSED_STATIC。

Event80b新53focused/1331完整Web/strict/build PASS；原SSE six-variant闭合、空格换行原文、显式after_seq重连、fresh actor清显示、刷新零自动GET。限定native04真实Chrome生产组件+typedfetch+合成loopback1PASS，非production owner/CLI/model验收。初始收集/ESM/挂载/type和transport原失败各保留、挂载唯一causeUNKNOWN。独审源/55explicit candidates/6×1499输入pair零新增；已整合412。两slice数与完整组合数重叠，不相加。

新通用审批UI仍在未合入的隔离9e4ce1分支：35focused与1394完整Web/166files、strict/build/spec、新17.063s bounded Chrome/local owners场景实际PASS，1522输入exact；两明确合成memory turn和一次纯literal内存操作不代表宿主工具。原031两次完整Web各1339PASS/1FAIL（不同旧测试）保留，不能追认唯一cause。独审刚发现具名Spec P2候选：旧保存approve请求被拒/未知时，会锁住仍pending审批的后续安全decline。正在做独立真实counter RED和最窄修复，原body/key必须保留、decline从鲜读safe approval_controls明确新key，不自动改旧命令。该UI不能以既有PASS宣布验收，尚未进canonical。

Tutor218窄观察保留原准确区域/locator/5000ms，仅25ms只读采样；同DOM原1FAIL2PASS→固定6PASS（3原业务+3DOM）、native/Webstrict PASS，独审零新增并已整合。原1a Tutor CI129PASS1FAIL和唯一causeUNKNOWN保留，不用该合成机制或local绿色倒推原CI原因。

公开源码仍为1a6473（PR56 OPEN/draft/unmerged）。1a push37207897702真实5success/1browserFAIL129PASS1FAIL；PR37207899600六success/native130。12原joblogs/checkouts/PR parents/tree已核。新本地源码尚未公开、没有新CI执行/merge/release/deploy。

边界：本次0实际外部模型请求，用户key未使用/存入仓库/上传。实际生产InputProof/Broker/CLI/工具/可靠writer停止/物理资源隔离/数学来源教学质量与整个M6.3/AC21/M7仍未完成；physical numeric仍BLOCKED、无fallback。旧扩展系统安全review自动中止保持NOT_RUN，不重启或转派。

下一任务：保存412原完整native终态；按真实RED修复审批安全decline锁并独审新delta、重新固定组合适用门禁；同步精确进度与显式安全证据，再做当前tree/outgoing history审计和正常sourcepush。所有历史FAIL与各自source边界保持。
<!-- engineering_progress:end -->
