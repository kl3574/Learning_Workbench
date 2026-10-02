import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AttemptSnapshot, ImportDraftSnapshot, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'

test('independent audit held real Review GET interleaves native fill and preserves exact form memory through original Policy recovery', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), errors: string[] = [], trace: { method: string; path: string; status: number }[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message)); page.on('response', r => { trace.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() }) }); await runtime.authenticateOnly(page)
    const fixture = originalAssessmentPackage('reviewformpolicy')
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.getByRole('button', { name: '导入', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '导入', exact: true })
    await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await dialog.getByLabel('解析格式').selectOption('markdown')
    await dialog.getByLabel('选择导入文件', { exact: true }).setInputFiles({ name: 'original-review-form.md', mimeType: 'text/markdown', buffer: Buffer.from('# 原创审核表单恢复材料\n\n只验证软件数据保留，不作学术验收。\n') })
    await dialog.getByRole('button', { name: '上传并生成预览', exact: true }).click()
    await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
    await expect(dialog.getByLabel('当前候选正文', { exact: true })).toBeVisible()
    const id = await dialog.getByLabel('选择预览候选').inputValue()
    const draft: ImportDraftSnapshot = await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())
    await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
    const panel = dialog.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await panel.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
    const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/drafts/${id}/review`))
    await panel.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
    const created = await creating; expect(created.status()).toBe(202); const ack = await created.json()
    await expect(panel.getByRole('button', { name: '另行读取当前审核回执', exact: true })).toBeEnabled()
    await page.evaluate(() => {
      const events: unknown[] = [], ids = new WeakMap<Element, number>(); let last = '', next = 0
      const identity = (element: Element | null) => { if (!element) return null; if (!ids.has(element)) ids.set(element, ++next); return { id: ids.get(element), tag: element.tagName, label: element.getAttribute('aria-label'), connected: element.isConnected } }
      const snapshot = () => ({ active: identity(document.activeElement), notes: [...document.querySelectorAll<HTMLTextAreaElement>('textarea[aria-label="本次审核备注"]')].map(el => ({ ...identity(el), value: el.value, disabled: el.disabled })) })
      const record = (kind: string, event?: Event) => { if (events.length < 150) events.push({ at: performance.now(), kind, target: event?.target instanceof Element ? identity(event.target) : null, ...snapshot() }) }
      const observer = new MutationObserver(() => { const current = JSON.stringify(snapshot()); if (current !== last) { last = current; record('DOM mutation') } })
      observer.observe(document.querySelector('.review-panel')!, { subtree: true, childList: true, attributes: true, attributeFilter: ['disabled'] })
      for (const type of ['focusin', 'focusout', 'beforeinput', 'input', 'change']) document.addEventListener(type, event => record(type, event), true)
      Object.assign(window, { independentReviewInputEvents: events, independentReviewInputRecord: record })
      record('installed before explicit read')
    })
    // Diagnostic-only named owner port gate. Keep the actual HTTP/session bytes;
    // delay only this Publication refresh resolution after Review selection.
    await page.evaluate(async () => {
      const path = '/src/features/draftPublication/publicationClient.ts'
      const { publicationClient } = await import(path), original = publicationClient.session
      let release!: () => void
      const held = new Promise<void>(resolve => { release = resolve })
      let once = false
      publicationClient.session = async () => {
        const actual = await original()
        if (!once) { once = true; Object.assign(window, { independentPublicationHeld: true }); await held }
        return actual
      }
      Object.assign(window, { independentPublicationRelease: release })
    })
    let releaseRead!: () => void, readHeld!: () => void
    const release = new Promise<void>(resolve => { releaseRead = resolve })
    const held = new Promise<void>(resolve => { readHeld = resolve })
    let intercepted = false
    await page.route(`**/api/v1/reviews/${ack.id}`, async route => {
      if (intercepted || route.request().method() !== 'GET') { await route.continue(); return }
      intercepted = true
      const response = await route.fetch()
      readHeld(); await release; await route.fulfill({ response })
    })
    await panel.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
    await held
    await expect(panel.getByLabel('本次审核备注', { exact: true })).toBeDisabled()
    const original: StoredReviewReceipt = await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())
    const note = '尚未提交的原创备注 🧠', reason = '尚未提交的原创人工理由：未进行真实学术验收。'
    // Diagnostic-only transport gate, pinned to installed Playwright 1.63.0.
    // Raw sendText delegates to Chromium Input.insertText, after fill's enabled
    // check/focus. Only the known original synthetic note is delayed.
    type Raw = { sendText: (progress: unknown, text: string) => Promise<void> }
    const raw = (page as unknown as { _connection: { toImpl: (p: unknown) => { keyboard: {_raw: Raw} } } })._connection.toImpl(page).keyboard._raw
    const send = raw.sendText.bind(raw)
    let releaseInput!: () => void, enteredInput = false
    const inputGate = new Promise<void>(resolve => { releaseInput = resolve })
    raw.sendText = async (progress, text) => { if (text === note) { enteredInput = true; await inputGate } await send(progress, text) }
    const filling = panel.getByLabel('本次审核备注', { exact: true }).fill(note)
    releaseRead()
    await expect.poll(() => enteredInput).toBe(true)
    await expect(panel.getByLabel('本次审核备注', { exact: true })).toBeDisabled()
    await page.evaluate(() => (window as unknown as {independentReviewInputRecord: (s: string) => void}).independentReviewInputRecord('before releasing held native Input.insertText while Publication busy'))
    releaseInput(); await filling; raw.sendText = send
    await page.evaluate(() => (window as unknown as {independentPublicationRelease: () => void}).independentPublicationRelease())
    await page.evaluate(() => (window as unknown as {independentReviewInputRecord: (s: string) => void}).independentReviewInputRecord('fill promise resolved'))
    writeFileSync(info.outputPath('independent-input-event-timeline.json'), JSON.stringify(await page.evaluate(() => (window as unknown as {independentReviewInputEvents: unknown[]}).independentReviewInputEvents), null, 2))
    const samples: unknown[] = []
    const observe = async (stage: string) => {
      const snapshot = await page.evaluate(async ({ stage, id }) => {
        const response = await fetch('/api/v1/session', { credentials: 'same-origin' })
        const session = await response.json()
        if (session.role !== 'author' || session.active_independent_attempt_id !== null || session.active_open_book_attempt_id !== null) throw new Error('Synthetic probe cannot inspect restricted form')
        const path = '/src/features/draftReview/reviewFormMemory.ts'
        const memory = await import(path)
        const forms = memory.originalReviewForms(session.workspace_id, 'import', session.actor_session_id)
        return { stage, forms: forms.map((form: {kind: string; candidate: {draft_id: string}; value: object}) => ({ kind: form.kind, matches: form.candidate.draft_id === id, value: form.value })), notes: [...document.querySelectorAll<HTMLTextAreaElement>('textarea[aria-label="本次审核备注"]')].map(el => el.value) }
      }, { stage, id })
      samples.push(snapshot)
      writeFileSync(info.outputPath('independent-form-memory-observations.json'), JSON.stringify(samples, null, 2))
      return snapshot
    }
    const justFilled = await observe('native_fill_completed')
    writeFileSync(info.outputPath('independent-input-event-timeline.json'), JSON.stringify(await page.evaluate(() => (window as unknown as {independentReviewInputEvents: unknown[]}).independentReviewInputEvents), null, 2))
    expect(justFilled.forms).toHaveLength(1) // retain exact original final recovery assertion below
    await panel.getByLabel('审核理由', { exact: true }).fill(reason)
    await panel.getByLabel('数学审核决定').selectOption('REJECTED')
    await observe('after_reason_and_math_inputs')
    const writes: string[] = [], reads: string[] = []
    page.on('request', r => { if (/\/(?:review|decision)$/.test(r.url()) && r.method() === 'POST') writes.push(r.url()); if (r.method() === 'GET' && (r.url().endsWith(`/drafts/${id}`) || r.url().endsWith(`/reviews/${ack.id}`))) reads.push(r.url()) })
    const session = await page.request.get('/api/v1/session').then(r => r.json())
    const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': crypto.randomUUID() }
    const started = await page.request.post(`/api/v1/assessments/${fixture.assessment.id}/attempts`, { headers, data: { assessment_ref: fixture.assessment, mode: 'independent' } })
    expect(started.status()).toBe(201); const attempt: AttemptSnapshot = await started.json()
    await expect(panel.getByText('当前只开放安全审核任务控制。候选、备注、审核回执与报告已收起；权限恢复后请明确重新读取。', { exact: true })).toBeVisible()
    await expect(panel.getByLabel('本次审核备注', { exact: true })).toHaveCount(0)
    await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
    const abandoned = await page.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })
    expect(abandoned.status()).toBe(200)
    const recover = panel.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单', exact: true })
    await expect(recover).toBeEnabled(); expect(writes).toEqual([])
    await recover.click()
    const recoveredNote = panel.getByRole('region', { name: '恢复的临时审核表单 1', exact: true })
    const recoveredReason = panel.getByRole('region', { name: '恢复的临时审核表单 2', exact: true })
    try { await expect(recoveredNote.getByLabel('本次审核备注', { exact: true })).toHaveValue(note) } catch (error) { writeFileSync(info.outputPath('panel.html'), await panel.innerHTML()); throw error }
    await observe('explicit_recovery_completed')
    await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
    await expect(recoveredReason.getByLabel('数学审核决定')).toHaveValue('REJECTED')
    await expect(recoveredReason.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true })).not.toBeChecked()
    expect(reads.filter(url => url.endsWith(`/drafts/${id}`)).length).toBeGreaterThanOrEqual(2)
    expect(reads.some(url => url.endsWith(`/reviews/${ack.id}`))).toBe(true)
    await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
    await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
    await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(recover).toBeEnabled(); await expect(recoveredReason).toHaveCount(0)
    await recover.click(); await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
    expect(writes).toEqual([])
    expect(await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())).toEqual(original)
    expect(await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())).toEqual(draft)
    await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.getByRole('button', { name: '返回导入与审核', exact: true }).click()
    await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
    await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭', exact: true }).click()
    await page.getByRole('button', { name: '导入', exact: true }).click()
    await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
    await expect(panel.getByRole('button', { name: `读取审核任务 ${ack.id}`, exact: true })).toBeVisible()
    await expect(recover).toHaveCount(0)
    expect(writes).toEqual([]); expect(errors).toEqual([])
    writeFileSync(info.outputPath('review-form-memory.json'), JSON.stringify({ scope: 'Synthetic UI, real SQLite/HTTP/worker/Policy; no academic approval', candidate: { id, revision: draft.revision, sha256: draft.candidate_sha256 }, original_review: original, attempt_id: attempt.id, protected_reads: reads, automatic_writes: writes, errors }, null, 2))
  } finally { writeFileSync(info.outputPath('http-trace.json'), JSON.stringify(trace, null, 2)); await runtime.close() }
})
