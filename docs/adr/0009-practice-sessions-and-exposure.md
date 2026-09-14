# ADR 0009 — 练习会话、冻结答案与帮助记录

唯一需求来源为 `PRODUCT_DESIGN.md` 3.0.0，尤其 §4.3、§7、§19.2、§20.1–20.2 和附录 A/B/C。本记录细化 M3.1 的实现，不增加产品规范；测试、发布及审查状态以进度回执为准。

Practice 应用服务负责七个真实路由。题面通过既有 Content 端口读取完整 ContentRef；私有答案只通过内部 PracticeContent 端口读取。创建会话冻结题集、全部题目以及每题对应的私有答案修订与哈希。创建时没有答案也属于冻结事实，之后发布答案不会使旧会话悄悄改用新答案。公共会话响应没有答案绑定、accepted_answers、rubric 或容差，完整解答只在显式请求后返回，并携带实际 review_status。

迁移 `0003_practice_sessions.sql` 在既有表上增加分配完整性哈希、提交快照和帮助关联。旧会话缺少完整冻结信息时返回明确完整性错误，不猜测旧答案修订。作答保存为带 expected_revision 的完整快照替换，空列表明确清空；重复题目和未分配题目被拒绝。提交冻结作答及当时的帮助记录，后续查看提示或解答追加曝光，不改写已提交作答。各写命令在验证当前权限、工作区及对象归属后处理幂等回执。

M3.1 尚未交付 M3.3 的评分器和 M3.4 的成绩复盘。因此提交结果严格为 needs_review、score=null，界面说明未评分，不生成正确率、零分或独立掌握结论。导入的私有答案仍保留既有 needs_review 状态；合成验收内容和公开解答读取不能冒充独立内容审核。后续评分阶段继续实施规范要求的审核与证据规则。

核心 SolutionPrivate 没有提示字段。M3.1 采用标有版本的固定提示规则，仅输入公开题型与题面输入说明；三个帮助等级均明确标注规则来源。没有调用模型、查阅私有 accepted_answers 或虚构生成记录。首次查看每个等级和首次查看完整解答，在同一数据库事务内记录服务端 LearningEvent、Practice exposure、帮助正文及会话版本；事务失败时不返回解答或留下半条曝光记录。

Learning 模块提供只接受 hint_revealed、solution_revealed、practice_submitted 的内部事务端口，自己拥有事件、进度投影与 outbox 的写入。该端口不接收客户端成绩、事件 ID 或时间。Practice 不能直接写 Learning 表；阅读与书签投影在更新练习事件后保留。读取曝光时经 Learning 的只读验证端口核对真实事件的工作区、服务端/native 来源、kind、精确引用、会话、事件 ID 与发生时间。关联行被故障注入改指其他事件时明确拒绝，不把合法外键误当作完整业务关联。

既有 exposures.event_id 唯一约束使一次题集提交不能共用同一个事件 ID 写多条逐题 prior_attempt。一次提交保留一个真实 practice_submitted 事件及完整题目参与快照，不伪造多个提交事件。后续测试与证据模块必须结合持久练习参与记录和逐题 hint/solution exposures 判断是否见过题；缺少 prior_attempt 行不构成从未见过题的证据。

练习标签的 active_ref 为准确 PracticeSet。开始前预览的 attempt_id 为 null；明确开始后，attempt_id 存储真实 practice session ID，作为 §4.3 既有标签身份公式中的实例部分，不冒充 Assessment attempt。attached_refs 保存准确 Course 和 Lesson。题集目录包含合法已发布历史修订，按对象 ID 与修订稳定分页，不以 current 替换旧 Reader 的题集；会话 DTO 同时返回冻结题集的公开 lesson_ref，使客户端可核对完整父链。Reader 反向查题集后继续核对完整 lesson_ref；同一标签身份遇到不同冻结对象或祖先引用时明确拒绝并保留当前草稿。

浏览器本机作答采用独立的 IndexedDB CAS 草稿队列，正式服务端作答由会话 revision 控制。离线和多窗口冲突需要比较本机、原基准及服务端内容；无法确认保存时保留本机草稿。Submitted 会话只显示冻结作答，不能通过自动保存覆盖历史记录。

验收 fixture 是本工程原创的五题型数量关系与基本运算内容，分别生成合成 learner/author learnpack。author 包含 needs_review 私有答案；learner 包不含私有答案。本阶段的公开 API 与包过滤测试不代表尚未实现的 M5 检索或 M7 导出已经通过验收。
