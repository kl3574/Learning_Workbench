import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { DraftStore, DraftSaveResult } from '../../apps/web/src/workbench/DraftStore'
import { RestartRuntime } from './restartRuntime'

type InputProbe = { events: { kind: string; at: number; result?: DraftSaveResult }[]; release: () => void }
type ProbeWindow = Window & { __routeDraftInputProbe?: InputProbe }

for (const order of ['save_first', 'load_first'] as const) test(`native route goal input survives its own initial draft ${order} delivery after focus`, async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start(), goalText = '原创路线目标：先读再练，保留每次明确输入。'
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    await page.evaluate(async order => {
      const path = '/src/features/routes/routeDrafts.ts'
      const { routeStore } = await import(path) as { routeStore: DraftStore }
      const save = routeStore.save.bind(routeStore), load = routeStore.load.bind(routeStore)
      let held = false, saveReleased = false, loadReleased = false, releaseSave!: () => void, releaseLoad!: () => void
      const saveGate = new Promise<void>(done => { releaseSave = done }), loadGate = new Promise<void>(done => { releaseLoad = done })
      const events: InputProbe['events'] = []
      const release = () => { saveReleased = true; loadReleased = true; releaseSave(); releaseLoad() }
      ;(window as ProbeWindow).__routeDraftInputProbe = { events, release }
      document.addEventListener('focusin', event => {
        if ((event.target as Element)?.getAttribute('aria-label') !== '路线学习目标') return
        events.push({ kind: 'native_goal_focused', at: performance.now() })
        if (order === 'save_first') { saveReleased = true; releaseSave(); queueMicrotask(() => { loadReleased = true; releaseLoad() }) }
        else { loadReleased = true; releaseLoad() }
      }, true)
      routeStore.save = async (...args) => {
        const envelope = JSON.parse(args[2]) as { candidate: { title: string; goal: string; steps: unknown[] } }
        if (!held && envelope.candidate.title === '' && envelope.candidate.goal === '' && envelope.candidate.steps.length === 0) {
          held = true
          const result = await save(...args)
          events.push({ kind: 'actual_initial_write_completed', at: performance.now(), result })
          await saveGate
          events.push({ kind: 'actual_initial_write_delivered', at: performance.now() })
          return result
        }
        events.push({ kind: 'subsequent_write_started', at: performance.now() })
        return save(...args)
      }
      routeStore.load = async (...args) => {
        const result = await load(...args)
        if (held && !loadReleased) { events.push({ kind: 'actual_load_completed_and_held', at: performance.now() }); await loadGate }
        if (held) events.push({ kind: saveReleased ? 'load_delivered_after_save_release' : 'load_delivered_before_save_release', at: performance.now() })
        return result
      }
    }, order)
    await page.getByRole('button', { name: '创建路线', exact: true }).first().click()
    const editor = page.getByRole('dialog', { name: '创建路线', exact: true })
    await editor.getByRole('button', { name: '填写新路线', exact: true }).click()
    await editor.getByLabel('路线名称', { exact: true }).fill('原创本机路线输入')
    await expect.poll(() => page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.events.some(value => value.kind === 'actual_initial_write_completed'))).toBe(true)
    const goal = editor.getByLabel('路线学习目标', { exact: true })
    await goal.fill(goalText)
    expect(await goal.inputValue()).toBe(goalText)
    await expect(goal).toBeFocused()
    const beforeRelease = await page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.events ?? [])
    if (order === 'load_first') {
      expect(beforeRelease.some(value => value.kind === 'load_delivered_before_save_release')).toBe(true)
      expect(beforeRelease.some(value => value.kind === 'actual_initial_write_delivered')).toBe(false)
    }
    await page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.release())
    await expect(editor.getByText('本机路线草稿存储可用', { exact: true })).toBeVisible()
    const persisted = await page.evaluate(async () => {
      const path = '/src/features/routes/routeDrafts.ts'
      const { routeStore } = await import(path) as { routeStore: DraftStore }
      const result = (window as ProbeWindow).__routeDraftInputProbe?.events.find(value => value.result)?.result
      if (!result) throw new Error('Actual initial draft receipt missing')
      const envelope = JSON.parse(result.record.text) as { workspace_id: string }
      return (await routeStore.load(envelope.workspace_id))[result.record.objectId]
    })
    expect(JSON.parse(persisted.text).candidate).toMatchObject({ title: '原创本机路线输入', goal: goalText })
    expect(persisted.conflicts).toEqual([])
    const events = await page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.events ?? [])
    if (order === 'save_first') expect(events.findIndex(value => value.kind === 'actual_initial_write_delivered')).toBeLessThan(events.findIndex(value => value.kind === 'subsequent_write_started'))
    await page.setViewportSize({ width: 390, height: 844 }); await goal.scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath(`route-goal-${order}-390.png`) })
    writeFileSync(info.outputPath(`actual-route-goal-${order}.json`), JSON.stringify({ scope: 'Original synthetic empty-workspace route form. Actual IndexedDB save/load operations complete normally; only original Promise delivery is controlled at native focus. No server write, result body or status is fabricated. This tests local input/durable draft preservation, not route publication or expert approval.', order, goal: goalText, events, actual_persisted_record: persisted }, null, 2))
  } finally { await runtime.close() }
})
