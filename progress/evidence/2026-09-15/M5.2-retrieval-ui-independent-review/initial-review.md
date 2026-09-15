# M5.2 检索 UI 独立只读首轮审查

本报告以当前 `PRODUCT_DESIGN.md` 3.0.3（SHA `a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8`）为唯一规范，审查列于 input-manifest.json 的 17 个源码/测试文件。源码属于未提交 WIP；未运行测试、浏览器、数据库或网络，未改主树。C 的运行结果仅是其报告，不计作本审查者执行或独立确认的测试。

## M52-UI-B-01 — 同一原命令并发重试形成不可恢复的本机冲突（P2，待运行复现）

位置：retrievalCommands.ts 的 persistCommand/readCommands；DraftStore.ts 的 revision 不匹配分支。

两个页面均读取同一 workspace、同一 command_id、同一 body 且 ack=null 的持久命令。控制两次 persistCommand.load 都先读 r1，随后 A 保存 r2、B 按 expected r1 保存。真实 DraftStore 对第二次写入追加 conflict，即使命令文本完全相同。readCommands 对任何冲突一律抛错；当前检索 UI 没有冲突恢复入口。由此下一次挂载及所有该工作区命令读取可持续失败。HTTP 是否已经发生取决于 reloadCommands 的交付顺序，不从静态源码推断。

这违背 §20.7 和 R-27 的同一原命令幂等恢复目标；没有证据表明服务端会创建第二任务，也不报告为服务端授权绕过。建议真实 DraftStore/IndexedDB seam 先测两次 load → 两次 save，证明同一命令可恢复；修复仅合并可证明相同的命令身份和单调 ACK 事实，真实不同 key/body/ACK 的候选必须继续保留和拒绝。

## M52-UI-B-02 — 结果父链导航绕过既有离开保护（P2，待运行复现）

位置：RetrievalPanel.tsx 的“沿此完整教材路径打开”按钮；Shell.tsx 的 RetrievalPanel open 回调与 protectLearningDialog。

初次本机 readCommands 发生 READ_FAILED 时 storageError 非空、safe=false；正常 status/query 可继续返回 course 范围的完整命中。普通关闭受 protectLearningDialog 阻止，但命中父链按钮只按 busy 禁用；其 open 回调调用 openReal 后无条件 setDialog(null)，可绕过正在展示的保护条件。

此处准确问题是关闭/导航保护不一致，未证明任何持久字节已经丢失；后端实际 Content/Policy 仍独立验证，不报告为已读取私有材料。建议用真实有效命中与一次本机读取失败验证普通关闭和父链导航一致，并在当前 owner/Policy/safe 不允许时拒绝导航。

## 已核范围与边界

当前代码通过严格 generated schema 和关系校验核 scope/ref/body SHA、whole-block codepoint locator、未审/历史/归档/来源警告；整块 text 以纯文本显示。父链按钮只针对实际 course 完整链，block/lesson 单独 scope 不猜教材父级。新命令先写本机存储再 POST；丢 ACK 重试使用持久原 key/body/版本，真实 ACK 和后续 Job GET 分开。owner/session-generation/paused/sequence guard 阻止迟到读取更新新视图。overview 是已登记范围的明确选择入口，不自动扩大 scope 或自动重建。此类结论是已读源码行为，不是运行证明。

C 自检的“practice 附加 lesson 被推成默认范围”有其单独 RED/GREEN；本次 snapshot 已包含限制真实 Reader context 的 helper。Panel details 布局调整也已进入本次 snapshot，未把 native-run-02 的截图或测试结果绑定为新布局已验收。

除上述两项，本次有界读取未发现另一条阻断；这不替代尚在继续的 owner 测试、最终原生或全阶段门禁。首次私有 snapshot manifest 脚本使用系统 Python 缺失的 datetime.UTC 而退出，原源码副本已产生；后续只清点这些原字节，capture-first-error.log 保留此 harness 错误，不涉及产品执行。
