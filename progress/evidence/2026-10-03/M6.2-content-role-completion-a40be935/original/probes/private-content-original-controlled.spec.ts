import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import './content-impacts.spec'
// The imported test, fixture, assertions and timeouts are byte-for-byte unchanged.
let restoreLaunch = () => {}
test.beforeEach(async ({ playwright }, info) => {
  const browser = playwright.chromium, launch = browser.launchPersistentContext.bind(browser)
  let count = 0
  browser.launchPersistentContext = async (...args) => {
    const context = await launch(...args)
    if (++count !== 2) return context
    const records: unknown[] = []; let release = () => {}, committed = false, roleReleased = false
    const pending = new Promise<void>(resolve => { release = resolve })
    await context.route('**/api/v1/session/role', async route => {
      if (route.request().postDataJSON().role !== 'author') { await route.continue(); return }
      const response = await route.fetch(); expect(response.status()).toBe(200)
      committed = true; records.push({ at: Date.now(), type: 'author-server-committed-response-held', role: (await response.json()).role })
      // A bounded response hold distinguishes a test that closes while the role
      // operation is pending from one that waits for the visible completed role.
      // It does not increase any product assertion's timeout or retry a command.
      const closedEarly = await route.request().frame().page().getByRole('dialog', { name: '导入', exact: true }).waitFor({ state: 'hidden', timeout: 1000 }).then(() => true, () => false)
      records.push({ at: Date.now(), type: 'import-closed-while-role-response-held', closed: closedEarly })
      if (!closedEarly) release()
      await pending; await route.fulfill({ response }); roleReleased = true; records.push({ at: Date.now(), type: 'author-response-released' })
    })
    await context.route(/\/api\/v1\/content\/impacts\/[^/?]+(?:\?.*)?$/, async route => {
      if (!committed || roleReleased || route.request().method() !== 'GET' || route.request().frame().page() !== context.pages()[0]) { await route.continue(); return }
      const response = await route.fetch(); expect(response.status()).toBe(200)
      records.push({ at: Date.now(), type: 'original-detail-get-after-click-and-close-before-role-response', status: response.status() })
      release()
      const page = context.pages()[0]
      await expect(page.getByRole('button', { name: /^查看影响详情 / }).first()).toHaveCount(0)
      records.push({ at: Date.now(), type: 'access-revoked-before-detail-return', dialog: await page.locator('dialog[aria-label="创作"][open]').count() })
      await route.fulfill({ response })
    })
    const close = context.close.bind(context)
    context.close = async (...closeArgs) => {
      const page = context.pages()[0]
      if (page && !page.isClosed()) records.push({ at: Date.now(), type: 'original-finally-before-browser-close', page: 'restored', dialog: await page.locator('dialog[aria-label="创作"]').count(), open: await page.locator('dialog[aria-label="创作"][open]').count(), detail: await page.getByRole('region', { name: '本次读取的内容影响详情', exact: true }).count() })
      writeFileSync(info.outputPath('safe-original-controlled-timeline.json'), JSON.stringify(records, null, 2)); release(); return close(...closeArgs)
    }
    return context
  }
  restoreLaunch = () => { browser.launchPersistentContext = launch }
})
test.afterEach(() => restoreLaunch())
