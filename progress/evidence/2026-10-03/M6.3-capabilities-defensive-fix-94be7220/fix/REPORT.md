# M6.3 控制探测防御修复回执

固定提交 `94be7220df926dd9bb38c775aafa07ab3e47649b`，parent `1ab169a83e9619bd529ca55ae8ef603c596432f2`。5 files：两个生产模块、两个测试文件及实现说明。原 DTO、路由、生成物、用户材料、唯一规范均不变。test-only 合同后续 `8d34b0446d2e59fbb5f9840792c9779b82fc831d` 仍是单独提交；组合应同时包含它。没有远端变更或原用户 checkout 改动。

## 最终实际结果

- `21-final-focused`：**68 PASS / 2 既有 warnings / 14.18 秒**。`22-final-static`：4 Python 文件 Ruff PASS；`23-final-mypy`：241 source files PASS。完整 1316 个非 progress 输入前后不变，随后逐项从固定 94be Git 对象读回核 SHA，全部相同。
- `24-final-actual-http`：真实固定 CLI 经真实应用读取 **PASS**。同一稳定隔离 Broker 两次 GET 200，available=true / authorized=false；三个产品能力仍 false。真实改变受检配置后 503，零新增子进程；业务数据库前后 dump 字节同摘要。原始账户、握手、stderr、认证头和数据库未保存。该 TestClient 应用读回不是浏览器/TCP 验收，不证明任何 thread/turn/model/工具执行。
- 原 reviewer 的命名 Unix socket probe，本体逐字一致，RED 实际 sent=18、父端收到；GREEN send_errno=1、父端未收到。只在外层 harness 将硬编码 child cwd 指向本隔离树、临时目录指向本任务专用目录，未改 probe 本体、没有运行或修改 reviewer 共享树。
- 原 reviewer 的 SysV probe 本体逐字一致，旧 profile 实际连接并改变父端自建合成共享段；修复后 attached=false、errno=1、父段未改变。新永久共享段回归也分别保留 RED/GREEN，资源最终清除。
- 原 FIFO probe 本体逐字一致；原独审证明需外部 writer 才结束，当前立即返回 503 CODEX_BROKER_CONFIG_CHANGED。owner 新回归在旧代码 2 秒超时、当前直接拒绝，坏 FIFO 不被删除/覆盖，无 CLI 启动。

## 精确修复范围

匿名 Unix 数据报 socketpair 本身并不限制目的地址。现在 sendto(44) 只接受目的地址指针高低两个 32 位字均为零，保留已连接匿名 peer 的发送；带间接地址的 sendmsg/sendmmsg 及收取描述符的 recvmsg/recvmmsg 拒绝。新测试覆盖真实 abstract Unix 接收方、三个发送 API、指针两个字和内部匿名通信。原 socket/connect/bind/accept、io_uring、架构限制保持。

SysV shm/sem/msg 家族通过整数 ID 寻址，不能依靠 Landlock 或 close_fds 隔离；当前明确拒绝。POSIX message queue 的单独自建队列检查受到既有 Landlock 的 EACCES，未发现新的外发；队列清除，没有因此扩写 API。

固定控制 profile 还防御性拒绝跨进程调试、内存访问和获取其他进程 FD 的入口。这是静态收紧，**对应扩展系统级探针为 NOT_RUN / automatic-review-interrupted**：root/editor 的后续运行被自动安全检查中止，状态只给出 possible cybersecurity risk。没有换线程、转派或继续执行该扩展探针。不能将此处规则存在、实际 CLI 能启动或先前测试视为该独审已完成。root 将另行检查已有代码与常规防御性测试。

配置读取增加 O_NONBLOCK，保持 O_NOFOLLOW 和先 fstat 普通文件校验，避免 FIFO 在类型核验前无限挂住。原协议错误处理增加 RecursionError，仍只返回既有安全 CODEX_PROTOCOL_INVALID；预算和请求方法没有放宽。

## 原失败与更正

必须与 ORIGINAL_REPORT_CORRECTION.md 一起读取。旧报告中的“匿名 pair 不能命名外部目标”“只有匿名 IPC”推断被独立反例否定，原61 PASS、旧真实CLI/HTTP观察仍保留，不推导完整安全 PASS。旧包原件与原摘要不修改，其公开候选清单单独使用仍 HOLD。

本目录 STAGES.json 包含24个阶段，名称 green/final 不代表通过，exit 和日志为准。

- 01：三个发送路径及 FIFO 共4 FAIL；03：这四项与相关回归共19 PASS。原 reviewer IPC 的02/04分别是红/绿观察，脚本本身正常退出不等于安全结论 PASS。
- 07/08：SysV 原诊断与永久回归 RED；09/10修复后通过。11为 POSIX mq 既有拒绝的控制，不是新缺陷。
- 16/17/18：初版“深 JSON”用2000层，锁定 Python 仍能解析，随后等待下一个响应而超时；因此这些 FAIL **不是 RecursionError 的证据**。原件保留。之后将样例改为16000层（仍低于64KiB预算），在只恢复原异常分类的受控源码上得到20的真正 RecursionError RED；21同样例得到安全503并通过。没有增加等待时间或降低期望。
- 19以及更早实际CLI成功是当时相应输入的真实观察；最终固定 source/结果使用21–24，不混淆源码。源快照、前后完整输入 maps、命令、时间、日志摘要均保留。

独立 Spec/HTTP/UI 轴原报告已通过其固定范围，路径为 `m63-spec-http-independent-evidence-oct03/REVIEW.md`，SHA `e7260cca400a9f263229407e47586908f9b3cc8fb3dfb233e9b2b33578425ab0`。它不关闭本次新修复的安全独审。最终组合完整 gates 尚由 root 负责，本报告不称 M6.3 完整交付。

## 原件与公开候选

SOURCE.json 将固定 Git、完整 inputs、原 reviewer probe 字节和外层 harness 区分。MANIFEST.json 覆盖本目录原件；SAFE_SHARE.json 列出明确候选，唯一内容转换为精确 `$HOME` → `$HOME`。原件SHA保留，现有仓库scanner不修改、不豁免，另查实际认证头值。不得 glob 原运行 Broker、数据库、TMPDIR、依赖、全局账号目录或后加文件。原probe来自独立 reviewer；本人修复回归不冒称第二次独立审查。
