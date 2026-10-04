<!-- task_id: M6.3 -->
task_id: `M6.3`

spec_version: `3.0.0`
spec_sha256: `ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`

唯一规范：根目录 PRODUCT_DESIGN.md（第 17/19 章及相关附录）。

需求 ID：R-23, R-27

目标：CodexBroker/App Server、操作审批、产物清单

依赖：M6.2

修改范围：规范对应模块、契约、测试和脱敏工程进度。

验收清单及预期证据：
- [ ] M6.3: 拒绝操作零执行，路径逃逸阻断，成果预览回导


未包含：其他里程碑的未实现功能、付费真实调用、公网部署；结构与模拟 PASS 不替代真实集成或教学效果。

实现、检查、证据和下一任务由 progress/state.json 及任务回执记录。
经审查/合并后才关闭任务；当前清单不表示已经验收。

<!-- engineering_progress:start -->
M6.3 in_progress，整个M6.3/AC21尚未验收。唯一规范PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec，已批准的受控turn补充按现行合同实施。

已公开branch与草稿PR56 head为1e7ad7a8656c0dc8373d4181fa3002f385ed1847，实际2026-10-04T22:44:26.904920UTC读回同head，draft/open/unmerged，依赖PR55。此次普通sourcepush包含已独核准备闭包v4与离线schema目录/有限codec、明确测试证据和进度。未GitHubmerge/release/deploy。

准备闭包v4固定source495e4daddddb64460326659be5af341085654131：同SQLite事务冻结和重核已检查BootstrapSnapshot/digest/Provider配置/任务材料与历史；implemented严格false，明确production_input_proof_unregistered、production_turn_protocol_unregistered、production_turn_runtime_unregistered。prepare仅建真实本地Job和原件，GET纯读，外发preview仍503/CODEX_INPUT_PROOF_UNAVAILABLE，无proposal/consent/start。原focused30/related九文件334和5static实际通过；root独核116明确候选，原RED/mypy3diagnostics/RuffF401及独立范围勘误保留。

新离线目录source27f549ff5a8fd67b0a601b67a5ba51ef35f6765f，正常localmerge8978880982f4190ce688d7fbf2a9be72d30d5657：严格校验规范指定9原schema/93287bytes/97localrefs，固定非秘密历史来源摘要2101bytes；私有完整receipt55893未入Git。codec仅序列化interrupt params或decline/cancel响应，不构成完整RPC、owned mapping、审批/发送/执行权限。生产main/ProofRegistry/executor仍空/None，原HTTP/54core/0001未改。固定27f原68focused/186related三文件/5static真实PASS；186含v4的30，不与旧334相加。Ruff全项目0/mypy290files0/gen82/specM0结构/diff0；root独核98候选、1541当前源、7Gitmaps10760bindings、15阶段46204bindings，Spec/Standards0P1P2。原first1FAIL→同27行1PASS、typed1FAIL65PASS→同239行66PASS、RuffF401/mypy调用exit2保留；没有真实CLI/model。

原公开6671 attempt1 push37234694749/PR37234699481现已各6job SUCCESS（terminal57 at22:20:03UTC）。每组backend926PASS、frontend1421PASS167files、spec962PASS、browser133PASS、integration2467PASS/2真实numericENVskip/2warnings；pushintegration4354.97s、PR4297.49s。owner12完整原joblog已核，root此前读4browser/integration原log；另一peer独验88候选1384checks，未打开私有完整log/ZIP。push6671/PRab37同treefe6a9cf，CI working-input before/aftermaps NOT_CAPTURED。原数值仍failed/environment_unavailable/BLOCKED/exit1，发布409未发布；6DTO=4logicalJob不是processcount，缺字段保留ABSENT。failurediagnostic步骤14均SKIPPED，失败上传资格NOT_RUN。旧35ae双FAIL、原因UNKNOWN及永久原rawLOSS全部保留。

新公开1e7ad两原CI实际已创建：push37241154917、PR37241158099，attempt1，最新已保存快照2026-10-04T22:44:58.097172+00:00；当时push queued/PR in_progress，各job queued/in_progress，未有新终态PASS。不借旧6671CI验收新495/27f后端。已启动27f完整Python原命令uv run --frozen --offline pytest，collected4441，session81265；截至本次记录尚无终态。其contract/test_tutor_transport进度出现真实F，详情待原完整日志；另行同source定向实测该SSE TypeScript执行case实际1FAIL：Node24.21.0 required/setup缺失，1541beforeafterexact（logbc4c83b8d6b7f54c3705ef615d291981455896af936331d5fb2c4cabe892cf2d）。这只确认独立定向失败的准备原因，不追认原完整suite唯一根因，不称已修复。原完整命令继续不改环境，另隔离tree按现有锁定setup准备后重验。新wholePython/native尚未验收。

本次固定待推送1e7ad审查：22290当前路径，其中21833旧mode/type/blob沿固定6671已独审来源保持；457新增/变化路径及514待推送新对象有限扫描0疑点。8明确证据包433newfiles+4docs，HOME/runnerprefix转换明确；私有原receipt、DB、完整CIlog/ZIP等未准入Git。扫描只是限定补充，不作全面PII/物理安全/学术质量保证。原用户b895clean保持。

production完整InputProof、完整turn协议与受控runtime仍缺实现及真实资格，属于工程缺口。真实DeepSeek/CLI模型turn、工具/Broker资源与停止、物理数值、来源数学教学、整个M6.3/AC21/M7未验收；M7仍todo。本续作0外部模型请求，用户key未使用/入库/上传；不重启已拒绝host probes，无原CI取消或rerun。

下一任务：保留并取得新原完整Python和新公开CI终态/原日志；在新隔离tree补锁定Node准备并对失败原case重验；继续规范范围内内部RPC/response/terminal pairing实现，生产仍unregistered/unavailable。真实完整输入和单次外发执行资格另行落实，不能以codec或subset替代真实Agent验收。
<!-- engineering_progress:end -->
