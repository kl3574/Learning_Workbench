原 push [37774154467](https://github.com/kl3574/Learning_Workbench/actions/runs/37774154467) 已终态 SUCCESS，browser 133 PASS；原 PR [37774163003](https://github.com/kl3574/Learning_Workbench/actions/runs/37774163003) 已终态 FAILURE，browser 132 PASS、1 FAIL。两次 attempt 均为 1，实际 checkout 分别为 5da115f 和 f56ef15，完整 Git tree 同为 15ddc060098288f284df2cbdddfb4bc73647dc11。push 的成功不能覆盖 PR 的失败，也不能证明结果确定。

两事件的其余五个 job 均 SUCCESS：integration 各 2540 PASS、2 ENV skip、2 warnings；backend 各 1114 PASS、3 warnings；spec-contracts 各 962 PASS、2 warnings；frontend 各 1424 PASS、167 test files；security-publication SUCCESS，未推断其测试数量。这些是逐事件计数，不合并成唯一用例数。两项 numeric skip 仍为 BLOCKED_ENVIRONMENT，保留原 sealed evaluator/calculator FAIL 与无 fallback 边界，不记作 PASS。

PR 的唯一 browser FAIL 位于 tests/e2e/review.spec.ts:203:138 的 r1 教材按钮点击，原测试总预算 30000 ms、retry 0、make exit 2。按钮已 resolved、visible/enabled/stable、完成 scrolling；点击尚未返回，reader-route 与后续断言未到达。原 body observer 记录 29 phases、301 HTTP records、零 dropped：click marker 为 23898.640834 ms，finally 为 24117.682727 ms，窗口 219.041893 ms。此后有此前 attempt GET 的完成记录及 workbench PUT，零新的教材 course/lesson/block/body 请求。实际框架 deadline、fixture setup 时长和点击剩余预算均 NOT_OBSERVED；不能用 30000 减 body elapsed 推认剩余时间。TargetClosed 文字不能单独证明独立浏览器崩溃，根因仍 UNKNOWN。

原上传 artifact 的九成员清单未包含 setup-helper timing 或 trace，仅能记作该 artifact 内 NOT_CAPTURED，不能推断 runner 上不存在文件。9aa4a53 只在 failure artifact allowlist 添加已存在的 review-history-setup-helper-timing.json 路径，不改变原测试源、预算、重试或断言；它是补充附件证据的改动，NOT_TESTED、NOT_A_FIX。

fixed06b 的历史 Python/native gates 和原 6e 事件保持独立，不能替代本轮 fixed5da 完整树的 CI 事实。生产 registry 仍 EMPTY、executor None、无生产准入，真实模型执行为 0。此摘要只读核合两份各八成员摘要；原始日志、maps、PNG 未复制或重新审阅，声明的 raw locator/hash 取自封存摘要。未运行测试、Cargo、网络、dispatch，未改 canonical、旧证据或源码。

四件摘要按 scripts/check_publication.py 的纯 inspect(path,data) 实际扫描为 0，逻辑目的地位于允许的 progress/evidence 根；未包含个人目录前缀、凭据、原始请求或 artifact payload。JSON 保留声明的 CI/job 来源定位与 hash，manifest 绑定两件 payload，seal 绑定 manifest。此结果只说明这四件有限摘要通过发布扫描，可供 root 后续独立审查发布；本任务未发布到 GitHub。原 observer 的工具失败继续保留，未改变 CI 终态。
