# 固定源码完整 Python 门禁私有终态

本次原完整门禁实际 **PASS**，`actualexit=0`。实际终态：`=========== 4593 passed, 2 skipped, 3 warnings in 3081.36s (0:51:21) ===========`。

原命令仅执行一次：`uv run --frozen --offline --no-sync pytest`；实际收集 4595 项。唯一显式 runtime 环境覆盖为受控私有 `TMPDIR`，安装用 `UV_LINK_MODE` 未带入。未更改断言、数值 guard、过滤、排除或重试。

固定 HEAD `93c44303f9635067d2fae44a40986ba947e75e21`；唯一规范 v3.0.15 SHA-256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`。1565 工程文件仅排除 literal `progress/`，Git/index/live bytes/modes 前后逐项一致；before/after map SHA-256 `e97793e19953f9b6c41950cebadefc8fe2b27d9cb910565d9ad9fcd6b2144f71`。

owned recorder `39311` 和原命令 child `39317` 已无活动进程；精确两日志 `lsof` 终态为 exit1、无 holder。launcher0只代表 detached 启动，本次测试状态来自 recorder 实际 child.wait。

所有旧两次完整 FAIL、原 six cases 6PASS、旧中断5件原件均保持有限成员原始 bytes/hash。旧中断 run 无终态回执，继续记 INTERRUPTED，不改记 PASS/FAIL。

实际 skip 原因及每项原 stdout 定位保存在 READBACK.json；原 stdout/stderr 仅留本包。native、其他 tests、网络、模型、host/profile/key 探测均未由本 owner 运行；后续独立复核及 native 决策归 root。
