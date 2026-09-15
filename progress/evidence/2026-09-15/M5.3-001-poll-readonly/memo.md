# 0010699 Tutor completed 尾窗：只读诊断

结论：当前安装且 lock 固定的 Playwright 1.63.0，`toBeVisible` 的真实路径允许“completed 文本已被独立观察到、稍后仍超时”这种结果。后段每次失败查询后等待500ms；timeout可在这段等待中中止，没有到截止时间再强制查询一次。因此当前数据与尾窗漏采相容，并非逻辑矛盾。原 CI 没有每次 selector 查询/可见性/内部 deadline 时间，尚不能把这一机制认定为本次唯一原因，不能据此扩大5s或宣告产品修复。

范围：只读实际00106992e33aecfa4d2cc0d79b474cb5aa463fdb源、已安装node_modules和原附件。使用 diagnosing-bugs 的分层/可证伪纪律；本次父任务限定只读，因此没有执行它的复现/实验/修复阶段，所有预测未测。无测试、服务、浏览器、CI rerun、网络或模型调用，无仓库改动。没有把旧Reader原因套用本次。

## 已观察事实

原附件 `tutor-completion-diagnostic.json` SHA `567faa4dcf0a12dc56602701795f8c784f49cbde7dd0a03f9b2d6279154ecab7`。全部数字来自同一Node相对时钟，omitted_events=0：

| 观测 | 自 observer 起(ms) | 自 assertion_start 起(ms) |
|---|---:|---:|
| assertion_start 标记 | 8412.992283 | 0 |
| POST consents开始 | 8437.249776 | 24.257493 |
| POST consents 201 | 8601.526549 | 188.534266 |
| DOM queued 收到 | 8888.467515 | 475.475232 |
| 当前SSE请求开始(id79,after_seq3) | 8880.026639 | 467.034356 |
| 同SSE收到HTTP200 | 12314.480156 | 3901.487873 |
| Run GET开始(id83) | 13003.885971 | 4590.893688 |
| Run GET收到200 | 13185.419438 | 4772.427155 |
| last_dom_delivered=completed | 13192.299068 | 4779.306785 |
| 原expect失败后同步freeze | 13415.224758 | 5002.232475 |

最后completed消息到失败freeze间为222.925690ms。实际DOM变更早于或等于消息到达，未记录它在浏览器内的确切时刻。assertion_start是调用前标记，不是Playwright ProgressController内部timeout起点，不能把8412.992+5000当已测实际deadline。后读Run为completed/seq6/job_revision6，终态receipt存在，真实input1322/output137；运行计数1 received/1 validated/0 invalid。这些后读不能倒推前面的SSE帧交付或早先数据库状态。

SSE只有请求/HTTP状态/终止元数据，未采帧；id79的net::ERR_ABORTED是已观察到的请求终止，不证明服务端没有完成或后端错误。没有测量vendor完成、worker队列、数据库事务或发送到浏览器每帧的时点。

## 真实实现路径与范围差异

- `tests/e2e/tutor.spec.ts:148,170,195–196`：确切region `真实问答线程与任务` 内确切heading `真实任务状态：completed`，`toBeVisible()`无options；整体90s不等于这个expect预算。当前配置无expect覆盖，原错误明确5000ms。
- `playwright/lib/matchers/expect.js:12788–12795`：toBeVisible→locator._expect('to.be.visible')；`:12094–12139`取options.timeout或matcher timeout，失败携带ariaSnapshot。
- `playwright-core/lib/coreBundle.js:58611` locator传完整selector，`:60637` frame._expect通过channel传timeout。
- 同文件`:24269–24314`：prechecks、一次单次检查后走retryWithProgressAndBackoff。`:23989–24020`实际backoff为 `[20,50,100,100,500]`，前置立即检查，后续重复最后500；5000预算不会把500裁掉。每轮查询/prechecks/失败ARIA快照本身耗时另外累积，不是从起点严格每500ms采样。不要误引该版本其他expect.poll/toPass路径的100/250/500/1000。
- `:12315–12386` ProgressController设置内部deadline与timer；`:24005–24009`睡眠通过progress.race可被timeout打断；`:24298–24313`超时使用lastIntermediateResult并抛ExpectError，未强制末次selector查询。一次one-shot有独立noAbort路径，不能泛称所有expect时长精确等于墙钟5s；本次实际失败走重试超时。
- 理想零耗时示意（不是实测）：立即失败后等待20+50+100+100，再500，查询位置可约为0、20、70、170、270、770、…、4270、4770ms；4779ms才变为可匹配时，下一次约5270ms被5000ms timer截断。真实开销会移动这些位置，不能凭这个示意反造本次最后poll=4770ms。
- `tutorDiagnostic.ts:81–97`观察的是第一个aria-label region中指定h3的textContent正则；它不使用Playwright角色解析，不核匹配数量/可访问性/CSS几何/visibility。`TutorWorkflow.tsx:13,26`实际section/aria-label/h3在正常可见DOM结构上与locator一致，没有从静态代码看到名称写错；仍缺故障时祖先hidden/aria-hidden、重复节点或样式证据。
- 内嵌injected代码在`coreBundle.js:19837`的字符串常量，非执行解码后logical lines5367–5394为queryRole（默认排除ARIA hidden，并算accessible name），3180为isElementVisible，8077为to.be.visible→elementState。这比textContent观察更严格。
- `tutorDiagnostic.ts:88`的DOM answer_present仅看pre.textContent；`TutorEvidence.tsx:8`无答案时也渲染“尚未收到回答原文。”，因此这个DOM布尔不能证明已有模型文字。post safeRun.answer_present来自真实API字段，是另一证据。此限制不使h3 completed文本变成假值。

## error-context中的queued为何不证明回退

该附件SHA `685f5c6c11652c549130b9579ff9b6e905fa905ed3963123b23be33e5afff93c`显示 queued，并包含回答文字。但Playwright在未匹配时取body ARIA snapshot并存lastIntermediateResult（coreBundle:24358–24376），timeout错误返回最后已保存快照。expect.js:12139将它放matcher结果，worker/workerProcessEntry.js:831–832转为errorContext；playwright/lib/index.js:660–674及703–707在已有matcher快照时不以事后新快照替代。因此queued可只是最后一次失败检查所见的历史文本，不应拿它与Node稍后completed消息构造“页面又回queued”的断言。截图的采样时刻同样未在该JSON绑定，本审没有进行肉眼观察，也不借PNG推断时序。

## 三个可证伪预测（未执行，保持原5s）

1. **优先：500ms尾窗。** 在隔离副本对这一个expect的真实重试边界仅记录Node单clock的查询开始/完成/等待和最后结果，安排一个稳定可见completed于最后失败查询之后、截止前约200ms出现。如果这是尾窗，日志应显示最后一次完成的miss在变更前，下一次sleep遭timeout且无变更后完成的查询；同一私有受控用例只把DOM变更前移到该poll之前会PASS，原5s不动。若本次能证明有截止前完成的后续同selector查询且匹配visible，则纯尾窗解释被否定。不要用假poll函数替换实际Playwright机制来宣称原case复现。
2. **候选：text观察与role/visibility不是同一谓词。** 在真实节点变更点只采安全的frame/匹配数量、role/name匹配与可见性布尔、祖先hidden状态（不采正文/headers），并绑定同一次节点查询。如果h3文本completed而exact role locator仍0或不可见，观测-断言差异成立；若同一可见唯一h3和region始终符合且无祖先隐藏，排除这一分支。不得单纯把CSS locator替换原断言令测试变绿；那会变更验收谓词。
3. **候选：查询/precheck/协议回包在截止前后阻塞。** 记录该expect安全的Node dispatch/start/completion以及对应selector检查是否实际返回，不拼接浏览器不同clock。如果DOM已变但后一次查询或prechecks已启动、结果直到timeout仍未返回，则不是单纯sleep漏采。只在私有受控回放单独移动阻塞段到截止后/移除该阻塞，原5s保持，预计结果改变；若所有查询都及时且最后只是sleep，则排除该分支。额外观察会扰动调度，所以必须保留原/有观测分别结果，不能拿一个受控PASS归因CI。

下一最小实验应由root/C统一browser窗口执行，先锁定实际poll与DOM谓词时序，勿直接修改产品、延长timeout或将普通GET完成改成唯一成功条件。本memo只证明机制可行性和观测边界；原CI仍为实际FAIL。
