# M3.3 有界规则与独立审阅证据

本包保留早期失败和修复后结果，全部输入为原创合成材料。本包不包含运行时数据库、会话、请求头、capability 值、浏览器 profile 或 DOM。唯一产品规范是仓库 PRODUCT_DESIGN.md。

- `rules/`：初次 85 PASS / 1 FAIL（0x10 安全拒绝但错误分类）。初次 shell 未保留 pytest 退出码，不能把 wrapper 的 0 当通过。第二次 90 PASS，ruff 两个 E702 失败（exit 1）。最终 91 PASS，ruff、mypy 均 exit 0。最终三源 before/after 哈希相同，打包时再次核对源码及快照仍相同；未重跑测试。
- `practice/static-review.json`：仅五文件静态审查，无新增发现，未独立跑集成测试；不借用 root 的 88 项通过计数。
- `assessment/`：初始两个真实 SQLite 故障探针均 FAIL（exit 1），证明一个坏 job/旧 outbox 可以饿死后续合法评分及安全 Markdown 导入。修复后保留原探针不变，与取消后历史成绩保留/新 key 恢复的控制一起 3 PASS（exit 0）。控制在修复前也独立 1 PASS。每次只固定九个被审源码，不宣称整个变化中的仓库固定；详情见 review.md。

`manifest.json` 逐文件列出本地原件描述、原始 SHA256、公开衍生 SHA256、字节数和转换；个人仓库前缀与本地临时证据路径改为说明或包内相对路径。诊断未删减。JSON 回执明确区分原始与公开日志哈希，源码哈希继续指原源码字节，不冒充已改写衍生字节。原始文件保留不变。`inspection.json` 为逐文件 scanner 结果；人工合成输入来源审核见 provenance.json，scanner 不替代人工检查。

探针以 `.py.txt` 保存避免自动测试收集。回放需在合适的项目版本将它们复制为临时 `.py` 文件，再按回执里的 uv/pytest 参数运行；公开 argv 的临时路径已转换，不能当成原始绝对路径逐字记录。纯规则最初及最终源码快照已包含；Practice 静态审查只记录当时五文件 SHA，未保存它们的完整原始快照。

本包不是 M3.3 全阶段验收，不包含独立资格判定、完整 native、CI 或人工标准答案审批声明。纯规则合成 approved 模型不能视为人工审批；真实导入材料始终 needs_review。SQLite 故障注入是测试安排，不表示公开 API 允许任意 SQL。
