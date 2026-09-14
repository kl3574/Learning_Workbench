# M3.2 前端开发证据

这是一组开发过程记录，不是最终精确提交门禁。原始材料留在私有临时目录；本包只提供日志的脱敏派生版、限定错误摘录和原创合成界面图。打包没有运行测试、改源码、提交 Git 或发布。

最终首次前端冻结是 **161 unit / 2 focused native / lint / build 通过**。此前最近一次完整测验浏览器轮次是 **6 通过、1 失败**；更早的 **7 通过** 属于另一开发状态。后续完整门禁又发现导入角色回归，因此这里的冻结不能视作当前最终源码已验收；该修复另见 M3.2-import-repair-development 包。

| 原日志 | 实际结果 | 范围与说明 |
| --- | --- | --- |
| m32-assessment-units-first.log | 20 PASS / 3 files / 2.69s | Initial assessment tests and prior Practice lifecycle tests |
| m32-assessment-native-first.log | 2 PASS / 2 FAIL / 22.4s | Initial shared-workspace setup; later private author imports correctly blocked after a submitted independent assessment |
| m32-assessment-native-isolated.log | 4 PASS / 26.3s | Each scenario moved to its own real RestartRuntime; guard unchanged |
| m32-assessment-local-first.log | 1 PASS / 16.6s | Initial local candidate and terminal-response scenario |
| m32-assessment-units-second.log | 26 PASS / 1 FAIL / 5 files / 2.71s | Test beforeEach returned a mock function, which Vitest invoked as cleanup; route was undefined |
| m32-assessment-units-fixed.log | 27 PASS / 5 files / 2.72s | Test hook uses a block with no returned cleanup; no production workaround |
| m32-frontend-units-all-first.log | 159 PASS / 22 files / 3.02s | Entire frontend unit suite at that earlier development point |
| m32-assessment-projection-first.log | 1 PASS / 9.5s | Real delayed redacted Workbench ETag save is rejected after independent submit; explicit selection-preserving rebase |
| m32-assessment-native-complete-first.log | 3 FAIL / 1 PASS / 1 INTERRUPTED / 1 NOT RUN / 20.2s | Three real create503 errors occurred during a coordinated backend service/migration transition; the owned runner was then interrupted. The log proves503, not the precise internal database cause |
| m32-assessment-native-final-first.log | 7 PASS / 56.4s | Before final wording/keyboard assertions and before late-GET Workbench fixes; cannot be assigned to the later freeze |
| m32-frontend-lint-final.log | PASS | Earlier tsc noEmit/unused checks |
| m32-frontend-build-final.log | PASS with chunk-size warning | Earlier build; warning retained |
| m32-frontend-units-final.log | 159 PASS / 22 files / 3.05s | Before two permanent late-GET regression tests |
| m32-assessment-native-final.log | 6 PASS / 1 FAIL / 56.3s | 29-file source candidate; live peer B correctly recreated its still-owned local candidate after A selected, contradicting a zero-conflicts test precondition |
| m32-workbench-recovery-fixed.log | 2 PASS / 1 file / 480ms | Permanent delayed restorePending and explicit server-reconnect ownership regressions |
| m32-frontend-lint-frozen.log | PASS | 31-file frontend development freeze |
| m32-durable-peer-native-fixed.log | 2 PASS / 19.4s | New Assessment and old Practice scenarios explicitly retained and closed the durable peer before choosing in one remaining writer |
| m32-frontend-units-frozen.log | 161 PASS / 23 files / 3.07s | 31-file development freeze; not the later import repair source |
| m32-frontend-build-frozen.log | PASS with chunk-size warning | 31-file build; main573.41kB and MathMarkdown2939.32kB, no performance acceptance claim |

原 npm 命令回显保留在每份日志开头；没有回显的外层 shell 环境或退出码不补造。临时输出根、进程 ID 和本机端口已规范化，具体转换及 raw/public SHA 在 manifest.json。

本机 CAS 的最后失败不要求删除保护逻辑：A 选择后，仍挂载且持有脏分支的 B 会重新保留其候选。独立 React + DraftStore 探针确认该因果，随后测试先通过真实确认窗口保留并关闭 B，再由 A 明确选择。共享 journal 算法未为此改动。旧 Practice 用例按同一前置条件修正，不能据此声称旧用例在本轮曾失败。独立探针完整红绿证据由主代理另包保存，本包不将其计为原生浏览器测试。

两份源码清单均为已有捕获：29 文件候选与31文件冻结。聚合算法直接写在文件中，可从原文件 SHA 清单复算；不追加不存在的历史 before/after。29文件轮次结束时实际做过无差异检查，但没有独立保存 after JSON，故本包不构造它。31清单相对29清单变化见 delta_from_previous_candidate。它们只覆盖该前端负责范围，不覆盖整个服务端、工具链或 fixture。源码清单的 head 是脏工作树基线，不是承诺这些字节已在该提交中。

完整错误附件含浏览器 DOM 和测试源码，因此仅提取 `# Error details` 后第一个 fenced error block；其余附件及后续错误块不复制。运行日志内的短断言/堆栈仍保留。每个 PNG 是原始字节副本，未造图或修图。inspection.json 逐文件调用当前 publication.inspect，并检查附件标记、进程 ID 和常见授权值；人工来源检查见 visual-review.md，自动扫描不是任意私密内容的通用识别保证。
