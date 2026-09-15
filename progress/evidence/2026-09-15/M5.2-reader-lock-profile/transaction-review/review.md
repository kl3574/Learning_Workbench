限定只读结论：发现两服务的八个读取方法在业务 SQL/调用链上均为纯读，但这不等于可以直接把共有 _access 改为 immediate=False。当前不建议未经实测与权限竞争决定就改这两个事务；原 CI 长时间无响应原因仍 UNKNOWN，未证明锁等待、饥饿或某个函数为热点。

| 入口 | 事务及实际调用链 | 纯读结论 |
|---|---|---|
| Content.read :76、current :90 | _access :58–66 → require_workspace → guard_subject_access → ContentRepository.load/current/decode | SELECT、严格模型/metadata SHA/工作区/生命周期核验；current 允许 note 不等于取消 subject guard。 |
| Content.body :81–88 | 同一 _access → block metadata → body_info → BlobStore.read | SQL只读；真实安全目录/常规文件/大小/正文hash核验，无write/mkdir或访问日志。文件字节读取现仍处在写锁持有区。 |
| Content.courses :124、revisions :146 | _access + SELECT/逐对象decode；cursor HMAC/expiry 内存计算 | 无SQL插入/更新；游标生成不持久化。 |
| Reader.outline :78–89 | _access :37–49 → _course :54–71 → reading_states | 只读完整课程/小节/块与Learning已有投影；无read-on-open事件。 |
| Reader.directory_search :91–114 | _access → _course → 内存标题/祖先匹配 | 无FTS维护、索引写入或新任务。 |
| Reader.block :116–130 | _access → block metadata → ProvenanceRepository.frozen/original_access/resolved | 原冻结来源/权限是只读投影，不回填provenance，不下载原件。 |

深链已核：ContentRepository :45–122 的 workspace/object/load/decode/current/body_info/decode_blob 仅 SELECT 与内存验证；learning.reading_states :24–49 调用 LearningRepository.progress :50–66，缺行仅投影 revision1 空状态，不INSERT。ProvenanceRepository.frozen :116–132 核精确block/source/citation/hash；original_access :134–158 只读source/artifact/manifest并调用Policy(private_artifact)，resolved :160–163复用该判断，不更改来源审核或放行私有字节。Policy.check :30–57 的 subject_read 分支仅 AssessmentAccess.active_independent :27–33；private_artifact 还走 protected :43–48/AssessmentRepository.load :107–156，后者明确只读且只验证分配、responses/submission。BlobStore.read :204–217 使用create=False；_read_file :136–155 O_RDONLY并重算长度/hash。这里“纯读”指业务持久状态；数据库 connect 仍有现有WAL/foreign-key/busy-timeout PRAGMA，不是承诺零系统I/O。

不能一起改的真实写路径：Content.publish :352–360 共用 _access，继而 publish_in_transaction :362 起写 revisions/objects/block_bodies/dependencies/outbox/current pointer/失效意图和实际blob；不得整体把该上下文改为只读或将写事务先读后隐式升级。Reader.backfill_provenance :144 起是显式启动恢复，:171/:191/:210 另开默认事务，最终 insert_recovered 真写；不属于三个GET，不应随读取修复改动。

权限/排他的区别：database.transaction :50–58 默认 BEGIN IMMEDIATE，而 Content._access :60–61 明文要求与attempt transition共用writer lock、不能mid-read开始独立测试。AssessmentService._access :52–57/create_attempt :209–235 的排他检查与实际allocation仍在该默认写事务；Policy.start_exclusion :59–65核active independent与活跃subject Jobs。只改Reader GET不会让两个independent开始都成功，也不会移除真实Jobs排他；但把读取改BEGIN会移除“这个GET从guard到结果构造期间阻止测试writer提交”的现有更强实现保证。

不能说旧快照即实时权限：BEGIN的首次读取建立一致观察后，其后的重复guard仍可看到同一旧snapshot。具体竞争候选是 R读guard为无active → T另一连接开始并提交independent → R继续元数据/正文读取且在同一R事务末尾再查guard仍是旧观察。由此只能把有限GET授权线性化到旧读快照，而不能声称新测试提交后再次核到了当前权限。§20.2 :972对任务/流/下载/解答明确再次检查；普通有限GET的精确授权时刻没有独立字段约定，不能不说明就以Retrieval现例覆盖当前Content注释。反过来也不能把与start重叠的所有旧快照读取直接宣称已证明违规：须先明确有限GET采用哪个授权线性化点。现BEGIN IMMEDIATE在service返回前释放，HTTP序列化/物理传输仍发生在其后，本来就不是事务与网络发送原子。

实际已有 immediate=False 仅在 application/retrieval.py 八处：scope_status :101、overview :134、job :168、query初始 :228、每block材料 :256、query最终另txn核scope/代际 :289、worker.compute开始 :328及每block :347。ContentRetrievalSource._access :271–279要求真实活动事务并核Policy/工作区；query跨事务会在新事务重核，区别于在同一旧snapshot末尾重查。worker计算另有真实非终态retrieval Job，开始排他受Jobs保护，写lease :339和finish :363仍默认写事务。scope_status/overview/job是同一快照观察，不能据此声称已测过Reader mid-read start竞争或保证零响应延迟。

已读测试源码、没有本轮运行：
- tests/unit/test_backend_database.py:32–45 使用真实两个连接证明既有writer下BEGIN读取旧已提交状态、第二IMMEDIATE在25ms预算内locked；:107–119证明reader事务存在时writer能提交WAL供backup读取。后者不是Reader权限竞争测试。
- tests/integration/test_assessment_attempts.py:404–416 真ThreadPool两个start，断言仅1active；test_assessment_policy.py:98–116验证现有学科Jobs阻止start并要求事务。它们不同时挂起Reader。
- test_content_repository.py:276与test_content_http.py:147、test_reader_provenance.py:28均在active attempt已存在后验证教材/来源拒绝，含author；不是在guard后制造start的并发反例。
- test_retrieval.py:239起与test_content_retrieval.py:214验证已有active策略/真实Job排他；Content source还有total_changes不变断言。不能从这些静态用例位置或此前suite结果推断本次假设已测。

最小安全候选（未采用、未实施）：
1. 先等待实际profile区分connect/BEGIN等待、Policy SQL、_course metadata校验、reading_states全workspace refs、原件权限projection、文件读取/响应序列化。不得删完整性核验或增断言超时来掩盖热点。保留全局默认以及所有publish/start/backfill写事务。
2. 若以后确实采用分段读取，只给这八个GET独立读入口：BEGIN中先guard再完整读取/验证/构造有界结果；完全退出旧读txn后，另开短BEGIN IMMEDIATE重新require_workspace/当前subject Policy，核所有拟交付的权限敏感投影，再作交付决定。尤其 Reader.block 的 original_access 必须用新快照重新投影，不把旧allowed摘要当下载许可；下载仍独立复核。返回正文不得换成“最新版本”或跳过body/metadata/hash，原历史/学习状态可明确是该受检读取快照。不得在旧BEGIN里假装重复guard就是新检查，不能增加dummy UPDATE伪装只读。
3. 该方案容许independent在准备阶段先成功，随后Reader须拒绝交付；并非原“writer全程等待”的同实现行为，应明确记录新授权点且先做真实两连接有界竞争测试：start先赢必拒、最终短guard先赢允许该已授权有限读、author也不能旁路；包括慢body/provenance、损坏后整项failclosed、无SQL写和原publish原子回滚。只在最后短guard释放之后再开始的网络发送仍不能声称锁住。若要完全保留原mid-read阻止start语义，则保留现锁，优先缩短实测证明的其它writer持锁段；不要把BEGIN候选当无语义代价的优化。

本轮只是源码/测试边界审查，没有运行DB/profile/测试/浏览器、修改源/规范/进度或使用私有Provider文件。
