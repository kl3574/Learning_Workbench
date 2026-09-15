# 当前工程进度

本文件从 `state.json` 生成；需求仅见 `PRODUCT_DESIGN.md`。

更新：2026-09-15T12:51:44Z；规范 SHA-256：`a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8`

仓库发布：VERIFIED；Issues 同步：VERIFIED
实施：IN_PROGRESS；当前任务：M5.2；下一任务：M5.2

继续M5.2：先封真实Shell的UI已保存而Policy未就绪窗口，验证首次导入点击的拒绝机制并保留实际独立测试负控；原用例追加最小阶段时钟以区分点击时策略，不增大60s、不自动重复受限操作。证据支持后修复、重验并读取新精确CI，再恢复M5.3 Thread/Run/SSE。平台Agent仍未实现/未端到端测试。

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
| M5.2 检索权限、中文 FTS、来源和修订哈希 | in_progress | [#27](https://github.com/kl3574/Learning_Workbench/issues/27) | d65e08e3c3fd896896f7228f6099ef93b9c3362d |
| M5.3 Tutor 状态机、SSE/取消/重连/异步上下文 | todo | [#28](https://github.com/kl3574/Learning_Workbench/issues/28) | 未验证提交 |
| M5.4 真实模型与搜索评测 | todo | [#29](https://github.com/kl3574/Learning_Workbench/issues/29) | 未验证提交 |
| M6.1 教材/例题/题目生成 schema + 数值验证 | todo | [#30](https://github.com/kl3574/Learning_Workbench/issues/30) | 未验证提交 |
| M6.2 审校/发布/版本对比/影响分析/恢复旧内容 | todo | [#31](https://github.com/kl3574/Learning_Workbench/issues/31) | 未验证提交 |
| M6.3 CodexBroker/App Server、操作审批、产物清单 | todo | [#32](https://github.com/kl3574/Learning_Workbench/issues/32) | 未验证提交 |
| M7.1 全备份/学习者包/作者包/恢复预览和事务 | todo | [#33](https://github.com/kl3574/Learning_Workbench/issues/33) | 未验证提交 |
| M7.2 安全/可访问性/性能/故障注入 | todo | [#34](https://github.com/kl3574/Learning_Workbench/issues/34) | 未验证提交 |
| M7.3 独立内容审校、真实用户试用、交付说明 | todo | [#35](https://github.com/kl3574/Learning_Workbench/issues/35) | 未验证提交 |
| E1 Zotero、博客增量、QTI/LTI、部署评估 | todo | [#36](https://github.com/kl3574/Learning_Workbench/issues/36) | 未验证提交 |

## 验证边界

- spec_checks: PASS_d65e08e_54CORE_70GENERATED_106DECLARED；结构和派生一致性，不冒充106真实HTTP实现。
- unit: 1673_FULL_PYTHON_PASS_d65e08e；355_WEB_PASS_c83b1d0_CARRIED_BY_IDENTICAL_INPUTS；测试组不混加。
- contract: PASS_1DB509F_243_CI_PER_WORKFLOW
- integration: PASS_1DB509F_527_CI_PER_WORKFLOW
- browser_native: 88_PASS_d65e08e_7.4m；真实浏览器本地验收，不代表远端CI或平台Agent。
- real_provider: DIRECT_VENDOR_SMOKE_PASS：2026-09-15 用户明确授权的独立 DeepSeek 最小测试，GET /models 200、单次 POST /chat/completions 200，deepseek-flash 回答合成算术题正确，实际 usage 14 input / 1 output / 15 total；无重试、无资料外发，凭据只在进程内存。PLATFORM_AGENT_NOT_RUN：生产 source/proof 未注册、Tutor/Run 未实现；不等于 M5.3/M5.4 验收。无秘密本地原回执留在仓库外，不提交。
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
- m5_2: LOCAL_PASS_REMOTE_FAIL：d65e08e固定代码新1673Python/88native与Ruff/mypy133/spec通过，c83相同前端输入355web/lint/types/build沿用；ab6真实双CI11success1failure（push导入前置失败，PR88browser通过）。不抵消原3dd/73d失败；PR50仍draft/open/unmerged。
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
- m5_2_current_publication: VERIFIED：ab6已push exit0并精确回读PR50/ref/body，相对d65仅324progress路径；该head双CI已终态失败。后续仅证据/检查点的提交不算修复，CI按自己的head另读，不替代ab6原结果。
- m5_2_ab6_ci: FAIL：ab6c27b精确push34968882564/PR34968887070双CI终态11success/1failure。push browser87PASS1FAIL13.6m，PR browser88PASS12.5m；其余10组成功，各frontend355、backend576、integration654、spec456（组间重叠不相加）。新失败是reader.spec.ts:209私件撤权用例的导入前置，:216等待不存在dialog的解析格式时总60s预算耗尽，未进入上传/撤权/下载断言。12实际checkout分别ab6/a327ee75，同tree7af20e913e503c89aa8a423a5399a7f27360c346；真实2附件和原日志已核，点击时策略分支原因未证。
- m5_2_ab6_import_opening: READONLY_DIAGNOSIS：实际两附件显示无Import dialog和Shell策略拒绝提示。唯一警告源openAux在subjectLocked时return；顶部导入始终enabled，UI saved与Policy known不同步。源码/原附件独立审查已核；点击当时unknown/暂败/真实independent未区分，受控实验和修复NOT_RUN。
- m5_3_implementation: NOT_IMPLEMENTED / PLATFORM_AGENT_NOT_RUN：六条Thread/Tutor/Run HTTP未注册，Tutor发送永久disabled；已有草稿/固定帮助、Provider控制与内部供应商流不等于公开Run SSE。生产source/proof默认空。静态源码和生成路由逐字核验，非新HTTP/模型测试。

## 阻塞与待决项

- M5_2_CI_REGRESSION: ab6实际双CI11success1failure；push导入前置失败，未到私件安全断言，需受控定位与修复。已有d65本地门禁通过与PR浏览器88通过不替代此失败。非权限或凭据阻塞。

许可证待所有者选择。真实 Provider、Codex 和学习效果分别验收；接口或结构检查不代表业务完成。
