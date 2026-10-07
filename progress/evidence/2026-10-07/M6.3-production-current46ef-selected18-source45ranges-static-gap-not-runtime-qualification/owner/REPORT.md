# 46eface：Codex 完整请求交接的最窄静态缺口

STATIC_REVIEW_COMPLETE；源码未改；实际 tests NOT_RUN；真实 App Server/model 资格 NOT_RUN/BLOCKED；M6.3 NOT_ACCEPTED。本报告不声明 CI、真实运行边界或生产功能 PASS。

固定源码46eface069616a313aa2300654414189ba901f4d；唯一规范 PRODUCT_DESIGN.md v3.0.15，SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec，§20.17.9（1852–1869行）。SOURCE-BINDINGS.json 对18个指定文件的实际字节、Git blob/mode及每个选定行区间给出原始偏移/SHA。选定 live 文件与固定 HEAD 字节/mode全部相等，末尾HEAD仍相同；这是选定源码映射，不是全平台/CI运行前后输入映射。

## 结论

现在的 Codex proof、请求准备器、runtime profile、执行结果均限定合成协议。最窄的可本地实施项是 **Provider 内部完整请求原始字节的 producer→checker→executor 交接合同**，并用受控适配器验证它。生产空 registry 不是新的用户权限阻塞；但增加注册名、available=True、一个hash、turn/start JSON或合成模型字节计数，均不能补成真实完整 proof，也不能开放调度。

## 已满足的源码合同及边界

| 合同 | 具体源码事实 |
|---|---|
| §20.17.9 第1/3项：无 proof 时不外发，测试/生产分开 | main.py97–119、153–166默认空 ProofRegistry 和executor=None。provider_codex_profile.py172–215、286–323只接受 SyntheticCodexProof，显式loopback、synthetic-*模型及固定合成闭包；1–11明确禁止把每字节一token规则用于真实模型。 |
| 第3项：合成完整输入及变化拒旧许可 | profile.py337–399把模板/messages/history/evidence/tool definitions/init/resume/config/endpoint/profile/output预算放进完整canonical bytes，并重新准备逐字比较；302–335处理过期/withdrawal/profile变化。371行计量只对合成语言有效。 |
| 第2/5项：owner/SQLite许可与开始边界 | provider_codex_consents.py274–355核对实际source/preparation/config/revision、冻结私有request_body和摘要；current重验相同完整请求及secret可用性。214–247核对当前actor/access/revoke/current及持久possible-send。 |
| 缺执行器拒绝与回滚已经存在 | codex_turn.py292–297在同一事务内tentative consume后检查execution_available，异常全部回滚；worker.py186–218在claim/record_start前再查，220–238在模型请求入口前核对原owner/lease/access/cancel/deadline。不能把补重复guard说成新的修复。 |
| 第3/5项：单次合成请求、保留原响应、无暗中重试 | execution.py89–134绑定完整合成shape/摘要；174–243只允许原bytes/endpoint/output预算一次，入口调用before_request并保留第一原响应。其墙钟检查不能中断阻塞call或证明实际CPU/memory/process限制。 |
| 未资格事实准确持久化 | preparation_models.py1–84已有implemented=False的原bootstrap/provider/history闭包和恰好三个missing qualification；protocol_models.py1–31、63–173已有九个固定schema原字节与内嵌refs目录，明确不是完整turn/RPC/model协议或runtime proof。 |

现有源码测试已包含相关断言：test_provider_codex_profile.py61–90、176–237覆盖无proof、ASCII/中文/Unicode/重复、完整refs/tools、隐藏字段及假真实模型拒绝；test_provider_codex_execution.py45–71、97–143、199–238、267–295覆盖无transport、exact bytes、绑定/guard变化、第二请求；test_codex_turn_dispatch_http.py307–322、504–518覆盖无adapter回滚及无proof拒绝；test_codex_unavailable_preparation_closure.py107–137、158–173、184–206覆盖原事实/重启只读/假资格拒绝。这里只读测试源码，未执行，不能记PASS。

## 未满足的真实资格

1. profile.py288/337–392没有 production complete-request producer/preparer：只接SyntheticCodexProof并生成SyntheticCompleteRequest。真实 App Server 可能在 turn/start之后内部构造/补充模型输入；仅计turn/start字节、传hash、九个approval/interrupt schema或已有已知事实闭包，都不能证明完整模型输入。没有注册实际模型tokenizer或审查过的完整输入上界checker。
2. profile.py91–108仅有literal synthetic profile；其进程无关peer闭包不是实际binary/deployment/init/resume/turn/network/resources全闭包，更不是宿主资源边界执行证据。
3. worker.py35–53与execution.py34–86的profile/result/first_response也是合成专用；worker.py283–285强制解析合成结果，293–300、309–340仅允许exact SyntheticCodexExecutor取得受控callback/stop/artifact映射。任意注入callable或返回DTO不能取得真实停止/工具/文件权威。生产protocol/runtime/executor/实际计量及完整proof仍缺，§20.17.9第9项不可判PASS。

## 下一项可编写实现及明确边界

实施一个小的 **Provider-owned Codex complete-request preparation port** 和可执行的纯本地交接校验器：

- 在provider_codex_ports.py（或一个集中新文件provider_codex_request_preparation.py）定义私有producer/preparer边界，交接原immutable bytes及format/checker/profile/config/目的地/model/source的精确绑定。checker必须检查交接的同一原bytes；digest-only、partial turn/start frame、一个“complete”布尔值或available=True不能生成InputTokenAssurance或RunnableTurnInput。
- 把provider_codex_profile.py当前合成准备器放在这个边界后，保留所有原v1请求/profile/checker原bytes与字节计数oracle。需要表达production候选时，只能返回明确 **unqualified candidate**，局部字节/hash/绑定一致性可验证；不能借synthetic proof、implemented=True或某个泛型callback自动晋升为真实资格。不得增HTTP/env注册入口或裸模型测试入口。
- provider_codex_consents.py299/343通过唯一内部prepare/verify边界处理完整原字节，使许可时冻结和再验的原bytes与执行入口一致；不改source/actor/revision/secret/consent/history的owner事务。生产producer/checker不存在时仍CODEX_INPUT_PROOF_UNAVAILABLE，preview/grant/start不能开放。
- executor交接以当前exact-byte/once/before_request受控入口为基准。不得把SyntheticCodexResponse或其octet用量改名当真实响应；后来真实adapter必须另有经审查的closed response/protocol/resource/stop映射，返回DTO本身不授callback/artifact权限。

这一项具有实际本地验证面：受控producer构造完整bytes；checker与受控executor分别记录收到的原bytes相等。新负例包括交接后篡改、隐藏附加bytes、config/endpoint/model/secret/profile/checker变化、过期/撤回、synthetic冒充production、partial frame/digest-only、第二请求；全部须在受控transport前拒绝。production-candidate注入仍应真实HTTP preview/start拒绝并保持owner全表事务回滚与零受控transport。保留原synthetic oracle/普通Provider隔离，不用真实CLI/model/key/host试探。上述实现与新增验证目前全部NOT_RUN。

这是§20.17.9第3项的内部实现前置合同；普通细节已经授权（1854、1869行），不用另造用户许可环节。它只闭合局部交接缺口，不能解决真实上游隐藏输入、实际token计量、唯一实际模型请求或宿主工具/资源边界，也不能关闭M6.3。真实完整proof与qualified runtime仍须先于生产调度。

## 只读范围与原失败保留

仅选定18个tracked spec/source/test文件及Codex/Provider窄rg文件发现；未import/execute应用，无测试/model/key/network/host/profile/ptrace/process_vm/process探测、无source/index/remote变更、无archive脚本执行。三次窄rg实际exit2仅因猜测路径不存在（provider_protocol.py；provider_execution.py/domain/ports.py；codex_turn_request_models.py）；后续按imports/rg --files读取actual provider_ports.py/provider_codex_ports.py。原static recorder actual1因范围267–297超过实际295行，失败目录另存，不是产品/test FAIL；v2只修正读取范围并成功封存，不是测试retry。
