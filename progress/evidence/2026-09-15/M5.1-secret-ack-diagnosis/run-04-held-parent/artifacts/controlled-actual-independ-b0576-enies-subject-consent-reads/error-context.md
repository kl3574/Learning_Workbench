# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: controlled.spec.ts >> actual independent assessment policy keeps settings controls available and denies subject consent reads
- Location: ../../../.cache/learning-workbench-acceptance/m51-secret-ack-diagnosis/controlled.spec.ts:112:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('dialog', { name: '设置', exact: true }).getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('dialog', { name: '设置', exact: true }).getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '设置', exact: true }).getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })

```

```yaml
- link "跳到学习内容":
  - /url: "#reader-main"
- banner:
  - link "知径 学习工作台":
    - /url: "#"
    - strong: 知径
    - text: 学习工作台
  - button "搜索与命令 Ctrl ⇧ P"
  - button "切换导航栏" [expanded]: 目录
  - button "切换 Agent 栏" [expanded]: Agent
  - button "专注"
  - button "导入"
- complementary "课程导航":
  - text: 测试工作区
  - heading "独立测试进行中" [level=2]
  - paragraph: 工作区学科材料暂受限制；自己的测试可继续、提交或放弃。
  - navigation "学习主导航":
    - button "学习路线"
    - button "教材"
    - button "习题"
    - button "测试题"
  - heading "测试上下文目录" [level=2]
  - navigation "测试题号目录":
    - button "第 1 题"
    - button "第 2 题"
    - button "第 3 题"
    - button "第 4 题"
    - button "第 5 题"
  - button "返回进行中的独立测试"
  - button "笔记"
  - button "创作"
  - button "设置"
- separator "导航栏宽度"
- main:
  - tablist "打开的学习对象":
    - tab "测试题"
    - tab "已固定数量关系参考测验：未审核内容的作答记录 · r1": ⌖ 数量关系参考测验：未审核内容的作答记录 · r1
    - button "固定标签 数量关系参考测验：未审核内容的作答记录 · r1": ⌖
    - button "关闭标签 数量关系参考测验：未审核内容的作答记录 · r1": ×
    - tab "已固定测试作答 · r1" [selected]: ⌖ 测试作答 · r1
    - button "固定标签 测试作答 · r1": ⌖
    - button "关闭标签 测试作答 · r1": ×
  - article:
    - text: 测试 · 冻结作答实例
    - heading "本次测试作答" [level=1]
    - strong: 独立测试 · 进行中
    - status: 服务端作答已保存
    - text: 本机草稿存储可用
    - paragraph: 会话修订 1。本次测试不计时，提交前可明确放弃。未提交时没有分数。
    - paragraph: 冻结策略：工作区教材与笔记受限；Agent 仅固定操作帮助；联网未获许可；标准答案按服务端冻结策略放行，实际已释放内容显示在评分结果中。
    - button "打开本次测试复盘" [disabled]
    - button "重新读取测试状态"
    - button "立即保存测试作答"
    - navigation "本次测试题目":
      - button "第 1 题"
      - button "第 2 题"
      - button "第 3 题"
      - button "第 4 题"
      - button "第 5 题"
    - heading "第 1 题 · 单选题" [level=2]
    - paragraph: 修订 1 · 概念回忆 · 按冻结内容状态核对；最终数值与推导依据分别判断
    - group: 题目引用与概念
    - paragraph: 选择 的结果。
    - paragraph: 作答格式：选择一个选项；练习尚未评分。
    - group "第 1 题作答":
      - text: 第 1 题作答
      - radio "4"
      - paragraph: "4"
      - radio "5"
      - paragraph: "5"
      - button "清除此题选择"
      - text: 推导步骤（可选）
      - textbox "第 1 题推导步骤"
      - text: 答案最多 4,000 个字符；步骤最多 20,000 个字符。表达式按原文保存，尚不做评分判定。
    - heading "结束本次测试" [level=2]
    - paragraph: 提交只使用服务端已保存的作答；关闭标签不会提交。放弃后不产生独立分数，未同步候选仍可保留在本机。
    - button "提交本次测试"
    - button "放弃本次测试"
    - group: 本次测试的冻结引用与范围
- separator "Agent 栏宽度"
- complementary "Agent 助教":
  - heading "Agent · 固定操作帮助" [level=2]
  - paragraph: 独立测试进行中。这里仅显示操作说明，不包含题目、作答、笔记或历史学科上下文。
  - list:
    - listitem: 用题号目录或 Tab 键移动，作答会自动保存并明确显示状态。
    - listitem: 离线或版本冲突时保留本机候选；重新读取后先比较，再明确恢复。
    - listitem: 提交前确认作答已保存；关闭标签或浏览器不会提交。
    - listitem: 可明确放弃当前测试；放弃不计为独立零分。
  - paragraph: 模型：未调用 · 联网：未调用 · 标准答案：未请求
- status: ✓ UI 会话已保存 内容修订 1 独立测试进行中 · 工作区材料受限 · 本机
- dialog "设置":
  - banner:
    - heading "设置" [level=2]
    - button "关闭设置": ×
  - button "学习目标与基础" [disabled]
  - button "概念与技能证据" [disabled]
  - region "提供商与授权设置":
    - heading "提供商与授权" [level=3]
    - paragraph: 设置操作只访问本机服务，不连接、验证密钥或调用模型。配置存在与模型可调度分别显示。
    - region "提供商能力":
      - heading "当前能力" [level=4]
      - button "重新读取配置与能力"
      - list:
        - listitem:
          - button "provider_native_independent" [disabled]
          - text: · 已配置 是 · 文本 不可调度 · 流 不可调度 · 搜索 不支持 · 工具 不支持 · 结构化 不支持
          - paragraph: MODEL_NOT_REGISTERED
    - text: 提供商标识
    - textbox "提供商标识" [disabled]: provider_native_independent
    - button "读取或准备新配置" [disabled]
    - paragraph: 提供商 provider_native_independent：当前读回 r2，有秘密引用
    - group "提供商配置":
      - text: 提供商配置 适配协议
      - combobox "适配协议":
        - option "官方 Responses" [selected]
        - option "兼容 Chat"
      - text: 服务地址
      - textbox "服务地址": https://example.invalid/v1
      - text: 模型名称
      - textbox "模型名称": synthetic-unregistered-native-model
      - text: Embedding 模型（可留空，当前不调用）
      - textbox "Embedding 模型（可留空，当前不调用）"
      - text: 目的地策略
      - combobox "目的地策略":
        - option "公网 HTTPS" [selected]
        - option "明确允许本机回环地址"
      - checkbox "填写本机估算价格"
      - text: 填写本机估算价格
    - button "准备配置保存命令" [disabled]
    - region "秘密控制":
      - heading "秘密控制" [level=3]
      - paragraph: 输入只在当前页面临时保留；不会写入浏览器草稿或恢复存储。刷新后不能恢复原秘密命令。
      - paragraph: 当前读回：配置 r2 · 有秘密引用。引用存在不表示密钥有效或可调用。
      - text: 新秘密
      - textbox "新秘密" [disabled]
      - button "保存秘密" [disabled]
      - button "重试原删除引用命令" [disabled]
      - button "明确丢弃临时秘密命令"
      - alert: 秘密控制版本冲突。临时输入与原基准仍保留，比较后再更正。
      - status: 原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。
      - paragraph: 另行回读当前配置：r2 · 有秘密引用。
      - region "秘密控制版本比较":
        - heading "比较原基准与当前版本" [level=4]
        - paragraph: 原始基准 r1；当前r2；本页候选为删除引用。
        - button "采用当前版本，明确更正秘密命令"
      - paragraph: 删除使引用不可再调度；不能撤回已发生外发，也不承诺介质级擦除。
    - region "授权任务":
      - heading "发起授权" [level=4]
      - paragraph: 本阶段尚无可发起授权的生成任务。后续由真实生成任务提供准备好的输入；这里不创建任意提示词任务。
    - region "配置与授权命令":
      - heading "配置与授权命令" [level=3]
      - status: 无秘密候选已安全保留在本机
      - region "当前原命令":
        - heading "配置保存" [level=4]
        - paragraph:
          - text: 原 key：
          - code: provider_872d72de-63b9-4b62-b4ab-b15559e773eb
        - region "配置三方比较":
          - article:
            - heading "原始基准 · r0" [level=5]
            - paragraph: 新配置尚不存在
          - article:
            - heading "本页候选" [level=5]
            - term: 协议
            - definition: official_responses
            - term: 地址
            - definition: https://example.invalid/v1
            - term: 模型
            - definition: synthetic-unregistered-native-model
            - term: Embedding
            - definition: 无
            - term: 目的地策略
            - definition: public_https
            - term: 本机价格
            - definition: 价格未知
          - article:
            - heading "当前服务端" [level=5]
            - paragraph: r1
            - term: 协议
            - definition: official_responses
            - term: 地址
            - definition: https://example.invalid/v1
            - term: 模型
            - definition: synthetic-unregistered-native-model
            - term: Embedding
            - definition: 无
            - term: 目的地策略
            - definition: public_https
            - term: 本机价格
            - definition: 价格未知
        - status: 原命令已确认 · 修订 1。此回执保留当时事实，不替代当前状态。
        - button "重试原配置或授权命令" [disabled]
        - button "另行读取当前状态"
        - button "比较后采用当前版本，准备更正"
        - button "保留候选，返回设置"
    - region "授权历史":
      - heading "授权历史与停止控制" [level=3]
      - paragraph: 撤销阻止新的派发，并请求停止在途处理；无法保证撤回内容或退款。
      - paragraph: 当前正在核验权限或处于独立测试。授权摘要隐藏，已停止新的摘要读取；此前安全取得的授权标识仍可用于撤销。
      - paragraph: 当前页面没有已取得的授权控制标识；不会读取受限摘要来寻找它们。
  - paragraph: 画像和授权摘要暂不可操作；配置、秘密控制和已有授权的撤销仍可使用。
```

# Test source

```ts
  36  | async function browserRetainsSecret(page: Page, secret: string) {
  37  |   return page.evaluate(async needle => {
  38  |     for (const storage of [localStorage, sessionStorage]) for (let index = 0; index < storage.length; index++) if ((storage.getItem(storage.key(index)!) ?? '').includes(needle)) return true
  39  |     for (const entry of await indexedDB.databases()) {
  40  |       if (!entry.name) continue
  41  |       const db = await new Promise<IDBDatabase>((accept, reject) => { const open = indexedDB.open(entry.name!); open.onsuccess = () => accept(open.result); open.onerror = () => reject(open.error) })
  42  |       try {
  43  |         for (const name of Array.from(db.objectStoreNames)) {
  44  |           const values = await new Promise<unknown[]>((accept, reject) => { const read = db.transaction(name, 'readonly').objectStore(name).getAll(); read.onsuccess = () => accept(read.result); read.onerror = () => reject(read.error) })
  45  |           if (JSON.stringify(values).includes(needle)) return true
  46  |         }
  47  |       } finally { db.close() }
  48  |     }
  49  |     return false
  50  |   }, secret)
  51  | }
  52  | 
  53  | test('real settings persist control configuration and temporary secrets without claiming production generation', async ({ playwright }, info) => {
  54  |   test.setTimeout(90_000)
  55  |   const runtime = await RestartRuntime.start(), id = 'provider_native_control', secret = 'synthetic-native-provider-control-only', errors: string[] = []
  56  |   try {
  57  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
  58  |     const dialog = await settings(page); await expect(dialog.getByText('本工作区尚无提供商配置。', { exact: true })).toBeVisible()
  59  |     await expect(dialog.getByRole('region', { name: '授权任务', exact: true })).toContainText('本阶段尚无可发起授权的生成任务')
  60  |     const before = await createConfig(page, dialog, id)
  61  |     await expect(dialog.getByLabel('新秘密', { exact: true })).toBeEnabled(); await dialog.getByLabel('新秘密', { exact: true }).fill(secret)
  62  |     expect(await browserRetainsSecret(page, secret)).toBe(false)
  63  |     await page.keyboard.press('Control+Shift+P')
  64  |     const closing = page.getByRole('dialog', { name: '保留配置与授权候选', exact: true }); await expect(closing).toBeVisible(); await expect(page.getByRole('dialog', { name: '命令面板', exact: true })).toHaveCount(0)
  65  |     await closing.getByRole('button', { name: '返回设置', exact: true }).click(); await expect(dialog.getByLabel('新秘密', { exact: true })).toHaveValue(secret)
  66  |     const secretSaved = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/providers/${id}/secret`))
  67  |     await dialog.getByRole('button', { name: '保存秘密', exact: true }).click(); expect((await secretSaved).status()).toBe(200)
  68  |     await expect(dialog.getByLabel('新秘密', { exact: true })).toHaveValue(''); await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
  69  |     const current: ProviderConfigView = await page.request.get(`/api/v1/providers/${id}/config`).then(value => value.json()); expect(current.revision).toBe(2); expect(current.secret_present).toBe(true)
  70  |     const capabilities: ProviderCapabilitiesResponse = await page.request.get('/api/v1/providers/capabilities').then(value => value.json()); expect(capabilities.items.find(value => value.provider_id === id)).toMatchObject({ configured: true, chat: false, streaming: false, web_search: false, tool_calls: false, structured_output: false })
  71  |     expect(await browserRetainsSecret(page, secret)).toBe(false); expect(JSON.stringify(current)).not.toContain(secret)
  72  |     await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-discard-before-reload')
  73  |     await dialog.getByRole('button', { name: '关闭设置', exact: true }).click(); await closing.getByRole('button', { name: '明确丢弃临时输入，保留本机命令并关闭', exact: true }).click()
  74  |     await page.reload(); const reopened = await settings(page); await reopened.getByRole('button', { name: id, exact: true }).click(); await expect(reopened.getByLabel('新秘密', { exact: true })).toHaveValue('')
  75  |     const deleting = page.waitForResponse(value => value.request().method() === 'DELETE' && value.url().endsWith(`/providers/${id}/secret`))
  76  |     await reopened.getByRole('button', { name: '删除秘密引用', exact: true }).click(); expect((await deleting).status()).toBe(200)
  77  |     await expect(reopened.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
  78  |     await page.screenshot({ path: info.outputPath('provider-controls-1440.png') }); await page.setViewportSize({ width: 390, height: 844 }); await reopened.getByRole('region', { name: '秘密控制', exact: true }).scrollIntoViewIfNeeded(); await expect(reopened.getByRole('button', { name: '关闭设置', exact: true })).toBeInViewport(); expect(await reopened.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('provider-controls-390.png') })
  79  |     expect(errors).toEqual([])
  80  |     writeFileSync(info.outputPath('actual-provider-controls.json'), JSON.stringify({ scope: 'Actual local configuration/secret routes and browser persistence inventory; synthetic secret only. Production registry has no source or accepted model proof. No actual paid provider dispatch or model quality claim.', initial_config: before, secret_reference_config: current, capability_readback: capabilities, secret_absent_from_browser_persistence: true, temporary_input_does_not_restore: true, explicit_secret_delete_revision: 3, runtime_errors: errors }, null, 2))
  81  |   } finally { await runtime.close() }
  82  | })
  83  | 
  84  | test('real config lost ACK restores the original command after browser/API restart and reads later current state separately', async ({ playwright }, info) => {
  85  |   test.setTimeout(90_000)
  86  |   const runtime = await RestartRuntime.start(), id = 'provider_native_recovery', commands: { key: string; body: string }[] = [], errors: string[] = []
  87  |   try {
  88  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
  89  |     const dialog = await settings(page); await createConfig(page, dialog, id)
  90  |     await dialog.getByLabel('模型名称', { exact: true }).fill('synthetic-original-candidate')
  91  |     await dialog.getByRole('button', { name: '准备配置保存命令', exact: true }).click()
  92  |     await page.route(`**/api/v1/providers/${id}/config`, async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! }); const response = await route.fetch(); expect(response.status()).toBe(200); await route.abort('failed') })
  93  |     await dialog.getByRole('button', { name: '确认发送配置保存', exact: true }).click(); await expect(dialog.getByRole('alert').filter({ hasText: '命令尚未确认' })).toBeVisible()
  94  |     const applied: ProviderConfigView = await page.request.get(`/api/v1/providers/${id}/config`).then(response => response.json()); expect(applied.revision).toBe(2)
  95  |     const later: ProviderConfigWrite = { expected_revision: 2, adapter: applied.adapter, base_url: applied.base_url, model: 'synthetic-later-server-config', embedding_model: applied.embedding_model, endpoint_policy: applied.endpoint_policy, pricing: applied.pricing }
  96  |     const changed = await page.request.put(`/api/v1/providers/${id}/config`, { headers: await headers(page, runtime, 'native-provider-later-config'), data: later }); expect(changed.status()).toBe(200)
  97  |     await dialog.getByRole('button', { name: '关闭设置', exact: true }).click(); await page.getByRole('dialog', { name: '保留配置与授权候选', exact: true }).getByRole('button', { name: '明确丢弃临时输入，保留本机命令并关闭', exact: true }).click()
  98  |     const database = runtime.databaseIdentity(); await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed(); expect(runtime.databaseIdentity()).toEqual(database)
  99  |     const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; restored.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(restored)
  100 |     const panel = await settings(restored); await panel.getByRole('button', { name: '恢复原命令 1', exact: true }).click()
  101 |     const comparison = panel.getByRole('region', { name: '配置三方比较', exact: true }); await expect(comparison.getByRole('heading', { name: '原始基准 · r1', exact: true })).toBeVisible(); await expect(comparison.locator('article').nth(2)).toContainText('r3')
  102 |     await restored.route(`**/api/v1/providers/${id}/config`, async route => { if (route.request().method() === 'PUT') commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! }); await route.continue() })
  103 |     await panel.getByRole('button', { name: '重试原配置或授权命令', exact: true }).click(); await expect(panel.getByText('原命令已确认 · 修订 2。此回执保留当时事实，不替代当前状态。', { exact: true })).toBeVisible()
  104 |     await expect(comparison.locator('article').nth(2)).toContainText('synthetic-later-server-config'); expect(commands).toHaveLength(2); expect(commands[1]).toEqual(commands[0])
  105 |     const current: ProviderConfigView = await restored.request.get(`/api/v1/providers/${id}/config`).then(response => response.json()); expect(current.revision).toBe(3); expect(current.model).toBe(later.model)
  106 |     await restored.screenshot({ path: info.outputPath('provider-original-ack-1440.png') }); await restored.setViewportSize({ width: 390, height: 844 }); await comparison.scrollIntoViewIfNeeded(); await expect(panel.getByRole('button', { name: '关闭设置', exact: true })).toBeInViewport(); expect(await panel.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await restored.screenshot({ path: info.outputPath('provider-original-ack-390.png') })
  107 |     expect(errors).toEqual([])
  108 |     writeFileSync(info.outputPath('actual-provider-original-ack.json'), JSON.stringify({ scope: 'Actual successful config HTTP ACK deliberately lost; later independent command; real browser/API restart and same original-key replay. No provider dispatch.', actual_commands: commands, original_ack_revision: 2, current_config: current, database_identity_unchanged: true, runtime_errors: errors }, null, 2))
  109 |   } finally { await runtime.close() }
  110 | })
  111 | 
  112 | test('actual independent assessment policy keeps settings controls available and denies subject consent reads', async ({ playwright }, info) => {
  113 |   test.setTimeout(90_000)
  114 |   const runtime = await RestartRuntime.start(), id = 'provider_native_independent', errors: string[] = []
  115 |   try {
  116 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
  117 |     // A learner package intentionally omits the private reference bindings and
  118 |     // cannot start even an unscored attempt. The actual author import retains
  119 |     // unreviewed references; this helper explicitly switches back to learner.
  120 |     const fixture = originalAssessmentPackage('providerpolicynative', 'author'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  121 |     const identityResponse = await page.request.get('/api/v1/session'); expect(identityResponse.status()).toBe(200)
  122 |     const identity: SessionResponse = await identityResponse.json(); expect(identity.role).toBe('learner')
  123 |     await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  124 |     await page.getByRole('radio', { name: '独立测试', exact: true }).check()
  125 |     await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  126 |     const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/assessments/${fixture.assessment.id}/attempts`))
  127 |     await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  128 |     const created = await creating; expect(created.status()).toBe(201)
  129 |     const attempt: AttemptSnapshot = await created.json()
  130 |     expect(attempt.status).toBe('active'); expect(attempt.policy.mode).toBe('independent'); expect(attempt.grading_status).toBe('not_graded')
  131 |     expect(attempt.preflight.startable).toBe(true); expect(attempt.preflight.grading).toMatchObject({ status: 'unreviewed', approved_count: 0, needs_review_count: 5, missing_count: 0, damaged_count: 0 })
  132 |     await expect(page.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
  133 |     const dialog = await settings(page); await expect(dialog.getByRole('region', { name: '授权历史', exact: true })).toContainText('授权摘要隐藏')
  134 |     const rejected = await page.request.get('/api/v1/consents'); expect(rejected.status()).toBe(409)
  135 |     await createConfig(page, dialog, id); await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-independent-control-only'); await dialog.getByRole('button', { name: '保存秘密', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
> 136 |     await dialog.getByRole('button', { name: '删除秘密引用', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
      |                                                                                                                                                                   ^ Error: expect(locator).toBeVisible() failed
  137 |     await expect(dialog.getByRole('region', { name: '冻结外发摘要', exact: true })).toHaveCount(0); expect(errors).toEqual([])
  138 |     writeFileSync(info.outputPath('actual-provider-independent-controls.json'), JSON.stringify({ scope: 'Real author package import with unreviewed reference bindings, explicit return to learner role, and actual independent unscored attempt; actual config and secret controls remain available while subject consent GET is denied. No injected consent, generation job, score, proof or provider dispatch.', authenticated_role: identity.role, attempt_id: attempt.id, attempt_status: attempt.status, attempt_policy: attempt.policy, grading_status: attempt.grading_status, preflight: attempt.preflight, consent_read_status: rejected.status(), config_revision_after_secret_delete: 3, subject_summary_visible: false, runtime_errors: errors }, null, 2))
  139 |   } finally { await runtime.close() }
  140 | })
  141 | 
  142 | import { installObservation, saveObservation } from './observer-v2'
  143 | const originalOpenBrowser = RestartRuntime.prototype.openBrowser
  144 | RestartRuntime.prototype.openBrowser = async function (...args: Parameters<typeof originalOpenBrowser>) {
  145 |   const context = await originalOpenBrowser.apply(this, args)
  146 |   await installObservation(context.pages()[0])
  147 |   return context
  148 | }
  149 | test.afterEach(async ({}, info) => { await saveObservation(info.outputPath('safe-observation.json')) })
  150 | 
```