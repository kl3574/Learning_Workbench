# 当前工程进度

本文件从 `state.json` 生成；需求仅见 `PRODUCT_DESIGN.md`。

更新：2026-09-15T05:17:45Z；规范 SHA-256：`397829f5267248aedfc60faf7cacbb12669966b1c1d636a909b04189e0cc09dd`

仓库发布：VERIFIED；Issues 同步：VERIFIED
实施：IN_PROGRESS；当前任务：M4.2；下一任务：M5.1

发布M4.2修复及精确CI归档；基于已验证8d源码续做M5.1，采用已独立审查的唯一规范细化并实施Provider本机控制/授权/受控传输。

| 任务 | 状态 | Issue | 验证代码 |
|---|---|---|---|
| M0.1 空工程、依赖锁、启动脚本、lint/typecheck/test/CI | review | [#10](https://github.com/kl3574/Learning_Workbench/issues/10) | 401e0819b61f33ee918dbe0d739b686c413d7366 |
| M0.2 迁入目标模型，生成 schema/client，API 错误、CSRF/host/幂等接口 | review | [#11](https://github.com/kl3574/Learning_Workbench/issues/11) | 401e0819b61f33ee918dbe0d739b686c413d7366 |
| M0.3 需求追踪与 ADR，内容哈希规范、迁移机制 | review | [#12](https://github.com/kl3574/Learning_Workbench/issues/12) | 401e0819b61f33ee918dbe0d739b686c413d7366 |
| M1.1 课程内页式三栏 Shell、紧凑四入口、上下文目录、状态条、标签 | review | [#13](https://github.com/kl3574/Learning_Workbench/issues/13) | 1c5963d058e56fc36eec378ee3a7f67d665f2307 |
| M1.2 可访问分隔条、折叠、焦点、快捷键、命令面板 | review | [#14](https://github.com/kl3574/Learning_Workbench/issues/14) | 1c5963d058e56fc36eec378ee3a7f67d665f2307 |
| M1.3 ViewContext/ContextBridge、按对象保存草稿与会话 | review | [#15](https://github.com/kl3574/Learning_Workbench/issues/15) | 1c5963d058e56fc36eec378ee3a7f67d665f2307 |
| M2.1 SQLite/blob、精确版本、原子文件、对象读取 | review | [#16](https://github.com/kl3574/Learning_Workbench/issues/16) | f304193f95461ebc3bdc60d6661c7b80f493cb1d |
| M2.2 MD/TXT/HTML/learnpack 导入暂存和确认 | review | [#17](https://github.com/kl3574/Learning_Workbench/issues/17) | fb2bb033060f8aaacb59e1a81c9826c65509f343 |
| M2.3 PDFtext/DOCX 提取隔离、低保真诊断 | review | [#18](https://github.com/kl3574/Learning_Workbench/issues/18) | c7bcd6c8e511e2fe31e3739da9718f276fbfc0cd |
| M2.4 Reader/LaTeX、例题锚点、笔记、阅读位置 | review | [#19](https://github.com/kl3574/Learning_Workbench/issues/19) | 4e53ce5e73b61650f93c1ea769f3e3143031f29d |
| M3.1 题面/私有答案库、练习/提示/暴露记录 | review | [#20](https://github.com/kl3574/Learning_Workbench/issues/20) | 0fc6340d33c26c9f6124ebb3d19f190709b860ad |
| M3.2 独立/辅助/开卷 policy snapshot，自动保存、并发版本 | review | [#21](https://github.com/kl3574/Learning_Workbench/issues/21) | 25501799321c621bec4999c6c684c6a13106771c |
| M3.3 单选、文本填空、数值/计算容差、人工复核 | review | [#22](https://github.com/kl3574/Learning_Workbench/issues/22) | 452138bdf70147c84108aeab382b45e6a2e42278 |
| M3.4 交卷/评分/复盘闭环，评分版本与 evidence | review | [#23](https://github.com/kl3574/Learning_Workbench/issues/23) | 40bd4298f28443ae4dff3c2eb4de987f60df4924 |
| M4.1 学习事件、概念/技能证据、路线完成 | review | [#24](https://github.com/kl3574/Learning_Workbench/issues/24) | 5bd81576a2a0e2dbb454165eb3bcde5920493b05 |
| M4.2 先修/补弱/复习/下一步推荐，接受/拒绝 | review | [#25](https://github.com/kl3574/Learning_Workbench/issues/25) | 8d4b36f57b3ace950f9d3f0e750c4810fce9b0ec |
| M5.1 ProviderPort/能力协商/外发授权/预算/脱敏 | todo | [#26](https://github.com/kl3574/Learning_Workbench/issues/26) | 未验证提交 |
| M5.2 检索权限、中文 FTS、来源和修订哈希 | todo | [#27](https://github.com/kl3574/Learning_Workbench/issues/27) | 未验证提交 |
| M5.3 Tutor 状态机、SSE/取消/重连/异步上下文 | todo | [#28](https://github.com/kl3574/Learning_Workbench/issues/28) | 未验证提交 |
| M5.4 真实模型与搜索评测 | todo | [#29](https://github.com/kl3574/Learning_Workbench/issues/29) | 未验证提交 |
| M6.1 教材/例题/题目生成 schema + 数值验证 | todo | [#30](https://github.com/kl3574/Learning_Workbench/issues/30) | 未验证提交 |
| M6.2 审校/发布/版本对比/影响分析/恢复旧内容 | todo | [#31](https://github.com/kl3574/Learning_Workbench/issues/31) | 未验证提交 |
| M6.3 CodexBroker/App Server、操作审批、产物清单 | todo | [#32](https://github.com/kl3574/Learning_Workbench/issues/32) | 未验证提交 |
| M7.1 全备份/学习者包/作者包/恢复预览和事务 | todo | [#33](https://github.com/kl3574/Learning_Workbench/issues/33) | 未验证提交 |
| M7.2 安全/可访问性/性能/故障注入 | todo | [#34](https://github.com/kl3574/Learning_Workbench/issues/34) | 未验证提交 |
| M7.3 独立内容审校、真实用户试用、交付说明 | todo | [#35](https://github.com/kl3574/Learning_Workbench/issues/35) | 未验证提交 |
| E1 Zotero、博客增量、QTI/LTI、部署评估 | todo | [#36](https://github.com/kl3574/Learning_Workbench/issues/36) | 未验证提交 |

## 验证边界

- spec_checks: PASS_1DB509F_54CORE_66GENERATED_102DECLARED_60REAL
- unit: 1197_FULL_PYTHON_AND_288_WEB_PASS_1DB509F
- contract: PASS_1DB509F_243_CI_PER_WORKFLOW
- integration: PASS_1DB509F_527_CI_PER_WORKFLOW
- browser_native: PASS_82_1DB509F
- real_provider: NOT_RUN
- real_codex: NOT_RUN
- learning_effectiveness: NOT_RUN
- ci: 8d4b36f精确源码12/12success；PR实际checkout0c350b3与head的GitHub tree相同。两browser分别82PASS12.0m/12.1m。后续纯证据提交CI独立记录。
- m4_1_development: 开发和独立审查的所有原失败/修复、环境诊断已保留；最终源码新验收通过，不覆盖历史失败。
- m4_1_exact: 5bd8157新lint/types/spec/247web/build/74native均PASS，504源码前后相同；同SHA双workflow12checks成功。
- m4_1_layout_repair: PASS:真实412布局及焦点回归；原失败保留，限定机制归因；新74完整套件通过。
- m4_2: 1db509f固定提交七类本地门禁PASS：1197 Python/288 web/82 native；545源码前后一致。精确源码双CI12/12 success，各82 native。独立最终源码/日志/产物/11图审查PASS。待人工review，未合并；证据提交发布与后续CI另报。
- m4_1_publication_ci: 98f1701仅证据提交实际12/12success已回读；独立于5bd8157源码验收，不推定M4.2 CI。
- m4_2_publication_ci: 1db完整本地1197Python/288web/82native和精确12CI PASS已归档。42f历史证据CI为10success2backend Ruff失败（132归档错误，pytest跳过），双browser各82PASS。8d仅修Ruff归档范围，固定本地lint/spec、独立审查及精确12CI全部PASS；两workflow各243contract/440backend/527integration/288web/82native，组间不相加。PR48 ready/open/unmerged。

## 阻塞与待决项

- 暂无已确认阻塞。

许可证待所有者选择。真实 Provider、Codex 和学习效果分别验收；接口或结构检查不代表业务完成。
