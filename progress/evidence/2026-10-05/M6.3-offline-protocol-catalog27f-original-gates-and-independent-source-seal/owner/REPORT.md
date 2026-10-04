# M6.3 已核验离线目录与有限 wire codec — 作者交付

固定HEAD `27f549ff5a8fd67b0a601b67a5ba51ef35f6765f`，base `8b8699d3aad45180ab3b339ea60979c1478f0b92`，14个新增路径/4,410+（models192行、catalog88行、test247行、manifest/非秘密来源摘要及9个原schema）。原1,527工程输入全部 mode/type/blob/size/SHA保持，最终1,541完整输入；规范v3.0.15 SHA `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`不变。§20.17.1.1/.1.2/.7/.8/.9范围内的内部模块，无新HTTP、无生产注册、无执行。

## 实际实现

`read_catalog/verify_catalog`返回严格 `OfflineTurnProtocolCatalog`，scope=selected9_schema_shapes_only，implemented严格false（0/0.0/True拒绝）。九成员要求精确原顺序/路径/size/hash，保存完整原raw UTF-8字节；97个内部ref全部local解析，不外部fetch/扩展refs。不允许剩余成员自洽掩盖尾删/全删/重复/乱序；原件和source-summary破坏均failclosed，坏读不补文件。

九原schema共93,287字节，逐字等于规范固定314非experimental来源和receipt相应条目。来源摘要是2,101字节closed/versioned人工核验投影（SHA a31441996822a75015aed858c104e9f82039de88bbeca66d8308bef5fc24af27），只标历史原receipt size/SHA、CLI/binary/profile/count/exit/time及九bindings。原55,893字节receipt含私有物理paths/argv，保持私有；未进Git或候选content。runtime read只是核摘要及九原schema，不称完整rawreceipt/currentbinary/其余305原件再验。规范所列binary SHA是历史source事实，不是当前环境/部署保证。另一experimental源三schema不同已独立分析，未替换此bundle。

有限codec：TurnInterruptParams仅支持严格threadId+turnId的owned-free形状（mapping/typed/严格JSONbytes或text），构造规范params字节；command/file_change响应只支持原schema合法decline/cancel。raw重复key、非有限数、surrogate、数字/bool当字符串、蛇形别名/extra拒绝；typed对象强制破坏后再次按真实wire别名严格核验。accept/acceptForSession/policy-amendment/permission/unknown kind不由codec开放。

这些字节不是完整RPC envelope，没有callback id/真实owned session/turn映射或任何传输许可，不证明已发拒绝/中断或远端停机。九schema只有所列参数/审批/一种patch通知，仍缺完整实际使用响应/通知配对、hidden finalrequest InputProof、deployment/session/profile/资源和单次外发强制资格。生产默认main/ProofRegistry空/executorNone、495v4与所有旧bootstrap/Provider/ACK/HTTP/54core/0001/依赖/CI预算均逐字不改。

## 真实失败与门禁

536 test-only原27行实际packaged-source-red 1FAIL（行7实际缺规范目录manifest）；450实现后同完整27行文件/同命令1PASS，不是collection或工具链失败。新增typed输入用例8a实际1FAIL/65PASS：Pydantic always-revalidate把内存Python字段名误当wire别名。387仅catalog函数2+，typed对象先model_dump(by_alias=True)再同closed校验；同8a完整239行test文件/同命令66PASS。27最终只新增两个forcedtypedmutation负例，生产models/schema/摘要未变化。

Ruff-01原F401 unused-import FAIL保留；后新增真实typed使用消除unused，并把弃用的instance.model_fields访问改成class。mypy-01是作者多余指定两目录的错误invocation，exit2/重复模块名，未进入production类型检查；未改config/依赖，按原repo配置noarg mypy-configured-01实际290files PASS。两次行为FAIL及两个静态invocationFAIL原件不追改。

固定最终27实际命令与资格：

| Stage | 终态 | 实际范围 |
|---|---|---|
| focused-final | 68PASS/pytest0.32s、wrapper0.503285s | 新源/codec test全部68；1 warning为故意forcedtyped bool损坏的serializer warning后拒绝 |
| related-final | 186PASS/pytest27.12s、wrapper27.523618s | 明确3文件：v4真实HTTP/SQLite准备、Provider synthetic profile、既有Codex DTO |
| ruff-final | command/wrapper0 | ruff check .，整个项目invocation |
| mypy-final | command/wrapper0 | repo配置noarg mypy，290 sourcefiles |
| spec-final | command/wrapper0 | M0结构/完整性checker，非产品/真实模型验收 |
| generated-final | command/wrapper0 | checked82 artifacts，旧生成品全部不变 |
| diff-final | command/wrapper0 | 8b→HEAD git diff --check |

68覆盖：精确source/字节/hash/member/source投影、尾删/全删/重复/乱序/未知path与字段、bad source/byte/重复JSON/数字bool别名、forced nested/typed对象破坏、严格有限wire与各种许可扩张拒绝、local ref缺失/外部/坏转义/数组及cycle有限解析。一个明确专项用例真实patch并断言process、bootstrap freeze/validity/execute、probe、synthetic model-transport六named seams各0，只覆盖该case的实际catalog读/核/codec调用；不是所有测试的物理监控。模块不读SecretStore/userconfig、不写SQLite或启动Job/worker；相关测试沿既有明确synthetic fixture，不称全部setup0或真实模型。

离线uv sync首次本地37已锁定依赖安装是tool stdout记录，仅配置准备，不当产品测试或host能力探针。无新全4,341/全Web/native/真实CLI/model门禁，旧CI/整体验收事实不借入或改写。

## 原件与共享范围

7固定Git图/10,760 sourcebindings，distinctblob按SOURCE_BINDING原实际值；最终1,541 live bytes/Git全部exact且clean。15阶段/30 fullmaps/46,204 sourcebindings、原command/receipt/log size/SHA和immutable Git前后全exact。两组同完整test原件分别绑定first27行、typed239行。作者自身封存不是独立review，root审查另记录。

SAFE_CANDIDATES逐项准读publication-candidates与outer SAFE/READBACK。候选仅原metadata/fullmaps、安全原logs、固定Git源码/首次两原testbytes、作者source/gate报告与封存脚本；全部identity或明确新documentary记录，不递归准读原DB/ZIP/profile/临时目录/私有完整receipt。原rawreceipt只hash/size来源声明。

生产InputProof/protocol/runtime仍未注册，typed catalog严格false。真实App Server/model/tool/network NOT_RUN；当前账号/资源/隔离环境NOT_EXAMINED，不能默认unavailable推出ENV阻塞。整体M6.3/M7仍NOT_ACCEPTED。本地candidate未merge/push/远端修改；下一步由root独立固定source/候选读回，再决定normal本地整合，真执行资格仍另验。
