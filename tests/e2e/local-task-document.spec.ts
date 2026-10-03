import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { SessionResponse } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { role, screenshot } from './authoringTestData'

// Real application and local browser download. No CLI/model control endpoint is
// called; the only explicit mutation after authentication is a role downgrade.
test('native offline task download contains four inputs, keeps the close guard and rejects revoked author access', async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author')
    await page.getByRole('button', { name: '创作', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '创作', exact: true })
    await expect(dialog.getByLabel('例题主题', { exact: true })).toBeEnabled()
    await dialog.getByLabel('例题主题', { exact: true }).fill('合成离线主题 α\n第二行')
    await dialog.getByLabel('已声明先修（每行一条）', { exact: true }).fill('线性代数\n  原空格')
    await dialog.getByLabel('学习目标（每行一条，至少一条）', { exact: true }).fill('保持完整证明\n明确边界')
    await dialog.getByLabel('已配置的提供商 ID', { exact: true }).fill('provider_omitted_synthetic')
    await dialog.getByText('明确加入其他准确内容块', { exact: true }).click()
    await dialog.getByLabel('内容块 ID', { exact: true }).fill('block_omitted_synthetic')
    await dialog.getByLabel('内容修订', { exact: true }).fill('3')
    await dialog.getByLabel('内容 SHA256', { exact: true }).fill('a'.repeat(64))
    await dialog.getByRole('button', { name: '加入这份准确引用', exact: true }).click()
    const button = dialog.getByRole('button', { name: '下载当前四项需求说明', exact: true })
    await expect(button).toBeEnabled()
    const calls: { method: string; path: string }[] = [], downloads: string[] = []
    page.on('request', request => { const path = new URL(request.url()).pathname; if (path.startsWith('/api/')) calls.push({ method: request.method(), path }) })
    page.on('download', download => downloads.push(download.suggestedFilename()))
    const downloaded = page.waitForEvent('download')
    await button.click(); const download = await downloaded
    expect(download.suggestedFilename()).toBe('learning-task.md'); expect(await download.failure()).toBeNull()
    const bytes = readFileSync((await download.path())!), text = bytes.toString('utf8')
    expect(text).toBe('# 离线创作需求说明\n\n未连接 Codex。本文件仅包含作者当前输入的四项需求，不含已选材料或其他任务设置；没有创建服务器任务、授权或生成结果。\n\n## 主题\n\n合成离线主题 α\n第二行\n\n## 已声明先修\n\n线性代数\n  原空格\n\n## 学习目标\n\n保持完整证明\n明确边界\n\n## 证明策略\n\nfull（完整证明）\n')
    writeFileSync(info.outputPath('offline-task-synthetic.md'), bytes)
    expect(text).not.toContain('provider_omitted_synthetic'); expect(text).not.toContain('block_omitted_synthetic'); expect(text).not.toContain('a'.repeat(64))
    await expect(dialog.getByText(/已交给浏览器下载；临时表单仍未保存到服务器/)).toBeVisible()
    const downloadCalls = [...calls]
    expect(downloadCalls).toEqual([{ method: 'GET', path: '/api/v1/session' }])
    await screenshot(page, dialog, 1440, button, 'offline-task-wide.png', info)
    await screenshot(page, dialog, 390, button, 'offline-task-narrow.png', info)
    await dialog.getByRole('button', { name: '关闭创作', exact: true }).click()
    const guard = page.getByRole('dialog', { name: '保留创作原命令', exact: true })
    await expect(guard).toBeVisible(); await guard.getByRole('button', { name: '返回创作', exact: true }).click()
    // React mirrors controlled textarea content into its implicit label DOM text;
    // use the unchanged exact accessible textbox name for filled-value readback.
    await expect(dialog.getByRole('textbox', { name: '例题主题', exact: true })).toHaveValue('合成离线主题 α\n第二行')
    // Change the real server role without a page reload/broadcast: the existing
    // visible button must independently recheck this new fact before download.
    const session: SessionResponse = await page.request.get('/api/v1/session').then(response => response.json())
    const downgraded = await page.request.post('/api/v1/session/role', { data: { role: 'learner' }, headers: {
      Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': 'synthetic-offline-downgrade',
    } })
    expect(downgraded.status()).toBe(200); expect((await downgraded.json()).role).toBe('learner')
    const checked = page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/v1/session')
    await button.click(); const denied = await checked
    expect(denied.status()).toBe(200); expect((await denied.json()).role).toBe('learner')
    await expect(dialog.getByRole('textbox', { name: '例题主题', exact: true })).toHaveCount(0)
    expect(downloads).toEqual(['learning-task.md'])
    expect(calls.filter(call => call.method !== 'GET')).toEqual([])
    writeFileSync(info.outputPath('offline-task-actual.json'), JSON.stringify({
      scope: 'Client-only four-field task document. Not a Codex generation, execution, task identity, artifact import or quality receipt.',
      suggested_filename: download.suggestedFilename(), bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'),
      exact_four_input_bytes: true, download_http: downloadCalls, explicit_role_downgrade_status: downgraded.status(),
      final_permission_read_status: denied.status(), downloads: downloads.length, mutations_from_page: calls.filter(call => call.method !== 'GET'),
      close_guard_seen: true, subject_form_hidden_after_revocation: true, codex_called: false,
    }, null, 2))
  } finally { await runtime.close() }
})
