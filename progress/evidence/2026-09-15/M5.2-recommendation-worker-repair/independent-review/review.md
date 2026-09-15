# RecommendationWorker 只读预检独立审查

结论：本次有界源码与证据审查未发现未关闭阻断。只读预检不发布或缓存学科结果、不消费 dirty；真正更新完整重进原写事务。此结论不证明原 GitHub Reader 秒级超时的唯一原因，不代表完整阶段或 CI 验收。D 仅阅读源码、测试、日志及回执并计算哈希，没有运行产品测试、浏览器、数据库 profile 或网络。

有效规范为 PRODUCT_DESIGN.md 3.0.3，SHA a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8；依据为 §13.3、§20.2 和 §20.7 的持久刷新、当前权限和有界维护条款。

## 最终源码与事务边界

- application/recommendations.py SHA 734e19c3077a7e2d63fb3aff0e30401317944cf147c122e8bbe2361f0bd7c8c9。新增 20 行；原 writer/catch 后缀逐字节相等，后缀 SHA f70daf4e539793edba6aa00cfaa1d6f26a78a8b0cb9b59e8d62c28fcdf60c1fa。
- tests/integration/test_recommendation_worker_readiness.py SHA 709dc3e093db81026c4d2ab14661ed863c5cf05f635360fabf8f09ec020b5393，8 个函数展开 10 例。最终测试全文在 focused-05、same-test-red-06、same-test-green-07 与当前文件一致。
- recommendations.py:233–249 的 _no_work 使用独立 BEGIN；先当前 Policy、完整 checked，后检查 retry。无 state、无 snapshot、dirty 或已有失败均进入真实工作路径；只有受检未到重试时点，或完整依据/规则参数/时钟仍匹配，才抑制本轮工作。不能把有效 retry 说成已核当前内容；该分支没有读取输入，也不返回内容。
- :255–286 完全退出读事务后，原 BEGIN IMMEDIATE 从 guard、完整历史及输入重新开始；只跨阶段传递 bool，没有复用旧 state/inputs/plan，没有读锁升级。实际发布仍持 writer 锁，fresh 比较及各 stop 回滚检查保留。
- :290–309 原错误行为保留。ASSESSMENT_ACTIVE 不登记刷新失败；受控预期异常仍在新的当前 Policy 保护事务中记录 warning/retry；不可信历史连恢复也拒绝覆盖；未纳入的 RuntimeError 原样传播。完整性错误没有被当作成功 current 空态。
- repository.inputs_changed:73–82 仍在来源原事务递增 generation 并清除 retry/failure；只读期间来源成功变更可使本轮返回 False 一次，但不清 dirty，下一轮必须重新消费。真正工作额外读取一次历史分类是本次有意保留的成本，不声称所有维护工作无写锁或没有计算开销。
- Content/Reader 及 Database 默认事务未改。它们既有的公开读取权限/发布排他行为不因本修复放宽。

## 实际证据回读

以下执行全部属于 B，本审查仅回读；详细命令、exit、原日志 SHA、786 项输入聚合和归档源码见 evidence-readback.json。

| 记录 | 实际结果与可支持的结论 |
|---|---|
| red-01 | driver 在 pytest 前因系统 Python datetime.UTC 不可用失败；没有产品运行。 |
| red-02 | 3FAIL，15.46s；observer 误把 connect 的 context manager 当连接，未到 contender BEGIN 观察，属于 harness 错误。 |
| red-03 | 原生产 3FAIL，3.50s；实际 basis_current=True 被 Event 保持时，真实 lesson/outline GET 和发布的 BEGIN 无法完成。 |
| green-04 | 2PASS、1FAIL，0.41s；两 GET 通过，发布与 dirty/下一轮刷新已完成；唯一失败为末尾错误期望 catalog 只含 r2，实际保留 r1/r2。原件保留。 |
| focused-05 | 39PASS、2 个既有依赖告警，17.75s；10 新例加 29 未改 Recommendation 集成例。 |
| same-test-red-06 → green-07 | 完全相同最终测试，原生产 3FAIL/3.49s → 修复 3PASS/0.39s；两轮各明确 7 deselected。归档及恢复 SHA 验证原生产仅用于该反事实窗口，随后恢复最终源码。 |
| ruff-08 / mypy-09 | 两 owned 文件 Ruff PASS；生产文件 mypy PASS（1 source file）。通用 driver 的 scope 字符串不能把这两项说成业务测试。 |

新反例的实际观察边界：

- :64、:97 使用真实 WAL 事务和 owner 服务，在 actual BEGIN trace 后等待完成；一秒是持有快照时的有界锁独立性观察，不是 CI 性能 SLA。finally 释放 gate，返回值随后真实回读；失败完成事件不会替代结果核验。
- :97 保留真实来源发布 r2 后 generation>completed、旧 snapshot，下一 tick 新 snapshot 与实际完整输入一致，并保留精确 r1/r2 历史引用。
- :154 在读事务彻底退出后实际发布 r3，最终 publication basis 等于当前 r1/r2/r3；实际发布处另一连接 BEGIN IMMEDIATE 被拒，证明 writer 边界仍在。
- :184 另一实际 Worker 在两阶段间先完成，外层再核后 False，全部持久行与 peer 完成时一致，没有第二发布。
- :201 当前独立测试分别在读前、两阶段之间真实启动，均拒绝且不写失败或 snapshot。独立测试恰在已判 no-work 的读事务期间启动未单列新测试；该分支无结果交付和持久写入由源码验证，不冒称另有动态覆盖。
- :220 受控读取异常保旧 snapshot，真实持久 retry；未到期仍执行 checked 且不再调用输入，前后全库行一致；到期恢复，同依据保留原 snapshot。来源变更清 retry 的语句额外静态确认，没有把它另计一个新测试。
- :258 故障 fixture 同时破坏 sequence 及 retry/failure 关系，checked 先遇历史错误；它证明损坏状态不能跳过完整校验，不是一个字段的孤立反例。
- :285 未知异常传播且零写。旧 29 例还覆盖真实评分时钟到期、同依据决定保留、原 ACK/CAS、注入发布失败与停止回滚，未重复计数或重跑。

## ADR 与证据范围

ADR 0017（SHA c405b43032507c87162ffe2ac6efa484e657f697abb3cc6f42dacc2547f87c58）全文与最终 seam 相符；它关于客户端 Policy 序号和推荐 layout effect 的描述也与实际源码一致，两个前端文件分别仍为此前独立审过的 b2234493… 和 612e7883…。它明确不证明原 CI 根因或 CI 通过。

B 的 786 项绑定算法为：git ls-files 加两 owned 路径，排除 progress 和非普通文件，按 path 排序，列表每项含 path/sha256/bytes，再对 JSON(sort_keys=True,separators=(',',':')) 的 UTF-8 求 SHA256。各完整运行 before/after 及归档、日志均已重算相符；最终聚合 ff3eb64d90deae0b93ecf378eb40ad1254893802b3951fae3ae5227836520915 与当前这 786 项相同。root 当时新增、未跟踪的 ADR 不在该运行清单内；本审查另外绑定其当前字节，绝不追认 ADR 在 B 运行前被观察。D 本次 12 项静态输入清单及原始证据定位独立记录，不称全仓测试或全依赖执行证明。

所有原失败保留。当前剩余工作属于 root 的组合门禁及精确提交 CI；本审查没有把局部锁机制修复转述成原历史 CI 唯一原因。
