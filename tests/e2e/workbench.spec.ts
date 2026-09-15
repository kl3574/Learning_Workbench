import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { bootstrap, openSyntheticLesson } from './helpers'
import type { WorkbenchSession } from '../../packages/contracts/generated/types'

test('empty workspace, native bootstrap, four fixed navigation and truthful auxiliary states', async ({ page }) => {
  await bootstrap(page)
  const labels = await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button').allTextContents()
  expect(labels.map(text => text.replace(/[↗▤✎☑]/g, '').replace(/含例题|含解答/g, '').trim())).toEqual(['学习路线', '教材', '习题', '测试题'])
  await expect(page.getByRole('heading', { name: '从学习目标开始', exact: true })).toBeVisible()
  await expect(page.getByText('本地任务 · 明确授权')).toBeVisible()
  for (const name of ['教材', '习题', '测试题', '学习路线']) {
    await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name, exact: false }).click()
    await expect(page.getByRole('heading', { name: 'Agent', exact: true })).toBeVisible()
  }
  await page.getByRole('button', { name: '创建本次问答任务 ↑' }).isDisabled().then(disabled => expect(disabled).toBe(true))
  await page.keyboard.press('Control+Shift+P')
  await expect(page.getByRole('dialog', { name: '命令面板' })).toBeVisible()
  await page.getByRole('dialog').getByRole('button', { name: '导出备份' }).click()
  await expect(page.getByRole('dialog')).toContainText('尚未实现')
})

test('real keyboard and mouse resize, native drawers, focus return and restored layout', async ({ page }) => {
  await bootstrap(page)
  const split = page.getByRole('separator', { name: '导航栏宽度' })
  await split.focus(); await page.keyboard.press('ArrowRight'); await expect(split).toHaveAttribute('aria-valuenow', '316')
  await page.keyboard.press('Home'); await expect(split).toHaveAttribute('aria-valuenow', '260')
  await page.keyboard.press('End'); await expect(split).toHaveAttribute('aria-valuenow', '360')
  await page.keyboard.press('Enter'); await expect(page.locator('#nav-pane')).toBeHidden()
  await page.keyboard.press('Enter'); await expect(page.locator('#nav-pane')).toBeVisible()
  const rect = await split.boundingBox(); if (!rect) throw new Error('Missing separator rectangle')
  await page.mouse.move(rect.x + 3, rect.y + 100); await page.mouse.down(); await page.mouse.move(rect.x - 29, rect.y + 100); await page.mouse.up()
  await expect(split).toHaveAttribute('aria-valuenow', '328')
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload(); await expect(split).toHaveAttribute('aria-valuenow', '328')
  await page.setViewportSize({ width: 390, height: 844 })
  const toggle = page.getByRole('button', { name: '切换导航栏' })
  await toggle.click(); const dialog = page.getByRole('dialog', { name: '课程目录' }); await expect(dialog).toBeVisible()
  await page.keyboard.press('Shift+Tab'); expect(await page.evaluate(() => document.querySelector('dialog')?.contains(document.activeElement))).toBe(true)
  await page.keyboard.press('Escape'); await expect(dialog).toBeHidden(); await expect(toggle).toBeFocused()
  await page.getByRole('button', { name: '切换 Agent 栏' }).click(); await expect(page.getByRole('dialog', { name: 'Agent 助教' })).toBeVisible()
  await page.getByRole('button', { name: '关闭Agent 助教' }).click(); await expect(page.getByRole('button', { name: '切换 Agent 栏' })).toBeFocused()
})

test('object drafts survive preview switches, close choice and browser reload without fake sending', async ({ page }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  const draft = page.getByRole('textbox', { name: '问题草稿' })
  await draft.fill('A 的未发送问题')
  await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  await expect(draft).toHaveValue(''); await draft.fill('B 的未发送问题')
  await page.getByRole('tab', { name: '1.2' }).click(); await expect(draft).toHaveValue('A 的未发送问题')
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload(); await expect(draft).toHaveValue('A 的未发送问题')
  await page.getByRole('button', { name: '关闭标签 1.2' }).click(); await expect(page.getByRole('dialog', { name: '保留问题草稿' })).toBeVisible()
  await page.getByRole('button', { name: '保留本地草稿并关闭' }).click()
  await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.2' }).click(); await expect(draft).toHaveValue('A 的未发送问题')
  const keys = await page.evaluate(() => Object.keys(localStorage))
  expect(keys).toContain('learning-workbench.last-confirmed-workspace.v1')
  expect((await page.evaluate(() => indexedDB.databases())).length).toBeGreaterThan(0)
  expect(keys).not.toContain('learning-workbench.unsent-drafts.v1')
})

test('server CAS conflict is visible, local object drafts survive and explicit readback recovers', async ({ page, context }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.getByRole('textbox', { name: '问题草稿' }).fill('冲突时保留的草稿')
  const second = await context.newPage(); await second.goto('/')
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await second.getByRole('button', { name: '切换导航栏' }).click(); await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.getByRole('button', { name: '切换 Agent 栏' }).click()
  await expect(page.getByText('会话版本冲突', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '读取服务端会话，保留草稿' }).click()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await expect(page.getByRole('textbox', { name: '问题草稿' })).toHaveValue('冲突时保留的草稿')
  await second.close()
})

test('offline pending UI is restored after actual connection recovery', async ({ page, context }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await context.setOffline(true)
  await page.getByRole('textbox', { name: '问题草稿' }).fill('断线草稿')
  await page.getByRole('button', { name: '切换导航栏' }).click()
  await expect(page.getByText('离线 · UI 待同步')).toBeVisible()
  await context.setOffline(false)
  await page.getByRole('button', { name: '重试连接' }).click()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload()
  await expect(page.getByRole('textbox', { name: '问题草稿' })).toHaveValue('断线草稿')
})

test('actual MathJax, no runtime errors, long formula local scrolling, all screenshot sizes', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  await bootstrap(page); await openSyntheticLesson(page)
  await expect(page.locator('.math-error')).toHaveCount(0)
  for (const [width, height] of [[1440, 900], [1920, 1080], [900, 900], [390, 844]]) {
    await page.setViewportSize({ width, height })
    const heading = page.locator('.reader-content h1'); await expect(heading).toBeVisible()
    await expect.poll(async () => (await heading.boundingBox())?.width ?? 0).toBeGreaterThan(180); const rect = await heading.boundingBox(); expect(rect).not.toBeNull(); expect(rect!.width).toBeGreaterThan(180); expect(rect!.x).toBeGreaterThanOrEqual(0); expect(rect!.x + rect!.width).toBeLessThanOrEqual(width)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: `../../docs/ui/m1-after-${width}.png` })
    if (width === 390) {
      await page.getByRole('button', { name: '切换导航栏' }).click(); await page.screenshot({ path: '../../docs/ui/m1-after-390-directory.png' }); await page.keyboard.press('Escape')
      await page.getByRole('button', { name: '切换 Agent 栏' }).click(); await page.screenshot({ path: '../../docs/ui/m1-after-390-agent.png' }); await page.keyboard.press('Escape')
    }
  }
  await page.setViewportSize({ width: 390, height: 844 })
  const formula = page.locator('.formula.display').last(); await formula.scrollIntoViewIfNeeded()
  expect(await formula.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true)
  await formula.evaluate(element => { element.scrollLeft = 150 })
  expect(await formula.evaluate(element => element.scrollLeft)).toBeGreaterThan(0)
  await page.screenshot({ path: '../../docs/ui/m1-after-390-long-formula.png' })
  expect(errors).toEqual([])
})


test('two browser pages keep drafts for different objects in native IndexedDB', async ({ page, context }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  const second = await context.newPage(); await second.goto('/')
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.getByRole('textbox', { name: '问题草稿' }).fill('窗口 A 的对象 A 草稿')
  await expect(page.getByText('草稿保存中…', { exact: true })).toBeHidden()
  await second.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  await second.getByRole('textbox', { name: '问题草稿' }).fill('窗口 B 的对象 B 草稿')
  await expect(second.getByText('草稿保存中…', { exact: true })).toBeHidden()
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.reload()
  await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.2' }).click()
  await expect(page.getByRole('textbox', { name: '问题草稿' })).toHaveValue('窗口 A 的对象 A 草稿')
  await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  await expect(page.getByRole('textbox', { name: '问题草稿' })).toHaveValue('窗口 B 的对象 B 草稿')
  await second.close()
})

test('exact reference mismatch stays unresolved and preserves the original snapshot', async ({ page }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.evaluate(async () => {
    const auth = await (await fetch('/api/v1/session')).json()
    const session = await (await fetch('/api/v1/workbench/session')).json()
    const tab = session.tabs.find((item: { id: string }) => item.id === session.active_tab_id)
    tab.context.active_ref.revision = 99; tab.context.active_ref.sha256 = 'b'.repeat(64)
    const response = await fetch('/api/v1/workbench/session', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf_token }, body: JSON.stringify({ expected_revision: session.revision, session }) })
    if (!response.ok) throw new Error(`Fixture mismatch setup failed ${response.status}`)
  })
  await page.reload()
  await expect(page.getByRole('heading', { name: '暂时无法打开这个对象' })).toBeVisible()
  await expect(page.locator('.reader-content')).toHaveCount(0)
  await expect(page.locator('.context-preview')).toContainText('修订 99')
  await expect(page.locator('.context-preview')).toContainText('引用待解析')
})

test('cold lazy renderer restores saved reading offset after the content is ready', async ({ page }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.locator('.reader-scroll').evaluate(element => { element.scrollTop = 700 })
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await expect.poll(() => page.locator('.reader-scroll').evaluate(element => element.scrollTop)).toBeGreaterThan(690)
  // The previous saved label can still be visible before the browser emits
  // the scroll event. This scenario requires an actually persisted position.
  await expect.poll(async () => {
    const response = await page.request.get('/api/v1/workbench/session')
    expect(response.status()).toBe(200)
    const stored: WorkbenchSession = await response.json()
    return stored.tabs.find(tab => tab.id === stored.active_tab_id)?.scroll_offset ?? 0
  }).toBeGreaterThan(690)
  await page.route('**/src/shared/Markdown.tsx*', async route => { await new Promise(resolve => setTimeout(resolve, 500)); await route.continue() })
  await page.reload()
  await expect(page.locator('.reader-content svg').first()).toBeAttached()
  await expect.poll(() => page.locator('.reader-scroll').evaluate(element => element.scrollTop)).toBeGreaterThan(690)
})


test('native concurrent same-object transactions preserve both candidates and expose explicit recovery', async ({ page, context }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  const second = await context.newPage(); await second.goto('/')
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  const target = await page.evaluate(async () => {
    const auth = await (await fetch('/api/v1/session')).json()
    const session = await (await fetch('/api/v1/workbench/session')).json()
    const store = await import('/src/workbench/DraftStore.ts')
    const all = await store.load(auth.workspace_id)
    return { workspace: auth.workspace_id, object: session.active_tab_id, revision: all[session.active_tab_id]?.revision ?? 0 }
  })
  const write = (targetPage: typeof page, text: string) => targetPage.evaluate(async ({ target, text }) => {
    const store = await import('/src/workbench/DraftStore.ts')
    return store.save(target.workspace, target.object, text, target.revision)
  }, { target, text })
  const results = await Promise.all([write(page, '同对象窗口 A 的候选'), write(second, '同对象窗口 B 的候选')])
  expect(results.map(result => result.kind).sort()).toEqual(['conflict', 'saved'])
  await expect(page.getByText('草稿版本冲突 · 两份文本均已保留')).toBeVisible()
  await expect(page.locator('.draft-feedback')).toContainText('已存草稿')
  await expect(page.locator('.draft-feedback')).toContainText('同对象窗口 A 的候选')
  await expect(page.locator('.draft-feedback')).toContainText('同对象窗口 B 的候选')
  await page.reload()
  await expect(page.getByText('草稿版本冲突 · 两份文本均已保留')).toBeVisible()
  await page.getByText('查看冲突草稿').click()
  await expect(page.locator('.draft-feedback')).toContainText('同对象窗口')
  await page.getByRole('button', { name: '采用这份草稿' }).click()
  await expect(page.getByText('草稿版本冲突 · 两份文本均已保留')).toBeHidden()
  const expected = results.find(result => result.kind === 'conflict')!.conflict.text
  await expect(page.getByRole('textbox', { name: '问题草稿' })).toHaveValue(expected)
  await second.close()
})


test('directory history restores the current course and navigation entry', async ({ page }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.locator('.directory-scroll').evaluate(element => { element.scrollTop = 180 })
  await expect.poll(() => page.locator('.directory-scroll').evaluate(element => element.scrollTop)).toBeGreaterThan(170)
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  await expect.poll(() => page.locator('.directory-scroll').evaluate(element => element.scrollTop)).toBeGreaterThan(170)
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload()
  await expect.poll(() => page.locator('.directory-scroll').evaluate(element => element.scrollTop)).toBeGreaterThan(170)
})

test('UI cache quota failure stays visibly unsaved until the real server acknowledges', async ({ page }) => {
  await bootstrap(page)
  await page.route('**/api/v1/workbench/session', route => route.request().method() === 'PUT' ? route.abort('failed') : route.continue())
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException('Synthetic quota fault', 'QuotaExceededError') } })
  await page.getByRole('button', { name: '切换导航栏' }).click()
  await expect(page.getByText('✓ UI 会话已保存')).toBeHidden()
  await expect(page.getByText('离线 · UI 待同步')).toBeVisible()
  await expect(page.locator('#nav-pane')).toBeHidden()
  const stored = await page.evaluate(async () => (await (await fetch('/api/v1/workbench/session')).json()).nav_collapsed)
  expect(stored).toBe(false)
  await page.unroute('**/api/v1/workbench/session')
  await page.getByRole('button', { name: '重试连接' }).click()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await expect(page.locator('#nav-pane')).toBeHidden()
  expect(await page.evaluate(async () => (await (await fetch('/api/v1/workbench/session')).json()).nav_collapsed)).toBe(true)
})

test('offline UI candidates from two pages remain separate on reload', async ({ page, context }) => {
  await bootstrap(page)
  const second = await context.newPage(); await second.goto('/')
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await context.setOffline(true)
  await page.getByRole('button', { name: '切换导航栏' }).click()
  await second.getByRole('button', { name: '切换 Agent 栏' }).click()
  await expect(page.getByText('离线 · UI 待同步')).toBeVisible(); await expect(second.getByText('离线 · UI 待同步')).toBeVisible()
  const candidates = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.includes('.pending-ui.')).map(([, value]) => { const record = JSON.parse(value); return record.session ?? record }))
  expect(candidates).toHaveLength(2)
  expect(candidates.some(value => value.nav_collapsed && !value.agent_collapsed)).toBe(true)
  expect(candidates.some(value => !value.nav_collapsed && value.agent_collapsed)).toBe(true)
  await context.setOffline(false)
  await page.reload()
  await expect(page.locator('#nav-pane')).toBeHidden()
  await expect(page.locator('#agent-pane')).toBeVisible()
  await expect(page.getByText('发现其他窗口的待同步 UI 快照；原始快照保留。')).toBeVisible()
  await second.close()
})


test('quota-only memory candidate with a changed server baseline shows three-way comparison before explicit CAS', async ({ page, context }) => {
  await bootstrap(page)
  const second = await context.newPage(); await second.goto('/')
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.route('**/api/v1/workbench/session', route => route.request().method() === 'PUT' ? route.abort('failed') : route.continue())
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException('Synthetic quota fault', 'QuotaExceededError') } })
  await page.getByRole('button', { name: '切换导航栏' }).click()
  await expect(page.getByText('离线 · UI 待同步')).toBeVisible()
  await second.getByRole('button', { name: '切换 Agent 栏' }).click()
  await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.unroute('**/api/v1/workbench/session')
  await page.getByRole('button', { name: '重试连接' }).click()
  await expect(page.getByText('会话版本冲突', { exact: true })).toBeVisible()
  await expect(page.locator('#nav-pane')).toBeHidden()
  const comparison = page.getByRole('region', { name: '会话三方比较' })
  await expect(comparison).toBeVisible()
  await expect(comparison).toContainText('原基准')
  await expect(comparison).toContainText('本地待同步')
  await expect(comparison).toContainText('服务端')
  const row = comparison.getByRole('row').filter({ has: page.getByRole('rowheader', { name: '导航栏', exact: true }) })
  await expect(row.getByRole('cell').nth(0)).toContainText('展开')
  await expect(row.getByRole('cell').nth(1)).toHaveText('已折叠')
  await expect(row.getByRole('cell').nth(2)).toContainText('展开')
  const remoteBeforeChoice = await page.evaluate(async () => (await (await fetch('/api/v1/workbench/session')).json()).nav_collapsed)
  expect(remoteBeforeChoice).toBe(false)
  await page.screenshot({ path: '../../docs/ui/m1-session-three-way-conflict.png' })
  await comparison.getByRole('button', { name: '采用本地会话并重新保存' }).click()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  expect(await page.evaluate(async () => (await (await fetch('/api/v1/workbench/session')).json()).nav_collapsed)).toBe(true)
  await second.close()
})


test('per-object details and focus survive A to B to A and browser reload after lazy content readiness', async ({ page }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.getByRole('button', { name: '固定标签 1.2' }).click()
  const summary = page.locator('.tex-source summary').first()
  await summary.scrollIntoViewIfNeeded(); await summary.click()
  await expect(page.locator('.tex-source').first()).toHaveAttribute('open', '')
  await expect(summary).toBeFocused()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  await expect(page.locator('.reader-content h1')).toContainText('1.3')
  await expect(page.locator('.tex-source').first()).not.toHaveAttribute('open', '')
  await page.getByRole('tab', { name: '1.2' }).click()
  await expect(page.locator('.tex-source').first()).toHaveAttribute('open', '')
  await expect(summary).toBeFocused()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload()
  await expect(page.locator('.tex-source').first()).toHaveAttribute('open', '')
  await expect(summary).toBeFocused()
})

test('first unsent-draft conflict shows original, local and stored text before any reload or choice', async ({ page, context }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.getByRole('textbox', { name: '问题草稿' }).fill('双方共同的原基准')
  await expect(page.getByText('草稿保存中…', { exact: true })).toBeHidden()
  const second = await context.newPage()
  // Delay broadcast delivery to model a genuinely stale open editor; the native
  // IndexedDB transaction and user typing still run unchanged.
  await second.addInitScript(() => {
    const Original = window.BroadcastChannel
    window.BroadcastChannel = class extends Original {
      get onmessage() { return null }
      set onmessage(_handler) { /* deliberately delayed notification */ }
    }
  })
  await second.goto('/')
  await expect(second.getByRole('textbox', { name: '问题草稿' })).toHaveValue('双方共同的原基准')
  await page.getByRole('textbox', { name: '问题草稿' }).fill('窗口 A 新的已存版本')
  await expect(page.getByText('草稿保存中…', { exact: true })).toBeHidden()
  await second.getByRole('textbox', { name: '问题草稿' }).fill('窗口 B 尚未确认候选')
  const comparison = second.locator('.draft-feedback')
  await expect(comparison).toContainText('草稿版本冲突')
  await expect(second.getByRole('textbox', { name: '问题草稿' })).toHaveValue('窗口 B 尚未确认候选')
  await expect(comparison).toContainText('双方共同的原基准')
  await expect(comparison).toContainText('窗口 A 新的已存版本')
  await expect(comparison).toContainText('窗口 B 尚未确认候选')
  await comparison.getByRole('button', { name: '使用已存版本' }).click()
  await expect(second.getByRole('textbox', { name: '问题草稿' })).toHaveValue('窗口 A 新的已存版本')
  await second.close()
})

test('route directory stays honestly empty and continue reading restores the exact last lesson', async ({ page }) => {
  await bootstrap(page)
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  await page.getByRole('button', { name: '浏览合成示例课程' }).click()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '学习路线', exact: true }).click()
  await expect(page.getByRole('region', { name: '学习路线目录', exact: true }).getByText('尚无正式学习路线。', { exact: true })).toBeVisible()
  await expect(page.getByRole('navigation', { name: '上下文目录' })).toHaveCount(0)
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  await page.getByRole('button', { name: '打开示例小节' }).click()
  await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  await expect(page.locator('.reader-content h1')).toContainText('1.3')
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  await page.getByRole('button', { name: '继续浏览示例' }).click()
  await expect(page.locator('.reader-content h1')).toContainText('1.3')
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
  await page.getByRole('button', { name: '继续浏览示例' }).click()
  await expect(page.locator('.reader-content h1')).toContainText('1.3')
})

test('native keyboard selection updates frozen-reference preview and ambiguous source matches are refused', async ({ page }) => {
  await bootstrap(page); await openSyntheticLesson(page)
  await page.evaluate(() => {
    const node = document.querySelector('.reader-content p')!.firstChild!
    // Establish one selected character, then extend it using real keyboard input.
    const range = document.createRange(); range.setStart(node, 0); range.setEnd(node, 1)
    const selection = getSelection()!; selection.removeAllRanges(); selection.addRange(range)
  })
  for (let i = 0; i < 3; i++) await page.keyboard.press('Shift+ArrowRight')
  await expect(page.locator('.context-preview blockquote')).toContainText('这是一段')
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  const quote = await page.evaluate(async () => {
    const session = await (await fetch('/api/v1/workbench/session')).json()
    return session.tabs.find((tab: { id: string }) => tab.id === session.active_tab_id).context.selection
  })
  expect(quote.exact_quote).toBe('这是一段'); expect(quote.start_codepoint).toBe(0); expect(quote.end_codepoint).toBe(4)
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.querySelector('.reader-content')!, NodeFilter.SHOW_TEXT)
    let node: Node | null
    while ((node = walker.nextNode())) {
      const offset = node.textContent?.indexOf('条件') ?? -1
      if (offset >= 0) { const range = document.createRange(); range.setStart(node, offset); range.setEnd(node, offset + 2); const selection = getSelection()!; selection.removeAllRanges(); selection.addRange(range); break }
    }
  })
  await expect(page.getByText('选文在原文中有多个匹配，未附加上下文；请选择更独特的片段。')).toBeVisible()
  await expect(page.locator('.context-preview blockquote')).toHaveCount(0)
})
