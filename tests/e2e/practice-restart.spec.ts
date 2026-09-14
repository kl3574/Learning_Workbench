import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { WorkbenchSession } from '../../packages/contracts/generated/types'
import type { PracticeSession, PracticeSessionCreated } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { originalPracticePackage, importPracticePackage } from './practiceTestData'

async function readPractice(page: Page, id: string): Promise<PracticeSession> {
  const response = await page.request.get(`/api/v1/practice/sessions/${id}`)
  expect(response.status()).toBe(200)
  return response.json()
}

async function workbench(page: Page): Promise<WorkbenchSession> {
  const response = await page.request.get('/api/v1/workbench/session')
  expect(response.status()).toBe(200)
  return response.json()
}

test('same practice tab identity rejects changed frozen parent or child hashes and preserves the original session', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await RestartRuntime.start()
  const fixture = originalPracticePackage('practiceidentity')
  try {
    const browser = await runtime.openBrowser(playwright.chromium)
    const page = browser.pages()[0]
    await runtime.authenticateOnly(page)
    const imported = await importPracticePackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const preview = { practice_ref: fixture.practice, course_ref: fixture.course, lesson_ref: fixture.lesson }
    await page.goto(`${runtime.origin}/?practice=${encodeURIComponent(JSON.stringify(preview))}`)
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/practice/sessions'))
    await page.getByRole('button', { name: '开始此练习', exact: true }).click()
    const session: PracticeSessionCreated = await (await creating).json()
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    await expect.poll(async () => {
      const value = await workbench(page)
      return value.tabs.find(tab => tab.id === value.active_tab_id)?.context.attempt_id
    }).toBe(session.id)
    const before = await workbench(page)
    const active = before.tabs.find(tab => tab.id === before.active_tab_id)!
    const snapshot = await readPractice(page, session.id)
    const target = { ...preview, session_id: session.id }
    for (const altered of [
      { ...target, lesson_ref: { ...target.lesson_ref, sha256: '0'.repeat(64) } },
      { ...target, practice_ref: { ...target.practice_ref, sha256: '0'.repeat(64) } },
    ]) {
      await page.goto(`${runtime.origin}/?practice=${encodeURIComponent(JSON.stringify(altered))}`)
      await expect(page.getByRole('heading', { name: '无法打开此精确链接', exact: true })).toBeVisible()
      const rejected = await workbench(page)
      expect(rejected.course_ref).toEqual(before.course_ref)
      expect(rejected.active_tab_id).toBe(active.id)
      expect(rejected.tabs.find(tab => tab.id === active.id)?.context).toEqual(active.context)
      expect(await readPractice(page, session.id)).toEqual(snapshot)
      await page.getByRole('button', { name: '返回原标签', exact: true }).click()
      await expect(page.locator('.practice-content > h1')).toHaveText('五类参考练习：作答与帮助记录')
    }
    writeFileSync(info.outputPath('practice-frozen-navigation.json'), JSON.stringify({
      same_tab_identity: active.id, original_context: active.context,
      changed_parent_hash_rejected: true, changed_practice_hash_rejected: true,
      preserved_course_and_original_session: true,
    }, null, 2))
  } finally { await runtime.close() }
})

test('actual browser close and API restart retain practice identity, exposure and an unsynced local response', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start()
  const fixture = originalPracticePackage('practicerestart')
  const errors: string[] = [], answerRequests: string[] = []
  const observe = (page: Page) => {
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => { if (/\/practice\/sessions\/[^/]+\/solutions$/.test(request.url())) answerRequests.push(request.method()) })
  }
  try {
    const firstBrowser = await runtime.openBrowser(playwright.chromium)
    const page = firstBrowser.pages()[0]
    observe(page)
    await runtime.authenticateOnly(page)
    const imported = await importPracticePackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const target = { practice_ref: fixture.practice, course_ref: fixture.course, lesson_ref: fixture.lesson }
    await page.goto(`${runtime.origin}/?practice=${encodeURIComponent(JSON.stringify(target))}`)
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/practice/sessions'))
    await page.getByRole('button', { name: '开始此练习', exact: true }).click()
    const created = await creating
    expect(created.status()).toBe(201)
    const session: PracticeSessionCreated = await created.json()
    expect(session.practice_ref).toEqual(fixture.practice)
    expect(session.lesson_ref).toEqual(fixture.lesson)
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    await page.getByRole('navigation', { name: '本次练习题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
    const answer = page.getByLabel('第 2 题答案', { exact: true })
    const baseAnswer = '加法交换律'
    await answer.fill(baseAnswer)
    await page.getByLabel('第 2 题推导步骤', { exact: true }).fill('先观察两边的加数保持相同，再比较它们的次序。')
    await expect.poll(async () => (await readPractice(page, session.id)).responses.find(value => value.question_id === fixture.questions[1].id)?.answer).toBe(baseAnswer)
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const hinting = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/practice/sessions/${session.id}/hints`))
    await page.getByRole('button', { name: '获取 1 级规则提示', exact: true }).click()
    expect((await hinting).status()).toBe(200)
    await expect(page.getByRole('heading', { name: '本机规则提示 · 1 级', exact: true })).toBeVisible()
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const before = await readPractice(page, session.id)
    expect(before.assisted).toBe(true)
    expect(before.exposure_event_ids).toHaveLength(1)
    expect(before.status).toBe('active')
    expect(before.results).toBeNull()
    const progressBefore = await page.request.get('/api/v1/learning/progress').then(value => value.json())
    const responseRoute = `**/api/v1/practice/sessions/${session.id}/responses`
    // Real network failure leaves a durable local candidate; no API or storage mock.
    await page.route(responseRoute, route => route.abort('internetdisconnected'))
    const localAnswer = '本机未同步候选 🧠：我还需要区分交换律和结合律。'
    await answer.fill(localAnswer)
    await expect(page.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
    await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
    expect(await readPractice(page, session.id)).toEqual(before)
    await expect.poll(async () => {
      const value = await workbench(page)
      return value.tabs.find(tab => tab.id === value.active_tab_id)?.context.attempt_id
    }).toBe(session.id)
    await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
    const workbenchBefore = await workbench(page)
    const activeBefore = workbenchBefore.tabs.find(tab => tab.id === workbenchBefore.active_tab_id)!
    expect(activeBefore.context).toMatchObject({ view_kind: 'practice', active_ref: fixture.practice, attempt_id: session.id })
    const database = runtime.databaseIdentity()
    const connection = firstBrowser.browser()
    await runtime.closeBrowser()
    expect(connection?.isConnected()).toBe(false)
    await runtime.restartApiAfterBrowserClosed()
    expect(runtime.generations).toHaveLength(2)
    expect(runtime.databaseIdentity()).toEqual(database)

    const secondBrowser = await runtime.openBrowser(playwright.chromium)
    const restored = secondBrowser.pages()[0]
    observe(restored)
    await restored.route(responseRoute, route => route.abort('internetdisconnected'))
    await runtime.authenticateOnly(restored)
    await expect(restored.locator('.practice-content > h1')).toHaveText('五类参考练习：作答与帮助记录')
    await expect(restored.getByRole('heading', { name: '发现本机未同步作答', exact: true })).toBeVisible()
    expect(await readPractice(restored, session.id)).toEqual(before)
    const workbenchAfter = await workbench(restored)
    const activeAfter = workbenchAfter.tabs.find(tab => tab.id === workbenchAfter.active_tab_id)!
    expect(activeAfter.context).toEqual(activeBefore.context)
    expect(workbenchAfter.course_ref).toEqual(fixture.course)
    await restored.getByRole('button', { name: '恢复这份本机作答', exact: true }).click()
    await expect(restored.getByLabel('第 2 题答案', { exact: true })).toHaveValue(localAnswer)
    await expect(restored.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
    await expect(restored.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
    expect(await readPractice(restored, session.id)).toEqual(before)
    expect(await restored.request.get('/api/v1/learning/progress').then(value => value.json())).toEqual(progressBefore)
    expect(answerRequests).toEqual([])
    await restored.setViewportSize({ width: 390, height: 844 })
    await restored.getByLabel('第 2 题答案', { exact: true }).scrollIntoViewIfNeeded()
    expect(await restored.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    expect(await restored.locator('.practice-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
    await restored.screenshot({ path: info.outputPath('practice-restored-draft-390.png') })
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-practice-restart.json'), JSON.stringify({
      scope: 'Original author learnpack, actual browser closure and API stop/start; no state reset or injected practice session.',
      different_api_process_generations: new Set(runtime.generations).size, same_database_inode: true,
      practice_ref: fixture.practice, lesson_ref: fixture.lesson, active_context: activeAfter.context,
      practice_session_id: session.id, server_revision: before.revision,
      unchanged_server_session_and_progress: true, restored_unsynced_local_response: true,
      retained_question_index: 2, exposure_event_ids: before.exposure_event_ids,
      automatic_solution_requests: answerRequests, runtime_errors: errors,
    }, null, 2))
  } finally { await runtime.close() }
})
