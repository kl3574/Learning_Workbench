import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { ContentRef, LearnerProfile, Route } from '../../packages/contracts/generated/types'
import type { ConceptStateResponse, LearningProgress, PageRoute, ProfileWrite } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importPracticePackage, originalPracticePackage } from './practiceTestData'

async function profile(page: Page): Promise<LearnerProfile> {
  const response = await page.request.get('/api/v1/learner/profile')
  expect(response.status()).toBe(200)
  return response.json()
}
async function progress(page: Page): Promise<LearningProgress> {
  const response = await page.request.get('/api/v1/learning/progress')
  expect(response.status()).toBe(200)
  return response.json()
}
async function conceptStates(page: Page, course: ContentRef): Promise<ConceptStateResponse> {
  const response = await page.request.get(`/api/v1/learning/concept-states?course_id=${course.id}`)
  expect(response.status()).toBe(200)
  return response.json()
}
async function headers(page: Page, runtime: RestartRuntime, command: string) {
  const response = await page.request.get('/api/v1/session')
  expect(response.status()).toBe(200)
  return { Origin: runtime.origin, 'X-CSRF-Token': (await response.json()).csrf_token as string, 'Idempotency-Key': command }
}
async function openProfile(page: Page) {
  await page.getByRole('button', { name: '设置', exact: true }).click()
  await page.getByRole('dialog', { name: '设置', exact: true }).getByRole('button', { name: '学习目标与基础', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '学习目标与基础', exact: true })
  await expect(dialog.getByLabel('学习目标', { exact: true })).toBeVisible()
  return dialog
}
function noDiagnosticEvidence(value: ConceptStateResponse) {
  expect(value.calibration).toBe('uncalibrated')
  expect(value.concepts.length).toBeGreaterThan(0)
  // The original fixture declares actual dimensions, so this is not a vacuous
  // all([]) assertion. Neither native reading nor self-report may diagnose them.
  expect(value.items.length).toBeGreaterThan(0)
  for (const item of value.items) {
    expect(item).toMatchObject({ evidence_state: 'none', independent_count: 0, assisted_count: 0,
      practice_submission_count: 0, hint_count: 0, solution_count: 0, evidence_ids: [], state_input_evidence_ids: [], sources: [] })
  }
}

test('actual browser and API restarts preserve profile candidates, exact route overrides and original reading sources', async ({ playwright }, info) => {
  test.setTimeout(150_000)
  const runtime = await RestartRuntime.start(), fixture = originalPracticePackage('learningstaterestart')
  const errors: string[] = []
  const observe = (page: Page) => page.on('pageerror', error => errors.push(error.message))
  try {
    const firstBrowser = await runtime.openBrowser(playwright.chromium), page = firstBrowser.pages()[0]
    observe(page)
    await runtime.authenticateOnly(page)
    const initialProfile = await profile(page)
    expect(initialProfile.revision).toBe(1)
    const imported = await importPracticePackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const initialStates = await conceptStates(page, fixture.course)
    noDiagnosticEvidence(initialStates)
    const concept = initialStates.concepts[0]

    // Explicit synthetic route setup uses only the real published API. The
    // original learnpack remains unreviewed; no approval or grade is injected.
    const originalRoute: Route = { schema_version: '3.0.0', entity: 'route', id: 'route_learning_state_restart', revision: 1,
      title: '原创重启验收路线', goal: '分别核对阅读事实与人工路线状态', steps: [
        { id: 'step_manual', title: '人工前置提醒', target: fixture.block, completion_rule: 'manual', requires_steps: [] },
        { id: 'step_read', title: '阅读真实导入章节', target: fixture.lesson, completion_rule: 'read', requires_steps: ['step_manual'] },
      ] }
    const created = await page.request.post('/api/v1/routes', { headers: await headers(page, runtime, 'restart-route-create'), data: originalRoute })
    expect(created.status()).toBe(201)
    const firstRoute: ContentRef = await created.json()
    await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
    const reading = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/learning/actions'))
    await page.getByRole('button', { name: '明确标记本节已读', exact: true }).click()
    const readReceipt = await reading
    expect(readReceipt.status()).toBe(200)
    const originalRead = await readReceipt.json()
    const readProgress = await progress(page)
    const automaticallyCompleted = readProgress.route_steps.find(step => step.step_id === 'step_read')!
    expect(automaticallyCompleted).toMatchObject({ route_ref: firstRoute, completed: true, completion_origin: 'read',
      manual_override: null, source_event_ids: [originalRead.event_id], unmet_requires_steps: ['step_manual'] })
    expect(automaticallyCompleted.completed_at).toBeTruthy()
    const cancel = await page.request.post(`/api/v1/routes/${firstRoute.id}/steps/step_read/complete`, {
      headers: await headers(page, runtime, 'restart-route-manual-false'),
      data: { route_revision: firstRoute.revision, expected_progress_revision: readProgress.revision, completed: false, origin: 'manual' },
    })
    expect(cancel.status()).toBe(200)
    const cancelReceipt = await cancel.json()
    const updatedRoute: Route = { ...originalRoute, revision: 2, title: '原创重启验收路线 · 新修订' }
    const updated = await page.request.put(`/api/v1/routes/${firstRoute.id}`, {
      headers: { ...await headers(page, runtime, 'restart-route-update'), 'If-Match': `"${firstRoute.sha256}"` }, data: updatedRoute,
    })
    expect(updated.status()).toBe(200)
    const secondRoute: ContentRef = await updated.json()
    const beforeProgress = await progress(page)
    expect(beforeProgress.route_steps.find(step => step.route_ref.revision === 1 && step.step_id === 'step_read')).toMatchObject({
      completed: false, completion_origin: 'manual', manual_override: false, completed_at: null, source_event_ids: [cancelReceipt.event_id],
    })
    expect(beforeProgress.route_steps.find(step => step.route_ref.revision === 2 && step.step_id === 'step_read')).toEqual({
      ...automaticallyCompleted, route_ref: secondRoute,
    })
    const beforeRoutesResponse = await page.request.get('/api/v1/routes')
    expect(beforeRoutesResponse.status()).toBe(200)
    const beforeRoutes: PageRoute = await beforeRoutesResponse.json()
    expect(beforeRoutes.items).toEqual([originalRoute, updatedRoute])

    const panel = await openProfile(page)
    await panel.getByRole('button', { name: '编辑学习目标与基础', exact: true }).click()
    await panel.getByLabel('学习目标', { exact: true }).fill('原始已保存目标：核对数量关系')
    await panel.getByLabel('每周学习分钟数', { exact: true }).fill('150')
    await panel.getByLabel(`自报基础：${concept.title}`, { exact: true }).selectOption('encountered')
    const saving = page.waitForResponse(response => response.request().method() === 'PUT' && response.url().endsWith('/api/v1/learner/profile'))
    await panel.getByRole('button', { name: '保存学习目标与基础', exact: true }).click()
    expect((await saving).status()).toBe(200)
    await expect(panel.getByRole('status')).toHaveText(/画像已保存到服务端.*本机画像草稿存储可用/)
    const beforeProfile = await profile(page)
    expect(beforeProfile.revision).toBe(2)
    expect(beforeProfile.self_assessments).toContainEqual(expect.objectContaining({ concept_id: concept.ref.id, level: 'encountered', origin: 'self_report' }))
    noDiagnosticEvidence(await conceptStates(page, fixture.course))

    const offlineGoal = '本机未同步目标 🧠：独立解释步骤；恢复后再明确保存'
    await page.route('**/api/v1/learner/profile', route => route.request().method() === 'PUT' ? route.abort('internetdisconnected') : route.continue())
    await panel.getByLabel('学习目标', { exact: true }).fill(offlineGoal)
    await panel.getByLabel(`自报基础：${concept.title}`, { exact: true }).selectOption('independent_use')
    await panel.getByRole('button', { name: '保存学习目标与基础', exact: true }).click()
    await expect(panel.getByRole('alert').filter({ hasText: '画像尚未确认保存' })).toBeVisible()
    await expect(panel.getByRole('status')).toHaveText(/画像更改尚未同步.*本机画像草稿存储可用/)
    expect(await profile(page)).toEqual(beforeProfile)
    const database = runtime.databaseIdentity(), connection = firstBrowser.browser()
    await runtime.closeBrowser()
    expect(connection?.isConnected()).toBe(false)
    await runtime.restartApiAfterBrowserClosed()
    expect(runtime.databaseIdentity()).toEqual(database)

    const secondBrowser = await runtime.openBrowser(playwright.chromium), restored = secondBrowser.pages()[0]
    observe(restored)
    await runtime.authenticateOnly(restored)
    expect(await profile(restored)).toEqual(beforeProfile)
    expect(await progress(restored)).toEqual(beforeProgress)
    expect(await (await restored.request.get('/api/v1/routes')).json()).toEqual(beforeRoutes)
    // A separate real command advances the authoritative profile. Recovery
    // must still display the candidate's original revision-2 baseline.
    const remoteWrite: ProfileWrite = { expected_revision: beforeProfile.revision, goals: ['另一个实际命令保存的目标'],
      goal_concept_ids: beforeProfile.goal_concept_ids ?? [], weekly_minutes: 240, language: beforeProfile.language ?? 'zh-CN',
      preferred_difficulty: beforeProfile.preferred_difficulty ?? 'beginner',
      self_assessments: (beforeProfile.self_assessments ?? []).map(item => ({ concept_id: item.concept_id, level: item.level })) }
    const remoteSave = await restored.request.put('/api/v1/learner/profile', {
      headers: await headers(restored, runtime, 'restart-profile-remote-change'), data: remoteWrite,
    })
    expect(remoteSave.status()).toBe(200)
    const remoteProfile: LearnerProfile = await remoteSave.json()
    expect(remoteProfile.revision).toBe(3)
    const recovered = await openProfile(restored)
    await expect(recovered.getByRole('heading', { name: '发现本机画像候选', exact: true })).toBeVisible()
    await recovered.getByRole('button', { name: '恢复画像候选 1', exact: true }).click()
    await expect(recovered.getByLabel('学习目标', { exact: true })).toHaveValue(offlineGoal)
    await expect(recovered.getByRole('heading', { name: '比较原基准、本页与服务端画像', exact: true })).toBeVisible()
    await expect(recovered.getByRole('heading', { name: '原基准 · 修订 2', exact: true })).toBeVisible()
    await expect(recovered.getByRole('heading', { name: '服务端 · 修订 3', exact: true })).toBeVisible()
    expect(await profile(restored)).toEqual(remoteProfile)
    await recovered.getByRole('button', { name: '保留本页画像并采用服务端基准', exact: true }).click()
    const confirming = restored.waitForResponse(response => response.request().method() === 'PUT' && response.url().endsWith('/api/v1/learner/profile'))
    await recovered.getByRole('button', { name: '保存学习目标与基础', exact: true }).click()
    expect((await confirming).status()).toBe(200)
    await expect(recovered.getByRole('status')).toHaveText(/画像已保存到服务端.*本机画像草稿存储可用/)
    const confirmedProfile = await profile(restored)
    expect(confirmedProfile).toMatchObject({ revision: 4, goals: [offlineGoal], weekly_minutes: 150 })
    expect(confirmedProfile.self_assessments).toContainEqual(expect.objectContaining({ concept_id: concept.ref.id, level: 'independent_use', origin: 'self_report' }))
    const confirmedStates = await conceptStates(restored, fixture.course)
    noDiagnosticEvidence(confirmedStates)
    for (const row of confirmedStates.items) expect(row.self_report).toEqual(confirmedProfile.self_assessments?.find(item => item.concept_id === row.concept_id) ?? null)
    await runtime.closeBrowser()
    await runtime.restartApiAfterBrowserClosed()
    expect(runtime.databaseIdentity()).toEqual(database)
    const thirdBrowser = await runtime.openBrowser(playwright.chromium), finalPage = thirdBrowser.pages()[0]
    observe(finalPage)
    await runtime.authenticateOnly(finalPage)
    expect(await profile(finalPage)).toEqual(confirmedProfile)
    expect(await progress(finalPage)).toEqual(beforeProgress)
    expect(await conceptStates(finalPage, fixture.course)).toEqual(confirmedStates)
    expect(await (await finalPage.request.get('/api/v1/routes')).json()).toEqual(beforeRoutes)
    const finalPanel = await openProfile(finalPage)
    await expect(finalPanel.getByLabel('学习目标', { exact: true })).toHaveValue(offlineGoal)
    await expect(finalPanel.getByRole('heading', { name: '发现本机画像候选', exact: true })).not.toBeVisible()
    await finalPage.screenshot({ path: info.outputPath('learning-profile-confirmed-1440.png') })
    await finalPage.setViewportSize({ width: 390, height: 844 })
    await expect(finalPanel.getByRole('heading', { name: '学习目标与基础', exact: true })).toBeInViewport()
    await expect(finalPanel.getByRole('button', { name: '关闭学习目标与基础', exact: true })).toBeInViewport()
    expect(await finalPage.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    expect(await finalPanel.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
    await finalPage.screenshot({ path: info.outputPath('learning-profile-confirmed-390.png') })
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-learning-state-restart.json'), JSON.stringify({
      scope: 'Original synthetic learnpack, real HTTP route setup, native Reader/profile controls, persisted Chrome profile and two actual API stop/start cycles. No expert approval, grading or external provider.',
      actual_api_process_generations: runtime.generations.length, same_database_inode: runtime.databaseIdentity().inode === database.inode,
      course_ref: fixture.course, original_read_event_id: originalRead.event_id, route_refs: [firstRoute, secondRoute],
      route_progress: beforeProgress.route_steps, original_server_profile: beforeProfile, intervening_server_profile: remoteProfile,
      final_server_profile: confirmedProfile, original_candidate_revision: beforeProfile.revision,
      complete_route_history_retained: true, latest_profile_and_self_report_timestamps_retained: true,
      self_report_and_reading_add_no_diagnostic_evidence: true, final_concept_states: confirmedStates, runtime_errors: errors,
    }, null, 2))
  } finally { await runtime.close() }
})
