# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: import-command-admission.spec.ts >> command import remains disabled while Policy is unknown after UI saved and original import helper works only after explicit admission
- Location: tests/e2e/import-command-admission.spec.ts:17:1

# Error details

```
Error: expect(locator).toBeDisabled() failed

Locator:  getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ })
Expected: disabled
Received: enabled
Timeout:  5000ms

Call log:
  - Expect "toBeDisabled" getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ })
    14 × locator resolved to <button>…</button>
       - unexpected value "enabled"

```

```yaml
- button "导入 ↵"
```

# Test source

```ts
  1  | import { writeFileSync } from 'node:fs'
  2  | import { expect, test, type Locator, type Page, type Route } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3  | import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'
  4  | import { RestartRuntime } from './restartRuntime'
  5  | import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
  6  | 
  7  | async function paletteImport(page: Page) {
  8  |   await page.keyboard.press('Control+Shift+P')
  9  |   const palette = page.getByRole('dialog', { name: '命令面板', exact: true })
  10 |   return { palette, button: palette.getByRole('button', { name: /^导入/ }) }
  11 | }
  12 | async function actualDisabledClick(page: Page, button: Locator) {
  13 |   const box = await button.boundingBox(); expect(box).not.toBeNull()
  14 |   await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height / 2)
  15 | }
  16 | 
  17 | test('command import remains disabled while Policy is unknown after UI saved and original import helper works only after explicit admission', async ({ playwright }, info) => {
  18 |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('gradingrecover')
  19 |   const facts: Record<string, unknown> = {}, deliveries: Promise<void>[] = []
  20 |   let release!: () => void, released = false, requests = 0, held = 0, importWrites = 0
  21 |   const gate = new Promise<void>(yes => { release = yes }), releaseGate = () => { released = true; release() }
  22 |   try {
  23 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  24 |     await runtime.authenticateOnly(page)
  25 |     page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/imports') importWrites++ })
  26 |     const handler = (route: Route) => {
  27 |       const delivery = (async () => {
  28 |         if (route.request().method() !== 'GET' || ++requests === 1 || released) { await route.continue(); return }
  29 |         const response = await route.fetch(); expect(response.status()).toBe(200)
  30 |         const actual = await response.json(); expect(actual.active_independent_attempt_id).toBeNull()
  31 |         held++; await gate; await route.fulfill({ response })
  32 |       })(); deliveries.push(delivery); return delivery
  33 |     }
  34 |     await page.route('**/api/v1/session', handler); await page.reload()
  35 |     await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
  36 |     await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toBeVisible()
  37 |     await expect.poll(() => held).toBeGreaterThan(0)
  38 |     await expect(page.locator('.import-trigger')).toBeDisabled()
  39 |     const { palette, button } = await paletteImport(page)
> 40 |     await expect(button).toBeDisabled()
     |                          ^ Error: expect(locator).toBeDisabled() failed
  41 |     await actualDisabledClick(page, button)
  42 |     await expect(palette).toBeVisible(); await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
  43 |     expect(importWrites).toBe(0); facts.unknownPolicyDisabledActualClick = true
  44 |     releaseGate(); await Promise.all(deliveries)
  45 |     await expect(button).toBeEnabled(); await expect(page.locator('.import-trigger')).toBeEnabled()
  46 |     await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0); expect(importWrites).toBe(0)
  47 |     facts.noAutomaticAdmissionAfterPermissionRecovery = true
  48 |     await palette.getByRole('button', { name: '关闭命令面板', exact: true }).click()
  49 |     const imported = await importAssessmentPackage(page, fixture)
  50 |     expect(imported.receipt.course_refs).toContainEqual(fixture.course); expect(importWrites).toBe(1)
  51 |     facts.originalFixtureAndUnchangedHelperSucceeded = true
  52 |     await page.screenshot({ path: info.outputPath('explicit-command-import-after-policy.png') })
  53 |   } finally {
  54 |     releaseGate(); await Promise.allSettled(deliveries); facts.actualPolicyResponsesHeld = held
  55 |     writeFileSync(info.outputPath('actual-command-unknown-policy.json'), JSON.stringify(facts, null, 2) + '\n')
  56 |     await runtime.close()
  57 |   }
  58 | })
  59 | 
  60 | test('command import keeps the actual independent attempt restriction and needs another explicit click after abandon', async ({ playwright }, info) => {
  61 |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('commandindependent')
  62 |   const facts: Record<string, unknown> = {}
  63 |   try {
  64 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  65 |     await runtime.authenticateOnly(page); await expect(page.locator('.import-trigger')).toBeEnabled()
  66 |     const imported = await importAssessmentPackage(page, fixture)
  67 |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  68 |     await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  69 |     await page.getByRole('radio', { name: '独立测试', exact: true }).check()
  70 |     await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  71 |     const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  72 |     await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  73 |     const response = await creating; expect(response.status()).toBe(201); const attempt: AttemptSnapshot = await response.json()
  74 |     expect(attempt.policy.mode).toBe('independent'); await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  75 |     const { palette, button } = await paletteImport(page)
  76 |     await expect(button).toBeDisabled(); await expect(page.locator('.import-trigger')).toBeDisabled()
  77 |     await expect(palette.getByRole('button', { name: /^查看快捷键/ })).toBeEnabled()
  78 |     await actualDisabledClick(page, button); await expect(palette).toBeVisible()
  79 |     await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
  80 |     expect((await page.request.get(`/api/v1/attempts/${attempt.id}`).then(r => r.json())).status).toBe('active')
  81 |     facts.actualIndependentAttemptDisabledBothEntries = true
  82 |     await palette.getByRole('button', { name: '关闭命令面板', exact: true }).click()
  83 |     await page.getByRole('button', { name: '放弃本次测试', exact: true }).click()
  84 |     const abandoning = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/attempts/${attempt.id}/abandon`))
  85 |     await page.getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click(); expect((await abandoning).status()).toBe(200)
  86 |     await expect(page.locator('.import-trigger')).toBeEnabled()
  87 |     await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
  88 |     const next = await paletteImport(page); await expect(next.button).toBeEnabled(); await next.button.click()
  89 |     await expect(page.getByRole('dialog', { name: '导入', exact: true }).getByText(/操作角色：(作者|学习者)$/)).toBeVisible()
  90 |     const final = await page.request.get(`/api/v1/attempts/${attempt.id}`).then(r => r.json())
  91 |     expect(final.status).toBe('abandoned'); expect(final.grading_status).toBe('not_graded')
  92 |     facts.explicitReadmissionOnlyAfterActualAbandon = true; facts.finalStatus = final.status
  93 |   } finally {
  94 |     writeFileSync(info.outputPath('actual-command-independent-policy.json'), JSON.stringify(facts, null, 2) + '\n')
  95 |     await runtime.close()
  96 |   }
  97 | })
  98 | 
```