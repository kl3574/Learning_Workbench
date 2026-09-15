import { writeFileSync } from 'node:fs'
import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'
import type { ContentRef, WorkbenchSession } from '../../packages/contracts/generated/types'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
import { RestartRuntime } from './restartRuntime'

const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page); await use(page)
  },
})

async function read(page: Page, path: string) {
  const response = await page.request.get(`/api/v1/${path}`)
  expect(response.status()).toBe(200)
  return response.json()
}

async function geometry(page: Page) {
  return page.evaluate(() => {
    const rect = (selector: string) => {
      const element = document.querySelector(selector)!, value = element.getBoundingClientRect()
      return { top: value.top, bottom: value.bottom, width: value.width, height: value.height, scrollTop: element.scrollTop, scrollHeight: element.scrollHeight }
    }
    return { viewport: [innerWidth, innerHeight], reader: rect('.reader-main'), scroll: rect('.assessment-scroll'), paragraph: rect('.practice-submit > p') }
  })
}

async function confirmSessionBeforeControlledConflict(page: Page, attempt: AttemptSnapshot, course: ContentRef) {
  const saved = page.getByText('✓ UI 会话已保存')
  const comparison = page.getByRole('region', { name: '会话三方比较', exact: true })
  await expect.poll(async () => await saved.count() > 0 || await comparison.count() > 0).toBe(true)
  const before: WorkbenchSession = await read(page, 'workbench/session')
  const explicitlyResolvedExistingConflict = await comparison.count() > 0
  if (explicitlyResolvedExistingConflict) {
    // The import/navigation setup may itself leave a real conflict. Make an
    // explicit user choice before installing the separate controlled gate.
    await comparison.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).click()
  }
  await expect(saved).toBeVisible()
  await expect(comparison).toHaveCount(0)
  const after: WorkbenchSession = await read(page, 'workbench/session')
  const active = after.tabs?.find(tab => tab.id === after.active_tab_id)
  expect(active?.context.attempt_id).toBe(attempt.id)
  expect(active?.context.active_ref).toEqual(attempt.assessment_ref)
  expect(after.course_ref).toEqual(course)
  const summary = (session: WorkbenchSession) => ({ revision: session.revision, active_tab_id: session.active_tab_id, active_context: session.tabs?.find(tab => tab.id === session.active_tab_id)?.context ?? null, course_ref: session.course_ref })
  return { explicitlyResolvedExistingConflict, before: summary(before), after: summary(after) }
}

async function holdRealSessionConflict(page: Page) {
  let continueRequest = () => {}, deliverResponse = () => {}
  const requestGate = new Promise<void>(resolve => { continueRequest = resolve })
  const responseGate = new Promise<void>(resolve => { deliverResponse = resolve })
  let gated = false, expectedRevision = 0, actualStatus = 0
  await page.route('**/api/v1/workbench/session', async route => {
    if (route.request().method() !== 'PUT' || gated) { await route.continue(); return }
    gated = true
    expectedRevision = (route.request().postDataJSON() as { expected_revision: number }).expected_revision
    await requestGate
    const actual = await route.fetch()
    actualStatus = actual.status()
    await responseGate
    // Deliver the server's original response without inventing a status, body or conflict.
    await route.fulfill({ response: actual })
  })
  return {
    async captureConflict() {
      await expect.poll(() => gated, { message: 'The controlled schedule requires an actual UI session PUT' }).toBe(true)
      const baseline: WorkbenchSession = await read(page, 'workbench/session')
      const auth: { csrf_token: string } = await read(page, 'session')
      const concurrent = await page.request.put('/api/v1/workbench/session', {
        headers: { Origin: new URL(page.url()).origin, 'X-CSRF-Token': auth.csrf_token },
        data: { expected_revision: baseline.revision, session: { ...baseline, nav_width: baseline.nav_width === 300 ? 301 : 300 } },
      })
      expect(concurrent.status()).toBe(200)
      const remote: WorkbenchSession = await concurrent.json()
      expect(remote.revision).toBeGreaterThan(expectedRevision)
      continueRequest()
      await expect.poll(() => actualStatus).toBeGreaterThan(0)
      expect(actualStatus).toBe(412)
      return remote
    },
    async deliver() {
      const delivered = page.waitForResponse(response => response.request().method() === 'PUT' && response.url().endsWith('/api/v1/workbench/session') && response.status() === 412)
      deliverResponse()
      await delivered
    },
    release() { continueRequest(); deliverResponse() },
    receipt() { return { expectedRevision, actualStatus } },
  }
}

test('real session conflict preserves the scrolled submitted explanation and requires an explicit comparison choice', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const fixture = originalAssessmentPackage('nativereaderconflict'), imported = await importAssessmentPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const created = await creating; expect(created.status()).toBe(201)
  const attempt: AttemptSnapshot = await created.json()
  await page.getByRole('radio', { name: '5', exact: true }).check()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
  const submitting = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/attempts/${attempt.id}/submit`))
  await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
  expect((await submitting).status()).toBe(202)
  await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible()
  await expect.poll(async () => (await read(page, `attempts/${attempt.id}`)).status).toBe('needs_review')
  const ended = await read(page, `attempts/${attempt.id}`)
  const responses = await read(page, `attempts/${attempt.id}/responses`)
  const result = await read(page, `attempts/${attempt.id}/result`)
  expect(ended.grading_status).toBe('needs_review')
  expect(ended.submitted_at).not.toBeNull()
  expect(result.items).toHaveLength(5)
  expect(result.items.every((item: { score: number | null; solution_markdown?: string | null }) => item.score === null && item.solution_markdown == null)).toBe(true)
  const setup = await confirmSessionBeforeControlledConflict(page, attempt, fixture.course)

  const gate = await holdRealSessionConflict(page)
  const observations: { stage: string; geometry: Awaited<ReturnType<typeof geometry>> }[] = []
  try {
    // Pinning is a real UI-session mutation even when the ended Reader has no
    // new scroll position to save. It keeps this exact attempt open.
    await page.locator('.object-tab.active .tab-pin').click()
    await page.setViewportSize({ width: 390, height: 844 })
    await page.mouse.move(8, 150)
    await page.mouse.wheel(0, -10_000)
    await expect.poll(() => page.locator('.assessment-scroll').evaluate(node => node.scrollTop)).toBe(0)
    await page.locator('.practice-submit > p').scrollIntoViewIfNeeded()
    const centered = await geometry(page)
    // Match the original regression's lower-pane reading position with actual
    // wheel movement; the incoming panel must leave this whole explanation visible.
    await page.mouse.wheel(0, centered.paragraph.bottom - centered.scroll.bottom + 1)
    await expect.poll(async () => {
      const current = await geometry(page)
      return Math.abs(current.paragraph.bottom - current.scroll.bottom + 1)
    }).toBeLessThanOrEqual(1)
    await page.locator('.practice-submit').scrollIntoViewIfNeeded()
    await expect(page.locator('.practice-submit > p')).toBeInViewport()
    const remote = await gate.captureConflict()
    observations.push({ stage: 'scrolled-before-real-412-delivery', geometry: await geometry(page) })
    await gate.deliver()
    const comparison = page.getByRole('region', { name: '会话三方比较', exact: true })
    await expect(comparison).toBeVisible()
    await expect(comparison).toBeInViewport()
    await expect(comparison.locator('details')).toHaveJSProperty('open', true)
    await expect(comparison).toContainText('原基准')
    await expect(comparison).toContainText('本地待同步')
    await expect(comparison).toContainText('服务端')
    await expect(comparison.getByRole('button', { name: '采用本地会话并重新保存', exact: true })).toBeEnabled()
    await expect(page.locator('.practice-submit > p')).toBeInViewport()
    expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    const after = await geometry(page)
    observations.push({ stage: 'real-conflict-visible-without-choice', geometry: after })
    expect(after.paragraph.top).toBeGreaterThanOrEqual(after.scroll.top)
    expect(after.paragraph.bottom).toBeLessThanOrEqual(after.scroll.bottom + 1)
    expect(await read(page, 'workbench/session')).toEqual(remote)
    expect(await read(page, `attempts/${attempt.id}`)).toEqual(ended)
    expect(await read(page, `attempts/${attempt.id}/responses`)).toEqual(responses)
    expect(await read(page, `attempts/${attempt.id}/result`)).toEqual(result)
    await expect(comparison).toBeVisible()
    await expect(page.getByText('会话版本冲突', { exact: true })).toBeVisible()
    expect(errors).toEqual([])
    await page.screenshot({ path: info.outputPath('reader-conflict-submitted-390.png') })
  } finally {
    gate.release()
    writeFileSync(info.outputPath('reader-conflict-layout-geometry.json'), JSON.stringify({ setup, ...gate.receipt(), observations }, null, 2) + '\n')
  }
})

test('real session conflict keeps the same enabled assessment input focused and visible in the shortened reader', async ({ page }, info) => {
  const fixture = originalAssessmentPackage('nativereaderfocusconflict'), imported = await importAssessmentPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const created = await creating; expect(created.status()).toBe(201)
  const attempt: AttemptSnapshot = await created.json()
  await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  const input = page.getByLabel('第 2 题答案', { exact: true })
  await input.fill('真实会话冲突前已保存的测试答案')
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  const setup = await confirmSessionBeforeControlledConflict(page, attempt, fixture.course)
  const active = await read(page, `attempts/${attempt.id}`)
  const responses = await read(page, `attempts/${attempt.id}/responses`)
  expect(active.status).toBe('active')
  expect(active.grading_status).toBe('not_graded')
  const focusedGeometry = () => input.evaluate(element => {
    const rect = element.getBoundingClientRect(), pane = element.closest('.reader-scroll')!, paneRect = pane.getBoundingClientRect()
    return { focused: document.activeElement === element, input: { top: rect.top, bottom: rect.bottom, height: rect.height }, pane: { top: paneRect.top, bottom: paneRect.bottom, scrollTop: pane.scrollTop }, viewportHeight: innerHeight }
  })
  const observations: { stage: string; geometry: Awaited<ReturnType<typeof focusedGeometry>> }[] = []
  const gate = await holdRealSessionConflict(page)
  try {
    await input.click()
    const positioned = await focusedGeometry()
    // Use the actual wheel/scroll pipeline to put the still-focused input in
    // the area the incoming comparison panel will occupy. No geometry is mocked.
    await page.mouse.move(8, positioned.pane.top + 24)
    await page.mouse.wheel(0, positioned.input.top - positioned.pane.top - 80)
    await expect.poll(async () => {
      const current = await focusedGeometry()
      return current.pane.scrollTop > 0 && current.input.top >= current.pane.top && current.input.top < current.pane.top + 150
    }).toBe(true)
    await expect(input).toBeFocused()
    await expect(input).toBeEnabled()
    const remote = await gate.captureConflict()
    const before = await focusedGeometry()
    observations.push({ stage: 'focused-upper-reader-before-real-412-delivery', geometry: before })
    await gate.deliver()
    const comparison = page.getByRole('region', { name: '会话三方比较', exact: true })
    await expect(comparison).toBeVisible()
    await expect(comparison.locator('details')).toHaveJSProperty('open', true)
    await expect(input).toBeFocused()
    await expect(input).toBeEnabled()
    await expect(input).toBeInViewport()
    const after = await focusedGeometry()
    observations.push({ stage: 'same-focus-visible-with-real-comparison', geometry: after })
    // The test must exercise the risky geometry: full compensation would put
    // the input above the new pane, despite leaving document.activeElement set.
    expect(before.input.bottom).toBeLessThan(after.pane.top)
    expect(after.input.top).toBeGreaterThanOrEqual(after.pane.top)
    expect(after.input.bottom).toBeLessThanOrEqual(after.pane.bottom)
    expect(after.input.bottom).toBeLessThanOrEqual(after.viewportHeight)
    expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    expect(await read(page, 'workbench/session')).toEqual(remote)
    expect(await read(page, `attempts/${attempt.id}`)).toEqual(active)
    expect(await read(page, `attempts/${attempt.id}/responses`)).toEqual(responses)
    await expect(page.getByText('会话版本冲突', { exact: true })).toBeVisible()
    await page.screenshot({ path: info.outputPath('reader-conflict-focused-input-390.png') })
  } finally {
    gate.release()
    writeFileSync(info.outputPath('reader-conflict-focus-geometry.json'), JSON.stringify({ setup, ...gate.receipt(), observations }, null, 2) + '\n')
  }
})
