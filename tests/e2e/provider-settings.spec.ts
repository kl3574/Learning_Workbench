import { expect, test, type Locator, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { AttemptSnapshot, ProviderCapabilitiesResponse, ProviderConfigView, ProviderConfigWrite, SessionResponse } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'

async function settings(page: Page) {
  await page.getByRole('button', { name: '设置', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '设置', exact: true })
  await expect(dialog.getByRole('region', { name: '提供商与授权设置', exact: true })).toBeVisible()
  await expect(dialog.getByText('无秘密候选已安全保留在本机', { exact: true })).toBeVisible()
  return dialog
}
async function createConfig(page: Page, dialog: Locator, id: string) {
  await dialog.getByLabel('提供商标识', { exact: true }).fill(id)
  await dialog.getByRole('button', { name: '读取或准备新配置', exact: true }).click()
  await expect(dialog.getByLabel('模型名称', { exact: true })).toBeEnabled()
  await dialog.getByLabel('服务地址', { exact: true }).fill('https://example.invalid/v1')
  await dialog.getByLabel('模型名称', { exact: true }).fill('synthetic-unregistered-native-model')
  await dialog.getByRole('button', { name: '准备配置保存命令', exact: true }).click()
  await expect(dialog.getByRole('button', { name: '确认发送配置保存', exact: true })).toBeEnabled()
  const saved = page.waitForResponse(value => value.request().method() === 'PUT' && value.url().endsWith(`/providers/${id}/config`))
  await dialog.getByRole('button', { name: '确认发送配置保存', exact: true }).click(); expect((await saved).status()).toBe(200)
  await expect(dialog.getByText('原命令已确认 · 修订 1。此回执保留当时事实，不替代当前状态。', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('模型名称', { exact: true })).toHaveValue('synthetic-unregistered-native-model')
  await expect(dialog.getByText(`提供商 ${id}：当前读回 r1，无秘密引用`, { exact: true })).toBeVisible()
  const response = await page.request.get(`/api/v1/providers/${id}/config`); expect(response.status()).toBe(200)
  const value: ProviderConfigView = await response.json(); expect(value.revision).toBe(1); expect(value.secret_present).toBe(false)
  return value
}
async function headers(page: Page, runtime: RestartRuntime, key: string) {
  const response = await page.request.get('/api/v1/session'); expect(response.status()).toBe(200)
  const session: { csrf_token: string } = await response.json()
  return { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': key }
}
async function browserRetainsSecret(page: Page, secret: string) {
  return page.evaluate(async needle => {
    for (const storage of [localStorage, sessionStorage]) for (let index = 0; index < storage.length; index++) if ((storage.getItem(storage.key(index)!) ?? '').includes(needle)) return true
    for (const entry of await indexedDB.databases()) {
      if (!entry.name) continue
      const db = await new Promise<IDBDatabase>((accept, reject) => { const open = indexedDB.open(entry.name!); open.onsuccess = () => accept(open.result); open.onerror = () => reject(open.error) })
      try {
        for (const name of Array.from(db.objectStoreNames)) {
          const values = await new Promise<unknown[]>((accept, reject) => { const read = db.transaction(name, 'readonly').objectStore(name).getAll(); read.onsuccess = () => accept(read.result); read.onerror = () => reject(read.error) })
          if (JSON.stringify(values).includes(needle)) return true
        }
      } finally { db.close() }
    }
    return false
  }, secret)
}

test('real settings persist control configuration and temporary secrets without claiming production generation', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await RestartRuntime.start(), id = 'provider_native_control', secret = 'synthetic-native-provider-control-only', errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
    const dialog = await settings(page); await expect(dialog.getByText('本工作区尚无提供商配置。', { exact: true })).toBeVisible()
    await expect(dialog.getByRole('region', { name: '授权任务', exact: true })).toContainText('本阶段尚无可发起授权的生成任务')
    const before = await createConfig(page, dialog, id)
    await expect(dialog.getByLabel('新秘密', { exact: true })).toBeEnabled(); await dialog.getByLabel('新秘密', { exact: true }).fill(secret)
    expect(await browserRetainsSecret(page, secret)).toBe(false)
    await page.keyboard.press('Control+Shift+P')
    const closing = page.getByRole('dialog', { name: '保留配置与授权候选', exact: true }); await expect(closing).toBeVisible(); await expect(page.getByRole('dialog', { name: '命令面板', exact: true })).toHaveCount(0)
    await closing.getByRole('button', { name: '返回设置', exact: true }).click(); await expect(dialog.getByLabel('新秘密', { exact: true })).toHaveValue(secret)
    const secretSaved = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/providers/${id}/secret`))
    await dialog.getByRole('button', { name: '保存秘密', exact: true }).click(); expect((await secretSaved).status()).toBe(200)
    await expect(dialog.getByLabel('新秘密', { exact: true })).toHaveValue(''); await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
    const current: ProviderConfigView = await page.request.get(`/api/v1/providers/${id}/config`).then(value => value.json()); expect(current.revision).toBe(2); expect(current.secret_present).toBe(true)
    const capabilities: ProviderCapabilitiesResponse = await page.request.get('/api/v1/providers/capabilities').then(value => value.json()); expect(capabilities.items.find(value => value.provider_id === id)).toMatchObject({ configured: true, chat: false, streaming: false, web_search: false, tool_calls: false, structured_output: false })
    expect(await browserRetainsSecret(page, secret)).toBe(false); expect(JSON.stringify(current)).not.toContain(secret)
    await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-discard-before-reload')
    await dialog.getByRole('button', { name: '关闭设置', exact: true }).click(); await closing.getByRole('button', { name: '明确丢弃临时输入，保留本机命令并关闭', exact: true }).click()
    await page.reload(); const reopened = await settings(page); await reopened.getByRole('button', { name: id, exact: true }).click(); await expect(reopened.getByLabel('新秘密', { exact: true })).toHaveValue('')
    const deleting = page.waitForResponse(value => value.request().method() === 'DELETE' && value.url().endsWith(`/providers/${id}/secret`))
    await reopened.getByRole('button', { name: '删除秘密引用', exact: true }).click(); expect((await deleting).status()).toBe(200)
    await expect(reopened.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
    await page.screenshot({ path: info.outputPath('provider-controls-1440.png') }); await page.setViewportSize({ width: 390, height: 844 }); await reopened.getByRole('region', { name: '秘密控制', exact: true }).scrollIntoViewIfNeeded(); await expect(reopened.getByRole('button', { name: '关闭设置', exact: true })).toBeInViewport(); expect(await reopened.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await page.screenshot({ path: info.outputPath('provider-controls-390.png') })
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-provider-controls.json'), JSON.stringify({ scope: 'Actual local configuration/secret routes and browser persistence inventory; synthetic secret only. Production registry has no source or accepted model proof. No actual paid provider dispatch or model quality claim.', initial_config: before, secret_reference_config: current, capability_readback: capabilities, secret_absent_from_browser_persistence: true, temporary_input_does_not_restore: true, explicit_secret_delete_revision: 3, runtime_errors: errors }, null, 2))
  } finally { await runtime.close() }
})

test('real config lost ACK restores the original command after browser/API restart and reads later current state separately', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await RestartRuntime.start(), id = 'provider_native_recovery', commands: { key: string; body: string }[] = [], errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
    const dialog = await settings(page); await createConfig(page, dialog, id)
    await dialog.getByLabel('模型名称', { exact: true }).fill('synthetic-original-candidate')
    await dialog.getByRole('button', { name: '准备配置保存命令', exact: true }).click()
    await page.route(`**/api/v1/providers/${id}/config`, async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! }); const response = await route.fetch(); expect(response.status()).toBe(200); await route.abort('failed') })
    await dialog.getByRole('button', { name: '确认发送配置保存', exact: true }).click(); await expect(dialog.getByRole('alert').filter({ hasText: '命令尚未确认' })).toBeVisible()
    const applied: ProviderConfigView = await page.request.get(`/api/v1/providers/${id}/config`).then(response => response.json()); expect(applied.revision).toBe(2)
    const later: ProviderConfigWrite = { expected_revision: 2, adapter: applied.adapter, base_url: applied.base_url, model: 'synthetic-later-server-config', embedding_model: applied.embedding_model, endpoint_policy: applied.endpoint_policy, pricing: applied.pricing }
    const changed = await page.request.put(`/api/v1/providers/${id}/config`, { headers: await headers(page, runtime, 'native-provider-later-config'), data: later }); expect(changed.status()).toBe(200)
    await dialog.getByRole('button', { name: '关闭设置', exact: true }).click(); await page.getByRole('dialog', { name: '保留配置与授权候选', exact: true }).getByRole('button', { name: '明确丢弃临时输入，保留本机命令并关闭', exact: true }).click()
    const database = runtime.databaseIdentity(); await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed(); expect(runtime.databaseIdentity()).toEqual(database)
    const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; restored.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(restored)
    const panel = await settings(restored); await panel.getByRole('button', { name: '恢复原命令 1', exact: true }).click()
    const comparison = panel.getByRole('region', { name: '配置三方比较', exact: true }); await expect(comparison.getByRole('heading', { name: '原始基准 · r1', exact: true })).toBeVisible(); await expect(comparison.locator('article').nth(2)).toContainText('r3')
    await restored.route(`**/api/v1/providers/${id}/config`, async route => { if (route.request().method() === 'PUT') commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData()! }); await route.continue() })
    await panel.getByRole('button', { name: '重试原配置或授权命令', exact: true }).click(); await expect(panel.getByText('原命令已确认 · 修订 2。此回执保留当时事实，不替代当前状态。', { exact: true })).toBeVisible()
    await expect(comparison.locator('article').nth(2)).toContainText('synthetic-later-server-config'); expect(commands).toHaveLength(2); expect(commands[1]).toEqual(commands[0])
    const current: ProviderConfigView = await restored.request.get(`/api/v1/providers/${id}/config`).then(response => response.json()); expect(current.revision).toBe(3); expect(current.model).toBe(later.model)
    await restored.screenshot({ path: info.outputPath('provider-original-ack-1440.png') }); await restored.setViewportSize({ width: 390, height: 844 }); await comparison.scrollIntoViewIfNeeded(); await expect(panel.getByRole('button', { name: '关闭设置', exact: true })).toBeInViewport(); expect(await panel.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1); await restored.screenshot({ path: info.outputPath('provider-original-ack-390.png') })
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-provider-original-ack.json'), JSON.stringify({ scope: 'Actual successful config HTTP ACK deliberately lost; later independent command; real browser/API restart and same original-key replay. No provider dispatch.', actual_commands: commands, original_ack_revision: 2, current_config: current, database_identity_unchanged: true, runtime_errors: errors }, null, 2))
  } finally { await runtime.close() }
})

test('actual independent assessment policy keeps settings controls available and denies subject consent reads', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await RestartRuntime.start(), id = 'provider_native_independent', errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
    // A learner package intentionally omits the private reference bindings and
    // cannot start even an unscored attempt. The actual author import retains
    // unreviewed references; this helper explicitly switches back to learner.
    const fixture = originalAssessmentPackage('providerpolicynative', 'author'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const identityResponse = await page.request.get('/api/v1/session'); expect(identityResponse.status()).toBe(200)
    const identity: SessionResponse = await identityResponse.json(); expect(identity.role).toBe('learner')
    await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    await page.getByRole('radio', { name: '独立测试', exact: true }).check()
    await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/assessments/${fixture.assessment.id}/attempts`))
    await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
    const created = await creating; expect(created.status()).toBe(201)
    const attempt: AttemptSnapshot = await created.json()
    expect(attempt.status).toBe('active'); expect(attempt.policy.mode).toBe('independent'); expect(attempt.grading_status).toBe('not_graded')
    expect(attempt.preflight.startable).toBe(true); expect(attempt.preflight.grading).toMatchObject({ status: 'unreviewed', approved_count: 0, needs_review_count: 5, missing_count: 0, damaged_count: 0 })
    await expect(page.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
    const dialog = await settings(page); await expect(dialog.getByRole('region', { name: '授权历史', exact: true })).toContainText('授权摘要隐藏')
    const rejected = await page.request.get('/api/v1/consents'); expect(rejected.status()).toBe(409)
    await createConfig(page, dialog, id); await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-independent-control-only'); await dialog.getByRole('button', { name: '保存秘密', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
    await dialog.getByRole('button', { name: '删除秘密引用', exact: true }).click(); await expect(dialog.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
    await expect(dialog.getByRole('region', { name: '冻结外发摘要', exact: true })).toHaveCount(0); expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-provider-independent-controls.json'), JSON.stringify({ scope: 'Real author package import with unreviewed reference bindings, explicit return to learner role, and actual independent unscored attempt; actual config and secret controls remain available while subject consent GET is denied. No injected consent, generation job, score, proof or provider dispatch.', authenticated_role: identity.role, attempt_id: attempt.id, attempt_status: attempt.status, attempt_policy: attempt.policy, grading_status: attempt.grading_status, preflight: attempt.preflight, consent_read_status: rejected.status(), config_revision_after_secret_delete: 3, subject_summary_visible: false, runtime_errors: errors }, null, 2))
  } finally { await runtime.close() }
})

for (const peerChange of [false, true]) test(`secret controls use an actual newer readback while the parent refresh is held; peer change ${peerChange}`, async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start(), id = 'provider_native_secret_basis'
  let releaseParent!: () => void
  let cleanupRoutes = async () => {}
  const parentGate = new Promise<void>(resolve => { releaseParent = resolve })
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    cleanupRoutes = () => page.unrouteAll({ behavior: 'wait' })
    await runtime.authenticateOnly(page)
    const dialog = await settings(page), initial = await createConfig(page, dialog, id)
    let armed = false, reads = 0, parentHeld!: () => void
    const held = new Promise<void>(resolve => { parentHeld = resolve })
    const deletes: { sha: string; key: string; status: number }[] = []
    await page.route(`**/api/v1/providers/${id}/secret`, async route => {
      const response = await route.fetch()
      if (route.request().method() === 'POST') { expect(response.status()).toBe(200); armed = true }
      if (route.request().method() === 'DELETE') {
        deletes.push({ sha: route.request().headers()['if-match'], key: route.request().headers()['idempotency-key'], status: response.status() })
        releaseParent()
      }
      await route.fulfill({ response })
    })
    await page.route(`**/api/v1/providers/${id}/config`, async route => {
      if (route.request().method() !== 'GET' || !armed) { await route.continue(); return }
      const ordinal = ++reads, response = await route.fetch()
      if (ordinal === 2) {
        expect(response.status()).toBe(200)
        const value: ProviderConfigView = await response.json(); expect(value.revision).toBe(2)
        parentHeld(); await parentGate
      }
      await route.fulfill({ response })
    })
    await dialog.getByLabel('新秘密', { exact: true }).fill('synthetic-held-parent-secret-only')
    await dialog.getByRole('button', { name: '保存秘密', exact: true }).click()
    await expect(dialog.getByText('原秘密命令已确认 · r2 · 当时有引用。当前状态另行回读。', { exact: true })).toBeVisible()
    await held
    await expect(dialog.getByText('最近实际读回的配置：r2 · 有秘密引用。', { exact: true })).toBeVisible()
    await expect(dialog.getByText(`提供商 ${id}：当前读回 r1，无秘密引用`, { exact: true })).toBeVisible()
    const readbackResponse = await page.request.get(`/api/v1/providers/${id}/config`); expect(readbackResponse.status()).toBe(200)
    const readback: ProviderConfigView = await readbackResponse.json(); expect(readback.revision).toBe(2)
    if (peerChange) {
      const body: ProviderConfigWrite = { expected_revision: 2, adapter: readback.adapter, base_url: readback.base_url, model: 'synthetic-real-peer-config', embedding_model: readback.embedding_model, endpoint_policy: readback.endpoint_policy, pricing: readback.pricing }
      const response = await page.request.put(`/api/v1/providers/${id}/config`, { headers: await headers(page, runtime, 'native-secret-peer-config'), data: body }); expect(response.status()).toBe(200)
    }
    await dialog.getByRole('button', { name: '删除秘密引用', exact: true }).click()
    if (peerChange) {
      const comparison = dialog.getByRole('region', { name: '秘密控制版本比较', exact: true })
      await expect(comparison).toContainText('原始基准 r2；当前r3')
      expect(deletes).toHaveLength(1); expect(deletes[0].status).toBe(412)
      await comparison.getByRole('button', { name: '采用当前版本，明确更正秘密命令', exact: true }).click()
      await dialog.getByRole('button', { name: '重试原删除引用命令', exact: true }).click()
      await expect(dialog.getByText('原秘密命令已确认 · r4 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
      expect(deletes).toHaveLength(2); expect(deletes[1].status).toBe(200); expect(deletes[1].key).not.toBe(deletes[0].key)
    } else {
      await expect(dialog.getByText('原秘密命令已确认 · r3 · 当时无引用。当前状态另行回读。', { exact: true })).toBeVisible()
      await expect(dialog.getByRole('region', { name: '秘密控制版本比较', exact: true })).toHaveCount(0)
      expect(deletes).toHaveLength(1); expect(deletes[0].status).toBe(200)
    }
    expect(deletes[0].sha).toBe(`"${readback.config_sha256}"`); expect(deletes[0].sha).not.toBe(`"${initial.config_sha256}"`)
    const finalResponse = await page.request.get(`/api/v1/providers/${id}/config`); expect(finalResponse.status()).toBe(200)
    const final: ProviderConfigView = await finalResponse.json(); expect(final.revision).toBe(peerChange ? 4 : 3); expect(final.secret_present).toBe(false)
    writeFileSync(info.outputPath('actual-secret-readback-basis.json'), JSON.stringify({ scope: 'Actual local synthetic secret/config requests; only the second real config GET after the POST is held. No forged response or production provider request.', peer_change: peerChange, parent_revision_when_held: 1, actual_hook_readback_revision: 2, first_delete_uses_actual_readback_hash: true, delete_statuses: deletes.map(value => value.status), explicit_correction: peerChange, final_revision: final.revision, final_secret_present: final.secret_present }, null, 2))
  } finally { releaseParent(); await cleanupRoutes(); await runtime.close() }
})
