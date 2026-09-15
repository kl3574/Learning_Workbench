已实施的最小变更仅为 .github/workflows/ci.yml 与 tests/e2e/playwright.config.ts。Reader、原5秒断言与观察hook未由本代理修改。源前/后原字节在source-before/source-after，root另拥有Reader诊断hook。

2026-09-15 实时官方核验：最新稳定 [actions/upload-artifact v7.0.1](https://github.com/actions/upload-artifact/releases/tag/v7.0.1)（非draft/prerelease）精确 tag commit 为043fb46d1a93c77aae656e7c1c64a875d1fc6a0a；[固定action.yml](https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/action.yml)声明runs.using=node24，所用inputs均存在。它是GitHub-hosted ubuntu-26.04现有Node24运行链可用的JavaScript action；本轮只核声明/结构，远端实际执行仍NOT_RUN，不将setup-node版本当成action自带运行时证明。

上传步骤仅在native步骤本身失败时执行。只匹配输出目录内error-context.md、test-failed*.png、reader-load-diagnostic.json三种名字；不上传整个目录、数据库、headers/session文件、trace、成功截图或key文件。trace维持off，自动截图改only-on-failure，行为见[Playwright官方配置说明](https://playwright.dev/docs/test-use-options#recording-options)。实际CI测试使用合成内容；路径白名单本身不是任意文件内容无秘密的证明，Reader观察JSON的字段安全由root/C独立检查，本轮未读取其未冻结hook或真实凭据。

官方说明默认排除隐藏目录中的文件；因此CI通过LEARNING_E2E_OUTPUT_DIR将本次结果放runner.temp的非隐藏专用目录。本地未设置该变量时仍使用原.local_data/e2e-results。无需include-hidden-files=true。[官方隐藏文件规则](https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/README.md#uploading-hidden-files)

保留期3天；名称绑定event/run ID/attempt，避免不同推送/PR/重跑互相覆盖；if-no-files-found=warn会明确提示没有诊断文件。原native失败未设continue-on-error，上传成功或没有文件都不会把失败测试变为通过。取消或在native之前失败可能没有产物，不能宣称每个故障都有截图。[官方上传/保留参数](https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/README.md#inputs)

实际结构核验PASS：YAML解析与官方固定inputs/runtime、失败条件、三pattern白名单、未修改其它jobs；Node24.21.0实际加载Playwright配置（默认/override两种）且trace off/截图 only-on-failure/worker1/timeout30000一致；私有假文件fixture确认白名单不选trace.zip/headers.json/state.sqlite/session.json/success.png/provider.key。此fixture仅测文件选择，假PNG不是浏览器截图。两源检查前后hash相同，当前两源publication.inspect均PASS。未运行测试套件、浏览器、webServer或upload action；没有修复历史Reader失败的声明，没有push。
