# ADR 0002：契约生成、哈希和结构验证基线

来源：`PRODUCT_DESIGN.md` v3.0.0 第 9/10/20 章与附录 A—G。
规范 SHA-256：`ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c`。
本记录只细化实现方式，不新增产品需求。

共享领域类型由附录 B 的严格 Pydantic 模型生成 2020-12 JSON Schema，TypeScript 从这些 Schema 机械投影。生成器遇到不支持的 Schema 结构直接失败，不退化成 any/unknown。所有产物保存源规范版本和 hash；`generate_contracts.py --check` 检查漂移。附录 D 保留泛型接口定义，具体前后端使用生成类型绑定。

实际应用工厂不初始化用户数据，生成器通过它读取运行 OpenAPI 3.1。当前 10 个实际操作的 22 个模型生成 `api-types.ts` 和按 method/path 索引的 `api-client.ts`；调用者不能自由指定与路径无关的响应类型。会话/CSRF/错误处理由同源 transport 提供，Idempotency-Key 等操作头由生成调用签名要求。`runtime-route-coverage.json` 把实际注册与剩余 92 个未注册目标操作分开；契约测试双向核对注册与 OpenAPI，再核对它们属于规范目录。生成器不为了消除缺口而创建接口桩。这里的覆盖是结构投影覆盖，实际业务成功仍由各业务测试证明。

元数据采用 `learning-json-1` / SHA-256：对象先经过固定 Pydantic 模型验证，序列化使用 `mode=json`、Unicode 码点键序、紧凑分隔和 UTF-8，拒绝 NaN/Infinity。正文和清单校验原始字节，不在读取时换行或 Unicode 规范化。生成器与后端共用 `packages/contracts/canonical.py`。ContextSnapshot 的自身 hash 字段被排除，原请求独立计算 hash。严格 JSON 读取拒绝重复对象键。

`verify_spec.py` 每次从磁盘读取唯一规范，在空临时目录抽取全部六个嵌入文件，执行 DDL、生成两个确定性学习包并重新读取 raw/object hashes。附录 E 的独立抽取示例仍可只凭规范运行；工程中的生成器已经演进为引用共享 canonical 实现，来源 block hash 保存在 `generated/spec-sources.json`。抽取器不会覆盖已有修改，因此重复开发无需把演进文件强制还原为附录文本。

包校验器只读取 ZIP，不提取文件；先检查路径、重复项、文件类型、文件数、解压总量和压缩比，再核对 manifest、公开模型、私有 profile、正文及精确引用。内容依赖、概念先修、路线步骤分别检查 DAG。此校验不能证明权限、数据库事务、数学正确性或真实学习效果；M2 导入事务与后续业务验收仍需单独实施。

需求和路由目录是从规范生成的追踪记录。38 需求、33 场景和 27 任务均保留稳定 ID；102 路由包括响应表格单元内的正文与作答读取接口。路由目录不储存容易漂移的实现状态，实际实现、运行 OpenAPI 和测试结果必须由进度和运行时证据提供，不能以目录存在声称接口已经实现。目标 Gherkin 未有 step definitions，标明 NOT_RUN。各里程碑开始前继续补齐所属内联 DTO，并最终执行规范—运行路由—OpenAPI—测试的双向覆盖。
