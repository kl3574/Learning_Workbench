# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: imports.spec.ts >> local encoding choice preserves the failed original and creates a separately confirmed UTF-8 import
- Location: ../../tests/e2e/imports.spec.ts:311:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('dialog', { name: '导入', exact: true }).getByText('预览已就绪，等待确认', { exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('dialog', { name: '导入', exact: true }).getByText('预览已就绪，等待确认', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByText('预览已就绪，等待确认', { exact: true })

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
  - text: 学习路线
  - heading "目标与任务顺序" [level=2]
  - paragraph: 阅读、自报、参与和独立证据分别记录。
  - button "学习目标与基础"
  - navigation "学习主导航":
    - button "学习路线"
    - button "教材 含例题"
    - button "习题 含解答"
    - button "测试题"
  - region "学习路线目录":
    - heading "路线与历史修订" [level=2]
    - button "刷新路线"
    - paragraph: 尚无正式学习路线。
    - list
    - button "创建路线"
    - button "学习建议"
    - button "查看概念与技能证据"
  - button "笔记"
  - button "创作"
  - button "设置"
- separator "导航栏宽度"
- main:
  - tablist "打开的学习对象":
    - tab "学习路线" [selected]
  - heading "从学习目标开始" [level=1]
  - paragraph: 路线把真实教材、练习和测试排成任务顺序。先修提醒帮助选择顺序，完成标记不代表掌握。
  - paragraph: 尚无正式学习路线。
  - button "创建路线"
  - button "学习建议"
  - button "学习目标与基础"
  - button "查看概念与技能证据"
  - list
- separator "Agent 栏宽度"
- complementary "Agent 助教":
  - heading "Agent" [level=2]
  - text: 本地任务 · 明确授权
  - group:
    - text: 当前上下文
    - paragraph: 尚未选择学习对象
  - heading "先选择真实学习对象" [level=3]
  - paragraph: 尚无可解析的学习对象；问题草稿仍可保留。
  - button "讲解" [pressed]
  - button "提示"
  - button "推导"
  - button "拓展"
  - text: 问题草稿
  - textbox "问题草稿":
    - /placeholder: 写下问题，草稿按当前对象保留…
  - text: 联网：未授权
  - button "创建本次问答任务 ↑" [disabled]
  - text: 本机草稿保留；发送与结果以本次任务记录为准。
- status: ✓ UI 会话已保存 尚未选择对象 正常学习 · 本机
```

# Test source

```ts
  1   | import { expect, test, type Locator, type Page, type TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2   | import { createHash } from 'node:crypto'
  3   | import { execFileSync } from 'node:child_process'
  4   | import { resolve } from 'node:path'
  5   | import { writeFileSync } from 'node:fs'
  6   | import { bootstrap } from './helpers'
  7   | 
  8   | function originalSyntheticAuthorPackage() {
  9   |   const root = resolve(import.meta.dirname, '../..')
  10  |   // Generate original test bytes using the sole-spec models. The package goes
  11  |   // through the same native upload/worker/confirmation as a user-selected file.
  12  |   return execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', String.raw`
  13  | import io, sys, zipfile
  14  | from packages.contracts import domain_models as dm
  15  | from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
  16  | def ref(value):
  17  |     return dm.ContentRef(entity=value.entity,id=value.id,revision=value.revision,sha256=metadata_sha256(value))
  18  | body=b'Synthetic author-package public body.\n'
  19  | block=dm.ContentBlock(id='block_native_author',revision=1,kind='text',title='Synthetic author block',body_path='content/body.md',body_sha256=sha256_bytes(body))
  20  | lesson=dm.Lesson(id='lesson_native_author',revision=1,title='Synthetic author lesson',objectives=[],block_refs=[ref(block)])
  21  | concept=dm.Concept(id='concept_native_author',revision=1,title='Synthetic concept')
  22  | course=dm.Course(id='course_native_author',revision=1,title='Synthetic author course',audience='Native test',lesson_refs=[ref(lesson)],concept_refs=[ref(concept)])
  23  | question=dm.QuestionPublic(id='question_native_author',revision=1,kind='text_blank',stem_markdown='Synthetic public question',concept_ids=[concept.id],skill='recall',exposure_group='exposure_native_author',input_instructions='Synthetic answer')
  24  | solution=dm.SolutionPrivate(id='solution_native_author',revision=1,question_ref=ref(question),grading_kind='text_normalized',accepted_answers=['synthetic-private-solution-marker'],solution_markdown='synthetic-private-solution-marker',review_status='needs_review')
  25  | payloads={'course.json':canonical_bytes(course),'lessons/lesson.json':canonical_bytes(lesson),'blocks/block.json':canonical_bytes(block),'concepts.json':canonical_bytes([concept.model_dump(mode='json')]),'questions/public.jsonl':canonical_bytes(question)+b'\n','private/solutions.jsonl':canonical_bytes(solution)+b'\n','content/body.md':body}
  26  | manifest=dm.Manifest(package_id='package_native_author',profile='author',created_at='2026-09-14T00:00:00Z',files=[dm.FileEntry(path=path,size=len(data),sha256=sha256_bytes(data),media_type='text/markdown' if path.endswith('.md') else 'application/json',visibility='author_private' if path.startswith('private/') else 'learner') for path,data in payloads.items()])
  27  | out=io.BytesIO()
  28  | with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
  29  |     archive.writestr('manifest.json',canonical_bytes(manifest))
  30  |     for path,data in payloads.items(): archive.writestr(path,data)
  31  | sys.stdout.buffer.write(out.getvalue())
  32  | `], { cwd: root })
  33  | }
  34  | 
  35  | async function openImports(page: Page) {
  36  |   // A cold reload may finish navigation before React has attached shortcuts.
  37  |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  38  |   await page.keyboard.press('Control+Shift+P')
  39  |   await page.getByRole('dialog', { name: '命令面板' }).getByRole('button', { name: /^导入/ }).click()
  40  |   const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  41  |   await expect(dialog.getByText('操作角色：学习者')).toBeVisible()
  42  |   return dialog
  43  | }
  44  | 
  45  | async function assertImportHeaderVisible(dialog: Locator, testInfo: TestInfo, label: string, scrolled = false) {
  46  |   const metrics = await dialog.evaluate(element => {
  47  |     const inner = element.querySelector<HTMLElement>('.dialog-inner')!
  48  |     const workflow = element.querySelector<HTMLElement>('.import-workflow')!
  49  |     const header = inner.querySelector<HTMLElement>(':scope > header')!
  50  |     const title = header.querySelector<HTMLElement>('h2')!
  51  |     const close = header.querySelector<HTMLElement>('button')!
  52  |     const box = (node: Element) => {
  53  |       const { x, y, width, height, top, bottom, left, right } = node.getBoundingClientRect()
  54  |       return { x, y, width, height, top, bottom, left, right }
  55  |     }
  56  |     const hitTests = (node: HTMLElement) => {
  57  |       const rect = node.getBoundingClientRect()
  58  |       const cx = rect.left + rect.width / 2
  59  |       const cy = rect.top + rect.height / 2
  60  |       // Sample the center and axial edges, inside the rounded button shape.
  61  |       return [[cx, cy], [cx, rect.top + 2], [cx, rect.bottom - 2], [rect.left + 2, cy], [rect.right - 2, cy]]
  62  |         .map(([x, y]) => { const hit = document.elementFromPoint(x, y); return { x, y, tag: hit?.tagName ?? null, within: node.contains(hit) } })
  63  |     }
  64  |     const scroll = (node: Element) => ({ top: node.scrollTop, height: node.scrollHeight, client: node.clientHeight, overflow: getComputedStyle(node).overflowY })
  65  |     return { viewport: { width: innerWidth, height: innerHeight }, dialog: box(element), header: box(header), workflow: box(workflow), title: box(title), close: box(close), titleHits: hitTests(title), closeHits: hitTests(close), scrolling: { dialog: scroll(element), inner: scroll(inner), workflow: scroll(workflow) } }
  66  |   })
  67  |   writeFileSync(testInfo.outputPath(`imports-layout-${label}.json`), JSON.stringify(metrics, null, 2))
  68  |   if (scrolled) expect(metrics.scrolling.workflow.top + metrics.scrolling.inner.top + metrics.scrolling.dialog.top).toBeGreaterThan(0)
  69  |   expect(metrics.scrolling.dialog.top).toBe(0)
  70  |   expect(metrics.scrolling.inner.top).toBe(0)
  71  |   expect(metrics.workflow.top).toBeGreaterThanOrEqual(metrics.header.bottom - 1)
  72  |   expect(metrics.header.top).toBeGreaterThanOrEqual(metrics.dialog.top)
  73  |   expect(metrics.header.bottom).toBeLessThanOrEqual(metrics.dialog.bottom)
  74  |   for (const target of [metrics.title, metrics.close]) {
  75  |     expect(target.top).toBeGreaterThanOrEqual(0)
  76  |     expect(target.bottom).toBeLessThanOrEqual(metrics.viewport.height)
  77  |     expect(target.left).toBeGreaterThanOrEqual(0)
  78  |     expect(target.right).toBeLessThanOrEqual(metrics.viewport.width)
  79  |   }
  80  |   expect(metrics.titleHits.every(hit => hit.within)).toBe(true)
  81  |   expect(metrics.closeHits.every(hit => hit.within)).toBe(true)
  82  | }
  83  | 
  84  | async function upload(page: Page, filename: string, text: string, kind: string) {
  85  |   const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  86  |   await dialog.getByLabel('解析格式').selectOption(kind)
  87  |   await dialog.getByLabel('选择导入文件').setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(text) })
  88  |   const staged = page.waitForResponse(response => response.url().endsWith('/api/v1/imports') && response.request().method() === 'POST')
  89  |   await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  90  |   const response = await staged
  91  |   expect(response.status()).toBe(202)
  92  |   const result = await response.json()
> 93  |   await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
      |                                                                 ^ Error: expect(locator).toBeVisible() failed
  94  |   await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
  95  |   await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
  96  |   return result
  97  | }
  98  | 
  99  | async function acceptAndCommit(page: Page) {
  100 |   const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  101 |   for (const checkbox of await dialog.getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  102 |   await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  103 |   const committed = page.waitForResponse(response => /\/api\/v1\/imports\/[^/]+\/commit$/.test(response.url()) && response.request().method() === 'POST')
  104 |   await dialog.getByRole('button', { name: '确认导入当前候选' }).click()
  105 |   const response = await committed
  106 |   expect(response.status()).toBe(200)
  107 |   await expect(dialog.getByRole('heading', { name: '导入已提交', exact: true })).toBeVisible()
  108 |   return response.json()
  109 | }
  110 | 
  111 | test('real Markdown upload stays staged, previews and downloads exact bytes, restores and commits exact course refs', async ({ page }, testInfo) => {
  112 |   await bootstrap(page)
  113 |   const original = '# 原生导入验收\n\n这是独立测试写入的合成 Markdown 原件，不是内置 UI 示例。\n\n$$x^2 \\ge 0$$\n'
  114 |   const dialog = await openImports(page)
  115 |   const before = await page.request.get('/api/v1/courses?limit=100').then(response => response.json())
  116 |   const staged = await upload(page, 'native-import.md', original, 'markdown')
  117 |   expect(staged.input_sha256).toBe(createHash('sha256').update(original).digest('hex'))
  118 |   expect((await page.request.get('/api/v1/courses?limit=100').then(response => response.json())).items).toEqual(before.items)
  119 |   await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toBeDisabled()
  120 |   // A parser may place course/lesson metadata before its first block; use the
  121 |   // actual preview selector rather than deriving IDs or substituting a fixture.
  122 |   for (let index = 0; index < 10 && !(await dialog.getByLabel('当前候选正文').innerText()).includes('这是独立测试写入的合成 Markdown 原件'); index++) {
  123 |     const next = dialog.getByRole('button', { name: '下一候选' })
  124 |     if (await next.isDisabled()) break
  125 |     await next.click()
  126 |     await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
  127 |     await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
  128 |   }
  129 |   await expect(dialog.getByLabel('当前候选正文')).toContainText('这是独立测试写入的合成 Markdown 原件')
  130 |   const downloadPromise = page.waitForEvent('download')
  131 |   await dialog.getByRole('button', { name: '下载受控原件' }).click()
  132 |   const download = await downloadPromise
  133 |   const stream = await download.createReadStream()
  134 |   const chunks: Buffer[] = []
  135 |   if (!stream) throw new Error('Download stream was unavailable')
  136 |   for await (const chunk of stream) chunks.push(Buffer.from(chunk))
  137 |   expect(Buffer.concat(chunks).toString('utf8')).toBe(original)
  138 |   const candidateSelect = dialog.getByLabel('选择预览候选')
  139 |   const candidateIds = await candidateSelect.locator('option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))
  140 |   for (const id of candidateIds) {
  141 |     await candidateSelect.selectOption(id)
  142 |     await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
  143 |     if (await dialog.locator('.formula').count()) break
  144 |   }
  145 |   await expect(dialog.locator('.formula').first()).toHaveAttribute('aria-label', '公式：x^2 \\ge 0')
  146 |   await expect(dialog.locator('svg').first()).toBeVisible()
  147 |   await expect(dialog.locator('.math-error')).toHaveCount(0)
  148 |   const cached = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith('learning-workbench.import-id.v1:')))
  149 |   expect(cached).toHaveLength(1)
  150 |   expect(JSON.parse(cached[0][1])).toEqual([staged.import_id, staged.job.id])
  151 |   expect(JSON.stringify(cached)).not.toContain('原生导入验收')
  152 |   await page.reload()
  153 |   await openImports(page)
  154 |   await dialog.getByRole('button', { name: `恢复 ${staged.import_id}`, exact: true }).click()
  155 |   await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  156 |   await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
  157 |   const restoredSelector = dialog.getByLabel('选择预览候选')
  158 |   const restoredIds = await restoredSelector.locator('option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))
  159 |   for (const id of restoredIds) {
  160 |     await restoredSelector.selectOption(id)
  161 |     await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
  162 |     if (await dialog.getByText(/包含.*个小节候选/).count()) break
  163 |   }
  164 |   await expect(dialog.getByText(/包含.*个小节候选/)).toBeVisible()
  165 |   await dialog.getByText('候选修订与校验信息', { exact: true }).click()
  166 |   const originalCourseId = await dialog.getByText('候选对象 ID', { exact: true }).evaluate(element => element.nextElementSibling?.textContent)
  167 |   expect(originalCourseId).toMatch(/^course_/)
  168 |   const mappedCourseId = `${originalCourseId}_mapped`
  169 |   await dialog.getByText('确认对象 ID 映射', { exact: true }).click()
  170 |   await dialog.getByRole('button', { name: '添加精确映射' }).click()
  171 |   await dialog.getByLabel('原对象 ID', { exact: true }).fill(originalCourseId!)
  172 |   await dialog.getByLabel('新对象 ID', { exact: true }).fill(mappedCourseId)
  173 |   const receipt = await acceptAndCommit(page)
  174 |   expect(receipt.course_refs).toHaveLength(1)
  175 |   const ref = receipt.course_refs[0]
  176 |   expect(ref.entity).toBe('course')
  177 |   expect(ref.id).toBe(mappedCourseId)
  178 |   await expect(dialog.locator('.import-result')).toContainText(ref.sha256)
  179 |   const courseResponse = await page.request.get(`/api/v1/courses/${ref.id}?revision=${ref.revision}`)
  180 |   expect(courseResponse.status()).toBe(200)
  181 |   expect(courseResponse.headers().etag).toBe(`"${ref.sha256}"`)
  182 |   await expect(dialog.locator('.import-result')).toContainText((await courseResponse.json()).title)
  183 |   await assertImportHeaderVisible(dialog, testInfo, 'committed-1440')
  184 |   await page.screenshot({ path: testInfo.outputPath('imports-committed-result-1440.png') })
  185 |   await dialog.getByRole('button', { name: '完成并关闭导入' }).click()
  186 |   await expect(dialog).toBeHidden()
  187 |   await expect(page.getByRole('heading', { name: '从学习目标开始', exact: true })).toBeVisible()
  188 | })
  189 | 
  190 | test('safe HTML warning requires explicit acceptance and native cancel leaves courses untouched', async ({ page }, testInfo) => {
  191 |   await bootstrap(page)
  192 |   await page.setViewportSize({ width: 390, height: 844 })
  193 |   const dialog = await openImports(page)
```