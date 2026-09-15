# ab6 导入窗口未出现：独立只读诊断

当前可定位到导入按钮的权限拒绝分支；尚不能确定点击时为何受限。不是旧历史 Reader 读取断言，也未进入 DOCX 上传、角色降权或私件下载阶段。没有改代码、运行测试/浏览器、请求模型或读取凭据。diagnosing-bugs 的实际复现/修复阶段按本次只读授权范围未执行，下列假说均待验证。

## 实际证据

精确源码 ab6c27b417b98e50eb5e2feb469be191d1db4d41。原 push job 104379946522 日志 SHA 27ba3ee6…：87PASS、1FAIL；reader.spec.ts:209 的整条测试 60 秒预算耗尽，最后位于 :216 selectOption，call log 只有等待 dialog 下的“解析格式”。没有各步骤起止时间，不能说 select 本身等满 60 秒，也不能分配 bootstrap、生成 DOCX、点击所用时长。

已实际阅读 artifact 10396848014 的 error-context.md（SHA 70c9a732…）并用 view_image 实看 test-failed-1.png（SHA 630775b8…）：没有导入 dialog；导入按钮保持焦点，顶部有“当前测试策略限制此操作…”；中央是空路线、右侧普通未配置 Agent、底栏“正常学习 · 本机”和 UI 已保存。PNG 肉眼观察与 DOM 分开记录。此附件只有这两文件，没有点击时刻账本、请求状态 JSON 或 trace。

## 源码闭合的路径

- Shell.tsx:99：subjectLocked = !policy.known || !!policy.independentId。
- :107：该警告由 openAux 的受限分支设置，随后立即 return，不 setDialog；:218 顶部导入按钮没有 disabled 条件，点击调用 openAux('导入')。
- :232：只有 dialog 非空才挂载真实 Dialog/ImportWorkflow。即使已经打开后暂停 ImportWorkflow，也会保留外层 dialog。本次最终附件中整个 dialog 不存在，比“内部表单请求慢”更符合入口被拒。
- helpers.ts:23–24 只等待 UI 会话保存。useWorkbench.ts:83–86 的 saved 属于布局恢复，与 useWorkspacePolicy 的异步读取不是同一完成条件。
- useWorkspacePolicy.ts:5、:12、:15–20、:23–29：初次读取/明确失效、当前读取失败都可能产生 known=false；后台成功可随后恢复。openAux 没有保存或自动重放被拒的导入意图；historyWarning 不会随权限恢复自动撤掉。
- Shell.tsx:230 的“正常学习”不检查 known，单靠该文字不能证明点击或截图时权限已核验。但当前附件同时显示普通路线和 Tutor，而 :198/:202/:226 在 subjectLocked 时切换受限内容，因此最终画面与随后恢复为不受限一致；它仍不是点击当时的状态证据。
- UploadForm.tsx:24–26 的解析格式明确存在 docx 选项。useImportWorkflow 的 connect 可能等待 session/courses，且暂停时隐藏表单，但这会发生在已经存在的 dialog 内；当前证据不支持把缺选项或表单请求本身列为首要根因。

## 排序后的可证伪假说

| 假说 | 预测与如何排除 |
|---|---|
| 1. 布局已 saved，但初始 Policy 或明确重新核验尚未完成时点击 | 点击时 known=false、无有效独立测试结论，出现拒绝且 dialog 缺失；正常响应完成后仍不自动打开，第二次明确点击可打开。若点击时实际 known=true 且 independentId=null，该假说被排除。 |
| 2. Policy 的当前读取暂时失败/失效，点击随后才恢复 | 点击前存在该 epoch 的失效或失败，known=false；后续正常读取清除受限内容，但旧拒绝文字仍留存。需同一单调时钟的请求结果与状态记录，截图无法区分它与假说 1。 |
| 3. 点击时确实存在工作区独立测试，之后提交/放弃/到期释放 | 点击时 hasIndependent=true，拒绝属于正确安全行为；必须有真实 attempt 状态变化支持。测试 bootstrap 只重置布局/本地缓存，不清测验数据库，现有截图不能自行排除该分支。 |

暂时不采用“旧 Reader SQL 锁问题”“DOCX option 不存在”或“select 独自等了 60 秒”归因。PR 同源通过由 CI owner 单独留证，不反向证明 push 原失败不存在。

## 下一步最小实验（未运行、未实施）

先在真实 Shell 接缝固定一个受控窗口：工作台已 saved，保留真实 useWorkspacePolicy 的未完成读取；在导入按钮首次可点击时点击。只记录同一单调时钟的 click、known/hasIndependent/subjectLocked、dialog-present、请求开始/结束及状态码；不采 header、cookie、响应全文、启动链接或秘密。释放正常读取后核按钮操作不会自动重放；第二次明确点击应打开。另以实际独立测试的 hasIndependent=true 保留拒绝负控。若 controlled unknown 不能复现同一“警告+无 dialog”形态，则不要据本假说修复。

之后在原 :209 用例限定记录 bootstrap 完成、DOCX 子进程完成、点击前后、dialog 出现、select 完成的相同 Node 时钟，保留原 60 秒和原安全断言；由这次观察决定是否需要进一步区分初始未完成、重新核验或真实测验。先获得这个边界证据，再选择是否调整按钮实际可用性或测试就绪条件。不要用固定 sleep、扩大超时、自动重复受限操作或移除权限 guard 代替诊断。

本次没有进入 :217 后的上传与 :228 后的角色/私件断言，不能给该安全场景记 PASS。Agent 生产实现与真实模型请求也不因本分析获得完成状态。
