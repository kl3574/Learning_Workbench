# M6.1 验收补证差异（9d4aa2e）

唯一依据为 PRODUCT_DESIGN 3.0.7（SHA `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`），M6.1 任务行、§20.8/20.9 及附录 A/D。固定实现 `9d4aa2e75c0583b4752e1a2669534ef621e6c7f9`。原 `OLD/crosswalk.md` 保持原字节；本件只读更新原表明确列出的缺口，不重跑测试。路径别名、原始/公开文件 SHA、源码与 Git 逐项比较、读取时间见 `pins.json`。

§20.9 所列三根本地纵向验收现有相应实际证据；这不等于整个 M6.1 或内容质量通过。以下每行均由真实 SQLite/owner/受控 loopback Provider 和相应用例支撑，没有以严格 DTO 代替纵向链。

| 原缺口 / 规范要求 | 新证据与实际断言 | 结论及范围 |
|---|---|---|
| assessment 缺完整作者 UI；§20.9 三根各贯通 prepare→同 Job 许可→完整响应→计划/组持久化 | `NATIVE/05-native-three-roots-cancel-gate` 3 PASS；三个 `group-*-actual.json`。`authoring-groups.spec.ts:20,350` 实际选择 assessment、Concept-only、independent + open_book、600 秒；准备无外发，许可绑定同一 Job，完成回读原响应、计划与候选。 | 本地三根已覆盖；lesson 含 definition + worked_example；两题目根各一个 numeric 题。合成内容未审，模式字段选择不等于运行活动测验。 |
| 每根 UI 权限锁下 safe cancel 缺失 | 同三根测试调用 `cancelSecondWithoutConsent:126`：先显示完成组及显式私解，再准备第二个未许可 Job；实际 author→learner 后 UI 学科清空，原详情/草稿/私解 GET 403。UI cancel 已由服务端提交，丢浏览器 ACK，再以原 key/body 重放；原 ACK 等于当前 cancelled 回读，首 Job 仍 completed、Provider 总计仍 1。 | 三根均已覆盖这个明确控制边界。取消的是第二个 awaiting_approval Job，不把终态 completed Job 当可取消；不是全部执行时点的取消矩阵。 |
| 每根完成后同库实际进程重启回读缺失 | `restartAndReadOriginal:191` 关闭浏览器、停止并重新启动 API；actual JSON 核同 SQLite device/inode、两个 API PID、原 Job/draft/plan/member/private DTO 完全相等；作者经真实 UI 显式重新读取。targets 首次 published_once、重启 reused_exact，原 refs 相同；Provider 观察器分段为重启前 1、后 0。 | 三根已覆盖真实 API/browser restart 与持久读取；未重新种 targets/配置 Provider，后段 0 不冒充累计计数。 |
| Provider 已完整消费、候选尚未终态时成功恢复缺失 | `BACKEND/13-final-all` 的 `test_authoring_group_recovery.py:50` 三根参数化：实际 CheckedDispatch 收完终态，尚无 plan/candidate；显式过期原 lease 后 fresh Database/context/source/CheckedDispatch/worker 采用原受检结果，唯一 plan/candidate/dispatch；另一次 fresh owner 回读原 ACK 与全内容，SQLite 不变，loopback 没有第二请求。 | 已覆盖成功恢复；租约故障注入不是 OS crash。该证据与上一行真实进程重启、既有取消恢复、numeric permit 不重跑各自独立。 |
| 四种非 numeric 题型只有纯校验，缺实际生成链 | `test_authoring_group_provider.py:159` 一个真实 checked practice_set 包含 single_choice、text_blank、numeric、expression、calculation，读取完整合法允许答案集合、私解 member SHA。`:256` 三个受检拒绝案例核错 grader、缺选项、非有限 numeric；保留合法 plan/原输出，零 candidate。 | 五题型结构评分兼容缺口关闭；表达式/计算题仍待相应人工审校，不声称实际学习者评分、答案数学唯一性或语义正确。无需 root×5 浏览器矩阵。 |
| 私解隔离缺实际索引全部存储检查 | 同 `:159` 用 PUBLIC/PRIVATE 哨兵核公开题面与安全控制；真实 index rebuild ready 后公开查询命中、私解零命中。`:233` 起读取全部 scope/generation/chunk/FTS 物理记录及 owner manifest，恰好一个真实公开 block，无私解哨兵/草稿成员；首次发布 3 个真实 targets 后，objects/revisions/block_bodies/solutions/drafts/reviews 在生成与索引后逐项不变。 | 已覆盖该隔离数据库的整个实际索引存储，不仅一个限定 scope 的负向搜索；生成未进入 Content、Import 或学习投放。 |
| 题目私有 NumericPlan 缺 native 独立拒绝/批准回执 | assessment native 显式再读准确私解，member/candidate/plan 完全绑定；第一次 decline 无 Job，第二次 approve 创建独立 numeric Job，原回执留存。lesson worked_example 同路径有回执。两个 actual result 都是 BLOCKED/environment_unavailable、exit 1。 | 独立决策的浏览器缺口关闭；真正隔离数值运行仍 BLOCKED，没有计算 PASS。practice 的相同 HTTP 链是既有证据，不追加 native 数值已执行的说法。 |

新后端最终 **12 PASS = 7 个新增 + 5 个既有 Provider 案例**，12.36 秒；939 声明输入前后相同，最终 Ruff 与两文件定向 mypy PASS。所有原始失败（字段名、预期错误阶段、model 比较/序列化、mypy 调用及类型问题）都由 `BACKEND/summary.json` 与 `BACKEND-PUBLIC/manifest.json` 指向保留，不改写成产品 RED。三根 native 定向 **3 PASS / 37.7 秒**，459 声明输入前后相同；运行时 HEAD 仍为 62d3，所用最终源码随后进入 9d4，本次逐项核所列源码与 9d4、459 输入与恢复后源码一致。native 原同步断言失败也保留。定向案例不能与全量复跑相加。

当前工程门禁另记：`GATES/01` 至 `08` 各命令 exit 0，939 输入前后相同；Python **2169 PASS / 1 SKIP / 2 warnings**，SKIP 是真实 sealed runtime 的环境阻塞；web **441 PASS / 74 files**。`GATES/09-native` 于 2026-09-22 04:00:57 UTC 完成 **99 PASS / 9.1 分钟**，exit 0，**原始 unchanged=false**：4 张已跟踪 PNG 与 `docs/ui/m1-native-zoom-metrics.json` 改变。原始 before/after 与新产物保留；父任务随后按精确 SHA 恢复这 5 项，`09-native/restoration.json` 时间 04:04:50 UTC，恢复后 939 项匹配原输入/Git。本次只读重核恢复清单的全部 939 当前 SHA，并核 5 项保存的原/实际/恢复 SHA；不将恢复写成原生运行无变化。62d3 的旧 Python 1 FAIL 等历史仍保留。

仍须独立记录的状态：

- **BLOCKED**：真正受限进程中的算术运行，当前 lesson/assessment 实际环境回执均非成功；工程/native 测试通过表示正确显示真实阻塞。
- **NOT_RUN**：生产 InputProof/费用授权的托管 DeepSeek 调用；`main.py` 默认空 `ProofRegistry()`，已有模型响应来自明确的 test-only loopback。不能据本地证据开放生产费用链。
- **NOT_RUN**：数学、允许答案语义/唯一性、来源可信度、教学与目标是否真正达成、独立审校。结构或数值状态均不提升 needs_review；结果仍未审草稿。
- native 权限锁实际覆盖角色降级；活动 independent 的保护另有真实 HTTP 证据，未宣称本组三根各执行所有 active open_book/independent 浏览器组合。既有端口检查继承原策略；本次未发现 §20.9 规定的额外生成根或必须补齐的 block×题型无限组合。自动生成新 Concept、M6.2 发布审校、M6.3 不在当前合同。

本对照表关闭的是原表列出的本地纵向证据缺口；真实模型、真正隔离数值和内容审校保持上述独立状态。`NATIVE-PUBLIC` 与 `BACKEND-PUBLIC` 仅为已固定公开候选证据，不代表这次审计执行了发布。
