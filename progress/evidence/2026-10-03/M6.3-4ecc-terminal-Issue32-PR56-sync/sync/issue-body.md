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
当前实际状态：in_progress，M6.3 / AC-21 未完成，Issue保持open。唯一规范v3.0.14（已批准375e55c0），SHA256 bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144。本地bootstrap只建立受限thread映射，allowed_actions=[]、三capability=false、active_turn_id=null；不授予模型/工具/学科读取。

本轮修订源码4ecc27a883782855a6e5611d7610979e4b4b05ca已实际普通push并独立读回；PR56 https://github.com/kl3574/Learning_Workbench/pull/56 保持draft/open/unmerged，依赖未合并PR55/e287。最终源码公开准入18368当前文件/306出站blobs零finding。原用户checkout clean b895保持不动。

精确4ecc实际push37165685426与pull_request37165687627均completed/success，各六job成功。root读取12完整job日志并核checkout：push=4ecc，PR merge=339d5a61f9be9a8306b1a6851286c765c6aeb21e，官方tree同b97103e9de52ac3f1d8bcce291f1f3aa648fc5f9，PR父级e287/4ecc。每套backend824PASS/2warnings、Ruff/mypy252PASS；contract808PASS/2warnings；integration2143PASS/2实际数值环境SKIP/2warnings；Web1058PASS/146files；native130PASS。结果不相加、不反写旧源码门禁。

00cb修复UI静态挂载拦截API方法：无静态目录和有同名API HTML都返回受控JSON，未知turn404、session错误方法405。完整824本地结果与受控with-ui RED、旧db14仅无static823PASS分别保留；runtime逐1383Git输入整合到b3bb。当前CI已执行实际修订组合。

§6.6四当前输入Markdown客户端下载已整合/发布：最终066（production83daf）Web1058PASS、新native2PASS；早期196b完整129PASS单独绑定，当前4ecc两次完整130PASS已实际运行。真实390bytes下载只四当前输入、fresh会话/权限重核、dirty退出guard/原值保留；真实角色降为learner后零第二下载。另一382bytes文件由用户另行明确选择进入普通Import，input/source/artifact同SHA，15候选均未审draft，无commit/publish/Codex。root核478原件/193safe/3outer/22完整Gitmaps及最终截图。原selector FAIL、文案P2与候选预检FAIL保留，不升级为Codex生成或教学质量。

两次新CI的四指定数值artifact已只读取6原JSON，上传ID/metadata head/transport digest/size/原bytes完整绑定；四次均environment_unavailable/BLOCKED/exit1/assertions[]/output_sha256=null，发布全409/PUBLISH_NUMERIC_REQUIRED；Single closed_chain仍draft、published_ref=null。记录外部模型调用全0。未保存ZIP、不推断底层环境原因、不把browser130PASS称物理数值PASS或实际CLI成功。

原e913两CI均完整FAIL：backend各822PASS1FAIL，其他五job成功；旧过期404断言与独审发现static边界P2分别保存。原DCF完整Python3683PASS1FAIL2setupERROR2ENVskip/exit1及ad494/a2d9/a480失败均不改；修订184同命令完整Python3686PASS2ENVskip/exit0按原1381Git输入绑定，两个旧setup原因UNKNOWN。实际045受限HTTP201/r2 ready、恰1零模型CLI及0 replay starts保留；browser五原ACK跨刷新/两API OS进程同DB逐字一致不独立计CLI。原三个v2unknown不升级、不重跑。

生产托管Provider缺完整输入计量ProofRegistry，真实平台Provider NOT_RUN，非key认证失败。数学/来源/教学、完整M7恢复、整个M6.3/Broker/AC21未验收。自动检查possible cybersecurity risk中止的扩展安全审阅与旧诊断保持NOT_RUN，未重试或转派。

下一任务：同步本轮真实证据；剩余turn/逐操作GenericApproval/interrupt/manifest/普通Import归属合同已形成固定独立提案4e8d4f79，root独审后请求所有者决定，尚未批准/实施/合并/推送。新语义批准前路径继续关闭，不借bootstrap许可。零付费模型；无merge/release/deploy。
<!-- engineering_progress:end -->
