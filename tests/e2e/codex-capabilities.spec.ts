import { writeFileSync } from 'node:fs'
import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { role, screenshot } from './authoringTestData'

test('actual Codex capability read is explicit, scoped and restored through a new API process', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await RestartRuntime.start(), errors: string[] = [], calls: string[] = []
  const observe = (page: Page) => {
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => {
      const path = new URL(request.url()).pathname
      if (path.startsWith('/api/v1/codex/')) calls.push(`${request.method()} ${path}`)
    })
  }
  const read = async (page: Page) => {
    await page.getByRole('button', { name: '创作', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '创作', exact: true })
    const panel = dialog.getByRole('region', { name: 'Codex 连接状态', exact: true })
    await expect(panel.getByText('尚未检查 Codex 连接。', { exact: true })).toBeVisible()
    await expect(panel.getByRole('button', { name: '检查 Codex 连接', exact: true })).toBeEnabled()
    const before = calls.length
    const responding = page.waitForResponse(response => response.request().method() === 'GET' && response.url().endsWith('/api/v1/codex/capabilities'))
    await panel.getByRole('button', { name: '检查 Codex 连接', exact: true }).click()
    const response = await responding, status = response.status(), body = await response.json()
    expect(calls.length).toBe(before + 1)
    if (status === 200) {
      expect(Object.keys(body).sort()).toEqual(['adapter_version', 'authorized', 'available', 'capabilities', 'sandbox_roots'])
      expect(body.authorized).toBe(false) // A new isolated Broker has no inherited global credentials.
      expect(body.capabilities).toEqual({ approvals: false, interrupt: false, artifacts: false })
      if (body.available) {
        expect(body.adapter_version).toBe('codex-cli/0.160.0')
        expect(body.sandbox_roots).toEqual([{ id: 'workspace_default', label: '此工作区的隔离 Broker 目录' }])
        await expect(panel.getByText('未连接 Codex：此工作区的隔离 Broker 尚未授权。', { exact: true })).toBeVisible()
      } else {
        expect(body.adapter_version).toBeNull(); expect(body.sandbox_roots).toEqual([])
        await expect(panel.getByText('未连接 Codex：未发现可用的本机适配器。', { exact: true })).toBeVisible()
      }
    } else {
      // CI may have an unsupported CLI or unavailable control-probe isolation.
      // This branch verifies honest UI degradation, never real probe success.
      expect(status).toBe(503)
      expect(['CODEX_ADAPTER_UNSUPPORTED', 'CODEX_PROTOCOL_INVALID', 'CODEX_PROBE_TIMEOUT', 'CODEX_BROKER_CONFIG_CHANGED', 'CODEX_PROBE_UNAVAILABLE']).toContain(body.error.code)
      await expect(panel.getByText('暂时无法确认 Codex 连接状态，请重新检查。 当前状态未知。', { exact: true })).toBeVisible()
      await expect(panel.getByText(/隔离 Broker 尚未授权/)).toHaveCount(0)
    }
    return { dialog, panel, actual: { status, ...(status === 200 ? { capabilities: body } : { error_code: body.error.code }) } }
  }
  try {
    let context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; observe(page)
    await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author')
    const jobsBefore = await page.request.get('/api/v1/authoring/jobs').then(value => value.json())
    const first = await read(page)
    const wide = await screenshot(page, first.dialog, 1440, first.panel, 'codex-capabilities-1440.png', info)
    const narrow = await screenshot(page, first.dialog, 390, first.panel, 'codex-capabilities-390.png', info)
    const identity = runtime.databaseIdentity()
    await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
    expect(runtime.databaseIdentity()).toEqual(identity)
    context = await runtime.openBrowser(playwright.chromium); page = context.pages()[0]; observe(page)
    await page.goto(runtime.origin); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
    const second = await read(page)
    expect(second.actual).toEqual(first.actual)
    const jobsAfter = await page.request.get('/api/v1/authoring/jobs').then(value => value.json())
    expect(jobsAfter).toEqual(jobsBefore)
    expect(calls).toEqual(['GET /api/v1/codex/capabilities', 'GET /api/v1/codex/capabilities'])
    await role(page, runtime.origin, 'learner'); await page.getByRole('button', { name: '创作', exact: true }).click()
    const panel = page.getByRole('region', { name: 'Codex 连接状态', exact: true })
    await expect(panel.getByRole('button', { name: '检查 Codex 连接', exact: true })).toBeDisabled()
    await expect(panel.getByText('请在作者会话且测试策略允许后检查 Codex。', { exact: true })).toBeVisible()
    await expect(panel.getByText('codex-cli/0.160.0', { exact: true })).toHaveCount(0)
    expect(calls).toHaveLength(2); expect(errors).toEqual([])
    writeFileSync(info.outputPath('codex-capabilities-actual.json'), JSON.stringify({
      scope: 'Actual production HTTP, isolated workspace, browser and API restart. Explicit control reads only; no thread/turn/login/model/tool operation. Availability/error branch recorded rather than promoted to probe success.',
      first: first.actual, second: second.actual, requests: calls, api_processes: runtime.generations.length,
      same_database: true, authoring_jobs_unchanged: true, learner_read_disabled: true,
      viewport_bounds: { wide, narrow }, page_errors: errors,
    }, null, 2))
  } finally { await runtime.close() }
})
