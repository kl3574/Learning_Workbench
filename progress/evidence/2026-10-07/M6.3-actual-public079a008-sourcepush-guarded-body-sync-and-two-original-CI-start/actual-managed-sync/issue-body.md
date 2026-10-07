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
M6.3 in_progress；整个 M6.3 / AC-21 尚未验收，M7 保持 todo。唯一规范 PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec。

公开分支和草稿 PR56 已实际回读 `079a008cf88b37e4517cb391503a1e7393ccf374`（2026-10-07T13:57:14.574769UTC），1561 工程输入；运行源码锚点 `d78c4d159a2831f7d5e1721a9a466ec5b3e66421`，之后仅进度证据与三个确切归档 whitespace 规则。原用户 b895 检出仍干净未改；本次为普通源码 push，没有 GitHub merge、release 或部署。

实际实现及有限验收：

- 私有 interrupt RPC 的严格配对、递归异常拒绝已实现：固定68a原120专项、290相关六文件、5静态通过；同502行原RED2FAIL与修复后GREEN120PASS均保留。
- Broker6f将两个取消入口通过具名owner绑定当前受检回调、线程、租约与持久可能发送事实；前向0036和私有v7历史相互核验。实际22专项、473相关十文件、5静态通过，原失败和源码/原阶段独立核验。仅 synthetic_peer_only、生产资格false及显式callback泵送；没有默认生产IPC或自动后台执行。
- Authoring3d只对确证已退出非零UI且所选端口冲突重试一次，共享原20秒期限；需要本ownedVite标记和HTTP，不扫描/停止未知listener。10个ownedNode行为和最终严格TS/build/5browser通过属于不同局部。原TS/list/Chrome长socket路径失败保留；最后同源仅短TMPDIR修正后5PASS，不宣称实际Vite碰撞注入或旧CI根因已闭合。

完整门禁与原失败分开：固定较早68a的原完整Python4561 collected，4559PASS、2真实数值环境SKIP、3warnings，3043.52s；1553全部输入前后一致。它不覆盖后续1561变更。更早27f原完整4433PASS/6FAIL/2SKIP仍为FAIL。旧公开1e两原CI各browser131PASS/2FAIL；原Review/评分失败原因仍UNKNOWN。单独未改1e原grading三个用例3PASS/40.8s、原firstReview唯一一次1PASS/16.4s，均1541全部输入一致；不替代旧FAIL，也未实施产品修复。评分测试202→0丢真实Job状态、Review fixture/page.request/JSONReact/exactURLpoll缺观测均如实保留。

新源码的实际原CI attempt1，快照seq3，2026-10-07T13:59:34.257827+00:00：

- [pull_request 37632662238](https://github.com/kl3574/Learning_Workbench/actions/runs/37632662238)：in_progress / 尚无终态；jobs {"in_progress": 4, "success": 2}
- [push 37632652743](https://github.com/kl3574/Learning_Workbench/actions/runs/37632652743)：in_progress / 尚无终态；jobs {"success": 3, "in_progress": 3}

以上快照仅反映该时点，不预填用例计数或整组PASS；后续只读观察同两个原事件，不重跑或取消。捕获日志exit0不等于测试成功，CI工作输入before/after未捕获时明确NOT_CAPTURED；原数值BLOCKED没有fallback，产物上传不构成已发布。

发布前实际检查458条进度/证据/归档规则、当前894变更路径与993待推对象，有限扫描0疑点；22281旧路径mode/type/blob连续性保持。原尾空格检查exit2及提交前guard错误保留；三个确切原件归档规则不裁剪测试证据、不放宽秘密扫描。私人API/raw失败载荷、ZIP/PNG/DB/profile及用户密钥未上传。

真实Agent剩余工程：默认空ProofRegistry与executor=None。完整最终模型请求字节的可信producer/checker、单次受限外发、真实App Server完整协议与受限runtime/停止回执仍缺实现/资格；现有schema、bootstrap和synthetic测试不能填补。当前0实际外部模型调用；这是工程缺口，不能把API key或旧CI当成功证明。物理数值BLOCKED、数学来源与教学验收NOT_RUN。备份保留历史而认证/许可不可执行的规范内本地工作继续核验，不能据此解锁M7。

下一任务：取得这两个新原CI的实际完整终态/原日志并处理可复现失败；继续完成规范内真实实现和可靠备份/恢复读回，保留所有旧FAIL/UNKNOWN/LOSS/环境阻塞。生产无完整证明时继续零外发，不重启曾被自动审批拒绝的主机探针。

<!-- engineering_progress:end -->
