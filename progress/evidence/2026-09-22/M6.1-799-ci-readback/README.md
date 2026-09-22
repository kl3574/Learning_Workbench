# PR 53 / 79908fb：CI 实际失败取证

两次 CI 均 completed/failure；各自 browser 为 **95 passed / 1 failed（96项）**。唯一失败是 `tests/e2e/tutor.spec.ts:148` 的 explicit same-Run consent 用例，`:195` 等待精确 heading `真实任务状态：completed`，原 `5000ms` 断言未找到元素。两个新 Authoring 用例均通过，不能将 Tutor 失败记成 Authoring 失败。

| Run | 事件 | API head | browser 实际 checkout | browser 终态时间 UTC |
|---|---|---|---|---|
| 35676551352 | push | 79908fb941898eb2b515719ce175c68dde3c71ef | 79908fb941898eb2b515719ce175c68dde3c71ef | 2026-09-22T01:55:42Z |
| 35676944952 | pull_request | 79908fb941898eb2b515719ce175c68dde3c71ef | a08bb873d8e85192e8a8938545ae96cdc2ed28b6 | 2026-09-22T02:00:43Z |

PR checkout 是合并提交，commit 身份不同；两者 Git tree 完全相同：`f8d97f6c22be33ff59edd00950c6f3be741646ba`。实际 checkout 有每个 job 的 `git log -1 --format=%H` 日志支持，tree/parents 另有原 Git 对象与 GitHub commit API 支持。相同源码树不表示 runner 调度或环境完全相同。

两次其他五个 jobs 均 success：backend 633 passed；contracts 543 passed；integration 764 passed、1 skipped；frontend 401 passed/72 files；security-publication success。Python 各项原日志中的两条 deprecation warnings 保留。integration 跳过的是 `test_authoring_numeric_runtime.py:46`：`BLOCKED_ENVIRONMENT`，真实 sealed runtime 未执行 calculator，原 FAIL 保留；不能记成数值运行 PASS。

## 冻结诊断支持的事实

| 同一 Node 观察时钟，ms | push | pull_request |
|---|---:|---:|
| completion_assertion_start | 8980.866466 | 8214.517846 |
| 最后已交付 DOM 记录 | 9531.997009 | 8779.247319 |
| assertion freeze | 13984.430898 | 13216.422164 |
| 最后 events 请求取得 HTTP 200 | 13187.961864 | 12161.526606 |

两次最后 DOM 都为 queued，grant_ack_present=true、consent_linked=true；最后 events 请求均 after_seq=3，在 freeze 前未观察到其 finished/failed。没有记录 SSE frame 内容或客户端 reducer 收取具体 seq 的事实；HTTP 200 不证明完成事件已送达，也不证明消费/渲染已经完成。

两次 **post-failure** 读回分别在约291.5ms、377.0ms内得到 Run completed / last_seq=6 / Provider complete；对应 test-only runtime received=1、validated=1、invalid=0。晚到读回不能证明 deadline 时后端已 completed，最后 DOM receipt 也不是 deadline 同步采样。此材料不足以锁定 SQLite、SSE、前端或历史根因。

`failure-artifacts` 保留原始截图、error-context 及诊断。PR截图显示 Failed to fetch/Policy核验页；`tutor.spec.ts:224` 在 finally 中关闭 runtime，故截图不得冒充 assertion freeze 瞬间或反推请求先后。另各有一份 `tutor-diagnostic-...` 诊断来自 observer 自身的预期失败测试，须与真正 Tutor 用例失败区分；它不是第二个失败用例。

## 有限下一步建议（本次未执行）

固定79908fb源码显示：Authoring 空闲循环每0.25s进入 `recover_unfinished`，再执行 claim；claim 默认 BEGIN IMMEDIATE。Numeric 空闲 claim 同样默认 BEGIN IMMEDIATE。Tutor本身也每0.25s recovery + claim。Provider recovery即使没有待恢复项，也先开启 busy_timeout=50ms 的写事务；普通claim事务默认 busy_timeout=10000ms。三个worker在同一应用lifespan同时启动。具体原文件SHA、行号和摘录见 `readback/source-excerpts.json`。

这些事实使“空闲worker写锁/恢复扫描参与等待”成为值得验证的候选解释，尚无本次CI的锁等待/持锁时长/claim开始时间证据，不能直接认定因果；WAL下读取与写入关系也不能简化为“所有读都被写锁阻断”。SSE入口在返回StreamingResponse前先完成service.read，之后还逐批/逐条重核权限与真实历史；最后events请求到HTTP200的延迟可能包含该链路或调度开销。

下一次经授权的本地受控诊断应保留原5秒断言，以同一请求/Job身份记录：BEGIN等待与事务持锁时长、worker recovery/claim阶段、Provider receipt及Tutor终态提交、SSE headers和具体seq发出/收到、前端状态提交。仅采时序/状态/哈希，不采cookie、凭据、正文或SSE内容。先取得基准，再做单变量隔离比较；没有这些证据，不建议直接改timeout、停掉安全检查或改恢复规则。本次未执行此建议。

## 包范围

所有远端命令为GET，逐命令明确设置HTTP_PROXY/HTTPS_PROXY及小写对应项为指定loopback代理，NO_PROXY/no_proxy为空；命令、时间、exit code、原响应SHA见 `readback/*commands.json`。PR browser运行期间首次日志请求404和initial in_progress事实保留，最终状态另存，未覆盖旧观测。

原ZIP仅在私有cache保存，不进入公开目录；公开文件均列入manifest，保留raw/public字节与SHA映射。日志只将固定CI HOME前缀替换为 `<CI_HOME>`；没有修改失败、skip、warnings或计数。没有session文件、数据库、浏览器storage state、HAR、trace、真实秘密或供应商请求；截图仅合成验收材料。没有执行CI rerun、源码修改、timeout修改、产品测试、remote写入或Provider调用。
