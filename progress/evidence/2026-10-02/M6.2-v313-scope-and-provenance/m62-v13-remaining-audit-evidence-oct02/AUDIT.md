# M6.2 现行 v3.0.13 只读余项审计

固定源码：`60fa2b8c18bbd3bbd4122df81bb798fd6d0a3dab`。隔离树：`$HOME/.cache/learning-workbench-acceptance/m62-v13-remaining-audit-oct02`。
唯一规范：`PRODUCT_DESIGN.md` v3.0.13，SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`。AGENTS 指定它为唯一规范。

本次是源码和测试源码审计；未运行 Python/Web/native 测试、数据库、Provider 或物理数值环境。下列“已实现”仅指所述窄范围存在真实接线和实现，测试栏为已读取的用例，不是本轮 PASS。root 当前固定组合门禁与历史门禁各自记录，不能从本报告推出完整 M6.2 验收。所有相对路径均相对于上述固定树。

## 实际接口与 owner

`services/api/app/main.py:112-128` 实例化 Restore/numeric/Review/publication/impact owner，`118-123` 将 Import、Single、Group、Edit、Restore 纳入真实 DraftCandidates/Review 解析；`213-219` 注册 Authoring、Group、Review、publication、Edit、Restore/numeric router。实际发布分派 `application/draft_publication.py:175-207` 只有 Restore、Edit、Single、Import 四种具名路径，其他材料返回 unsupported。

`tests/contract/test_api_projection.py:25-79` 要求实际路由与 OpenAPI 双向相等、110 个已注册/130 个声明，列出上述实际接口。数字来自固定契约断言，本轮未调用 app factory 重新计算。路由已注册不等于所有宽 DTO 枚举都有实现。

## 已闭合范围与精确边界

| 项目 | 当前实现判断、源码依据 | 对应测试源码（本轮未执行） |
| --- | --- | --- |
| Quality Review / 人工决定 | 已实现各具名候选的机器检查、独立人工决定和历史读回；发布单独准入。`interfaces/review_http.py:21-32`，`application/review_checks.py:96-133`，`application/draft_publication.py:44-79`，`features/draftReview/ReviewPanel.tsx:63-123`。结构 PASS 不等于数学/来源/教学合格；Edit/Restore 无生成声明的命名检查保持 NOT_RUN。 | `tests/integration/test_review_workflow.py`、`test_review_history.py`、`test_review_materials.py`、`test_review_numeric_observations.py`；`tests/e2e/review.spec.ts`。 |
| Import 发布 | 已实现真实普通 text/markdown 导入块的 r1 新对象发布；`application/import_publication.py:27-68` 对 package、私解、符号、非 text、concepts/depends_on 等拒绝；不能称所有 Import 类型均可走这条发布。 | `test_draft_publication_scope.py:36-120`（真实 parser、unsupported、Jobs、同 actor）；`test_draft_publication_atomic.py`、`test_draft_publication_integrity.py`。 |
| 已发布 text 标题/正文编辑 | 部分：无 concepts 且无 depends_on 的公开 text 已贯通 create/PATCH/精确 GET/Review/发布；§20.10 的标题正文编辑覆盖仍被额外收窄。`application/draft_edits.py:87-128,129-178`；`draft_edit_models.py:116-128` 限定可修改字段；`features/draftEditor/DraftEditor.tsx:33-69` 包含本地持久化、三方恢复、精确候选进入审核；`application/edit_publication.py:27-35` 仅改 revision/title/body SHA。 | `test_draft_edit_read_http.py:29-155`、`test_draft_edit_boundaries.py:94-198`；`test_edit_publication.py:68-291`、`test_edit_publication_atomic.py:31-198`；`tests/e2e/draft-editor.spec.ts:54`、`edit-publication.spec.ts:42`。 |
| 精确历史版本比较 | 已实现公开块两侧独立精确读回、完整 metadata/source/body 差异；只是文字/字段比较。`features/reader/versionCompare/BlockVersionCompare.tsx:11-44`。不是全 Course/Lesson/Question 的通用结构差异编辑器。 | `tests/e2e/block-version-compare.spec.ts:5`、`features/reader/versionCompare/{compareClient,boundedDiff,BlockVersionCompare}.test.*`。 |
| 恢复历史公开块 | 已实现同稳定 block ID、source<active current 的独立 Restore 候选、全字段副本、全新 Review、强 CAS 发布为 current+1；不回退旧 revision，不改父级 pin。`application/content_restore_source.py:22-99`、`content.py:434-448`；`features/contentRestore/RestorePanel.tsx:41-76`。非 Question/私解/Course/Lesson/Route/归档恢复，边界来自 §20.11。 | `test_content_restore_http.py:60-111` 实际 text/theorem/proof；`:197-215` 保留原 concept revision 和 depends_on；`:218-228` 旧 grade/私解/Note/index；`tests/e2e/content-restore.spec.ts:86,157,207`。不能称 11 种 kind 各自 native 全验。 |
| Restore worked_example 数值链 | 已实现 §20.14 专属手填材料/源 codepoint 锚定、preview/独立批准、Jobs/runtime、完整有序账本、新 Review/发布约束。真实 numeric PASS 仍必须由实际运行给出，空结果、旧 PASS、合成人审不能代替。`main.py:112-122`；`application/restore_numeric_service.py`、`restore_numeric_worker.py`、`restore_review_numeric.py`；`features/contentRestore/RestoreNumericPanel.tsx`。 | `test_restore_numeric_http_boundary.py:107-289`、`test_restore_numeric_execution.py:59-228`、`test_restore_numeric_integrity.py`；`test_restore_numeric_actual_runtime.py:11`、`tests/e2e/restore-numeric.spec.ts:8`。物理环境本轮未测；既有 BLOCKED 不能改称 PASS。 |
| Single worked_example 发布 | §20.15 的单个真实 authoring_single→新 block r1 已有真正 owner/UI；原 payload、声明来源依赖、原 published_ref 与后来 current 分离。`application/draft_publication.py:143-172`；`features/authoring/AuthoringPanel.tsx:48,54-55`；`features/draftReview/ReviewPanel.tsx:121-122`。发布后新 preview/approve/start 与 publication 原子准入，已 started/unknown 保留实际事实。 | `test_single_publication.py:31-190`，`test_single_publication_sources.py:60`，`test_single_publication_races.py:42`，`test_single_publication_continuity.py:24-123`；`tests/e2e/single-publication.spec.ts:67-111` 明确 BLOCKED 拒绝分支和实际 PASS 后发布分支。执行哪个分支须看该次输出，不由 test 名断言。 |
| Content 影响发现及逐对象决定 | 已实现真实 invalidation 事件发现→详情→当前目标基准→append-only 决定。`infrastructure/content_repository.py:197-226` 同事务 current/outbox/frozen snapshot；`interfaces/content_impact_http.py:26-46`；`application/content_impact_decisions.py:194-218` 将无有效决定列 pending、new_revision_required 列 action；`features/contentImpacts/ContentImpactsPanel.tsx:28-41`。new_revision_required 就是可追踪待办，没有自动修订/发布；这符合 §20.11，不应把它误报为关闭待办的缺陷。 | `test_content_impact_snapshot.py`、`test_content_impact_decisions_http.py`、`test_content_impact_discovery_http.py`；`tests/e2e/content-impacts.spec.ts:28-95` 从实际发布后的 HTTP 列表取得 event ID、CAS、三页高水位、restart、parent pin。 |
| Learning 旧证据适用性 | 已实现逐真实事件/原 evidence 的独立判断，所有有效 usable 才解除该原因 pending；不改 grade/attempt/私解/独立性。`interfaces/evidence_applicability_http.py:32,48`；`application/evidence_applicability.py:94-119,228-269`，`concept_states.py:86` 和 `assessment_recommendation_access.py:153` 消费同 owner 投影；UI `features/learning/ConceptStates.tsx:15-28`。 | `test_evidence_applicability_decisions.py:87-429` 含多事件、archive、原资格、CAS、atomic dirty、坏历史；`tests/e2e/evidence-applicability.spec.ts:41`；`features/evidenceApplicability/applicability.test.tsx`。 |
| 旧 Note stale / 手工重锚 / 索引 | 已有独立 Note 和 Retrieval UI 闭环，不由 Content 决定自动完成。发布使原 Note stale；用户读取准确新源、显式采用选文，再单独保存。旧范围索引明确 stale/无命中，显式 rebuild 仍按原 pinned scope；不偷换到新 current。 | `tests/integration/test_edit_publication_learning_http.py:32`、`test_edit_publication_atomic.py:31,71`；`tests/e2e/note-reanchor-publication.spec.ts:28` 实际 UI 编辑发布→原 Note 保留→手工重锚→旧范围 rebuild；`features/notes/NoteReanchor.tsx`、`features/retrieval/RetrievalPanel.tsx`。 |

## 不应从 v13 推出的范围

- Group 的 lesson/practice_set/assessment 原 producer、候选、私解权限、成员数值检查和 Review 已实现；发布仍缺具名映射。`AuthoringPanel.tsx:54` 只传 group candidate 给 Review，`:55` 才向 Single 分支传 published projection；发布 dispatcher 不接受 GroupReviewMaterial。§20.9 要求真正身份/暴露/私解 owner，§20.15 明确只扩单例题。不能把 Single allocator 复制过去就声称 Group 已获批准，也不能把未实现的 Group 发布当成 v13 回归。
- `DraftCreateWrite.kind` 的宽枚举和路由目录不是通用草稿实现。`draft_edits.py:136-137` 只接受 block+非 null base；`apply_patch` 只接受标题/正文。新 Course/Lesson/Question/PracticeSet/Assessment、任意 block kind 的新建/编辑、修改概念/依赖字段、自动父 pin 更新，都不在本窄切片内。
- 因此 M6.2 仍不能标“全种类创作发布/影响全部消解完成”。范围外 owner 映射需要最小明确合同后再实施；当前可继续已批准 text 编辑覆盖、现有路径验收和已证实竞态修复，无需再造一个宽发布设计。

## 下一个既有规范内的最小垂直片段：保留既存 depends_on 的 text 编辑

明确缺口有三重服务端/前端拒绝：`content_draft_source.py:24`、`draft_edit_models.py:53-55`、`content.py:427`；UI `DraftEditor.tsx:33` 和 `editPublicationSchema.ts:15` 也拒绝。`tests/integration/test_draft_edit_integrity.py:255-280` 把 kind/concept/dependency 作为 first-scope 负例。真实反例是一个已经公开、无 concepts、带合法精确 depends_on 的 text 块：只想更正文错字也无法创建现有 Edit。

**合同判断：不需要新增严格 DTO 字段、接口或新产品语义。** §20.10 已限定公开 text 的标题/正文编辑，既存依赖可以只读保留：`initial_payload` L109-113 将完整 `DraftBaseMaterial`（含完整 `ContentBlock` metadata/body/provenance/warnings）哈希放入 `base_material_sha256`；`DraftEditRecord` L153-156 再验证该绑定，candidate SHA 覆盖 payload。显式 `depends_on` 完整 refs 与顺序已在 base.metadata，`EditBlockPublication` L32-35 从它复制完整块，原字段不必进可编辑 payload。前端 `editPublicationSchema.ts:22-24` 同样从准确基准构造目标。原空依赖记录的字节、hash、ACK 不必迁移或重解释。

**实施须完整，不能只删除 guard。** 读取/Review/发布需核原精确依赖存在、hash/正文/owner/权限有效，损坏 fail closed；历史依赖的 current 后移不得使保存的 refs 漂移。发布继续准确 active base CAS、独立新 Review/人审、原事务 current/outbox/Note stale。UI 必须展示只读原 refs，仍只可编辑 title/body。

**本轮候选不开放 concepts。** concepts 是纯 ID，base metadata hash 覆盖 ID 列表但不直接覆盖其解析 revision；`Content._closure` L299-317 对新 revision 未传 frozen binding 会采用当前 Concept。若将来开放，须沿原 `concept_dependency` pin（Restore 在 `content.py:445-446` 已有具名实现）并核完整性，不能删除 concepts guard 后悄悄重绑定。此点不应混入本次最小 depends_on 片段。

建议验收：合成公开 text（空 concepts、两个有序 depends_on）→实际 HTTP create/PATCH/GET→新 Review/人工决定→强 CAS publish→GET full refs/order 原样；推进依赖 current 仍保留原 refs；基准/依赖坏 hash 或 body 零写拒绝；同原 actor ACK/Policy边界不退化；旧无引用历史 hash/ACK 不变；concept/kind 继续拒绝。完整旧门禁不因该未来片段局部 PASS 自动继承。

## 证据边界

固定源只读，没有改产品、规范、progress、CI 或测试。审计没有发现需要立即放宽数值、身份、源材料或父 pin 边界的理由。本报告没有验证远端 CI、外部平台模型、人工数学/来源正确性或教学效果；这些不应从本地协议测试推断。完整现行组合验收由 root 分别绑定其实际 SHA/结果封存。
