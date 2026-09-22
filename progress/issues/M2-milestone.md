<!-- task_id: M2-milestone -->
task_id: `M2`

spec_version: `3.0.6`
spec_sha256: `30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924`

唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。

需求 ID：R-04, R-06, R-07, R-08, R-09, R-10, R-19, R-26, R-38

目标：DB/blob、导入预览、章节/块/LaTeX、笔记、精确版本

依赖：无；总任务按子任务依赖推进。

修改范围：规范对应模块、契约、测试和脱敏工程进度。

验收清单及预期证据：
- [ ] M2.1: 外键、回滚、文件失败、旧引用可读
- [ ] M2.2: 恶意 HTML/zip、哈希错、取消不污染
- [ ] M2.3: 失败可见、原件保留、不伪造 TeX
- [ ] M2.4: 实际浏览器刷新与重启回读；长公式滚动


未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。

实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。
经审查/合并后才关闭任务；当前清单不表示已经验收。

<!-- engineering_progress:start -->
当前实际状态：`review`
规范：`3.0.6` / `30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924`
当前需求关联：
验证代码：`NOT_RUN`
验证：`NOT_RUN`
审查 PR：https://github.com/kl3574/Learning_Workbench/pull/42
下一动作：按子任务依赖推进。
<!-- engineering_progress:end -->
