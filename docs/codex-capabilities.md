# M6.3 本机 Codex 控制状态

对应唯一规范 v3.0.13 §6.6、§12.5、附录 A 的 `GET /codex/capabilities`。本切片依赖 PR55 的已验证本地基线；不声明完整 Codex 会话、操作审批、中断或产物回导已经交付。

应用只在已认证且当前 Policy 允许的 GET 中进行探测。导入模块、创建应用和生成 OpenAPI 不创建 Broker 目录、不启动进程。GET 不写业务数据库、任务或幂等账本；探测前后重新检查当前会话和独立测试保护。

`LEARNING_CODEX_EXECUTABLE` 可指定服务端本机可执行文件；未设置时在服务端 PATH 中查找 `codex`。当前适配器只接受 Linux x86_64 的 Codex CLI 0.160.0，固定 SHA-256 为 `12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad`。版本号或文件名本身不足以通过校验。每次把文件复制到匿名 memfd，封闭写入、扩缩和 seal 修改后计算摘要，并把同一个描述符交给受限子进程执行，避免校验后替换文件路径。该内存快照不写入仓库或私有磁盘副本。

稳定 Broker 上下文位于应用数据目录下 `codex-broker/`；`home/` 是未来该 Broker 使用的身份上下文，`workspace/` 对应产品中的 `workspace_default` 沙盒根。刷新不会新建空账号上下文，不复制或读取用户全局 Codex 配置、登录、插件或 hooks。目录必须属于当前服务用户、权限不允许其他用户访问，关键目录不可为符号链接；固定配置若变化直接报错，不覆盖或重置。

子进程拥有独立环境、工作目录与进程组，只继承三个 stdio 管道和该封存的可执行描述符。启动器用 `no_new_privs`、Landlock ABI 3 及 seccomp 限制本地访问：文件访问仅限 Broker 目录及 `/dev/null`，Broker 文件不可执行；禁止创建/连接/绑定可寻址 socket，禁止 io_uring。Tokio 信号处理所需的匿名 socketpair 保留，但没有继承的 socket 描述符，且所有 socket/connect/bind 入口均被拒绝。这是本地控制探测隔离，不是未来模型或工具执行沙盒。

控制交互严格限定为 `initialize`、`initialized`、`account/read`（`refreshToken=false`）。受控超时为 8 秒，stdout/stderr 合并预算 64 KiB；原始响应只在内存中用于严格解析，不写日志、数据库或前端。完成、错误、超时后终止整个进程组并回收子进程。Linux fence 不可用时没有普通进程 fallback。

产品只返回既有严格 DTO。已完成握手才报告 available；实际 `account/read` 中 account 为 null 才报告该隔离 Broker 的 authorized=false。这不判断用户全局 CLI 是否登录，也不证明任何付费模型调用获准。找不到 CLI 返回 available=false；已发现但版本、隔离、协议或状态无法核验则返回安全 503，授权未知。协议/schema 声明不构成端到端能力证据，审批、中断、产物回导三个标志保持 false。任何 raw codexHome、账号邮箱、认证材料、路径或 stderr 都不返回。

上游依据为固定 CLI 本地产生的 JSON Schema，以及官方 [app-server 初始化与账户读取](https://learn.chatgpt.com/docs/app-server)、[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)、[关闭 hooks](https://learn.chatgpt.com/docs/hooks#turn-hooks-off)；Linux 限制参考 [Landlock 官方文档](https://docs.kernel.org/userspace-api/landlock.html) 与本机 Linux UAPI 头文件。上游协议的 nullable `workspaceRouting` 仅允许 absent/null；其他路由值暂不解释为已授权。实际证据区分受控协议测试、真实内核 fence 和真实固定 CLI 控制读取，均不推导 thread/turn/model 或产物验收通过。
