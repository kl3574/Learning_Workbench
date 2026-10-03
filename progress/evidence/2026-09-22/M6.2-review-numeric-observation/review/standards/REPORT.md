# ReviewNumeric Standards review

结论：1 项 P2 规范边界问题；未发现额外的运行时执行、写库或权限绕过问题。仅审查固定 WIP，不构成 M6.2 完成或后续修复通过。

**S1 — P2：事件前缀读取绕过 Jobs owner。** `services/api/app/application/review_numeric.py:68-70` 通过 `repo.conn.execute('SELECT * FROM job_events ...')` 读取事件。`PRODUCT_DESIGN.md:349` 要求模块间调用 application ports，禁止直接访问其他模块的表；`:2913`、`:2944` 明确 Jobs owner 持有生命周期及其投影。此处应由 Jobs-owned `AuthoringJobRepository` 提供具名、受检的只读事件前缀端口，继续使用调用方连接。该查询前的 `jobs.snapshot()` 已调用完整账本校验，所以本次未据此认定返回了未验证事件；问题是新增跨 owner SQL，令 Review 代码承担 Jobs 存储结构和序列规则。不要仅将相同 SQL 移入 numeric repository。

其余检查：

- `review_numeric.py:109-148` 经当前作者会话、Policy 和真实 Authoring 材料端口读/复核；`AuthoringContext.check_access:39-47` 与 `security.author_execution_identity:95-107` 强制调用方事务及当前会话。两个 service 新端口均复用传入连接。
- 新观察链仅执行读取；无新增 DB mutation、`Database.connect/transaction` 或 runtime `prepare/check/run_checked` 调用。历史核验保留命令/事件前缀，缺失旧项或修改旧事实通过原 owner 检查及完整比较拒绝（`:41-94`、`:124-139`）。
- 模型均继承 required、strict、extra-forbid、有限数规则和隐藏 repr/error input 的 `AuthoringModel`；完整 descriptor、源类型、候选身份、观察时间及输入/结果关系受检。组成员还由现有 group numeric owner 核完整 target/私解计划。
- Import 明示无数值 owner 流水线，未产生 PASS、数学批准或运行事实；未来 Review owner 仍须认证观察的真实保存历史。

范围与证据：基线 `e100f1b2ce02ccd0af85e2596b53ba2a24da9cda`；7 个 `initial-inputs` 文件逐 SHA/大小复核，与捕获时 live bytes 一致。审查 4 个既有文件的 `git diff e100f1b2` 及 3 个新文件全文；规格为已保存的 `PRODUCT_DESIGN.md` 3.0.7 与 AGENTS。固定输入与 11 个支持文件的哈希见 `pins.json`。测试文件的 query-only、禁止额外连接/runtime、篡改、当前权限及 WAL 快照断言已读；本次未运行产品测试，未读取 06/07 日志，未进行网络、vendor 或秘密访问。未增加推测性的 smell 发现。
