本包仅记录 D 实际执行的 CI 失败诊断保留结构检查，状态为 LOCAL_STRUCTURE_PASS；远端 GitHub upload 功能验证为 NOT_RUN。两文件的前/后快照各两份：.github/workflows/ci.yml 与 tests/e2e/playwright.config.ts，原始执行日志、配置加载结果和脚本均保存。没有 Reader 业务源码、断言修改或浏览器执行结果。

实际检查包括 YAML 结构、固定 action 输入/runtime 声明、Node 24.21.0 下默认和 CI override 两次 Playwright 配置加载，以及私有假文件对白名单的选择检查。假 PNG 仅为合成占位字节，不是截图，未纳入本包。结构 PASS 不是远端上传成功证明，也不证明任意 DOM/JSON 都不含秘密。

父代理 root 后来报告过独立的 happy native 1 PASS，以及故障注入后原 5 秒断言 FAIL 并生成三类诊断。那些运行属于 root，本包未收录其运行原件或把它们算作 D 的测试；应另查 root 的对应证据。独立 reviewer 的结论也不冒充本包作者运行。

官方版本在 2026-09-15 实际只读核验：v7.0.1 非 draft/prerelease，tag 指向 043fb46d1a93c77aae656e7c1c64a875d1fc6a0a，固定 action.yml 声明 node24。短官方回执记录原下载文件 SHA；完整外部 README、release/tag 原文和 action.yml 均保留在原私有证据目录，未复制进这个最小包。可用以下官方直链核对：
- https://github.com/actions/upload-artifact/releases/tag/v7.0.1
- https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/action.yml
- https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/README.md#inputs
- https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/README.md#uploading-hidden-files
- https://playwright.dev/docs/test-use-options#recording-options

validate.py.txt 是实际执行脚本的归一化存档，并非新执行或可直接运行的完整发布包：其原执行依赖当时工作区、私有目录中下载的固定 action.yml 与原快照。原始绝对路径仅按固定前缀顺序替换，其他字节不改；所有内嵌源/执行 SHA 保持原值。归一化脚本后缀加 .txt 防止归档被当产品 Python 扫描。

manifest.json 的 payloads 给每项原/公开 SHA-256、字节数、归一化 source_path 与替换计数。raw_aggregate/public_aggregate 均对按公开相对 path 字典序排列的 UTF-8 行“path + NUL + 对应 SHA-256 + LF”串接后做 SHA-256；不包含 manifest 自身和 publication-scan.json，避免自指。manifest 与扫描回执由私有 packaging-receipt.json 单独绑定。

全部实际公开文件使用仓库当前 scripts.check_publication.inspect(path,data) 扫描；当前模块没有 inspect_file。扫描是有界路径/凭据模式检查，并非任意私人文本安全保证。源路径以 <REPO>/<ACCEPTANCE_CACHE>/<HOME> 表达；原件未改。无生产测试重跑、浏览器、GitHub 上传、提交或 push。
