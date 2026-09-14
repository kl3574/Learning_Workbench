# M3.3 独立评分与队列审阅

唯一规范为本仓库 PRODUCT_DESIGN.md（SHA256 ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c）。此为有界独立审阅，不代表 M3.3 全量验收、CI 或真实数学标准答案审批。

## 范围与证据来源

静态审查 Assessment 评分服务、评分仓储、Assessment 服务与 DTO、Jobs 查询入口、ImportWorker 分发、相关 HTTP 路由和 0005 迁移。运行两个真实 SQLite 故障注入探针与一个重评生命周期控制。使用项目原创合成学习包，通过真实导入 fixture 初始化；没有用户学习资料、外部模型或联网评分。SQLite UPDATE 是测试内可控存储损坏，不能解释为 HTTP 用户能够执行任意 SQL。

每次执行的 before/after 记录只固定列出的九个被审源码，且均一致；没有宣称整个开发中的仓库被冻结。探针复用了仓库 fixture 和其他依赖，其全部文件并未在初次运行前单独快照。原始代码与日志留存于本目录；初始、修复后源码分别以 initial- / green- 前缀保存。私有 trace 不被公开接口返回的结论属于静态范围，不能替代完整安全门禁。

## 实际发现及修复

1. **损坏的最早 grading job 导致队列饥饿（已修复）**。初始 application/grading.py 的 claim 仅选择最早 queued job；input_sha256 损坏后每次校验抛错，ImportWorker 在导入之前调用评分并把该异常路径报告为有工作。原探针连续四次 tick 后，后续合法评分为 0、真实 Markdown 导入仍 staged，四次返回均 True。修复后 claim 逐项校验，坏 job 在其可信 jobs 行命名空间中记 safe failed 与终态事件，不信损坏 input 选择其他 domain 写目标，再继续合法 job（当前 grading.py:161–181）。

2. **坏旧提交恢复阻塞所有后续队列（已修复）**。真实旧阶段 submission/outbox 尚无评分 allocation，其中 outbox payload 损坏；初始 recover 在同一循环内抛错，每次再从该项失败，导致相同饥饿结果。修复后每项 SAVEPOINT 隔离，登记 GRADING_RECOVERY_INVALID 并跳过已隔离项，不伪造成功 job 或成绩（当前 grading.py:143–159、migrations/0005_grading.sql:14）。原坏数据读取仍采取拒绝行为，修复没有把损坏内容当成有效成绩。

两个原始探针文件未为迎合修复修改。原 RED 为 2 failed / exit 1，修复后的同两探针连同以下控制为 3 passed / exit 0。

## 独立通过的生命周期控制

真实初次评分形成 needs_review grade1；测试中的实际 author 会话提交明确逐题人工分数，形成 grade2。下一次重评 claim 和 compute 后取消：旧 lease finish 返回 False；grade2 canonical 字节保留；同 key 重放返回原历史 JobRef；新 key 可产生并完成 grade3。断言仅两个实际应用的签名回执、取消任务一个终态、grades 递增且旧 grade2 不覆盖。首次控制 1 passed / exit 0；修复后同控制仍通过。这里的 author 是原创合成测试身份，不是对真实课程答案的人工审核声明。取消最新 job 后如何展示全部旧成绩属于后续完整结果历史界面范围，本次只证明保留和明确重评恢复。

## 命令与真实结果

- queue-red-receipt.json：原 test_queue_boundaries.py.txt，2 failed，exit 1；原始诊断在 queue-red.log。
- regrade-recovery-receipt.json：原 test_regrade_recovery.py.txt，1 passed，exit 0；日志 regrade-recovery.log。
- queue-green-receipt.json：上述两个文件一起运行，3 passed，exit 0，1.61 秒；日志 queue-green.log。

所有命令均使用 uv run --frozen pytest、-q --tb=short -o pythonpath=.；完整 argv 与原始日志哈希在各次回执。两条现有依赖弃用 warning 已保留，不描述为无 warning。pytest wrapper 自身会在打印后正常退出；应读取记录的 pytest exit_code，不能用包装器 shell 退出码替代。

## 结论与局限

上述两个真实队列问题已由后端负责人修复，原探针回归通过；本次限定静态回读没有新增阻断。纯规则 91 项、后端自测、停机 stop/过期 lease 自测和根端真实浏览器/API 重启由其他范围提供，不计入本次独立 3 项。未执行全量测试，未发布或变更进度，未证明对数据库管理员任意重写与移除 immutable trigger 的抵抗能力。后续源变更需由根的 exact-source 门禁重新验证。
