# M3.4 复盘、评分历史与可信学习证据

唯一规范为 PRODUCT_DESIGN.md §13.2、§20.1–20.2、M3.4 与附录 A/B/C。本记录解释工程实现；阶段状态和实际验收以 progress/state.json 及绑定源码的运行回执为准。

## 两阶段资格与原始事实

新提交在原 CAS/答案快照/test_submitted/outbox/真实 Job 的同一事务中保存不可变 `learning_submission_bases`。非分数前提绑定原分配与提交哈希、原题目顺序、精确概念修订、固定答案审核状态、原 preflight.prior_seen 和提交前帮助事件见证。第一次调用评分规则前、重评和提交幂等回读都核验该依据。不能重新计算包含本次测试自己的 prior_seen，不能根据得分反推前提。

Practice-owned port 先核验帮助原生事件、题目/模板关系、原会话分配和完整回执，再判断相关性与截止时间；两处服务端时间不要求相等。跨截止的时间冲突或损坏的关联保留 unknown，不把它们当成“没有帮助”。Learning 只保存帮助元数据及原哈希，不复制帮助 Markdown。复读仅核验被冻结的事件集合，提交后的合法复盘不反向改写旧资格。

评分完成后纯规则逐项结合真实 resolved 状态判定。已审、未见、无帮助的独立作答，即使零分也可以是有效证据；满分或人工复核不能升级原未审标准答案。未解决分数保持 null。辅助模式的 assisted 表示模式能力，不声称确曾调用工具；开卷保持 MODE_OPEN_BOOK，并映射核心 independence=unknown。本次独立性和历史新颖性分别表达，已有帮助暴露不标 novel。

概念映射按题目自己的不可变依赖获得完整 ContentRef；不能把全卷概念分配给每题，不能用概念 ID 临时取最新修订。缺失或歧义映射保留明确排除，没有可验证概念时只保留逐题历史，不造占位 Evidence。核心 Evidence 的 score 是真实 score/max_score；它不是掌握概率。

## 同一事务与历史恢复

真实 grade、私有审计、attempt 状态和 completed Job 终态写入后，同事务通过 Assessment-owned read ports 核验，再记录一条真实 grade_finalized、Learning progress/outbox、完整绑定及逐概念 Evidence。任一步失败整体回滚，不留下半份成绩或证据。一版一个事件；重复内部调用只允许完整相同记录回读。

新增 0007 迁移，不改已发布 0001–0006 或旧 canonical 模型。迁移只把当时已提交或已有评分的作答正向分类为 history_not_frozen；原 active 作答在新版真正交卷时仍正常冻结。迁移后缺依据的新提交属于完整性错误，不能当成旧记录兜底。

历史补记由现有 Worker 每轮有限处理一版，使用当前真实事件时间，原 grade.finalized_at、评分 JSON、提交和签名不变。所有历史版和后续重评永久保留 HISTORY_PREREQUISITES_NOT_FROZEN；不能追认当时已完成事前资格核验。坏记录在 savepoint 回滚后隔离为安全诊断，继续合法评分与导入。诊断 source_fingerprint 是实际待恢复 GradeKey 的规范化哈希，用于定位该版本，不声称它是损坏原始私有载荷的内容哈希。

GET 不执行补记。历史尚待恢复返回 EVIDENCE_RECOVERY_PENDING；被隔离或无法验证返回明确错误，不默默掉版本，不将 evaluated 当作 eligible。

## 公开历史、分页和复盘

已有 result 的 200/202 语义保持。两者返回严格、完整、按真实评分修订排序的历史摘要；摘要没有反馈 Markdown、原作答、私有 pin 或解答。202 仍包含真实任务和最近完成结果，旧结果的解答始终隐藏。当前可释放的反馈和解答由当前 Policy 单独检查；新的独立测试及角色变化不能被旧缓存绕过。

一次结果读取按实际 UTF-8 JSON 响应字节计量，包含 202 嵌套重复摘要。工程初值为可配置 16 MiB，超限明确返回 GRADING_HISTORY_RESPONSE_LIMIT；不截断、不删除历史，扩大预算后仍可完整读取。该默认值不是产品文档声称的既定数值。

规范内 GET /learning/evidence 先按每个作答选择最新真实成功持久化的评分版，再过滤概念/技能和分页；新 failed/cancelled Job 没有新评分，保留上一成功版。游标 HMAC 绑定工作区、过滤条件、页大小和 Learning 投影水位；新版本出现后旧游标明确过期。默认 20，最大 100。空数据为空页，不生成能力画像。

复盘通过显式独立标签显示冻结的交卷原文、真实历史版本、资格理由和经验证的原课程/小节/块导航。所选评分修订作为本机 UI 偏好持久化，不伪装内容 ContentRef，也不覆盖作答标签的未同步候选。当前复盘能力单独投影，不改原冻结 policy；学科上下文可恢复时仍不伪造 M5 才接入的 Provider/Tutor 调用。

## 验收边界

纯规则、迁移、原子性、HTTP 预算、帮助见证、分页和重启需要分别给出真实证据。受控 approved 原创 fixture 只验证该数学审批前提下的软件行为，不是实际专家审批。核心 freshness 仍为 novel/repeated/unknown；本阶段不因出现新内容修订就声称旧证据过期。内容适用性传播、完整技能/路线投影和推荐由后续 M4/M6 承接，模型答案和学习效果评测另行记录。
