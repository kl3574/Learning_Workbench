M4.2 前端开发证据公开派生包 v2；完整阶段验收以主代理后续固定提交整套门禁为准。

V1 全包首次扫描有 40 / 138 文件因个人绝对路径被拦截，当次未复制发布任何 payload。V1 和私有原件保持不变。V2 将路径前缀规范化为 `<REPOSITORY_ROOT>`、`<ACCEPTANCE_CACHE>`、`<NATIVE_TMPDIR>` 或 `<USER_HOME>`，保留后缀、原测试结果和执行源哈希。

每份执行 receipt 的 `output_sha256` 仍指原始 stdout；公开日志哈希另见 `public_derivative.public_log_sha256` 和 [manifest.json](manifest.json)。配置/源码的执行哈希也仍指原始字节，路径已归一化的公开脚本没有再次执行。

最新开发性 native-04 为 4 PASS（23.8s），当时仅另一 Python integration test 变化；随后按主代理指示删除一条死 CSS 规则，旧 receipt 未回填新源。全部早期实际失败和受控 fixture 边界见 [summary.json](summary.json)。这不是最终固定提交整套门禁通过声明。

16 张 PNG 均已逐张查看且未改字节，最新一轮为 7 张；实际业务 JSON 也未改字节。截图只显示其 viewport，完整行为结论须结合测试断言和 JSON。合成材料未经专家审核；四父链 ContentService fixture、归档 SQL fixture 和注入配额错误不代表用户发布/归档 API、Import 复用或物理配额耗尽。

逐文件公开检查见 [publication-scan.json](publication-scan.json)。建议仓库位置：progress/evidence/2026-09-15/M4.2-frontend-development。
