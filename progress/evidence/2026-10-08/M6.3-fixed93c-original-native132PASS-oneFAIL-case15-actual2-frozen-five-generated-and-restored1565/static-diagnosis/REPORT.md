# Fixed93c native case15 — finite read-only diagnosis

结论：原断言 **FAIL** (`completed` expected, `running` received, 原5000ms)；截止时刻的完整根因 **UNKNOWN**。只读源码和三个既有安全 artifact，未运行测试/应用/CLI/模型/API/SQL/host probes，未读取 live database、secret/control正文或请求/响应body，未修改 runtime、断言或规范。

固定工程源 `93c44303f9635067d2fae44a40986ba947e75e21`，从 canonical Git 的该 immutable commit 取出，不用当前可变化 HEAD 代替。13个有限源原件 SHA/尺寸在 SOURCE-BINDINGS.json；根 AGENTS 规定的 sole PRODUCT v3.0.15 未改变。以下行号均针对固定93c。

## 已证事实与时间边界

- `tests/e2e/authoring-groups.spec.ts:58–79` grant 写10秒模型总预算，收到201后使用默认5000ms `expect.poll` GET精确Job summary；没有延长窗口。case15位于297；失败后341–354的最终 `finally` 关闭runtime。错误现场两个 SHA 与 root 即时观察记录一致。
- prepare observer started UTC03:08:53.095Z；其成功阶段只覆盖相对2210.776–2274.559ms的 detail click（original click timeout10000ms）。最后网络metadata是 GET `/authoring/jobs/:id` request。该 observer 已提前冻结，没有捕获后续grant、原5秒poll、Provider parser/ledger/Job adoption。
- root安全晚快照：queued03:08:56.523456Z，running56.867308Z，failed03:09:01.854401Z；同一个 fixture later received1/validated1/invalid0。晚快照只有最后状态与时间，不是原deadline采样，不能反推那时在哪个阶段。
- 持久 Provider terminal later error `PROVIDER_TIMEOUT`，`provider_outcome=completed`。这不是本机成功terminal。`provider_compatible_chat.py:55–56` 在解析 `finish_reason=stop` 时已设completed；usage和 `[DONE]` 仍可在之后，后者才产生finished（18–23）。因此该字段只证明stop字段曾被解析，不证明整个SSE、usage/[DONE]、持久成功提交或草稿completed。

## 实际链与可证边界

1. group worker claim 将queued转running；`authoring_group_worker.py:210–250` 读取原consent后启动watch，每250ms通过 `asyncio.to_thread(_watch)` 复验/续租（94–103）并消费真实Provider stream，stream结束才 `_finish`。watch异常/stop只设abort。没有证据显示本次watch失败。
2. `provider_dispatch.py:193–199` 在真实dispatch开始固定单调钟预算deadline；`_guard:201–222` 用此deadline执行总时限检查。`_run:280–320` 复核、真实transport、解析、usage检查，再持久终态；消费者输出permission检查254是另一个DB边界。`authoring_group_worker.py:105–208` 只有持久checked complete结果、当前权限、完整计划/schema/binding合法才采用草稿和本机completed；单个远端stop不能跳过它们。
3. `_db:107–121` 若无显式deadline，则 **1秒仅限每次操作的预进入/SQLBUSY重试窗口**，耗尽也 `raise timed_out()`，对应文案“提供商请求超过总时限”（47–48）。已进入的transaction不会重试，await的to_thread操作也不会被这1秒强制中断。成功或异常commit不允许自动重启。
4. `_finish`持久terminal（320/338）、output delivery guard（254）没有传模型deadline，使用上述默认窗口；`_guard`和usage写（278/313）则传真实start.deadline。因此同一个PROVIDER_TIMEOUT码既可来自总预算，也可来自本地预进入重试耗尽。完整归因须知道实际触发phase，不能只凭terminal码认定fixture/网络响应慢。
5. `Database.connect:34–48` ordinary SQLite busy timeout10秒，transaction默认BEGIN IMMEDIATE；`_watch`使用默认写事务，而Provider transaction明确50ms（provider_dispatch96）。这些源足以说明读/复验/续租与终态可竞争同一SQLite writer，不能证明本次确有锁等待或哪个writer造成。
6. `provider_protocol_fixture.py:118–149` local_provider记录/验证body后（默认holdFalse、stall_afterNone）写整个固定SSE并drain；group factory90使用同API事件循环中的此服务，monitor只是周期计数没有阶段时钟。later验证数1既不证明在原deadline前完成，也不证明server drain/client parser/durable adoption当时完成。
7. testfinally调用 `AuthoringRuntime.close:114–117`，并行关闭browser/UI/API；`ownedStartup.stopOwned:42–61` 对自己创建的group SIGTERM，5秒后才SIGKILL。应用lifespan `main.py:193–201` 在async finally同步调用各worker.stop；group stop `authoring_group_worker.py:43–46` 同步join最多5秒，API事件循环因此可能在join期间停止推进fixture handle/monitor。这是可独立修的shutdown liveness风险，但关闭由失败后触发，不能据它解释原断言截止时的running，也不能把之后failed时间当根因证据。

## 最窄后续观测与独立工程修正边界

原样保留5000ms assertion；下一次若有单独授权的固定源观测切片，最少需要在同一原grant/poll阶段冻结安全metadata：grant ACK、poll start/deadline/last status、finally/close入场时间；固定dispatch预算数字/start单调钟；parser stop/usage/DONE阶段；DB phase名称/预进入busy重试/进入与结束时间；durable terminal与Job adoption开始/结束。各时钟注明自身epoch，不能猜测跨epoch匹配，不读或记body/headers/secret。截止采样必须在原assertion around wrapper内冻结，不靠之后GET/SQL追认。

静态可修的准确性问题是 `_db` 本地1秒等待耗尽与实际模型总deadline共享PROVIDER_TIMEOUT及“超过总时限”文案。最小修正方向是显式区分local record/DB-unavailable或OUTCOME_UNKNOWN与真实模型deadline；仍保守保持已消耗原dispatch、不自动重试，不延长assertion。这可改善诊断与错误语义，**尚不能声称会修复case15**。

shutdown同步join可独立移到受控thread await，使共享API/fixture loop在停止期间继续推进；这同样不是已证本次断言原因。此轮不实现、不运行验证、不以任何静态分支或候选修正填PASS。

## 状态

- Original native assertion: FAIL；原完整native在root观察时RUNNING，未干扰。
- Deadline root cause: UNKNOWN。
- Local DB waiting / thread scheduling / delayed fixture write / parser delivery / terminal/adoption阶段：本次缺截止时观测，不能排除或排序为已证原因。
- Fix/replay/model/API/SQL/probes by reviewer: NOT_RUN。
