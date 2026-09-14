import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'

type ResizeGate = { hold: boolean; pending: number; release: () => void }
declare global { interface Window { __layoutResizeGate: ResizeGate } }
const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await page.addInitScript(() => {
      // Delay delivery of real resize listeners, without replacing browser layout or API responses.
      const add = window.addEventListener.bind(window), remove = window.removeEventListener.bind(window)
      const wrappers = new WeakMap<EventListenerOrEventListenerObject, EventListener>(), pending: (() => void)[] = []
      const gate: ResizeGate = { hold: false, pending: 0, release: () => { gate.hold = false; gate.pending = 0; for (const run of pending.splice(0)) run() } }
      window.__layoutResizeGate = gate
      window.addEventListener = ((type: string, listener: EventListenerOrEventListenerObject, options?: boolean | AddEventListenerOptions) => {
        if (type !== 'resize' || !listener) return add(type, listener, options)
        const wrapper: EventListener = event => {
          const run = () => typeof listener === 'function' ? listener.call(window, event) : listener.handleEvent(event)
          if (gate.hold) { pending.push(run); gate.pending = pending.length } else run()
        }
        wrappers.set(listener, wrapper); return add(type, wrapper, options)
      }) as typeof window.addEventListener
      window.removeEventListener = ((type: string, listener: EventListenerOrEventListenerObject, options?: boolean | EventListenerOptions) => remove(type, wrappers.get(listener) ?? listener, options)) as typeof window.removeEventListener
    })
    await runtime.authenticateOnly(page); await use(page)
  },
})

async function geometry(page: Page) {
  return page.evaluate(() => {
    const rect = (selector: string) => {
      const element = document.querySelector(selector)!, value = element.getBoundingClientRect()
      return { x: value.x, y: value.y, width: value.width, height: value.height, bottom: value.bottom, scrollTop: element.scrollTop, scrollHeight: element.scrollHeight }
    }
    return { time: performance.now(), viewport: [innerWidth, innerHeight], pendingResizeListeners: window.__layoutResizeGate.pending, scroll: rect('.assessment-scroll'), section: rect('.practice-submit'), paragraph: rect('.practice-submit > p') }
  })
}

test('narrow layout and submitted explanation remain visible before React resize listeners run', async ({ page }, info) => {
  const fixture = originalAssessmentPackage('nativeresponsiveresize'), imported = await importAssessmentPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const created = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const response = await created; expect(response.status()).toBe(201)
  const attempt: AttemptSnapshot = await response.json()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
  await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
  await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible()
  await expect.poll(async () => (await page.request.get(`/api/v1/attempts/${attempt.id}`).then(value => value.json())).status).toBe('needs_review')
  const observations: { stage: string; geometry: Awaited<ReturnType<typeof geometry>> }[] = []
  const sample = async (stage: string) => { observations.push({ stage, geometry: await geometry(page) }) }
  await sample('desktop')
  try {
    await page.evaluate(() => { window.__layoutResizeGate.hold = true })
    await page.setViewportSize({ width: 390, height: 844 })
    await expect.poll(() => page.evaluate(() => window.__layoutResizeGate.pending)).toBeGreaterThan(0)
    await sample('narrow-before-listeners')
    expect.soft(observations.at(-1)!.geometry.scroll.width).toBe(390)
    await page.locator('.practice-submit').scrollIntoViewIfNeeded()
    await sample('section-scrolled-before-listeners')
    await expect(page.locator('.practice-submit > p')).toBeInViewport()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(await page.locator('.workbench-grid').evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true)
    await page.evaluate(() => window.__layoutResizeGate.release())
    await expect(page.locator('#nav-pane')).toBeHidden()
    await sample('after-listeners')
    await expect(page.locator('.practice-submit > p')).toBeInViewport()
    expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
  } finally {
    await page.evaluate(() => window.__layoutResizeGate.release())
    await sample('final')
    writeFileSync(info.outputPath('responsive-layout-geometry.json'), JSON.stringify(observations, null, 2))
    await page.screenshot({ path: info.outputPath('responsive-submitted-390.png') })
  }
})
