# 既存 depends_on 的 text 编辑切片

固定提交 `316bf693e52f1ca08a675fc7671f4d9cebad3e8b`，parent `60fa2b8c18bbd3bbd4122df81bb798fd6d0a3dab`；隔离树 `m62-text-edit-dependencies-oct02`。唯一规范 v3.0.13 SHA256 `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05` 未变。

公开 text 已有精确 depends_on 时，现在可沿原编辑流程只改标题和正文。完整依赖 refs 与顺序从原完整 metadata 保留并在编辑/发布界面只读展示。原 base_material_sha256 继续覆盖完整原基准，原候选 payload/hash/ACK 解释不变；无新 DTO 字段、接口、schema、迁移或 generated 文件。本块 concepts、非 text kind、私有正文、修改依赖字段仍拒绝。

ContentService 具名只读端口核原精确 metadata/body、持久 edges、原 concept pin 和有界 DAG；DraftSource 只调用 owner 端口，发布同事务再次核原依赖与 active base 强 CAS。不从 source current 重解析引用，不重建或修补缺失边；历史归档不禁止原 ACK 读回，当前角色/Policy 仍先核。旧无依赖记录沿原分支。

固定源验证：

- `final-python.log`：170 PASS / 2 既有依赖 deprecation warnings，192.96s。命令为 `python -m pytest tests/integration/test_draft_edit*.py tests/integration/test_edit_publication*.py tests/contract/test_draft_edit_projection.py --tb=short --basetemp=<private>/tmp-final-python`。包含17新增依赖用例及旧 Edit/发布/迁移/坏历史/HTTP回归，不重复累计。
- `final-web.log`：16 files / 131 PASS。限定 draftEditor、editPublication、draftReview、reader/versionCompare，含2新增 UI/journal 用例。
- `final-web-lint.log`：strict TypeScript/noUnused PASS。
- `final-ruff.log`：5 个变更 Python 文件 Ruff PASS；`final-mypy.log`：235 source files PASS。
- `final-web-build.log`：build PASS；保留既有 bundle>500 kB advisory。
- `FINAL-INPUTS-BEFORE.json` / `FINAL-INPUTS-AFTER.json`：1045 个输入与固定 Git 字节一致、前后不变、树 clean。范围明确为 Git tracked 的 `apps/ services/ packages/ tests/ scripts/ migrations/` 和根目录文件；不包含 `.github/`、`docs/`、`progress/` 等其他目录，也不包含工具环境及 ignored 输出。因此不是 root 1275 个完整 nonprogress 输入的同一集合。

新增真实 HTTP：create/PATCH/GET/机器 Review/明确合成人审/发布，完整 refs 与顺序、source current 推进不漂移、base CAS、原 ACK，坏正文/metadata/缺边/额外边零写拒绝，role 与 independent/open_book/assisted Policy，嵌套原 Concept pin 和 archive 历史读取；实际 app Database 的 SQLite authorizer 禁止任何 INSERT/UPDATE/DELETE，正常/错 query/错 owner GET 均未尝试 DML。合成人审只是软件协议意图，不是数学、来源或教学验收。

失败原件保持：

- `http-red-01.log`：旧 guard 拒绝合法有依赖 text，1 FAIL；`http-green-01.log` 1 PASS。
- `http-red-02.log`：仅移除入口 guard 后坏依赖正文仍被接受，1 FAIL；加入真实 Content 核验后 `http-green-02.log` 2 PASS。
- `web-red-01.log`：编辑入口与发布严格 basis 拒绝依赖，2 FAIL；`web-green-01.log` 11 PASS。
- `http-04.log` 和 `python-regression-01.log`（168 PASS / 1 FAIL）是新增零写检查器的测试包装错误：将 contextmanager 当 SQLite connection，且未挂到 app 实际 Database；业务的 archive 历史 ACK 当时已成功。这些原件不删除。修正为真实连接上下文和 app Database 后 `http-05.log` 2 PASS，最后固定170回归 PASS。
- 开发阶段日志保留原运行结果，但未逐次封存完整开发源码集合；不将它们冒充最后提交上的完整门禁。最终固定门禁有前后输入绑定。

本提交 native、完整 Python/Web、远端 CI、物理数值、外部 Provider、学术/教学验收均 NOT_RUN。未整合 root，不继承 root 正在封存的 Single 完整验收。后续真正 native 用例将单独提交/封存，不能追记为本报告已运行。
