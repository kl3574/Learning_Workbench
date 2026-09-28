# M6.2 编辑审核数学适用性修复：独立 Spec 增量审查

固定修复提交 `2035fc9bf92f1c6b38725b2936898ad49adb4c16`，前置实现 `5c6d9959fee4ef7cf22fe2cca8e0f07fa524c18d`。唯一规范 `<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md` SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`。本审查只读，未运行产品测试、访问网络或修改 Main/候选。旧 `m62-general-draft-service-spec-independent-v1/REPORT.md` 的 F1 保留为修复前历史，不能重写为旧版无问题。

## 原 F1 的复核结论：已修正限定反例

`review_service.py:144-147` 现在只对 `EditReviewMaterial.record.payload` 调用既有数学信号检查，其他 Import/Single/Group 材料的分支保持原输入。`DraftEditRecord` 仍保存完整 `base`；`DraftEditService._history` 和 Content owner 每次回读继续核原历史 `ContentRef`、元数据、物理公开正文及冻结来源。审核选择的是该 Review 绑定的编辑候选 payload，并未偷换为当前 editable head。该变更符合规范 `PRODUCT_DESIGN.md:997`（无数学内容可由人明确写原因作 N/A）和 `:972`、`:3246-3250`（精确候选绑定）。

新测试以真实本地 Content r1 的 `equation*` 公式、另一个已发布 r2、固定 r1 的 Draft、删除公式后的纯文字 Draft r2、真实 Review job/worker/机器回执，以及明确写理由的**合成人类决定**构造反例。前置源码在阶段01决策处真实返回 `MATHEMATICAL_REVIEW_REQUIRED`，**1 FAIL**；只改服务判定后阶段02 **3 PASS**，包括现有两项“当前编辑正文含公式则 N/A 被拒绝”的反向用例。修复提交阶段03的四文件限定回归 **134 PASS、6 deselected、2 warnings**；两改变文件 Ruff PASS，`services/api/app` mypy 208 源文件 PASS。阶段01/02的 Git HEAD 仍记录为 `5c6d995...`、实际测试输入哈希证明只在01→02替换 `review_service.py`；阶段03–05的 1051 个输入才与 Git `2035fc9...` 完全一致。

新测试的机器数学、来源、教学字段仍为 NOT_RUN；合成决定记录 `mathematical=NOT_APPLICABLE`、`sources=REJECTED`、当前操作者、原因及精确 r2 候选。接着生成编辑 r3，原 r2 决定与 Review 创建键回原 ACK；损坏 r1 物理正文后，Draft 创建原键、Review 读取、决定原键和 Review 创建原键都被拒，数据库无修补写入。这证明“只调整适用性观察范围”没有放松旧基准完整性和历史 ACK 边界。原 r1 正文有数学、当前 r2 无数学的正向路径已实测；原 r1 自身若启动审核，按当前 payload 分支和既有当前公式反向用例应拒 N/A，但没有单独运行 r1 决策测试，不扩称该个案被直接执行。

## 新发现：标题中的明确公式仍可绕过 N/A 信号检查

这是现有数学信号函数的独立边界，**不由本次两文件修复引入**，但编辑 owner 的 `title` 允许修改而且属于当前候选。`draft_edit_models.py:75-81,96-109` 将 `title` 和 `body_markdown` 一同纳入完整候选；`review_service.py:133-143` 只在字符串字段名包含 `markdown` 或为 `formula`/`proof` 时搜索 TeX，跳过 `title`。因此 `kind=text`、`title="$x^2$"`、普通纯文本正文的当前编辑候选会令 `declares_math` 返回 false，显式 N/A 可进入决定记录。规范 `PRODUCT_DESIGN.md:997` 禁止以 N/A 绕过含公式内容。现有修复测试仅测试正文公式，没有标题公式。此判断可由源码分支静态确定，但本审查未运行标题反例；建议补定向 RED 测试后修正字符串检查范围，并同时保留“历史基准公式不影响当前纯文候选”的通过路径。不要用更宽的全材料扫描恢复旧 F1。

## 证据与限制

`verify.py` 独立重算原开发包 **1180 个成员**和修复包 **1063 个成员**的字节/哈希，检查修复包五阶段 receipt、日志、前后 1051 输入、1034 CAS 源字节及实际 Git 的 1051 个工程输入。原包清单 SHA 为 `d88f0e44e1703d8e8d27fdc4d01ee2e8d04d186562ece974269946c634d63e0f`，修复包清单 SHA 为 `d7fa8d2285852b287d77dce5983df279bd551e105878790690f1ceb9ff6efe81`；核验结果见 `VERIFY_RESULT.json`。修复包没有改原包。原 5c6d995 的 450 用例结果不能转称在 2035fc9 上重跑；后者有上述 134 用例限定回归。两者都不是全后端套件、HTTP/浏览器、真实供应商、数值执行、真实人工内容批准或 M6.2 完整验收。

建议先关闭标题明确公式的 N/A 边界，再接通用 Draft HTTP 与生成契约。此报告仅给固定修复提交的 Spec 增量结论，不替代其他轴审查。
