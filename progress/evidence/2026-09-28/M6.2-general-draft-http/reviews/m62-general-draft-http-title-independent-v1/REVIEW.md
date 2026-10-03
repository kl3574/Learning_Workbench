# ea86495 Draft 标题数学适用性增量独立审查

固定对象：ea86495ac8a55287b3e412f8e4aac9a602c3fa39，相对 4c05cf6c3f49d776ea2e191e6129ab3e360e2cf7；工作树无未提交变更。唯一规范为 PRODUCT_DESIGN.md v3.0.7，SHA256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d，§20.3 第997行及附录 A 审核决定第1970行。

Standards：本增量仅修改 review_service.py 和 test_draft_edit_integrity.py。显式 TeX 信号检测仍采用原有限规则；新增的 title 检查仅对 EditReviewMaterial 开启，未扩散到 Import、单块生成或组生成。源码未见新增阻断。错误文案“原材料包含”对当前编辑标题略含糊，是非阻断措辞问题。git diff --check 通过。未以静态审查冒称真实数学正确性。

Spec：当前编辑候选的 title 含 $x^2$ 或反斜杠括号公式而正文为普通文本时，数学 NOT_APPLICABLE 被拒绝；旧冻结基准标题、正文即使有公式，也不替代当前候选决定适用性。Review 读取仍经 Edit owner 的 _history、ContentDraftSource.verify_exact 和 Content 完整性读口，旧基准实际物理字节损坏会阻断读取及原命令重放。当前候选的无数学信号只容许带原因的人类 N/A，不产生机器 APPROVED。新增测试同时覆盖正反例、原回执重放、损坏原件后的零副作用。与规范“包含公式不能用 N/A 绕过”一致。审查未发现此增量的 Spec 阻断。

证据边界：私有原件 m62-general-draft-service-title-na-repair-v1 的 1062 个 manifest 成员经本次独立 SHA256 重算全部吻合。其 stage01 为真实 2 FAIL 红灯，stage02 为 5 PASS，stage03 为 136 PASS / 6 deselected / 2 warnings，stage04 Ruff 与 stage05 mypy 通过；五阶段日志哈希和前后 1051 工程输入吻合。运行时仓库 HEAD 是 2035fc9 的未提交修复源码；最终 ca788 和当前 ea86495 的两项增量 Git blob 相同。上述阶段不是 ea86495 的完整 HTTP 组合测试。先前 HTTP 03b 的 237 PASS 原件与 ea86495 比较有五条源码差异，不能按 ea86495 复述；先前 contract-focused 104 PASS 也有三条差异。ea86495 的 OpenAPI、DTO 和生成客户端 Git blob 与 4c05 相同，标题增量不修改对外 Schema；当前精确提交的 HTTP/前端全量门须另以实际运行证据记录。真实 Provider、数值执行、人工学术批准、完整 M6.2 验收均未由此证据完成。

持续限制：通用 Draft 仍只开放既有公开文本块编辑写入，编辑稿无外部精确 GET，编辑稿发布未接通；不得据此次修复把 M6.2 记为完成。
