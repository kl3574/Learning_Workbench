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
当前实际状态：in_progress，M6.3 / AC-21 未完成，Issue保持open。现行唯一规范v3.0.15，SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec。所有者已批准4e8d4f79受控turn/逐操作审批/manifest普通Import草稿回导合同及实施；7820199b只补既有安全控制GET的减权基准、不新增接口/权限。原两P2已有独立CLOSED_STATIC复核，原OPEN报告与批准原件均保留；静态闭合不是功能验收。

当前源码69029bc1ab355efdbb6e0fdb8a86204c59cea71a已实际普通push并独立读回PR56 https://github.com/kl3574/Learning_Workbench/pull/56 draft/open/unmerged，依赖未合并PR55/e287。该修订是已批准规范、派生目录/归属、合同测试计数及证据同步；公开扫描18569当前文件/272出站blobs零finding，原用户checkout clean b895保持。

固定50ec2738结构80generated/54core PASS、168合同/单元 PASS（135.74s）、Ruff与Web TypeScript PASS，完整1386工程输入前后同Git。原147!=133的一FAIL保留，修正仅两行声明计数；147是声明，实际仍116注册、31未实现。54core、0001、普通Provider和原bootstrap DTO/ACK不变。ee905c5本地仅整合已批准提案历史，所有原门禁输入不变，不是GitHub PR合并。

两个隔离树正在strict新DTO以及真实准备Job/安全控制读回/取消实施；准备HTTP固定eae757a9真实404 RED已保存，未整合、未报功能通过。新grant/dispatch/逐操作执行/manifest回导仍待完成。每turn至多一次模型请求，工具默认禁用，工具后第二模型请求必须停止并要求新turn和完整新许可；不承诺无人值守连续Agent循环。当前690完整CI尚未验收，4ecc的成功不重标为新修订。

上一公开源码4ecc的push37165685426与PR37165687627各六jobSUCCESS，12完整日志核push4ecc/PRmerge339d5a61及同tree b97103e9；每backend824、contract808、integration2143/2真实数值环境SKIP、Web1058/146files、native130 PASS。此前完整184 Python3686/2物理ENVskip、实际045受限零模型thread一次start/零replay starts，以及四输入下载与普通Import15未审draft分别绑定原来源，不升级为新turn验收。

两次4ecc CI四指定数值artifact只读6原JSON，全部environment_unavailable/BLOCKED、发布409/PUBLISH_NUMERIC_REQUIRED，Single仍draft/published_ref=null、记录外部模型调用0。原e913两完整FAIL、DCF完整3683PASS1FAIL2setupERROR2ENVskip及ad494/a2d9/a480失败保留，两个旧setup原因UNKNOWN。未升级或重跑三个v2unknown。自动检查possible cybersecurity risk中止的扩展审阅和旧诊断仍NOT_RUN，未重试或转派。

生产托管Provider缺完整输入计量ProofRegistry，真实平台Provider NOT_RUN，非key认证失败；无proof零外发。整个M6.3/Broker/AC21、真实模型、数学/来源/教学质量和完整M7恢复均未验收。下一任务：完成固定DTO和真实准备/安全GET/cancel的局部验收与独立审阅，整合并运行适用组合门禁，同时读取当前修订CI真实结果。无merge/release/deploy/外部模型调用。
<!-- engineering_progress:end -->
