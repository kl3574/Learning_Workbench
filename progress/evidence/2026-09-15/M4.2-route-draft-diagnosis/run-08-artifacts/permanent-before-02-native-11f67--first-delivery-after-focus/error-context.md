# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: permanent-before-02.spec.ts >> native route goal input survives its own initial draft save_first delivery after focus
- Location: ../m42-route-save-diagnosis/permanent-before-02.spec.ts:9:60

# Error details

```
Error: expect(locator).toBeFocused() failed

Locator:  getByRole('dialog', { name: '创建路线', exact: true }).getByLabel('路线学习目标', { exact: true })
Expected: focused
Received: inactive
Timeout:  5000ms

Call log:
  - Expect "toBeFocused" getByRole('dialog', { name: '创建路线', exact: true }).getByLabel('路线学习目标', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '创建路线', exact: true }).getByLabel('路线学习目标', { exact: true })
    14 × locator resolved to <textarea rows="3" aria-label="路线学习目标">原创路线目标：先读再练，保留每次明确输入。</textarea>
       - unexpected value "inactive"

```

```yaml
- textbox "路线学习目标": 原创路线目标：先读再练，保留每次明确输入。
```

# Test source

```ts
  1  | import { expect, test } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { writeFileSync } from 'node:fs'
  3  | import type { DraftStore, DraftSaveResult } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/src/workbench/DraftStore.ts'
  4  | import { RestartRuntime } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/tests/e2e/restartRuntime.ts'
  5  | 
  6  | type InputProbe = { events: { kind: string; at: number; result?: DraftSaveResult }[]; release: () => void }
  7  | type ProbeWindow = Window & { __routeDraftInputProbe?: InputProbe }
  8  | 
  9  | for (const order of ['save_first', 'load_first'] as const) test(`native route goal input survives its own initial draft ${order} delivery after focus`, async ({ playwright }, info) => {
  10 |   const runtime = await RestartRuntime.start(), goalText = '原创路线目标：先读再练，保留每次明确输入。'
  11 |   try {
  12 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  13 |     await runtime.authenticateOnly(page)
  14 |     await page.evaluate(async order => {
  15 |       const path = '/src/features/routes/routeDrafts.ts'
  16 |       const { routeStore } = await import(path) as { routeStore: DraftStore }
  17 |       const save = routeStore.save.bind(routeStore), load = routeStore.load.bind(routeStore)
  18 |       let held = false, saveReleased = false, loadReleased = false, releaseSave!: () => void, releaseLoad!: () => void
  19 |       const saveGate = new Promise<void>(done => { releaseSave = done }), loadGate = new Promise<void>(done => { releaseLoad = done })
  20 |       const events: InputProbe['events'] = []
  21 |       const release = () => { saveReleased = true; loadReleased = true; releaseSave(); releaseLoad() }
  22 |       ;(window as ProbeWindow).__routeDraftInputProbe = { events, release }
  23 |       document.addEventListener('focusin', event => {
  24 |         if ((event.target as Element)?.getAttribute('aria-label') !== '路线学习目标') return
  25 |         events.push({ kind: 'native_goal_focused', at: performance.now() })
  26 |         if (order === 'save_first') { saveReleased = true; releaseSave(); queueMicrotask(() => { loadReleased = true; releaseLoad() }) }
  27 |         else { loadReleased = true; releaseLoad() }
  28 |       }, true)
  29 |       routeStore.save = async (...args) => {
  30 |         const envelope = JSON.parse(args[2]) as { candidate: { title: string; goal: string; steps: unknown[] } }
  31 |         if (!held && envelope.candidate.title === '' && envelope.candidate.goal === '' && envelope.candidate.steps.length === 0) {
  32 |           held = true
  33 |           const result = await save(...args)
  34 |           events.push({ kind: 'actual_initial_write_completed', at: performance.now(), result })
  35 |           await saveGate
  36 |           events.push({ kind: 'actual_initial_write_delivered', at: performance.now() })
  37 |           return result
  38 |         }
  39 |         events.push({ kind: 'subsequent_write_started', at: performance.now() })
  40 |         return save(...args)
  41 |       }
  42 |       routeStore.load = async (...args) => {
  43 |         const result = await load(...args)
  44 |         if (held && !loadReleased) { events.push({ kind: 'actual_load_completed_and_held', at: performance.now() }); await loadGate }
  45 |         if (held) events.push({ kind: saveReleased ? 'load_delivered_after_save_release' : 'load_delivered_before_save_release', at: performance.now() })
  46 |         return result
  47 |       }
  48 |     }, order)
  49 |     await page.getByRole('button', { name: '创建路线', exact: true }).first().click()
  50 |     const editor = page.getByRole('dialog', { name: '创建路线', exact: true })
  51 |     await editor.getByRole('button', { name: '填写新路线', exact: true }).click()
  52 |     await editor.getByLabel('路线名称', { exact: true }).fill('原创本机路线输入')
  53 |     await expect.poll(() => page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.events.some(value => value.kind === 'actual_initial_write_completed'))).toBe(true)
  54 |     const goal = editor.getByLabel('路线学习目标', { exact: true })
  55 |     await goal.fill(goalText)
  56 |     expect(await goal.inputValue()).toBe(goalText)
> 57 |     await expect(goal).toBeFocused()
     |                        ^ Error: expect(locator).toBeFocused() failed
  58 |     const beforeRelease = await page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.events ?? [])
  59 |     if (order === 'load_first') {
  60 |       expect(beforeRelease.some(value => value.kind === 'load_delivered_before_save_release')).toBe(true)
  61 |       expect(beforeRelease.some(value => value.kind === 'actual_initial_write_delivered')).toBe(false)
  62 |     }
  63 |     await page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.release())
  64 |     await expect(editor.getByText('本机路线草稿存储可用', { exact: true })).toBeVisible()
  65 |     const persisted = await page.evaluate(async () => {
  66 |       const path = '/src/features/routes/routeDrafts.ts'
  67 |       const { routeStore } = await import(path) as { routeStore: DraftStore }
  68 |       const result = (window as ProbeWindow).__routeDraftInputProbe?.events.find(value => value.result)?.result
  69 |       if (!result) throw new Error('Actual initial draft receipt missing')
  70 |       const envelope = JSON.parse(result.record.text) as { workspace_id: string }
  71 |       return (await routeStore.load(envelope.workspace_id))[result.record.objectId]
  72 |     })
  73 |     expect(JSON.parse(persisted.text).candidate).toMatchObject({ title: '原创本机路线输入', goal: goalText })
  74 |     expect(persisted.conflicts).toEqual([])
  75 |     const events = await page.evaluate(() => (window as ProbeWindow).__routeDraftInputProbe?.events ?? [])
  76 |     if (order === 'save_first') expect(events.findIndex(value => value.kind === 'actual_initial_write_delivered')).toBeLessThan(events.findIndex(value => value.kind === 'subsequent_write_started'))
  77 |     await page.setViewportSize({ width: 390, height: 844 }); await goal.scrollIntoViewIfNeeded()
  78 |     await page.screenshot({ path: info.outputPath(`route-goal-${order}-390.png`) })
  79 |     writeFileSync(info.outputPath(`actual-route-goal-${order}.json`), JSON.stringify({ scope: 'Original synthetic empty-workspace route form. Actual IndexedDB save/load operations complete normally; only original Promise delivery is controlled at native focus. No server write, result body or status is fabricated. This tests local input/durable draft preservation, not route publication or expert approval.', order, goal: goalText, events, actual_persisted_record: persisted }, null, 2))
  80 |   } finally { await runtime.close() }
  81 | })
  82 | 
```