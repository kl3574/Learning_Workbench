# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: reader.spec.ts >> historical course revisions stay in separate exact tabs and hash-mismatched links preserve unresolved reference
- Location: ../../tests/e2e/reader.spec.ts:171:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: locator('.real-reader')
Expected substring: "第二修订选文"
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toContainText" locator('.real-reader') with timeout 5000ms
  - waiting for locator('.real-reader')

```

```yaml
- link "跳到学习内容":
  - /url: "#reader-main"
- banner:
  - link "知径 学习工作台":
    - /url: "#"
    - strong: 知径
    - text: 学习工作台
  - button "搜索与命令 Ctrl ⇧ P"
  - button "切换导航栏" [expanded]: 目录
  - button "切换 Agent 栏" [expanded]: Agent
  - button "专注"
  - button "导入"
- complementary "课程导航":
  - text: 当前课程
  - button "正在解析所选课程"
  - paragraph: 从自己的学习目标开始
  - text: 暂无已读取的阅读记录 · 未诊断
  - button "查看教材修订"
  - navigation "学习主导航":
    - button "学习路线"
    - button "教材 含例题"
    - button "习题 含解答"
    - button "测试题"
  - region "当前教材目录":
    - heading "当前教材目录" [level=2]
    - status: 正在读取精确课程目录…
  - button "笔记"
  - button "创作"
  - button "设置"
- separator "导航栏宽度"
- main:
  - tablist "打开的学习对象":
    - tab "教材"
    - tab "已固定block_nativehistory_definition · r2" [selected]: ⌖ block_nativehistory_definition · r2
    - button "固定标签 block_nativehistory_definition · r2": ⌖
    - button "关闭标签 block_nativehistory_definition · r2": ×
  - status: 正在读取准确修订与正文…
- separator "Agent 栏宽度"
- complementary "Agent 助教":
  - heading "Agent" [level=2]
  - text: 未配置模型
  - group:
    - text: 当前上下文
    - paragraph
    - text: 修订 2 · 引用待解析
    - group: 查看引用范围
  - heading "围绕当前内容，一起思考" [level=3]
  - paragraph: 模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。
  - paragraph: 现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。
  - button "讲解" [pressed]
  - button "提示"
  - button "推导"
  - button "拓展"
  - text: 问题草稿
  - textbox "问题草稿":
    - /placeholder: 写下问题，草稿按当前对象保留…
  - text: 联网：未授权
  - button "发送 ↑" [disabled]
  - text: 草稿保留在本机浏览器，尚未发送。
- status: ✓ UI 会话已保存 内容修订 2 正常学习 · 本机
```

# Test source

```ts
  81  |   const offset = source.lastIndexOf('重复句子用于选择定位。')
  82  |   expect(note.anchor.start_codepoint).toBe(Array.from(source.slice(0, offset)).length)
  83  |   expect(note.anchor.end_codepoint - note.anchor.start_codepoint).toBe(Array.from(note.anchor.exact_quote).length)
  84  |   expect(note.anchor.ref).toEqual(fixture.blocks[0])
  85  |   await dialog.getByLabel('笔记正文').fill('编辑后仍绑定第二次重复选文')
  86  |   await dialog.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
  87  |   await expect(dialog.getByText('笔记已保存到服务端', { exact: true })).toBeVisible()
  88  |   await expect(dialog.locator('.note-identity')).toContainText('修订 2')
  89  |   await dialog.getByRole('button', { name: '删除此笔记', exact: true }).click()
  90  |   await dialog.getByRole('button', { name: '确认软删除笔记', exact: true }).click()
  91  |   await expect(dialog.getByText('笔记已从当前视图删除；历史引用保留。')).toBeVisible()
  92  |   expect((await page.request.get('/api/v1/notes').then(value => value.json())).items.some((item: Note) => item.id === ref.id)).toBe(false)
  93  |   const revisions = await page.request.get(`/api/v1/objects/${ref.id}/revisions`).then(value => value.json())
  94  |   expect(revisions.items.length).toBeGreaterThanOrEqual(2)
  95  | })
  96  | 
  97  | 
  98  | test('native source keyboard selection creates exact Markdown codepoints without rendered-text guessing', async ({ page }, info) => {
  99  |   const fixture = await openActual(page, 'nativekeyboard')
  100 |   const definition = page.locator(`#block-${fixture.blocks[0].id}-r1`)
  101 |   await definition.getByText('原始 Markdown 与精确选文', { exact: true }).click()
  102 |   const source = definition.getByLabel('原始 Markdown：定义：残差与损失')
  103 |   await source.focus()
  104 |   await expect(source).toBeFocused()
  105 |   // Chromium readonly textareas support Ctrl+A; Ctrl+Home + Shift+End leaves a collapsed caret.
  106 |   await page.keyboard.press('Control+A')
  107 | 
  108 |   await info.attach('native-textarea-selection', { body: JSON.stringify(await source.evaluate(node => ({ start: (node as HTMLTextAreaElement).selectionStart, end: (node as HTMLTextAreaElement).selectionEnd, focused: document.activeElement === node }))), contentType: 'application/json' })
  109 |   await expect(page.getByRole('button', { name: '为当前选文记笔记', exact: true })).toBeEnabled()
  110 |   await page.getByRole('button', { name: '为当前选文记笔记', exact: true }).click()
  111 |   const dialog = page.getByRole('dialog', { name: '笔记', exact: true })
  112 |   await dialog.getByRole('button', { name: '用当前选文新建笔记', exact: true }).click()
  113 |   await expect(dialog.locator('blockquote')).toHaveText(fixture.bodies[fixture.blocks[0].id])
  114 |   await page.setViewportSize({ width: 390, height: 844 })
  115 |   const close = dialog.getByRole('button', { name: '关闭笔记', exact: true })
  116 |   await expect(close).toBeVisible()
  117 |   const geometry = await dialog.evaluate(node => ({ width: node.clientWidth, scrollWidth: node.scrollWidth }))
  118 |   expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.width + 1)
  119 |   expect(await close.evaluate(node => { const box = node.getBoundingClientRect(); return node.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)) })).toBe(true)
  120 |   await page.screenshot({ path: info.outputPath('reader-exact-note-390.png') })
  121 | })
  122 | 
  123 | test('offline local note recovery and a real concurrent server revision show three-way comparison before CAS save', async ({ page }) => {
  124 |   const fixture = await openActual(page, 'nativeconflict')
  125 |   await selectRepeat(page, fixture)
  126 |   await page.getByRole('button', { name: '为当前选文记笔记', exact: true }).click()
  127 |   let dialog = page.getByRole('dialog', { name: '笔记', exact: true })
  128 |   await dialog.getByRole('button', { name: '用当前选文新建笔记', exact: true }).click()
  129 |   await dialog.getByLabel('笔记正文').fill('原基准笔记')
  130 |   const created = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/notes'))
  131 |   await dialog.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
  132 |   const baseRef = await (await created).json()
  133 |   await expect(dialog.getByText('笔记已保存到服务端', { exact: true })).toBeVisible()
  134 |   const base: Note = (await page.request.get('/api/v1/notes').then(value => value.json())).items.find((item: Note) => item.id === baseRef.id)
  135 |   await dialog.getByLabel('笔记正文').fill('本页离线编辑，必须保留')
  136 |   await expect(dialog.getByText('本机草稿已保留；尚未同步为服务端笔记。')).toBeVisible()
  137 |   await page.route('**/api/v1/notes**', route => route.abort('internetdisconnected'))
  138 |   await page.route(`**/api/v1/objects/${base.id}/current`, route => route.abort('internetdisconnected'))
  139 |   await page.reload()
  140 |   await expect(page.locator('.real-reader > h1')).toBeVisible()
  141 |   await page.getByRole('button', { name: '查看笔记', exact: true }).click()
  142 |   dialog = page.getByRole('dialog', { name: '笔记', exact: true })
  143 |   await dialog.getByRole('button', { name: `恢复本机笔记草稿 ${base.id}`, exact: true }).click()
  144 |   await expect(dialog.getByLabel('笔记正文')).toHaveValue('本页离线编辑，必须保留')
  145 |   await expect(dialog.getByRole('alert').first()).toBeVisible()
  146 |   await page.unroute('**/api/v1/notes**')
  147 |   await page.unroute(`**/api/v1/objects/${base.id}/current`)
  148 |   const changed = await page.evaluate(async ({ base, baseRef }) => {
  149 |     const auth = await fetch('/api/v1/session').then(value => value.json())
  150 |     const response = await fetch(`/api/v1/notes/${base.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf_token, 'Idempotency-Key': crypto.randomUUID(), 'If-Match': `"${baseRef.sha256}"` }, body: JSON.stringify({ ...base, revision: 2, markdown: '另一写入者的服务端笔记' }) })
  151 |     return { status: response.status, ref: await response.json() }
  152 |   }, { base, baseRef })
  153 |   expect(changed.status).toBe(200)
  154 |   const rejected = page.waitForResponse(value => value.request().method() === 'PATCH' && value.url().endsWith(`/api/v1/notes/${base.id}`))
  155 |   await dialog.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
  156 |   expect((await rejected).status()).toBe(412)
  157 |   await expect(dialog.getByRole('heading', { name: '笔记版本冲突', exact: true })).toBeVisible()
  158 |   const comparison = dialog.locator('.note-conflict')
  159 |   await expect(comparison).toContainText('原基准笔记')
  160 |   await expect(comparison).toContainText('本页离线编辑，必须保留')
  161 |   await expect(comparison).toContainText('另一写入者的服务端笔记')
  162 |   await dialog.getByRole('button', { name: '保留本地内容并采用新基准', exact: true }).click()
  163 |   await dialog.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
  164 |   await expect(dialog.getByText('笔记已保存到服务端', { exact: true })).toBeVisible()
  165 |   await expect(dialog.locator('.note-identity')).toContainText('修订 3')
  166 |   const actual: Note = (await page.request.get('/api/v1/notes').then(value => value.json())).items.find((item: Note) => item.id === base.id)
  167 |   expect(actual.markdown).toBe('本页离线编辑，必须保留')
  168 |   expect(actual.anchor).toEqual(base.anchor)
  169 | })
  170 | 
  171 | test('historical course revisions stay in separate exact tabs and hash-mismatched links preserve unresolved reference', async ({ page }, info) => {
  172 |   await bootstrap(page)
  173 |   const current = originalReaderPackage('nativehistory', 2, true)
  174 |   const old = originalReaderPackage('nativehistory', 1)
  175 |   const imported = await importReaderPackage(page, current)
  176 |   await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  177 |   const target = { course: current.course, lesson: current.lessons[0], block: current.blocks[0], view: 'lesson' }
  178 |   const diagnostic = observeReaderLoad(page)
  179 |   try {
  180 |     await page.goto(`/?reader=${encodeURIComponent(JSON.stringify(target))}`)
> 181 |     await expect(page.locator('.real-reader')).toContainText('第二修订选文')
      |                                                ^ Error: expect(locator).toContainText(expected) failed
  182 |   } catch (error) {
  183 |     await diagnostic.capture(info).catch(() => console.error('Historical Reader failure diagnostic could not be saved.'))
  184 |     throw error
  185 |   } finally { diagnostic.dispose() }
  186 |   const oldTarget = { course: old.course, lesson: old.lessons[0], block: old.blocks[0], view: 'lesson' }
  187 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  188 |   await page.goto(`/?reader=${encodeURIComponent(JSON.stringify(oldTarget))}`)
  189 |   await expect(page.locator('.real-reader')).toContainText('正在阅读旧修订')
  190 |   await expect(page.locator('.real-reader')).toContainText('选文甲')
  191 |   await expect(page.getByRole('tab', { name: /定义：残差与损失 · r1/ })).toBeVisible()
  192 |   await expect(page.getByRole('tab', { name: /block_nativehistory_definition · r2/ })).toBeVisible()
  193 |   await page.getByRole('tab', { name: /block_nativehistory_definition · r2/ }).click()
  194 |   await expect(page.locator('.real-reader')).toContainText('第二修订选文')
  195 |   await page.getByRole('button', { name: '查看教材修订', exact: true }).click()
  196 |   const revisions = page.getByRole('dialog', { name: '教材修订', exact: true })
  197 |   await expect(revisions.getByRole('button', { name: /教材修订 1/ })).toBeVisible()
  198 |   await expect(revisions.getByRole('button', { name: /教材修订 2/ })).toBeVisible()
  199 |   await revisions.getByRole('button', { name: '关闭教材修订', exact: true }).click()
  200 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  201 |   const invalid = { ...oldTarget, block: { ...oldTarget.block, sha256: 'b'.repeat(64) } }
  202 |   await page.goto(`/?reader=${encodeURIComponent(JSON.stringify(invalid))}`)
  203 |   await expect(page.getByRole('heading', { name: '无法打开此精确链接', exact: true })).toBeVisible()
  204 |   await expect(page.getByRole('alert')).toContainText('不一致')
  205 |   await expect.poll(async () => { const value = await page.request.get('/api/v1/workbench/session').then(response => response.json()); return value.tabs.find((tab: {id:string}) => tab.id === value.active_tab_id)?.context.active_ref }).toEqual(current.blocks[0])
  206 | })
  207 | 
  208 | 
  209 | test('a private original authorized before a cross-profile role decrease cannot trigger a late browser download', async ({ page, browser }) => {
  210 |   test.setTimeout(60_000)
  211 |   await bootstrap(page)
  212 |   const root = resolve(import.meta.dirname, '../..')
  213 |   const bytes = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'import sys;from tests.document_fixtures import docx_fixture;sys.stdout.buffer.write(docx_fixture())'], { cwd: root })
  214 |   await page.getByRole('button', { name: '导入', exact: true }).click()
  215 |   const imported = page.getByRole('dialog', { name: '导入', exact: true })
  216 |   await imported.getByLabel('解析格式').selectOption('docx')
  217 |   await imported.getByLabel('选择导入文件').setInputFiles({ name: 'synthetic-reader-source.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: bytes })
  218 |   await imported.getByRole('button', { name: '上传并生成预览', exact: true }).click()
  219 |   await expect(imported.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  220 |   for (const checkbox of await imported.getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  221 |   await imported.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  222 |   await imported.getByRole('button', { name: '确认导入当前候选', exact: true }).click()
  223 |   await imported.getByRole('button', { name: '打开已导入课程', exact: true }).click()
  224 |   await page.getByRole('button', { name: '继续阅读 →', exact: true }).click()
  225 |   const panel = page.locator('.reader-sources').first()
  226 |   await panel.locator('summary').click()
  227 |   await expect(panel.getByText('原件需要作者角色。', { exact: false })).toBeVisible()
  228 |   await panel.getByRole('button', { name: '切换为作者以读取原件', exact: true }).click()
  229 |   await expect(panel.getByRole('button', { name: '下载受控原件', exact: true })).toBeVisible()
  230 |   const alternate = await browser.newContext({ storageState: await page.context().storageState() })
  231 |   let release!: () => void
  232 |   try {
  233 |     const second = await alternate.newPage()
  234 |     await second.goto('/')
  235 |     await expect(second.getByText('✓ UI 会话已保存')).toBeVisible()
  236 |     await second.getByRole('button', { name: '导入', exact: true }).click()
  237 |     const secondDialog = second.getByRole('dialog', { name: '导入', exact: true })
  238 |     await expect(secondDialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  239 |     let loaded!: () => void
  240 |     const responseLoaded = new Promise<void>(resolve => { loaded = resolve })
  241 |     const held = new Promise<void>(resolve => { release = resolve })
  242 |     let artifactUrl = ''
  243 |     await page.route('**/api/v1/artifacts/*/download', async route => { const response = await route.fetch(); expect(response.status()).toBe(200); artifactUrl = route.request().url(); loaded(); await held; await route.fulfill({ response }) })
  244 |     const downloads: string[] = []; page.on('download', value => downloads.push(value.suggestedFilename()))
  245 |     await panel.getByRole('button', { name: '下载受控原件', exact: true }).click()
  246 |     await responseLoaded
  247 |     const changed = second.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/session/role'))
  248 |     await secondDialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  249 |     expect((await changed).status()).toBe(200)
  250 |     expect((await page.request.get(artifactUrl)).status()).toBe(403)
  251 |     release()
  252 |     await expect(panel.getByRole('alert')).toBeVisible()
  253 |     await expect(panel.getByRole('button', { name: '下载受控原件', exact: true })).toBeEnabled()
  254 |     expect(downloads).toEqual([])
  255 |   } finally { release?.(); await alternate.close() }
  256 | })
  257 | 
```