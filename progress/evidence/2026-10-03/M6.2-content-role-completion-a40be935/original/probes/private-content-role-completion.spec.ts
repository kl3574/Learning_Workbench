import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { publishEditedBlock } from './contentImpactsData'
for (const late of [false, true]) test(`Content detail role completion ${late ? 'after read' : 'before read control'}`, async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), events: unknown[] = []
  let release = () => {}; let snapshot: (() => Promise<unknown>) | undefined
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page); await publishEditedBlock(page, runtime)
    await page.getByRole('button', { name: '创作', exact: true }).click(); await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click()
    const panel = page.getByRole('region', { name: '内容变更影响复核', exact: true }), detail = panel.getByRole('region', { name: '本次读取的内容影响详情', exact: true })
    snapshot = async () => ({ page: 'subject', dialog: await page.locator('dialog[aria-label="创作"]').count(), open: await page.locator('dialog[aria-label="创作"][open]').count(), panel: await panel.count(), detail: await detail.count() })
    const controls = await context.newPage(); await controls.goto(runtime.origin); await controls.getByRole('button', { name: '导入', exact: true }).first().click()
    await controls.getByRole('button', { name: '切换为学习者角色', exact: true }).click(); await expect(controls.getByText('操作角色：学习者', { exact: true })).toBeVisible()
    let committed = () => {}; const committedPromise = new Promise<void>(r => { committed = r }), held = new Promise<void>(r => { release = r })
    await controls.route('**/api/v1/session/role', async route => { const response = await route.fetch(); expect(response.status()).toBe(200); events.push({ at: Date.now(), type: 'role-server-committed', role: (await response.json()).role }); committed(); await held; await route.fulfill({ response }); events.push({ at: Date.now(), type: 'role-response-released' }) })
    const completion = controls.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/session/role')
    await controls.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await committedPromise
    await controls.getByRole('button', { name: '关闭导入', exact: true }).click()
    if (!late) { release(); await completion }
    await panel.getByRole('button', { name: '重新核验内容复核权限', exact: true }).click()
    await panel.getByLabel('按原变更对象标识筛选（留空查看全部）', { exact: true }).fill('')
    await panel.getByLabel('每页事件数', { exact: true }).fill('20')
    const listed = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === '/api/v1/content/impacts')
    await panel.getByRole('button', { name: '从第一页读取内容变更', exact: true }).click(); expect((await listed).status()).toBe(200)
    await panel.getByRole('button', { name: /^查看影响详情 / }).first().click(); await expect(detail).toBeVisible()
    events.push({ at: Date.now(), type: 'before-late-release', ...(await snapshot() as object) })
    if (late) { release(); await completion; await expect(detail).toHaveCount(0) }
    try { await expect(detail).toBeVisible() }
    catch (error) { events.push({ at: Date.now(), type: 'assertion-failed', ...(await snapshot() as object) }); throw error }
  } finally {
    events.push({ at: Date.now(), type: 'finally-enter', ...(snapshot ? await snapshot() as object : {}) }); release()
    writeFileSync(info.outputPath('safe-role-timeline.json'), JSON.stringify(events, null, 2))
    await runtime.close()
  }
})
