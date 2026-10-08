B03-r2 独立只读复核闭合：0 P1、0 P2；标准轴保留 1 P3。B02 的 session-header P2 是真实历史 finding，在 B03-r2 的机械准备接口中修正；旧 B02 的 65 成员 review 包、原 FAIL、原 30 项限定 PASS 均保持原样。Reviewer 没有运行测试、模型、CLI、App Server、HTTP 请求或宿主探测，也没有修改被审源码、canonical 或远端。

当前冻结来源为 upstream `a956835d020762cb2b570053af06f643a11c0ecc`。B03-r2 before pin 为 `7328c68eac5a325c080da04908b802a2b78d4fbd20a68ca876caa51014a42d7e`；after pin 为 `8b74a415f036436b9cf8f8d97775f87aa116f06f94c65a4b41413d1a206b8305`；final status 为 `675558d43ab8b75fcf31f21f1e1575830c6ff3e42667b25fd5216eaa50c02603`。Author 的 230 个明确成员逐项实际 bytes、mode、symlink target 均独立回读一致，manifest `4c98b69450d5e15f18f8e848d2178d9ad579ede822f3ab9663d261c5ab236771`，seal `aed509ff06e997260aade5835fc9bb63ebe29f99a603bd48b5bc7d91d93eeb23`。

源码修正准确复用原 `client.rs:589` 的 `responses_session_id` 规则及 `build_responses_options` 中的实际传递：`SessionSource::Internal` 和 `SubAgent` 走 `metadata.session_id`，其余 root 走 `policy.prompt_cache_key`。新 `ControlledHttpFacts.responses_session_id` 明确表示实际 Responses cache-affinity header；logical session 仍单独存在于 `CodexResponsesMetadata`，最终 body 的 `client_metadata.session_id` 继续取该 metadata。`responses_producer.rs:389` 计算期望 header，399 校验 supplied header，最终 options 使用同一 supplied value。并未把 original logical session 填入合法 root header 来绕过检查。

相对 B02，只有 `responses_producer.rs`、其专用 pure tests 的内容变化和原 archive 已有的 LICENSE symlink 恢复；另三个 B core 文件字节完全保持 B02。B03-r2 source 的 producer SHA 为 `7b91f952457704cc5e5a1cd759e65bc158dd1292cdb025b27e84a941dc84d8d9`，tests SHA 为 `45f1c1c1ddb840f40c1c050e892707d724e9a9320c5947b62280464a408b7799`。AC 原 16 路径中只有原已声明的 `client.rs` overlap，其他 15 路径及全部 AC API/HTTP 源码 exact。原 ordinary build/caller/wire、lite/filter IDs、guardian/tier/access、reserved/first-wins contribution、header 处理、optional metadata budget 和一次 shared EncodedJson 编码的 B02 复核结论适用于未变化内容。新 delta 没有引入 callback、attestation、global originator、tracewriter 或 global metrics 的纯 prepare 隐藏调用。

真实行为证据按原实际 argv/cwd、完整 stdout/stderr 和终态 receipt 核对如下，均为 owner 执行，reviewer 只读：

| 当前 B03-r2 执行 | 实际结果 | filtered | actual exit |
| --- | ---: | ---: | ---: |
| `cargo check -p codex-core --lib --locked --offline` | check 完成 | — | 0 |
| `responses_producer::tests` 全部当前 controlled module | 11 PASS / 0 FAIL | 2665 | 0 |
| 原 WS handshake `own_cache` / `inherited_cache` | 2 PASS / 0 FAIL | 2674 | 0 |
| 原 internal cache key parent-thread 测试 | 1 PASS / 0 FAIL | 2675 | 0 |

当前有限测试合计 14 PASS，四命令和 batch 均有实际终态。core 仍有已有编译 warning，未把 check0 说成 warning0。完整 core 2676 项、guardian suite、原 API190、HTTP8、B02 原其他 23 项都没有在 B03-r2 重跑。本次不是 full core、模型传输或生产 PASS。

实际 meaningful RED 位于 `red-session-tests-locked-offline-B02-02`：原 B02 implementation exact，三个同材料 fixture 得到 1 PASS / 2 FAIL、actual101。root 正确 parent affinity 被误拒绝，root 把 logical identity 作为实际 header 被误接受，是两条真实反例。三个 fixture 在 B03-r2 保持实际值和断言，仅字段 identifier rename 与 Rustfmt whitespace/trailing comma 差异；它们在 GREEN 成功。新增第四个 non-root 错用 parent cache body 为 header 的负例也成功。原七个测试字节仅有必要 actual header fixture 值与 field rename，原断言没有放宽。

来源图由独立 stdlib 直接读固定 archive `351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927`，未执行作者 extractor：真 tar 8775 项；source/test-copy 各 8781 项；全部 bytes、mode 和 links 与冻结图 exact。真 tar 到 candidate 仅声明的 20 code paths。测试副本只把 workspace package version `0.160.0` 归一为 `0.0.0`，原 lock `5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c` exact，没有原 release binary/profile 等价声明。终后 source/test 两个 whole graph 与 before 全等；实际 830879912-byte lib-test binary 独立流式 SHA 为 `e9e68ca5b8b89785dc9c4d0e7992c80e7ab32cc9eefe8015b258c48e20c495bb`，只读 hash，没有执行。

旧 private stock 8774 / B02 8780 图是 content 与 link 图，并没有全 mode 同一性：相对真 tar 少 `codex-rs/vendor/bubblewrap/LICENSE -> COPYING`，还有 57 个 regular mode `0664` / 原 `0775` 差异。新 source 来自真实完整 tar，保持原 symlink 和所有原 modes；code patch 不添加本来已有的 link 或改 modes。真 tar combined patch applied copy 的 8781 项全 bytes/modes/links exact。旧 private AC incremental patch copy 只恢复它自有 copy 的原 link，content/links 全等但 57 个 mode 差异继续单列。原错误读回 actual1 和完整 stderr 保留；随后 limited readback actual0，没有回写旧 stock/AC/B02 或把旧图称成全 archive exact。

失败和无覆盖历史单独保存：aead/console offline missing crate actual101；旧 fixture E0308/E0063 编译101；B01 E0277 编译101；真实前 B02 controlled-gate RED101；B02 header RED1P2F101；B02 source-graph metadata filename FileNotFoundError1 及有限修正0；B03 private mode 假设错误1及有限限定0；旧 AC selector actual0但 0 PASS / 190 filtered，不能计覆盖。旧 HTTP04 全库 114 PASS / 6 FAIL / 101 继续保留，没有转成 PASS。首版 B03 的 before 记录仍为 NOT_RUN，没有把 r2 receipts 归到首版。

标准轴 P3：新四个 fixture 的 `prepare_controlled_core_request` 调用，例如 `responses_producer_tests.rs:454/456/458`，未给 `None` / `false` 加仓库 `AGENTS.md` 要求的 `/*effort*/`、`/*service_tier*/`、`/*include_internal*/` 参数注释。这是可读性和仓库约定债；argument-comment-lint/Bazel NOT_RUN，不推断其实际失败，也不盖过行为 GREEN。旧冻结 r2 原件保持，根已安排新工程副本单独处理。

唯一规范 `PRODUCT_DESIGN.md` v3.0.15 SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`，§20.17.1.1 仍要求完整最终原始字节、可信具名端口、InputProof、capacity/profile 与受控外发边界。当前 `Resolved`/`Requirement` 和 supplied facts 只做机械完整性检查，不验证来源权威，不产生 InputProof/FinalAuth/ledger，不登记 platform bridge，不证明 token/capacity/model/resource/DNS 资格，也没有生产注册。规范轴因此只闭合授权的 private mechanical preparation 范围，生产状态仍 INCOMPLETE / NOT_ADMITTED。

所有 reviewer 命令是已结束的有限只读操作。一次 reviewer fixture identity checker 忽略 Rustfmt trailing comma 产生 actual1，原脚本及 stderr 保留；新 token 归一 checker actual0，严格保留 string values/断言并只忽略 whitespace、optional trailing comma 与字段 identifier rename。该工具错误不是被审测试 FAIL。旧 B02 65-member manifest 及每一成员实际 hash/bytes 完全一致。后续工程入口和注释副本未纳入本版 review。
