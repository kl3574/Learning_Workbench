import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page, type APIResponse } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AssessmentGradingResult, AttemptSnapshot } from '../../packages/contracts/generated/api-types'
import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
import { RestartRuntime } from './restartRuntime'

const root = resolve(import.meta.dirname, '../..')

let observeResult: ((response: APIResponse) => Promise<void>) | undefined

async function result(page: Page, id: string, revision: number) {
  let value: AssessmentGradingResult | undefined
  await expect.poll(async () => {
    const response = await page.request.get(`/api/v1/attempts/${id}/result`)
    await observeResult?.(response)
    if (response.status() === 202) return 0
    expect(response.status()).toBe(200)
    value = await response.json()
    return value!.grading_revision
  }).toBe(revision)
  return value!
}

test('a real failed regrade survives reload and can recover from the last actual grade without losing the old submission', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('gradingrecover')
  const errors: string[] = [], reviewCommands: string[] = []
  const events: { kind: string; ms: number; status?: number; code?: string }[] = []
  const mark = (kind: string, status?: number, code?: string) => events.push({ kind, ms: performance.now(), status, code })
  let releaseSubmit: (() => void) | undefined, gateTimer: ReturnType<typeof setTimeout> | undefined
  let routeFinished: Promise<void> | undefined
  const dump = () => writeFileSync(info.outputPath('submission-order.json'), JSON.stringify({ scope: 'Owned synthetic exact submission request held before dispatch; real API responses, original result assertions and timeout unchanged.', events }, null, 2))
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/regrade')) reviewCommands.push(request.headers()['idempotency-key']) })
    await runtime.authenticateOnly(page)
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    await page.getByRole('radio', { name: '独立测试', exact: true }).check()
    await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
    await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
    const created = await creating
    expect(created.status()).toBe(201)
    const attempt: AttemptSnapshot = await created.json()
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const submitPath = `/api/v1/attempts/${attempt.id}/submit`
    const gate = new Promise<void>(resolve => { releaseSubmit = resolve })
    page.on('response', response => { if (response.request().method() === 'POST' && new URL(response.url()).pathname === submitPath) mark('submit_response', response.status()) })
    await page.route(`**${submitPath}`, async route => {
      if (route.request().method() !== 'POST') { await route.continue(); return }
      let finished!: () => void
      routeFinished = new Promise<void>(resolve => { finished = resolve })
      mark('submit_held')
      gateTimer = setTimeout(() => { mark('gate_deadline_release'); releaseSubmit?.() }, 1500)
      try { await gate; mark('submit_released'); await route.continue() } finally { finished() }
    })
    observeResult = async response => {
      observeResult = undefined
      let code: string | undefined
      if (response.status() === 409) {
        const value = await response.json()
        const actualCode = value?.error?.code ?? value?.code
        code = actualCode === 'ATTEMPT_NOT_SUBMITTED' ? actualCode : 'OTHER_ERROR_CODE'
      }
      mark('first_actual_result', response.status(), code)
      releaseSubmit?.(); clearTimeout(gateTimer)
      await routeFinished
      dump()
    }
    await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
    await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
    await result(page, attempt.id, 1)
  } finally { releaseSubmit?.(); clearTimeout(gateTimer); await routeFinished; observeResult = undefined; dump(); await runtime.close() }
})
