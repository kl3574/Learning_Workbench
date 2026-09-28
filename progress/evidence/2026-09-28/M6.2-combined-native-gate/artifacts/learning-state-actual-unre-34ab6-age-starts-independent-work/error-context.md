# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: learning-state.spec.ts >> actual unreviewed submission stays excluded and its precise sources disappear when another page starts independent work
- Location: ../../tests/e2e/learning-state.spec.ts:30:1

# Error details

```
Error: route.fulfill: Route is already handled!
```

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('独立测试进行中', { exact: true }).first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText('独立测试进行中', { exact: true }).first() with timeout 5000ms
  - waiting for getByText('独立测试进行中', { exact: true }).first()

```

# Test source

```ts
  1  | import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { writeFileSync } from 'node:fs'
  3  | import { RestartRuntime } from './restartRuntime'
  4  | import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
  5  | import type { ConceptStateResponse, LearnerProfile } from '../../packages/contracts/generated/api-types'
  6  | const test = base.extend<{ runtime: RestartRuntime }>({
  7  |   runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  8  |   page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
  9  | })
  10 | async function openProfile(page: Page) { await page.getByRole('button', { name: '设置', exact: true }).click(); await page.getByRole('dialog', { name: '设置', exact: true }).getByRole('button', { name: '学习目标与基础', exact: true }).click(); const dialog = page.getByRole('dialog', { name: '学习目标与基础', exact: true }); await expect(dialog.getByRole('button', { name: '编辑学习目标与基础', exact: true })).toBeEnabled(); return dialog }
  11 | 
  12 | test('real self-report persists a lost-ACK command once and never creates independent evidence', async ({ page }, info) => {
  13 |   const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  14 |   const fixture = originalAssessmentPackage('profileacknative', 'learner'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  15 |   const before: ConceptStateResponse = await page.request.get('/api/v1/learning/concept-states').then(response => response.json()), initial: LearnerProfile = await page.request.get('/api/v1/learner/profile').then(response => response.json())
  16 |   expect(initial.revision).toBe(1); expect(before.items.every(item => item.independent_count === 0 && item.state_input_evidence_ids.length === 0)).toBe(true)
  17 |   const dialog = await openProfile(page); await dialog.getByRole('button', { name: '编辑学习目标与基础', exact: true }).click()
  18 |   await dialog.getByLabel('学习目标', { exact: true }).fill('原创自报目标 🧠é\n阅读与证据分别记录'); await dialog.getByLabel('每周学习分钟数').fill('240'); await dialog.getByLabel(`自报基础：${before.concepts[0].title}`, { exact: true }).selectOption('independent_use')
  19 |   const commands: string[] = []; let first = true
  20 |   await page.route('**/api/v1/learner/profile', async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; commands.push(route.request().headers()['idempotency-key']); if (first) { first = false; const response = await route.fetch(); expect(response.status()).toBe(200); await route.abort('failed') } else await route.continue() })
  21 |   await expect(dialog.getByRole('button', { name: '保存学习目标与基础', exact: true })).toBeEnabled(); await dialog.getByRole('button', { name: '保存学习目标与基础', exact: true }).click(); await expect(dialog.getByRole('alert').filter({ hasText: '尚未确认保存' })).toBeVisible()
  22 |   const applied: LearnerProfile = await page.request.get('/api/v1/learner/profile').then(response => response.json()); expect(applied.revision).toBe(2)
  23 |   await dialog.getByRole('button', { name: '重试原画像保存命令', exact: true }).click(); await expect(dialog.getByRole('status')).toContainText('画像已保存到服务端'); await expect(dialog.getByRole('status')).toContainText('本机画像草稿存储可用')
  24 |   expect(commands).toHaveLength(2); expect(commands[0]).toBe(commands[1]); const saved: LearnerProfile = await page.request.get('/api/v1/learner/profile').then(response => response.json()); expect(saved).toEqual(applied); expect(saved.self_assessments?.[0].origin).toBe('self_report')
  25 |   await page.screenshot({ path: info.outputPath('profile-saved-1440.png') }); await dialog.getByRole('button', { name: '关闭学习目标与基础', exact: true }).click(); await page.reload(); const restored = await openProfile(page); await expect(restored.getByLabel('学习目标', { exact: true })).toHaveValue(saved.goals!.join('\n')); await restored.getByRole('button', { name: '关闭学习目标与基础', exact: true }).click()
  26 |   const after: ConceptStateResponse = await page.request.get('/api/v1/learning/concept-states').then(response => response.json()); expect(after.items.map(item => [item.concept_ref, item.skill, item.evidence_state, item.independent_count, item.evidence_ids])).toEqual(before.items.map(item => [item.concept_ref, item.skill, item.evidence_state, item.independent_count, item.evidence_ids])); expect(errors).toEqual([])
  27 |   writeFileSync(info.outputPath('actual-profile-lost-ack.json'), JSON.stringify({ scope: 'original synthetic profile through actual HTTP, response loss, identical-command retry and browser reload', initial_revision: 1, final_revision: saved.revision, same_command_replayed: true, exact_server_response_unchanged_after_retry: true, evidence_unchanged: true, runtime_errors: errors }, null, 2))
  28 | })
  29 | 
  30 | test('actual unreviewed submission stays excluded and its precise sources disappear when another page starts independent work', async ({ page }, info) => {
  31 |   const fixture = originalAssessmentPackage('conceptsourcenative'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  32 |   const href = `${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`
  33 |   await page.goto(href); await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); await page.getByRole('button', { name: '提交本次测试', exact: true }).click(); await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible()
  34 |   await page.getByRole('button', { name: '设置', exact: true }).click(); await page.getByRole('button', { name: '概念与技能证据', exact: true }).click(); const dialog = page.getByRole('dialog', { name: '知识画像', exact: true }); const data: ConceptStateResponse = await page.request.get('/api/v1/learning/concept-states').then(response => response.json()); expect(data.items.some(item => item.sources.length > 0)).toBe(true)
  35 |   const row = data.items.find(item => item.sources.length > 0)!; expect(row.independent_count).toBe(0); expect(row.state_input_evidence_ids).toEqual([]); expect(row.sources.every(source => source.reason_codes.includes('ANSWER_UNREVIEWED'))).toBe(true)
  36 |   await dialog.locator('summary').filter({ hasText: `查看此概念技能的原始来源（${row.sources.length} 条证据）` }).first().click(); await dialog.locator('.learning-source>summary').first().click(); await expect(dialog.locator('.learning-source[open]').first()).toContainText('冻结的参考答案尚未审核'); await expect(dialog.locator('.learning-source[open]').first()).toContainText(row.sources[0].question_ref.sha256)
  37 |   const source = dialog.locator('.learning-source[open]').first(); await source.scrollIntoViewIfNeeded(); await page.screenshot({ path: info.outputPath('concept-sources-1440.png') })
  38 |   await page.setViewportSize({ width: 390, height: 844 }); await source.locator('summary').first().scrollIntoViewIfNeeded(); await expect(source.locator('summary').first()).toBeInViewport(); await expect(dialog.getByRole('button', { name: '关闭知识画像', exact: true })).toBeInViewport(); expect(await dialog.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true); await page.screenshot({ path: info.outputPath('concept-sources-390.png') })
  39 |   let release!: () => void, captured!: () => void; const gate = new Promise<void>(resolve => { release = resolve }), ready = new Promise<void>(resolve => { captured = resolve })
  40 |   await page.route('**/api/v1/learning/concept-states*', async route => { const response = await route.fetch(); captured(); await gate; await route.fulfill({ response }) }); await dialog.getByRole('button', { name: '刷新概念状态', exact: true }).click(); await ready
  41 |   const other = await page.context().newPage()
> 42 |   try { await other.goto(href); await other.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await other.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); await expect(other.getByText('独立测试进行中', { exact: true }).first()).toBeVisible(); release(); await expect(dialog.locator('.concept-state')).toHaveCount(0); expect((await page.request.get('/api/v1/learning/concept-states')).status()).toBe(409) } finally { release(); await page.unroute('**/api/v1/learning/concept-states*'); await other.close() }
     |                                                                                                                                                                                                                                                                          ^ Error: expect(locator).toBeVisible() failed
  43 | })
  44 | 
  45 | test('a quota-failed profile remains mounted when a global command tries to leave it', async ({ page }, info) => {
  46 |   const dialog = await openProfile(page)
  47 |   await dialog.getByRole('button', { name: '编辑学习目标与基础', exact: true }).click()
  48 |   await expect(dialog.getByRole('status')).toContainText('本机画像草稿存储可用')
  49 |   await page.evaluate(() => {
  50 |     const original = IDBObjectStore.prototype.put
  51 |     Object.defineProperty(IDBObjectStore.prototype, 'put', { configurable: true, writable: true, value: function (this: IDBObjectStore, ...args: Parameters<typeof original>) {
  52 |       if (this.transaction.db.name === 'learning-workbench.profile-drafts.v1' && localStorage.getItem('synthetic-profile-quota') === 'enabled') throw new DOMException('Synthetic profile quota failure', 'QuotaExceededError')
  53 |       return Reflect.apply(original, this, args)
  54 |     } })
  55 |     localStorage.setItem('synthetic-profile-quota', 'enabled')
  56 |   })
  57 |   await dialog.getByLabel('学习目标', { exact: true }).fill('未落盘原创画像，不可被命令面板卸载 🧠')
  58 |   await expect(dialog.getByRole('status')).toContainText('本机画像草稿尚未安全保存')
  59 |   await page.keyboard.press('Control+Shift+P')
  60 |   const confirmation = page.getByRole('dialog', { name: '保留未同步画像', exact: true })
  61 |   await expect(confirmation).toBeVisible(); await expect(confirmation.getByRole('button', { name: '保留本机画像草稿并关闭', exact: true })).toBeDisabled()
  62 |   await expect(page.getByRole('dialog', { name: '命令面板', exact: true })).toHaveCount(0)
  63 |   await expect(dialog.getByLabel('学习目标', { exact: true })).toHaveValue('未落盘原创画像，不可被命令面板卸载 🧠')
  64 |   expect(await page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); dispatchEvent(event); return event.defaultPrevented })).toBe(true)
  65 |   await confirmation.getByRole('button', { name: '返回编辑', exact: true }).click()
  66 |   await page.evaluate(() => localStorage.removeItem('synthetic-profile-quota'))
  67 |   await dialog.getByRole('button', { name: '重试本机画像保存', exact: true }).click(); await expect(dialog.getByRole('status')).toContainText('本机画像草稿存储可用')
  68 |   await page.keyboard.press('Control+Shift+P'); await confirmation.getByRole('button', { name: '保留本机画像草稿并关闭', exact: true }).click()
  69 |   await page.reload(); await page.getByRole('button', { name: '设置', exact: true }).click(); await page.getByRole('dialog', { name: '设置', exact: true }).getByRole('button', { name: '学习目标与基础', exact: true }).click()
  70 |   const restored = page.getByRole('dialog', { name: '学习目标与基础', exact: true }); await restored.getByRole('button', { name: '恢复画像候选 1', exact: true }).click(); await expect(restored.getByLabel('学习目标', { exact: true })).toHaveValue('未落盘原创画像，不可被命令面板卸载 🧠')
  71 |   expect((await page.request.get('/api/v1/learner/profile').then(response => response.json())).revision).toBe(1)
  72 |   writeFileSync(info.outputPath('actual-profile-command-close.json'), JSON.stringify({ scope: 'real IndexedDB quota exception; real keyboard shortcut; explicit durable close and reload', unsafe_command_switch_blocked: true, unsafe_beforeunload_protected: true, exact_unsent_candidate_restored: true, profile_server_revision: 1 }, null, 2))
  73 | })
  74 | 
```