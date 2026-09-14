import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { Note, WorkbenchSession } from '../../packages/contracts/generated/types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, originalReaderPackage } from './readerTestData'

async function savedSession(page: Page): Promise<WorkbenchSession> {
  const response = await page.request.get('/api/v1/workbench/session')
  expect(response.status()).toBe(200)
  return response.json()
}

test('actual browser close and API process restart retain imported references, notes, progress and Reader position', async ({ browserName, playwright }, testInfo) => {
  test.setTimeout(120_000)
  expect(browserName).toBe('chromium')
  const runtime = await RestartRuntime.start()
  const fixture = originalReaderPackage('restart')
  const errors: string[] = []
  try {
    const firstBrowser = await runtime.openBrowser(playwright.chromium)
    const page = firstBrowser.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(page)
    const initialWorkspace = await page.request.get('/api/v1/workspace').then(value => value.json())
    const imported = await importReaderPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const target = { course: fixture.course, lesson: fixture.lessons[0], view: 'lesson' }
    await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify(target))}`)
    await expect(page.locator('.reader-content.real-reader > h1')).toHaveText('从定义到证明与例题的完整推导')
    const definition = page.locator(`#block-${fixture.blocks[0].id}-r1`)
    await definition.getByText('原始 Markdown 与精确选文', { exact: true }).click()
    const original = definition.getByLabel('原始 Markdown：定义：残差与损失')
    await original.focus()
    await expect(original).toBeFocused()
    // Native Chrome readonly textareas support Select All; caret movement from
    // a focus-only empty selection is not equivalent to an editable textarea.
    await page.keyboard.press('Control+a')
    const selectedOriginal = await original.evaluate((element: HTMLTextAreaElement) => ({
      start: element.selectionStart, end: element.selectionEnd,
      quote: element.value.slice(element.selectionStart, element.selectionEnd),
      focused: document.activeElement === element,
      activeElement: document.activeElement?.getAttribute('aria-label') ?? document.activeElement?.tagName,
      statuses: Array.from(document.querySelectorAll('[role=status],.stale-notice')).map(node => node.textContent),
    }))
    writeFileSync(testInfo.outputPath('native-original-selection.json'), JSON.stringify(selectedOriginal, null, 2))
    expect(selectedOriginal.quote).toBe(fixture.bodies[fixture.blocks[0].id])
    await expect(page.getByRole('button', { name: '为当前选文记笔记', exact: true })).toBeEnabled()
    await page.getByRole('button', { name: '为当前选文记笔记', exact: true }).click()
    const notes = page.getByRole('dialog', { name: '笔记', exact: true })
    await notes.getByRole('button', { name: '用当前选文新建笔记', exact: true }).click()
    const noteText = '实际重启回读：🧠 中文 café é；引用、笔记正文和阅读操作分别验证。'
    await notes.getByLabel('笔记正文').fill(noteText)
    const creating = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/notes'))
    await notes.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
    const created = await creating
    expect(created.status()).toBe(201)
    const noteRef = await created.json()
    await expect(notes.getByText('笔记已保存到服务端', { exact: true })).toBeVisible()
    const noteBefore: Note = (await page.request.get('/api/v1/notes').then(value => value.json())).items.find((value: Note) => value.id === noteRef.id)
    expect(noteBefore.markdown).toBe(noteText)
    expect(noteBefore.anchor.ref).toEqual(fixture.blocks[0])
    expect(noteBefore.anchor.exact_quote).toBe(fixture.bodies[fixture.blocks[0].id])
    expect(noteBefore.anchor.start_codepoint).toBe(0)
    expect(noteBefore.anchor.end_codepoint).toBe(Array.from(noteBefore.anchor.exact_quote).length)
    const localDraftText = `${noteText}\n未同步的本机续写：只保留在草稿，不能替换已确认的服务端笔记。`
    await notes.getByLabel('笔记正文').fill(localDraftText)
    await expect(notes.getByText('本机草稿已保留；尚未同步为服务端笔记。', { exact: true })).toBeVisible()
    await notes.getByRole('button', { name: '关闭笔记', exact: true }).click()
    const preserveDraft = page.getByRole('dialog', { name: '保留未同步笔记', exact: true })
    await preserveDraft.getByRole('button', { name: '保留本机笔记草稿并关闭', exact: true }).click()
    await expect(notes).not.toBeVisible()

    const markingRead = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/learning/actions'))
    await page.getByRole('button', { name: '明确标记本节已读', exact: true }).click()
    const readResponse = await markingRead
    writeFileSync(testInfo.outputPath('read-after-note-response.json'), JSON.stringify({
      request: readResponse.request().postDataJSON(), status: readResponse.status(),
      response: await readResponse.json(),
      current_progress: await page.request.get('/api/v1/learning/progress').then(value => value.json()),
    }, null, 2))
    expect(readResponse.status()).toBe(200)
    await expect(page.getByRole('button', { name: '撤销本节已读标记', exact: true })).toBeEnabled()
    await page.getByRole('button', { name: '为此对象添加书签', exact: true }).click()
    await expect(page.getByRole('button', { name: '移除此对象书签', exact: true })).toBeEnabled()
    const progressBefore = await page.request.get('/api/v1/learning/progress').then(value => value.json())
    expect(progressBefore.readings).toContainEqual(expect.objectContaining({ ref: fixture.lessons[0], read: true }))
    expect(progressBefore.bookmarks).toContainEqual(expect.objectContaining({ ref: fixture.lessons[0], value: true }))

    // Save details/focus through real controls and scroll through a native wheel.
    const sourceSummary = definition.getByText('来源与提取诊断', { exact: true })
    await sourceSummary.click()
    await expect(definition.locator('.reader-sources')).toHaveAttribute('open', '')
    await sourceSummary.focus()
    const readerScroll = page.locator('.reader-scroll')
    await readerScroll.hover()
    await page.mouse.wheel(0, 480)
    await expect.poll(() => readerScroll.evaluate(node => node.scrollTop)).toBeGreaterThan(100)
    await expect.poll(async () => {
      const session = await savedSession(page)
      return session.tabs.find(tab => tab.id === session.active_tab_id)?.scroll_offset ?? 0
    }).toBeGreaterThan(100)
    await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
    const sessionBefore = await savedSession(page)
    const activeBefore = sessionBefore.tabs.find(tab => tab.id === sessionBefore.active_tab_id)!
    const actualOffsetBefore = await readerScroll.evaluate(node => node.scrollTop)
    expect(Math.abs(activeBefore.scroll_offset - actualOffsetBefore)).toBeLessThanOrEqual(2)
    const databaseBefore = runtime.databaseIdentity()
    const firstConnection = firstBrowser.browser()
    await runtime.closeBrowser()
    expect(firstConnection?.isConnected()).toBe(false)
    await runtime.restartApiAfterBrowserClosed()
    expect(runtime.generations).toHaveLength(2)
    expect(runtime.databaseIdentity()).toEqual(databaseBefore)

    const secondBrowser = await runtime.openBrowser(playwright.chromium)
    const restored = secondBrowser.pages()[0]
    restored.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(restored)
    await expect(restored.locator('.reader-content.real-reader > h1')).toHaveText('从定义到证明与例题的完整推导')
    await expect(restored.locator('.reader-content.real-reader svg').first()).toBeVisible()
    await expect.poll(() => restored.locator('.reader-scroll').evaluate(node => node.scrollTop)).toBeCloseTo(actualOffsetBefore, 0)
    const restoredDefinition = restored.locator(`#block-${fixture.blocks[0].id}-r1`)
    await expect(restoredDefinition.locator('.reader-original')).toHaveAttribute('open', '')
    await expect(restoredDefinition.locator('.reader-sources')).toHaveAttribute('open', '')
    await expect(restoredDefinition.getByText('来源与提取诊断', { exact: true })).toBeFocused()
    const sessionAfter = await savedSession(restored)
    const activeAfter = sessionAfter.tabs.find(tab => tab.id === sessionAfter.active_tab_id)!
    expect(activeAfter.context).toEqual(activeBefore.context)
    expect(sessionAfter.course_ref).toEqual(sessionBefore.course_ref)
    expect(sessionAfter.expanded_keys).toEqual(sessionBefore.expanded_keys)
    expect(await restored.request.get('/api/v1/workspace').then(value => value.json())).toEqual(initialWorkspace)
    expect(await restored.request.get('/api/v1/learning/progress').then(value => value.json())).toEqual(progressBefore)
    const noteAfter: Note = (await restored.request.get('/api/v1/notes').then(value => value.json())).items.find((value: Note) => value.id === noteRef.id)
    expect(noteAfter).toEqual(noteBefore)
    expect(await restored.request.get(`/api/v1/objects/${noteRef.id}/current`).then(value => value.json())).toEqual(noteRef)
    await restored.getByRole('button', { name: '查看笔记', exact: true }).click()
    const reopened = restored.getByRole('dialog', { name: '笔记', exact: true })
    await reopened.getByRole('button', { name: new RegExp('实际重启回读：') }).click()
    await expect(reopened.getByLabel('笔记正文')).toHaveValue(localDraftText)
    await expect(reopened.getByText('本机草稿已恢复并核对服务端基准。', { exact: true })).toBeVisible()
    await expect(reopened.locator('.note-editor blockquote')).toHaveText(noteBefore.anchor.exact_quote)
    await reopened.getByRole('button', { name: '关闭笔记', exact: true }).click()
    await restored.getByRole('dialog', { name: '保留未同步笔记', exact: true }).getByRole('button', { name: '保留本机笔记草稿并关闭', exact: true }).click()
    await restored.setViewportSize({ width: 390, height: 844 })
    const narrowReader = restored.locator('.reader-scroll')
    await narrowReader.hover()
    await restored.mouse.wheel(0, -10_000)
    await expect.poll(() => narrowReader.evaluate(node => node.scrollTop)).toBe(0)
    expect(await restored.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    expect(await narrowReader.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
    await restored.screenshot({ path: testInfo.outputPath('reader-restored-390.png') })
    expect(errors).toEqual([])
    writeFileSync(testInfo.outputPath('actual-reader-restart.json'), JSON.stringify({
      scope: 'Original synthetic package, actual browser closure and backend process restart; no state reset or memory substitutes.',
      process_generations: runtime.generations, same_database_inode: true,
      course_ref: fixture.course, active_ref: activeAfter.context.active_ref, note_ref: noteRef,
      saved_scroll_before: actualOffsetBefore, restored_scroll_after: activeAfter.scroll_offset,
      note_anchor: noteAfter.anchor, native_note_ui_readback: true,
      local_unsynced_note_draft_restored: true, server_note_not_overwritten: true,
      progress_unchanged: true,
      runtime_errors: errors,
    }, null, 2))
  } finally { await runtime.close() }
})
