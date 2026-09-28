# M6.2 Authoring 控制列表时序：受控缺陷修复与 CI 诊断边界

记录日期：2026-09-28 UTC。唯一规范 PRODUCT_DESIGN.md 3.0.7，SHA-256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`；本树与工作目录原文件 hash 一致。本次读回 §20.8/20.9、§17/19.3 的准备、原 ACK、当前状态、控制权限与证据要求，并核对 ADR 0020。未引入第二份产品需求。

结论：已用实际 RED 确认并修复两个控制列表时序缺陷。它们不能被称为 21fc CI 超时的已确定根因。候选尚未集成、独立审查或发布；原 CI 失败仍开放。

## 原 CI 可证事实

- Push run `35708863885` browser job `106684300581`：实际 checkout `21fc190bc95b47cf794f2f4358544651be9e3f17`，98 PASS / 2 FAIL。本文仅处理新增 group 失败，Tutor 由另一独立诊断处理。
- Group case `authoring-groups.spec.ts:294` 在 `readPrepared` 第 48 行超时；调用点第 322 行。原 locator 等待精确 Job 的详情按钮，超时 10000 ms。日志没有记录已找到按钮而无法点击的 actionability 子阶段。
- 实际读取失败 PNG：创作面板原命令显示“准备组合草稿 · 原命令已确认”，安全列表显示“本页没有任务”；刷新、回放、表单灰显。图像只是当时可见状态，不证明某 HTTP 请求、数据库阶段或 React 生命周期的实际时序。
- PR run `35708867857` browser job `106684313105`：实际 checkout `50dd55714da755058a7ec2adcd17daa78e492e0a`，100 PASS，同一 group case PASS 14.7 s。两份精确 group spec 同 blob / SHA-256。
- 原 CI artifact ZIP digest 与成员 hashes 已由 `artifact-source-readback.json` 核对；本文又读取并计算原 log、context、PNG 和 spec hashes，见 `ci-source-artifact-index.json`。没有 trace/HAR 或该组的 request/IDB/list/admission 因果账本，不能从截图倒推出唯一原因。

原失败源程序在 replay response 202、与原 ACK 完全相等、两次请求 key/body 相等的断言之后，才进入失败行。可据测试控制流确定这些前置断言通过；不能据 HTTP 202 认定随后浏览器已完成原 ACK 持久化、列表读取或渲染。

## 当前反馈与区分试验

先运行原完整 native case 一次，基线 `72e4e64ce0e97b444146fe237efee9f199da16dc`：PASS 10.6 s。它没有复现 CI。第一次私有 runner 因 ESM 上下文错误未能加载配置，产品测试 NOT_RUN，失败日志保留；仅修复私有 package type 后才作这一次实际测试。原 spec 未编辑。

三项在试验前提出的可区分路径：

1. 回放后列表仍未完成：预测原 ACK 可已持久，列表仍为空且 busy=true；释放该列表后恢复。真实 hook + IndexedDB 语义受控持有 list Promise 得到此状态并通过释放正控。这证明可达状态，不证明 CI 当时存在同一 pending request。
2. 较早初始列表晚于新的回放后列表返回：预测当前列表先有 Job，随后被旧空页覆盖。实际固定 RED 复现，但此时 busy=false，与 CI 截图的全部状态不一致。
3. 当前 workspace 未变而 Policy 生命周期改变：预测旧生命周期列表仍可覆盖更新的控制版本。实际固定 RED 复现 r2 cancelled 被回退显示成 r1 awaiting_approval，同样不能单独解释 CI 的繁忙状态。

没有重跑到绿色、放宽超时、加 retries、伪造当前 Job 状态或将原 ACK 代替当前状态。

## 修复与真实回执

独立树 `m62-group-ci-diagnosis-active`，基线 72e4e64。仅两个文件：

- `apps/web/src/features/authoring/useAuthoring.ts`：每次列表请求取得自己的读取代际；响应只有属于当前会话/工作区且为该生命周期最新请求时，才解码并采用列表和 cursor。effect cleanup 废弃旧列表请求。原权限判定、命令 key/body/ACK、繁忙状态、学科写取消和 API 均保持原语义。
- `apps/web/src/features/authoring/useAuthoringListOrder.test.tsx`：真实 hook、原命令存储与受控 AuthoringPort；五项覆盖持有列表状态、同 key 回放后旧页、Policy 生命周期旧页、分页 cursor、最新空页正控。不是 SQLite/native/真实 Provider 集成测试。

提交按顺序为 `236fbc93dce481ca31943fb4e0a643cefd1ecfbe`（受控 RED）和 `f18c92c1ad74598a70b731ce9caf241e40d8e841`（修复及五测试）。

| 阶段 | 实际结果 | 绑定范围 |
|---|---|---|
| 初始 native runner | ESM 加载失败，exit 1 | 产品用例未运行；原日志保留 |
| 原 native 完整 case | 1 PASS 10.6 s | 基线 72e4e64，964 Git inputs |
| 初次受控测试 | 2 FAIL / 1 PASS | 原 runner 只采 tracked 文件，未采当时新测试；不作为完整固定输入证明 |
| 固定受控 RED | 2 FAIL / 1 PASS | 236fbc9，965 Git inputs，before/after 相同 |
| 最小修复反馈 | 3 PASS | 当时工作树有生产修改；不是 clean HEAD 验收 |
| 最终 Authoring web | 63 PASS / 11 files，3.17 s | f18c92c，965 Git inputs，before/after 相同 |
| 最终 TypeScript/lint | exit 0 | f18c92c；tsc noEmit、noUnusedLocals、noUnusedParameters |
| 修后原 native 完整 case | 1 PASS 9.0 s | f18c92c，965 Git inputs，before/after 相同 |

所有实际命令、退出码、时间、log SHA 在 `command-index.json` 和各原始 receipt 中。`actual-git-input-bindings.json` 核了每个相应阶段的所有输入与实际 Git blob SHA-1 及 SHA-256。`source-origins.json` 核 21fc、72e4e64、f18c92c 的 hook、原 native spec 和 runtime；原 spec/runtime 均未改变。

native 使用原 AuthoringRuntime 的独立动态 loopback 端口。私有 Playwright 配置省略与该用例无关的固定 8765/5173 webServer；所有用例步骤和 action/assertion 超时不变。它与完整 CI 配置仍有此差别，结果不等同在 CI 资源环境复现。只管理此 harness 创建的子进程；未杀未知服务。

## 尚未证明及下一任务

- 历史 push CI 的 group busy/空列表确切原因未确定；本地修前/修后各一次 PASS 都不能关闭原失败。
- 未对最终候选运行整个浏览器集或整体平台验收；没有运行真实托管 Provider、付费 DeepSeek、模型质量/教学审核或隔离算术。
- 没有 DB migration、HTTP/生成契约、worker、政策或授权变更，没有读 key 或进行远端写。
- 独立审查候选后才由 root 决定集成；review 结果与当前合并基线的门禁另记。
- 对原 CI case 的下一项因果工作：在保持原断言的前提下记录有界无正文的 replay ACK decode/admission、IDB commit、list request/headers/body decode、list admission generation、busy finish 和目标按钮 DOM 状态。使用各进程自己的序号/时钟，跨进程只用明确关联 ID；断言失败后冻结快照。不能将后读取成功或跨时钟相减作为截止前完成证明。不采 body、主题、材料、headers、凭据或完整服务端错误。

完整最小任务回执见 `task-receipt.json`。历史 CI 失败必须保持开放。
