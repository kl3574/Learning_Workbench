# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: recommendations.spec.ts >> real offline and stale decision candidates require explicit 412 correction and current independent policy hides delayed subject sources
- Location: tests/e2e/recommendations.spec.ts:109:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '明确开始本次测试', exact: true })
    - locator resolved to <button disabled class="primary-button">明确开始本次测试</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
      - waiting 100ms
    19 × waiting for element to be visible, enabled and stable
       - element is not enabled
     - retrying click action
       - waiting 500ms

```

# Test source

```ts
  32  |   await expect(dialog.getByText('本机推荐候选存储可用', { exact: true })).toBeVisible()
  33  |   return dialog
  34  | }
  35  | async function selectDecision(dialog: Locator, item: RecommendationView, decision: 'accepted' | 'dismissed', reason: string) {
  36  |   const row = dialog.locator(`[data-recommendation-id="${item.id}"]`)
  37  |   await row.getByRole('button', { name: decision === 'accepted' ? '接受此建议' : '拒绝此建议', exact: true }).click()
  38  |   const editor = dialog.getByRole('region', { name: '推荐决定编辑', exact: true })
  39  |   await editor.getByRole('textbox', { name: '决定理由（可不填）', exact: true }).fill(reason)
  40  |   await expect(editor.getByRole('button', { name: '保存推荐决定', exact: true })).toBeEnabled()
  41  |   return editor
  42  | }
  43  | async function markRead(page: Page, runtime: RestartRuntime, course: ContentRef, lesson: ContentRef) {
  44  |   await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course, lesson }))}`)
  45  |   const response = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/learning/actions'))
  46  |   await page.getByRole('button', { name: '明确标记本节已读', exact: true }).click(); expect((await response).status()).toBe(200)
  47  | }
  48  | async function setGoals(page: Page, runtime: RestartRuntime, concepts: string[], key: string) {
  49  |   const before = await page.request.get('/api/v1/learner/profile'); expect(before.status()).toBe(200)
  50  |   const profile: LearnerProfile = await before.json()
  51  |   const body: ProfileWrite = { expected_revision: profile.revision, goals: ['原创推荐验收：跨教材核对精确对象与来源'], goal_concept_ids: concepts, weekly_minutes: profile.weekly_minutes ?? 120, language: profile.language ?? 'zh-CN', preferred_difficulty: profile.preferred_difficulty ?? 'beginner', self_assessments: (profile.self_assessments ?? []).map(item => ({ concept_id: item.concept_id, level: item.level })) }
  52  |   const saved = await page.request.put('/api/v1/learner/profile', { headers: await headers(page, runtime, key), data: body }); expect(saved.status()).toBe(200)
  53  |   return await saved.json() as LearnerProfile
  54  | }
  55  | 
  56  | test('real recommendation decisions recover a lost ACK across browser and API restart without rewriting later decisions or learning facts', async ({ playwright }, info) => {
  57  |   test.setTimeout(120_000)
  58  |   const runtime = await RestartRuntime.start(), fixture = originalPracticePackage('recommendationacknative', 'learner')
  59  |   const commands: { key: string; if_match: string; body: string }[] = [], errors: string[] = []
  60  |   try {
  61  |     const browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]; page.on('pageerror', value => errors.push(value.message)); await runtime.authenticateOnly(page)
  62  |     const imported = await importPracticePackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  63  |     await markRead(page, runtime, fixture.course, fixture.lesson)
  64  |     const batch = await readyRecommendations(page), item = batch.items.find(value => value.target_ref.id === fixture.practice.id && value.reason_codes.includes('read_without_practice'))!
  65  |     expect(item).toBeTruthy(); expect(item.evidence_refs).toEqual([]); expect(item.activity_refs.some(value => value.kind === 'read_marked' && value.target_ref.id === fixture.lesson.id)).toBe(true); expect(item.estimated_minutes).toBeNull()
  66  |     const before = await facts(page), originalURL = page.url(), dialog = await openRecommendations(page), editor = await selectDecision(dialog, item, 'accepted', '原始接受理由 🧠é，打开内容另作选择')
  67  |     const path = `**/api/v1/recommendations/${item.id}/decision`
  68  |     await page.route(path, async route => { commands.push({ key: route.request().headers()['idempotency-key'], if_match: route.request().headers()['if-match'], body: route.request().postData()! }); const response = await route.fetch(); expect(response.status()).toBe(200); await route.abort('failed') })
  69  |     await editor.getByRole('button', { name: '保存推荐决定', exact: true }).click(); await expect(dialog.getByRole('alert').filter({ hasText: '推荐决定尚未确认' })).toBeVisible()
  70  |     const accepted = (await recommendations(page, item.id)).items[0]; expect(accepted).toMatchObject({ decision: 'accepted', decision_revision: 2, decision_reason: '原始接受理由 🧠é，打开内容另作选择' }); expect(page.url()).toBe(originalURL); expect(await facts(page)).toEqual(before)
  71  |     const remote = await page.request.post(`/api/v1/recommendations/${item.id}/decision`, { headers: { ...await headers(page, runtime, 'native-later-explicit-correction'), 'If-Match': `"${accepted.decision_sha256}"` }, data: { decision: 'dismissed', reason: '另一个真实命令明确更正' } })
  72  |     expect(remote.status()).toBe(200); expect(await remote.json()).toEqual({ id: item.id, revision: 3, applied: true })
  73  |     await dialog.getByRole('button', { name: '关闭学习建议', exact: true }).click(); await page.getByRole('dialog', { name: '保留未同步推荐决定', exact: true }).getByRole('button', { name: '保留本机推荐候选并关闭', exact: true }).click()
  74  |     const identity = runtime.databaseIdentity(), connection = browser.browser(); await runtime.closeBrowser(); expect(connection?.isConnected()).toBe(false); await runtime.restartApiAfterBrowserClosed(); expect(runtime.databaseIdentity()).toEqual(identity)
  75  |     const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; restored.on('pageerror', value => errors.push(value.message)); await runtime.authenticateOnly(restored)
  76  |     const panel = await openRecommendations(restored); await panel.getByRole('button', { name: '恢复推荐候选 1', exact: true }).click()
  77  |     const recovered = panel.getByRole('region', { name: '推荐决定编辑', exact: true }); await expect(recovered.getByRole('heading', { name: '原始基准 · r1', exact: true })).toBeVisible(); await expect(recovered.getByRole('heading', { name: '当前服务端 · r3', exact: true })).toBeVisible(); await expect(recovered.getByRole('textbox')).toHaveValue('原始接受理由 🧠é，打开内容另作选择')
  78  |     expect((await recommendations(restored, item.id)).items[0].decision_revision).toBe(3)
  79  |     await restored.route(path, async route => { commands.push({ key: route.request().headers()['idempotency-key'], if_match: route.request().headers()['if-match'], body: route.request().postData()! }); await route.continue() })
  80  |     const replaying = restored.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/recommendations/${item.id}/decision`))
  81  |     await recovered.getByRole('button', { name: '重试原推荐决定命令', exact: true }).click(); const replay = await replaying; expect(replay.status()).toBe(200); const acknowledgement: MutationAck = await replay.json(); expect(acknowledgement).toEqual({ id: item.id, revision: 2, applied: true })
  82  |     await expect(recovered.getByRole('status')).toContainText('原命令已确认 · 决定修订 2'); await expect(panel.getByText('本机推荐候选存储可用', { exact: true })).toBeVisible(); await expect(recovered.getByRole('heading', { name: '当前服务端 · r3', exact: true })).toBeVisible()
  83  |     expect(commands).toHaveLength(2); expect(commands[0]).toEqual(commands[1]); expect(commands[0].if_match).toBe(`"${item.decision_sha256}"`); expect(JSON.parse(commands[0].body)).toEqual({ decision: 'accepted', reason: '原始接受理由 🧠é，打开内容另作选择' }); const final = (await recommendations(restored, item.id)).items[0]; expect(final).toMatchObject({ decision: 'dismissed', decision_revision: 3, decision_reason: '另一个真实命令明确更正' }); expect(await facts(restored)).toEqual(before)
  84  |     await restored.screenshot({ path: info.outputPath('recommendation-original-ack-1440.png') }); await restored.setViewportSize({ width: 390, height: 844 }); await recovered.getByRole('heading', { name: '原基准、本页候选与服务端', exact: true }).scrollIntoViewIfNeeded(); await expect(panel.getByRole('button', { name: '关闭学习建议', exact: true })).toBeInViewport(); expect(await panel.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); expect(await restored.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390); await restored.screenshot({ path: info.outputPath('recommendation-original-ack-390.png') })
  85  |     expect(errors).toEqual([])
  86  |     writeFileSync(info.outputPath('actual-recommendation-original-ack.json'), JSON.stringify({ scope: 'Original unreviewed learner learnpack, real Import/Reader/API, actual successful HTTP response deliberately dropped before client ACK, actual later correction, persistent Chrome and actual API restart. No expert approval or independent scoring eligibility claimed.', original_item: item, actual_commands: commands, original_acknowledgement: acknowledgement, final_server_item: final, api_generations: runtime.generations.length, database_identity_unchanged: runtime.databaseIdentity().inode === identity.inode, all_learning_facts_unchanged_by_decisions: true, acceptance_did_not_navigate: true, runtime_errors: errors }, null, 2))
  87  |   } finally { await runtime.close() }
  88  | })
  89  | 
  90  | test('real local suggestions cover another imported textbook and open its complete original refs independently of acceptance', async ({ playwright }, info) => {
  91  |   const runtime = await RestartRuntime.start(), shared = originalSharedRecommendationPackages(), [first, second] = shared.packages, errors: string[] = []
  92  |   try {
  93  |     const browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]; page.on('pageerror', value => errors.push(value.message)); await runtime.authenticateOnly(page)
  94  |     for (const fixture of [first, second]) { const imported = await importPracticePackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click() }
  95  |     const before = await facts(page); const profile = await setGoals(page, runtime, [...new Set(before.concepts.concepts.map(value => value.ref.id))], 'native-cross-course-goals')
  96  |     const batch = await readyRecommendations(page); expect(batch.rule_parameters.calibration).toBe('uncalibrated'); expect(batch.warnings.some(value => value.code === 'UNREVIEWED_MATERIAL_ONLY')).toBe(true)
  97  |     const item = batch.items.find(value => value.target_ref.id === shared.block.id && value.reason_codes.includes('user_goal'))!
  98  |     expect(item).toBeTruthy(); expect(item.navigation_options).toHaveLength(4); expect(item.navigation_options).toEqual(expect.arrayContaining([first.course, second.course].flatMap(course_ref => shared.lessons.map(lesson_ref => ({ kind: 'reader', course_ref, lesson_ref, block_ref: shared.block }))))); expect(item.profile_basis?.revision).toBe(profile.revision); expect(item.estimated_minutes).toBeNull(); expect(item.evidence_refs).toEqual([])
  99  |     await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: first.course, lesson: first.lesson }))}`)
  100 |     const dialog = await openRecommendations(page), row = dialog.locator(`[data-recommendation-id="${item.id}"]`)
  101 |     await expect(dialog.getByText('范围：工作区全部可访问教材。读取只核对已有投影，不代表已启动生成。', { exact: true })).toBeVisible(); await expect(row).toContainText('预计用时：未知'); await row.getByText('核对推荐原因与真实来源', { exact: true }).click(); await expect(row).toContainText('原创推荐验收：跨教材核对精确对象与来源')
  102 |     await page.screenshot({ path: info.outputPath('recommendations-cross-course-1440.png') }); await page.setViewportSize({ width: 390, height: 844 }); await row.getByRole('heading').first().scrollIntoViewIfNeeded(); await expect(dialog.getByRole('button', { name: '关闭学习建议', exact: true })).toBeInViewport(); expect(await dialog.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('recommendations-cross-course-390.png') })
  103 |     const opening = row.getByRole('button', { name: `从教材 ${second.course.id} · r${second.course.revision} / 小节 ${shared.lessons[1].id} · r${shared.lessons[1].revision} 打开材料`, exact: true }); expect(await opening.getAttribute('href')).toBeNull(); await expect(row.getByRole('link')).toHaveCount(0); const checking = page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).searchParams.get('recommendation_id') === item.id); await opening.click(); expect((await checking).status()).toBe(200); const target = { course: second.course, lesson: shared.lessons[1], block: shared.block }; await expect.poll(() => new URL(page.url()).searchParams.get('reader')).toBe(JSON.stringify(target)); const href = page.url().slice(runtime.origin.length); expect(new URL(page.url()).hash).toBe(`#block-${shared.block.id}-r${shared.block.revision}`); await expect(page.locator('.real-reader .breadcrumbs')).toContainText('原创推荐四父链教材 b'); await expect(page.locator('.real-reader')).toContainText('同一原创材料的第二精确小节父链')
  104 |     expect((await recommendations(page, item.id)).items[0]).toMatchObject({ decision: 'pending', decision_revision: 1 }); expect((await facts(page)).evidence).toEqual(before.evidence); expect(errors).toEqual([])
  105 |     writeFileSync(info.outputPath('actual-recommendation-cross-course.json'), JSON.stringify({ scope: 'Two original unreviewed learner imports sharing one block with four real course/lesson parent chains; real profile goal write, persisted local projection and explicit checked native Reader navigation. No approval or evidence eligibility injected.', selected_course_before: first.course, opened_original_course: second.course, opened_original_lesson: shared.lessons[1], opened_original_block: shared.block, all_four_navigation_options: item.navigation_options, actual_href: href, source_profile: profile, original_recommendation: item, decision_unchanged_by_navigation: true, independent_evidence_unchanged: true, runtime_errors: errors }, null, 2))
  106 |   } finally { await runtime.close() }
  107 | })
  108 | 
  109 | test('real offline and stale decision candidates require explicit 412 correction and current independent policy hides delayed subject sources', async ({ playwright }, info) => {
  110 |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('recommendationcasnative', 'learner'), errors: string[] = []
  111 |   const commands: { key: string; if_match: string; body: string; transport: string }[] = []
  112 |   try {
  113 |     const browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]; page.on('pageerror', value => errors.push(value.message)); await runtime.authenticateOnly(page)
  114 |     const imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click(); await markRead(page, runtime, fixture.course, fixture.lesson)
  115 |     const item = (await readyRecommendations(page)).items.find(value => value.target_ref.id === fixture.practice.id && value.reason_codes.includes('read_without_practice'))!
  116 |     expect(item).toBeTruthy(); const before = await facts(page), dialog = await openRecommendations(page), editor = await selectDecision(dialog, item, 'dismissed', '原本机拒绝理由 🧠')
  117 |     const path = `**/api/v1/recommendations/${item.id}/decision`
  118 |     await page.route(path, async route => { commands.push({ key: route.request().headers()['idempotency-key'], if_match: route.request().headers()['if-match'], body: route.request().postData()!, transport: 'aborted_before_server' }); await route.abort('internetdisconnected') })
  119 |     await editor.getByRole('button', { name: '保存推荐决定', exact: true }).click(); await expect(dialog.getByRole('alert').filter({ hasText: '推荐决定尚未确认' })).toBeVisible(); expect((await recommendations(page, item.id)).items[0].decision_revision).toBe(1)
  120 |     await page.unroute(path); const external = await page.request.post(`/api/v1/recommendations/${item.id}/decision`, { headers: { ...await headers(page, runtime, 'native-recommendation-concurrent'), 'If-Match': `"${item.decision_sha256}"` }, data: { decision: 'accepted', reason: '另一真实会话的选择' } }); expect(external.status()).toBe(200)
  121 |     await page.route(path, async route => { commands.push({ key: route.request().headers()['idempotency-key'], if_match: route.request().headers()['if-match'], body: route.request().postData()!, transport: 'real_http' }); await route.continue() })
  122 |     const conflicting = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/recommendations/${item.id}/decision`)); await editor.getByRole('button', { name: '重试原推荐决定命令', exact: true }).click(); expect((await conflicting).status()).toBe(412)
  123 |     const comparison = editor.getByRole('region', { name: '推荐决定三方比较', exact: true }); await expect(comparison.getByRole('heading', { name: '原始基准 · r1', exact: true })).toBeVisible(); await expect(comparison.getByRole('heading', { name: '当前服务端 · r2', exact: true })).toBeVisible(); await expect(comparison).toContainText('原本机拒绝理由 🧠'); await expect(comparison).toContainText('另一真实会话的选择'); expect(commands[0].key).toBe(commands[1].key); expect(commands[0].body).toBe(commands[1].body); expect(commands[0].if_match).toBe(commands[1].if_match)
  124 |     await page.setViewportSize({ width: 390, height: 844 }); await comparison.getByRole('heading', { name: '原基准、本页候选与服务端', exact: true }).scrollIntoViewIfNeeded(); await expect(dialog.getByRole('button', { name: '关闭学习建议', exact: true })).toBeInViewport(); expect(await dialog.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('recommendation-412-comparison-390.png') }); expect((await recommendations(page, item.id)).items[0].decision_revision).toBe(2)
  125 |     await editor.getByRole('button', { name: '采用服务端基准，显式更正决定', exact: true }).click(); await editor.getByRole('textbox').fill('明确比较后保留我的拒绝理由'); await expect(editor.getByRole('button', { name: '保存推荐决定', exact: true })).toBeEnabled(); expect(commands).toHaveLength(2); const saving = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/recommendations/${item.id}/decision`)); await editor.getByRole('button', { name: '保存推荐决定', exact: true }).click(); expect((await saving).status()).toBe(200); await expect(editor.getByRole('status')).toContainText('原命令已确认 · 决定修订 3'); expect(commands[2].key).not.toBe(commands[1].key); expect(commands[2].if_match).not.toBe(commands[1].if_match); expect(await facts(page)).toEqual(before)
  126 |     await editor.getByRole('button', { name: '返回推荐列表', exact: true }).click()
  127 |     let release!: () => void, captured!: () => void; const gate = new Promise<void>(done => { release = done }), ready = new Promise<void>(done => { captured = done })
  128 |     await page.route('**/api/v1/recommendations?*', async route => { const response = await route.fetch(); expect(response.status()).toBe(200); captured(); await gate; await route.fulfill({ response }) })
  129 |     await dialog.getByRole('button', { name: '重新读取学习建议', exact: true }).click(); await ready
  130 |     const other = await page.context().newPage()
  131 |     try {
> 132 |       await other.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`); await other.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await other.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); await expect(other.getByText('独立测试进行中', { exact: true }).first()).toBeVisible(); release()
      |                                                                                                                                                                                                                                                                                                                                  ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  133 |       await expect(dialog.locator('[data-recommendation-id]')).toHaveCount(0); await expect(dialog.locator('.recommendation-sources')).toHaveCount(0); await expect(dialog).toContainText('本机候选保留，暂停读写'); expect((await page.request.get(`/api/v1/recommendations?recommendation_id=${item.id}`)).status()).toBe(409); await page.screenshot({ path: info.outputPath('recommendations-policy-hidden-390.png') })
  134 |     } finally { release(); await page.unroute('**/api/v1/recommendations?*'); await other.close() }
  135 |     expect(errors).toEqual([])
  136 |     writeFileSync(info.outputPath('actual-recommendation-412-policy.json'), JSON.stringify({ scope: 'Original unreviewed assessment learnpack; offline POST aborted before server; actual concurrent decision and actual 412; explicit new command; unchanged actual GET body delayed until another page really starts an independent ungraded attempt.', original_recommendation: item, actual_commands: commands, rejected_original_revision: 1, concurrent_revision: 2, corrected_revision: 3, facts_unchanged_by_decisions: true, independent_mode_is_ungraded_not_expert_approved: true, stale_async_subject_sources_hidden: true, runtime_errors: errors }, null, 2))
  137 |   } finally { await runtime.close() }
  138 | })
  139 | 
  140 | test('a controlled archived fixture makes the real historical recommendation stale and its formerly current UI cannot open the old target', async ({ playwright }, info) => {
  141 |   const runtime = await RestartRuntime.start(), fixture = originalPracticePackage('recommendationarchivenative', 'learner')
  142 |   try {
  143 |     const browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]; await runtime.authenticateOnly(page)
  144 |     const imported = await importPracticePackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click(); await markRead(page, runtime, fixture.course, fixture.lesson)
  145 |     const item = (await readyRecommendations(page)).items.find(value => value.target_ref.id === fixture.practice.id && value.reason_codes.includes('read_without_practice'))!
  146 |     expect(item).toBeTruthy(); const dialog = await openRecommendations(page), row = dialog.locator(`[data-recommendation-id="${item.id}"]`), originalURL = page.url()
  147 |     const button = row.getByRole('button', { name: `从教材 ${fixture.course.id} · r${fixture.course.revision} / 小节 ${fixture.lesson.id} · r${fixture.lesson.revision} 打开练习`, exact: true })
  148 |     await expect(button).toBeEnabled(); await expect(row.getByRole('link')).toHaveCount(0)
  149 |     const sessionResponse = await page.request.get('/api/v1/session'); expect(sessionResponse.status()).toBe(200); const session: { workspace_id: string } = await sessionResponse.json()
  150 |     const assignment = archiveRecommendationFixture(runtime, session.workspace_id, item.target_ref)
  151 |     expect(assignment).toMatchObject({ exact_ref: item.target_ref, before_lifecycle: 'active', after_lifecycle: 'archived', changed_rows: 1 })
  152 |     // No UI refresh: this row still looks current until the actual navigation
  153 |     // guard re-reads its original historical ID through the real HTTP endpoint.
  154 |     const reading = page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).searchParams.get('recommendation_id') === item.id)
  155 |     await button.click(); const response = await reading; expect(response.status()).toBe(200); const historical: RecommendationPage = await response.json(); expect(historical.projection_state).toBe('stale'); expect(historical.items[0]).toMatchObject({ id: item.id, target_ref: item.target_ref, staleness: 'stale', decision: 'pending', decision_revision: 1 })
  156 |     await expect(dialog.getByRole('alert').filter({ hasText: '推荐依据已过期，请查看最新推荐' })).toBeVisible(); await expect(button).toBeDisabled(); await expect(row.getByRole('button', { name: '接受此建议', exact: true })).toBeDisabled(); expect(page.url()).toBe(originalURL); await expect(page.getByRole('dialog', { name: '学习建议', exact: true })).toBeVisible()
  157 |     await row.getByText('核对推荐原因与真实来源', { exact: true }).click(); await expect(row).toContainText(item.target_ref.sha256)
  158 |     await page.setViewportSize({ width: 390, height: 844 }); await dialog.getByRole('alert').filter({ hasText: '推荐依据已过期，请查看最新推荐' }).scrollIntoViewIfNeeded(); await expect(dialog.getByRole('button', { name: '关闭学习建议', exact: true })).toBeInViewport(); expect(await dialog.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('recommendation-stale-open-blocked-390.png') })
  159 |     writeFileSync(info.outputPath('actual-recommendation-stale-open.json'), JSON.stringify({ scope: 'Controlled exact-object lifecycle assignment in a private synthetic RestartRuntime; NOT an implemented native user archive action or HTTP archive feature. Actual historical GET, stale metadata, button disable and no navigation are the browser/API acceptance scope.', controlled_precondition: assignment, original_current_item: item, real_historical_page: historical, original_url: originalURL, final_url: page.url(), old_recommendation_open_blocked: true, historical_source_metadata_retained: true }, null, 2))
  160 |   } finally { await runtime.close() }
  161 | })
  162 | 
```