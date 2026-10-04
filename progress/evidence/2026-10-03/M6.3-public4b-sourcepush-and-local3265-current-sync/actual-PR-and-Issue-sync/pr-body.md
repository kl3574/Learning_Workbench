受控回合现在可通过真实 Job/Run 完成准备、完整输入预览及单次许可、启动和结果读回。准备与安全取消 UI 在发送前保存原 actor、key、完整请求和 GET 基准；刷新只读事实，用户显式选择后才能重放原命令。普通 Import 任务文档入口及此前已验收的本地会话切片保留。

关联 #32，需求 R-23/R-27，唯一规范 v3.0.15。依赖尚未合并的 #55；本 PR 为 draft，当前分支实现仍未合入 main。新增 forward migrations 0027–0029，核心 0001、54 core 和学习包 3.0.0 保持原合同。当前实际注册 127/147 个操作。

本地完整验证固定 `29e864a6157f3bb23c6ced5d1a2f34f77bf3b875`；公开 `4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f` 仅追加终态进度，1433 个工程输入与受测源码一致。

- Python：4085 PASS、2 个真实数值环境 SKIP、2 个既有 warnings；Web：1201 PASS，Ruff/mypy/生成合同/spec/strict/build 通过。
- 原 `make test-e2e`：130 PASS。外层文件检查原 exit1 保留；独立核对十个既有测试输出路径，实际五个输出变更，其余 1428 个受控文件未变。没有把原文件检查失败改写成成功。
- 回执、原始失败及补充检查见 [完整本地门禁](progress/evidence/2026-10-03/M6.3-fixed-29e-complete-python-web-static-terminal/REPORT.json) 和 [原生验收与原文件检查失败](progress/evidence/2026-10-03/M6.3-fixed-29e-formal-native130-and-original-wrapper-failure/REPORT.json)。新 CI 的真实运行状态另行读回。

生产完整输入 ProofRegistry/executor 尚不可用，因此真实模型请求为 0。物理数值环境仍 BLOCKED，发布拒绝保持；数学、来源和教学质量尚未验收。逐操作执行、新 interrupt/外发 UI、产物 manifest 与普通 Import 草稿回导在隔离分支继续实施，不属于上述固定源码的验收。工具运行闭包绑定和新 UI 保留回答状态检查的复核发现正在修复。M6.3/AC-21 与 M7 均未完成，本 PR 不关闭 #32。
