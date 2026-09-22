# 当前工程进度

本文件从 `state.json` 生成；需求仅见 `PRODUCT_DESIGN.md`。

更新：2026-09-22T04:18:41Z；规范 SHA-256：`2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d`

仓库发布：VERIFIED；Issues 同步：VERIFIED_READBACK
实施：IN_PROGRESS；当前任务：M6.1；下一任务：M6.1

同步PR54确切head的CI状态与真实证据；继续生产输入计量checker候选工程和受限数值运行诊断，再推进M6.1验收。生产证明、数值环境、内容质量与既有PR53 CI失败边界保持。

| 任务 | 状态 | Issue | 验证代码 |
|---|---|---|---|
| M0.1 空工程、依赖锁、启动脚本、lint/typecheck/test/CI | review | [#10](https://github.com/kl3574/Learning_Workbench/issues/10) | 401e0819b61f33ee918dbe0d739b686c413d7366 |
| M0.2 迁入目标模型，生成 schema/client，API 错误、CSRF/host/幂等接口 | review | [#11](https://github.com/kl3574/Learning_Workbench/issues/11) | 401e0819b61f33ee918dbe0d739b686c413d7366 |
| M0.3 需求追踪与 ADR，内容哈希规范、迁移机制 | review | [#12](https://github.com/kl3574/Learning_Workbench/issues/12) | 401e0819b61f33ee918dbe0d739b686c413d7366 |
| M1.1 课程内页式三栏 Shell、紧凑四入口、上下文目录、状态条、标签 | review | [#13](https://github.com/kl3574/Learning_Workbench/issues/13) | 1c5963d058e56fc36eec378ee3a7f67d665f2307 |
| M1.2 可访问分隔条、折叠、焦点、快捷键、命令面板 | review | [#14](https://github.com/kl3574/Learning_Workbench/issues/14) | 1c5963d058e56fc36eec378ee3a7f67d665f2307 |
| M1.3 ViewContext/ContextBridge、按对象保存草稿与会话 | review | [#15](https://github.com/kl3574/Learning_Workbench/issues/15) | 1c5963d058e56fc36eec378ee3a7f67d665f2307 |
| M2.1 SQLite/blob、精确版本、原子文件、对象读取 | review | [#16](https://github.com/kl3574/Learning_Workbench/issues/16) | f304193f95461ebc3bdc60d6661c7b80f493cb1d |
| M2.2 MD/TXT/HTML/learnpack 导入暂存和确认 | review | [#17](https://github.com/kl3574/Learning_Workbench/issues/17) | fb2bb033060f8aaacb59e1a81c9826c65509f343 |
| M2.3 PDFtext/DOCX 提取隔离、低保真诊断 | review | [#18](https://github.com/kl3574/Learning_Workbench/issues/18) | c7bcd6c8e511e2fe31e3739da9718f276fbfc0cd |
| M2.4 Reader/LaTeX、例题锚点、笔记、阅读位置 | review | [#19](https://github.com/kl3574/Learning_Workbench/issues/19) | 4e53ce5e73b61650f93c1ea769f3e3143031f29d |
| M3.1 题面/私有答案库、练习/提示/暴露记录 | review | [#20](https://github.com/kl3574/Learning_Workbench/issues/20) | 0fc6340d33c26c9f6124ebb3d19f190709b860ad |
| M3.2 独立/辅助/开卷 policy snapshot，自动保存、并发版本 | review | [#21](https://github.com/kl3574/Learning_Workbench/issues/21) | 25501799321c621bec4999c6c684c6a13106771c |
| M3.3 单选、文本填空、数值/计算容差、人工复核 | review | [#22](https://github.com/kl3574/Learning_Workbench/issues/22) | 452138bdf70147c84108aeab382b45e6a2e42278 |
| M3.4 交卷/评分/复盘闭环，评分版本与 evidence | review | [#23](https://github.com/kl3574/Learning_Workbench/issues/23) | 40bd4298f28443ae4dff3c2eb4de987f60df4924 |
| M4.1 学习事件、概念/技能证据、路线完成 | review | [#24](https://github.com/kl3574/Learning_Workbench/issues/24) | 5bd81576a2a0e2dbb454165eb3bcde5920493b05 |
| M4.2 先修/补弱/复习/下一步推荐，接受/拒绝 | review | [#25](https://github.com/kl3574/Learning_Workbench/issues/25) | 8d4b36f57b3ace950f9d3f0e750c4810fce9b0ec |
| M5.1 ProviderPort/能力协商/服务端冻结授权/受控预算/秘密与脱敏 | review | [#26](https://github.com/kl3574/Learning_Workbench/issues/26) | 254a4ffe70dcab9db56663cc37245a33ae1495a5 |
| M5.2 检索权限、中文 FTS、来源和修订哈希 | review | [#27](https://github.com/kl3574/Learning_Workbench/issues/27) | 69e54478ae3c3604a925f2cdb905ce03ddda2b8b |
| M5.3 Tutor 状态机、SSE/取消/重连/异步上下文 | review | [#28](https://github.com/kl3574/Learning_Workbench/issues/28) | 919a00532b499cff604ef2be4e90c88cc6378490 |
| M5.4 真实模型与搜索评测 | blocked | [#29](https://github.com/kl3574/Learning_Workbench/issues/29) | e982a14644317c7be12a63ec0b31c1e615c72fa6 |
| M6.1 教材/例题/题目生成 schema + 数值验证 | in_progress | [#30](https://github.com/kl3574/Learning_Workbench/issues/30) | 9d4aa2e75c0583b4752e1a2669534ef621e6c7f9 |
| M6.2 审校/发布/版本对比/影响分析/恢复旧内容 | todo | [#31](https://github.com/kl3574/Learning_Workbench/issues/31) | 未验证提交 |
| M6.3 CodexBroker/App Server、操作审批、产物清单 | todo | [#32](https://github.com/kl3574/Learning_Workbench/issues/32) | 未验证提交 |
| M7.1 全备份/学习者包/作者包/恢复预览和事务 | todo | [#33](https://github.com/kl3574/Learning_Workbench/issues/33) | 未验证提交 |
| M7.2 安全/可访问性/性能/故障注入 | todo | [#34](https://github.com/kl3574/Learning_Workbench/issues/34) | 未验证提交 |
| M7.3 独立内容审校、真实用户试用、交付说明 | todo | [#35](https://github.com/kl3574/Learning_Workbench/issues/35) | 未验证提交 |
| E1 Zotero、博客增量、QTI/LTI、部署评估 | todo | [#36](https://github.com/kl3574/Learning_Workbench/issues/36) | 未验证提交 |

## 验证边界

- spec_checks: 919a005：6嵌入/54 core/72生成/38需求/33场景/27任务/107声明路由；结构PASS不等于107条已实现。
- unit: 919a005固定Python全量1807PASS（含单元/契约/集成/安全），三个类别共享此总数，不重复累计；详见M5.3-final-python-01。
- contract: 919a005固定Python全量1807PASS（含单元/契约/集成/安全），三个类别共享此总数，不重复累计；详见M5.3-final-python-01。
- integration: 919a005固定Python全量1807PASS（含单元/契约/集成/安全），三个类别共享此总数，不重复累计；详见M5.3-final-python-01。
- browser_native: 919a005全量93PASS8.2m，包括3新增Tutor真实持久化/控制/受控Provider浏览器用例；不含生产模型验收。
- real_provider: DIRECT_VENDOR_SMOKE_PASS：2026-09-15 用户明确授权的独立 DeepSeek 最小测试，GET /models 200、单次 POST /chat/completions 200，deepseek-flash 回答合成算术题正确，实际 usage 14 input / 1 output / 15 total；无重试、无资料外发，凭据只在进程内存。PLATFORM_AGENT_NOT_RUN：真实Tutor/source现已实现并有受控链定向证据；production InputProof为空，平台实际DeepSeek/模型质量仍未验收。
- real_codex: NOT_RUN
- learning_effectiveness: NOT_RUN
- ci: 8d4b36f精确源码12/12success；PR实际checkout0c350b3与head的GitHub tree相同。两browser分别82PASS12.0m/12.1m。后续纯证据提交CI独立记录。
- m4_1_development: 开发和独立审查的所有原失败/修复、环境诊断已保留；最终源码新验收通过，不覆盖历史失败。
- m4_1_exact: 5bd8157新lint/types/spec/247web/build/74native均PASS，504源码前后相同；同SHA双workflow12checks成功。
- m4_1_layout_repair: PASS:真实412布局及焦点回归；原失败保留，限定机制归因；新74完整套件通过。
- m4_2: 1db509f固定提交七类本地门禁PASS：1197 Python/288 web/82 native；545源码前后一致。精确源码双CI12/12 success，各82 native。独立最终源码/日志/产物/11图审查PASS。待人工review，未合并；证据提交发布与后续CI另报。
- m4_1_publication_ci: 98f1701仅证据提交实际12/12success已回读；独立于5bd8157源码验收，不推定M4.2 CI。
- m4_2_publication_ci: 1db完整本地1197Python/288web/82native和精确12CI PASS已归档。42f历史证据CI为10success2backend Ruff失败（132归档错误，pytest跳过），双browser各82PASS。8d仅修Ruff归档范围，固定本地lint/spec、独立审查及精确12CI全部PASS；两workflow各243contract/440backend/527integration/288web/82native，组间不相加。PR48 ready/open/unmerged。 4ed纯证据后续CI实际12/12success，两browser82PASS11.7m/11.3m；轻回执只抽两browser日志，不重复宣称完整本地重跑。
- m5_1: PASS：254a4ff本地323web/87native及lint/types/spec/build通过；305 backend/contracts/tooling输入与原769一致，1494Python原证据沿用而未重跑。发布f0b4ce2双workflow12/12成功，各323web/87native。PR49仍draft/open/unmerged；真实供应商独立最小调用成功，平台Agent端到端未实施/未验。
- m5_1_ci: 历史e480 CI快照（原件保留，后续254修复与f0成功另记）：10success2failure，push revoke单元准备失败及PR native删除秘密后r3ACK等待失败；原观察不追认唯一因果。
- m5_1_native_repair: PASS at254a4ff：新命令及明确更正采用同owner/provider较高真实readback，ACK不伪造current；unknown原命令不变。真实受控parent-delay DELETE由r1If-Match/412变r2If-Match/200，peer抢先r3仍412再explicit新key成功；原CI只确知r3ACK等待失败，不追认唯一因果。14secret/35Provider定向unit及5native通过；同source新323web/87fullnative通过。
- m5_1_254a4ff_local: 六项实际命令PASS：lint、types(mypy125+web)、spec(54core/6embedded/106routes结构检查)、build(709modules,chunk警告保留)、323web/52files3.37s、87native6.9m。600source aggregate b00ae17d2d6e87e01aee18c0082ff1eee32c4be891d343fe4bd1b8df48417452；83完整native产物私有留存，当前阶段尚待新发布head CI。
- m5_1_ci_current: PASS：发布f0b4ce2精确双workflow12/12success；每组323web/52files、87native（12.0m/11.9m）。6push checkout f0b4ce2、6PR checkout95ff622，全部Git tree c8d7d132相同；600source与254a4ff等同。85payload原件/公开件SHA、size、全部转换与聚合root逐项核验；此CI基于规范3.0.2，不涵盖当前M5.2工作树。
- m5_2: LOCAL_VERIFIED_REVIEW_PENDING：69e5447导入入口与原Policy guard一致，原实现场景1RED→同测试1GREEN，独立Policy/保留选择及原Reader共3PASS；最终355web/58files、lint/types/build、90native7.5m通过。788非progress源逐项同Git，native仅已知PNG直接输出，82原件预存/after归档/精确恢复，原unchanged=false保留。后端代码/测试/配置相对d65未改，沿用原1673Python而非重跑。0484双CI12success（各88browser）另列；新修复head CI实际结果如下；旧ab6失败保留。 b895实际attempt1双CI12/12success，两个browser各90PASS11.0m/10.8m；push b895、PR merge f8c699e 同tree dff2a3f6但不同commit；12原日志及零artifact已回读。不改旧ab6失败。
- m5_1_358bf5d_historical: LOCAL_FIXED_SOURCE_PASS：769原本地1494Python/314web/85native保留；6c首次CI10success2frontend FAIL，0c修refresh测试并五门禁PASS。e480新CI的PRfrontend314PASS，push不同revoke准备测试313PASS1FAIL，原件保留。358bf5d仅加7行等待journal/ACK后完整回读，600输入before/after/Git相同，lint/types/spec/build与314web/52files新PASS；原RED/观测/两次guard mutation反例保留，production原字节恢复。358本地未重跑backend/native（输入未变），新提交未推送、远端CI NOT_RUN；真实Provider/Codex/学习效果未验。
- m5_2_input_coverage: 补证PASS：同f9新Python02实际1663PASS/2依赖弃用警告/273.45s，427声明输入与Git及before/after一致，含6个顶层helper；新spec03对430输入实测PASS，另含3个派生docs。Python02不追认这3个docs运行前快照，其内容由套件generate(check=True)及独立spec03核验。原01的1663PASS/421绑定和两条遗漏审查原件保留。
- m5_2_ui_review: 两处修复有界闭合：同一合法11case在原逻辑快照7FAIL4PASS、修后同测通过，完整检索23web/5filesPASS。相同本机命令/ACK候选可恢复，不同身份/正文/ACK冲突保持拒绝；安全读取失败禁止父链离开。B独立源码/原日志/hash回读无新增阻断，未冒称其另跑测试。默认Reader scope误用practice的独立原RED/GREEN另保留。
- m5_2_native_development: native04实际1PASS13.5s，root独立看1440/390图，完整r1原文/currentr2/未审与历史warning可见；root另存原04附件。native02的两图和响应附件曾因03测试输出目录误配置被覆盖，原02源码/receipt/log保留，丢失附件明确不可恢复；03产物只归03，04为新正确目录与实际视口内正文截图。不得说所有早期附件仍完整。
- m5_2_ci: FAIL：3dd75f0 push34957539421与PR34957746128均completed/failure；两workflow合计10success/2failure，各browser 87PASS/1FAIL（10.7m/12.9m）。同一historical Reader首个真实r2页面的.real-reader断言5000ms element(s) not found。旧CI未上传DOM/截图，artifacts实际为0，根因未知。六push checkout3dd，六PR checkoutb945694，全部tree c4c5dfd7相同；原12日志与精确回读已保留。
- m5_2_reader_diagnostics: DIAGNOSTIC_ONLY：仅四处测试/CI观察改动，保持原goto、5s expect与其余测试字节。原案例本地1PASS/7.7s，独立冷恢复对照2PASS/13.5s均未复现。新增helper三个受控边界通过；实际带helper正常路径1PASS/7.8s；合成GET阻断运行真实exit1/1FAIL，原5s断言重抛并生成JSON/页面上下文/截图，只验证诊断路径。初始私有ESM harness失败保留；诊断两等待各250ms非硬实时。诊断改动已实际发布73d65af并回读PR50；73d新CI已终态失败，GitHub实际failure artifact上传step success、ZIP digest/下载/安全枚举3文件及真实JSON/PNG已核，诊断能力已实际验证，未宣称产品根因已修复。
- m5_2_ci_diagnostic_head: FAIL：73d65af精确双workflow最终10success/2failure。push34961802654 frontend345PASS1FAIL、browser88PASS9.6m；PR34961806202 frontend346PASS、browser87PASS1FAIL13.2m。PR仍同Reader首5s断言失败，真实JSON显示known策略后Reader loading，小节/outline两GET在5.4s观察结束仍未response、未发block GET。原12日志/checkout同tree已核；不能据此断言服务端、数据库或浏览器的具体延迟层。
- m5_2_policy_repair: LOCAL_FIXED_SOURCE atc83b1d0：条件性慢response/poll饥饿受控原6例4FAIL2PASS；coalesce候选6PASS但新挂起反例2FAIL6PASS，被否决保留。最终明确权限epoch+已完成request序号，8例PASS；独立静态审无新增阻断。并非73d Reader loading失败原因，该实际现场不在Policy unknown。
- m5_2_recommendation_navigation_repair: LOCAL_FIXED_SOURCE atc83b1d0：真实DOM首enabled点击可被迟到passive cleanup取消；同无插桩两例1FAIL1PASS→2PASS，同永久test1FAIL→1PASS。仅guard重置改layout effect，原guard函数/原7Panel断言及5种延迟失效负控不变。推荐29例PASS及独立review无新增阻断；原CI没有click时序，未认定唯一因果。
- m5_2_c83_gates: LOCAL_FIXED_SOURCE_PASS：c83b1d0完整355web/58files、lint/typecheck/build及88native/7.6m均PASS。五门禁785个声明输入before逐项同Git；四项before/after一致，native仅已知测试输出PNG变化，原unchanged=false保留且两图归档、精确hash保护恢复。初次恢复命令在完成恢复后因系统Python datetime.UTC写回执失败，后以项目Python真实读回；未冒称第一命令成功。独立终态读回已完成。仅此代码与命令范围，不宣称当前后端修复已测或远端CI通过。
- m5_2_reader_lock_profile: MECHANISM_OBSERVED_NOT_CI_REPRODUCTION：真实累计合成数据库候选副本中一次RecommendationWorker no-work检查持写锁169.81ms；实际Content lesson/outline BEGIN等待178.69/228.71ms，返回均正常。原库/785源码不变，零blob读取；候选库有14精确fixture refs但缺随机全套artifact绑定，不是CI数据库。新建小库与累计库分别保留；线程SQL单时钟核验，CPU profile跨线程不误归因。无人工睡眠/数据放大/断言超时改动，未复现数秒等待。
- m5_2_worker_repair: FOCUSED_PASS：最终生产734e19c3与test709dc3e0；同test旧逻辑3FAIL→新3PASS，另7负控未在此选择运行。完整新10+旧29相关integration共39PASS/2原警告；owned Ruff/mypy通过，原writer/catch后缀逐字相同，D独立8完整run读回无阻断。B786清单为原785tracked+owned新test，不含当时root新增untracked ADR，未追认全仓不变。red01/02 harness问题、green04错误历史catalog期望与最终同bytes闭合均保留。
- m5_2_d65_gates: LOCAL_FIXED_SOURCE_PASS：d65e08e新完整Python1673PASS/2依赖弃用警告/291.76s，native88PASS/7.4m，完整Ruff、mypy133、spec均PASS。五门禁787before逐项同Git，四非nativeafter全同aggregate fcc585248ac016f6817d380962eb391b8fea3294ec23e154a287460815fdde02；native仅已知直接输出PNG改变，原unchanged=false保留，82界面文件预存原件、实际after归档后按精确hash恢复。前端c83的355web/58files、lint/types/build依377保守执行输入同字节与全Git仅三源变更的独立回读沿用，不称重跑。后续发布ab6真实双CI11success1failure另列；不能用本地通过抹去原失败。
- m5_2_current_publication: LOCAL_READY：69e5447源修复固定本地门禁通过，本次进度/证据提交推送后核确切head，不先称发布或新CI成功。
- m5_2_ab6_ci: FAIL：ab6c27b精确push34968882564/PR34968887070双CI终态11success/1failure。push browser87PASS1FAIL13.6m，PR browser88PASS12.5m；其余10组成功，各frontend355、backend576、integration654、spec456（组间重叠不相加）。新失败是reader.spec.ts:209私件撤权用例的导入前置，:216等待不存在dialog的解析格式时总60s预算耗尽，未进入上传/撤权/下载断言。12实际checkout分别ab6/a327ee75，同tree7af20e913e503c89aa8a423a5399a7f27360c346；真实2附件和原日志已核，点击时策略分支原因未证。
- m5_2_ab6_import_opening: READONLY_DIAGNOSIS：实际两附件显示无Import dialog和Shell策略拒绝提示。唯一警告源openAux在subjectLocked时return；顶部导入始终enabled，UI saved与Policy known不同步。源码/原附件独立审查已核；点击当时unknown/暂败/真实independent未区分，受控实验和修复NOT_RUN。 后续同源受控RED/修复GREEN及原例通过见m5_2_import_admission；旧点击时证据限制不变。
- m5_3_implementation: 历史开发记录，当前结果见m5_3_local/m5_3_001_ci：IMPLEMENTING_NOT_ACCEPTED：已有e088分支保留history并FF69e5447；隔离工作树及外层采用唯一规范3.0.4，core54/0001/F.1不变。DTO/Provider受检输出及真实Tutor owner/UI正在实施，尚未整链验收。无生产InputProof注册，平台Agent真实模型端到端NOT_RUN。
- m5_2_0484_ci: ACTUAL_PASS：0484 push34972052054/PR34972056900均attempt1成功，12/12success；各browser88PASS（12.5m/9.2m），12实际checkout同treef9156ba8，push0484/PR83374449不是同commit，真实artifact均0。相对ab6仅97progress路径，此PASS不算源修复。
- m5_2_import_admission: CONTROLLED_RED_TO_GREEN_AND_FINAL_GATES_PASS：原UI saved/Policy unknown真实响应hold/release复现guard拒绝，修后disabled，无自动重放；新增真实independent start/abandon保留dialog/file/format负控。focused03测试locator错误和active污染保留，final改own RestartRuntime隔离。原Reader字节/60s不变，未认定旧CI唯一原因。
- m5_3: 历史开发记录，当前结果见m5_3_local/m5_3_001_ci：IMPLEMENTING_NOT_ACCEPTED：真实Thread/Run/Jobs/Context/Provider source及7条HTTP/SSE已实现。受控loopback完整Provider链、恢复/取消及原回执校验定向通过；根12项真实Practice/assisted/复盘Context通过，旧ACK缺失消息2项RED修复后同case+相关组34PASS。浏览器本地prepare/空生产proof诊断/cancel/reload1PASS；受控模型浏览器链已到真实completed，移动布局测试修正中。Practice AI帮助事实和坏Job公平性修复仍在测试。未固定整阶段门禁/发布M5.3；平台DeepSeek E2E仍NOT_RUN。 后续真实浏览器lostACK同key回放、openbook跨页清正文已过；安全停止GET jobs实证500，正在修契约投影，第三native未通过。练习AI帮助11项和有界调度24相关项已实际通过，不能替代固定全阶段验收。
- m5_2_b895_ci: PASS：attempt1 push34977114033/PR34977119117共12success；各90native；原12logs与实际checkout/tree均核。
- m5_3_local: LOCAL_VERIFIED_REVIEW_PENDING：固定919a005实跑1807 Python/328.07s、383 web/64files、93 native/8.2m，ruff、mypy148源、web lint/build及规范6嵌入/54core/72生成均PASS。838非progress输入逐项与Git一致；native仅4张已有PNG直接输出改变，44个顶层UI原文件预存、after归档及精确hash恢复，原unchanged=false保留。三新增浏览器用例包含实际SQLite/HTTP/IndexedDB/Policy与test-only loopback Provider；生产ProofRegistry仍空，真实DeepSeek平台E2E、外部搜索、Codex与教学效果NOT_RUN。原失败和修复回执完整保留；70b0278后续CI真实失败另见m5_3_ci，原固定本地PASS不覆盖该失败。
- m5_3_ci: FAIL：70b0278 attempt1双CI实际11success/1failure。push34984643765 browser93PASS11.1m；PR34984703682 browser92PASS1FAIL14.8m。原Tutor批准后completed heading在5000ms内未出现，实际上下文仅证明UI queued；backend当时状态和流时序未知。12原日志、两失败附件及相同tree/不同commit核验保留。
- m5_4_targeted: IN_PROGRESS_LOCAL_SOURCE_FIXED：64b5db9包含精确endpoint/模型/格式/有效性proof绑定与Responses none；定向80+factory1通过，五项全仓静态PASS；官方参考5流47事件实跑，terminal role真实14PASS1FAIL后同15+旧29共44PASS。独立审查通过。官方完整转换计数13输入、15外层拒绝及错误词表实际负控另列离线证据，不能证明托管API等价。850源逐Git/blob/mode绑定全量Python实际1838PASS/349.75s/2依赖弃用警告、前后相同；生产proof仍空，真实平台DeepSeek/搜索/质量NOT_RUN。
- m5_4_offline: LOCAL_OFFLINE_ONLY：官方PyPI wheel11367229bytes总SHA781880…经部分下载续取实际完成；v1失败保留。v2禁网13官方完整转换/计数及重复token IDs通过，15自写严格入口反例拒绝；4实际官方行为controls、1旧digest-only检查分列，新增wrong-pin真实执行在import前拒绝。4889声明输入前后同。native报告0.1.0/distribution0.1.1；二进制构建与托管API等价均未证明。
- m5_4_python: PASS：64b5db9固定850全部非progress源逐Git blob+mode匹配；完整1838PASS349.75s/2依赖弃用警告，before/after同aggregate d1af15efb6b6cd72145f52cf814c530cda0a6a9b37f07ab3dfa1981368e00247。不是生产模型、浏览器或整阶段验收。
- m5_3_diagnostic_publication: PUBLISHED：PR51实际head0010699，新增e30c519五诊断/CI文件，draft/open/unmerged。远端ref、PR head、PR正文及Issue28正文实际回读相同；该head双CI已回读11success/1failure，详见m5_3_001_ci。
- m5_4_web: PASS：固定e982a146上的web lint/typecheck、64文件383tests、build及spec72生成检查实际exit0；各852非progress源在执行前后均逐Git匹配且同aggregate addcdf8efae9ca0db0de80dceb51060535e1c4d497225b3f6774d6976cd045a2。build原大chunk警告保留；94项native实际PASS8.1m，原unchanged=false的4PNG在44顶层UI原件/after保全后按hash恢复，当前852源逐Git相同。Python1838是在64b5db9执行，未称在e982重跑。
- m5_4_native: PASS：e982a146实际94项/8.1m，ordinal1..94各一次，原5s业务断言未放宽。44顶层UI前后原件保全；仅4已有直接输出PNG改变，原unchanged=false与after aggregate保留，精确guard恢复后852源逐Git/blob/mode一致。Root已读取本轮1440/390 Tutor实际合成截图，不推断真实模型或旧CI失败原因。
- m5_3_001_ci: FAIL：0010699 attempt1双CI终态11success/1failure。push34991095035 browser104455641488实际93PASS1FAIL14.4m；PR34991097477 browser104455650410实际94PASS10.8m。原第三Tutor completed断言仍5000ms。新单Node观察时钟记录completed DOM在断言开始后4779.307ms、失败冻结5002.232ms；post读取真实Run completed seq6/job r6，受控请求1received/1validated/0invalid。框架error-context仍queued，PNG已见合成回答；不能把不同采样时点合并。DOM answer_present包含占位，不表示真实回答；safeRun读取另有真实answer。实际12logs、4失败artifact和checkout同tree已核，原70b失败同样保留，尚未认定根因或修复。
- m5_3_completion_diagnostics: DIAGNOSTICS_IMPLEMENTED_NOT_ROOT_CAUSE_FIXED：e30c519仅5个测试/CI诊断文件，产品/原三case业务断言/5s不变。诊断自己的部分回读丢失1RED→同test1GREEN；原第三case加被动观察1PASS10.9s，真实queued GET保留至同Runcompleted后原样交付对照1PASS11.9s；均未复现原CI。No-tests-found、ESM及adhoc类型解析前置失败保留。新诊断CI待实际发布运行。 以上为001发布前历史；该head实际11success/1failure另列m5_3_001_ci。
- m5_4_publication: PUBLISHED：81d2b92公开分支和PR52 draft/open/unmerged已回读；该head双CI终态11success1failure，详见M5.4_exact_81d_ci。不是全部CI通过。
- M6.1_local: LOCAL_FIRST_SLICE_VERIFIED_FULL_STAGE_INCOMPLETE：80986ea固定903非progress源。实际1927Python PASS1ENV SKIP396.73s/2依赖弃用警告、401web PASS72files、96完整native PASS8.3m；Ruff全仓、mypy162、web lint/types/build和spec75生成均PASS。八非浏览器门禁逐Git/blob/mode前后不变；native仅4已知PNG直接输出变化，44前后原件保全后按精确hash恢复，原unchanged=false不改。真实7HTTP、loopback同Job授权→候选、独立数值拒绝/批准、安全取消与1440/390已验证；数值实际environment_unavailable/BLOCKED，1SKIP不是执行成功。生产proof仍空、平台真实DeepSeek/搜索/数学/来源/教学验收未通过；其他M6.1生成类型未实现，不能关闭M6.1。
- M5.4_exact_81d_ci: 11 success / 1 failure, push93+1FAIL vs PR94PASS; exact same tree, distinct commits; raw evidence imported locally
- M6.1_fixed_gates: LOCAL_FIRST_SLICE_VERIFIED_FULL_STAGE_INCOMPLETE：80986ea固定903非progress源。实际1927Python PASS1ENV SKIP396.73s/2依赖弃用警告、401web PASS72files、96完整native PASS8.3m；Ruff全仓、mypy162、web lint/types/build和spec75生成均PASS。八非浏览器门禁逐Git/blob/mode前后不变；native仅4已知PNG直接输出变化，44前后原件保全后按精确hash恢复，原unchanged=false不改。真实7HTTP、loopback同Job授权→候选、独立数值拒绝/批准、安全取消与1440/390已验证；数值实际environment_unavailable/BLOCKED，1SKIP不是执行成功。生产proof仍空、平台真实DeepSeek/搜索/数学/来源/教学验收未通过；其他M6.1生成类型未实现，不能关闭M6.1。
- M6.1_remote: PUBLISHED_FIRST_SLICE_ONLY：2026-09-22T02:28:53Z GitHub ref和PR53 head均bebf806，draft/open/unmerged。该head双CI合计9success3failure，完整证据与失败边界见M6.1_bebf_ci；groups仅本地，不借PR53声称其发布。
- M6.1_next_precheck: IMPORTED_UNCOMMITTED：38 focused/145 Import 的已验证提取和脱敏原证据精确移入groups-active；903/905输入与该测试版本同字节，仅采用后的规范/端口不同。尚无新组生成或3.0.7全门禁通过结论。
- M6.1_group_implementation: LOCAL_DEVELOPMENT_PARTIALLY_VERIFIED：3.0.7；实际6新增HTTP、93已注册/119声明路由，76生成文件结构PASS。纯DTO/构造138PASS、Content targets44PASS、prepare/Provider11PASS、cancel+revocation4PASS、新HTTP3PASS/旧2PASS、numeric24PASS各自独立范围。组数值实际bwrap BLOCKED，未称隔离计算成功。前端接线后原18Authoring、web lint/types、Ruff、mypy177 PASS；新组浏览器与最终全阶段门禁待验。
- M6.1_group_contract_development: 原609 PASS/94 FAIL165.41s保留。测试按3.0.7明确补6路由和两个封闭具名联合；新API投影96PASS92.59s，逐分支拒额外字段且限定旧/组variant。运行中新增3个无关前端/fixture测试源，before/after变化如实保留；不作固定全仓门禁结论。
- M6.1_799_ci: FAIL：79908fb push35676551352/PR35676944952各5success1browserfailure，各95PASS1Tutor FAIL；原:195 completed heading5000ms缺失，两Authoring通过。PR实际checkouta08bb873与head同tree，不同commit；原日志/2ZIP/诊断/源码及精确派生映射已独立核验并导入。
- M6.1_799_local_diagnosis: NO_REPRODUCTION_NO_FIX：固定799隔离树原Tutor单例3PASS，原5000ms未改；2完整后端测量(12616/12049事件、0dropped)，第一次backend export缺失保留。51公共文件/50原始派生/12Git源码及3分析输出字节由root独立重放核验；本机争用不构成CI根因，未作产品修复。
- M6.1_bebf_ci: FAIL：bebf806 push35677956691为4success/2failure；browser94PASS2FAIL（Tutor原:195 5秒未见completed、grading-recovery初次结果GET409预期200），integration763PASS1FAIL1SKIP（并发cancel窗口lease_until+312ms，未证明cancel改lease）。PR35677959449为5success/1browserFAIL，95PASS1Tutor FAIL；integration764PASS1SKIP。12jobs实际checkout分别bebf/merge5579332，同tree a7f63f5不同commit；两个Authoringcase两run均PASS。post_assertion.run.state=failed仅诊断read失败，不是实际Run.status；没有Run.value。57文件/56原始派生/13实际Git及2ZIP全部成员由root独立核验，不追認根因。
- M6.1_group_web: DEVELOPMENT_PASS：新增30项首28PASS2FAIL揭示workspace/Policy变化后late数值preview ACK仍写私有plan入IDB；原用例保留，最小scope guard后新31+旧11共42PASS，安全cancel迟到ACK正控保留。当前937声明输入前后同字节：完整432web/74files与build实际PASS，bundle体积警告保留。新2native已实际通过，非固定整阶段门禁；独立review与数值决定原ACK补证仍进行中。
- M6.1_group_history_review: REPAIRED_DEVELOPMENT_PASS_INDEPENDENTLY_REVIEWED：原干净RED12FAIL2PASS13.92s，旧/组preview/read/approve及原ACK replay/worker prebegin未核Provider bytes；接入实际Authoring owner.verify_history，原conn/事务核原Provider产物且再绑定candidate，safe Job/cancel仅control历史。新18PASS18.16s含4个缺owner failclosed，938输入前后相同。另6旧/组numeric+HTTP文件43PASS92.03s、Ruff全仓/mypy177 PASS。尚非固定提交全门禁；原审查P1及RED原件保留。 独立修复复审未见新增阻断；不替代最终固定源码门禁。
- M6.1_group_native: DEVELOPMENT_PASS：新增2条lesson/practice_set原生15.5s；旧2条Authoring回归12.7s。旧02字段declined/approved只是pending preview ACK，原件保留；新07教材单例1PASS10.7s补齐实际decline/approve ACK及declined GET。459声明输入前后相同，strict TS8输入PASS。实际numeric environment_unavailable/BLOCKED exit1。root核155raw/23receipt/4Git PNG及新390公式图，108公开文件导入；不借历史结果验证后续history修复。
- M6.1_group_storage_review: REPAIRED_DEVELOPMENT_PASS_INDEPENDENTLY_REVIEWED：永久新7RED32PASS保留；修复后60PASS（40组commands/hooks+20既有DraftStore/Authoring）及types，938输入稳定。测试使用真实hook/DraftStore代码和fake-indexeddb事件，非浏览器原生竞态证明；覆盖等待load、GET/PUT事件准入前失效和显式commit后撤权保留合法ACK，安全cancel及原key回放保留。独立事务设计按W3C committing不可撤回、complete才持久化成功；三生产文件最终修复review未见新增阻断；全量浏览器仍待验。
- M6.1_group_fixed_gates: 62d3b1af固定938源前后/Git一致：Ruff/mypy177、web lint/types、441web74files4.54s、build和spec76生成均PASS。完整Python实际2161PASS1FAIL1ENVSKIP524.78s：唯一失败为test_spec_catalog旧len113，3.0.7已声明119；root已按六条明确group路由更新断言，focused catalog实际4PASS1.13s。原FAIL保留。该提交native NOT_RUN；先补assessment UI、三root安全取消/真实重启和五题型/私解索引隔离覆盖，再新提交完整门禁。
- M6.1_group_task_sync: 实际发布后36 Issue body逐字匹配当前state与原body保留规则；9 milestone身份/标题/状态不变；PR54草稿，未关闭Issue或merge。
- M6.1_group_native_completion: DEVELOPMENT_NATIVE_PASS：三根lesson/practice_set/assessment实际3PASS37.7s。每根同SQLite新API进程读取原Job/plan/完整candidate和question私解；前进程1次loopback/后进程0新增分别记录。撤权前正文/私解可见，实际learner后403及清空，第二无consent Job取消真实丢ACK后同key/body回放与当前GET一致。assessment explicit Concept-only、两modes/600s和成员独立decline/approve已实走；lesson/assessment numeric实际environment_unavailable/BLOCKED exit1。root重核3原JSON并看390题面/私解图；限定459输入稳定，未称全固定提交门禁。
- M6.1_group_backend_completion: DEVELOPMENT_PASS：五题型同组受控Provider→SQLite→完整私解/质量记录；3真实评分不兼容响应拒绝留原输出和plan，零candidate；3根已消费唯一Provider结果后人工过期lease、新owner恢复唯一candidate，再全新实例回读零新增dispatch。实际ready索引有公开哨兵命中正控，全部物理scope/generation/chunk/FTS只含已有公开block；私解哨兵无索引，Content/Import/review表未增加。新增7+原5共12PASS12.36s，939前后同；原测试预期错误3FAIL及修复另存。新2文件mypy/Ruff通过，非OS崩溃或真实供应商。
- M6.1_group_9d4_gates: LOCAL_GROUP_GATES_PASS_NOT_PUBLISHED_NOT_ACCEPTED：固定939源码9d4aa2e；Python2169PASS1环境SKIP，web441PASS74files，完整native99PASS9.1m，Ruff/mypy177/lint/types/build/spec76均通过。native实际改变4PNG+1缩放JSON，44前/44后文件保留；精确恢复后939全部匹配固定Git。三根生成/授权/真实进程重启/权限锁/安全取消，五题型与私解索引隔离及checked-result恢复有定向补证。仅受控loopback Provider；真正隔离算术BLOCKED，平台DeepSeek E2E及教学质量NOT_RUN。原62d3失败和PR53 CI失败保留。
- M6.1_group_publication: VERIFIED：PR54 draft/open，35c5f26 head/branch/body实际一致；依赖PR53/bebf，未merge/关闭Issue。
- M6.1_group_pr54_initial_ci: 35c5f26初始CI读取：push35686100865、PR35686102890均in_progress，各backend/frontend/security-publication success；browser/integration/spec-contracts仍running。仅初态，非全套终态。详见M6.1-group-pr54-initial-ci.json。

## 阻塞与待决项

- M5_3_CI_TUTOR_COMPLETION_OBSERVATION_FAILED: 70b与001均实际11success1failure；001在同Node时钟4.779s已观察completed、约5s仍断言失败，具体轮询/交付原因待受控复现。不是已修复。
- PRODUCTION_INPUT_PROOF_NOT_ESTABLISHED: 尚未建立当前托管模型完整请求格式的exact/严格upper-bound证明；已有官方编码资料允许继续离线工程审计。这是工程/证据缺口，不是权限或缺凭据。
- M61_NUMERIC_SANDBOX_ENVIRONMENT: 实际封存完整运行闭包的bwrap启动被本机AppArmor拒绝EPERM；普通宿主路径对照不构成封存闭包验收。未修改系统profile，未回退普通进程；真实隔离数值完成/取消尚未验收，其余本地工作继续。

许可证待所有者选择。真实 Provider、Codex 和学习效果分别验收；接口或结构检查不代表业务完成。
