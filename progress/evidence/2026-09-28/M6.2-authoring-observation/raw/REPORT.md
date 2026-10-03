# M6.2 Authoring 合成回放被动观察：待独立审查

固定候选 `8b6629205a72593ab835e2c61a20b6e1eac7061e`，基准 `ce42bf8cae734e49166a1472184fd9c3fa875bc7`。独立工作树 `m62-authoring-observation-active`，9 文件、474 新增/14 删除，已提交且 clean；未改 main、未推送。唯一规范 v3.0.7 SHA256 `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`，依据 R-29/R-36、§14/17.3/18.4/20.8。

## 原始 RED 与结论边界

原 507 PR run `36368226913` 的实际 checkout `f74cd7a8f81a8b51abf06ae12fb62a51da3bb99d`，浏览器 99 PASS/2 FAIL。此任务针对 `authoring-groups.spec.ts:294` 原回放用例，`readPrepared:48` / caller 322 的详情按钮 click 10 秒失败。原日志 SHA256 `3c1d436f4bc5953c99fb20e83486dda5ba771e65424a996ba249ba62b8f877d5`；完整日志、错误上下文、截图和源定位的私有位置/哈希见 `original-red-bindings.json`。原 ACK 确认、空列表和忙状态截图缺少列表生命周期证据，根因仍为 **UNKNOWN**。

本任务使用 diagnosing-bugs 技能，但明确限于新增经授权的观察能力：没有可确定复现原 CI 因果的本地环路，故不声称完成原故障修复/关闭。没有重跑原 case 或 CI 找绿、延长原等待、增加业务请求或改变最新列表/权限决策。新测试的 RED 指观察能力缺失或观察器自身问题，不能替代原故障 RED。

待区分的假设（均未据此判定原根因）：

1. 回放 ACK 后列表请求/响应处理仍未结束：观察 Node request/response/finished 与 Hook list_requested/returned。传输结束也不等于 JSON/契约处理完成；同路径并发请求无法唯一对应时不猜测。
2. 列表已返回，但被当前生命周期或较新序号丢弃：观察 Hook returned/discarded 及闭合 reason/原序号。
3. 列表校验或执行分支抛错，或原操作尚未 finally：观察 error/finally、原操作序号及实际 working/busy。
4. 列表已接受而控件投影仍为空/忙：观察 accepted 的 job_count 与 React 提交后的 rendered 元数据。它们仍不等于页面上每个 DOM 按钮的同步快照。

## 实现与保留的不变量

`authoringObservation.ts` 仅在显式合成开关与绑定接收器同时存在时启用；默认无 ring、无投递。闭合字段只含 epoch/Hook/序号、布尔、数量及固定 stage/reason，不含对象 ID、工作区、命令 key、异常文本或正文。512 条/epoch、64 条/批、一次一批；阻塞或失败接收器不等待业务。

`useAuthoring` 在原 await/guard/写入前后被动记录 ACK 接收/落盘、列表开始/返回/接受/丢弃/错误/finally、操作结束，以及实际 React busy/ready/academic/job_count。原条件、请求参数、调用顺序和返回值保留。单独的 working latch 与提交后的 busy 不合并。

`authoringDiagnostic.ts` 用真实 Playwright Request 对象的 WeakMap 分配唯一 Node ID，仅记录主 frame 的固定 session/prepare/list/detail 路径类别、GET/POST、状态、finished 或闭合失败码。无 body/header/query 读取或追加；原测试自身既有合成 route 回放检查保持原状。2000 个网络事件、1024 条投递记录，异常只计数。浏览器 source_ms 与 Node delivered_ms 独立；没有跨钟相减或猜测 Hook→HTTP 配对；source_delivery_completeness 明示 unknown。

原实践题组 case 只在准备阶段启用观察；readPrepared 的原 click 返回或抛错时同步冻结已收到记录。保存/attach 上限 250 毫秒发生于断言之后，原失败对象重抛，保存失败不更改断言。没有断言后 API/HTTP 读回。failure-only CI artifact 列表只增加该 JSON glob，其余 CI 条件/权限不变。无 DTO、核心模型、后端、数据库迁移或产品状态变更。

## 实际验证（全部保留原输出）

| stage | 实际结果 | 范围 |
|---|---|---|
| 01 | 3 FAIL | 已完成业务状态断言后，缺少 Hook 观察记录；观察能力 RED |
| 02 | 8 PASS | 3 受控 Hook + 5 原列表顺序测试 |
| 03 | 4 PASS / 1 FAIL | 已捕获 snapshot 在开关关闭后引用空对象的观察器自身问题 |
| 04 | 13 PASS | snapshot 绑定原 ring 修复及上述相关测试 |
| 05 | 3 PASS，10.9 秒 | 独立真实 Chrome：原 10 秒 click 故障对象保留；两个同路径实际请求的 response/finished 分离；晚投递冻结；保存失败不覆盖原结果 |
| 06 | 74 PASS / 13 文件 | 全 Authoring 前端测试，含 off/blocked/throwing 接收器下原回放次数、参数、ACK 与 busy 恢复 |
| 07 | PASS | 全 Web strict lint/typecheck |
| 08 | FAIL | 私有 native 类型配置未解析仓库既有 `@playwright/test/index.mjs` 声明；原报错全部保留 |
| 09 | PASS | 私有声明桥精确 re-export 已安装官方 index.d.ts，strict 不变；3 native 文件及其依赖 |
| 10 | PASS / 9 文件 | 原 scanner 暂存检查，零豁免 |

每阶段 command/UTC/exit/log SHA、前后输入清单及全部原字节见该阶段 receipt、inputs-before/after 和 source-by-sha256。06–10 的 827 项显式工程输入逐项与候选 Git blob 相同；05 的 825 项相同，只有之后追加的 Hook 单测与 ADR 两个非 native 执行输入不同。`GIT_SOURCE_BINDINGS.json` 明确所有早期版本差异，不把早期执行冒称最终字节执行。827 是 run.py 显式根范围，不声称覆盖仓库全部文件或所有外部运行时。私有 Playwright config 固定只跑新 3 case、retries=0、webServer=[]，仅测试自己创建的 127.0.0.1 临时端口；未占 8765/5173、未停止未知服务。

## 下一任务与未运行项

本候选需独立 Spec/Standards 审查后由 root 决定整合。未运行原 Authoring case、全原生套件、新远端 CI、真实模型/DeepSeek、生产数据；也未判定原 507 失败已修。下一次 root 授权发布后如原失败出现，读取本次固定断言边界内实际观察，再针对可证实分支设计独立诊断；缺失观察仍 UNKNOWN。本目录是含私有绝对路径及完整工程原件的开发证据，不能整目录直接公开。
