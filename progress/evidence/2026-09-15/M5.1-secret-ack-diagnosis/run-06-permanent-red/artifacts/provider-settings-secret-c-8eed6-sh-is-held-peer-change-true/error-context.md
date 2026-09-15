# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: provider-settings.spec.ts >> secret controls use an actual newer readback while the parent refresh is held; peer change true
- Location: tests/e2e/provider-settings.spec.ts:142:41

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('dialog', { name: '设置', exact: true }).getByRole('region', { name: '秘密控制版本比较', exact: true })
Expected substring: "原始基准 r2；当前r3"
Received string:    "比较原基准与当前版本原始基准 r1；当前r3；本页候选为删除引用。采用当前版本，明确更正秘密命令"
Timeout: 5000ms

Call log:
  - Expect "toContainText" getByRole('dialog', { name: '设置', exact: true }).getByRole('region', { name: '秘密控制版本比较', exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '设置', exact: true }).getByRole('region', { name: '秘密控制版本比较', exact: true })
    13 × locator resolved to <section aria-label="秘密控制版本比较">…</section>
       - unexpected value "比较原基准与当前版本原始基准 r1；当前r3；本页候选为删除引用。采用当前版本，明确更正秘密命令"

```

```yaml
- region "秘密控制版本比较":
  - heading "比较原基准与当前版本" [level=4]
  - paragraph: 原始基准 r1；当前r3；本页候选为删除引用。
  - button "采用当前版本，明确更正秘密命令"
```

# Test source

```ts
  89  |     const dialog = await settings(page); await createConfig(page, dialog, id)
  90  |     await dialog.getByLabel('模型名称', { exact: true }).fill('synthetic-original-candidate')
  91  |     await dialog.getByRole('button', { name: '准备配置保存命令', exact: true }).click()
  92  |     await page.route(`**/api/v1/providers/${id}/config`, async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! }); const response = await route.fetch(); expect(response.status()).toBe(200); await route.abort('failed') })
  93  |     await dialog.getByRole('button', { name: '确认发送配置保存', exact: true }).click(); await expect(dialog.getByRole('alert').filter({ hasText: '命令尚未确认' })).toBeVisible()
  94  |     const applied: ProviderConfigView = await page.request.get(`/api/v1/providers/${id}/config`).then(response => response.json()); expect(applied.revision).toBe(2)
  95  |     const later: ProviderConfigWrite = { expected_revision: 2, adapter: applied.adapter, base_url: applied.base_url, model: 'synthetic-later-server-config', embedding_model: applied.embedding_model, endpoint_policy: applied.endpoint_policy, pricing: applied.pricing }
  96  |     const changed = await page.request.put(`/api/v1/providers/${id}/config`, { headers: await headers(page, runtime, 'native-provider-later-config'), data: later }); expect(changed.status()).toBe(200)
  97  |     await dialog.getByRole('button', { name: '关闭设置', exact: true }).click(); await page.getByRole('dialog', { name: '保留配置与授权候选', exact: true }).getByRole('button', { name: '明确丢弃临时输入，保留本机命令并关闭', exact: true }).click()
  98  |     const database = runtime.databaseIdentity(); await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed(); expect(runtime.databaseIdentity()).toEqual(database)
  99  |     const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; restored.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(restored)
  100 |     const panel = await settings(restored); await panel.getByRole('button', { name: '恢复原命令 1', exact: true }).click()
  101 |     const comparison = panel.getByRole('region', { name: '配置三方比较', exact: true }); await expect(comparison.getByRole('heading', { name: '原始基准 · r1', exact: true })).toBeVisible(); await expect(comparison.locator('article').nth(2)).toContainText('r3')
  102 |     await restored.route(`**/api/v1/providers/${id}/config`, async route => { if (route.request().method() === 'PUT') commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! }); await route.continue() })
  103 |     await panel.getByRole('button', { name: '重试原配置或授权命令', exact: true }).click(); await expect(panel.getByText('原命令已确认 · 修订 2。此回执保留当时事实，不替代当前状态。', { exact: true })).toBeVisible()
  104 |     await expect(comparison.locator('article').nth(2)).toContainText('synthetic-later-server-config'); expect(commands).toHaveLength(2); expect(commands[1]).toEqual(commands[0])
  105 |     const current: ProviderConfigView = await restored.request.get(`/api/v1/providers/${id}/config`).then(response => response.json()); expect(current.revision).toBe(3); expect(current.model).toBe(later.model)
  106 |     await restored.screenshot({ path: info.outputPath('provider-original-ack-1440.png') }); await restored.setViewportSize({ width: 390, height: 844 }); await comparison.scrollIntoViewIfNeeded(); await expect(panel.getByRole('button', { name: '关闭设置', exact: true })).toBeInViewport(); expect(await panel.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await restored.screenshot({ path: info.outputPath('provider-original-ack-390.png') })
  107 |     expect(errors).toEqual([])
  108 |     writeFileSync(info.outputPath('actual-provider-original-ack.json'), JSON.stringify({ scope: 'Actual successful config HTTP ACK deliberately lost; later independent command; real browser/API restart and same original-key replay. No provider dispatch.', actual_commands: commands, original_ack_revision: 2, current_config: current, database_identity_unchanged: true, runtime_errors: errors }, null, 2))
  109 |   } finally { await runtime.close() }
  110 | })
  111 | 
  112 | test('actual independent assessment policy keeps settings controls available and denies subject consent reads', async ({ playwright }, info) => {
  113 |   test.setTimeout(90_000)
  114 |   const runtime = await RestartRuntime.start(), id = 'provider_native_independent', errors: string[] = []
  115 |   try {
  116 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
  117 |     // A learner package intentionally omits the private reference bindings and
  118 |     // cannot start even an unscored attempt. The actual author import retains
  119 |     // unreviewed references; this helper explicitly switches back to learner.
  120 |     const fixture = originalAssessmentPackage('providerpolicynative', 'author'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  121 |     const identityResponse = await page.request.get('/api/v1/session'); expect(identityResponse.status()).toBe(200)
  122 |     const identity: SessionResponse = await identityResponse.json(); expect(identity.role).toBe('learner')
  123 |     await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  124 |     await page.getByRole('radio', { name: '独立测试', exact: true }).check()
  125 |     await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  126 |     const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/assessments/${fixture.assessment.id}/attempts`))
  127 |     await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  128 |     const created = await creating; expect(created.status()).toBe(201)
  129 |     const attempt: AttemptSnapshot = await created.json()
  130 |     expect(attempt.status).toBe('active'); expect(attempt.policy.mode).toBe('independent'); expect(attempt.grading_status).toBe('not_graded')
  131 |     expect(attempt.preflight.startable).toBe(true); expect(attempt.preflight.grading).toMatchObject({ status: 'unreviewed', approved_count: 0, needs_review_count: 5, missing_count: 0, damaged_count: 0 })
  132 |     await expect(page.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
  133 |     const dialog = await settings(page); await expect(dialog.getByRole('region', { name: '授权历史', exact: true })).toContainText('授权摘要隐藏')
  134 |     const rejected = await page.request.get('/api/v1/consents'); expect(rejected.status()).toBe(409)
  135 |     await createConfig(page, dialog, id); await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-independent-control-only'); await dialog.getByRole('button', { name: '保存秘密', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
  136 |     await dialog.getByRole('button', { name: '删除秘密引用', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
  137 |     await expect(dialog.getByRole('region', { name: '冻结外发摘要', exact: true })).toHaveCount(0); expect(errors).toEqual([])
  138 |     writeFileSync(info.outputPath('actual-provider-independent-controls.json'), JSON.stringify({ scope: 'Real author package import with unreviewed reference bindings, explicit return to learner role, and actual independent unscored attempt; actual config and secret controls remain available while subject consent GET is denied. No injected consent, generation job, score, proof or provider dispatch.', authenticated_role: identity.role, attempt_id: attempt.id, attempt_status: attempt.status, attempt_policy: attempt.policy, grading_status: attempt.grading_status, preflight: attempt.preflight, consent_read_status: rejected.status(), config_revision_after_secret_delete: 3, subject_summary_visible: false, runtime_errors: errors }, null, 2))
  139 |   } finally { await runtime.close() }
  140 | })
  141 | 
  142 | for (const peerChange of [false, true]) test(`secret controls use an actual newer readback while the parent refresh is held; peer change ${peerChange}`, async ({ playwright }, info) => {
  143 |   const runtime = await RestartRuntime.start(), id = 'provider_native_secret_basis'
  144 |   let releaseParent!: () => void
  145 |   let cleanupRoutes = async () => {}
  146 |   const parentGate = new Promise<void>(resolve => { releaseParent = resolve })
  147 |   try {
  148 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  149 |     cleanupRoutes = () => page.unrouteAll({ behavior: 'wait' })
  150 |     await runtime.authenticateOnly(page)
  151 |     const dialog = await settings(page), initial = await createConfig(page, dialog, id)
  152 |     let armed = false, reads = 0, parentHeld!: () => void
  153 |     const held = new Promise<void>(resolve => { parentHeld = resolve })
  154 |     const deletes: { sha: string; key: string; status: number }[] = []
  155 |     await page.route(`**/api/v1/providers/${id}/secret`, async route => {
  156 |       const response = await route.fetch()
  157 |       if (route.request().method() === 'POST') { expect(response.status()).toBe(200); armed = true }
  158 |       if (route.request().method() === 'DELETE') {
  159 |         deletes.push({ sha: route.request().headers()['if-match'], key: route.request().headers()['idempotency-key'], status: response.status() })
  160 |         releaseParent()
  161 |       }
  162 |       await route.fulfill({ response })
  163 |     })
  164 |     await page.route(`**/api/v1/providers/${id}/config`, async route => {
  165 |       if (route.request().method() !== 'GET' || !armed) { await route.continue(); return }
  166 |       const ordinal = ++reads, response = await route.fetch()
  167 |       if (ordinal === 2) {
  168 |         expect(response.status()).toBe(200)
  169 |         const value: ProviderConfigView = await response.json(); expect(value.revision).toBe(2)
  170 |         parentHeld(); await parentGate
  171 |       }
  172 |       await route.fulfill({ response })
  173 |     })
  174 |     await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-held-parent-secret-only')
  175 |     await dialog.getByRole('button', { name: '保存秘密', exact: true }).click()
  176 |     await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
  177 |     await held
  178 |     await expect(dialog.getByText('另行回读当前配置：r2 · 有秘密引用。', { exact: true })).toBeVisible()
  179 |     await expect(dialog.getByText(`提供商 ${id}：当前读回 r1，无秘密引用`, { exact: true })).toBeVisible()
  180 |     const readbackResponse = await page.request.get(`/api/v1/providers/${id}/config`); expect(readbackResponse.status()).toBe(200)
  181 |     const readback: ProviderConfigView = await readbackResponse.json(); expect(readback.revision).toBe(2)
  182 |     if (peerChange) {
  183 |       const body: ProviderConfigWrite = { expected_revision: 2, adapter: readback.adapter, base_url: readback.base_url, model: 'synthetic-real-peer-config', embedding_model: readback.embedding_model, endpoint_policy: readback.endpoint_policy, pricing: readback.pricing }
  184 |       const response = await page.request.put(`/api/v1/providers/${id}/config`, { headers: await headers(page, runtime, 'native-secret-peer-config'), data: body }); expect(response.status()).toBe(200)
  185 |     }
  186 |     await dialog.getByRole('button', { name: '删除秘密引用', exact: true }).click()
  187 |     if (peerChange) {
  188 |       const comparison = dialog.getByRole('region', { name: '秘密控制版本比较', exact: true })
> 189 |       await expect(comparison).toContainText('原始基准 r2；当前r3')
      |                                ^ Error: expect(locator).toContainText(expected) failed
  190 |       expect(deletes).toHaveLength(1); expect(deletes[0].status).toBe(412)
  191 |       await comparison.getByRole('button', { name: '采用当前版本，明确更正秘密命令', exact: true }).click()
  192 |       await dialog.getByRole('button', { name: '重试原删除引用命令', exact: true }).click()
  193 |       await expect(dialog.getByText('原秘密命令已确认 · r4 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
  194 |       expect(deletes).toHaveLength(2); expect(deletes[1].status).toBe(200); expect(deletes[1].key).not.toBe(deletes[0].key)
  195 |     } else {
  196 |       await expect(dialog.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
  197 |       await expect(dialog.getByRole('region', { name: '秘密控制版本比较', exact: true })).toHaveCount(0)
  198 |       expect(deletes).toHaveLength(1); expect(deletes[0].status).toBe(200)
  199 |     }
  200 |     expect(deletes[0].sha).toBe(`"${readback.config_sha256}"`); expect(deletes[0].sha).not.toBe(`"${initial.config_sha256}"`)
  201 |     const finalResponse = await page.request.get(`/api/v1/providers/${id}/config`); expect(finalResponse.status()).toBe(200)
  202 |     const final: ProviderConfigView = await finalResponse.json(); expect(final.revision).toBe(peerChange ? 4 : 3); expect(final.secret_present).toBe(false)
  203 |     writeFileSync(info.outputPath('actual-secret-readback-basis.json'), JSON.stringify({ scope: 'Actual local synthetic secret/config requests; only the second real config GET after the POST is held. No forged response or production provider request.', peer_change: peerChange, parent_revision_when_held: 1, actual_hook_readback_revision: 2, first_delete_uses_actual_readback_hash: true, delete_statuses: deletes.map(value => value.status), explicit_correction: peerChange, final_revision: final.revision, final_secret_present: final.secret_present }, null, 2))
  204 |   } finally { releaseParent(); await cleanupRoutes(); await runtime.close() }
  205 | })
  206 | 
```