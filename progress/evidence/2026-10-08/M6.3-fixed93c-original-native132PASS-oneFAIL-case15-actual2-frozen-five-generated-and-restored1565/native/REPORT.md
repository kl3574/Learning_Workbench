# 固定源码原 native 门禁私有终态

实际原 native 门禁 **FAIL**，`make test-e2e` actual exit `2`。实际 footer：1 failed；132 passed (20.2m)。

实际运行原 133 cases、1 worker、timeout 30000ms、retry0；未加 filters/exclusions/fallback，未重复执行。wrapper SHA-256 `496dd89cd2bc09a0995636645e0b56634296d690d19c4272c88dbc3e3096e9a1`；root Python admission SHA-256 `0a864d28be7763c76e8f9fca6e84dfd780e39641f36ce0d8268be8ad1cafe415`。

固定 HEAD `93c44303f9635067d2fae44a40986ba947e75e21`；规范 v3.0.15 SHA-256 `b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec`。1565 tracked Git/index/live paths 仅排除 literal `progress/`；after-restored all_equal `True`，before/restored rows equal `True`。

已知 generated 改动 `5` 件，实际 frozen `5` 件；guarded restoration `PASS`；unknown `0`、index changes `0`。所有 frozen bytes 已核其原 raw-map SHA。未知 mutation 未覆盖。

失败 section 与实际 error 定位保存在 READBACK.json；分类仅记录明确日志文本，root cause UNKNOWN，不推断与旧 65PASS68FAIL 同因。native-output 的 .last-run.json、失败截图及上下文原件保持私有。

所有已观察 owned PID 身份均已终态；精确四 logs lsof exit1 无 holder。旧原 native FAIL stdout/stderr 及所有 top-level 原件 byte exact 保留。未写 canonical/GitHub、未调用新模型或增加 host/ptrace/security 探测。M6.3 NOT_ACCEPTED、M7 todo、numeric BLOCKED_ENVIRONMENT 边界继续保留。
