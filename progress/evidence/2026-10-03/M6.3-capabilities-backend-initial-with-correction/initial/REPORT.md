# M6.3 隔离 Codex 能力读取：后端固定回执

2026-10-03；Learning_Workbench。基线 `0ede5f94cf9bd7569e568bad15d73bc8ac26ea44`（依赖 PR55），唯一规范 v3.0.13 不变。仅本地隔离 worktree 提交，无远端变更，不碰用户原 checkout。

后端固定 `1ab169a83e9619bd529ca55ae8ef603c596432f2`，19 files；后续仅测试 `8d34b0446d2e59fbb5f9840792c9779b82fc831d`，2 files。完整路径与 patch 摘要见 SOURCE.json。后端树 `m63-codex-capabilities-oct03` 与后续树 `m63-capability-contract-checks-oct03` 均 clean。UI 和真实原生浏览器由 root 在另一组合树负责，不在本报告中宣称 UI 验收。

## 已执行结果与限制

- 固定后端源：61 focused PASS、2 个既有 Starlette/httpx deprecation warnings；14 Python 文件 Ruff PASS，mypy 241 source files PASS，78 generated artifacts check PASS。32-final-backend 的 1315 个完整非 progress 输入前后相同，包含源码/锁/配置，不是仅改动文件。使用既有 frozen venv/toolchain 只读，无安装、同步或修改共享依赖。
- `33-contract` 在 1ab 上完整终态为 **731 PASS / 1 FAIL / 2 warnings**。唯一失败为旧测试仍期待 110 个已注册路由，而实际为 111；规范总数仍 130，未注册为 19。原 FAIL 不改写。8d 仅修正确数量并明确 sessions 仍未注册，加 18 个严格 DTO 反例；`35-contract-followup` 原失败项及新测试合计 **19 PASS**。不把这些局部结果相加或改称原完整 gate PASS；最终组合完整 gate 由 root 另跑。
- 固定 CLI 的实际 Linux 控制探测通过：`25-actual-sealed-probe` 已使用同一 sealed memfd 进行校验与执行。`34-actual-http` 在固定 1ab 上使用真实 FastAPI/TestClient、真实数据库、真实固定 CLI、真实 kernel fence，两次 GET 均 HTTP 200，稳定 Broker 目录身份相同。真实结果是 available=true、authorized=false、adapter_version=codex-cli/0.160.0；三个产品能力 false。该账户事实只属于本应用的稳定隔离 Broker，不判断用户全局 Codex 是否登录。
- 同一真实 HTTP 验收中：未认证 GET 为 401 且未启动子进程；改变专用 Broker 的受检配置后 GET 503 CODEX_BROKER_CONFIG_CHANGED，未增加子进程，随后恢复原固定配置。两次成功读取及一次失败读取前后业务数据库 dump 字节完全相同（仅输出摘要，不保存 dump/database）。TestClient 是真实 HTTP 应用边界，**不是浏览器、TCP 或生产 UI 的验收**。
- 没有 thread/turn/login/model/tool 请求，没有任何外部模型/计数调用，没有读取/复制用户全局密钥、账号或 hooks/plugin 配置。没有数值、产物、教学质量、完整 Broker 会话验收；这些均 NOT_RUN。全部过程保留网络 fence，不曾用普通无隔离进程重试状态探测。

## 实现范围

仅既有 `GET /api/v1/codex/capabilities`。严格 DTO、query/body 拒绝、no-store、会话与 Policy 前后受检。未知/未验证不是 unauthorized：找到但不受支持或失败的 CLI 返回安全 503；缺 CLI 才是 available=false。探测不写业务数据库/Job/idempotency；首次运行可建立独立 Broker 运行目录和固定配置，这属于本地控制上下文初始化，不宣称整个文件系统零写。

固定 binary SHA-256 为 `12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad`，289101384 bytes。服务端把字节复制到 memfd，加入禁止写入、扩缩和再加 seal 的内核 seal，再计算 SHA；只把该描述符交给启动器，最终 execve(fd)。路径/inode 随后改变不影响执行字节，写入封存描述符被内核拒绝；测试不是仅比较版本字符串。

Linux x86_64 子进程使用 no_new_privs + Landlock ABI3 + seccomp；独立环境、工作目录和进程组；close_fds=True，只额外继承 sealed executable FD。可命名文件访问仅 Broker 层级和 /dev/null，Broker 文件不可执行；memfd 为已经核验的匿名可执行快照。禁用的 syscall 精确为 socket(41)、connect(42)、accept(43)、bind(49)、listen(50)、accept4(288)、io_uring_setup/enter/register(425/426/427)，拒绝非 x86_64 与 x32。匿名 socketpair 为 Tokio 信号处理保留，不能命名外部目标，没有继承的 socket FD。实际 kernel 测试验证内部双向匿名 IPC 及 AF_INET/AF_INET6/AF_UNIX socket 创建均被拒；本测试不声称未来任意工具执行已隔离。

只发送 initialize、initialized、account/read(refreshToken=false)。合并 stdout/stderr 预算 64 KiB、协议等待 8 秒；错误和终态都杀整个 owned process group 并 wait/reap。raw stdout/account/codexHome/stderr 只在有限内存解析，未写入日志或前端。内部明确识别 nullable workspaceRouting，不允许未知 routing 值。上游协议声明不授予本产品尚未实现的三个能力。

## 保留的失败及来源

STAGES.json 列出 34 个完整 runner 阶段；第 01 阶段另有原日志、原单一测试字节及重建来源限制收据。阶段目录名中的 green 不代表结果为 PASS，准确结果以 exit 和原日志为准。

- 01：缺失 create_app 的新适配端口，预期 RED。此首次 source binding 在实现前立即重建，已在原收据标明，不冒称有同时捕获的完整 before map。
- 02：HTTP 返回正确，但测试错误地让无关后台 worker 同时写 DB，使“全 DB 不变”失败；03 使用不启动 lifespan 的真实应用读取边界后通过。原失败保持。
- 04/06：缺 fence/projector 的测试 RED。05/07 通过当时实现。
- 08：早期任意 256 MiB 文件限制比真实固定 CLI 小；明确 unsupported，没有启动普通 CLI。随后改为真实固定 byte count。
- 09–17：有界失败/诊断，发现 Tokio 使用匿名 IPC、默认 remoteControl 状态通知、固定版本 account 返回 nullable workspaceRouting。仅记录 chunk 字节数/摘要、安全形状与布尔诊断；原始 stderr/account 从未保存。逐项调整内部适配，没有移除可寻址网络/fence。
- 18：旧 pathname exec 方案实际控制 PASS；它不是最终 TOCTOU 保证的证据。19 是 sealed snapshot 的缺实现 RED。20–23 保留 uv Python 未导出 memfd/密封常量造成的真实失败；最终使用同一 Linux UAPI syscall/常量实现，24 四项 PASS，25 实际 sealed CLI PASS。
- 27：两个权限晚变测试第一次复用不含真实 session 行的既有 assessment fixture，提前 SESSION_REQUIRED；修为真实 consume_bootstrap 后 29/32 共 61 PASS。28 mypy 的闭包 stdin 可空收窄错误保留，31 通过。
- 33/35：完整合同旧计数 FAIL 与精确后续 GREEN 如上。

每个 runner 阶段保留命令、时间、head、完整非 progress 输入 before/after SHA map 和当时改动源快照。原始阶段运行本身无源码变化；依赖锁摘要、固定提交补丁、全部私有原件摘要由 SOURCE.json/MANIFEST.json 绑定。实际测试脚本与诊断脚本由本次 manifest 绑定；不把 root 离线 schema 收据冒充本 agent 重新生成，SOURCE.json 明确原件来自 root 的 m63-app-server-protocol-recon-oct03。

本回执不包含独立审查结论。root 已另派 reviewer 对 1ab 的安全、规范与实际边界独审；结论应单独引用。

## 分享规则

MANIFEST.json 覆盖原件。SAFE_SHARE.json 是显式候选清单，唯一内容转换是精确 `$HOME` → `$HOME`；原始 SHA 与转换后 SHA 均保留。scanner 使用仓库现有规则，未更改或豁免规则，并另查实际认证头/字段值。不要 glob 复制专用 Broker、外部 TMPDIR、数据库、共享依赖、全局账号目录或后来新增文件。allowlist 外一律仍私有；原始日志没有 raw CLI/account payload，不能以此报告推导“已公开完整握手”。
