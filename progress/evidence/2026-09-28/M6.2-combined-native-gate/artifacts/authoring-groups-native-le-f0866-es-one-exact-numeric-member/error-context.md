# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: authoring-groups.spec.ts >> native lesson group preserves its plan and formulas, then separately declines and executes one exact numeric member
- Location: ../../tests/e2e/authoring-groups.spec.ts:235:1

# Error details

```
TimeoutError: page.waitForResponse: Timeout 10000ms exceeded while waiting for event "response"
```

# Test source

```ts
  154 |   for (const name of ['私有解答草稿', '组合草稿候选', '受保护创作详情', '冻结的内容计划', '独立数值执行批准', '实际数值结果']) await expect(dialog.getByRole('region', { name, exact: true })).toHaveCount(0)
  155 |   const control = dialog.getByRole('region', { name: '创作任务安全控制', exact: true })
  156 |   await expect(control).toBeVisible()
  157 |   expect((await page.request.get(`/api/v1/authoring/jobs/${first.id}`)).status()).toBe(403)
  158 |   expect((await page.request.get(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}`)).status()).toBe(403)
  159 |   if (draft.root.entity !== 'lesson') expect((await page.request.get(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`)).status()).toBe(403)
  160 |   const attempts: { key: string; body: unknown }[] = []
  161 |   let original!: JobSnapshot
  162 |   let firstResponseDropped = false
  163 |   const routePattern = `**/api/v1/jobs/${ack.id}/cancel`
  164 |   await page.route(routePattern, async route => {
  165 |     const request = route.request(); attempts.push({ key: request.headers()['idempotency-key'], body: request.postDataJSON() })
  166 |     if (attempts.length === 1) {
  167 |       const actual = await route.fetch(); expect(actual.status()).toBe(200); original = await actual.json()
  168 |       await route.abort('failed'); firstResponseDropped = true
  169 |     } else await route.continue()
  170 |   })
  171 |   try {
  172 |     await control.getByRole('button', { name: `明确取消任务 ${ack.id}`, exact: true }).click()
  173 |     await expect.poll(() => firstResponseDropped).toBe(true)
  174 |     await expect(dialog.getByText('取消任务 · 结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
  175 |     expect(attempts).toHaveLength(1); expect(attempts[0].body).toEqual({ expected_revision: before.revision })
  176 |     expect(original.id).toBe(ack.id); expect(original.status).toBe('cancelled'); expect(original.revision).toBe(before.revision + 1)
  177 |     const replaying = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/api/v1/jobs/${ack.id}/cancel`))
  178 |     await dialog.getByRole('button', { name: `回放原命令 ${attempts[0].key}`, exact: true }).click()
  179 |     const replay = await replaying; expect(replay.status()).toBe(200); expect(await replay.json()).toEqual(original)
  180 |     expect(attempts).toHaveLength(2); expect(attempts[1]).toEqual(attempts[0])
  181 |     await expect(control.getByText(`${ack.id} · cancelled · r${original.revision}`, { exact: true })).toBeVisible()
  182 |     const final: JobSnapshot = await page.request.get(`/api/v1/jobs/${ack.id}`).then(value => value.json())
  183 |     expect(final).toEqual(original); expect(final.result_refs).toEqual([])
  184 |     await expect(control.getByRole('button', { name: `明确取消任务 ${first.id}`, exact: true })).toBeDisabled()
  185 |     expect((await page.request.get(`/api/v1/jobs/${first.id}`).then(value => value.json())).status).toBe('completed')
  186 |     expect(runtime.control().received_request_count).toBe(1)
  187 |     return { second_prepare_ack: ack, second_prepared: second, private_before_lock: privateBeforeLock, before, attempts, original_cancel_ack: original, readback: final, permission: 'actual author-to-learner role change; academic endpoints denied with 403; safe control remains available' }
  188 |   } finally { await page.unroute(routePattern) }
  189 | }
  190 | 
  191 | async function restartAndReadOriginal(runtime: AuthoringRuntime, browser: BrowserType, completed: AuthoringGroupJobView, draft: AuthoringGroupDraftView, solution: AuthoringPrivateSolutionView | null, errors: string[]) {
  192 |   const databaseBefore = runtime.databaseIdentity(), providerBefore = runtime.control(), processesBefore = [...runtime.generations]
  193 |   expect(providerBefore.received_request_count).toBe(1); expect(providerBefore.validated_request_count).toBe(1)
  194 |   expect(providerBefore.target_initialization).toBe('published_once')
  195 |   await runtime.closeBrowser()
  196 |   await runtime.restartApiAfterBrowserClosed()
  197 |   expect(runtime.databaseIdentity()).toEqual(databaseBefore)
  198 |   expect(runtime.generations).toHaveLength(processesBefore.length + 1)
  199 |   const context = await runtime.openBrowser(browser), page = context.pages()[0]
  200 |   page.on('pageerror', error => errors.push(error.message))
  201 |   // Resume the existing workspace through the actual session endpoints. No
  202 |   // provider config/secret write, fixture import, or content publication occurs.
  203 |   await runtime.authenticateOnly(page)
  204 |   const auth: SessionResponse = await page.request.get('/api/v1/session').then(value => value.json())
  205 |   expect((await page.request.post('/api/v1/session/role', { data: { role: 'author' }, headers: { Origin: runtime.origin, 'X-CSRF-Token': auth.csrf_token, 'Idempotency-Key': 'native-group-author-after-restart' } })).status()).toBe(200)
  206 |   await page.reload(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
  207 |   await page.getByRole('button', { name: '创作', exact: true }).click()
  208 |   const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  209 |   await dialog.getByRole('button', { name: `读取创作详情 ${completed.summary.id}`, exact: true }).click()
  210 |   await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toBeVisible()
  211 |   const reloaded: AuthoringGroupJobView = await page.request.get(`/api/v1/authoring/jobs/${completed.summary.id}`).then(value => value.json())
  212 |   expect(reloaded).toEqual(completed)
  213 |   await dialog.getByRole('button', { name: '读取这份准确组合候选', exact: true }).click()
  214 |   const group = dialog.getByRole('region', { name: '组合草稿候选', exact: true })
  215 |   await expect(group.getByRole('heading', { name: draft.root.title, exact: true })).toBeVisible()
  216 |   await expect(group.getByRole('region', { name: '冻结的内容计划', exact: true })).toContainText(objective)
  217 |   const candidate: AuthoringGroupDraftView = await page.request.get(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}`).then(value => value.json())
  218 |   expect(candidate).toEqual(draft)
  219 |   let privateReadback: AuthoringPrivateSolutionView | null = null
  220 |   if (solution) {
  221 |     await expect(group.getByRole('region', { name: '私有解答草稿', exact: true })).toHaveCount(0)
  222 |     const reading = page.waitForResponse(value => value.request().method() === 'GET' && value.url().endsWith(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`))
  223 |     await group.getByRole('button', { name: '明确读取第 1 题的私有解答草稿', exact: true }).click()
  224 |     const response = await reading; expect(response.status()).toBe(200); privateReadback = await response.json()
  225 |     expect(privateReadback).toEqual(solution)
  226 |     await expect(group.getByRole('region', { name: '私有解答草稿', exact: true })).toContainText('私有合成解答')
  227 |   }
  228 |   const providerAfter = runtime.control()
  229 |   expect(providerAfter.api_pid).not.toBe(providerBefore.api_pid)
  230 |   expect(providerAfter.target_initialization).toBe('reused_exact'); expect(providerAfter.target_refs).toEqual(providerBefore.target_refs)
  231 |   expect(providerAfter.received_request_count).toBe(0); expect(providerAfter.validated_request_count).toBe(0); expect(providerAfter.invalid_request_count).toBe(0)
  232 |   return { database_before: databaseBefore, database_after: runtime.databaseIdentity(), api_processes: runtime.generations, provider_before: providerBefore, provider_after: providerAfter, job: reloaded, draft: candidate, private_solution: privateReadback, scope: 'Same SQLite file and exact targets; first process one Provider request, restarted process zero additional requests. Explicit author UI reopens original persisted plan, candidate and private solution. No re-seeding or provider reconfiguration.' }
  233 | }
  234 | 
  235 | test('native lesson group preserves its plan and formulas, then separately declines and executes one exact numeric member', async ({ playwright }, info) => {
  236 |   test.setTimeout(120_000)
  237 |   const runtime = await AuthoringRuntime.start('lesson', 'groups'), errors: string[] = []
  238 |   try {
  239 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  240 |     page.on('pageerror', error => errors.push(error.message))
  241 |     await runtime.authenticateOnly(page); await configure(page, runtime)
  242 |     const dialog = await form(page, 'lesson')
  243 |     const preparing = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/authoring/group-jobs'))
  244 |     await dialog.getByRole('button', { name: '明确准备本次组合创作任务', exact: true }).click()
  245 |     const accepted = await preparing; expect(accepted.status()).toBe(202)
  246 |     const ack: JobRef = await accepted.json(), prepared = await readPrepared(page, dialog, ack)
  247 |     expect(runtime.control().received_request_count).toBe(0)
  248 |     const { completed, draft, group, proposal } = await grant(page, dialog, ack)
  249 |     expect(completed.raw_answer).toBe(runtime.control().answer_markdown)
  250 |     await expect(group.locator('.formula svg').first()).toBeVisible()
  251 |     const wide = await picture(page, dialog, group.getByRole('heading', { name: '原创合成倍数定义', exact: true }), 1440, 'group-lesson-1440', info)
  252 |     const narrow = await picture(page, dialog, group.getByRole('heading', { name: '原创合成倍数定义', exact: true }), 390, 'group-lesson-390', info)
  253 |     const first = await numericPreview(page, dialog, group, draft)
> 254 |     const declining = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/api/v1/authoring/group-numeric-checks/${first.id}/decision`))
      |                            ^ TimeoutError: page.waitForResponse: Timeout 10000ms exceeded while waiting for event "response"
  255 |     await dialog.getByRole('button', { name: '明确拒绝本次数值执行', exact: true }).click()
  256 |     const declined = await declining; expect(declined.status()).toBe(200)
  257 |     const declineAck: NumericCheckDecisionAck = await declined.json()
  258 |     expect(declineAck).toEqual({ id: first.id, revision: 2, operation_sha256: first.operation_sha256, decision: 'decline', applied: true, job: null })
  259 |     const declineReading = await page.request.get(`/api/v1/authoring/group-numeric-checks/${first.id}`)
  260 |     expect(declineReading.status()).toBe(200)
  261 |     const declineReadback: AuthoringGroupNumericCheckView = await declineReading.json()
  262 |     expect(declineReadback).toEqual({ ...first, revision: 2, decision: 'decline', job: null, job_revision: null, result: null })
  263 |     const second = await numericPreview(page, dialog, group, draft)
  264 |     expect(second.id).not.toBe(first.id); expect(second.operation_sha256).not.toBe(first.operation_sha256)
  265 |     await dialog.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
  266 |     const approving = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/api/v1/authoring/group-numeric-checks/${second.id}/decision`))
  267 |     await dialog.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click()
  268 |     const approved = await approving; expect(approved.status()).toBe(202)
  269 |     const approveAck: NumericCheckDecisionAck = await approved.json()
  270 |     expect(approveAck).toEqual({ id: second.id, revision: 2, operation_sha256: second.operation_sha256, decision: 'approve_once', applied: true, job: { id: expect.any(String), status: 'queued' } })
  271 |     expect(approveAck.job!.id).not.toBe(ack.id)
  272 |     let numeric!: AuthoringGroupNumericCheckView
  273 |     await expect.poll(async () => { numeric = await page.request.get(`/api/v1/authoring/group-numeric-checks/${second.id}`).then(value => value.json()); return numeric.result !== null }).toBe(true)
  274 |     expect(numeric.id).toBe(second.id); expect(numeric.revision).toBe(2); expect(numeric.decision).toBe('approve_once')
  275 |     expect(numeric.operation_sha256).toBe(second.operation_sha256); expect(numeric.candidate).toEqual(second.candidate); expect(numeric.target).toEqual(second.target)
  276 |     expect(numeric.job!.id).toBe(approveAck.job!.id); expect(numeric.result!.job_id).toBe(approveAck.job!.id)
  277 |     expect(['passed', 'environment_unavailable']).toContain(numeric.result!.outcome)
  278 |     expect(numeric.result!.verdict).toBe(numeric.result!.outcome === 'passed' ? 'PASS' : 'BLOCKED')
  279 |     await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
  280 |     await expect(dialog.getByRole('heading', { name: `实际数值结果：${numeric.result!.verdict}`, exact: true })).toBeVisible()
  281 |     await picture(page, dialog, dialog.getByRole('region', { name: '实际数值结果', exact: true }), 390, 'group-numeric-390', info)
  282 |     const finalDraft: AuthoringGroupDraftView = await page.request.get(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}`).then(value => value.json())
  283 |     expect(finalDraft.candidate).toEqual(draft.candidate); expect(finalDraft.content_plan).toEqual(draft.content_plan)
  284 |     expect(finalDraft.state).toBe('draft'); expect(finalDraft.numeric_check_ids).toEqual([first.id, second.id])
  285 |     await expect.poll(() => runtime.control().validated_request_count).toBe(1)
  286 |     expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0)
  287 |     const cancellation = await cancelSecondWithoutConsent(page, dialog, runtime, ack, finalDraft)
  288 |     const recovery = await restartAndReadOriginal(runtime, playwright.chromium, completed, finalDraft, null, errors)
  289 |     expect(errors).toEqual([])
  290 |     writeFileSync(info.outputPath('group-lesson-actual.json'), JSON.stringify({ scope: 'Real browser, SQLite and test-only loopback single consent. Original pending preview ACKs, actual decision ACKs and declined GET readback are distinct. Numeric actual environment verdict is preserved; BLOCKED is not successful arithmetic. Candidate and quality remain unreviewed draft.', prepared, completed, proposal_id: proposal.id, draft: finalDraft, first_preview_ack: first, second_preview_ack: second, decline_ack: declineAck, decline_readback: declineReadback, approve_ack: approveAck, numeric, cancellation, recovery, runtime: recovery.provider_before, bounds: { wide, narrow }, page_errors: errors }, null, 2))
  291 |   } finally { await runtime.close() }
  292 | })
  293 | 
  294 | test('native practice group replays its lost prepare ACK with one key and clears explicitly read private answers after permission changes', async ({ playwright }, info) => {
  295 |   test.setTimeout(120_000)
  296 |   const runtime = await AuthoringRuntime.start('practice_set', 'groups'), errors: string[] = []
  297 |   try {
  298 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  299 |     page.on('pageerror', error => errors.push(error.message))
  300 |     await runtime.authenticateOnly(page); await configure(page, runtime)
  301 |     const dialog = await form(page, 'practice_set')
  302 |     const attempts: { key: string; body: unknown }[] = []
  303 |     let originalAck!: JobRef
  304 |     await page.route('**/api/v1/authoring/group-jobs', async route => {
  305 |       const request = route.request()
  306 |       attempts.push({ key: request.headers()['idempotency-key'], body: request.postDataJSON() })
  307 |       if (attempts.length === 1) {
  308 |         const actual = await route.fetch(); expect(actual.status()).toBe(202)
  309 |         originalAck = await actual.json()
  310 |         // Server commits the actual first prepare; only its browser response is lost.
  311 |         await route.abort('failed')
  312 |       } else await route.continue()
  313 |     })
  314 |     await dialog.getByRole('button', { name: '明确准备本次组合创作任务', exact: true }).click()
  315 |     await expect(dialog.getByText('准备组合草稿 · 结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
  316 |     expect(attempts).toHaveLength(1); expect(runtime.control().received_request_count).toBe(0)
  317 |     const replaying = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/authoring/group-jobs'))
  318 |     await dialog.getByRole('button', { name: `回放原命令 ${attempts[0].key}`, exact: true }).click()
  319 |     const replay = await replaying; expect(replay.status()).toBe(202); expect(await replay.json()).toEqual(originalAck)
  320 |     expect(attempts).toHaveLength(2); expect(attempts[1]).toEqual(attempts[0])
  321 |     await page.unroute('**/api/v1/authoring/group-jobs')
  322 |     const prepared = await readPrepared(page, dialog, originalAck)
  323 |     expect(prepared.preparation.targets.map(value => value.ref.entity)).toEqual(['lesson', 'concept'])
  324 |     const { completed, draft, group, proposal } = await grant(page, dialog, originalAck)
  325 |     expect(draft.root.entity).toBe('practice_set')
  326 |     expect(JSON.stringify(draft)).not.toContain('accepted_answers'); expect(JSON.stringify(draft)).not.toContain('私有合成解答')
  327 |     await expect(group.getByRole('region', { name: '私有解答草稿', exact: true })).toHaveCount(0)
  328 |     await expect(group.locator('.formula svg').first()).toBeVisible()
  329 |     const wide = await picture(page, dialog, group.getByRole('heading', { name: '第 1 题 · numeric', exact: true }), 1440, 'group-practice-1440', info)
  330 |     const narrow = await picture(page, dialog, group.getByRole('heading', { name: '第 1 题 · numeric', exact: true }), 390, 'group-practice-390', info)
  331 |     const reading = page.waitForResponse(value => value.request().method() === 'GET' && value.url().endsWith(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`))
  332 |     await group.getByRole('button', { name: '明确读取第 1 题的私有解答草稿', exact: true }).click()
  333 |     const response = await reading; expect(response.status()).toBe(200)
  334 |     const solution: AuthoringPrivateSolutionView = await response.json()
  335 |     expect(solution.payload.answer.accepted_answers).toEqual(['18', '18.0'])
  336 |     const privatePanel = group.getByRole('region', { name: '私有解答草稿', exact: true })
  337 |     await expect(privatePanel).toContainText('私有合成解答')
  338 |     await picture(page, dialog, privatePanel, 390, 'group-private-390', info)
  339 |     const cancellation = await cancelSecondWithoutConsent(page, dialog, runtime, originalAck, draft)
  340 |     await expect(privatePanel).toHaveCount(0)
  341 |     await expect.poll(() => runtime.control().validated_request_count).toBe(1)
  342 |     expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0)
  343 |     const recovery = await restartAndReadOriginal(runtime, playwright.chromium, completed, draft, solution, errors)
  344 |     expect(errors).toEqual([])
  345 |     writeFileSync(info.outputPath('group-practice-actual.json'), JSON.stringify({ scope: 'Lost browser prepare response after actual server commit, then explicit identical original command replay. One original Job and one actual loopback model dispatch. Exact existing Content targets, public/private separation and real role change clearing without page reload. No review or publication.', prepare_attempts: attempts, original_prepare_ack: originalAck, prepared, completed, proposal_id: proposal.id, draft, solution, cancellation, recovery, runtime: recovery.provider_before, bounds: { wide, narrow }, page_errors: errors }, null, 2))
  346 |   } finally { await runtime.close() }
  347 | })
  348 | 
  349 | 
  350 | test('native assessment group keeps explicit modes and time, checks its exact private numeric plan, and cancels a separate unconsented job under a permission lock', async ({ playwright }, info) => {
  351 |   test.setTimeout(120_000)
  352 |   const runtime = await AuthoringRuntime.start('assessment', 'groups'), errors: string[] = []
  353 |   try {
  354 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
```