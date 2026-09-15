# M4.2 共享草稿日志独立复审

复审结论：在本次固定范围内，迟到 ACK、本页基准误判、显式选择保全和正常选择通知的已报告问题均已闭合；未发现新的阻断 finding。此结论不是 M4.2 阶段验收、完整套件通过或原生浏览器通过。

唯一规范为 PRODUCT_DESIGN.md 3.0.1，SHA `397829f5267248aedfc60faf7cacbb12669966b1c1d636a909b04189e0cc09dd`。依据 §4.3、§4.5、§9.3、§15.3 的草稿保全、可读错误、版本冲突和显式比较。复审最终 shared SHA `e24982ac1da83e32b3a993d8dfc01d29827f4365422139d31686f62edb06d419`；永久 shared test SHA `d2aa79645971b3c16780e9f1692c4979330da52ab6f1b882e8a54d4ac9d6c1d6`；RouteEditorDraftSequence test SHA `e8fe4ced478370a40039c752608ff98e7d469c7ec355572d9731a88124caec05`。完整源与证据 hash 见同目录 final-review-receipt.json。

| 问题 / 来源 | 具体反例与最终处理 | 闭合证据 |
|---|---|---|
| 已有原生症状：本页旧写入被当跨页冲突 / root、frontend | 已知 expected baseline 或完整 writing{text,expected} 的 expected+1 自通知不是第二页候选；实际不同 primary 和同 revision 的持久 conflict IDs 仍保留。 | 原 run05 1 FAIL、run06 同最小目标 3 FAIL 保留；owner unit-red02 4 FAIL→green01 4 PASS。未追认原失败唯一根因。 |
| RJ-1：旧 enqueue ACK 误清内存 / root 发现，独立静态确认 | retainObserved 虽保 r2 B，却用 raw r1 A 判断耐久和 acknowledge；无第二编辑时 A 不在磁盘而 safe=true。最终按 adopted observed 判耐久/清 memory，未保留活跃 A 则以 expected0 追加为冲突；失败不无限重试。 | owner unit-red03/red04 真正安全断言 FAIL→green02 5 PASS；永久测试有 beforeunload 实际 defaultPrevented 和最终两候选磁盘回读。 |
| RJ-2：交付顺序证据不足 / 独立静态发现 | 原 own_save_first 先释放 reload，再释放 ACK，没有证明消费顺序。最终先等第二实际 save 调用开始证明第一 ACK 已消费，再释放 held load；反序等 load 返回和 React commit，ACK 仍 held。 | 固定 RouteEditorDraftSequence 41–49 行与 green02；两种顺序不是仅由 case 名字作证。 |
| RJ-3：迟到 resolve ACK 隐藏已观察 peer / 独立真实反例 | resolve r2A ACK held→hook 已读 r3C→旧 ACK→保全写 held，原 hook 退 r2 且 C 消失，unsafe 仍 true。本例只证明候选隐藏，不夸成持久字节丢失。最终 resolve 也 retainObserved 并保同 revision 新 conflict IDs，变化后拒把旧选择当当前。 | 原私有固定 c455e880 单例 1 RED；原 harness 字节不变，只换最终 e24982ac 源后独立 1 PASS。 |
| RJ-4：selected != current branch 时丢选择 / 独立真实反例 | 原 primary B+conflict A，选择 A 的 r2 ACK held，再 peer r3C；保全队列完成后原 disk/hook 仅 C+B、无 A、unsafe=false。最终 selection 在首次 await 前取得独立 memory identity，不覆盖 branch；按 adopted record 证明耐久，否则独立 expected0 保全。 | 原私有固定 8e111500 单例 1 RED→同字节 harness +最终源独立 1 PASS。永久正常例更强地断言 disk A/B/C 全在且 unsafe=false。 |
| RJ-4 的 quota/工作区恢复边界 / owner 补充 | selection 保全写失败时保留 A 的 memory；原 workspace 的候选不进入另一 workspace records，全局 unsafe 保持，另一 workspaceUnsafe 可为 false。重挂载并恢复实际存储后 A/B/C 回磁盘。 | 永久 shared test 131–204 行；明确 disk 不含 A、hook 含 A、beforeunload 被阻止、切 workspace/remount 后恢复；owner focused 23/24 PASS 与最终源 full02 中该文件通过。 |
| RJ-5：正常选择的自通知误补回旧分支 / root 发现，独立静态核验 | own resolve load-before-ACK 会把已明确替换的 B 误认为丢失并触发 pending guard。最终只在 resolving 的完整 text、expected+1、sequence 全匹配时暂缓保全旧 branch；busy 继续保护。更高修订、不同文本或真实新编辑不匹配，仍保全/重比较。 | owner unit-resolve-own-red01 3 PASS/1 FAIL→own-green01 24 PASS；正常永久例断言正确 chosen、0 额外保全写、disk 只有 A 且无冲突。 |

最终静态检查还核实：workspace/session/epoch 的读取与异步归属检查保留；records 继续按工作区投影；global unsafe 与 beforeunload 仍包含整个 memory，而非只算当前工作区；queued 保存不会靠旧 ACK 改写更高已观察修订。原 DraftStore CAS 和真实 conflict ID 存储语义未修改。RouteEditor 的 Policy/access/epoch 与原服务端命令 ACK 保护未修改，源 hash 与 4cf 基线一致。本审查没有改产品或测试源码。

ADR 0015 的共享日志段落与最终实现一致：独立选择身份、adopted record 的耐久判断、expected0 保全、正常选择自通知例外以及本机存储/服务端完成的区分均准确。ADR SHA `ba2aa261a75636c93e95c06ef46e83c8acf08f015c2344a1d054063cc3b9643e`。其首次工作台恢复段落属于另一 owner；本次未把该部分当独立审完或测试通过。

我实际只运行了四次隔离单例：两个原 RED、各自在最终源上的同字节 GREEN；环境为 JSDOM/fake-indexeddb，生产 DraftStore 和 hash 固定 shared hook、两个真实 store 实例，使用合成 envelope。没有浏览器、网络或 API 调用。原始源码、日志、控制配置、输入清单、失败均保留。Vitest 关于未来 configLoader 的原始提示保留，未伪装业务失败或移除。

owner 日志与回执已实际读回并逐项核 stdout SHA 和相关 source before/after。own-green01 的 24 PASS 绑定 a70aecb，而非最后 finally 小补丁 e24982ac；最终 e24982ac 有 lint02 PASS、full02 的 284 PASS/1 FAIL 以及上述两个独立 GREEN。full02 唯一失败是另一 owner 新增 useWorkbenchRecovery 初次占位导航 RED；本报告不将这次完整运行写成全通过，也不把它误列为 shared 的未关闭 finding。新 route-draft-input 原生测试源码仅静态读过，本轮未执行或回读其新原生结果。
