# M6.2 通用 Draft 编辑服务：独立 Spec 审查

固定基线 `a944ebfbdb835a731393977a606db5b473846e98`，候选 `5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d`。唯一规范为 `<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md`，SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`。本审查只读；没有运行产品测试、网络、远端或改动候选/Main。Inventory 与 ADR 仅作为定位和实现说明，不取代规范。

## 结论

**1 个需要修正的 Spec 缺陷。** 当前服务的创建、编辑、不可变账本、精确历史基准、当前作者与 Policy 核验、候选版本隔离和编辑发布拒绝均有实际代码路径及相关测试支持；下述人类审核适用性错误应在接受这段服务并接 HTTP 前修正。HTTP、UI、生成契约、其他 kind/null 基准、通用 Draft 状态和编辑发布均未在本提交实现，因此不能宣称 M6.2 完成。

### F1：旧基准正文错误地阻止当前无数学内容候选的 NOT_APPLICABLE（阻断本切片的审核语义）

`PRODUCT_DESIGN.md:997` 明确规定无数学内容可以在人类写明原因后标 `NOT_APPLICABLE`，有定理/公式则不能借此绕过审核；`:972` 与 `:3246-3250` 规定审核绑定精确草稿版本。`services/api/app/application/review_service.py:131-145` 的适用性函数却把整个 `material.payload.model_dump()` 递归扫描为数学内容。新 `EditReviewMaterial` 在 `review_material_models.py:83-85` 包含完整 `DraftEditRecord`，而记录在 `draft_edit_models.py:117-140` 同时包含**旧基准 `base.body_markdown`**和当前 `payload.body_markdown`。因此，原公开 text 块正文含 `$x^2$`，PATCH 后当前候选正文只剩普通文字时，作者针对当前候选的 `mathematical=NOT_APPLICABLE` 会因旧正文而收到 `MATHEMATICAL_REVIEW_REQUIRED`。旧版正文应继续供来源与历史完整性核验，但审核适用性应检查当前编辑候选正文/字段。现有正向测试 `test_draft_edit_integrity.py:103-116` 只覆盖“当前候选新加入公式则拒绝 N/A”，没有覆盖“旧版有公式而当前候选删除公式”。此结论来自完整静态调用链；本审查没有执行该反例。

## 已核的边界

- `DraftEditService` 先验证当前会话、作者和现行受保护材料 Policy，再在同一事务读取精确 `ContentRef` 的元数据和公开物理正文；不以 current 指针代替指定历史版本。正文 SHA 与完整候选 SHA 分开核验。原私有导入文件未做物理回读，其冻结来源描述符也不等于来源真实性。
- 创建要求完整命令幂等键；PATCH 使用 `expected_revision` 和实际 head CAS，选择性命令键保留原 ACK。版本、父哈希、命令和候选目录分开持久化；服务/仓库在失败后回滚，旧审核记录仍指向原版本。
- Review 新命令要求编辑 head；原 Review 回执、已排队 worker 与原命令 ACK 仍可读取旧版。机器结构只声明两项已运行 PASS，其余声明及数值没有 owner pipeline 时为 NOT_RUN；人类决定的测试材料为合成事实。
- 0019 迁移在 FK 开启时重建原 11 表闭包，保留普通列和 rowid，只扩大两处 source_kind 限制并新增编辑表。非空 Import/Review/发布与合成生成 owner 历史迁移、两处注入失败回滚已有实测；未独立重跑迁移。
- `PublicationAdmissionService` 和实际 `DraftPublicationService` 均拒绝此编辑 owner；无编辑发布成功事实。没有把旧审批用于新修订，亦没有实现恢复旧发布内容为新的 Content revision。

## 证据范围

`verify.py` 独立读取原始私有包 **1180 个成员**并逐项比对字节/哈希；核对 **25 个阶段**的 receipt、日志、前后输入与 **1065 个 CAS 源字节**；从实际 Git `5c6d995...` 读取 **1051 个工程输入**、21 个变更路径和原始 diff，确认最终阶段输入与 Git/worktree 一致且只排除 `progress/`。验证结果见 `VERIFY_RESULT.json`，原始包清单 SHA 为 `d88f0e44e1703d8e8d27fdc4d01ee2e8d04d186562ece974269946c634d63e0f`。

原始第25阶段为 **450 passed、20 deselected、2 warnings**，16 个受限相关集成文件，含本切片 83 个新用例；mypy 对 `services/api/app` 的 **208 个源文件**通过，Ruff 对 **19 个改变的 Python 文件**通过。原始第22阶段实际退出 1，命令漏排除两项受控 loopback 生成 fixture，日志以 `KeyboardInterrupt` 及 teardown 异常结束；它不是成功门禁。两个临时 DB 的 dispatch/terminal 数量只见原操作者的转述，DB 未留存，不作为本审查可复放事实。无完整后端套件、真实供应商/用户 key、受控数值执行、真实人工审校、HTTP/浏览器或全 M6.2 验收结果。

下一步是在候选编辑 Review 的数学适用性上补上述逆向用例，修复范围为当前候选，保留旧基准完整性证据；再进行定向回归和源/evidence 复核，之后接 HTTP 与生成契约。所有结论限定于固定候选及已列证据。
