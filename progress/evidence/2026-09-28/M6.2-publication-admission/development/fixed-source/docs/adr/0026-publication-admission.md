# 发布前只读准入观察

依据 PRODUCT_DESIGN.md 3.0.7 §12.4、§15.1、§19.3、§20.3 与附录 A 的发布请求四字段。

本切片只实现 PublicationAdmissionService.check 的当前事务内只读端口，接受严格 DraftPublishWrite。它通过 ReviewService.read_publication_basis 重新核当前会话、作者、工作区和 Policy，以及原候选 owner、完整审核历史、原数值历史前缀、报告与递归证据物理字节。不能用调用方 JSON 或上次返回的观察冒充权限。结果仅包含精确候选、审核修订与证据摘要，publication 固定 NOT_RUN；它不生成 ContentRef，不注册 HTTP 假发布、不改变 Draft 状态或 Authoring DTO，也不调用 Provider/数值 runtime。实际发布者以后必须在自己的写事务中重新调用该端口并完成所有所属事务。

准入要求原机器结构检查 PASS、当前审核最后的人类决定批准全部适用的数学/来源条件、完整材料范围、真实数值覆盖和实际 owner 警告确认。数学 N/A 由 Quality 在全历史回读中按原材料检查，理由和 actor 保留；真实来源存在时来源 N/A 不成立。独立教学 NOT_RUN 保留，不被升为已验证，也不额外作为本软件交付门槛。警告 severity=error 拒绝，warning 必须明确确认，未知确认代码拒绝。

数值计划来自实际 single payload 或 group 每个 worked_example 成员；group target 比较全部规范字段而非 Python 子类身份。Numeric owner 的 candidate_checks 按持久 SQLite rowid 枚举，ReviewNumeric 冻结原有顺序并逐项重验原前缀。每个精确 plan/member 采用该冻结列表最后匹配检查作为当前发布依据：必须明确批准、有实际启动与真实 Job completed、完整输出、已取得 exit 0、原断言全部 PASS。最后 pending/queued/running/failed/cancelled/BLOCKED 或无记录不能复用早先 PASS。较早失败仍完整验证和保留，不是终身否决；真实重跑成功必须被新机器 Review 观察到，不能升级旧冻结回执。这是当前准入依据的工程选择，不删除旧失败，也不把数值 PASS 当数学批准。此切片不引入跨 Review 的全局优先级或 Draft 当前审核选择规则。

当前 Import block 可提供完整正文，但 imported worked_example 没有独立数值 owner 历史；Import question 材料明确 excluded 私解，其他导入图只有候选元数据而没有完整成员材料，均给出具体未支持原因。Import.commit 原参考导入行为不变，公开题面审核不审批私解。当前生成题组的七类必要题目语义检查仍为 NOT_RUN，两个全候选 APPROVED 不能补造这些检查；本端口以真实未检查范围阻断，不定义永久禁止题目发布或新增产品状态，后续可由规范允许的真实人类/独立证据补全。

测试使用实际 Import/Authoring/Review/Numeric SQLite owner 与受控 loopback 生成。明确标记的合成人类意图和 numeric ledger 终态只验证持久协议与准入选择，不是实际专家批准或数值沙箱成功。当前实现不处理发布输出转换、私解入库、版本影响传播、恢复、UI、HTTP、迁移或状态转换。
