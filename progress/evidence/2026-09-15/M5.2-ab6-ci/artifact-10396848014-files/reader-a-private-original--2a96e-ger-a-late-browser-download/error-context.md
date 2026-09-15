# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: reader.spec.ts >> a private original authorized before a cross-profile role decrease cannot trigger a late browser download
- Location: ../../tests/e2e/reader.spec.ts:209:1

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 60000ms exceeded.
Call log:
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByLabel('解析格式')

```

# Page snapshot

```yaml
- generic [ref=f2e3]:
  - link "跳到学习内容" [ref=f2e4] [cursor=pointer]:
    - /url: "#reader-main"
  - banner [ref=f2e5]:
    - link "知径 学习工作台" [ref=f2e6] [cursor=pointer]:
      - /url: "#"
      - generic [aria-hidden] [ref=f2e7]: 径
      - strong [ref=f2e8]: 知径
      - generic [ref=f2e9]: 学习工作台
    - button "搜索与命令 Ctrl ⇧ P" [ref=f2e10] [cursor=pointer]:
      - generic [aria-hidden] [ref=f2e11]: ⌕
      - text: 搜索与命令
      - generic [ref=f2e12]: Ctrl ⇧ P
    - generic [ref=f2e13]:
      - button "切换导航栏" [expanded] [ref=f2e14] [cursor=pointer]: 目录
      - button "切换 Agent 栏" [expanded] [ref=f2e15] [cursor=pointer]: Agent
      - button "专注" [ref=f2e16] [cursor=pointer]
      - button "导入" [active] [ref=f2e17] [cursor=pointer]
  - status [ref=f2e18]: 当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。
  - generic [ref=f2e19]:
    - complementary "课程导航" [ref=f2e20]:
      - generic [ref=f2e21]:
        - generic [ref=f2e22]:
          - generic [ref=f2e23]: 学习路线
          - heading "目标与任务顺序" [level=2] [ref=f2e24]
          - paragraph [ref=f2e25]: 阅读、自报、参与和独立证据分别记录。
          - button "学习目标与基础" [ref=f2e26] [cursor=pointer]
        - navigation "学习主导航" [ref=f2e27]:
          - button "学习路线" [ref=f2e28] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e29]: ↗
          - button "教材 含例题" [ref=f2e31] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e32]: ▤
            - generic [ref=f2e33]: 教材
            - generic [ref=f2e34]: 含例题
          - button "习题 含解答" [ref=f2e35] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e36]: ✎
            - generic [ref=f2e37]: 习题
            - generic [ref=f2e38]: 含解答
          - button "测试题" [ref=f2e39] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e40]: ☑
        - region "学习路线目录" [ref=f2e42]:
          - generic [ref=f2e43]:
            - heading "路线与历史修订" [level=2] [ref=f2e44]
            - button "刷新路线" [ref=f2e45] [cursor=pointer]
          - generic [ref=f2e46]:
            - paragraph [ref=f2e47]: 尚无正式学习路线。
            - list
            - generic [ref=f2e48]:
              - button "创建路线" [ref=f2e49] [cursor=pointer]
              - button "学习建议" [ref=f2e50] [cursor=pointer]
              - button "查看概念与技能证据" [ref=f2e51] [cursor=pointer]
        - generic [ref=f2e52]:
          - button "笔记" [ref=f2e53] [cursor=pointer]
          - button "创作" [ref=f2e54] [cursor=pointer]
          - button "设置" [ref=f2e55] [cursor=pointer]
    - separator "导航栏宽度" [ref=f2e56]
    - main [ref=f2e57]:
      - tablist "打开的学习对象" [ref=f2e58]:
        - tab "学习路线" [selected] [ref=f2e59] [cursor=pointer]
      - generic [ref=f2e60]:
        - heading "从学习目标开始" [level=1] [ref=f2e61]
        - paragraph [ref=f2e62]: 路线把真实教材、练习和测试排成任务顺序。先修提醒帮助选择顺序，完成标记不代表掌握。
        - paragraph [ref=f2e63]: 尚无正式学习路线。
        - generic [ref=f2e64]:
          - button "创建路线" [ref=f2e65] [cursor=pointer]
          - button "学习建议" [ref=f2e66] [cursor=pointer]
          - button "学习目标与基础" [ref=f2e67] [cursor=pointer]
          - button "查看概念与技能证据" [ref=f2e68] [cursor=pointer]
        - list
    - separator "Agent 栏宽度" [ref=f2e69]
    - complementary "Agent 助教" [ref=f2e70]:
      - generic [ref=f2e71]:
        - generic [ref=f2e72]:
          - heading "Agent" [level=2] [ref=f2e73]
          - generic [ref=f2e74]: 未配置模型
        - group [ref=f2e75]:
          - generic "当前上下文" [ref=f2e76] [cursor=pointer]
          - paragraph [ref=f2e77]: 尚未选择学习对象
        - generic [ref=f2e78]:
          - generic [aria-hidden] [ref=f2e79]: ✦
          - heading "围绕当前内容，一起思考" [level=3] [ref=f2e80]
          - paragraph [ref=f2e81]: 模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。
          - paragraph [ref=f2e82]: 现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。
        - generic [ref=f2e83]:
          - generic "教学意图" [ref=f2e84]:
            - button "讲解" [pressed] [ref=f2e85] [cursor=pointer]
            - button "提示" [ref=f2e86] [cursor=pointer]
            - button "推导" [ref=f2e87] [cursor=pointer]
            - button "拓展" [ref=f2e88] [cursor=pointer]
          - generic [ref=f2e89]: 问题草稿
          - textbox "问题草稿" [ref=f2e90]:
            - /placeholder: 写下问题，草稿按当前对象保留…
          - generic [ref=f2e91]:
            - generic [ref=f2e92]: 联网：未授权
            - button "发送 ↑" [disabled] [ref=f2e93]
          - generic [ref=f2e94]: 草稿保留在本机浏览器，尚未发送。
  - status [ref=f2e95]:
    - generic [ref=f2e96]: ✓ UI 会话已保存
    - generic [ref=f2e97]: 尚未选择对象
    - generic [ref=f2e98]: 正常学习 · 本机
```

# Test source

```ts
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
  181 |     await expect(page.locator('.real-reader')).toContainText('第二修订选文')
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
> 216 |   await imported.getByLabel('解析格式').selectOption('docx')
      |                                     ^ Error: locator.selectOption: Test timeout of 60000ms exceeded.
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