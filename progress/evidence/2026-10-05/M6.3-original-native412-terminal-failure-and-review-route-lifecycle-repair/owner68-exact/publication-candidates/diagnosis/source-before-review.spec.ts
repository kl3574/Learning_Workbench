import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import { RestartRuntime } from './restartRuntime'
import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
import type { AssessmentGradingResult, AttemptSnapshot, PageEvidence } from '../../packages/contracts/generated/api-types'
const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
})
async function start(page: Page, prefix: string) {
  const fixture = originalAssessmentPackage(prefix), imported = await importAssessmentPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const created = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); expect((await created).status()).toBe(201)
  const attempt: AttemptSnapshot = await (await created).json()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  return { fixture, attempt }
}
async function grade(page: Page, id: string, revision: number): Promise<AssessmentGradingResult> {
  let result: AssessmentGradingResult | undefined
  await expect.poll(async () => { const response = await page.request.get(`/api/v1/attempts/${id}/result`); if (response.status() === 202) return 0; expect(response.status()).toBe(200); result = await response.json(); return result!.grading_revision }).toBe(revision)
  return result!
}
async function submit(page: Page) { await page.getByRole('button', { name: '提交本次测试', exact: true }).click(); await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible() }
async function manual(page: Page) {
  await page.getByRole('button', { name: '切换为作者角色以人工复核', exact: true }).click(); await page.getByRole('button', { name: '填写人工复核', exact: true }).click()
  await page.getByLabel('人工复核理由', { exact: true }).fill('原创软件复盘验收：显式逐项给分，不代表参考内容获批。')
  for (let i = 1; i <= 5; i++) { await page.getByRole('checkbox', { name: `复核第 ${i} 题`, exact: true }).check(); await page.getByLabel(`第 ${i} 题人工分数`, { exact: true }).fill(i === 2 ? '1' : '0'); await page.getByLabel(`第 ${i} 题复核依据`, { exact: true }).fill(`原创第 ${i} 项当前复核依据，不把推导正确性或审核状态从分数推出。`) }
  await page.getByRole('button', { name: '提交人工复核', exact: true }).click(); await page.getByRole('button', { name: '确认提交人工分数与依据', exact: true }).click()
}
async function settleLayout(page: Page) { const choice = page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }); if (await choice.isVisible()) { await choice.click(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible() } }

test('real history and exact material review preserve original submitted text, null scores and a selected old revision after reload', async ({ page }, info) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  const { fixture, attempt } = await start(page, 'reviewnativehistory')
  await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  const answer = '交卷原始答案 🧠é', steps = '原始推导第一行\n\\alpha < beta\n**按原文保留**'
  await page.getByLabel('第 2 题答案', { exact: true }).fill(answer); await page.getByLabel('第 2 题推导步骤', { exact: true }).fill(steps)
  await expect.poll(async () => { const value = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json()); return value.responses.find((item: { question_id: string }) => item.question_id === fixture.questions[1].id) }).toMatchObject({ answer, steps_markdown: steps })
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible(); await submit(page)
  const first = await grade(page, attempt.id, 1)
  expect(first.history).toHaveLength(1); expect(first.items.every(item => item.score === null)).toBe(true)
  const responses = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json())
  await settleLayout(page); await page.getByRole('button', { name: '打开本次测试复盘', exact: true }).click()
  await expect(page.getByRole('heading', { name: '本次测试复盘', exact: true })).toBeVisible()
  await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  await expect(page.getByLabel('第 2 题已提交答案', { exact: true })).toHaveText(answer); await expect(page.getByLabel('第 2 题已提交推导步骤', { exact: true })).toHaveText(steps)
  expect(await page.getByRole('region', { name: '第 2 题交卷原文', exact: true }).locator('input,textarea').count()).toBe(0)
  await expect(page.getByRole('region', { name: '本题证据资格', exact: true })).toContainText('冻结的参考答案尚未审核')
  await manual(page); const final = await grade(page, attempt.id, 2)
  expect(final.history.map(entry => entry.grading_revision)).toEqual([1, 2]); expect(final.history[0]).toEqual(first.history[0]); expect(final.history[1].items.every(item => !item.eligible && item.reason_codes.includes('ANSWER_UNREVIEWED'))).toBe(true)
  expect(final.current_review_policy).toEqual({ tutor_scope: 'academic', allow_materials: true, allow_web: false })
  await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toContainText('评分版本 2')
  const history = page.getByRole('region', { name: '完整评分历史', exact: true })
  await expect(history.getByLabel('选择评分版本')).toHaveValue('2'); await history.getByLabel('选择评分版本').selectOption('1'); await expect(history).toContainText('本题在版本 1：待复核 · 分数为空')
  await history.locator('summary').filter({ hasText: '比较评分版本' }).click(); await history.getByLabel('对照评分版本').selectOption('2'); await expect(history.getByRole('table')).toContainText('1 / 1')
  expect(final.history.every(entry => entry.items.every(item => !('feedback_markdown' in item) && !('solution_markdown' in item)))).toBe(true)
  await page.setViewportSize({ width: 1440, height: 900 }); await history.getByRole('heading', { name: '评分版本与证据' }).evaluate(node => node.scrollIntoView({ block: 'start' })); await page.screenshot({ path: info.outputPath('review-history-after-1440.png') })
  await settleLayout(page); await page.reload(); await expect(history.getByLabel('选择评分版本')).toHaveValue('1'); await expect(page.getByLabel('第 2 题已提交答案')).toHaveText(answer)
  const material = page.getByRole('region', { name: '本题对应教材', exact: true }); await material.getByRole('button', { name: /r1/ }).first().click()
  await expect.poll(() => new URL(page.url()).searchParams.has('reader')).toBe(true)
  const link = new URL(page.url()); const target = JSON.parse(link.searchParams.get('reader')!); expect(target.course).toEqual(fixture.course); expect(target.lesson).toEqual(fixture.lesson); expect(target.block).toEqual(fixture.block)
  await expect(page.locator(`#block-${fixture.block.id}-r${fixture.block.revision}`)).toBeVisible()
  const reviewTab = page.getByRole('tab', { name: /测试复盘/ }); await reviewTab.click(); await expect(history.getByLabel('选择评分版本')).toHaveValue('1')
  await page.setViewportSize({ width: 390, height: 844 }); await history.getByRole('heading', { name: '评分版本与证据' }).evaluate(node => node.scrollIntoView({ block: 'start' })); expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('review-history-after-390.png') })
  await page.getByRole('button', { name: '切换 Agent 栏', exact: true }).click(); const drawer = page.getByRole('dialog', { name: 'Agent 助教', exact: true }); await expect(drawer).toContainText('当前测试复盘上下文'); await expect(drawer).toContainText('评分版本 1：待复核'); await expect(drawer).toContainText('此版本没有当前获准的反馈正文'); await expect(drawer.getByRole('button', { name: '创建本次问答任务 ↑' })).toBeDisabled(); await drawer.getByRole('button', { name: '关闭Agent 助教', exact: true }).click()
  const evidence: PageEvidence = await page.request.get('/api/v1/learning/evidence?limit=100').then(response => response.json())
  const latestIds = final.history[1].items.flatMap(item => item.evidence_ids)
  expect(evidence.items.map(item => item.id).sort()).toEqual([...latestIds].sort()); expect(evidence.items.every(item => !item.eligible)).toBe(true); expect(evidence.items.some(item => item.score === 1)).toBe(true)
  expect((await page.request.get(`/api/v1/attempts/${attempt.id}/responses`).then(response => response.json())).responses).toEqual(responses.responses); expect(errors).toEqual([])
  writeFileSync(info.outputPath('actual-review-history.json'), JSON.stringify({ scope: 'original synthetic true upload/worker/manual review/history/Reader/browser reload', grading_revisions: final.history.map(entry => entry.grading_revision), original_history_unchanged: JSON.stringify(first.history[0]) === JSON.stringify(final.history[0]), first_null_scores: first.items.every(item => item.score === null), all_unreviewed_excluded: final.history[1].items.every(item => !item.eligible), selected_revision_after_reload: 1, exact_material_target: target, latest_evidence_count: evidence.items.length, original_submission_preserved: true, runtime_errors: errors }, null, 2))
})

test('a delayed old review response cannot restore history or academic context after another page starts a real independent attempt', async ({ page }) => {
  const { fixture, attempt } = await start(page, 'reviewnativepolicy'); await submit(page); await manual(page); await grade(page, attempt.id, 2); await page.getByRole('button', { name: '打开本次测试复盘', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果' })).toContainText('评分版本 2'); await expect(page.getByRole('button', { name: '重新读取评分结果', exact: true })).toBeEnabled()
  let release!: () => void, captured!: () => void; const gate = new Promise<void>(resolve => { release = resolve }), ready = new Promise<void>(resolve => { captured = resolve })
  const routePattern = `**/api/v1/attempts/${attempt.id}/result`
  await page.route(routePattern, async route => { const response = await route.fetch(); captured(); await gate; await route.fulfill({ response }) })
  await page.getByRole('button', { name: '重新读取评分结果', exact: true }).click(); await ready
  const other = await page.context().newPage()
  try {
    await other.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    await other.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await other.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); await expect(other.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
    release(); await expect(page.getByRole('region', { name: '完整评分历史' })).toHaveCount(0); await expect(page.getByText('当前测试复盘上下文', { exact: true })).toHaveCount(0)
    expect((await page.request.get(`/api/v1/attempts/${attempt.id}/result`)).status()).toBe(409)
  } finally { release(); await page.unroute(routePattern); await other.close() }
})
