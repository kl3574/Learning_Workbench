import { writeFileSync } from 'node:fs'
import { expect, type Locator, type Page, type TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AuthoringJobView, JobRef, NumericCheckView, ProviderConfigWrite, SessionResponse } from '../../packages/contracts/generated/api-types'
import { AuthoringRuntime } from './authoringRuntime'

const providerId = 'provider_authoring_native'
export async function role(page: Page, origin: string, value: 'author' | 'learner') {
  const session: SessionResponse = await page.request.get('/api/v1/session').then(v => v.json())
  const response = await page.request.post('/api/v1/session/role', { data: { role: value }, headers: { Origin: origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': `synthetic-authoring-role-${value}` } })
  expect(response.status()).toBe(200)
  // Only the real role endpoint changes permissions; reloading observes it.
  await page.reload()
  await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
}
export async function configure(page: Page, runtime: AuthoringRuntime) {
  const session: SessionResponse = await page.request.get('/api/v1/session').then(v => v.json())
  const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token }
  const control = runtime.control()
  const config: ProviderConfigWrite = { expected_revision: 0, adapter: control.adapter, base_url: control.base_url, model: control.model, embedding_model: null, endpoint_policy: 'explicit_loopback', pricing: null }
  expect((await page.request.put(`/api/v1/providers/${providerId}/config`, { data: config, headers: { ...headers, 'Idempotency-Key': 'synthetic-authoring-native-config' } })).status()).toBe(200)
  expect((await page.request.post(`/api/v1/providers/${providerId}/secret`, { data: { expected_revision: 1, secret: 'synthetic-authoring-native-constant-only' }, headers: { ...headers, 'Idempotency-Key': 'synthetic-authoring-native-secret' } })).status()).toBe(200)
}
export async function prepare(page: Page) {
  await page.getByRole('button', { name: '创作', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  await expect(dialog.getByLabel('例题主题', { exact: true })).toBeEnabled()
  await dialog.getByLabel('例题主题', { exact: true }).fill('原创合成双倍例题')
  await dialog.getByLabel('学习目标（每行一条，至少一条）', { exact: true }).fill('明确区分模型草稿、数值复算与数学审核。')
  await dialog.getByLabel('已配置的提供商 ID', { exact: true }).fill(providerId)
  const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/authoring/jobs'))
  await dialog.getByRole('button', { name: '明确准备本次例题任务', exact: true }).click()
  const accepted = await response; expect(accepted.status()).toBe(202)
  const ack: JobRef = await accepted.json()
  expect(ack.status).toBe('awaiting_approval')
  await dialog.getByRole('button', { name: `读取创作详情 ${ack.id}`, exact: true }).click()
  await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toBeVisible()
  const original: AuthoringJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json())
  expect(original.request.source_refs).toEqual([]); expect(original.preparation.materials).toEqual([])
  expect(original.consent_id).toBeNull(); expect(original.proposal_id).toBeNull(); expect(original.raw_answer).toBeNull()
  return { dialog, ack, original }
}
export async function preview(page: Page, dialog: Locator) {
  const panel = dialog.getByRole('region', { name: '准备授权预览', exact: true })
  await expect(panel.getByLabel('最大输入 token', { exact: true })).toBeEnabled()
  await panel.getByLabel('最大输入 token', { exact: true }).fill('20000')
  await panel.getByLabel('最大输出 token', { exact: true }).fill('5000')
  await panel.getByLabel('总超时秒数', { exact: true }).fill('10')
  await panel.getByLabel('到期时间 UTC', { exact: true }).fill(new Date(Date.now() + 300_000).toISOString())
  await panel.getByRole('button', { name: '准备服务端预览命令', exact: true }).click()
  const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/consents/preview'))
  await dialog.getByRole('button', { name: '确认发送授权预览', exact: true }).click()
  return response
}
export async function numericPreview(page: Page, dialog: Locator, draftId: string) {
  const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/drafts/${draftId}/numeric-checks`))
  await dialog.getByRole('button', { name: '明确准备独立数值检查预览', exact: true }).click()
  const accepted = await response; expect(accepted.status()).toBe(201)
  const value: NumericCheckView = await accepted.json()
  expect(value.decision).toBe('pending'); expect(value.job).toBeNull(); expect(value.result).toBeNull()
  await dialog.getByRole('button', { name: '刷新候选的检查记录', exact: true }).click()
  await dialog.getByRole('button', { name: `读取数值检查 ${value.id}`, exact: true }).click()
  await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toBeVisible()
  return value
}
export async function screenshot(page: Page, dialog: Locator, width: number, target: Locator, name: string, info: TestInfo) {
  await page.setViewportSize({ width, height: 900 })
  await target.scrollIntoViewIfNeeded()
  await expect(target).toBeVisible()
  const bounds = await dialog.evaluate(element => { const inner = element.querySelector('.dialog-inner')!; return { client: element.clientWidth, scroll: element.scrollWidth, inner_client: inner.clientWidth, inner_scroll: inner.scrollWidth, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, viewport: innerWidth, document: document.documentElement.scrollWidth } })
  writeFileSync(info.outputPath(name.replace('.png', '-geometry.json')), JSON.stringify(bounds, null, 2))
  await page.screenshot({ path: info.outputPath(name) })
  expect(bounds.inner_scroll).toBeLessThanOrEqual(bounds.inner_client + 1)
  expect(bounds.scroll).toBeLessThanOrEqual(bounds.client + 1)
  expect(bounds.left).toBeGreaterThanOrEqual(0); expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
  expect(bounds.document).toBeLessThanOrEqual(bounds.viewport)
  await page.screenshot({ path: info.outputPath(name) })
  return bounds
}

