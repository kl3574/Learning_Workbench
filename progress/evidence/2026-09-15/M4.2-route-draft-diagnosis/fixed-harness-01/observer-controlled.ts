import type { Page, TestInfo } from '<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test/index.mjs'
import { startObserver as startSamples, finishObserver as finishSamples } from './observer-sampled'
import { writeFileSync } from 'node:fs'
type ProbeWindow = Window & { __routeStoreGate?: { events: unknown[]; release: () => void } }
export async function startObserver(page: Page, info: TestInfo) {
  await startSamples(page, info)
  await page.evaluate(async () => {
    const modulePath = '/src/features/routes/routeDrafts.ts'
    type Store = { save: (...args: [string, string, string, number, readonly string[]?]) => Promise<unknown>; load: (...args: [string]) => Promise<unknown> }
    const { routeStore } = await import(modulePath) as { routeStore: Store }
    const save = routeStore.save.bind(routeStore), load = routeStore.load.bind(routeStore)
    let held = false, released = false, release!: () => void
    const gate = new Promise<void>(done => { release = done })
    const events: unknown[] = []
    const unlock = () => { if (released) return; released = true; events.push({ kind: 'release_on_goal_focus', time: performance.now() }); release() }
    ;(window as ProbeWindow).__routeStoreGate = { events, release: unlock }
    document.addEventListener('focusin', event => { if ((event.target as Element)?.getAttribute('aria-label') === '路线学习目标') unlock() }, true)
    routeStore.save = async (...args) => {
      const envelope = JSON.parse(args[2]) as { candidate: { title: string; goal: string; steps: unknown[] } }
      if (!held && envelope.candidate.title === '' && envelope.candidate.goal === '' && envelope.candidate.steps.length === 0) {
        held = true
        const actual = await save(...args)
        events.push({ kind: 'actual_initial_save_completed_result_held', time: performance.now(), result: actual })
        await gate
        return actual
      }
      return save(...args)
    }
    routeStore.load = async (...args) => {
      const actual = await load(...args)
      if (held && !released) { events.push({ kind: 'actual_reload_result_held', time: performance.now() }); await gate }
      return actual
    }
  })
}
export async function finishObserver(page: Page, info: TestInfo) {
  const events = await page.evaluate(() => { const state = (window as ProbeWindow).__routeStoreGate; const events = [...state?.events ?? []]; state?.release(); return events })
  writeFileSync(info.outputPath('controlled-store-timeline.json'), JSON.stringify({ scope: 'Original case; CPU=2 as previous sample. Original first blank route DraftStore.save and subsequent load perform real IndexedDB operations; only returned Promise delivery is held until the actual goal control focus event. No source/response body override.', events }, null, 2))
  await finishSamples(page, info)
}
