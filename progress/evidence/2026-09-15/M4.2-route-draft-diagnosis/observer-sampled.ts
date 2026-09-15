import type { Page, TestInfo } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
import { startObserver as startNetwork, finishObserver as finishNetwork } from './observer'
import { writeFileSync } from 'node:fs'
type ProbeWindow = Window & { __routeInputProbe?: { events: unknown[]; stopped: boolean } }
export async function startObserver(page: Page, info: TestInfo) {
  startNetwork(page, info)
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 2 })
  await page.evaluate(() => {
    const state = { events: [] as unknown[], stopped: false }; (window as ProbeWindow).__routeInputProbe = state
    let last = '', nextID = 0; const identities = new WeakMap<Element, number>()
    const sample = (reason: string) => {
      const panel = document.querySelector('.route-editor'); let instance = null
      if (panel) { if (!identities.has(panel)) identities.set(panel, ++nextID); instance = identities.get(panel) }
      const fields = Array.from(document.querySelectorAll('.route-editor input,.route-editor textarea,.route-editor select')).map(value => ({ label: value.getAttribute('aria-label'), value: (value as HTMLInputElement).value, disabled: value.matches(':disabled') }))
      const snapshot = { instance, fields }; const encoded = JSON.stringify(snapshot)
      if (reason !== 'frame' || encoded !== last) state.events.push({ elapsed_ms: performance.now(), reason, ...snapshot })
      last = encoded
    }
    document.addEventListener('input', event => { if ((event.target as Element)?.closest('.route-editor')) { sample('input-capture'); queueMicrotask(() => sample('input-after-microtask')) } }, true)
    document.addEventListener('change', event => { if ((event.target as Element)?.closest('.route-editor')) sample('change-capture') }, true)
    const tick = () => { if (state.stopped) return; sample('frame'); requestAnimationFrame(tick) }; tick()
  })
}
export async function finishObserver(page: Page, info: TestInfo) {
  const events = await page.evaluate(() => { const state = (window as ProbeWindow).__routeInputProbe; if (state) state.stopped = true; return state?.events ?? [] })
  writeFileSync(info.outputPath('input-timeline.json'), JSON.stringify({ scope: 'Read-only DOM frame/input/change sampling; CDP CPU rate=2 to widen natural asynchronous boundaries; original test steps/assertions unchanged, no response fabrication.', events }, null, 2))
  await finishNetwork(page, info)
}
