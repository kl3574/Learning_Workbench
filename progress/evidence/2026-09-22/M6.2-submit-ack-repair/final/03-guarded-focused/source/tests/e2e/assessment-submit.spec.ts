import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'
import { importAssessmentPackage, originalAssessmentPackage, submitAssessment } from './assessmentTestData'
import { RestartRuntime } from './restartRuntime'

test('a pending real submission remains unsubmitted until its exact acknowledgement, then exposes only the actual grading result', async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('submitack')
  let release: (() => void) | undefined, routed: Promise<void> | undefined
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    await page.getByRole('radio', { name: '独立测试', exact: true }).check()
    await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
    const creating = page.waitForResponse(response => response.request().method() === 'POST'
      && new URL(response.url()).pathname === `/api/v1/assessments/${fixture.assessment.id}/attempts`)
    await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
    const created = await creating
    expect(created.status()).toBe(201)
    const attempt: AttemptSnapshot = await created.json()
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const saved = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`)
    expect(saved.status()).toBe(200)
    const savedResponses = await saved.json()

    let intercepted!: () => void, requestHeld = false
    const held = new Promise<void>(resolve => { intercepted = resolve })
    const gate = new Promise<void>(resolve => { release = resolve })
    await page.route(`**/api/v1/attempts/${attempt.id}/submit`, async route => {
      if (route.request().method() !== 'POST') { await route.continue(); return }
      let finish!: () => void
      routed = new Promise<void>(resolve => { finish = resolve })
      requestHeld = true; intercepted()
      try { await gate; await route.continue() } finally { finish() }
    })
    let acknowledged = false
    const submitting = submitAssessment(page, attempt.id).then(value => { acknowledged = true; return value })
    // Retain a rejection until the awaited command below, without an unhandled promise.
    void submitting.catch(() => undefined)
    await Promise.race([held, submitting.then(() => {
      if (!requestHeld) throw new Error('Submission finished without the expected real request gate')
    })])
    const premature = await page.request.get(`/api/v1/attempts/${attempt.id}/result`)
    expect(premature.status()).toBe(409)
    expect((await premature.json()).error.code).toBe('ATTEMPT_NOT_SUBMITTED')
    const active = await page.request.get(`/api/v1/attempts/${attempt.id}`)
    expect(active.status()).toBe(200)
    const before: AttemptSnapshot = await active.json()
    expect(before.status).toBe('active')
    expect(before.revision).toBe(attempt.revision)
    expect(acknowledged).toBe(false)

    if (!release) throw new Error('Submission gate was not initialized')
    release()
    const ack = await submitting
    expect(ack.revision).toBeGreaterThan(attempt.revision)
    expect(acknowledged).toBe(true)
    await expect.poll(async () => {
      const response = await page.request.get(`/api/v1/attempts/${attempt.id}/result`)
      if (response.status() === 202) return false
      expect(response.status()).toBe(200)
      const result = await response.json()
      expect(result.grading_revision).toBe(1)
      expect(result.status).toBe('needs_review')
      expect(result.items.every((item: { score: number | null }) => item.score === null)).toBe(true)
      return true
    }).toBe(true)
    const after = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`)
    expect(after.status()).toBe(200)
    expect((await after.json()).responses).toEqual(savedResponses.responses)
    writeFileSync(info.outputPath('actual-submission-ack.json'), JSON.stringify({
      scope: 'Real UI, held outgoing submit request, actual HTTP/SQLite state and grading worker; no fabricated response.',
      before_ack: { result_status: 409, error_code: 'ATTEMPT_NOT_SUBMITTED', attempt_status: before.status, revision: before.revision },
      submission_ack: { status: ack.status, revision: ack.revision },
      grading_revision: 1, original_responses_preserved: true, mathematical_approval: 'NOT_RUN',
    }, null, 2))
  } finally { release?.(); await routed; await runtime.close() }
})
