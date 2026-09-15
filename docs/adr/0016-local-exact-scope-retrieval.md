# M5.2 本地精确范围检索实现记录

本记录说明当前实现如何落实唯一规范 `PRODUCT_DESIGN.md` 3.0.3 §20.7、附录 A/D/F.1，不增加产品要求。实际验收、失败和修复记录见 `progress/CURRENT.md` 与 M5.2 Issue。

检索只消费完整 course/lesson/block 引用。Content owner 在真实只读事务中展开冻结子引用，核当前 Policy、公开元数据、来源描述和预算；读取命中正文时再次核实际字节、大小、哈希与 UTF-8/LF。Retrieval 不直接读取 Content、Provenance 或私有答案表。公开未审教材可以被明确选中，每个命中仍显示未审与真实来源状态。

`scope_sha256` 绑定工作区和规范化 roots；`corpus_sha256` 绑定当前完整材料描述；`indexed_corpus_sha256` 来自已提交代际。旧范围重建保留原 roots 和正文，重新记录其当前指针、生命周期与来源事实。GET/query 只读，不因 missing/stale 自动登记任务或扩大范围。

词法实现固定 Unicode 15.0.0 和 `lexical-han-gram-v1`。只将派生的安全 ASCII term 放入参数化 FTS5 MATCH，按所选范围内 query term 覆盖率和完整引用稳定排序。原正文不做规范化，也不截断成摘要。返回预算按完整块选择，数量、正文和实际 JSON 字节遗漏分别计数。

新增迁移 `0011_local_retrieval.sql` 维护检索自己的命令、scope、代际、chunk/FTS、失效消费账本。Jobs adapter 拥有任务、租约与事件写入；原重建回执和实际 Job 读回分开。短事务领取租约，事务外计算，提交前重新核租约、取消、Policy 和完整 descriptor，再原子发布整个代际及唯一终态。过期租约仅恢复本地确定性工作。

Content/Provenance 在各自修改事务登记检索失效意图。检索消费自己的水位，不清除共享 Content outbox 的其他消费者信号。后台维护对推荐、检索、评分、导入各给有界轮次；检索账本损坏保留错误，其他队列仍可推进。

HTTP 使用真实严格 DTO 和三个已注册路由。辅助检索窗口通过命令面板进入，默认范围来自已解析 Reader；选择小节/教材扩大范围须明确操作。完整父链可进入 Reader，没有完整父链时只回读精确块。前端原写命令在发出前保存到本机，未知结果保留原 key/body/base；ACK 不充当当前索引或任务状态。最终浏览器与恢复边界的验收结果单列，不能由接口测试推定。

F.1 的 30 个原创块和 42 条 gold 在首次运行前冻结。真实 service 基准的逐条响应、运行前 passport 和哈希记录独立保存；小型词法召回结果不能证明通用 RAG、数学审校、模型质量或性能 SLA。

本阶段不注册生产 Provider source，不发送模型请求。平台 Tutor/Run/SSE 属于 M5.3；真实模型与搜索评测属于 M5.4。独立供应商连通测试不改变这些实现边界。
