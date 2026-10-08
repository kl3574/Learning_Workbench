# Fixed dcfda8c2 complete Python gate — FAIL

固定源码 `dcfda8c270dff3e6db75011c50ffa7d6f5826512`，独立 detached checkout。唯一规范 PRODUCT_DESIGN.md v3.0.14，SHA256 `bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144`。没有修改源码、测试、共享 timeout、全局环境、progress 或 remote；没有对失败用例重跑或减少原集合。

实际命令为 `uv run --frozen --no-sync pytest tests/contract tests/unit tests/integration --tb=short`，另指定独立短 basetemp 与独立 pytest cache。范围内全部用例执行，无 `-k`、`-x` 或用例排除。启动前核对 pyproject 与旧正式 full runner；当前父任务明确要求的三个测试目录为本轮完整范围，不冒称另行执行 security 扩展、Web/native 或真实模型调用。

**终态：3683 passed，1 failed，2 errors，2 skipped，2 warnings；收集 3688 项；退出码 1。**

| 类型 | 原节点 | 原短 traceback 事实 |
| --- | --- | --- |
| ERROR / setup | `tests/integration/test_draft_candidate_owners.py::test_missing_provider_owner_cannot_reuse_registered_candidate[single]` | fixture 经 provider history 进入 `test_authoring_numeric_service.py:63`；`candidate is not None` 断言失败，实际 candidate 为 None。未推断候选未生成的根因。 |
| ERROR / setup | `tests/integration/test_review_http.py::test_review_http_write_guards_and_strict_request[extra_body-decision]` | `test_review_http.py:31` 从 drafts 查找 block 时触发 StopIteration；fixture 转为 `RuntimeError: generator raised StopIteration`。目标 guard 断言尚未执行，不据此判定该 guard 产品失效。 |
| FAIL | `tests/integration/test_review_storage_migration.py::test_actual_backup_script_can_clear_legacy_session_without_changing_receipt` | `test_review_storage_migration.py:111` 比较原 receipt 与 reviewer_session_id；第 2 项实际仍是合成 `session_review_original`，测试期待 None。这里只报告失败事实，未修改旧断言或裁定所需修法。 |

失败原始 traceback 在 python.log 的 L264–356，最终摘要在 L368–373。两次 ERROR 和后续 FAIL 第一次出现在运行中时，分别另存原日志前缀及只含路径/标记的观察记录；这些前缀不是另一次运行，也不替代完整终态日志。

环境跳过保留原理由，不计作物理 numeric PASS：

- `tests/integration/test_authoring_numeric_runtime.py:46`：`BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained`。
- `tests/integration/test_restore_numeric_actual_runtime.py:42`：`BLOCKED_ENVIRONMENT: actual sealed Restore evaluator did not return a numeric PASS; no fallback`。

两条 warning 为既有 Starlette TestClient/httpx 与 AnyIO BlockingPortal 弃用提示；原文保存在完整日志中。

## 输入与时间绑定

- Python 3.12.13，pytest 9.1.1；使用只读共享锁定依赖，`uv --frozen --no-sync`。临时环境覆盖仅作用于该子进程：私有 TMPDIR、`PYTHONDONTWRITEBYTECODE=1`、清空额外 `PYTEST_ADDOPTS`。
- 1381 个全部 tracked 非 progress 工程文件，前后均通过 `git cat-file --batch` 原字节比较，不只比较工作区 hash；没有额外未跟踪工程 probe。实际 private runner 单独 SHA 绑定。
- 全部输入前后相同，工作树终态 clean。root 的 progress 更新不影响这个独立固定 HEAD。
- runner SHA256：`fa2ad1f73aa7c0011caeb3094f0a923148e558d164fd0a84c6bdc5469b95b5a1`。
- 原完整日志 SHA256：`550d97bb81121f32b9992e3faedc4bcffa34e9d82a6368a39fefd5f64630e711`。
- pytest 用时 2249.18 秒；runner 的 monotonic 用时 2250.136 秒。两者约 37.5 分钟。
- 原 UTC 起止为 `2026-10-03T14:08:24.989322+00:00` 与 `2026-10-03T16:03:31.854622+00:00`，差 6906.8653 秒，与 monotonic 差 4656.729 秒。两套值原样保留，未归一化或覆盖。UTC 墙钟差异原因 **NOT_INVESTIGATED**，未将其宣称为两个 setup ERROR 的原因。目录沿原 oct03 名称保留。

## 封存边界

这是一次完整原始失败门禁；既有 subset 或实际 bootstrap 成功不消除本轮 FAIL。没有发起模型/account/login/turn/tool，也没有重启此前被自动检查中止的系统扩展或 UI 诊断。测试只使用现有合成/loopback fixture；未读取或复制真实用户 DB、全局凭据。

公开候选只取 SAFE_SHARE.json 显式列出的报告、runner、输入清单、日志、终态和中途观察收据。仅将原字节中的精确本机 home 前缀替换为 `$HOME`，记录原/候选 hash 与字节数；原件不变。私有 pytest 临时 DB、ZIP、key、Broker 状态和 cache 全部不在清单中。扫描只给路径/字段/原因，不输出疑似敏感值；自动扫描不替代人工来源审查。
