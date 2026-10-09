import { expect, test as base, type Page, type Request, type Response } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import { RestartRuntime } from './restartRuntime'
import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
import type { AssessmentGradingResult, AttemptSnapshot } from '../../packages/contracts/generated/api-types'
type GradingPhase = 'fixture-enter' | 'runtime-start' | 'runtime-ready' | 'browser-open' | 'browser-opened' | 'authentication-start' | 'authentication-complete' | 'page-use' | 'page-finally' | 'fixture-finally'
  | 'assessment-fixture-build' | 'assessment-fixture-built' | 'assessment-import' | 'assessment-imported' | 'assessment-goto' | 'assessment-goto-returned' | 'assessment-created-ack' | 'assessment-saved-visible'
  | 'submit-enter' | 'submit-returned' | 'manual-form-enter' | 'manual-form-returned' | 'manual-confirm-enter' | 'manual-confirm-returned' | 'grade-enter' | 'grade-returned' | 'second-page-observed'
type GradingCaller = 'revision-1' | 'revision-2' | 'revision-3' | 'other-revision'
type ObservedJobStatus = 'queued' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'cancelled'
type GradingPoll = { sequence: number; elapsed_ms: number; caller: GradingCaller; route: '/api/v1/attempts/:id/result'; method: 'GET'; status: number; request_elapsed_ms: number; job_status?: ObservedJobStatus; job_status_invalid?: boolean; job_status_unreadable?: boolean; job_status_not_observed?: boolean }
type GradingTiming = { mark: (stage: GradingPhase) => void; poll: (caller: GradingCaller, status: number, duration: number) => ((value: unknown, unreadable?: boolean) => void) | undefined; save: (boundary: 'page-finally' | 'fixture-finally') => void; observePage: (page: Page) => void }
const gradingTimingByPage = new WeakMap<Page, GradingTiming>()
function shareGradingTiming(original: Page, second: Page) { const timing = gradingTimingByPage.get(original); if (timing) { gradingTimingByPage.set(second, timing); timing.observePage(second); timing.mark('second-page-observed') } }
const test = base.extend<{ runtime: RestartRuntime; gradingTiming: GradingTiming }>({
  // This observer stays test-scoped inside the original timeout and does not add a request or wait.
  gradingTiming: [async ({}, use, info) => {
    const enabled = info.title === 'two browser profiles keep a stale manual-review baseline through an actual 412 before explicit three-way rebase'
    const started = performance.now(), phases: { sequence: number; elapsed_ms: number; stage: GradingPhase }[] = [], polls: GradingPoll[] = []
    let sequence = 0, phaseDropped = 0, pollDropped = 0, statusReadDropped = 0, statusReadAttempts = 0, statusReadPending = 0, saved = false
    // Passive browser events observe the existing POST, not a new request or an ACK wait.
    type RegradeEvent = 'request' | 'response-headers' | 'request-finished' | 'request-failed'
    type RegradePending = { started: number; page_ordinal: number; request_ordinal: number; status?: number; settled: boolean }
    const regradePending = new WeakMap<Request, RegradePending>(), regradePages = new WeakSet<Page>()
    const regradeDetach: (() => void)[] = []
    const regradeHttp: { sequence: number; elapsed_ms: number; event: RegradeEvent; route: '/api/v1/attempts/:id/regrade'; method: 'POST'; page_ordinal: number; request_ordinal: number; status?: number; request_elapsed_ms?: number; ack_202_complete: boolean }[] = []
    let regradePageCount = 0, regradeRequestCount = 0, regradePendingCount = 0
    let regradePageDropped = 0, regradeRequestDropped = 0, regradeEventDropped = 0, regradeObserverErrors = 0
    const observeRegrade = (request: Request, event: RegradeEvent, pageOrdinal: number, status?: number) => {
      if (!enabled || saved) return
      try {
        let value = regradePending.get(request)
        if (event === 'request') {
          if (request.method() !== 'POST' || !/^\/api\/v1\/attempts\/[A-Za-z][A-Za-z0-9_-]{0,79}\/regrade$/.test(new URL(request.url()).pathname)) return
          if (regradeRequestCount === 8 || regradePendingCount === 4) { regradeRequestDropped++; return }
          value = { started: performance.now(), page_ordinal: pageOrdinal, request_ordinal: ++regradeRequestCount, settled: false }
          regradePending.set(request, value); regradePendingCount++
        }
        if (!value || value.settled) return
        if (status !== undefined) {
          if (!Number.isInteger(status) || status < 100 || status > 599) { regradeObserverErrors++; return }
          value.status = status
        }
        if (event === 'request-finished' || event === 'request-failed') { value.settled = true; regradePendingCount-- }
        if (regradeHttp.length === 32) { regradeEventDropped++; return }
        regradeHttp.push({ sequence: ++sequence, elapsed_ms: performance.now() - started, event,
          route: '/api/v1/attempts/:id/regrade', method: 'POST', page_ordinal: value.page_ordinal, request_ordinal: value.request_ordinal,
          ...(value.status === undefined ? {} : { status: value.status }),
          ...(event === 'request' ? {} : { request_elapsed_ms: performance.now() - value.started }),
          ack_202_complete: event === 'request-finished' && value.status === 202 })
      } catch { regradeObserverErrors++ }
    }
    const timing: GradingTiming = {
      observePage(page) {
        if (!enabled || saved || regradePages.has(page)) return
        if (regradePageCount === 2) { regradePageDropped++; return }
        regradePages.add(page); const ordinal = ++regradePageCount
        const requested = (request: Request) => observeRegrade(request, 'request', ordinal)
        const responded = (response: Response) => observeRegrade(response.request(), 'response-headers', ordinal, response.status())
        const finished = (request: Request) => observeRegrade(request, 'request-finished', ordinal)
        const failed = (request: Request) => observeRegrade(request, 'request-failed', ordinal)
        page.on('request', requested); page.on('response', responded); page.on('requestfinished', finished); page.on('requestfailed', failed)
        regradeDetach.push(() => { page.off('request', requested); page.off('response', responded); page.off('requestfinished', finished); page.off('requestfailed', failed) })
      },
      mark(stage) { if (!enabled || saved) return; if (phases.length === 256) { phaseDropped++; return }; phases.push({ sequence: ++sequence, elapsed_ms: performance.now() - started, stage }) },
      poll(caller, status, duration) {
        if (!enabled || saved || !Number.isInteger(status) || status < 100 || status > 599 || !Number.isFinite(duration) || duration < 0) return
        if (polls.length === 64) { pollDropped++; return }
        const entry: GradingPoll = { sequence: ++sequence, elapsed_ms: performance.now() - started, caller, route: '/api/v1/attempts/:id/result', method: 'GET', status, request_elapsed_ms: duration }
        polls.push(entry)
        if (status !== 202) return
        if (statusReadAttempts === 32 || statusReadPending === 8) { statusReadDropped++; entry.job_status_not_observed = true; return }
        statusReadAttempts++; statusReadPending++
        let settled = false
        return (value, unreadable = false) => {
          if (saved || settled) return
          settled = true; statusReadPending--
          if (unreadable) { entry.job_status_unreadable = true; return }
          // Access only the top-level status. Never retain the response or inspect any other field.
          const state: unknown = value != null && typeof value === 'object' && !Array.isArray(value) ? (value as { status?: unknown }).status : undefined
          if (state === 'queued' || state === 'running' || state === 'awaiting_approval' || state === 'completed' || state === 'failed' || state === 'cancelled') entry.job_status = state
          else entry.job_status_invalid = true
        }
      },
      save(boundary) {
        if (!enabled || saved) return
        saved = true // Freeze before writing; late JSON observations cannot alter this record.
        for (const detach of regradeDetach) { try { detach() } catch { regradeObserverErrors++ } }
        try {
          writeFileSync(info.outputPath('grading-two-profile-timing.json'), JSON.stringify({
            version: 'grading-two-profile-metadata-v1', clock: 'Node performance.now milliseconds since test-scoped observer fixture entry', observed_timeout_ms: info.timeout, retry: info.retry,
            saved_at_boundary: boundary, phases, polls,
            regrade_http: { version: 'grading-regrade-http-metadata-v1', clock: 'Same test-scoped Node performance.now origin as phases and polls',
              events: regradeHttp, pages_observed: regradePageCount, requests_observed: regradeRequestCount, pending_at_freeze: regradePendingCount,
              dropped: { pages: regradePageDropped, requests_capacity: regradeRequestDropped, events: regradeEventDropped }, observer_errors: regradeObserverErrors,
              limits: { pages: 2, requests: 8, pending: 4, events: 32 },
              scope: 'Existing browser POST regrade only. Request ordinals and page ordinals are synthetic counters. A 202 response-header event is distinct from request-finished with ack_202_complete=true; neither proves UI JSON consumption, a worker claim or grade completion. No extra request, ACK await, body, header, ID, query or error text. Synchronous observation changes scheduling.' },
            status_reads: { attempted: statusReadAttempts, pending_at_freeze: statusReadPending }, dropped: { phases: phaseDropped, polls: pollDropped, status_reads: statusReadDropped }, limits: { phases: 256, polls: 64, status_reads: 32, status_reads_pending: 8 },
            scope: 'Original test-scoped runtime/page/start/submit/manual/grade boundaries and existing GET result HTTP status/duration. A non-awaited read of an existing 202 response projects only the strict top-level job status enum. No added request/wait, ID, URL/query, header, authentication value, answer/reason, DOM, private field or raw JSON is recorded. Page-finally freeze precedes runtime cleanup; fixture-finally fallback covers setup failure. Timing includes observer scheduling overhead; worker/browser setup before observer entry and server progress between observations are unobserved. No cause or repair verdict.',
          }, null, 2), { flag: 'wx' })
        } catch { info.annotations.push({ type: 'diagnostic', description: 'Bounded grading metadata could not be saved; original outcome preserved.' }) }
      },
    }
    timing.mark('fixture-enter')
    try { await use(timing) } finally { timing.mark('fixture-finally'); timing.save('fixture-finally') }
  }, { auto: true }],
  runtime: async ({ gradingTiming }, use) => { gradingTiming.mark('runtime-start'); const runtime = await RestartRuntime.start(); gradingTiming.mark('runtime-ready'); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright, gradingTiming }, use) => {
    gradingTiming.mark('browser-open'); const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; gradingTiming.mark('browser-opened')
    gradingTimingByPage.set(page, gradingTiming); gradingTiming.observePage(page); gradingTiming.mark('authentication-start'); await runtime.authenticateOnly(page); gradingTiming.mark('authentication-complete'); gradingTiming.mark('page-use')
    try { await use(page) } finally { gradingTiming.mark('page-finally'); gradingTiming.save('page-finally'); gradingTimingByPage.delete(page) }
  },
})
async function start(page: Page, prefix: string) {
  const timing = gradingTimingByPage.get(page); timing?.mark('assessment-fixture-build')
  const fixture = originalAssessmentPackage(prefix)
  timing?.mark('assessment-fixture-built'); timing?.mark('assessment-import')
  const imported = await importAssessmentPackage(page, fixture)
  timing?.mark('assessment-imported')
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  timing?.mark('assessment-goto')
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  timing?.mark('assessment-goto-returned')
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const pending = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const response = await pending; expect(response.status()).toBe(201)
  timing?.mark('assessment-created-ack')
  const attempt: AttemptSnapshot = await response.json()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  timing?.mark('assessment-saved-visible')
  return { fixture, attempt }
}
async function submit(page: Page) { const timing = gradingTimingByPage.get(page); timing?.mark('submit-enter'); await page.getByRole('button', { name: '提交本次测试', exact: true }).click(); await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible(); timing?.mark('submit-returned') }
async function grade(page: Page, id: string, revision: number): Promise<AssessmentGradingResult> {
  let result: AssessmentGradingResult | undefined
  const timing = gradingTimingByPage.get(page), caller: GradingCaller = revision === 1 ? 'revision-1' : revision === 2 ? 'revision-2' : revision === 3 ? 'revision-3' : 'other-revision'; timing?.mark('grade-enter')
  await expect.poll(async () => { const started = performance.now(); const response = await page.request.get(`/api/v1/attempts/${id}/result`); const observe = timing?.poll(caller, response.status(), performance.now() - started); if (response.status() === 202) { if (observe) void response.json().then(value => observe(value), () => observe(undefined, true)).catch(() => { /* Diagnostic parsing must not change the original poll. */ }); return 0 }; expect(response.status()).toBe(200); result = await response.json(); return result!.grading_revision }).toBe(revision)
  timing?.mark('grade-returned')
  return result!
}
async function settleLayout(page: Page) { const choice = page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }); if (await choice.isVisible()) { await choice.click(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible() } }
async function beginReview(page: Page) { const timing = gradingTimingByPage.get(page); timing?.mark('manual-form-enter'); const author = page.getByRole('button', { name: '切换为作者角色以人工复核', exact: true }); if (await author.isVisible()) await author.click(); await page.getByRole('button', { name: '填写人工复核', exact: true }).click(); timing?.mark('manual-form-returned') }
async function fillReview(page: Page, number: number, score: string, text: string) { await page.getByRole('checkbox', { name: `复核第 ${number} 题`, exact: true }).check(); await page.getByLabel(`第 ${number} 题人工分数`, { exact: true }).fill(score); await page.getByLabel(`第 ${number} 题复核依据`, { exact: true }).fill(text) }
async function sendReview(page: Page) { const timing = gradingTimingByPage.get(page); timing?.mark('manual-confirm-enter'); await page.getByRole('button', { name: '提交人工复核', exact: true }).click(); await page.getByRole('button', { name: '确认提交人工分数与依据', exact: true }).click(); timing?.mark('manual-confirm-returned') }

test('unreviewed original content stays null until an explicit author form creates a signed new grade without altering its reference approval', async ({ page }, info) => {
  const errors: string[] = [], resultStatuses: number[] = [], privateCalls: string[] = []
  page.on('pageerror', error => errors.push(error.message)); page.on('request', request => { if (/\/solutions$/.test(request.url())) privateCalls.push(request.method()) }); page.on('response', response => { if (/\/result$/.test(response.url())) resultStatuses.push(response.status()) })
  const { fixture, attempt } = await start(page, 'gradingnativeform')
  expect(resultStatuses).toEqual([])
  await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  await page.getByLabel('第 2 题答案', { exact: true }).fill('原创工程作答 🧠é')
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  const saved = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json())
  await submit(page)
  const initial = await grade(page, attempt.id, 1)
  expect(initial.status).toBe('needs_review'); expect(initial.items.every(item => item.score === null && item.solution_markdown == null)).toBe(true); expect(initial.manual_reviews).toEqual([])
  const current = page.getByRole('region', { name: '当前评分结果', exact: true }); await expect(current).toContainText('暂无分数，不将未知项计为零分')
  await settleLayout(page); await beginReview(page)
  await page.getByLabel('人工复核理由', { exact: true }).fill('原创软件验收：模拟作者明确复核操作，不代表内容已审核或学习效果。')
  for (let i = 1; i <= 5; i++) await fillReview(page, i, i === 2 ? '1' : '0', `合成第 ${i} 项复核依据；仅验证逐题分数、签名及版本保存。`)
  await settleLayout(page); await page.setViewportSize({ width: 390, height: 844 }); await page.getByRole('region', { name: '人工复核', exact: true }).getByRole('heading', { name: '人工复核', exact: true }).evaluate(node => node.scrollIntoView({ block: 'start' }))
  await expect(page.getByLabel('人工复核理由', { exact: true })).toBeInViewport()
  expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
  await page.screenshot({ path: info.outputPath('grading-review-390.png') })
  const sending = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/attempts/${attempt.id}/regrade`))
  await sendReview(page); expect((await sending).status()).toBe(202)
  const final = await grade(page, attempt.id, 2)
  await expect(current).toContainText('评分版本 2'); expect(final.status).toBe('graded'); expect(final.items.map(item => item.score)).toEqual([0, 1, 0, 0, 0]); expect(final.solution_reviews.every(item => item.review_status === 'needs_review')).toBe(true); expect(final.eligibility_status).toBe('evaluated'); expect(final.history.at(-1)?.items.every(item => !item.eligible && item.reason_codes.includes('ANSWER_UNREVIEWED'))).toBe(true); expect(final.manual_reviews[0].signature).toMatch(/^[a-f0-9]{64}$/)
  expect((await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json())).responses).toEqual(saved.responses)
  expect((await page.request.get(`/api/v1/attempts/${attempt.id}`).then(response => response.json())).preflight.grading.needs_review_count).toBe(5)
  await settleLayout(page); await page.setViewportSize({ width: 1440, height: 900 }); await current.getByRole('heading', { name: '评分已完成', exact: true }).evaluate(node => node.scrollIntoView({ block: 'start' })); await expect(current).toContainText('总分 1 / 5')
  await page.screenshot({ path: info.outputPath('grading-result-1440.png') })
  await page.reload(); await expect(current).toContainText('评分版本 2'); expect(privateCalls).toEqual([]); expect(errors).toEqual([])
  writeFileSync(info.outputPath('actual-grading-form.json'), JSON.stringify({ scope: 'original synthetic UI and real HTTP/SQLite worker', question_count: fixture.questions.length, initial: { status: initial.status, scores: initial.items.map(item => item.score) }, final: { status: final.status, scores: final.items.map(item => item.score), grading_revision: final.grading_revision, signature_count: final.manual_reviews.length, original_solution_reviews: final.solution_reviews.map(item => item.review_status) }, observed_result_http_statuses: resultStatuses, no_private_solution_calls: privateCalls.length === 0, runtime_errors: errors }, null, 2))
})

test('two browser profiles keep a stale manual-review baseline through an actual 412 before explicit three-way rebase', async ({ page, browser }) => {
  const { attempt } = await start(page, 'gradingnativecas'); await submit(page); await beginReview(page)
  await page.getByLabel('人工复核理由', { exact: true }).fill('A 作者保留的原版本复核'); await fillReview(page, 1, '0.25', 'A 本页逐题依据')
  const other = await browser.newContext({ baseURL: new URL(page.url()).origin, storageState: await page.context().storageState() })
  try {
    const second = await other.newPage(); shareGradingTiming(page, second); await second.goto(page.url()); await beginReview(second)
    await second.getByLabel('人工复核理由', { exact: true }).fill('B 作者先提交的新版本'); await fillReview(second, 1, '0.75', 'B 服务端逐题依据'); await sendReview(second); await grade(second, attempt.id, 2)
    const rejected = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/attempts/${attempt.id}/regrade`))
    await sendReview(page); expect((await rejected).status()).toBe(412)
    const comparison = page.getByRole('region', { name: '人工复核三方比较', exact: true }); await expect(comparison).toContainText('A 本页逐题依据'); await expect(comparison).toContainText('B 服务端逐题依据'); await expect(comparison).toContainText('原评分基准')
    await page.getByRole('button', { name: '保留本页复核并采用当前评分基准', exact: true }).click(); await sendReview(page)
    const final = await grade(page, attempt.id, 3); expect(final.items[0].score).toBe(0.25); expect(final.items.slice(1).every(item => item.score === null)).toBe(true)
  } finally { await other.close() }
})

test('a failed manual request preserves its durable exact command and editable author draft after browser reload', async ({ page }) => {
  const { attempt } = await start(page, 'gradingnativeoffline'); await submit(page); await beginReview(page)
  await page.getByLabel('人工复核理由', { exact: true }).fill('断网保留的明确复核理由 🧠é'); await fillReview(page, 2, '1', '断网前已保存的人工依据')
  const pattern = `**/api/v1/attempts/${attempt.id}/regrade`
  await page.route(pattern, route => route.abort('internetdisconnected')); await sendReview(page)
  await expect(page.getByRole('region', { name: '人工复核', exact: true })).toContainText('人工复核尚未确认')
  await expect(page.getByText('本机复核草稿存储可用', { exact: true })).toBeVisible()
  await page.reload(); await page.getByRole('button', { name: '恢复复核候选 1', exact: true }).click()
  await expect(page.getByLabel('人工复核理由', { exact: true })).toHaveValue('断网保留的明确复核理由 🧠é')
  await expect(page.getByLabel('第 2 题人工分数', { exact: true })).toHaveValue('1')
  expect((await grade(page, attempt.id, 1)).items.every(item => item.score === null)).toBe(true)
  await page.unroute(pattern); await sendReview(page); expect((await grade(page, attempt.id, 2)).items[1].score).toBe(1)
})
