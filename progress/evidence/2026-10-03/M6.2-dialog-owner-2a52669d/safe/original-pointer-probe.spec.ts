import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { publishEditedBlock } from './contentImpactsData'

for (const mode of ['stationary control', 'access refresh', 'release outside']) test(`impact dialog pointer ${mode}`, async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start()
  let release = () => {}
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    await publishEditedBlock(page, runtime)
    await page.getByRole('button', { name: '创作', exact: true }).click()
    await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click()
    const panel = page.getByRole('region', { name: '内容变更影响复核', exact: true })
    await panel.getByRole('button', { name: '从第一页读取内容变更', exact: true }).click()
    const button = panel.getByRole('button', { name: /^查看影响详情 / }).first()
    await expect(button).toBeVisible()
    const controls = await context.newPage(); await controls.goto(runtime.origin)
    await controls.getByRole('button', { name: '导入', exact: true }).first().click()
    await expect(controls.getByRole('button', { name: '切换为学习者角色', exact: true })).toBeEnabled()
    // Only categories and counts are observed. No text, request headers, IDs, or payloads.
    await page.evaluate(() => {
      const records: unknown[] = []; Object.assign(window, { pointerRecords: records })
      const category = (target: EventTarget | null) => target instanceof Element ? target.matches('dialog') ? 'dialog' : target.matches('button') ? 'button' : target.tagName.toLowerCase() : 'other'
      for (const type of ['pointerdown', 'pointerup', 'click', 'cancel', 'close']) document.addEventListener(type, event => records.push({ at: performance.now(), type, target: category(event.target), dialog: document.querySelectorAll('dialog[aria-label="创作"]').length }), true)
      new MutationObserver(() => records.push({ at: performance.now(), type: 'dom', dialog: document.querySelectorAll('dialog[aria-label="创作"]').length, panel: document.querySelectorAll('.content-impacts').length })).observe(document.body, { childList: true, subtree: true })
    })
    await button.scrollIntoViewIfNeeded(); const box = (await button.boundingBox())!
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down()
    if (mode === 'access refresh') {
      const held = new Promise<void>(resolve => { release = resolve })
      await page.route('**/api/v1/session', async route => { await held; await route.continue() })
      const response = controls.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/session/role')
      await controls.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
      expect((await response).status()).toBe(200)
      await expect(button).toHaveCount(0)
      release()
      await expect(panel.getByRole('button', { name: '重新核验内容复核权限', exact: true })).toBeEnabled()
    }
    if (mode === 'release outside') await page.mouse.move(2, 2)
    await page.mouse.up()
    try { await expect(page.getByRole('dialog', { name: '创作', exact: true })).toBeVisible() }
    finally { writeFileSync(info.outputPath('pointer-metadata.json'), JSON.stringify(await page.evaluate(() => (window as unknown as { pointerRecords: unknown[] }).pointerRecords), null, 2)) }
    release()
  } finally { release(); await runtime.close() }
})
