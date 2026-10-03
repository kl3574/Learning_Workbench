import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { publishEditedBlock } from './contentImpactsData'

test('native dialog keeps a content gesture through layout change and still accepts explicit closing', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    await publishEditedBlock(page, runtime)
    const writes: string[] = []
    page.on('request', request => { if (request.method() === 'POST' && /\/content\/impacts\/[^/]+\/decisions$/.test(new URL(request.url()).pathname)) writes.push('decision') })
    await page.getByRole('button', { name: '创作', exact: true }).click()
    await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '创作', exact: true }), panel = page.getByRole('region', { name: '内容变更影响复核', exact: true })
    await panel.getByRole('button', { name: '从第一页读取内容变更', exact: true }).click()
    const button = panel.getByRole('button', { name: /^查看影响详情 / }).first()
    await expect(button).toBeVisible()
    await page.setViewportSize({ width: 700, height: 900 })
    await button.scrollIntoViewIfNeeded()
    const box = (await button.boundingBox())!, point = { x: box.x + 8, y: box.y + box.height / 2 }
    await button.evaluate(element => { Object.assign(window, { originalDialogButton: element }) })
    await page.mouse.move(point.x, point.y); await page.mouse.down()
    // A real viewport layout change moves the still-mounted button away from the
    // stationary pointer. No role, payload, DOM replacement, or transport is faked.
    await page.setViewportSize({ width: 1800, height: 900 })
    const shifted = await dialog.evaluate((element, originalPoint) => {
      const rect = element.getBoundingClientRect(), original = (window as unknown as { originalDialogButton: Element }).originalDialogButton
      return { button_connected: original.isConnected, same_button: element.contains(original), outside: originalPoint.x < rect.left || originalPoint.x >= rect.right || originalPoint.y < rect.top || originalPoint.y >= rect.bottom, target_is_dialog: document.elementFromPoint(originalPoint.x, originalPoint.y) === element }
    }, point)
    expect(shifted).toEqual({ button_connected: true, same_button: true, outside: true, target_is_dialog: true })
    await page.mouse.up()
    try { await expect(dialog).toBeVisible() }
    finally { writeFileSync(info.outputPath('dialog-pointer-layout.json'), JSON.stringify({ scope: 'Synthetic actual Content UI; layout and pointer categories only. Separate from the original full-gate cause.', shifted }, null, 2)) }
    // A stationary ordinary click still invokes the actual Content detail read.
    await button.click(); await expect(panel.getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toBeVisible()
    await page.mouse.click(2, 2); await expect(dialog).toHaveCount(0)
    await page.getByRole('button', { name: '创作', exact: true }).click()
    await expect(dialog).toBeVisible(); await page.keyboard.press('Escape'); await expect(dialog).toHaveCount(0)
    await page.getByRole('button', { name: '创作', exact: true }).click()
    await dialog.getByRole('button', { name: '关闭创作', exact: true }).click(); await expect(dialog).toHaveCount(0)
    expect(writes).toEqual([])
  } finally { await runtime.close() }
})
