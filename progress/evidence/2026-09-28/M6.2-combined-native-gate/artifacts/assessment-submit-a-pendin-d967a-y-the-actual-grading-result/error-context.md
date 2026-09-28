# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: assessment-submit.spec.ts >> a pending real submission remains unsubmitted until its exact acknowledgement, then exposes only the actual grading result
- Location: ../../tests/e2e/assessment-submit.spec.ts:7:1

# Error details

```
TimeoutError: locator.check: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('radio', { name: '独立测试', exact: true })

```

# Test source

```ts
  1  | import { writeFileSync } from 'node:fs'
  2  | import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3  | import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'
  4  | import { importAssessmentPackage, originalAssessmentPackage, submitAssessment } from './assessmentTestData'
  5  | import { RestartRuntime } from './restartRuntime'
  6  | 
  7  | test('a pending real submission remains unsubmitted until its exact acknowledgement, then exposes only the actual grading result', async ({ playwright }, info) => {
  8  |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('submitack')
  9  |   let release: (() => void) | undefined, routed: Promise<void> | undefined
  10 |   try {
  11 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  12 |     await runtime.authenticateOnly(page)
  13 |     const imported = await importAssessmentPackage(page, fixture)
  14 |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  15 |     await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
> 16 |     await page.getByRole('radio', { name: '独立测试', exact: true }).check()
     |                                                                  ^ TimeoutError: locator.check: Timeout 10000ms exceeded.
  17 |     await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  18 |     const creating = page.waitForResponse(response => response.request().method() === 'POST'
  19 |       && new URL(response.url()).pathname === `/api/v1/assessments/${fixture.assessment.id}/attempts`)
  20 |     await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  21 |     const created = await creating
  22 |     expect(created.status()).toBe(201)
  23 |     const attempt: AttemptSnapshot = await created.json()
  24 |     await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  25 |     const saved = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`)
  26 |     expect(saved.status()).toBe(200)
  27 |     const savedResponses = await saved.json()
  28 | 
  29 |     let intercepted!: () => void, requestHeld = false
  30 |     const held = new Promise<void>(resolve => { intercepted = resolve })
  31 |     const gate = new Promise<void>(resolve => { release = resolve })
  32 |     await page.route(`**/api/v1/attempts/${attempt.id}/submit`, async route => {
  33 |       if (route.request().method() !== 'POST') { await route.continue(); return }
  34 |       let finish!: () => void
  35 |       routed = new Promise<void>(resolve => { finish = resolve })
  36 |       requestHeld = true; intercepted()
  37 |       try { await gate; await route.continue() } finally { finish() }
  38 |     })
  39 |     let acknowledged = false
  40 |     const submitting = submitAssessment(page, attempt.id).then(value => { acknowledged = true; return value })
  41 |     // Retain a rejection until the awaited command below, without an unhandled promise.
  42 |     void submitting.catch(() => undefined)
  43 |     await Promise.race([held, submitting.then(() => {
  44 |       if (!requestHeld) throw new Error('Submission finished without the expected real request gate')
  45 |     })])
  46 |     const premature = await page.request.get(`/api/v1/attempts/${attempt.id}/result`)
  47 |     expect(premature.status()).toBe(409)
  48 |     expect((await premature.json()).error.code).toBe('ATTEMPT_NOT_SUBMITTED')
  49 |     const active = await page.request.get(`/api/v1/attempts/${attempt.id}`)
  50 |     expect(active.status()).toBe(200)
  51 |     const before: AttemptSnapshot = await active.json()
  52 |     expect(before.status).toBe('active')
  53 |     expect(before.revision).toBe(attempt.revision)
  54 |     expect(acknowledged).toBe(false)
  55 | 
  56 |     if (!release) throw new Error('Submission gate was not initialized')
  57 |     release()
  58 |     const ack = await submitting
  59 |     expect(ack.revision).toBeGreaterThan(attempt.revision)
  60 |     expect(acknowledged).toBe(true)
  61 |     await expect.poll(async () => {
  62 |       const response = await page.request.get(`/api/v1/attempts/${attempt.id}/result`)
  63 |       if (response.status() === 202) return false
  64 |       expect(response.status()).toBe(200)
  65 |       const result = await response.json()
  66 |       expect(result.grading_revision).toBe(1)
  67 |       expect(result.status).toBe('needs_review')
  68 |       expect(result.items.every((item: { score: number | null }) => item.score === null)).toBe(true)
  69 |       return true
  70 |     }).toBe(true)
  71 |     const after = await page.request.get(`/api/v1/attempts/${attempt.id}/responses`)
  72 |     expect(after.status()).toBe(200)
  73 |     expect((await after.json()).responses).toEqual(savedResponses.responses)
  74 |     writeFileSync(info.outputPath('actual-submission-ack.json'), JSON.stringify({
  75 |       scope: 'Real UI, held outgoing submit request, actual HTTP/SQLite state and grading worker; no fabricated response.',
  76 |       before_ack: { result_status: 409, error_code: 'ATTEMPT_NOT_SUBMITTED', attempt_status: before.status, revision: before.revision },
  77 |       submission_ack: { status: ack.status, revision: ack.revision },
  78 |       grading_revision: 1, original_responses_preserved: true, mathematical_approval: 'NOT_RUN',
  79 |     }, null, 2))
  80 |   } finally { release?.(); await routed; await runtime.close() }
  81 | })
  82 | 
```