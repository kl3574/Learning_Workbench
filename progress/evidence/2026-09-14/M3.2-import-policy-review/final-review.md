# M3.2 Import 策略修复：冻结后有界静态复核

结论：原报告提出的两项修复均已实际落入冻结源码；本次指定范围没有再发现阻断恢复的具体残余问题。这是静态复核，不是新的原生运行或“安全全通过”结论。原始静态报告的公开派生见 initial-review.md，原报告字节保持不变。

## 实际核对

1. **原件下载末端授权已落地。** `apps/web/src/features/imports/DraftPreview.tsx:43-55` 在获得并校验 blob 后真实 GET `/api/v1/sources/{id}`，检查当前 source ID、source hash/size、artifact ID/hash/size；重复检查 mounted、局部 accessEpoch 与共享访问 generation 后才创建 Object URL。403/409 或错绑定进入错误路径，不会 click 下载。组件卸载仍撤销所持 URL。此修复补上另一 profile 启动 independent 时不共享浏览器广播的服务端授权接缝；不宣称最后读取之后绝无任何后续策略变化，也不宣称撤回先前已经合法取得的本机文件。
2. **重新选择的 File 归属已上提。** `useImportWorkflow.ts:234-241` 的 rememberOriginalFile 以当前 active import ID 保存 File 至持续挂载的 originalFiles map；`ImportWorkflow.tsx:59-60` 将回调同时交给 EncodingPreview 和 FailedOriginal；两处 input 回调（EncodingPreview:53、FailedOriginal:48）同步写回。暂停仍卸载敏感子视图，清理其解码文本、派生 bytes、确认、验证状态与 Object URL，恢复时从该 import 自己的 map 值重新初始化 File，必须再次严格核验。整工作区更换或用户真正关闭导入会清空内存 File；恢复 localStorage 仍只保存任务 ID，不写原件或正文。
3. **root 补充的晚上传时序有明确恢复入口。** `useImportWorkflow.ts:159-169`：策略恢复 effect 在 activeRef=null 时已读完，随后上传 POST 晚返回，确实不会因 setActive 单独自动 refresh；现在会保留 server import/job IDs、File、缓存失败提示，并显示“原件已暂存，但访问策略已经变化。请重新读取导入状态后继续。”。`ImportWorkflow.tsx:37` error+active 分支渲染重试按钮；`retry:137-142` 用同一真实 active ID 读取。finally 清除 mutation/busy，恢复授权后按钮可达。仍受暂停限制时不执行读取，解锁后 effect 会尝试真实回读；没有自动确认、取消或重新上传。明确重试状态不等于永久无提示的 snapshot=null。

## 保留的策略边界

Shell 按 workspace key 持续挂载 ImportWorkflow，并以 paused 暂停材料；hook 每轮 access/paused 切换使旧 task/draft/下载 epoch 失效，清空服务端投影，真实 GET session 后重新读取原 active ID。active independent 全 workspace 材料阻断仍在服务端。submitted/grading/needs_review 只解除一般 subject 锁；相关帮助/答案与无法证明不含保护答案的 opaque 作者私有原件/私有预览仍由各实际端点拒绝。DOCX 安全 learner 衍生正文可以恢复而作者原件保持受限，不能用 session 的 active_independent_attempt_id=null 作为下载授权。规范依据为 PRODUCT_DESIGN.md:46、314-320、943-956。

## 验证范围与源码限制

- 最终工作树 HEAD 为 `bae4438d3e374fd80999a2704b0588452edf9537`；11 项工作树字节与该提交的 Git blob 逐一相符。独立读取 frontend-freeze.json 的 11 项并逐文件计算 SHA-256 全部相符；这是 9 个变更的生产/测试文件加 2 个原生旧测试文件。复算 manifest 定义的聚合哈希相符。本文语义审查限于两项原发现与 hook 恢复路径；并未语义审阅所有 11 个文件。
- source-comparison.json 记录初次读取开始 5 个源文件、初次读取结束 9 个源文件、最终读取 9 个源文件；早期只保存了哈希及阅读输出，没有保留完整旧源码快照，不能重建成整份历史源码验收。
- 只回读前端已有输出：定向 native 日志为 5 PASS / 21.5s，unit 为 162 PASS / 23 文件 / 2.97s，最后 lint 日志无诊断。它们由前端执行，独立 reviewer 未重跑，未把这些数量重标为自己的测试。未在此包复制原始 native 日志、DOM、截图、DB 或 profile。
- frontend-freeze.json 明示：五项 native 完成之后又增加晚上传重试提示与最终 source.id 相等校验；这两项没有分别获得该五项 native 的运行覆盖。最终 lint 在最后一项之后完成。完整固定源码验证仍由 root 后续执行；本次静态复核不替代它。
- 新增加的 native 对失败编码任务 File 恢复有实际覆盖；FailedOriginal 的相同接线在本次只作静态核对。末端授权逻辑已读到，不把一般角色切换测试冒称所有跨 profile 延迟字节时序都已验证。

## 发布安全与来源

本包只含审阅文字、相对工程路径和哈希。临时本机证据的绝对路径替换成 local-evidence:描述名；原始报告与前端冻结回执的原 SHA、公开衍生 SHA 分别写入 manifest.json。没有修改原始临时日志，没有复制能力码、CSRF/cookie 值、个人学习内容、数据库或浏览器资料。提及的失败与回归均来源本项目原创合成导入场景；本静态包不新增任何学习数据。逐文件 scanner 结果见 inspection.json，它只补充人工检查，不保证能识别任意个人文字。
