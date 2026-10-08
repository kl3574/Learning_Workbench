# 实际上游 HTTP 发送门控切片

最终 candidate04 已冻结。真正的 `ReqwestTransport::send` 消费现有 `EncodedJsonBody` / `Request::into_prepared` 原冻结 allocation 和 bytes；原子 one-use 在实际 `inner.execute` 前消费。4path 补丁可直接审查采用，尚未接入 AppServer 或注册任何生产资格。

| 有界证据 | 实际结果 |
| --- | --- |
| candidate04 专门门控 | PASS：8通过、0失败、112 filtered，exit0 |
| candidate04 完整 HTTP 库 | FAIL：114通过、6失败，exit101 |
| 未改上游基线、同工具/环境/原锁 | FAIL：106通过、6失败；与04六个失败名称完全相同 |
| 原 candidate02 纯本地永久负例重现 | EXPECTED RED：0通过、7失败，exit101；旧freeze误接纳全部七个expected-reject |
| 独立静态审查 | 原2P1/3P2均CLOSED，04无剩余P1/P2；reviewer tests NOT_RUN |
| 生产完整 InputProof / executor / profile | NOT_ADMITTED |

完整库失败未改写为PASS。对照证明相同六个TLS/证书测试在未改上游代码中同样失败，未证明根因仅为环境。所有原始 FAIL/RED、终态、stdout/stderr、before/after源图均保留。未捕获各阶段test binary SHA，未以随后被覆盖的target文件伪补出处。

具体约束：只接受原真实encoded HTTPS Responses POST及明确正整数max_output_tokens和disabled truncation；JSON根必须为object，所有层级duplicate names拒绝；Host/Content-Length/Transfer-Encoding/Content-Encoding覆盖拒绝；Content-Type恰好一个application/json；Accept在freeze前显式存在。冻结完整headers、timeout、response byte cap；URL/body/headers/timeout/cap或allocation变化导致zero send且保守消费。并发16个Arc复用只有一个claim成功；失败、重建sender、clone均不refund。

受控专用factory仅Fixed/Direct，关闭proxy、redirect、reqwest retry、HTTP2、idle reuse与四种自动解压协商。冻结后直接调用inner.execute，绕过普通wrapper晚加trace/default headers；本库受控日志及Frozen Debug不含材料。公开prepared_request返回原Request，是可信私有材料，调用者仍须禁止将其Debug公开。普通constructor和新freeze并非全局额度防绕过能力；平台必须提供持久ledger，并共享同一个permit、禁止替代运输路径。

实际代码和可采用补丁：

- `test-copy-04/codex-rs/http-client/src/frozen_responses_request.rs`（freeze125、claim205）、`transport.rs`（受控factory85、send106）、`lib.rs`、`frozen_responses_request_tests.rs`。
- `public-candidate/tool-source/`保留同一4path字节；`public-candidate/upstream-http-send-gate.patch`使用正常git patch的新文件/dev/null格式，实际git apply --check退出0。
- `CANDIDATE-04-before-cargo.json`、`CANDIDATE-04-before-cargo.diff`绑定4SHA；`CANDIDATE-04-ALL-CRATE-SOURCE-HASHES.json`绑定最终完整50个crate文件；全部04源码从冻结后未改。
- `public-candidate/LICENSE`及`NOTICE`为固定上游原件。

固定上游commit：a956835d020762cb2b570053af06f643a11c0ecc，tag rust-v0.160.0；归档SHA256：351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927。原source逐件8774个regular files与archive重验零mismatch。官方sigstore subject精确匹配norm binary SHA12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad，嵌入cert签名自洽；CA/Rekor SET/SCT及可复现binary等价NOT_RUN。exact signing attempt1为failure，不以current attempt6 success替换。

归档自身manifest包版本0.160.0与原lock内部包0.0.0使初始strictlocked失败。本任务在独立测试副本仅归一workspace.package.version→0.0.0，锁SHA仍5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c，全部外部pins/Git refs/checksums保留。该差异精确记录于TEST-BUILD-METADATA-03.json。Rust1.95.0真实official独立工具链位于任务私有目录；compiler-identity回执固定59807616e1fa2540724bfbac14d7976d7e4a3860、hostx86_64-unknown-linux-gnu、LLVM22.1.2。锁SDK182个选定normal/dev依赖见LOCKED-SDK-DEPENDENCIES.json；实际cargo tree回执另存。未改HOME/CODEX、用户检出或canonical工程。

回放只运行库tests，见REPLAY.md。实际核心回执准确位置：

- `receipts/gate-test-locked-offline-04/command.json`与同目录stdout.log/stderr.log：04有限PASS。
- `receipts/library-test-locked-offline-04/`：完整114/6 FAIL。
- `receipts/baseline-library-test-locked-offline/`及BASELINE-before/after-cargo.json：原112对照。
- `receipts/red-test-locked-offline-02/`及RED-02-before/after-cargo.json：原02实现SHA固定，新增legacy测试纯freeze7case，不构造client/不发送/不调用03不兼容claim。
- `receipts/gate-test-offline-01/`、`gate-test-locked-02/`、`resolver-locked-04/`保留初始真实依赖/锁FAIL。
- `receipts/public-source-readback/`内五个API原JSON/signature、argv、exit、时间、hash；SIGSTORE自洽见SIGSTORE-SELF-CONSISTENCY.json；归档逐件读回见receipts/SOURCE-ARCHIVE-READBACK.json。
- 独立审查：`independent-rust-review-d5nwl8b_/REPORT-CANDIDATE-04.md`（SHA bb0469835ee9121c37ffecbc6b9489a42858b5f68b5fd664e0c820889d0abd9f）及该目录packet/REPORT-CANDIDATE-04.json。

公开候选为明确有限10文件，见PUBLIC-SAFE-CANDIDATE-ALLOWLIST.json；仅4path源码、patch、LICENSE/NOTICE及relative source/SDK/hash metadata。不包含私有命令/raw logs/cache/testbinary/CA fixture；本代理未公开发布。

下一实际整合边界仍明确：stock ResponsesApiRequest无max_output_tokens/truncation，因此真实producer须先增加并消费经过审查的输出限制，抽取共用纯本地最终producer以满足prepare零CLI，不可用dry-run替代。平台持久permit须覆盖重启/新turn及同permit全部retry/auth-recovery/WS/compaction外发；真实模型meter/capacity/alias、config/secret版本、pinDNS/连接边界、单独turn runtime聚合资源资格均未闭合。合同未被判不可实现；当前empty registry/defaultNone继续阻止生产执行。
