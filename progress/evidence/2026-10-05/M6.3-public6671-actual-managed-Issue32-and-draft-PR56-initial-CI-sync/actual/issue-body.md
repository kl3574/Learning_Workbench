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
M6.3 in_progress，AC21尚未验收。唯一规范PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec；初始Issue任务头保持创建时版本。

普通源码推送后branch与草稿PR56均实际读回 6671dd5c924edbac8ca7f479c4f51d4afec14480，draft/open/unmerged，依赖PR55。实现包括冻结受控回合、逐操作审批、只读SSE与产物清单、普通Import待审回导，以及现成session interrupt合同的UI入口。中断前先持久化原actor/session CAS/body/key；刷新无自动POST，丢ACK后须显式重放；412保留原命令，当前GET与历史ACK分开。回导只产生待审草稿，没有自动人审或发布。

本地新固定48693936两个原Review用例实际2PASS（15.4s/10.7s、total29.1s，command/wrapper0，原30000ms/worker1/retry0与断言保持）；独立有限核验26候选/7maps/10675绑定0新增缺口，LOG8cdedf6526644841530bcefbbf73724d0a22c1e3887a4cc4721dd823f6198102。原bare-selector list01命令0但列3项/scope wrapper1、业务NOT_RUN，exactlist02后只有这一次组合业务运行。486完整133native未运行。原22dade Web1421/167files、focused127/4files、strict/build/diff0和完整native133PASS20.4m只按各自源码限定；当前Web/package/Node输入同22dade。原4353完整Python4341PASS/2真实numericENVskip/2warnings按564Python输入一致限定沿用，没有新全量Python/Web重跑。上述重叠门禁不相加。

新CI实际快照 2026-10-04T21:06:22.360688+00:00：pull_request 37234699481 attempt1 in_progress/尚无终态；push 37234694749 attempt1 in_progress/尚无终态。仅记录API实际状态，完整新CI终态及日志未取得时不报PASS。首Review新增payload-free阶段/HTTP静态模板计时，保持业务断言/30s；唯一新增CI白名单行仅在既有failure条件保留review-history-timing.json，实际失败上传读回尚NOT_RUN。观察改变调度，不证明修复CI，也不证明全部JSON/React效果完成。

旧35ae两原CI37226331207/37226334354均terminalFAIL、各5SUCCESS+browser132P1F，首Review30s耗尽/唯一根因UNKNOWN、第二late-responsePASS；各integration2467PASS/2真实numericBLOCKED_ENVIRONMENT skips，12原log及实际checkout已核，后续成功不追改原失败。实际数值BLOCKED、发布409/PUBLISH_NUMERIC_REQUIRED/未发布保持。原中断首轮动态raw误重跑覆盖永久LOSS、retainedrun01 SECONDsetupFAIL、新run02仅FOURguard且boundedChromePASS保持；旧工具链0tests、TS7016/strict错误与旧oracle失败均保留。

公开前文档检查也保留原件：staged空白exit2，只增加六个精确归档路径规则，生产源码规则不变；公开扫描exit1拦住state/CURRENT十九本机目录字段，原私有bytes保留，后续仅HOME前缀转换后491暂存文件scan0、最终diff0、M0结构check0。结构检查不是业务验收；固定6671当前树/待推送历史另独立有限审核后才推送。原35ae推送git0/postcheck1及首API响应未保存/UNKNOWN继续保留。

当前production完整InputProof/profile/checker/受控执行闭包仍缺实现，默认unavailable；真实Provider/DeepSeek/Codex CLI模型turn、物理Broker/工具资源与停止边界、物理数值、来源数学教学质量及整体M6.3/AC21未验收。本轮0真实外部模型调用，用户API key未使用、入库或上传。已中止的扩展主机探针不重启，没有GitHubmerge/release/deploy。M7备份7cff只隔离保护覆盖准备；正式restore、新调度、M7依赖未解锁，M7保持todo。

下一任务：读取这两个新原CI的真实终态/完整日志及各checkout；若失败按明确有界metadata定位，不放宽30s或重跑掩盖。继续现行规范内的production受检输入和执行实现，保持真实执行/数值/质量验收边界。
<!-- engineering_progress:end -->
