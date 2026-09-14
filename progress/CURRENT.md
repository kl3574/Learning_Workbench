# 当前工程进度

本文件从 `state.json` 生成；需求仅见 `PRODUCT_DESIGN.md`。

更新：2026-09-14T13:53:50Z；规范 SHA-256：`ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`

仓库发布：VERIFIED；Issues 同步：VERIFIED
实施：IN_PROGRESS；当前任务：M3.1；下一任务：M3.2

M2.4精确4e53ce5全本地门禁及12CI通过，PR42待审；从最新含进度记录的M2.4 HEAD继续M3.1练习、提示与暴露，不重新初始化。

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
| M3.1 题面/私有答案库、练习/提示/暴露记录 | ready | [#20](https://github.com/kl3574/Learning_Workbench/issues/20) | 未验证提交 |
| M3.2 独立/辅助/开卷 policy snapshot，自动保存、并发版本 | todo | [#21](https://github.com/kl3574/Learning_Workbench/issues/21) | 未验证提交 |
| M3.3 单选、文本填空、数值/计算容差、人工复核 | todo | [#22](https://github.com/kl3574/Learning_Workbench/issues/22) | 未验证提交 |
| M3.4 交卷/评分/复盘闭环，评分版本与 evidence | todo | [#23](https://github.com/kl3574/Learning_Workbench/issues/23) | 未验证提交 |
| M4.1 学习事件、概念/技能证据、路线完成 | todo | [#24](https://github.com/kl3574/Learning_Workbench/issues/24) | 未验证提交 |
| M4.2 先修/补弱/复习/下一步推荐，接受/拒绝 | todo | [#25](https://github.com/kl3574/Learning_Workbench/issues/25) | 未验证提交 |
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

- spec_checks: PASS
- unit: PASS_M2_4_SCOPE_558_PYTHON_118_WEB
- contract: PASS_M2_4_SCOPE
- integration: PASS_M2_4_SCOPE
- browser_native: PASS_41_EXACT_4e53ce5
- real_provider: NOT_RUN
- real_codex: NOT_RUN
- learning_effectiveness: NOT_RUN
- ci: PASS_12_EXACT_4e53ce5_M2_4_SCOPE

## 阻塞与待决项

- 暂无已确认阻塞。

许可证待所有者选择。真实 Provider、Codex 和学习效果分别验收；接口或结构检查不代表业务完成。
