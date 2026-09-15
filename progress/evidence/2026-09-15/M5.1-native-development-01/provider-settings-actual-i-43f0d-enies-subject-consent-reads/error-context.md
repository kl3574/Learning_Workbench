# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: provider-settings.spec.ts >> actual independent assessment policy keeps settings controls available and denies subject consent reads
- Location: ../../tests/e2e/provider-settings.spec.ts:112:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '明确开始本次测试', exact: true })
    - locator resolved to <button disabled class="primary-button">明确开始本次测试</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
      - waiting 100ms
    19 × waiting for element to be visible, enabled and stable
       - element is not enabled
     - retrying click action
       - waiting 500ms

```

# Test source

```ts
  19  |   await dialog.getByLabel('模型名称', { exact: true }).fill('synthetic-unregistered-native-model')
  20  |   await dialog.getByRole('button', { name: '准备配置保存命令', exact: true }).click()
  21  |   await expect(dialog.getByRole('button', { name: '确认发送配置保存', exact: true })).toBeEnabled()
  22  |   const saved = page.waitForResponse(value => value.request().method() === 'PUT' && value.url().endsWith(`/providers/${id}/config`))
  23  |   await dialog.getByRole('button', { name: '确认发送配置保存', exact: true }).click(); expect((await saved).status()).toBe(200)
  24  |   await expect(dialog.getByText('原命令已确认 · 修订 1。此回执保留当时事实，不替代当前状态。', { exact: true })).toBeVisible()
  25  |   await expect(dialog.getByLabel('模型名称', { exact: true })).toHaveValue('synthetic-unregistered-native-model')
  26  |   await expect(dialog.getByText(`提供商 ${id}：当前读回 r1，无秘密引用`, { exact: true })).toBeVisible()
  27  |   const response = await page.request.get(`/api/v1/providers/${id}/config`); expect(response.status()).toBe(200)
  28  |   const value: ProviderConfigView = await response.json(); expect(value.revision).toBe(1); expect(value.secret_present).toBe(false)
  29  |   return value
  30  | }
  31  | async function headers(page: Page, runtime: RestartRuntime, key: string) {
  32  |   const response = await page.request.get('/api/v1/session'); expect(response.status()).toBe(200)
  33  |   const session: { csrf_token: string } = await response.json()
  34  |   return { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': key }
  35  | }
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
  117 |     const fixture = originalAssessmentPackage('providerpolicynative', 'learner'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  118 |     await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
> 119 |     await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); await expect(page.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
      |                                                                                                                                                                 ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  120 |     const dialog = await settings(page); await expect(dialog.getByRole('region', { name: '授权历史', exact: true })).toContainText('授权摘要隐藏')
  121 |     const rejected = await page.request.get('/api/v1/consents'); expect(rejected.status()).toBe(409)
  122 |     await createConfig(page, dialog, id); await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-independent-control-only'); await dialog.getByRole('button', { name: '保存秘密', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
  123 |     await dialog.getByRole('button', { name: '删除秘密引用', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
  124 |     await expect(dialog.getByRole('region', { name: '冻结外发摘要', exact: true })).toHaveCount(0); expect(errors).toEqual([])
  125 |     writeFileSync(info.outputPath('actual-provider-independent-controls.json'), JSON.stringify({ scope: 'Real unreviewed learner import and actual independent unscored attempt; actual config and secret controls remain available while subject consent GET is denied. No injected consent, generation job, score, proof or provider dispatch.', consent_read_status: rejected.status(), config_revision_after_secret_delete: 3, subject_summary_visible: false, runtime_errors: errors }, null, 2))
  126 |   } finally { await runtime.close() }
  127 | })
  128 | 
```