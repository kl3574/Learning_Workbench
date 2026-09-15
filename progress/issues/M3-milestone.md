<!-- task_id: M3-milestone -->
task_id: `M3`

spec_version: `3.0.5`
spec_sha256: `2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37`

唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。

需求 ID：R-11, R-12, R-13, R-14, R-20, R-24, R-25, R-29

目标：公开/私有模型、自动保存、评分、暴露、服务端测试策略

依赖：无；总任务按子任务依赖推进。

修改范围：规范对应模块、契约、测试和脱敏工程进度。

验收清单及预期证据：
- [ ] M3.1: 公开 API/包/检索中无私有解答
- [ ] M3.2: 多标签直调 API 不能绕过独立测试限制
- [ ] M3.3: 正反评分样例、空答、单位、非有限数、重复交卷
- [ ] M3.4: 评分更新不覆盖旧成绩，未审推导不标正确


未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。

实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。
经审查/合并后才关闭任务；当前清单不表示已经验收。

<!-- engineering_progress:start -->
当前实际状态：`review`
规范：`3.0.5` / `2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37`
当前需求关联：
验证代码：`NOT_RUN`
验证：`NOT_RUN`
审查 PR：https://github.com/kl3574/Learning_Workbench/pull/46
下一动作：按子任务依赖推进。
<!-- engineering_progress:end -->
