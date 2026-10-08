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
当前 M6.3 in_progress / AC21 未完成；唯一规范 v3.0.15 b140764e，已批准4e8/782合同继续实施，没有待用户批准的该合同阻塞。

实际公开 head 4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f；PR56 draft/open/unmerged、base PR55/e287。未 GitHub merge/release/deploy；本次只同步 Issue32 管理区块，不推送或改 PR。

公开4b的 push37200167062 与 PR37200168176 已实际终态 success，各6job，共12job全部成功。12份原始 job 日志已读回，每个checkout均实际解析：push=4b、PR=ff1b1c05e670fd622bd7daa48caa03d598a5374b，PR两parent=e287/4b、真实tree与4b完全相同。两个事件各有Web1201/154files、native130、contract953、unit/security888、integration2258 PASS/2实际ENVskip；范围有交叠，不相加。日志私有保存/摘要与SHA绑定，不能借给后续79ac。本地首次网络connection reset读取失败原件保留，后续成功另录；不是CI失败或权限阻塞。

当前 canonical 79acabc2566318f9ea099da067abd7e9c4f010a2 已普通本地整合 unsupported审批fdd、中断79a、UI92、受限memory工具83d、v4/v5共有历史融合ee及混合回归6127。每次整合原owner路径和其他原文件逐字核验；历史冲突/原错误断言/归档whitespace检查失败及窄路径attrs限定均保留。当前1465完整非progress Git输入/clean已冻结；7静态均PASS（Ruff、mypy276、生成82、54core/147声明/130实际路由、完整Web1278/157files、strict/build）。新完整Python4213 collected仍RUNNING，未以subset替代。

79ac新原正式make test-e2e已真实130 PASS、make0/wrapper0，12:54:01至13:14:39 UTC，1237.701s。隔离树完整1465映射中实际5个已具名生成输出变化，1460总输入不变；排除既有完整10输出后1455源码全部不变。原10输出前后/实际diff/dirty隔离树保留，零restore/copyback；不称1465全不变。实际数值receipt仍BLOCKED_ENVIRONMENT、发布409，流程测试PASS不代表算术或发布成功；产物候选仍待根独立读回。

UI92四种写命令丢ACK/刷新0POST/显式原key完整ACK真实Chrome已核，actual memory模型请求仅1、实际外部模型/CLI为NOT_RUN。83d有55 focused及226 related PASS（范围重叠），运行闭包旧P2 OPEN与新CLOSED_STATIC分开保留；默认生产operation registry仍空，受限literal执行不称宿主工具。新混合HTTP回归6127有5与9相关PASS、原1FAIL错误完整动态view oracle保留；当前完整79ac门禁另行判定。

产物/回导继续在隔离树实施。a0ea9396真实单请求原答案→新Broker-owned同步文件writer→完整目录扫描→Blob复制→不可变清单/唯一终态/下载，其固定214 PASS/六静态/1443输入一致仅为原门禁事实。封包自查新实际Blob写失败反例1FAIL已证P2 OPEN（原模型completed后Job仍running），a0e NOT_ACCEPTED，正在窄修边界分类与终态前副本再读失败。聚合回导WIP另树，经Import-owned同事务端口/独立0033与0034，真实预览/原ACK/来源成员合同继续测试；不自动commit/review/publish。原3route缺失RED和后续真实FAIL全部保留，不报闭环成功。

阻塞与边界：生产完整InputProof/executor仍不可用、真实平台Provider/CLI turn NOT_RUN；物理数值BLOCKED_ENVIRONMENT、无fallback；真实Broker/资源隔离/CLI工具writer停止/数学来源教学质量未验收，整个M6.3/AC21与M7未完成。密钥未上传，本轮0实际外部模型请求；memory计数不冒充全系统流量监测。

下一任务：等待79ac完整Python真实终态与1465输入后映射，封存原native实际输出差异及mixed/peer证据；复核并修复Artifact Blob P2、完成同事务Import聚合真实HTTP闭环、产物UI与原命令刷新恢复。冻结结束后录精确候选/进度，再做发布扫描与正常sourcepush及新CI读回；不得提前报整阶段成功。
<!-- engineering_progress:end -->
