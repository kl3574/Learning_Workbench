# ADR 0003 — 本机运行、安全会话和 SQLite 基线

- 状态：已实现的 M0 基础设施；Workbench 保存接口为 M1.3 的基础支撑，不能据此宣布 M1 全部完成。
- 唯一规范：`PRODUCT_DESIGN.md` 3.0.0，第 7、9、11、14、17、20.2、20.4 章及附录 A—C。
- 需求：R-16、R-26、R-29、R-34、R-36、R-38；M0.2、M0.3，后续 M1.3 依赖。

## 模块和真实实现范围

`services/api/app/main.py` 只组装应用。`interfaces/` 负责 Host/Origin、HTTP、严格 DTO、安全 cookie 和脱敏错误；`application/` 按 Session、Workspace、Workbench、Runtime 分开实现用例；`infrastructure/` 提供 SQLite、迁移和本机凭证适配。Workspace 通过 `LayoutReader` 读取 Workbench 布局，不跨模块写 UI session 表。原 `config`、`database`、`security` 导入保留稳定 facade，供 launcher 和备份脚本使用。领域模型仅从规范提取，未手改。

当前仅注册 `/health`、本机会话 bootstrap/read/role/logout、readiness、workspace/preferences、workbench/session 的实际处理器。未注册导入、评分、模型或队列的假成功接口。没有运行中的可靠 worker，所以 `worker_ready=false`。提供商配置仅本地查询元数据，不联网、不验证密钥，也不表示真实提供商已经通过验收。

正文 20.4 要求 readiness 报告提供商是否配置，附录 A 的字段表省略此项。按正文与附录的共同约束补充布尔字段 `providers_configured`；其余字段保持附录名称。这是缺失的机器投影补全，不改变产品需求。

## Launcher 和浏览器接合

稳定 Python 接口：

```python
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.security import issue_bootstrap_code

settings = Settings.from_env()
database = Database(settings)
database.initialize()
code = issue_bootstrap_code(database)
# 仅交给浏览器打开同源 /#bootstrap=<code>，不打印 code 或完整 URL。
```

ASGI 工厂为 `services.api.app.main:create_app`。模块 import 和调用 factory 都不写用户目录；lifespan 才检查并初始化数据库。生产构建存在时同源托管 `apps/web/dist`。默认 API `127.0.0.1:8765`；仅接受 `127.0.0.1` 或 `::1` 绑定。`LEARNING_HOST`、`LEARNING_PORT` 可选择本机地址/端口；远程绑定立即失败。开发可明确设置 `LEARNING_UI_ORIGIN=http://127.0.0.1:5173`，只增加此精确 Origin/Host，没有通配 CORS。

bootstrap 随机量为 32 字节、有效期 120 秒，数据库仅存 SHA-256。消耗 code、建立会话在同一 `BEGIN IMMEDIATE` 事务；过期和重复使用返回 401。只有 bootstrap 在无法已有会话时免 CSRF，仍须有效 Host 和同源 Origin。所有其他写操作同时检查会话、Origin、`X-CSRF-Token`。

会话 cookie 为 HttpOnly、SameSite=Strict、Path=/；本机 HTTP 不设置 Secure，启动地址不会开放公网。会话有效期 12 小时，数据库仅存 token/CSRF 哈希；CSRF 通过 token 的固定域 HMAC 派生，`GET /session` 能刷新回读，前端不用在 localStorage 保存凭证。请求正文和原始验证错误不进入日志，统一错误只返回静态说明和服务端生成的 request_id。提供商密钥的写入接口属于后续里程碑，当前未注册。

角色切换用 `Idempotency-Key`：相同键和载荷重放原回执，不同载荷 409，副作用和回执同事务。原文 logout 字段契约仅要求空对象和 CSRF，因此保持此请求形状。其底层 `UPDATE ... WHERE revoked_at IS NULL` 原子地幂等撤销会话；注销后的同 cookie 请求按已失效凭证返回 401，不为了回执恢复认证。bootstrap 则按一次性语义明确拒绝重放。

## 存储、迁移和备份

默认数据为 `$XDG_DATA_HOME/learning-workbench`，未配置 XDG 时为用户标准数据目录；`LEARNING_DATA_DIR` 可显式覆盖，禁止落在仓库内部。目录 0700、数据库和在线快照 0600；不硬编码个人路径。

每次 SQLite 连接启用并验证 `foreign_keys=ON` 和 WAL，busy timeout 为 10 秒。初始化逐项校验已应用迁移的原始字节 SHA-256；缺失、修改、较新未知版本或迁移历史缺口都拒绝启动，不自动降级。SQL 通过 `sqlite3.complete_statement` 切分并在一个写事务内执行，因此 trigger 正文不会被错误按分号拆开。新迁移失败回滚 DDL 与迁移回执。当前直接应用附录 C 的 `0001_baseline.sql`，无需伪造第二个迁移版本。

已有数据库迁移前使用 SQLite online backup API，在持有写入锁时以单独读连接取得一致快照，不复制活跃 `.db` 忽略 WAL。快照完成后关闭目标连接，调用方可以立即读取或切换 journal mode；备份失败阻断迁移。根 `make backup` 的打包/凭证清理属于独立脚本，其测试与本 ADR 的原始一致性快照测试分开记录。M7 的恢复预览、恢复新工作区及完整 blob 清单验收尚未由这些基础设施证明。

Workbench 的 session 行在工作区首次初始化时创建，GET 不生成学习数据。PUT 先严格校验完整快照，以数据库 `WHERE revision=expected_revision` 原子比较后递增；竞争写入只有一个成功，其余返回 412，保留先提交的快照。Workspace 偏好有独立 revision。快照不接受成绩等未知字段，不创建缺失内容对象；缺失引用和精确 revision/hash 原样保留，由前端显示未解析状态。核心 WorkbenchSession 没有额外 `unresolved` 字段，未为此修改原模型。

Workbench 快照可能含选文，因此有活动独立测试时读取/保存该快照返回 `ASSESSMENT_ACTIVE`；安全布局投影仍可读，作者切换不会绕过工作区 guard。这只证明当前端口的策略基础，不能代替未来所有学科端点和流式竞态的完整测试。

## 验证与未运行范围

实际运行命令：

```text
uv run --frozen pytest -q tests/security tests/integration tests/unit/test_backend_database.py tests/unit/test_backup_command.py
uv run --frozen mypy services/api
uv run --frozen ruff check services/api tests/security tests/integration tests/unit/test_backend_database.py
```

测试使用临时真实 SQLite 文件，覆盖 Host/Origin/CSRF、并发一次性 bootstrap、过期/撤销、严格字段/脱敏、角色幂等、workspace guard、跨应用重启、Workbench CAS、迁移哈希/回滚、WAL 一致性在线备份和目标连接关闭。具体数量和最终命令输出以 `progress/` 的本次回执为准。HTTPX/Starlette 测试客户端有上游弃用告警，实际执行成功不等于没有告警。

未运行：真实 worker 领取/租约、提供商连接、付费调用、完整备份恢复、评分隔离闭环。它们不因本次基础设施测试通过而标为完成；后续任务需追加真实业务和独立验收。
