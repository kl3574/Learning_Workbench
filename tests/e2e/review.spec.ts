import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import { RestartRuntime } from './restartRuntime'
import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
import { observeNextResponseJson } from './responseJsonBarrier'
import type { AssessmentGradingResult, AttemptSnapshot, PageEvidence } from '../../packages/contracts/generated/api-types'
type SetupPhase = 'fixture-enter' | 'runtime-start' | 'runtime-ready' | 'browser-open' | 'browser-opened' | 'authentication-start' | 'authentication-complete' | 'page-use' | 'body-enter' | 'body-finally' | 'fixture-finally'
  | 'assessment-fixture-build' | 'assessment-fixture-built' | 'assessment-import' | 'assessment-imported' | 'assessment-dialog-close' | 'assessment-dialog-closed' | 'assessment-goto' | 'assessment-goto-returned' | 'assessment-confirm-start' | 'assessment-confirmed' | 'assessment-created-ack' | 'assessment-saved-visible'
  | 'manual-role-click' | 'manual-role-clicked' | 'manual-form-open' | 'manual-form-opened' | 'manual-reason-fill' | 'manual-reason-filled' | 'manual-item-1' | 'manual-item-2' | 'manual-item-3' | 'manual-item-4' | 'manual-item-5' | 'manual-confirm' | 'manual-confirmed'
  | 'grade-first-enter' | 'grade-first-returned' | 'grade-second-enter' | 'grade-second-returned' | 'grade-other-enter' | 'grade-other-returned'
type SetupCaller = 'initial-grade-poll' | 'manual-grade-poll' | 'later-grade-poll'
type SetupTiming = { mark: (stage: SetupPhase) => void; poll: (caller: SetupCaller, status: number, duration: number) => void; save: (boundary: 'body-finally' | 'fixture-finally') => void }
const setupTimingByPage = new WeakMap<Page, SetupTiming>()
const test = base.extend<{ runtime: RestartRuntime; setupTiming: SetupTiming }>({
  // Test-scoped and inside the original timeout. No fixture is moved to worker scope.
  setupTiming: [async ({}, use, info) => {
    const enabled = info.title === 'real history and exact material review preserve original submitted text, null scores and a selected old revision after reload'
    const started = performance.now(), phases: { sequence: number; elapsed_ms: number; stage: SetupPhase }[] = []
    const polls: { sequence: number; elapsed_ms: number; caller: SetupCaller; route: '/api/v1/attempts/:id/result'; method: 'GET'; status: number; request_elapsed_ms: number }[] = []
    let sequence = 0, phaseDropped = 0, pollDropped = 0, saved = false
    const observer: SetupTiming = {
      mark(stage) { if (!enabled) return; if (phases.length === 256) { phaseDropped++; return }; phases.push({ sequence: ++sequence, elapsed_ms: performance.now() - started, stage }) },
      poll(caller, status, duration) {
        if (!enabled || !Number.isInteger(status) || status < 100 || status > 599 || !Number.isFinite(duration) || duration < 0) return
        if (polls.length === 64) { pollDropped++; return }
        polls.push({ sequence: ++sequence, elapsed_ms: performance.now() - started, caller, route: '/api/v1/attempts/:id/result', method: 'GET', status, request_elapsed_ms: duration })
      },
      save(boundary) {
        if (!enabled || saved) return
        saved = true
        try {
          writeFileSync(info.outputPath('review-history-setup-helper-timing.json'), JSON.stringify({
            version: 'review-setup-helper-metadata-v1', clock: 'Node performance.now milliseconds since test-scoped observer fixture entry',
            observed_timeout_ms: info.timeout, retry: info.retry, saved_at_boundary: boundary, phases, polls,
            dropped: { phases: phaseDropped, polls: pollDropped }, limits: { phases: 256, polls: 64 },
            scope: 'Original runtime/page fixture and start/manual/grade helper boundaries. Existing page.request result polling records only fixed caller/route, status and elapsed time. No new request, JSON, query, header, body, ID, URL, DOM, React state, form or authentication value. Body-finally freeze excludes teardown; fixture-finally fallback covers setup failure. Worker/browser-runner setup before this fixture and JSON/React completion remain unobserved. Synchronous instrumentation changes scheduling; no cause or repair verdict.',
          }, null, 2), { flag: 'wx' })
        } catch { info.annotations.push({ type: 'diagnostic', description: 'Bounded setup/helper metadata could not be saved; original outcome preserved.' }) }
      },
    }
    observer.mark('fixture-enter')
    try { await use(observer) } finally { observer.mark('fixture-finally'); observer.save('fixture-finally') }
  }, { auto: true }],
  runtime: async ({ setupTiming }, use) => { setupTiming.mark('runtime-start'); const runtime = await RestartRuntime.start(); setupTiming.mark('runtime-ready'); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright, setupTiming }, use) => {
    setupTiming.mark('browser-open'); const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; setupTiming.mark('browser-opened')
    setupTimingByPage.set(page, setupTiming); setupTiming.mark('authentication-start'); await runtime.authenticateOnly(page); setupTiming.mark('authentication-complete')
    setupTiming.mark('page-use'); try { await use(page) } finally { setupTimingByPage.delete(page) }
  },
})
async function start(page: Page, prefix: string) {
  const timing = setupTimingByPage.get(page)
  timing?.mark('assessment-fixture-build'); const fixture = originalAssessmentPackage(prefix); timing?.mark('assessment-fixture-built')
  timing?.mark('assessment-import'); const imported = await importAssessmentPackage(page, fixture); timing?.mark('assessment-imported')
  timing?.mark('assessment-dialog-close')
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  timing?.mark('assessment-dialog-closed'); timing?.mark('assessment-goto')
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  timing?.mark('assessment-goto-returned'); timing?.mark('assessment-confirm-start')
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  timing?.mark('assessment-confirmed')
  const created = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); expect((await created).status()).toBe(201)
  timing?.mark('assessment-created-ack')
  const attempt: AttemptSnapshot = await (await created).json()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  timing?.mark('assessment-saved-visible')
  return { fixture, attempt }
}
async function grade(page: Page, id: string, revision: number): Promise<AssessmentGradingResult> {
  const timing = setupTimingByPage.get(page), caller: SetupCaller = revision === 1 ? 'initial-grade-poll' : revision === 2 ? 'manual-grade-poll' : 'later-grade-poll'
  timing?.mark(revision === 1 ? 'grade-first-enter' : revision === 2 ? 'grade-second-enter' : 'grade-other-enter')
  let result: AssessmentGradingResult | undefined
  await expect.poll(async () => { const started = performance.now(); const response = await page.request.get(`/api/v1/attempts/${id}/result`); timing?.poll(caller, response.status(), performance.now() - started); if (response.status() === 202) return 0; expect(response.status()).toBe(200); result = await response.json(); return result!.grading_revision }).toBe(revision)
  timing?.mark(revision === 1 ? 'grade-first-returned' : revision === 2 ? 'grade-second-returned' : 'grade-other-returned')
  return result!
}
async function submit(page: Page) { await page.getByRole('button', { name: '提交本次测试', exact: true }).click(); await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible() }
async function manual(page: Page) {
  const timing = setupTimingByPage.get(page)
  timing?.mark('manual-role-click'); await page.getByRole('button', { name: '切换为作者角色以人工复核', exact: true }).click(); timing?.mark('manual-role-clicked')
  timing?.mark('manual-form-open'); await page.getByRole('button', { name: '填写人工复核', exact: true }).click(); timing?.mark('manual-form-opened')
  timing?.mark('manual-reason-fill')
  await page.getByLabel('人工复核理由', { exact: true }).fill('原创软件复盘验收：显式逐项给分，不代表参考内容获批。')
  timing?.mark('manual-reason-filled')
  for (let i = 1; i <= 5; i++) { await page.getByRole('checkbox', { name: `复核第 ${i} 题`, exact: true }).check(); await page.getByLabel(`第 ${i} 题人工分数`, { exact: true }).fill(i === 2 ? '1' : '0'); await page.getByLabel(`第 ${i} 题复核依据`, { exact: true }).fill(`原创第 ${i} 项当前复核依据，不把推导正确性或审核状态从分数推出。`); timing?.mark((['manual-item-1', 'manual-item-2', 'manual-item-3', 'manual-item-4', 'manual-item-5'] as const)[i - 1]) }
  timing?.mark('manual-confirm')
  await page.getByRole('button', { name: '提交人工复核', exact: true }).click(); await page.getByRole('button', { name: '确认提交人工分数与依据', exact: true }).click()
  timing?.mark('manual-confirmed')
}
async function settleLayout(page: Page) { const choice = page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }); if (await choice.isVisible()) { await choice.click(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible() } }

test('real history and exact material review preserve original submitted text, null scores and a selected old revision after reload', async ({ page, setupTiming }, info) => {
  // BEGIN REVIEW_HISTORY_TIMING_OBSERVER: metadata only; no request or response bodies.
  type ObservedRequest = import('../../apps/web/node_modules/@playwright/test/index.mjs').Request
  type ObservedResponse = import('../../apps/web/node_modules/@playwright/test/index.mjs').Response
  const timingStarted = performance.now(), timingStartedAt = new Date().toISOString()
  let timingSequence = 0, timingPhaseDropped = 0, timingHttpDropped = 0
  const timingPhases: { sequence: number; elapsed_ms: number; stage: string }[] = []
  const timingHttp: { sequence: number; elapsed_ms: number; event: string; route: string; method: string; status?: number; request_elapsed_ms?: number }[] = []
  const timingRoutes: [RegExp, string][] = [
    [/^\/api\/v1\/session$/, '/api/v1/session'], [/^\/api\/v1\/session\/role$/, '/api/v1/session/role'],
    [/^\/api\/v1\/workbench\/session$/, '/api/v1/workbench/session'],
    [/^\/api\/v1\/imports$/, '/api/v1/imports'], [/^\/api\/v1\/imports\/[^/]+$/, '/api/v1/imports/:id'],
    [/^\/api\/v1\/imports\/[^/]+\/commit$/, '/api/v1/imports/:id/commit'],
    [/^\/api\/v1\/jobs\/[^/]+$/, '/api/v1/jobs/:id'],
    [/^\/api\/v1\/assessments\/[^/]+\/attempts$/, '/api/v1/assessments/:id/attempts'],
    [/^\/api\/v1\/attempts\/[^/]+$/, '/api/v1/attempts/:id'],
    [/^\/api\/v1\/attempts\/[^/]+\/responses$/, '/api/v1/attempts/:id/responses'],
    [/^\/api\/v1\/attempts\/[^/]+\/submit$/, '/api/v1/attempts/:id/submit'],
    [/^\/api\/v1\/attempts\/[^/]+\/result$/, '/api/v1/attempts/:id/result'],
    [/^\/api\/v1\/attempts\/[^/]+\/regrade$/, '/api/v1/attempts/:id/regrade'],
    [/^\/api\/v1\/questions\/[^/]+$/, '/api/v1/questions/:id'],
    [/^\/api\/v1\/courses\/[^/]+$/, '/api/v1/courses/:id'],
    [/^\/api\/v1\/lessons\/[^/]+$/, '/api/v1/lessons/:id'],
    [/^\/api\/v1\/blocks\/[^/]+$/, '/api/v1/blocks/:id'],
    [/^\/api\/v1\/blocks\/[^/]+\/body$/, '/api/v1/blocks/:id/body'],
    [/^\/api\/v1\/learning\/evidence$/, '/api/v1/learning/evidence'],
  ]
  const timingPending = new WeakMap<ObservedRequest, { route: string; method: string; started: number }>()
  const timingPhase = (stage: string) => {
    if (timingPhases.length === 128) { timingPhaseDropped++; return }
    timingPhases.push({ sequence: ++timingSequence, elapsed_ms: performance.now() - timingStarted, stage })
  }
  const timingRequest = (request: ObservedRequest) => {
    const path = new URL(request.url()).pathname, route = timingRoutes.find(([pattern]) => pattern.test(path))?.[1]
    const method = request.method()
    if (!route || !['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'].includes(method)) return
    timingPending.set(request, { route, method, started: performance.now() })
    timingEvent(request, 'request')
  }
  const timingEvent = (request: ObservedRequest, event: string, status?: number) => {
    const value = timingPending.get(request)
    if (!value) return
    if (timingHttp.length === 512) { timingHttpDropped++; return }
    timingHttp.push({ sequence: ++timingSequence, elapsed_ms: performance.now() - timingStarted, event,
      route: value.route, method: value.method, ...(status === undefined ? {} : { status }),
      ...(event === 'request' ? {} : { request_elapsed_ms: performance.now() - value.started }) })
  }
  const timingResponse = (response: ObservedResponse) => timingEvent(response.request(), 'response-headers', response.status())
  const timingFinished = (request: ObservedRequest) => timingEvent(request, 'request-finished')
  const timingFailed = (request: ObservedRequest) => timingEvent(request, 'request-failed')
  page.on('request', timingRequest); page.on('response', timingResponse)
  page.on('requestfinished', timingFinished); page.on('requestfailed', timingFailed)
  // Synchronous memory marks add measurement overhead, not waits or a new budget.
  // Browser HTTP events exclude page.request polling and do not prove JSON/React completion.
  // END REVIEW_HISTORY_TIMING_OBSERVER
  try {
  timingPhase('body-enter')
  setupTiming.mark('body-enter')
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  timingPhase('assessment-start')
  const { fixture, attempt } = await start(page, 'reviewnativehistory')
  timingPhase('question-select')
  await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  timingPhase('answer-constants')
  const answer = '交卷原始答案 🧠é', steps = '原始推导第一行\n\\alpha < beta\n**按原文保留**'
  timingPhase('answer-fill')
  await page.getByLabel('第 2 题答案', { exact: true }).fill(answer); await page.getByLabel('第 2 题推导步骤', { exact: true }).fill(steps)
  timingPhase('responses-persisted')
  await expect.poll(async () => { const value = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json()); return value.responses.find((item: { question_id: string }) => item.question_id === fixture.questions[1].id) }).toMatchObject({ answer, steps_markdown: steps })
  timingPhase('submit')
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible(); await submit(page)
  timingPhase('initial-grading')
  const first = await grade(page, attempt.id, 1)
  timingPhase('initial-history-assert')
  expect(first.history).toHaveLength(1); expect(first.items.every(item => item.score === null)).toBe(true)
  timingPhase('responses-snapshot')
  const responses = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json())
  timingPhase('review-open')
  await settleLayout(page); await page.getByRole('button', { name: '打开本次测试复盘', exact: true }).click()
  timingPhase('review-heading')
  await expect(page.getByRole('heading', { name: '本次测试复盘', exact: true })).toBeVisible()
  timingPhase('review-question-select')
  await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  timingPhase('submitted-text-assert')
  await expect(page.getByLabel('第 2 题已提交答案', { exact: true })).toHaveText(answer); await expect(page.getByLabel('第 2 题已提交推导步骤', { exact: true })).toHaveText(steps)
  timingPhase('readonly-input-assert')
  expect(await page.getByRole('region', { name: '第 2 题交卷原文', exact: true }).locator('input,textarea').count()).toBe(0)
  timingPhase('material-eligibility')
  await expect(page.getByRole('region', { name: '本题证据资格', exact: true })).toContainText('冻结的参考答案尚未审核')
  timingPhase('manual-review-and-grade')
  await manual(page); const final = await grade(page, attempt.id, 2)
  timingPhase('history-immutability')
  expect(final.history.map(entry => entry.grading_revision)).toEqual([1, 2]); expect(final.history[0]).toEqual(first.history[0]); expect(final.history[1].items.every(item => !item.eligible && item.reason_codes.includes('ANSWER_UNREVIEWED'))).toBe(true)
  timingPhase('current-policy-assert')
  expect(final.current_review_policy).toEqual({ tutor_scope: 'academic', allow_materials: true, allow_web: false })
  timingPhase('current-result-assert')
  await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toContainText('评分版本 2')
  timingPhase('history-region')
  const history = page.getByRole('region', { name: '完整评分历史', exact: true })
  timingPhase('history-select-old')
  await expect(history.getByLabel('选择评分版本')).toHaveValue('2'); await history.getByLabel('选择评分版本').selectOption('1'); await expect(history).toContainText('本题在版本 1：待复核 · 分数为空')
  timingPhase('history-comparison')
  await history.locator('summary').filter({ hasText: '比较评分版本' }).click(); await history.getByLabel('对照评分版本').selectOption('2'); await expect(history.getByRole('table')).toContainText('1 / 1')
  timingPhase('history-no-private-body')
  expect(final.history.every(entry => entry.items.every(item => !('feedback_markdown' in item) && !('solution_markdown' in item)))).toBe(true)
  timingPhase('desktop-screenshot')
  await page.setViewportSize({ width: 1440, height: 900 }); await history.getByRole('heading', { name: '评分版本与证据' }).evaluate(node => node.scrollIntoView({ block: 'start' })); await page.screenshot({ path: info.outputPath('review-history-after-1440.png') })
  timingPhase('reload-old-selection')
  await settleLayout(page); await page.reload(); timingPhase('reload-returned'); await expect(history.getByLabel('选择评分版本')).toHaveValue('1'); await expect(page.getByLabel('第 2 题已提交答案')).toHaveText(answer)
  timingPhase('exact-material-open')
  const material = page.getByRole('region', { name: '本题对应教材', exact: true }); await material.getByRole('button', { name: /r1/ }).first().click()
  timingPhase('reader-route')
  await expect.poll(() => new URL(page.url()).searchParams.has('reader')).toBe(true)
  timingPhase('reader-binding')
  const link = new URL(page.url()); const target = JSON.parse(link.searchParams.get('reader')!); expect(target.course).toEqual(fixture.course); expect(target.lesson).toEqual(fixture.lesson); expect(target.block).toEqual(fixture.block)
  timingPhase('reader-visible')
  await expect(page.locator(`#block-${fixture.block.id}-r${fixture.block.revision}`)).toBeVisible()
  timingPhase('review-tab-return')
  const reviewTab = page.getByRole('tab', { name: /测试复盘/ }); await reviewTab.click(); timingPhase('review-tab-clicked'); await expect(history.getByLabel('选择评分版本')).toHaveValue('1')
  timingPhase('mobile-screenshot')
  await page.setViewportSize({ width: 390, height: 844 }); timingPhase('mobile-viewport-set'); await history.getByRole('heading', { name: '评分版本与证据' }).evaluate(node => node.scrollIntoView({ block: 'start' })); expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('review-history-after-390.png') })
  timingPhase('agent-drawer')
  await page.getByRole('button', { name: '切换 Agent 栏', exact: true }).click(); const drawer = page.getByRole('dialog', { name: 'Agent 助教', exact: true }); await expect(drawer).toContainText('当前测试复盘上下文'); await expect(drawer).toContainText('评分版本 1：待复核'); await expect(drawer).toContainText('此版本没有当前获准的反馈正文'); await expect(drawer.getByRole('button', { name: '创建本次问答任务 ↑' })).toBeDisabled(); await drawer.getByRole('button', { name: '关闭Agent 助教', exact: true }).click()
  timingPhase('evidence-read')
  const evidence: PageEvidence = await page.request.get('/api/v1/learning/evidence?limit=100').then(response => response.json())
  timingPhase('latest-evidence-ids')
  const latestIds = final.history[1].items.flatMap(item => item.evidence_ids)
  timingPhase('evidence-assert')
  expect(evidence.items.map(item => item.id).sort()).toEqual([...latestIds].sort()); expect(evidence.items.every(item => !item.eligible)).toBe(true); expect(evidence.items.some(item => item.score === 1)).toBe(true)
  timingPhase('original-submission-assert')
  expect((await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json())).responses).toEqual(responses.responses); expect(errors).toEqual([])
  timingPhase('original-evidence-write')
  writeFileSync(info.outputPath('actual-review-history.json'), JSON.stringify({ scope: 'original synthetic true upload/worker/manual review/history/Reader/browser reload', grading_revisions: final.history.map(entry => entry.grading_revision), original_history_unchanged: JSON.stringify(first.history[0]) === JSON.stringify(final.history[0]), first_null_scores: first.items.every(item => item.score === null), all_unreviewed_excluded: final.history[1].items.every(item => !item.eligible), selected_revision_after_reload: 1, exact_material_target: target, latest_evidence_count: evidence.items.length, original_submission_preserved: true, runtime_errors: errors }, null, 2))
  timingPhase('original-body-complete')
  } finally {
    // BEGIN REVIEW_HISTORY_TIMING_FINALIZER
    timingPhase('body-finally')
    page.off('request', timingRequest); page.off('response', timingResponse)
    page.off('requestfinished', timingFinished); page.off('requestfailed', timingFailed)
    try {
      writeFileSync(info.outputPath('review-history-timing.json'), JSON.stringify({
        version: 'review-history-metadata-v1', body_started_at: timingStartedAt,
        observed_timeout_ms: info.timeout, retry: info.retry, phases: timingPhases, http: timingHttp,
        dropped: { phases: timingPhaseDropped, http: timingHttpDropped },
        limits: { phases: 128, http: 512 },
        scope: 'Body-only Node monotonic timing; browser HTTP static route templates/status only. No query, ID, header, payload, DOM or error text. Page-request polling and fixture setup are not observed. Synchronous instrumentation changes scheduling; root cause remains unknown.',
      }, null, 2), { flag: 'wx' })
    } catch { info.annotations.push({ type: 'diagnostic', description: 'Bounded history metadata could not be saved; original outcome preserved.' }) }
    // END REVIEW_HISTORY_TIMING_FINALIZER
    setupTiming.mark('body-finally'); setupTiming.save('body-finally')
  }
})

test('a delayed old review response cannot restore history or academic context after another page starts a real independent attempt', async ({ page }, info) => {
  const { fixture, attempt } = await start(page, 'reviewnativepolicy'); await submit(page); await manual(page); await grade(page, attempt.id, 2); await page.getByRole('button', { name: '打开本次测试复盘', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果' })).toContainText('评分版本 2'); await expect(page.getByRole('button', { name: '重新读取评分结果', exact: true })).toBeEnabled()
  let release!: () => void, captured!: () => void; const gate = new Promise<void>(resolve => { release = resolve }), ready = new Promise<void>(resolve => { captured = resolve })
  const routePattern = `**/api/v1/attempts/${attempt.id}/result`
  const consumed = await observeNextResponseJson(page, `/api/v1/attempts/${attempt.id}/result`)
  const phases: { event: string; invocation?: number; status?: number }[] = []; let invocations = 0
  const phase = (event: string, invocation?: number, status?: number) => { phases.push({ event, invocation, status }); writeFileSync(info.outputPath('late-response-phases.json'), JSON.stringify(phases)) }
  let handled: Promise<void> | undefined
  // Only the clicked old GET is delayed; later permission reads stay real.
  // A times:1 handler is removed on entry, so await its own promise as well.
  await page.route(routePattern, route => { handled = (async () => { const invocation = ++invocations; phase('handler-enter', invocation); const response = await route.fetch(); phase('captured', invocation, response.status()); captured(); await gate; phase('fulfill-enter', invocation); try { await route.fulfill({ response }); phase('fulfill-complete', invocation) } catch (error) { phase('fulfill-error', invocation); throw error } })(); return handled }, { times: 1 })
  await page.getByRole('button', { name: '重新读取评分结果', exact: true }).click(); await ready
  const other = await page.context().newPage()
  try {
    await other.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    await other.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await other.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); await expect(other.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
    phase('other-independent-visible'); release(); await handled; await page.unrouteAll({ behavior: 'wait' }); expect(invocations).toBe(1); phase('handlers-drained'); expect(await consumed.wait()).toEqual({ outcome: 'fulfilled', jsonCalls: 1 }); phase('client-chain-observed'); await expect(page.getByRole('region', { name: '完整评分历史' })).toHaveCount(0); await expect(page.getByText('当前测试复盘上下文', { exact: true })).toHaveCount(0)
    expect((await page.request.get(`/api/v1/attempts/${attempt.id}/result`)).status()).toBe(409)
  } finally { release(); await handled; await page.unrouteAll({ behavior: 'wait' }); await consumed.dispose(); await other.close() }
})
