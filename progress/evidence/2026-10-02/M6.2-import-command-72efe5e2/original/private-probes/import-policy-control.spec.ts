import { writeFileSync } from 'node:fs'
import { expect, test, type Route } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'

for (const timing of ['before_click', 'after_rejected_click'] as const) test(`controlled Policy release ${timing} with original fixture and import helper`, async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('gradingrecover')
  const facts: Record<string, unknown> = { baseline: 'c2f47a2778bb6a78c73237f8bb89fb271dfedcd6', fixture: 'originalAssessmentPackage(gradingrecover)', original_helper_unchanged: true, original_role_assertion_timeout_ms: 5000 }
  let release!: () => void, released = false, requests = 0, held = 0
  const gate = new Promise<void>(yes => { release = yes }), deliveries: Promise<void>[] = []
  const releaseGate = () => { released = true; release() }
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    const handler = (route: Route) => {
      const delivery = (async () => {
        if (route.request().method() !== 'GET' || ++requests === 1 || released) { await route.continue(); return }
        const response = await route.fetch(); expect(response.status()).toBe(200)
        const body = await response.json(); facts.actual_server_policy = { independent: body.active_independent_attempt_id, open_book: body.active_open_book_attempt_id, role: body.role }
        held++; await gate; await route.fulfill({ response })
      })(); deliveries.push(delivery); return delivery
    }
    await runtime.authenticateOnly(page)
    await page.route('**/api/v1/session', handler)
    await page.reload()
    await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toBeVisible()
    await expect.poll(() => held).toBeGreaterThan(0)
    await expect(page.locator('.import-trigger')).toBeDisabled()
    facts.ui_saved_while_policy_unknown = true
    facts.topbar_disabled = await page.locator('.import-trigger').isDisabled()
    if (timing === 'before_click') {
      releaseGate()
      await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toHaveCount(0)
      await expect(page.locator('.import-trigger')).toBeEnabled()
      const imported = await importAssessmentPackage(page, fixture)
      expect(imported.receipt.course_refs).toContainEqual(fixture.course)
      facts.original_helper_after_preclick_release = 'PASS'
    } else {
      let rejected: unknown
      const importing = importAssessmentPackage(page, fixture).catch(error => { rejected = error; return null })
      await expect(page.getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。', { exact: true })).toBeVisible()
      facts.original_palette_click_rejected = true
      releaseGate()
      await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toHaveCount(0)
      await expect(page.locator('.import-trigger')).toBeEnabled()
      await importing
      expect(rejected).toBeTruthy()
      expect(String(rejected)).toContain('Timeout: 5000ms')
      await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
      facts.original_assertion_failed_then_no_auto_replay = true
      const imported = await importAssessmentPackage(page, fixture)
      expect(imported.receipt.course_refs).toContainEqual(fixture.course)
      facts.fresh_original_helper_after_rejected_click = 'PASS'
    }
  } finally {
    releaseGate(); await Promise.allSettled(deliveries); facts.held_responses = held
    writeFileSync(info.outputPath(`controlled-${timing}.json`), JSON.stringify(facts, null, 2) + '\n')
    await runtime.close()
  }
})
