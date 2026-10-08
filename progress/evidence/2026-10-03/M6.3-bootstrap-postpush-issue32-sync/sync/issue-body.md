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
当前实际状态：`in_progress`，M6.3 / AC-21 未完成，Issue保持open。唯一规范v3.0.14（已批准375e55c0），SHA256 `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`。本地会话切片只建立受限thread映射，allowed_actions=[]、三capability=false、active_turn_id=null。

后端固定df0 focused264PASS（其中bootstrap107，不相加）、Ruff/mypy250/结构80PASS；root核1365完整工程输入逐Git/前后不变及642原件/140明确候选。五个真实端点、原actor/权限/CAS/完整历史/一次消费/owner恢复已实施；完整阶段验收仍待后续。

实际固定045受限控制：真实HTTP prepare→GET→approve→GET→consume取得201/r2 ready，恰1固定CLI，0.963秒；原201ACK及同DB应用重建回放逐字相同、零新start。profile-v3保留三帧/预算/限制，四个所选schema逐字绑定离线440文件。无模型、turn、账号登录、工具、网络或学科读取。三个原真实v2unknown保持unknown、不升级或重跑。原owner文件P2已由852/31静态修复及终态文件数量回归实际闭合，不称完整隔离安全审计。

UI初始false→true写准入取消合法只读响应，受控RED复现后a480仅两文件窄修；原a2d9新nativeFAIL（准备/创建/thread NOT_RUN）和日志/截图保留。a480新native1PASS，实际browser/IndexedDB/两API OS进程/同DB贯通，五个显式原命令ACK回放字节相同，登记session/permit/finish保持1/1/1。浏览器证据不独立计OS CLI启动。

原a480完整Web1037PASS/1FAIL保留；f321仅在新回归等待写按钮实际ready，读取断言、production/native不改。f321完整Web1038PASS/145files、strict/build849PASS，17161 tracked/1376工程输入逐Git前后不变。

正式固定bd3完整native：128PASS、0FAIL、0skip、exit0、1worker/0retry、无casefilter，18.1分钟；root独立核230原件hash/23明确候选、17628 tracked/1381工程输入逐Git前后不变。Authoring/Restore实际数值environment_unavailable、Job failed、verdict BLOCKED；Restore发布409。浏览器安全路径PASS不升级物理运行。

固定dcf正式完整Python：3688收集，3683PASS/1FAIL/2setupERROR/2物理数值环境SKIP、exit1，原完整失败封存。旧备份测试期待清空reviewer actor引用与现行M7保历史合同冲突；b51仅修测试并cherry到当前canonical1843556e，原RED1FAIL、新single1PASS（包含在七文件65PASS中）、Ruff及独立静态审阅通过。没有生产/native/timeout/租约修改，65相关PASS不替代整套FAIL。

两个原setup ERROR（Provider owner single、Review guards extra_body-decision）原因UNKNOWN，正文未执行。先核源/收集/allocator/独占basetemp关联，再只读合成DB非秘密状态时间计数，观察authoring running r3/import running r2；不能推断租约丢失、UTC差值或宿主原因，不恢复/改写原实例。修订后固定184的同命令完整Python3688收集已终态：3686PASS/0FAIL/0ERROR/2物理数值环境SKIP/2既有warnings、exit0，2199.36秒。1381工程输入逐Git前后不变；root独立核全部输入/runner/log及11原件/12明确候选。无筛选/超时修改；新PASS不解释两个原setup原因。

root固定c73备份CLI四种合成Codex历史4PASS，1374工程输入逐Git，原actor/八表保留，旧cookie401、新actor不继承旧许可。它与legacy65回归不是完整M7.1真实恢复验收；私有DB/ZIP不分享。

原ad494完整Python3633PASS2ENVskip1setupERROR/exit1、native126PASS1FAIL/exit1均保留。自动检查 possible cybersecurity risk 中止的扩展安全审阅和旧native诊断为NOT_RUN，未重启或转派。完整M6.3/Broker、turn、多轮/通用审批/产物/登录/导出/工具/回导与发布尚未完成；生产托管Provider缺完整输入计量ProofRegistry，真实平台Provider NOT_RUN，非key认证失败；数学/来源/教学分别未验。

M6.3本地控制源码e91376f0568542050f11e79b2e9b729d1b7df85c已实际普通push并独立读回；PR56 https://github.com/kl3574/Learning_Workbench/pull/56 为draft/open/unmerged，依赖未合并PR55/e287。最终公开scanner17956当前文件/1096 outgoing blobs零finding；明确准入仅本切片，不宣称整平台发布。原用户checkout clean b895保留。

e913实际push37140042060与pull_request37140046223：两个backend均822PASS/1FAIL，过期测试仍要求GET /codex/sessions 为404且整个路径不注册；v3.0.14已实施POST创建，所以真实GET列表返回405。原完整CI失败/日志保留。root在独立固定db14仅修该测试，重新约束GET405严格JSON、OpenAPI仅POST、未实现turn404；完整backend823PASS/0FAIL/2既有warning，Ruff/mypy251 PASS，1382工程输入逐Git前后不变。固定修正尚未推送，远程新PASS不得提前声称。最近读回两个spec-contracts/frontend/security-publication已PASS，integration/browser仍RUNNING；整套CI不是PASS。

§6.6客户端四当前输入需求下载：独立28c真实browser保存378byte learning-task.md，四原输入逐字、无source/provider/hash，仅GET/session，dirty退出guard原值保持；真实降为learner并freshGET后零第二下载。完整Web1054PASS。两个原native selector FAIL与撤权NOT_RUN保持原件；独立增量审查指出footer误把不调用路径写成断线事实，已在196b修文案并补unknown/authorized状态回归。该最终固定源码完整Web/native正在运行，尚未整合/推送，不认定整个fallback或R23/AC21完成。

下一任务：独审并整合测试窄修，待e913两个CI实际终态保留后推送适用固定修订；完成196b客户端全门禁与独立显式候选核验，再整合。后续turn/通用审批/产物的冻结权限及DTO缺口单独复核，不借bootstrap许可。零付费模型；无merge/release/deploy。
<!-- engineering_progress:end -->
