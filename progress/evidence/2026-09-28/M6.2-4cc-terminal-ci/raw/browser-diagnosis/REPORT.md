# 4cc push / PR Tutor browser 失败：分源只读比较

**根因仍为 UNKNOWN。** 新 4cc 两个 browser job 都是原 Tutor `completed` 标题 5000 ms 断言失败，各 106 PASS / 1 FAIL。本轮实际下载和检查了两个完整 job 日志、两个完整原 artifact ZIP 及 16 个解包成员，未重跑测试、未改源码或远端。a944 双 CI 失败及 4cc 三次本地合成 PASS 均保持各自原状态。

本轮发现一个明确的现场区别：**4cc 两个 browser 冻结前已收到 HTTP 200 并验证、应用了 answer_delta seq4；a944 两个现场的最后 SSE 请求冻结前尚无 response。** 不能继续把“末 SSE 未响应”套用于新现场，也不能把已有答案增量等同于已完成终态。

唯一产品/工程规范仍为 `<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md`，hash `2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`；正文 593–595 行要求保存回答/来源之后才能 completed，附录 1409 行要求严格事件与游标，R-29 / 942 行要求验证层次分开。本任务仅诊断真实验收失败，不修改这些要求。

## 远端身份、完整日志与附件

| 来源 | run / browser job | 日志真实 checkout | 原 browser 结果 |
| --- | --- | --- | --- |
| push | 36386011041 / 108811427645 | 4cc4fd5c24fe135186147dfb86d3f071b26f4fb7 | 106 PASS / 1 FAIL，19.3 m |
| PR | 36386016520 / 108811444631 | 538bf74da04fac1cdea69cc70e1416d54c5643cd | 106 PASS / 1 FAIL，18.5 m |

PR run.head_sha 是 4cc，实际执行的是上表 merge commit；没有把两者混用。独立 GitHub Git commit API 回读两 commit 的 tree 均为 `7014f0f0abfe5f692141415752403922624e10f9`，并与本机固定 4cc 的 Git tree 一致。15 个相关源文件已逐 Git blob 保存和校验，包括原 case/runtime/observer、Tutor HTTP/service/worker/client/hook、Provider dispatch、DB/repository、loopback fixture 与 CI workflow。

* push 完整日志 `push-browser-108811427645.log`，90656 bytes，SHA256 `672713464dc3f38ca776943dfd76dc032261a8fc6d9affb825d325a66f788dc5`。146 行为 checkout，783 行起失败名，785–803 行为原断言，818–820 行为结果。
* PR 完整日志 `browser-108811444631.log`，90609 bytes，SHA256 `4ac51c9f3fa8fcb55465e6e519692efd8ddefbb3395132073e9145b3dfd466c0`。148 行为 checkout，785 行起失败名，787–805 行为原断言，820–822 行为结果。
* push 原 artifact 10955211920，298222 bytes，ZIP SHA256 `48290daac0d75ee7fabb9448afdcb3e40c90597602390bd3b67d69b27b0a2f3d`。
* PR 原 artifact 10954533289，298883 bytes，ZIP SHA256 `545369324422ff855ed53ef025d41767a92664910155d9ae29918b6588eed28b`。

两个 ZIP hash 均与 GitHub artifact.digest 完全相同；各 8 成员全解包并逐 bytes/hash 回对 ZIP，没有只保留成功摘录。每份包含原 Tutor diagnostic、error-context、截图及其他已有诊断附件。图片未在本轮目视审阅，不据图推断唯一根因。

两个 browser job 的原安装步骤均 success，`dpkg-query` 实际输出 bubblewrap `0.11.1-1ubuntu0.3`；失败步骤为 make test-e2e。此处不把测试失败描述成 APT 解析阻塞。采集时 PR 整个 run 已 completed/failure，其余五 job success；push 整个 run 仍 in_progress，browser 已终态 failure。只读包保留当时 API 回执，不冒称完整 push 的后续状态，也不替代父任务对其 integration 的监测。

## 单时钟事实

原目标仍为 `tests/e2e/tutor.spec.ts:148` 的同一合成 loopback case，195 行 completed 标题断言；原单次点击、5000 ms 等待和产品判断未改。以下 Node 时间均为同一个对应现场的 observer epoch，不与 API clock 拼接。

| Node / 冻结前事实 | 4cc push | 4cc PR |
| --- | --- | --- |
| 原断言冻结 | 14569.993352 ms | 14792.089123 ms |
| 最后 SSE 请求 / after_seq | id74 / 3 | id82 / 3 |
| 请求开始 | 10172.819580 ms | 10361.986122 ms |
| response 200 | 14171.391831 ms | 14464.904066 ms |
| validated_event_yield 到达 Node | 14194.610940 ms，answer_delta seq4 | 14469.545671 ms，answer_delta seq4 |
| event_applied 到达 Node | 14194.620558 ms | 14489.717075 ms |
| 最后 DOM 状态 | queued / r4 / seq4 | running / r5 / seq4 |
| Node / browser / DOM 投影数 | 241 / 24 / 7 | 268 / 24 / 7 |

两源 omitted/invalid 都为 0，7 个 DOM 投影均 matched_source。既有前三条被 abort 的 SSE 属于旧操作，不能混为末条流已失败。这里能证明浏览器已验证并应用 seq4；不能证明完成事件已产生、已发出或被丢弃。DOM 的回答容器存在也不是本文判断答案增量的依据，判断来自记录的事件类型及 seq。

API 信息独立保留其 `source_ns`：push 事后 periodic snapshot 有 98 条，PR 有 99 条，invalid/omitted=0、无 contention。两者均有 answer_delta seq4 的 frame_offered / asgi_send_returned；push 未记录 Provider terminal commit，PR 记录了 `provider_terminal_commit_returned`。两份快照均没有 Tutor terminal commit 或 completed frame。Provider 原终态提交和 Tutor 采用并提交终态是不同步骤，前者不能当作后者已发生。

事后 GET：push 诊断操作 state=failed，没有可用 Run 快照；这不是 Run.failed。PR 诊断 GET 操作完成，返回 Run running / r5 / seq5，input_tokens=1322、output_tokens=137，Tutor 视图 provider_receipt_present=false。两源合成 runtime received=1 / validated=1 / invalid=0。以上 GET / API snapshot 都是断言之后读取，不能把 PR 的 Provider commit 或 usage 放进 Node 5000 ms 截止前。

## 与 a944 的边界

冻结的 a944 诊断包 `../m62-a944-tutor-diagnosis-v1` manifest 为 `9343a7edd1f6e61028c4bf5026a2bd62bc321f1609f2286b656f16dd2c0d4c81`，本轮重新核过其 1101 成员，再引用原两份失败投影。原 a944 push/PR 均 105 PASS / 1 FAIL；最后 SSE 分别 id78/id76，在断言冻结前没有 response/finished/failed。新 4cc 各多一个已实现 Reader compare 案例，统计为 106 PASS / 1 FAIL，不把数量差写作 Tutor 回归进展。

a944 与 4cc 的 Tutor 路径和完整 backend 未变化；4cc 的全工程组合、实际运行环境及执行时序仍与 a944 不同。a944 诊断中的三次本地 4cc 实验分别原 case、被动计时、单 CPU 开关，全部 PASS；这些本地 PASS 没有关闭四个实际远端失败。

最新可支持的诊断是：新两源已经越过首答案增量，原窗口内未观测到最终 completed；现场没有同 clock 的 Provider guard、DB 进入、transport chunk、Tutor consume 与 finish 阶段耗时，无法唯一分解等待成本或确定是否有具体停顿/错误。不能据此宣称 UI 丢 terminal、SQLite 锁死、模型未调用、随机 flaky，或任何修复已成功。

下一步仍是先独立审查默认关闭、仅合成 E2E 的有界 API 阶段计时，而非放宽断言、追绿重跑或删验证。需要用相同 API monotonic clock 分开记录 `_guard` / `_output_allowed`、DB 进入、第一 chunk、消费事件类型和 Tutor `_finish` 的进入/提交返回；保留请求关联和原 Node 冻结边界，不采正文/凭据/headers，不增加产品请求。本轮只提交证据，不把私有 throwaway profile 自动作为产品/CI实现。

## 重放与隐私范围

`verify.py` 只读检查所有下载回执、原 ZIP 与逐成员字节、15 actual Git 源、真实日志 checkout/失败行、APT 步骤、两个新诊断及 a944 冻结包。`projection_helper.py` 的四个投影函数来自旧冻结 verifier 的精确 AST 段，机械来源列于 `projection-provenance.json`；新比较另显式保留 browser event/http_status 和事后 Run 的有限元数据，所有原 JSON 不改。

本包是**私有原件**，含原 CI 元数据、合成身份/诊断与截图，未作公开净化或扫描；不得直接整体上传。没有读取真实 runtime DB、用户 key 或提供商秘密。正常复核：`PYTHONDONTWRITEBYTECODE=1 python verify.py`，依赖既有固定 Git 对象和冻结 a944 诊断包；不触发网络、测试或工作树修改。
