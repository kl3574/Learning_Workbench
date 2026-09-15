限定结论：当前最终 sequence 修复的两文件静态复审无新增阻断。不是原 CI Reader 失败根因认定，也不是独立重跑测试、真实 API 或浏览器验证。

useWorkspacePolicy.ts 的显式 access/focus/refresh 仍先增加 epoch 并立即 known=false；旧 epoch 响应无论成功或失败不能落状态。后台 poll 不推进 epoch，仅分配递增 sequence；同 epoch 中只有 requestSequence>applied 的完成结果能推进观察，成功和失败都更新 applied。因此旧成功不能覆盖新失败，旧失败不能覆盖新成功。live=false 与 epoch 共同拒绝已清理 effect 的后续结果；工作区字段还须与实际 response.workspace_id 相符。旧 coalescing 没有留在最终源里，每2秒仍可发下一次读取，某个 promise 挂起不再阻塞后续发起。

采用较旧但同 epoch 的真实已完成响应、即便较新请求仍未返回，是这次明确的恢复语义。known 表示最近已采用观察，不是服务器墙钟当前策略的证明；浏览器配置间仍有原轮询/网络时延窗口。安全判断仍须由每个受保护后端 owner 在实际读写时核当前 Policy，不得以该 hook 的 known 作为授权。后台重叠请求及没有全局 fetch 超时是原实现保留的边界，本修复没有声称全部请求可终止/网络资源有界。不能将“允许较旧完成响应”解释成覆盖已完成的较新错误或越过显式失效。

读过的永久 8 case 使用 deferred Promise 与 fake clock，保留 slow read 后续 restricted、access/focus/refresh 三种失效、失败后恢复、挂起读取仍有后续 poll、旧成功不能盖新失败、工作区/卸载释放。旧失败不能盖新成功的对称方向本轮由 current/applied 同一代码分支静态核验，不冒称有单独实跑用例。清理 timer/access listener/focus handler 保持，原2秒间隔未放宽；这组测试不是权限服务器端或浏览器实际调度证明。

实际只读核四轮原 receipts/logs：原6例 4FAIL2PASS→同字节6PASS；新增两反例后 coalesced 2FAIL6PASS→相同8例最终8PASS。原 hook 与73d65af Git字节相同；原6例 red/green 测试字节相同，扩展8例 counterexample/finalgreen 测试字节相同。每轮声明的 before/after输入一致；原日志 hash 与已声明项一致。当前两源与 green-02 归档逐字相同。运行者是 root，本代理没有重跑。
