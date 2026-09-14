import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import { RestartRuntime } from './restartRuntime'
import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
import type { AssessmentGradingResult, AttemptSnapshot } from '../../packages/contracts/generated/api-types'
const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
})
async function start(page: Page, prefix: string) {
  const fixture = originalAssessmentPackage(prefix)
  const imported = await importAssessmentPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const pending = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const response = await pending; expect(response.status()).toBe(201)
  const attempt: AttemptSnapshot = await response.json()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  return { fixture, attempt }
}
async function submit(page: Page) { await page.getByRole('button', { name: '提交本次测试', exact: true }).click(); await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible() }
async function grade(page: Page, id: string, revision: number): Promise<AssessmentGradingResult> {
  let result: AssessmentGradingResult | undefined
  await expect.poll(async () => { const response = await page.request.get(`/api/v1/attempts/${id}/result`); if (response.status() === 202) return 0; expect(response.status()).toBe(200); result = await response.json(); return result!.grading_revision }).toBe(revision)
  return result!
}
async function settleLayout(page: Page) { const choice = page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }); if (await choice.isVisible()) { await choice.click(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible() } }
async function beginReview(page: Page) { const author = page.getByRole('button', { name: '切换为作者角色以人工复核', exact: true }); if (await author.isVisible()) await author.click(); await page.getByRole('button', { name: '填写人工复核', exact: true }).click() }
async function fillReview(page: Page, number: number, score: string, text: string) { await page.getByRole('checkbox', { name: `复核第 ${number} 题`, exact: true }).check(); await page.getByLabel(`第 ${number} 题人工分数`, { exact: true }).fill(score); await page.getByLabel(`第 ${number} 题复核依据`, { exact: true }).fill(text) }
async function sendReview(page: Page) { await page.getByRole('button', { name: '提交人工复核', exact: true }).click(); await page.getByRole('button', { name: '确认提交人工分数与依据', exact: true }).click() }

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
    const second = await other.newPage(); await second.goto(page.url()); await beginReview(second)
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
