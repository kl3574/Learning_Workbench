# M3.2 Import 策略恢复有界只读审阅

本次仅静态读取当前 m32 工作树和 root 已执行浏览器日志；没有启动服务、运行测试、修改工程或重新标记验收成功。唯一规范为 PRODUCT_DESIGN.md，SHA-256 `ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`。前端正在并行修复，因此下文是验收风险交接，不能充当最终固定源码验收。

## 已有失败的真实范围

`local-evidence:m32-exact-browser-runner.log` SHA-256 `d0b117b4d45b2b1bdd3b391e84a355d49ea7df43db516beeb639db24a370bf52`：54 PASS / 3 FAIL，make 退出非零；三个失败分别为 document-imports.spec.ts:127 的 DOCX 角色切换、imports.spec.ts:254 的作者学习包角色切换、imports.spec.ts:379 的迟到预览/原件。失败位置分别等不到恢复的 preview_ready 或角色拒绝提示。日志并未证明迟到字节已经泄露；第三项在释放被延迟响应前就失败。独立审阅没有重复前端正在进行的复现。

当前 Shell.tsx:176 已把“导入”排除于通用替换分支，保持 `ImportWorkflow key={workspaceId} paused={subjectLocked}` 实例；UploadForm.tsx:8-19 保留 File/kind/courseId 的 React 状态，只移除表单 DOM。这解决原有暂时 unknown 导致整个 hook 卸载的结构问题，是否完整通过原三项由前端实际原生复验判断。

## 两项具体剩余验收风险（已发给前端）

1. **延迟原件需要服务端末端权限复查。** 所读 DraftPreview.tsx:38-50 在 GET artifact 返回后只验证原件字节、`getSessionGeneration` 和局部 epoch，随后创建 URL 并 click；没有 Reader SourcePanel.tsx:28-31 已使用的再次 GET sources。跨浏览器 profile 在同 workspace 开始独立测试不会共享 BroadcastChannel；在 useWorkspacePolicy.ts:23 的两秒轮询下一次读到变化之前，先前已获 200 但被延迟的原件仍可能发起下载。最小验收时序：A 已取到作者原件响应并暂停交付 → B 同工作区真正开始 independent → 轮询尚未获新状态时释放 A 的旧响应 → 期望零下载，最终 GET sources 返回真实 guard 拒绝。最终来源复查还须比较 source ID、artifact ID、hash、size，并在其后重复局部 epoch 检查。本次只是源码可推导时序风险，未声称新增 native 红测；不同 profile 的角色是否共享须依实际 session 身份，不用它替代上述真实 workspace 测试策略触发。应用外已经合法取得的文件不能被撤回（规范 §20.2:952）。
2. **失败任务重新选择的本机 File 仍位于将被卸载的子组件。** 所读 ImportWorkflow.tsx:32-66 在 suspended 时卸载 EncodingPreview/FailedOriginal；两者文件选择保存在各自 `useState(originalFile)`（EncodingPreview:8,53；FailedOriginal:8,48），没有写回 hook 的 originalFiles map。最小操作：恢复一个旧失败任务（原 originalFile=null）→ 重新选择同哈希原件 → focus 触发策略重新检查/明确角色切换 → 恢复。该重新选择的 File 随子组件卸载丢失。新上传且存入 originalFiles map 的文件不属于这个缺口。可以提升这份 File 所有权或保留子组件，仅清除/隐藏解码正文、派生 bytes、确认与 URL；不要把安全清除正文与丢失用户文件选择混为一事。

## 状态所有权与敏感投影

| 数据 | 当前所有者/位置 | 暂停或权限变化要求 |
|---|---|---|
| active.importId/jobId、recovery IDs、manualId | hook active / recovery.ts:12-38 workspace 分区 localStorage / Workflow | 保留定位，不当作读取权；只有 ID 写恢复缓存。workspace 改变用 key 卸载隔离。 |
| 上传 File、解析格式、目标课程 ID | UploadForm 本机内存；上传成功后 hook originalFiles map | 保留未提交输入，不持久化原件；暂停移除文件名/表单，恢复后重新校验目标可用性。 |
| accepted warning codes、ID mapping、confirmed | hook useState | 可以保留未提交设置；只能配合重新取得的相同 input_sha256/candidate 和服务端校验执行确认，不自动重放写入。 |
| snapshot candidate_summary（标题、counts、unresolved refs）、warnings（message/locator）、preview_refs | hook snapshot；Workflow:49-55 | 全部是材料派生投影，不仅 body 敏感；清空并在当前角色/策略下重读。 |
| draft payload（正文、题干、标题/目标/引用、citation metadata）、draft warnings/hashes | hook draft；DraftPreview:11-24,69-70 | 不留隐藏 DOM、旧选择结果或异步回填；按当前 import/draft 精确 ID 重读。公开题面结构也不能绕过 active independent 全局材料锁。 |
| source.artifact（下载路径、文件名、媒体类型、hash、size）及 source warnings | hook source；DraftPreview:27-55 | 与安全正文独立授权；私有原件拒绝不应把允许的 DOCX 安全文本误标为失败。字节下载需最后真实来源复查。 |
| Job progress label/error/warnings/result_refs、commit course refs/titles/result | hook job/result/committedCourses | 暂停清空；由授权 GET 回读已发生结果；不把取消、关闭、响应丢弃变成“未提交”或“已撤销”。 |
| encoding preview、UTF-8 derivative、原件验证状态、object URLs | EncodingPreview / FailedOriginal | 暂停清理派生可见文本、确认和 URL，并使迟到 File.arrayBuffer 无法恢复；File 本身的可恢复内存所有权单独处理。 |

## 授权、迟到响应与取消接缝

- useWorkspacePolicy.ts:9-25 在 access broadcast/focus 先 known=false，真实 GET session 校验 workspace，epoch 拒旧读；后台轮询不等于即时跨 profile 通知。Shell unknown 与 active 都必须暂停材料，但 unknown 不是取消任务或清空未提交输入的理由。
- useImportWorkflow.ts:103-122 每次 paused/accessVersion 变化递增 taskGeneration/draftGeneration/accessEpoch，清空服务端投影，connect 完成后才 refresh 同 active ID。当前最新 accessReady 还包含 `!auth?.active_independent_attempt_id`。失败 GET 应保持可读拒绝提示，不显示旧成功。
- 上传 POST 可能已经在服务端完成，即使响应返回时 paused 或窗口已关。现 hook:154-169 在收到有效响应后记录任务 ID，再按 generation 决定是否展示；这符合不虚报取消的边界。关闭 hook:77 只清理本机引用与回调，不能自动 POST cancel。真正取消仅由明确按钮调用、服务端终态确认；commit 同理必须用当前 input hash 与 mapping 明确请求。
- 本轮不要求 AbortController 代替所有权校验；网络 abort 不能撤销已执行的服务端事务。关键是旧异步 callback 不修改新 generation 的材料投影，以及下载 URL 在失去授权后不生成/不复活。

## independent → submitted pending 的准确释放范围

依据规范 §1.1:46、§6.4:314-320、§20.2:943-956。真实实现 `Policy.check` application/policy.py:30-57 与 assessment_access.py:43-48：

| 状态 | 导入普通安全材料 | 作者私有包 preview / draft / job 私有诊断、opaque 原件 | 相关提示/解答 |
|---|---|---|---|
| active independent | 全 workspace subject guard 拒绝；仅自己的 attempt 正常读写 | 作者也不能读取 | 拒绝，包括已缓存的旧 Practice 释放 |
| independent submitted / grading / needs_review | 正常安全教材、笔记与 learner 衍生正文可重新请求 | 仍受 ASSESSMENT_ANSWER_PROTECTED；无法证明无受保护答案的 opaque 作者原件仍拒绝 | 相同完整题引用或 exposure_group 的帮助/答案继续拒绝 |
| 必要评分完成后的 graded，且无其他保护实例 | 依当前角色正常读取 | 仍须作者权限、workspace/hash/来源校验 | 按冻结策略及主动授权请求释放 |

GET session 返回 active_independent_attempt_id=null 只表示广泛 subject 锁可解除，绝不证明 private_artifact 可读。ImportService._access:65-70、_guard_preview:81-84、preview:163-175、draft:265-296、_artifact/source:298-324 分别实施这些边界；没有要把后续 pending 原件拒绝改成 UI 便利放行。DOCX 的安全 learner preview 与 author_private 原件本来是两条边界。取消回执的既有敏感 Job 字段会在当前策略下重新裁剪（imports.py:206-226），不能因旧回执成功恢复私有诊断。

## 源码边界与本次操作

只写 本机临时目录 本报告及起始哈希记录；没有 production/test/进度/Git 写入。下面记录开始读取和结束读取哈希，变化说明前端修复正并行进行；已通知前端上述两个风险，后续修复及 native 验收不属于本报告的 PASS 范围。

| 文件 | 开始 SHA-256 | 结束观察 SHA-256 |
|---|---|---|
| `apps/web/src/workbench/Shell.tsx` | `ebff9aba6b0df91c87e3578d8718a00d466be65257a911d15a3998d1ec2f4faa` | `ebff9aba6b0df91c87e3578d8718a00d466be65257a911d15a3998d1ec2f4faa` |
| `apps/web/src/features/imports/ImportWorkflow.tsx` | `cd74cdbac406b206911d95f391666b5a10838b4dc97a75819f99825cbec2e972` | `360d4d916dc695c5d047e3624e7ad8c671a8ce3d31afb236946dea104eb6fb06` |
| `apps/web/src/features/imports/UploadForm.tsx` | `aafac080da83c860ca1220327342594e3b2f890620b4fe9b3d8f2af27886c0cb` | `aafac080da83c860ca1220327342594e3b2f890620b4fe9b3d8f2af27886c0cb` |
| `apps/web/src/features/imports/useImportWorkflow.ts` | `7d69690e9ffa213c4637bc2c88ae8f81dd11639214fb2ddcdbed7a4468f7195e` | `fc0b87f5f459ee527fe4d687d8ec31d310d831fdfbec040300c9426db035dcc2` |
| `apps/web/src/features/assessment/useWorkspacePolicy.ts` | `986216cd86cc1068af2d70b3dff8b957e4ebd8176c92244855c35a35abf46c11` | `986216cd86cc1068af2d70b3dff8b957e4ebd8176c92244855c35a35abf46c11` |
| `apps/web/src/features/imports/DraftPreview.tsx` | `开始未固定，仅结束观察` | `804d25344f1d03740fa6641b80b4f4609ae3dfcc3532b131d279cc0ddc92e769` |
| `apps/web/src/features/imports/EncodingPreview.tsx` | `开始未固定，仅结束观察` | `7bd81904b739377455766fc60b3b3b6949d9c0cdcf985dbe33e4576a93494c0d` |
| `apps/web/src/features/imports/FailedOriginal.tsx` | `开始未固定，仅结束观察` | `053b7e41d93aff4d27104caef24925cde7eaa84b58f47f1702805e78c77e8163` |
| `apps/web/src/api/client.ts` | `开始未固定，仅结束观察` | `1e39413dcd63ac19bdcd802f2550632365cf8bb70bd83805ed63b13f3bf4e49b` |
