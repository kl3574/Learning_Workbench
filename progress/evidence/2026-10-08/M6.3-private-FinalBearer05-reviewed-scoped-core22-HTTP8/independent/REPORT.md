# FinalBearer05 — 独立有限静态审查

结论：本次新增的私有 static-bearer finalization 机制 **Spec P1/P2 = 0，Standards P1/P2 = 0**，在明确范围内静态闭合。审阅者没有运行测试、编译、模型、CLI、AppServer、网络或宿主探针，也没有修改候选、canonical 或远端；审阅者测试为 **NOT_RUN**。这不是完整 FinalAuth、InputProof、平台桥或生产 profile 验收。生产保持 **NOT_ADMITTED**。

固定作者包为 `$HOME/.cache/learning-workbench-acceptance/m63-final-bearer-rust-private-oct08-sa5_h9px`，最终 `source-05` / `test-copy-05`。作者 manifest SHA256 `8f6922b8a3e211c1eb4902df273083e6ac1898ca1932ba5dafc92168f7f55669`，SEAL `532e4623efd131fae26afbd150b5459d202e7c842e46f13d915d3144a595f4b7`。唯一规范 v3.0.15 为 canonical `PRODUCT_DESIGN.md`，SHA256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`；本次直接复读 §20.5、§20.17.1–20.17.1.2 和实际 upstream root `AGENTS.md`。上游规范的测试/格式操作没有在只读审阅中执行，作者的受限工程命令由 root 的显式指令限定。

| 固定材料 | SHA256 |
| --- | --- |
| `codex-rs/core/src/responses_producer.rs` | `747c973d33bfffef7b45a8524aed6c4d7192c259c7cccb427fe66a4291185b1f` |
| `responses_producer_tests.rs` | `9f5ca40984a5172a465dcb257d29e355eceacb471f2b8d778cccbc6e30d2fe54` |
| 两文件 incremental patch | `95a0d1d8c7f9670090629ae63c087a916b645da3f08378bfd1fb789888504781` |
| 原 `Cargo.lock` | `5553f06583159ed64666b6eb4beea3154e06b612e6312528131bdc226a6a860c` |

`responses_producer.rs:512–554` 消费实际 `Request`。它先拒绝 unresolved、ChatGPT、签名、refreshing，以及已有 Authorization、Proxy-Authorization、Cookie（包括重复值）或非 `EncodedJson` body；随后检验单一 ASCII `Bearer ` token 的明确形式，把 HeaderValue 标为 sensitive，安装 Authorization，最后调用真实 HTTP04 `FrozenResponsesRequest::freeze`。没有 live auth object、callback、telemetry、I/O、传输、重试或第二次 encoding。错误为固定 unavailable code，不包含凭据。这里的 auth mode 与 HeaderValue 是机械材料，不是可信来源证明。

继承 HTTP04 的 `frozen_responses_request.rs:125–192` 在最终 Auth 已安装后冻结 URL/method/header/body 和输出硬限。`request.rs:124–156` / `prepare_body_for_send` 对本次未压缩 EncodedJson 使用共享 Bytes，未把 DTO 重编码为替代请求。冻结对象仅输出隐藏内部字段的 Debug；Authorization 的 sensitive 属性在真实 Request/HeaderMap 克隆中保留。该机制没有新增日志调用；受控 sender 的 request-body TRACE 已关闭。一般 Request 的 body 仍能被独立调用者 Debug，因此不能把整个库表面宣称为普遍材料保密边界。

真实 `transport.rs:85–154` 专用构造器固定 Direct backend、no proxy/redirect/retry/decompression、HTTP1、零 idle pool；`FrozenResponsesRequest::claim:205–229` 在真正 `inner.execute` 前原子消费共享 Arc，核最终 built method/URL/headers/timeout/response cap/body bytes 和 allocation，后面绕过普通晚默认/trace header 修改。新增代码没有改变这一发送边界。一次变更、连接失败或新建 sharing-Arc sender 不能退还已消费 capability；clones 共用原有 CAS。已有 explicit Accept 与严格 Content-Type/framing 限定仍由未变 HTTP04 执行。

新增测试 `responses_producer_tests.rs:566–821` 使用实际 B03 preparation 与 HTTP04 sender。它们覆盖 Auth-before-freeze、allocation/bytes/method/URL/timeout/cap 保留、sensitive/单值/Debug、非静态/未解析模式、重复/冲突鉴权、畸形 token、普通 JSON/输出硬限/压缩/method 拒绝、late-auth mutation 零 owned-listener connection、closed-loopback-port 的实际 connection failure 不退款。测试没有使用真实模型或用户 key。审阅者只读回作者原 stdout/stderr、command exit、脚注和来源图，没有重跑这些动作。

| 作者真实最终命令 | 结果 | filtered |
| --- | --- | --- |
| core producer 模块 | 19 PASS / 0 FAIL，exit 0 | 2665 |
| 原 WS cache header 两例 | 2 PASS / 0 FAIL，exit 0 | 2682 |
| 原 internal parent cache | 1 PASS / 0 FAIL，exit 0 | 2683 |
| 继承 HTTP04 gate | 8 PASS / 0 FAIL，exit 0 | 112 |
| core `--lib` check | exit 0；不是测试 | — |

core 22 与 HTTP 8 为分开的有限范围。完整 core 2684、guardian tests、API 190、HTTP 全 120 和 workspace/Bazel 检查均 **NOT_RUN**；旧 HTTP04 完整 **114 PASS / 6 FAIL / exit101** 仍为 FAIL。本次不能以 check 的成功外推完整测试通过。

实际排序 RED 原 stdout 为 **0 PASS / 1 FAIL / exit101**，冻结 Auth 为 None、之后候选 Auth 为 Sensitive。它显示缺少 Auth-before-freeze 的接缝；旧 HTTP04 本来就拒绝 late Auth，故不是发现旧门控可外发的安全漏洞。Cookie04 的相同十九项测试实际 **18 PASS / 1 FAIL / exit101**；05 只加 Cookie guard，测试源 SHA04/05 完全一致，再取得 19/0。首个 GREEN 1/0、错误 cwd101（零测试）和 E0432/E0599 compile101（零测试）均按真实阶段保留。没有改断言消除失败。

独立读回实际退出 0（工具 chunk `23334b`）：作者 209 个有限成员中 205 个非测试二进制成员重新核 SHA/size/已声明 mode/链接目标，零差异；四个大测试二进制只核 size/mode 和作者声明 SHA，没有重新 hash 或执行。本报告不把后二者称为独立 binary qualification。记录图 before/after 对相同 source/test-copy 都一致，8781 行；相对 inherited engineering 图只有上述两文件改变，8779 行相同。十个选定 live source/test 文件实际重新读回并同图核对；没有重新递归枚举 whole live tree/target。test-only manifest 精确单次 `workspace.package.version 0.160.0 → 0.0.0`，原 lock 相同，其余图均相同。作者四个实际 git check/apply 回执退出 0，日志/hash 与固定 tar→engineering→incremental chain 相符；审阅者未重复 apply。官方固定源仍为 a956835d020762cb2b570053af06f643a11c0ecc、archive SHA351a23896ba75c2c32c2d9d2050a0987079d683ea4e92d3429b3e1833945e927，不等于原 CLI release binary/profile qualification。

审阅者自己的首轮 readback 因 manifest symlink 记录没有 mode、脚本却比较额外 mode 而退出 1（chunk `9bd85b`）。原脚本、真实失败与 stderr 存在 `readback-attempt-01.py` / `READBACK-ATTEMPT-01.json`；只修审阅脚本，使其严格比较 manifest 已声明字段后实际退出 0。候选没有变化。该失败属于审阅工具 schema 处理，不是候选 Cargo/test/source 失败。

尚未实施的边界明确保留：同一具名可信 owner 从真实 SecretStore 读取并稳定版本，基于同一 auth 解析所有 B03 required facts，再把这个实际 Rust request handle 与已有持久 Codex/Provider record_start 同事务绑定，提交前零 send，提交后只走受控 route；Python↔Rust 真 handle bridge、完整 InputProof、模型/计数/容量、实际资源/DNS/TLS/runtime/AppServer/WS/隐藏额外请求全闭合仍缺。已有持久平台账本确实存在，缺的是它与实际 sender 的可信整合。`prepared_request` clone 可被再次 freeze 成新 Arc，普通 constructor 仍存在；可信 owner 必须阻止同许可建立新 capability 或进入 ordinary AuthProvider/EndpointSession/retry。这些是当前明确未注册的整合边界，不能把 plain fact 或本次机械 helper 冒充该权威。

Standards 审查没有发现本次两文件 patch 的新增 P1/P2：私有 `pub(super)`、具名 enum、独立 tests module、固定错误、函数参数类型和新增 positional-literal 注释均与适用 root AGENTS 相符；70 行 helper/enum 与 261 行测试处于有限 patch。没有改依赖、schema、公共 DTO、现有 ordinary caller、生产注册或用户流程。后续扩大功能时应按 upstream 模块长度指导抽取；这不是本次阻塞性 finding。
