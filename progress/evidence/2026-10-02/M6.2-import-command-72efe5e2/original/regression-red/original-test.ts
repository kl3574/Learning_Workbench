import { writeFileSync } from 'node:fs'
import { expect, test, type Locator, type Page, type Route } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'

async function paletteImport(page: Page) {
  await page.keyboard.press('Control+Shift+P')
  const palette = page.getByRole('dialog', { name: '命令面板', exact: true })
  return { palette, button: palette.getByRole('button', { name: /^导入/ }) }
}
async function actualDisabledClick(page: Page, button: Locator) {
  const box = await button.boundingBox(); expect(box).not.toBeNull()
  await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height / 2)
}

test('command import remains disabled while Policy is unknown after UI saved and original import helper works only after explicit admission', async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('gradingrecover')
  const facts: Record<string, unknown> = {}, deliveries: Promise<void>[] = []
  let release!: () => void, released = false, requests = 0, held = 0, importWrites = 0
  const gate = new Promise<void>(yes => { release = yes }), releaseGate = () => { released = true; release() }
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/imports') importWrites++ })
    const handler = (route: Route) => {
      const delivery = (async () => {
        if (route.request().method() !== 'GET' || ++requests === 1 || released) { await route.continue(); return }
        const response = await route.fetch(); expect(response.status()).toBe(200)
        const actual = await response.json(); expect(actual.active_independent_attempt_id).toBeNull()
        held++; await gate; await route.fulfill({ response })
      })(); deliveries.push(delivery); return delivery
    }
    await page.route('**/api/v1/session', handler); await page.reload()
    await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
    await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toBeVisible()
    await expect.poll(() => held).toBeGreaterThan(0)
    await expect(page.locator('.import-trigger')).toBeDisabled()
    const { palette, button } = await paletteImport(page)
    await expect(button).toBeDisabled()
    await actualDisabledClick(page, button)
    await expect(palette).toBeVisible(); await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
    expect(importWrites).toBe(0); facts.unknownPolicyDisabledActualClick = true
    releaseGate(); await Promise.all(deliveries)
    await expect(button).toBeEnabled(); await expect(page.locator('.import-trigger')).toBeEnabled()
    await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0); expect(importWrites).toBe(0)
    facts.noAutomaticAdmissionAfterPermissionRecovery = true
    await palette.getByRole('button', { name: '关闭命令面板', exact: true }).click()
    const imported = await importAssessmentPackage(page, fixture)
    expect(imported.receipt.course_refs).toContainEqual(fixture.course); expect(importWrites).toBe(1)
    facts.originalFixtureAndUnchangedHelperSucceeded = true
    await page.screenshot({ path: info.outputPath('explicit-command-import-after-policy.png') })
  } finally {
    releaseGate(); await Promise.allSettled(deliveries); facts.actualPolicyResponsesHeld = held
    writeFileSync(info.outputPath('actual-command-unknown-policy.json'), JSON.stringify(facts, null, 2) + '\n')
    await runtime.close()
  }
})

test('command import keeps the actual independent attempt restriction and needs another explicit click after abandon', async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('commandindependent')
  const facts: Record<string, unknown> = {}
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page); await expect(page.locator('.import-trigger')).toBeEnabled()
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    await page.getByRole('radio', { name: '独立测试', exact: true }).check()
    await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
    await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
    const response = await creating; expect(response.status()).toBe(201); const attempt: AttemptSnapshot = await response.json()
    expect(attempt.policy.mode).toBe('independent'); await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const { palette, button } = await paletteImport(page)
    await expect(button).toBeDisabled(); await expect(page.locator('.import-trigger')).toBeDisabled()
    await expect(palette.getByRole('button', { name: /^查看快捷键/ })).toBeEnabled()
    await actualDisabledClick(page, button); await expect(palette).toBeVisible()
    await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
    expect((await page.request.get(`/api/v1/attempts/${attempt.id}`).then(r => r.json())).status).toBe('active')
    facts.actualIndependentAttemptDisabledBothEntries = true
    await palette.getByRole('button', { name: '关闭命令面板', exact: true }).click()
    await page.getByRole('button', { name: '放弃本次测试', exact: true }).click()
    const abandoning = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/attempts/${attempt.id}/abandon`))
    await page.getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click(); expect((await abandoning).status()).toBe(200)
    await expect(page.locator('.import-trigger')).toBeEnabled()
    await expect(page.getByRole('dialog', { name: '导入', exact: true })).toHaveCount(0)
    const next = await paletteImport(page); await expect(next.button).toBeEnabled(); await next.button.click()
    await expect(page.getByRole('dialog', { name: '导入', exact: true }).getByText(/操作角色：(作者|学习者)$/)).toBeVisible()
    const final = await page.request.get(`/api/v1/attempts/${attempt.id}`).then(r => r.json())
    expect(final.status).toBe('abandoned'); expect(final.grading_status).toBe('not_graded')
    facts.explicitReadmissionOnlyAfterActualAbandon = true; facts.finalStatus = final.status
  } finally {
    writeFileSync(info.outputPath('actual-command-independent-policy.json'), JSON.stringify(facts, null, 2) + '\n')
    await runtime.close()
  }
})
