# 22dade session interrupt UI：独立最终审阅

固定 head `22dade7996f13634202250ef5e1c05dc976214a5`，base `35aebd3039241abb3393300affd593f4826a4a0c`。**Standards：零新增 P1/P2；Spec：零新增 P1/P2。** 一个未拥有此次源码的独立审阅人分别审两轴。结论仅覆盖此 UI 源码、明确准入的原 Web 门禁及 learner/awaiting turn 的受控 Chrome 证据；不等于 M6.3、AC21 或真实 CLI/model/tool 验收。本人没有执行新产品测试。

## 固定源与 Standards

精确 8 个 Web 路径、234+/13-：4 个生产 client/command/hook/Panel 文件、fixture 最小补项及 3 个测试路径，其中组件测试新增。base1524、final1525；1517 旧非重叠输入 mode/type/blob/size/SHA 全部保持。两个独立固定 Git 图3049 bindings、1513 distinct blobs，final live bytes exact。唯一 PRODUCT_DESIGN v3.0.15 SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`、后台、配置、依赖、迁移及生成品不变。

client 使用既有生成 endpoint 和 closed CodexInterruptWrite/Ack；没有 raw wire、宽松 DTO 或内部自动 retry。现有 Origin/CSRF/Idempotency transport 保持。journal 的 v1 namespace、旧 prepare/cancel decode、immutable 比较及原 ACK 合并规则保持。新增 kind 是明确的完整持久命令，不重建旧 body/key/basis/ACK。

## Spec

依据既有 §20.17.5/.7/.9，不新增规范或 route。

- `turnClient.ts:125–129` 严格校验完整 body，向原 session endpoint 单次 POST 原 key；拒绝错 session/turn/status/extra ACK。
- `turnCommands.ts:44–56/67–69` 完整冻结独立 current session 与 target turn，不用 Job revision 替代 session CAS。session、turn、revision、活动 turn 关联及 terminal 例外严格绑定；creator 克隆完整 actor/workspace/body/key/basis，先持久再 POST。
- `useCodexTurns.ts:118–153/226–231` 只使用分别显式 GET 的 current session 和 control；选择改变清空基准。stale basis 交给后台 CAS 裁决，不从旧 ACK 或 client 猜 revision。
- `:171–213` shared execute 核原 actor、retain/persist、再核 fresh 原 actor，才唯一 POST。保存失败零 POST；412/409 留原 body/key/basis/error，不重建、不隐式第二 POST。显式 replay 保持原命令，独立 GET 不执行命令。
- ACK 先归原命令严格 decode/retain，再核 page/access/port/store/unmount/token 和当前原 actor；晚 ACK 不跨 scope 采用，保存失败保留隔离 memory。新 safe actor 可独立读取并创建自己的 safe 命令，但不能 replay 旧 actor 命令。
- `:254–265` interrupt 与 cancel 使用 safe control 资格，learner/independent/open_book 可执行安全停止控制；准备正文仍受作者及当前学科策略保护。Panel 保留 Job cancel，并明确 session interrupt、历史 ACK 与当前 GET 分开；terminal ACK 不声称远端或物理进程已停止。

新增整组件负例、wire DTO 负例和 journal 负例覆盖真实 client/body/persistence/controlled Promise 时序。page/access/port/存储保护复用原 shared guards；本审不声称所有 interrupt 组合都逐项进行了 native 执行。

## Web 原件读回

仅准入 seal-22dade 的50 candidates及2 outer metadata，逐项 bytes/SHA 校验；identity 或文档明示的 literal homeprefix 转换与 raw SHA 一致。没有打开被排除的原 DOM 失败日志、runtime、DB 或临时目录。11 原阶段、22 完整 before/after maps 共33550 bindings，对3固定 Git heads 的 mode/type/blob/size/SHA 全核。原运行输入不被本次静态回读冒充为新测试。

| 原阶段 | 实际终态与限界 |
| --- | --- |
| af20 三次早期 toolchain | 各 exit1、0 tests；ENOENT/module layout failures，不能计行为 RED |
| af20 focused-baseline-private-temporary | 原4 FAIL/1file；只读准入 bounded summary+原完整log SHA，不读25892-byte private raw DOM |
| 684 focused-original-green | 原4 PASS/1file，exit0；与 af20 原整组件文件 SHA 完全相同 |
| 684 strict-first | 原 exit1：TS6133 未用 refresh、TS2339 callback 中联合类型 narrowing，两项保留 |
| 22 focused-final-components | 原127 PASS/4files，exit0 |
| 22 full-web | 原1421 PASS/167files，exit0 |
| 22 strict-final / diff-final / build-final | 各原 exit0；build 既有大 chunk advisory 保留 |

af20/684 整组件 SHA `095e267d26a78188f46f9ccf3d49d4000cc0983f8bae7c78a657a0a58197079f`；final 组件有新增负例，不能说它与行为 RED 是同整文件。final22 同时将 callback narrowing 改为 closure 外固定 target，并删除 unused helper。中间 SOURCE_ONLY 中的早期口述精度不追改，最终按实际源码和原 strict failures 校正。

成功原 log SHA：focused-original-green `327cef304c3649a5ffac1d633ea7d5bd3e2f0604f0f31870d6790d14e79c1a65`；final focused `f9207edaa5a3ab214392e17df56b756d2a5568f6db0f498b877e0e7e2649b146`；Web `b0ea9b96abd5a8b079de19b352a03aba5d1a7456b1f4e7875ac897afaa3a9d58`；strict `b9df407f06dd3350bcb5d41df640c2603d5d70f268d57fe256fe1159da11cc68`；build `1866368facc52a1ae8f9c70787a10d3715b750caebe3ca546bc6133b199fcbcc`。

历史 Web runner SHA 未在原 receipt 捕获。当前 runner hash 只证明当前 bytes，不能回填到旧运行。失败后临时布局变化有记录，不补造历史 runner binding。

## 受限 Chrome 原件与保留损失

仅准入 native seal-22dade 的38 identity candidates及2 outer metadata。9 retained maps、13725 bindings 与 final1525 Git inputs 全 exact；脚本、commands、receipts、logs 及 terminal sentinels 均读回。本人查看全部6张原 PNG 并核 hash/geometry；1440/390 展示 learner 安全控制、原 ACK/独立 current、fresh actor 对原命令只读，无可见学科正文或认证秘密。390 图片是 viewport slice，不证明整页或全部 React effects 完成。

**FIRST_RUN_PRESERVATION_LOSS / LOSS_V2 必须保留：首轮动态原始日志、回执与 maps 已被误执行覆盖并丢失。** 首轮时间/hash 仅为文档或工具派生事实，无法独立重读或恢复；没有重构原件。现有 run-01 是第二次误执行，实际 exit1、工厂配置失败，未进入 Chrome，产品 NOT_RUN；sentinels NOT_AVAILABLE，不能计零执行。它不能冒充首轮记录。

run-02 是新目录中的独立受限成功，实际 wrapper/build/native exit0，native log SHA `78d183295b68aa7076bb6cde05821bb24301f979bcea07d423ffef0f2d860241`。真实 Chrome154、私有 loopback Uvicorn、原 lifespan/SQLite/IndexedDB；受控内存 bootstrap1，生产 executor=None。未批准或启动模型请求。

实际 learner awaiting turn UI：持久完整原 actor/workspace/key/body/session+turn basis 后发送；原真实200 ACK 丢交付，刷新无自动 POST，显式原 key/body replay 取得同 ACK 后持久；独立 GET 显示释放 session/取消 control。第二命令以明确 fixture 竞争中断产生 stale CAS，UI 原 basis 真实412，fresh GET/reload 不改原命令；显式原请求 replay 仍412。切换新的 learner cookie 后原命令只读、不能 replay，旧 journal bytes 保持。实际 browser interrupt POST4 次，另有 fixture 竞争 POST1 次，bootstrap/config/role/prepare setup 写属于明确夹具边界。

terminal sentinels 原事实：lifespan-exited，codex_executor/provider_transport/literal_operation/later_bootstrap 各0，synthetic bootstrap1，executor_none=true。Chrome关闭和 owned Uvicorn 退出有 awaited cleanup；不升级为主机全局进程审计、真实模型/tool/CLI 或运行中 job interrupt 证明。independent/open_book 仅本次组件覆盖，未声称其 Chrome 路径运行。

run-02 原防覆盖只有 **4 paths**：command.json、run-receipt.json、native.log、build.log。failure.json 与 receipt.json 未列入该原检查；后来的6路径要求不能回填原脚本。后续必须使用全新目录并在执行前保护所有6输出，原丢失事实不关闭。受限新成功不抵消首轮保留损失，也不构成产品 RED→GREEN。

## 最终资格与共享范围

共读88明确 candidates、4 owner outer metadata；31 retained maps 共47275 bindings。新测试、模型、真实 CLI、网络/主机探针、发布、source/canonical/旧seal mutation 均0。两个轴源码零新增 P1/P2；首轮不可恢复原证据、完整能力和整体验收仍有限界。

root另行运行的完整22dade native，在本审最后明确消息仍 RUNNING，未准入本包，不预报 PASS。public35ae 两个 browser CI 原132P1F、首 Review timeout/causeUNKNOWN，仅为 root 报告，未读该原件；本地 UI 门禁不覆盖它们。whole M6.3/AC21 仍 NOT_ACCEPTED，真实 CLI/model/tool NOT_RUN。

`REVIEW_SOURCE_ONLY.md` 历史中间报告保持原 SHA `5d7bc6dfb28a470e57ba13cd121a3be84a938dab23fdbb798b5fb64dbeb7710a`，不重写为完整证据审结。SOURCE_STATIC.json 中 pending 资格也是历史快照；本最终报告与 FINAL_READBACK.json 明确新增的实际准入范围。

本包只准许 SAFE_SHARE.json 列明5文件与 OUTER_METADATA.json 明确两份 metadata；其余中间报告/私有 maps 不是递归共享授权。两个 VERIFY 脚本仅供纯文件/Git documentary readback，不包含产品测试执行。此独审包未经发布。
