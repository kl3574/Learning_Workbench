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
当前实际状态：in_progress，M6.3 / AC-21 未完成，Issue保持open。唯一规范v3.0.15 SHA256 b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec；4e8d4f79已获所有者批准，7820199b同范围安全减权基准澄清已纳入，不新增正文/批准权限。

公开源码仍69029bc1ab355efdbb6e0fdb8a86204c59cea71a，PR56 draft/open/unmerged，依赖PR55/e287。该源码push37170415116与PR37170416801各六job实际SUCCESS；12份完整job日志独立核push690、PR合成6692d62db971b9b46cbf118efe6f26b4e0fd3b8c，Git树同09c22a9a18b064c36a84e05f091e37cf3e76e5cd。每组backend825、contract809、integration2143/2实际数值环境SKIP、Web1058/146files、native130 PASS。首次gh run --log返回exit0但空bytes的采集失败保留，随后独立jobs日志API取得真实bytes；不把采集器失败记为CI失败，也不借CI推定真实模型/数学/质量通过。

新strict DTO fixed8da已局部342合同PASS并整合764，旧bootstrap/Provider/54core/0001不变。真实准备/安全控制/取消owner最终6f3f8107相关13files416PASS/2warnings，1403完整工程输入前后逐Git相同；四条真实新增HTTP预约Job/Run/context、冻结来源、只读控制与r3→r5取消释放，零CLI/模型/工具。原5a的取消修订、损坏成员排序、大来源正文遗漏核验、撤权交付反例与原失败分别保留，新固定来源复核不改旧FAIL。运行profile完整证明缺失时实际preparation unavailable、所有执行能力false。

当前本地主验收分支已整合后端与独审后的当前session界面，固定ff656a2fc360551f872bb0ff4ebe14d8240d82d3，尚未推送。运行实际120/声明147/未注册27，未用stub占路由。该组合Ruff/mypy259/82生成check/54core+147规范检查、完整Web1068/147files、strict/build PASS，1405工程输入前后同Git。旧当前GET拒r3的3FAIL/7PASS及一次测试typingFAIL保留；原命令/ACK decoder未改宽。

原生Chrome154、真实HTTP/SQLite/IndexedDB与明确受控bootstrap端口组合PASS：真实准备202后r3/活动turn显示、Jobs取消200后r5/null显示、原201/202ACK同key逐bytes回放、关闭浏览器和重启API后同actor与本机命令读回、零自动POST。1440/390无横向溢出。明确仅synthetic bootstrap，不是实际CLI或模型；首验收脚本收尾继承管道问题与root诊断更正保留，独立fixed02有界自有进程清理后真实exit0，不冒称旧脚本自行正常退出。

完整组合Python首次实际失败：3948收集，1939PASS/440FAIL/1568ERROR/1SKIP；临时目录Errno122 Disk quota exceeded及SQLite I/O错误记录保留，不能用子集PASS替代。相同源码已使用全新专属磁盘basetemp重跑完整3948，当前RUNNING，未提前报PASS；不删旧数据、不改源码绕测试。该固定组合完整门禁完成前不发布新源码。

下一任务：完成同源完整Python重跑、6f最终独审闭合与证据读回，公开准入后同步新源码到draftPR56并验该SHA；并行在独立树实施Provider-owned Codex完整输入证明注册缝、preview/grant/revoke/start与受控唯一dispatch。生产完整ProofRegistry仍无证明，零外发；真实平台Provider/Codex turn NOT_RUN/BLOCKED，非key认证失败。每turn至多一次模型请求，默认零工具，第二请求必须新turn/新完整许可；不是无人值守连续Agent循环。

当前数值物理环境仍BLOCKED、发布仍409，690指定CI数值产物内容正在独立读回，不借旧4ecc产物代表新run。旧完整门禁失败、两个setup UNKNOWN、三个v2unknown和自动审查中止扩展诊断仍保留，不重试或转派被拒诊断。数学/来源/教学质量、整个M6.3/Broker/AC21和完整M7仍未验收。原用户checkout clean b895未改。无GitHubmerge/release/deploy/外部模型调用，密钥未进入仓库或本轮外发。
<!-- engineering_progress:end -->
