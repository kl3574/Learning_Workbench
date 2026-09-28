# e58abaaf 通用 Draft HTTP 切片独立双轴审查

固定对象为 m62-draft-combined-active 的 e58abaaf4baa5b06d27bd1db1f06c8a13c1c730a，相对已存在的 4cc4fd5 进度主线。唯一规范是 PRODUCT_DESIGN.md v3.0.7，SHA256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d。主线新四个提交分别与原服务 5c6d995、N/A 修复 6f4da06、HTTP 4c05cf6、标题修复 ea86495 的 21/2/12/2 个改动路径 Git blob 一致。工程树已提交源码未修改；存在独立的未跟踪 progress/evidence 包，它不在此提交或 1066 项工程门禁输入中。

## Standards

未发现这个固定切片的新阻断。draft_http.py 只作严格传输投影：本机会话、重复控制头、Origin/CSRF、无多余 query 和 no-store 响应由现有边界保护；POST 需要 Idempotency-Key，PATCH 用正文 expected_revision 强 CAS，原 key 可选且由 owner 保存原命令回执。Review/Content 的跨 owner 校验仍在调用方事务中。初始开发版的测试 lambda 触发 Ruff E731、递归 map 特例可吞额外 JSON Schema 关键字，均已在固定源码修复：普通 def、完整 map 字典精确匹配及 patternProperties/unevaluatedProperties 负控。DraftJsonValue 具名七分支递归 Schema、生成 TypeScript 的 typed map、闭合 Draft DTO 与实际 OpenAPI 路由由合同测试核对；未放宽其他开放 map。

## Spec

PRODUCT_DESIGN.md 第531、1262–1271、1968、1975行要求的两项写操作已真实绑定 DraftEditService；PATCH 的 JSON 值保留通用递归形状，并由当前 text block 的 title/body_markdown 白名单二次严格验证。已有 Import GET 仍是 ImportDraftSnapshot，对编辑草稿返回404；不会误把新 owner 冒充旧读口。创建只支持带精确既有 ContentRef 的公开、无依赖/概念 text block；六种 kind 和 nullable base_ref 仍保持声明 DTO，但超出首切片的请求以明确409拒绝且零写。创建、编辑、Review 和原回执通过真实本机 SQLite/Content/Import/Quality 路径；机器数学/来源状态保持 NOT_RUN。当前编辑标题/正文的显式公式阻止数学 NOT_APPLICABLE，历史基准的公式不代替当前稿适用性，旧基准物理字节损坏仍使回读/重放失败。符合第997行“不以 N/A 绕过包含公式的审核”，不等于机器已证明数学正确。

范围限制明确存在：编辑草稿没有外部精确 GET，页面刷新后无法凭服务端读取当前编辑正文和 revision 完成第454行的三方冲突比较；编辑草稿的发布仍被现有 Import-only 发布 owner 拒绝。其他 kind、从零新建、作者浏览器编辑/恢复/发布闭环、影响分析与 M6.2 整体验收均未完成。这些是后续阶段任务，不是本次已开放的公开文本块 POST/PATCH 假成功。

## 实际证据

固定 e58 的 m62-draft-main-combined-gates-v1 七个终态阶段均 exit0。前端单测 91 文件/538 PASS，Ruff PASS，mypy 210 个 Python 源文件 PASS，verify_spec PASS，前端严格类型检查 PASS，构建 PASS；相关 Python 八文件组合 239 PASS/2 条既有依赖警告。本人独立重算七组原始日志 SHA256、运行前后 1066 项工程输入以及当前 e58 文件 SHA256，全部吻合；所有 receipt 的提交身份均为 e58。相关组合含实际 Draft HTTP、Owner、Review、Import publication 和完整 API 投影用例，但不是全后端套件，也不是浏览器端到端。

旧开发阶段的 237 PASS 与 e58 在共有的 1055 项工程输入中有 8 条路径差异、另缺本次主线 11 条新增路径；104 项合同阶段对应为 6 条差异加 11 条新增，均不能当 e58 结果。原 ea 固定 full Python 也不能归给 e58。e58 的全后端套件、作者真实浏览器路径、真实 Provider、数值执行、人类数学/来源审校及 M6.2 完整验收没有由本审查包运行或证明。测试中的人类决定是合成协议 fixture，不是学术批准。此审查没有修改工程树、调用供应商或远端仓库。
