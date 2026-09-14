import { chromium, expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdtempSync, existsSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { bootstrap, openSyntheticLesson } from './helpers'
test('real browser 200 percent zoom reflows CSS width through Chrome appearance setting', async () => {
  const profile = mkdtempSync(`${tmpdir()}/learning-workbench-zoom-`)
  const context = await chromium.launchPersistentContext(profile, { headless: true, viewport: null, baseURL: 'http://127.0.0.1:5173', executablePath: existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined, args: ['--window-size=1440,1000'] })
  try {
    const page = await context.newPage()
    await bootstrap(page); await openSyntheticLesson(page)
    const before = await page.evaluate(() => ({ width: innerWidth, height: innerHeight, dpr: devicePixelRatio }))
    const settings = await context.newPage()
    await settings.goto('chrome://settings/appearance')
    await settings.locator('#zoomLevel').selectOption({ label: '200%' })
    await page.bringToFront()
    await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBe(before.dpr * 2)
    const after = await page.evaluate(() => ({ width: innerWidth, height: innerHeight, dpr: devicePixelRatio, scrollWidth: document.documentElement.scrollWidth }))
    expect(Math.abs(after.width * 2 - before.width)).toBeLessThanOrEqual(1)
    expect(after.scrollWidth).toBeLessThanOrEqual(after.width)
    await expect(page.locator('.reader-content h1')).toBeVisible()
    await expect(page.locator('#nav-pane')).toBeHidden()
    const cdp = await context.newCDPSession(page)
    const capture = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, fromSurface: true })
    const png = Buffer.from(capture.data, 'base64')
    expect(png.readUInt32BE(16)).toBe(before.width * before.dpr)
    writeFileSync('../../docs/ui/m1-after-200-percent-native.png', png)
    writeFileSync('../../docs/ui/m1-native-zoom-metrics.json', JSON.stringify({ browser: context.browser()?.version(), method: 'Chrome native chrome://settings/appearance #zoomLevel selection 200%, isolated temporary profile; no CSS zoom or emulation', before, after }, null, 2) + '\n')
  } finally { await context.close(); rmSync(profile, { recursive: true, force: true }) }
})
