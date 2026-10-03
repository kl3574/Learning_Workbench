# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: independent-review-form-race.spec.ts >> independent audit held real Review GET interleaves native fill and preserves exact form memory through original Policy recovery
- Location: ../../tests/e2e/independent-review-form-race.spec.ts:7:1

# Error details

```
Error: expect(locator).toHaveValue(expected) failed

Locator:  getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByRole('region', { name: '恢复的临时审核表单 1', exact: true }).getByLabel('本次审核备注', { exact: true })
Expected: "尚未提交的原创备注 🧠"
Received: ""
Timeout:  5000ms

Call log:
  - Expect "toHaveValue" getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByRole('region', { name: '恢复的临时审核表单 1', exact: true }).getByLabel('本次审核备注', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByRole('region', { name: '恢复的临时审核表单 1', exact: true }).getByLabel('本次审核备注', { exact: true })
    12 × locator resolved to <textarea aria-label="本次审核备注"></textarea>
       - unexpected value ""

```

```yaml
- textbox "本次审核备注"
```

# Test source

```ts
  30  |     const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/drafts/${id}/review`))
  31  |     await panel.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
  32  |     const created = await creating; expect(created.status()).toBe(202); const ack = await created.json()
  33  |     await expect(panel.getByRole('button', { name: '另行读取当前审核回执', exact: true })).toBeEnabled()
  34  |     await page.evaluate(() => {
  35  |       const events: unknown[] = [], ids = new WeakMap<Element, number>(); let last = '', next = 0
  36  |       const identity = (element: Element | null) => { if (!element) return null; if (!ids.has(element)) ids.set(element, ++next); return { id: ids.get(element), tag: element.tagName, label: element.getAttribute('aria-label'), connected: element.isConnected } }
  37  |       const snapshot = () => ({ active: identity(document.activeElement), notes: [...document.querySelectorAll<HTMLTextAreaElement>('textarea[aria-label="本次审核备注"]')].map(el => ({ ...identity(el), value: el.value, disabled: el.disabled })) })
  38  |       const record = (kind: string, event?: Event) => { if (events.length < 150) events.push({ at: performance.now(), kind, target: event?.target instanceof Element ? identity(event.target) : null, ...snapshot() }) }
  39  |       const observer = new MutationObserver(() => { const current = JSON.stringify(snapshot()); if (current !== last) { last = current; record('DOM mutation') } })
  40  |       observer.observe(document.querySelector('.review-panel')!, { subtree: true, childList: true, attributes: true, attributeFilter: ['disabled'] })
  41  |       for (const type of ['focusin', 'focusout', 'beforeinput', 'input', 'change']) document.addEventListener(type, event => record(type, event), true)
  42  |       Object.assign(window, { independentReviewInputEvents: events, independentReviewInputRecord: record })
  43  |       record('installed before explicit read')
  44  |     })
  45  |     // Diagnostic-only named owner port gate. Keep the actual HTTP/session bytes;
  46  |     // delay only this Publication refresh resolution after Review selection.
  47  |     await page.evaluate(async () => {
  48  |       const path = '/src/features/draftPublication/publicationClient.ts'
  49  |       const { publicationClient } = await import(path), original = publicationClient.session
  50  |       let release!: () => void
  51  |       const held = new Promise<void>(resolve => { release = resolve })
  52  |       let once = false
  53  |       publicationClient.session = async () => {
  54  |         const actual = await original()
  55  |         if (!once) { once = true; Object.assign(window, { independentPublicationHeld: true }); await held }
  56  |         return actual
  57  |       }
  58  |       Object.assign(window, { independentPublicationRelease: release })
  59  |     })
  60  |     let releaseRead!: () => void, readHeld!: () => void
  61  |     const release = new Promise<void>(resolve => { releaseRead = resolve })
  62  |     const held = new Promise<void>(resolve => { readHeld = resolve })
  63  |     let intercepted = false
  64  |     await page.route(`**/api/v1/reviews/${ack.id}`, async route => {
  65  |       if (intercepted || route.request().method() !== 'GET') { await route.continue(); return }
  66  |       intercepted = true
  67  |       const response = await route.fetch()
  68  |       readHeld(); await release; await route.fulfill({ response })
  69  |     })
  70  |     await panel.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  71  |     await held
  72  |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toBeDisabled()
  73  |     const original: StoredReviewReceipt = await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())
  74  |     const note = '尚未提交的原创备注 🧠', reason = '尚未提交的原创人工理由：未进行真实学术验收。'
  75  |     // Diagnostic-only transport gate, pinned to installed Playwright 1.63.0.
  76  |     // Raw sendText delegates to Chromium Input.insertText, after fill's enabled
  77  |     // check/focus. Only the known original synthetic note is delayed.
  78  |     type Raw = { sendText: (progress: unknown, text: string) => Promise<void> }
  79  |     const raw = (page as unknown as { _connection: { toImpl: (p: unknown) => { keyboard: {_raw: Raw} } } })._connection.toImpl(page).keyboard._raw
  80  |     const send = raw.sendText.bind(raw)
  81  |     let releaseInput!: () => void, enteredInput = false
  82  |     const inputGate = new Promise<void>(resolve => { releaseInput = resolve })
  83  |     raw.sendText = async (progress, text) => { if (text === note) { enteredInput = true; await inputGate } await send(progress, text) }
  84  |     const filling = panel.getByLabel('本次审核备注', { exact: true }).fill(note)
  85  |     releaseRead()
  86  |     await expect.poll(() => enteredInput).toBe(true)
  87  |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toBeDisabled()
  88  |     await page.evaluate(() => (window as unknown as {independentReviewInputRecord: (s: string) => void}).independentReviewInputRecord('before releasing held native Input.insertText while Publication busy'))
  89  |     releaseInput(); await filling; raw.sendText = send
  90  |     await page.evaluate(() => (window as unknown as {independentPublicationRelease: () => void}).independentPublicationRelease())
  91  |     await page.evaluate(() => (window as unknown as {independentReviewInputRecord: (s: string) => void}).independentReviewInputRecord('fill promise resolved'))
  92  |     writeFileSync(info.outputPath('independent-input-event-timeline.json'), JSON.stringify(await page.evaluate(() => (window as unknown as {independentReviewInputEvents: unknown[]}).independentReviewInputEvents), null, 2))
  93  |     const samples: unknown[] = []
  94  |     const observe = async (stage: string) => {
  95  |       const snapshot = await page.evaluate(async ({ stage, id }) => {
  96  |         const response = await fetch('/api/v1/session', { credentials: 'same-origin' })
  97  |         const session = await response.json()
  98  |         if (session.role !== 'author' || session.active_independent_attempt_id !== null || session.active_open_book_attempt_id !== null) throw new Error('Synthetic probe cannot inspect restricted form')
  99  |         const path = '/src/features/draftReview/reviewFormMemory.ts'
  100 |         const memory = await import(path)
  101 |         const forms = memory.originalReviewForms(session.workspace_id, 'import', session.actor_session_id)
  102 |         return { stage, forms: forms.map((form: {kind: string; candidate: {draft_id: string}; value: object}) => ({ kind: form.kind, matches: form.candidate.draft_id === id, value: form.value })), notes: [...document.querySelectorAll<HTMLTextAreaElement>('textarea[aria-label="本次审核备注"]')].map(el => el.value) }
  103 |       }, { stage, id })
  104 |       samples.push(snapshot)
  105 |       writeFileSync(info.outputPath('independent-form-memory-observations.json'), JSON.stringify(samples, null, 2))
  106 |       return snapshot
  107 |     }
  108 |     const justFilled = await observe('native_fill_completed')
  109 |     writeFileSync(info.outputPath('independent-input-event-timeline.json'), JSON.stringify(await page.evaluate(() => (window as unknown as {independentReviewInputEvents: unknown[]}).independentReviewInputEvents), null, 2))
  110 |     expect(justFilled.forms).toHaveLength(1) // retain exact original final recovery assertion below
  111 |     await panel.getByLabel('审核理由', { exact: true }).fill(reason)
  112 |     await panel.getByLabel('数学审核决定').selectOption('REJECTED')
  113 |     await observe('after_reason_and_math_inputs')
  114 |     const writes: string[] = [], reads: string[] = []
  115 |     page.on('request', r => { if (/\/(?:review|decision)$/.test(r.url()) && r.method() === 'POST') writes.push(r.url()); if (r.method() === 'GET' && (r.url().endsWith(`/drafts/${id}`) || r.url().endsWith(`/reviews/${ack.id}`))) reads.push(r.url()) })
  116 |     const session = await page.request.get('/api/v1/session').then(r => r.json())
  117 |     const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': crypto.randomUUID() }
  118 |     const started = await page.request.post(`/api/v1/assessments/${fixture.assessment.id}/attempts`, { headers, data: { assessment_ref: fixture.assessment, mode: 'independent' } })
  119 |     expect(started.status()).toBe(201); const attempt: AttemptSnapshot = await started.json()
  120 |     await expect(panel.getByText('当前只开放安全审核任务控制。候选、备注、审核回执与报告已收起；权限恢复后请明确重新读取。', { exact: true })).toBeVisible()
  121 |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toHaveCount(0)
  122 |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  123 |     const abandoned = await page.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })
  124 |     expect(abandoned.status()).toBe(200)
  125 |     const recover = panel.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单', exact: true })
  126 |     await expect(recover).toBeEnabled(); expect(writes).toEqual([])
  127 |     await recover.click()
  128 |     const recoveredNote = panel.getByRole('region', { name: '恢复的临时审核表单 1', exact: true })
  129 |     const recoveredReason = panel.getByRole('region', { name: '恢复的临时审核表单 2', exact: true })
> 130 |     try { await expect(recoveredNote.getByLabel('本次审核备注', { exact: true })).toHaveValue(note) } catch (error) { writeFileSync(info.outputPath('panel.html'), await panel.innerHTML()); throw error }
      |                                                                             ^ Error: expect(locator).toHaveValue(expected) failed
  131 |     await observe('explicit_recovery_completed')
  132 |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  133 |     await expect(recoveredReason.getByLabel('数学审核决定')).toHaveValue('REJECTED')
  134 |     await expect(recoveredReason.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true })).not.toBeChecked()
  135 |     expect(reads.filter(url => url.endsWith(`/drafts/${id}`)).length).toBeGreaterThanOrEqual(2)
  136 |     expect(reads.some(url => url.endsWith(`/reviews/${ack.id}`))).toBe(true)
  137 |     await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  138 |     await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
  139 |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  140 |     await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  141 |     await expect(recover).toBeEnabled(); await expect(recoveredReason).toHaveCount(0)
  142 |     await recover.click(); await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  143 |     expect(writes).toEqual([])
  144 |     expect(await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())).toEqual(original)
  145 |     expect(await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())).toEqual(draft)
  146 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  147 |     await page.getByRole('button', { name: '返回导入与审核', exact: true }).click()
  148 |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  149 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  150 |     await page.getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭', exact: true }).click()
  151 |     await page.getByRole('button', { name: '导入', exact: true }).click()
  152 |     await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
  153 |     await expect(panel.getByRole('button', { name: `读取审核任务 ${ack.id}`, exact: true })).toBeVisible()
  154 |     await expect(recover).toHaveCount(0)
  155 |     expect(writes).toEqual([]); expect(errors).toEqual([])
  156 |     writeFileSync(info.outputPath('review-form-memory.json'), JSON.stringify({ scope: 'Synthetic UI, real SQLite/HTTP/worker/Policy; no academic approval', candidate: { id, revision: draft.revision, sha256: draft.candidate_sha256 }, original_review: original, attempt_id: attempt.id, protected_reads: reads, automatic_writes: writes, errors }, null, 2))
  157 |   } finally { writeFileSync(info.outputPath('http-trace.json'), JSON.stringify(trace, null, 2)); await runtime.close() }
  158 | })
  159 | 
```