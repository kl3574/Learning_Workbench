# 原始 M6.3 后端报告的安全结论更正

原报告 `m63-codex-capabilities-evidence-oct03/REPORT.md` SHA-256 `c0254e3ca92c7562b6bd3b4d252fb155e0ab4afdc8dc8734a5dca3b02e4b5351`、原件 MANIFEST `705f991ce955b9a7e8d22ee900f7c17ae968a5f72a99d3e86cbc9ff296e4494a` 保持原字节。不得单独公开该报告并沿用其中“匿名 pair 不能命名外部目标”“只有匿名 IPC”的推断；这两项已被独立 reviewer 的真实内核反例否定。

原61 focused、真实CLI握手、真实HTTP读取和其各自来源是真实观察，继续保留。它们未覆盖匿名 Unix 数据报 socketpair 的显式目的地址，也未覆盖 SysV 标识的共享内存访问，不能推导完整安全 PASS。原公开候选清单暂 HOLD，必须与本更正及修复/独审结论同时读取。未改写扫描器或删除原失败。

独立反例包括：sendto 向现有外部 Unix socket 实际发送18 bytes；无继承 FD 的 SysV shmat 连接并读写父端合成共享段。另一个不同原因的资源缺陷是损坏为 FIFO 的 config.toml 在常规文件检查前阻塞，尚未进入协议8秒限时。它们分别保存原probe及RED/GREEN，不混称同一原因，也不声称固定CLI实际曾使用这些逃逸路径。

修复证据在本目录，实际仍仅控制探测，不拓展到模型、turn、工具或任意 shell 的验收。
