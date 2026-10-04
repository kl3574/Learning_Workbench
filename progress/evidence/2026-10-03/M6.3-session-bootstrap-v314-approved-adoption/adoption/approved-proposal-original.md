# M6.3：仅本地控制的 session bootstrap 提案

状态：待审阅、未采纳。基于 `ad49490e78c21174349595da8090c6c2b445bce9` 与唯一规范 PRODUCT_DESIGN v3.0.13（SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`）。本文件不是新规范，不改变当前运行能力；未执行 CLI、thread、turn、模型、系统探针或远端操作。

## 问题与范围

附录 A 已规定 POST `/codex/sessions` 必须携带 `consent_id`，以及精确 GET session。现有 Provider consent 必须来自实际 job/provider 的冻结外发输入；它尚不批准 codex，不能把另一个 Authoring/Tutor 的许可拿来创建 Codex session。session 的公开状态及 bootstrap 结果未知时的读回也未闭合。

本提案仅补齐：本地控制准备 → 阅读冻结范围 → 单次明确决定 → 消费对应许可创建受控 thread 映射 → 当前元数据读回。新增三个准备端点，补充原有两个 session 端点；不修改 Provider consent 合同，不开放 turn、登录、工具、学科文件访问、网络、通用审批或产物回导。`allowed_actions` 本切片只接受 `[]`，包括 `read` 在内的任何非空项均拒绝。建立 Broker 自有控制记录不等于获准读取教材或执行文件操作；不扩大已有隔离目录和固定控制 profile 的文件访问范围。

协议依据是此前由固定 Codex CLI 0.160.0 离线生成的 schema，而非本提案运行的结果：`ThreadStartParams` 没有 turn 的 `input`，`TurnStartParams` 的 `input/threadId` 必填，两个方法独立。schema 的 nullable、默认值和空 `turns` 不证明无联网。零外发由受检外层隔离强制；首次交付必须另证固定上游确实能在该边界内完成建 thread。若不能证实，保持不支持，不降低隔离、不调用模型来“验证”，不返回虚假成功。

## 严格 HTTP 合同

以下对象全部闭合；除显式 `|null` 外不可为空，所列字段均 required。沿用 Id、Revision、Sha256、UTC、ApprovalDecision 和安全 ErrorEnvelope；整数拒 bool，字符串合法 Unicode。所有 GET 无 body、拒未知/重复 query、no-store、零数据库写、零 CLI 启动。`EmptyActions` 是长度恰为 0 的数组。

```text
EmptyActions = []
CodexBootstrapPreparationWrite = {
  sandbox_root_id: Id, allowed_actions: EmptyActions
}
CodexBootstrapScope = {
  version: codex-local-session-bootstrap-v1,
  sandbox_root_id: Id, sandbox_label: nonblank safe string,
  allowed_actions: EmptyActions,
  adapter_version: nonblank safe string,
  bootstrap_profile_sha256: Sha256
}
CodexBootstrapPreparationStatus = pending | approved | declined | consumed
CodexBootstrapValidity = current | expired | changed | unavailable | closed
CodexBootstrapPreparationView = {
  id: Id, revision: Revision,
  actor_session_id: Id,
  status: CodexBootstrapPreparationStatus,
  scope: CodexBootstrapScope, operation_sha256: Sha256,
  created_at: UTC, expires_at: UTC,
  consent_id: Id|null, session_id: Id|null,
  validity: CodexBootstrapValidity
}
CodexBootstrapDecisionAck = {
  preparation_id: Id, revision: 2,
  actor_session_id: Id,
  decision: approve_once | decline,
  operation_sha256: Sha256,
  consent_id: Id|null,
  decided_at: UTC
}
CodexSessionCreateWrite = {
  sandbox_root_id: Id, consent_id: Id,
  allowed_actions: EmptyActions
}
CodexBootstrapSessionStatus = initializing | ready | failed | unknown
CodexSessionCreateAck = {
  id: Id, revision: 2, status: ready,
  capabilities: {approvals:false, interrupt:false, artifacts:false},
  adapter_version: nonblank safe string
}
CodexSessionView = {
  id: Id, revision: Revision, status: CodexBootstrapSessionStatus,
  active_turn_id: null,
  adapter_version: nonblank safe string,
  capabilities: {approvals:false, interrupt:false, artifacts:false}
}
```

| 操作 | 请求/返回 | 明确边界 |
|---|---|---|
| **新增** POST `/codex/session-preparations` | CodexBootstrapPreparationWrite → 201 CodexBootstrapPreparationView | 冻结实际本地控制计划，初始 r1/pending；不启动 CLI，不创建 thread/Job，不授予许可 |
| **新增** GET `/codex/session-preparations/{id}` | CodexBootstrapPreparationView | 回读冻结操作、当前资格及已绑定 session ID；只读 |
| **新增** POST `/codex/session-preparations/{id}/decision` | 原 ApprovalDecision → 200 CodexBootstrapDecisionAck | 只允许一次 approve_once 或 decline，expected_revision 必须对应 r1，操作 SHA 完全一致 |
| **补充** POST `/codex/sessions` | 保留原三个请求字段 → 201 CodexSessionCreateAck | 仅实际受检 thread 映射成功且本地持久化后返回 201；失败/未知返回安全错误，真实状态另 GET |
| **补充** GET `/codex/sessions/{id}` | 保留原返回字段 → CodexSessionView | 当前本地受检事实；不启动/恢复 CLI，不补建 thread，不返回外部 thread ID、路径或原始响应 |

这三个新增路径才是本切片控制准备/决定入口，不占用 `/approvals/{id}/decision`，不让其既有 RunSnapshot 响应承担另一类业务。

## 权限、修订与原命令

本提案选择最窄创作入口：准备、决定、新建 session 均要求当前 author、本工作区有效会话、同源 Origin/CSRF，且没有 active independent/open_book。读取这两个不含学科正文的控制 View 允许本工作区当前有效 learner/author，会话失效仍拒绝；不因测试策略卡死安全元数据读回。上述写入准入是本提案明确的切片选择，不反向改变现 capabilities GET 的权限。

每项写操作要求单个原 Idempotency-Key，完整绑定 workspace、原 actor_session_id、route、key、全部 body 与 CAS；请求不得自报 actor。当前身份/权限与自有完整历史先于原 ACK 回放。同 key 同命令返回原不可变 ACK/已记录终态安全错误，不重新批准或启动；同 key 异命令 409。新命令的 expected_revision 不符为 412；operation_sha256、操作哈希或绑定不符为 409，不能把它们合称版本过期。新 actor 不能接管旧 actor 的批准或命令。准备与批准的原 ACK 不是当前资格，应另 GET；刷新/失权不得自动生成新 key 或重发新命令。

准备 r1/pending；唯一决定使其 r2/approved 或 r2/declined。approve_once 由 CodexBroker owner 同事务产生一个真实本地控制 `consent_id` 并绑定该准备，decline 的 consent_id 为 null。只有 approved 可被消费；消费使准备 r3/consumed，并绑定恰一实际 session ID。不同 key 重复决定或重复消费同一许可均 409；原相同命令按原身份回放。

`actor_session_id` 在准备、决定 ACK、内部许可、session 与命令账本中始终是原创建/批准 actor，不能用当前读者回填。仅该原 actor 的当前有效 author 会话能批准和消费。`consent_id` 不是访问令牌；仅有字符串不授予执行。Provider/Tutor/Authoring consent、未知 ID、跨工作区或与原准备不符的 ID 不可被消费。

准备有效期为创建后 10 分钟，固定 created_at/expires_at 进入原操作哈希。GET 的 validity 是只读推导，不改 status、revision、时间、许可或命令行：declined/consumed → closed；其余已到期 → expired；固定根/profile/config 等已确认改变 → changed；当前已实现的受限 profile/环境不可用于准入或无法核验 → unavailable；否则 current。准备及读取不启动 CLI 来消除环境未知。记录本身缺失/哈希或关联损坏是安全错误，不以 unavailable/空列表掩盖。只有 pending/current 可 approve_once，只有 approved/current 可消费；有效期内 pending 可 decline，即使当前环境不可用，也不执行操作。过期后不得再作新决定。原决定/消费 ACK 不因后来到期或 profile 更新改写；原记录自身仍须校验。

## 完整冻结与真正的一次消费

`operation_sha256` 对 owner 私有、版本化的完整规范记录计算，至少覆盖 workspace、准备 ID、原 actor、创建/到期时间、公开 scope，以及以下实际控制事实：

- 完整初始化及 bootstrap 协议帧的确切请求字节和顺序，包括固定请求 ID、实际 `thread/start` 参数；不是只散列摘要、方法名或客户端 body。仅固定控制方法可出现，不含 `turn/start`、登录、任意 RPC、自动工具递归或用户 prompt。不得在批准后追加 instructions/config/模型或环境默认参数。
- 精确固定可执行字节 SHA/size、协议 schema/profile 版本、固定非秘密配置字节、服务端解析的稳定 Broker 根及权限绑定、受检环境变量集合、隔离启动器/fence 与必要部署闭包 SHA。秘密/认证字节及其可公开比对摘要不得进入冻结记录或浏览器；它们不构成此项控制许可来源。
- 实际资源规则和终止/回收方式。首 profile 沿当前控制限制：总 wall 8 秒、CPU 5 秒、地址空间 2 GiB、文件大小 16 MiB、描述符 128、core 0、stdout/stderr 合计 64 KiB。若这些事实或完整运行闭包变化，需要新版本/新准备/明确批准，不能借旧 SHA 换运行条件。

私有冻结中的物理路径、原请求帧和原控制响应不经 View 返回。公开 scope 只展示安全逻辑根/固定适配版本、profile SHA 和“仅本地控制建会话”的范围；操作 SHA 不能替代服务端回读完整冻结事实。`bootstrap_profile_sha256` 覆盖完整受限部署描述，不能自行填写一个 hash 即称环境已验收。

POST session 事务内重核原 actor、当前 Policy、准备 r2/approved/current、全部冻结事实及三字段与原准备一致；原子保存单次消费、r1/initializing session、原命令与唯一开始许可。随后在短事务之外由受控执行 owner 执行这一已登记实例，不在 DB 写锁中等 CLI。并发同 key 只观察同一实例；不同 key 不能拿已消费许可另起实例。开始许可一旦持久化便保守消费，失联/重启不能恢复为未使用。

固定控制 profile 必须明确服务端 cwd、read-only/never 配置、关闭 hooks/plugins/更新/遥测与任意配置透传，且在外层隔离中强制零可寻址网络/IPC、零宿主范围扩展。`never` 不是批准工具，`read-only` 不是学科 read 权限；本切片没有 turn 或工具入口。遇不支持、隔离不可核验、意外请求/输出或超预算，安全停止并记录事实，不降低 profile。已有 capabilities 的三产品 flags 与本切片 session flags 始终 false。

## 201、未知结果与当前读回

session r1/initializing 表示单次控制开始许可已登记，并不表示存在外部 thread。只有从该唯一实际控制实例取得完整、匹配、受检的成功响应，验证 root/profile/返回身份并持久保存外部 thread 映射及回执后，才变为 r2/ready 并产生原 201 ACK。ready 仅表示 bootstrap 映射已核验成功，不表示模型调用、真实账号授权、当前进程仍运行或整个 Broker 已完成；账号授权状态仍由已有能力读取独立观察。

确定在 thread/start 尚未发送前已终止且未建立映射，可记 r2/failed；一旦发送可能发生、成功响应丢失/无法验证、进程中断或无法证明结果，记 r2/unknown，并保存安全 `CODEX_SESSION_OUTCOME_UNKNOWN` 错误，绝不补造 thread ID、ready 或 201。外部过程与本地事务不宣称原子。任一失败后的原同 key 回放不能再启 CLI；未知结果尤其禁止第二次 thread/start。

开始后当前会话失权或 Policy 改变，不回滚已经发生的外部事实或单次消费，也不能把已开始改成“未执行”。执行 owner 仍按受检结果持久保存 ready/failed/unknown、原 actor、映射或安全错误与原命令历史；保存事实不代表可以向已失权调用者交付成功。返回前再核当前身份及该写操作权限，不满足时不返回 201 或正文；后续原命令回放仍核当前写权限，当前 GET 仍核有效会话、工作区归属和上述无正文控制读取权限。未知结果不因权限恢复而再次启 CLI。

客户端已持有准备 ID：读取该准备的 session_id，再 GET session 即可定位初始化中或未知的原实例，无需新增任意“按 key 搜索”入口，也不把 ID 塞进原始错误文本。GET 与原 ACK 分离；准备/决定原 ACK 保留当时修订，GET 显示真实 r3 消费和当前 session。consumed/closed 准备仍保留非 null 的 session_id，允许受权读者查看旧 unknown；这既不接管原 actor，也不自动启动。若另建准备，只能作为满足当前写权限的 actor 的新操作，不能继承旧许可或更改旧命令归属。`active_turn_id` 始终 null。

重启恢复只处理本机已登记实例及实际执行 owner 的结束事实；有仍活动的 owner 时不另领/重复启动。owner 已结束而未持久取得成功响应的 initializing 收敛为 unknown，不从时间经过推定未开始；GET 本身不负责该写入。ready 的读回是已保存映射事实，不偷偷调用 thread/resume/read 来改变状态；原映射/回执损坏安全拒绝。失败或未知若需重新尝试，须另建准备、显示旧未知事实、再明确批准；不自动替用户创建新准备或宣称旧外部副作用已清除。

## 最低验收与不交付的范围

规范采纳只批准业务合同，不等于已验证固定上游运行。实现须有独立来源绑定的 strict DTO/生成物、真实 HTTP 与 UI 验收，并区分：

1. 准备/GET/批准/拒绝零 CLI、零模型、零网络；原 actor、schema、跨工作区、Origin/CSRF、过期及损坏拒绝；GET query_only/全表不变；r1/r2/r3 与派生 validity 不写回。
2. 同 key 完整命令回放、同 key 异 body 409、expected_revision 不符 412、operation/hash/binding 不符 409、不同 key 重复消费 409；并发、开始后角色/Policy 变化、事务故障、丢 ACK、重启均不能产生第二个实际 start。开始后失权仍保存真实结果但不向当前失权者交付 201；consumed/closed GET 保留原 session_id，旧 unknown 可受权查看且不自动启动。拒绝决定零执行。
3. 测试专用受控协议的 ready/failed/unknown、坏/重复/过量响应、超时/回收分别验证；仅 fake thread ID 或协议测试不能证明真实上游成功。
4. 在固定受限部署中完成获准的真实零模型控制建 thread，核实际响应、唯一 start、稳定根、原 ACK 与同 DB 重启后当前映射读回；未运行则真实 session 为 NOT_RUN，受限环境无法成功则 BLOCKED，不改三 flags 或隔离来使测试变绿。若现有 schema/受限配置和实际验收仍不能证明该控制路径遵守零外发，保持明确不可用门禁，不注册虚假可用成功能力。

不包含 Provider codex 外发/InputProof、多轮对话、GenericApprovalView、Codex 产物清单、登录 UI、任务导出、普通文件执行/写入、回导或发布。它们仍按 v3.0.13 的对应目标另行补齐，不由本提案关闭 AC-21 或整个 M6.3。
