import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { publishEditedBlock } from './contentImpactsData'

test('native rendered Content form is guarded before passive state propagation', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    const publication = await publishEditedBlock(page, runtime), target = publication.fixture.lessons[0]
    let decisions = 0
    page.on('request', request => { if (request.method() === 'POST' && /\/content\/impacts\/[^/]+\/decisions$/.test(new URL(request.url()).pathname)) decisions++ })
    const open = async () => { await page.getByRole('button', { name: '创作', exact: true }).click(); await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click() }
    await open()
    const panel = page.getByRole('region', { name: '内容变更影响复核', exact: true })
    await panel.getByRole('button', { name: '从第一页读取内容变更', exact: true }).click()
    await panel.getByRole('button', { name: /^查看影响详情 / }).first().click()
    await panel.getByRole('button', { name: `读取对象当前依据 ${target.id}`, exact: true }).click()
    await expect(panel.getByRole('button', { name: '采用本次对象依据准备决定', exact: true })).toBeEnabled()
    // The browser performs the real adopt first. A one-shot DOM observer invokes
    // the real close button as soon as the actual form is connected, before the
    // child-to-parent passive effect chain can be treated as a safety boundary.
    // This is a controlled programmatic DOM click, not a trusted pointer claim.
    await page.evaluate(() => {
      const state = { form_connected: false, close_clicks: 0, close_found: false }
      Object.assign(window, { renderedFormGuard: state })
      const observer = new MutationObserver(() => {
        const form = document.querySelector('[aria-label="本次人工内容决定"]')
        if (!form?.isConnected) return
        observer.disconnect()
        const close = document.querySelector<HTMLButtonElement>('dialog[aria-label="创作"] button[aria-label="关闭创作"]')
        state.form_connected = true; state.close_found = !!close
        if (close) { state.close_clicks++; close.click() }
      })
      observer.observe(document.body, { childList: true, subtree: true })
    })
    await panel.getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click()
    const observed = await page.evaluate(() => (window as unknown as { renderedFormGuard: { form_connected: boolean; close_clicks: number; close_found: boolean } }).renderedFormGuard)
    expect(observed).toEqual({ form_connected: true, close_clicks: 1, close_found: true })
    const guard = page.getByRole('dialog', { name: '保留创作原命令', exact: true })
    try { await expect(guard).toBeVisible() }
    finally { writeFileSync(info.outputPath('rendered-form-guard.json'), JSON.stringify({ scope: 'Synthetic actual API/React form and native DOM; one programmatic close click at real form insertion, zero scheduling changes or sleeps.', observed, decision_posts: decisions }, null, 2)) }
    await guard.getByRole('button', { name: '返回创作', exact: true }).click()
    const form = panel.getByRole('group', { name: '本次人工内容决定', exact: true })
    await expect(form).toContainText(target.id); await expect(form).toContainText(target.sha256)
    await form.getByRole('textbox', { name: '决定理由', exact: true }).fill('Synthetic original form remains editable')
    await page.getByRole('button', { name: '关闭创作', exact: true }).click(); await expect(guard).toBeVisible()
    await guard.getByRole('button', { name: '保留原命令，明确丢弃临时表单并关闭', exact: true }).click()
    await expect(page.getByRole('dialog', { name: '创作', exact: true })).toHaveCount(0)
    await open(); await expect(panel.getByRole('group', { name: '本次人工内容决定', exact: true })).toHaveCount(0)
    await expect(panel.getByText(/本页仍保留未提交的内容决定表单与原依据/)).toHaveCount(0)
    expect(decisions).toBe(0)
  } finally { await runtime.close() }
})
