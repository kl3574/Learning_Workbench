# M6.2 当前规范余项只读盘点

取证固定 `8e9239a78d45b100abdcca5036dad887968ffcf3`（root 集成树），唯一规范 `PRODUCT_DESIGN.md` v3.0.13，SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`。共享树随后已前进；本文源码均用 `git show 8e9239a:路径` 读取。范围仅 M6.2 及其必要引用；未运行产品测试、未改规范/代码、未读数据库/环境/凭据、未联网。下列测试是读取其实际断言，绝不等于本轮执行 PASS。

## implemented-unverified

| 能力与规范 | 当前真实实现／测试 | 尚不能关闭的边界 |
|---|---|---|
| 编辑、审校、人审、发布：规范 L1176–1190、L1471–1472 | `services/api/app/main.py:215–219` 注册实际路由；`application/draft_edits.py:132–183` 不可变创建/PATCH；`application/draft_publication.py:186–203` 分派 Import/Edit/Restore/Single；`tests/e2e/edit-publication.spec.ts:42` 覆盖真实保存→Review→发布、原 ACK、父 pin、重启；依赖保留 HTTP 测试 `tests/integration/test_edit_publication_dependencies.py:66,163,196,236` | 已接入有序依赖与内部冻结见证，不能再报“所有带引用 text 均不可编辑”；原 316 不单独接受。180 owner、56 独审、1 native 是不同固定源与范围，不是当前完整组合通过。 |
| 块版本比较与恢复：规范 L955、L1202、L1219 | `interfaces/content_http.py:94–100` 真 current/history；`apps/web/src/features/reader/versionCompare/BlockVersionCompare.tsx:11,31–44` 精确两修订、完整字段/正文与显式 Restore；`tests/e2e/block-version-compare.spec.ts:5–54` 核原文及零写；`tests/e2e/content-restore.spec.ts:86,207` 真 proof 恢复、重启、原 ACK、父 pin、412；HTTP `test_content_restore_http.py:60,197,218` 包含 text/theorem/proof、原概念 pin、旧成绩/私解/Note/index | 不是缺少实现，也不等于所有块 kind、损坏组合或最新完整 native 均已验收；Question/私解/Course/Lesson 恢复明确不在 L1202 内。 |
| 影响发现/决定、Evidence、Note 与检索：规范 L1194–1221、L1242–1246 | `interfaces/content_impact_http.py:26,36,46` 实际三路由；`tests/e2e/content-impacts.spec.ts:28,98` 实际发布事件发现、分页/CAS/回放/角色；`tests/e2e/evidence-applicability.spec.ts:41–111` 两事件及真实旧 grade/private pin 保留；`tests/e2e/note-reanchor-publication.spec.ts:28–93` 已有 UI 发布→Note stale→显式新源重锚→旧 scope 显式 rebuild；HTTP `test_edit_publication_learning_http.py:32–138` 实际旧成绩与 index 保留 | 不应再提一套重复的重锚/rebuild 实现。接单时 root 报告的完整 native 仍为旧 0b 的 121 PASS/1 FAIL，a40 的 2 条 focused PASS 不关闭该失败，也未证明唯一原因；Dialog 另树待整合。 |
| Single 与 Restore worked_example 数值发布：规范 L1282、L1290、L1305、L1344–1360 | `draft_publication.py:196–203` 两具名 owner；`apps/web/src/features/draftReview/ReviewPanel.tsx:119–122` 两实际发布分支；`tests/e2e/single-publication.spec.ts:67–124`、`restore-numeric.spec.ts:80–129` 分开断言物理 BLOCKED 拒发与实际 PASS 发布 | 本机封存环境 BLOCKED，正向真实隔离 PASS→发布仍未验收。受控 runner/合成人审的正向协议证据不能填成物理或学术 PASS。可在满足既定隔离要求的环境运行原批准流程；不可降低准入。 |

接单时 root 的全 Python 在固定 7d 仍 RUNNING；本文不查询其进程、不把后续结束推定为 PASS。现有实现的首要收尾是固定组合后的剩余验收，而非因旧进度标题重新开发。规范 L1221/L1286/L1360 要求实际证据；当前没有完整 M6.2 关闭依据。

## missing-authorized

**公开 text 带非空 `concepts` 时的标题/正文编辑覆盖尚缺。** 规范 L1176 定义已发布公开 text，严格 payload L1178 不允许编辑 concepts，但没有把“只读保留原 concepts”的 text 排除；core `ContentBlock` L2283–2291 合法含 concepts。当前 `application/content_draft_source.py:25`、`draft_edit_models.py:79–84`、`content.py:503` 三处直接拒绝。相反，`draft_edit_models.py:45–46,136–140` 已把完整原 metadata 放入 base hash，`edit_publication.py:32–34` 只改 revision/title/body hash；不存在必须为此加入外部 DTO 字段的证据。

下一个可在既有 text 编辑合同内实施的产品片段：只补该合法输入的原概念身份/历史 pin 保留与完整性核验，仍只编辑 title/body，使用 Content 所属受检能力（现有 Restore 在 `content.py:518–530` 显式带原 concept pin 发布）。应先真实 HTTP 负例，再覆盖概念 current 移动后旧 pin 不漂移、冻结后损坏拒绝、强 CAS/原 ACK、旧无概念 raw/hash 兼容；不能只删上述 guards，不能让发布按 latest 重新解析 concept。此项是范围覆盖不足的静态确认，不是本轮实证的新完整性漏洞；未授权本轮直接实施。

## contract-gap

1. **通用 Draft 广义入口已声明，具体非 text payload 合同仍不足。** 规范 L1469 枚举 course/lesson/block/question/practice_set/assessment 与 null base；L1470、L2186 要求各 kind 白名单及严格 DTO。实际 `draft_edits.py:141–142` 只接受有 base 的 block，`draft_edit_models.py:143–147` 只接受 title/body；`interfaces/draft_http.py:44–59` 确实注册这些路由，故不能声称枚举全实现。现行精确编辑形状仅 L1178，Import 专属 GET L2178 也不能被换成宽 union。缺的是其余 kind／无 base 的合法初始材料、可编辑字段与具名读回/发布绑定；不能凭 JSON 值类型自行发明。该局部合同缺口不阻断已具名 text/Restore/Single 工作，也不自动要求另写提案。
2. **Group/题目发布未由 v13 扩权。** L1152 是未审组草稿；L1162 明示草稿题族不等于已发布 exposure_group；L1305 排除 Lesson 组、题目和父级改写，L1356 排除课程路径切换。真实 `review_material_models.py:63–80,94` 已有 Group 受检 Review 材料（`tests/integration/test_review_materials.py:64,306`），不是全无 owner；但 `draft_publication.py:202–203` 拒绝 Group，`AuthoringGroupDraft.tsx:11–19` 仍显示草稿与成员数值口。由候选组到正式根/成员、私解身份及审核、跨版本暴露关系、父级引用与原子发布的具体映射仍未闭合。不能把 Single 的 r1/四字段请求直接套到 Group，也不能把现有 core 模型或 Group 数值检查当作该映射已经获准。

本次未发现需要修改唯一规范才能继续已明确范围的比较、影响、恢复验收；也没有把单块能力升级为整个 M6.2 或课程发布完成。以上不覆盖冻结前任意协同篡改、学术/来源/教学质量或真实外部模型验收。
