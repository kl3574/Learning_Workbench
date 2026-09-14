import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { bootstrap } from './helpers'

function originalSyntheticAuthorPackage() {
  const root = resolve(import.meta.dirname, '../..')
  // Generate original test bytes using the sole-spec models. The package goes
  // through the same native upload/worker/confirmation as a user-selected file.
  return execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', String.raw`
import io, sys, zipfile
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
def ref(value):
    return dm.ContentRef(entity=value.entity,id=value.id,revision=value.revision,sha256=metadata_sha256(value))
body=b'Synthetic author-package public body.\n'
block=dm.ContentBlock(id='block_native_author',revision=1,kind='text',title='Synthetic author block',body_path='content/body.md',body_sha256=sha256_bytes(body))
lesson=dm.Lesson(id='lesson_native_author',revision=1,title='Synthetic author lesson',objectives=[],block_refs=[ref(block)])
concept=dm.Concept(id='concept_native_author',revision=1,title='Synthetic concept')
course=dm.Course(id='course_native_author',revision=1,title='Synthetic author course',audience='Native test',lesson_refs=[ref(lesson)],concept_refs=[ref(concept)])
question=dm.QuestionPublic(id='question_native_author',revision=1,kind='text_blank',stem_markdown='Synthetic public question',concept_ids=[concept.id],skill='recall',exposure_group='exposure_native_author',input_instructions='Synthetic answer')
solution=dm.SolutionPrivate(id='solution_native_author',revision=1,question_ref=ref(question),grading_kind='text_normalized',accepted_answers=['synthetic-private-solution-marker'],solution_markdown='synthetic-private-solution-marker',review_status='needs_review')
payloads={'course.json':canonical_bytes(course),'lessons/lesson.json':canonical_bytes(lesson),'blocks/block.json':canonical_bytes(block),'concepts.json':canonical_bytes([concept.model_dump(mode='json')]),'questions/public.jsonl':canonical_bytes(question)+b'\n','private/solutions.jsonl':canonical_bytes(solution)+b'\n','content/body.md':body}
manifest=dm.Manifest(package_id='package_native_author',profile='author',created_at='2026-09-14T00:00:00Z',files=[dm.FileEntry(path=path,size=len(data),sha256=sha256_bytes(data),media_type='text/markdown' if path.endswith('.md') else 'application/json',visibility='author_private' if path.startswith('private/') else 'learner') for path,data in payloads.items()])
out=io.BytesIO()
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
    archive.writestr('manifest.json',canonical_bytes(manifest))
    for path,data in payloads.items(): archive.writestr(path,data)
sys.stdout.buffer.write(out.getvalue())
`], { cwd: root })
}

async function openImports(page: Page) {
  // A cold reload may finish navigation before React has attached shortcuts.
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.keyboard.press('Control+Shift+P')
  await page.getByRole('dialog', { name: '命令面板' }).getByRole('button', { name: /^导入/ }).click()
  const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await expect(dialog.getByText('操作角色：学习者')).toBeVisible()
  return dialog
}

async function upload(page: Page, filename: string, text: string, kind: string) {
  const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await dialog.getByLabel('解析格式').selectOption(kind)
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(text) })
  const staged = page.waitForResponse(response => response.url().endsWith('/api/v1/imports') && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  const response = await staged
  expect(response.status()).toBe(202)
  const result = await response.json()
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
  await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
  return result
}

async function acceptAndCommit(page: Page) {
  const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  for (const checkbox of await dialog.getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  const committed = page.waitForResponse(response => /\/api\/v1\/imports\/[^/]+\/commit$/.test(response.url()) && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '确认导入当前候选' }).click()
  const response = await committed
  expect(response.status()).toBe(200)
  await expect(dialog.getByRole('heading', { name: '导入已提交', exact: true })).toBeVisible()
  return response.json()
}

test('real Markdown upload stays staged, previews and downloads exact bytes, restores and commits exact course refs', async ({ page }, testInfo) => {
  await bootstrap(page)
  const original = '# 原生导入验收\n\n这是独立测试写入的合成 Markdown 原件，不是内置 UI 示例。\n\n$$x^2 \\ge 0$$\n'
  const dialog = await openImports(page)
  const before = await page.request.get('/api/v1/courses?limit=100').then(response => response.json())
  const staged = await upload(page, 'native-import.md', original, 'markdown')
  expect(staged.input_sha256).toBe(createHash('sha256').update(original).digest('hex'))
  expect((await page.request.get('/api/v1/courses?limit=100').then(response => response.json())).items).toEqual(before.items)
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toBeDisabled()
  // A parser may place course/lesson metadata before its first block; use the
  // actual preview selector rather than deriving IDs or substituting a fixture.
  for (let index = 0; index < 10 && !(await dialog.getByLabel('当前候选正文').innerText()).includes('这是独立测试写入的合成 Markdown 原件'); index++) {
    const next = dialog.getByRole('button', { name: '下一候选' })
    if (await next.isDisabled()) break
    await next.click()
    await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
    await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
  }
  await expect(dialog.getByLabel('当前候选正文')).toContainText('这是独立测试写入的合成 Markdown 原件')
  const downloadPromise = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载受控原件' }).click()
  const download = await downloadPromise
  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  if (!stream) throw new Error('Download stream was unavailable')
  for await (const chunk of stream) chunks.push(Buffer.from(chunk))
  expect(Buffer.concat(chunks).toString('utf8')).toBe(original)
  const candidateSelect = dialog.getByLabel('选择预览候选')
  const candidateIds = await candidateSelect.locator('option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))
  for (const id of candidateIds) {
    await candidateSelect.selectOption(id)
    await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
    if (await dialog.locator('.formula').count()) break
  }
  await expect(dialog.locator('.formula').first()).toHaveAttribute('aria-label', '公式：x^2 \\ge 0')
  await expect(dialog.locator('svg').first()).toBeVisible()
  await expect(dialog.locator('.math-error')).toHaveCount(0)
  const cached = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith('learning-workbench.import-id.v1:')))
  expect(cached).toHaveLength(1)
  expect(JSON.parse(cached[0][1])).toEqual([staged.import_id, staged.job.id])
  expect(JSON.stringify(cached)).not.toContain('原生导入验收')
  await page.reload()
  await openImports(page)
  await dialog.getByRole('button', { name: `恢复 ${staged.import_id}`, exact: true }).click()
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
  const restoredSelector = dialog.getByLabel('选择预览候选')
  const restoredIds = await restoredSelector.locator('option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))
  for (const id of restoredIds) {
    await restoredSelector.selectOption(id)
    await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
    if (await dialog.getByText(/包含.*个小节候选/).count()) break
  }
  await expect(dialog.getByText(/包含.*个小节候选/)).toBeVisible()
  await dialog.getByText('候选修订与校验信息', { exact: true }).click()
  const originalCourseId = await dialog.getByText('候选对象 ID', { exact: true }).evaluate(element => element.nextElementSibling?.textContent)
  expect(originalCourseId).toMatch(/^course_/)
  const mappedCourseId = `${originalCourseId}_mapped`
  await dialog.getByText('确认对象 ID 映射', { exact: true }).click()
  await dialog.getByRole('button', { name: '添加精确映射' }).click()
  await dialog.getByLabel('原对象 ID', { exact: true }).fill(originalCourseId!)
  await dialog.getByLabel('新对象 ID', { exact: true }).fill(mappedCourseId)
  const receipt = await acceptAndCommit(page)
  expect(receipt.course_refs).toHaveLength(1)
  const ref = receipt.course_refs[0]
  expect(ref.entity).toBe('course')
  expect(ref.id).toBe(mappedCourseId)
  await expect(dialog.locator('.import-result')).toContainText(ref.sha256)
  const courseResponse = await page.request.get(`/api/v1/courses/${ref.id}?revision=${ref.revision}`)
  expect(courseResponse.status()).toBe(200)
  expect(courseResponse.headers().etag).toBe(`"${ref.sha256}"`)
  await expect(dialog.locator('.import-result')).toContainText((await courseResponse.json()).title)
  await page.screenshot({ path: testInfo.outputPath('imports-committed-result-1440.png') })
  await dialog.getByRole('button', { name: '完成并关闭导入' }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('heading', { name: '从一个学习目标开始' })).toBeVisible()
})

test('safe HTML warning requires explicit acceptance and native cancel leaves courses untouched', async ({ page }, testInfo) => {
  await bootstrap(page)
  await page.setViewportSize({ width: 390, height: 844 })
  const dialog = await openImports(page)
  const before = await page.request.get('/api/v1/courses?limit=100').then(response => response.json())
  await upload(page, 'native-active.html', '<html><body><h1>安全 HTML 合成验收</h1><p>保留的正文。</p><script>window.import_attack=true</script><img src="https://external.invalid/private.png" onerror="window.import_attack=true"></body></html>', 'html')
  await expect(dialog.getByRole('checkbox', { name: /接受警告/ }).first()).toBeVisible()
  await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toBeDisabled()
  expect(await page.evaluate(() => 'import_attack' in window)).toBe(false)
  expect(await dialog.locator('script,img').count()).toBe(0)
  await dialog.getByLabel('选择预览候选').focus()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => !!document.querySelector('dialog')?.contains(document.activeElement))).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('imports-html-preview-390.png') })
  await dialog.getByRole('button', { name: '取消本次导入', exact: true }).click()
  await expect(dialog.getByText('已取消', { exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/courses?limit=100').then(response => response.json())).items).toEqual(before.items)
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
})

test('UTF-8 text can target a real existing course and creates a newer exact revision', async ({ page }) => {
  await bootstrap(page)
  const dialog = await openImports(page)
  await upload(page, 'native-course.md', '# 追加内容目标\n\n真实合成目标课程。\n', 'markdown')
  const first = await acceptAndCommit(page)
  const original = first.course_refs[0]
  await dialog.getByRole('button', { name: '完成并关闭导入' }).click()
  await openImports(page)
  await dialog.getByLabel('导入目标').selectOption(original.id)
  await upload(page, 'native-append.txt', '这是追加的 UTF-8 文本。\n不声称已解析所有数学语义。\n', 'text')
  const second = await acceptAndCommit(page)
  expect(second.course_refs[0].id).toBe(original.id)
  expect(second.course_refs[0].revision).toBeGreaterThan(original.revision)
  expect((await page.request.get(`/api/v1/courses/${original.id}?revision=${original.revision}`)).status()).toBe(200)
})

test('upload request failure keeps the selected file; preview failure keeps the recovery ID and explicit retry works', async ({ page }) => {
  await bootstrap(page)
  const dialog = await openImports(page)
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'retry.md', mimeType: 'text/markdown', buffer: Buffer.from('# 重试验收\n\n合成内容。\n') })
  await page.route('**/api/v1/imports', route => route.abort('failed'))
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  await expect(dialog.getByRole('alert')).toBeVisible()
  expect(await dialog.getByLabel('选择导入文件').evaluate((input: HTMLInputElement) => input.files?.[0]?.name)).toBe('retry.md')
  await page.unroute('**/api/v1/imports')
  const previewPattern = /\/api\/v1\/imports\/[^/]+$/
  await page.route(previewPattern, route => route.abort('failed'))
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  await expect(dialog.getByRole('button', { name: '重试读取导入状态' })).toBeVisible()
  const cached = await page.evaluate(() => Object.values(localStorage).filter(value => value.includes('job_')))
  expect(cached.length).toBeGreaterThan(0)
  await page.unroute(previewPattern)
  await dialog.getByRole('button', { name: '重试读取导入状态' }).click()
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
})

test('author package requires explicit role change and clears the private preview after returning to learner', async ({ page }) => {
  await bootstrap(page)
  const dialog = await openImports(page)
  await dialog.getByLabel('解析格式').selectOption('learnpack')
  const archive = originalSyntheticAuthorPackage()
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'native-author.learnpack.zip', mimeType: 'application/zip', buffer: archive })
  const stagedResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/imports') && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  expect((await stagedResponse).status()).toBe(202)
  await expect(dialog.getByRole('alert')).toContainText('需要作者角色')
  await expect(dialog.getByLabel('当前候选正文')).toHaveCount(0)
  const sourceResponse = page.waitForResponse(response => /\/api\/v1\/sources\/[^/]+$/.test(response.url()))
  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('当前候选正文')).toContainText('Synthetic author-package public body.')
  await expect(dialog.getByRole('button', { name: '下载受控原件' })).toBeVisible()
  const source = await (await sourceResponse).json()
  const downloadPromise = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载受控原件' }).click()
  const downloaded = await (await downloadPromise).createReadStream()
  if (!downloaded) throw new Error('Author original download is unavailable')
  const chunks: Buffer[] = []
  for await (const chunk of downloaded) chunks.push(Buffer.from(chunk))
  expect(Buffer.concat(chunks)).toEqual(archive)
  await expect(dialog).not.toContainText('synthetic-private-solution-marker')
  await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('需要作者角色')
  await expect(dialog.getByLabel('当前候选正文')).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '下载受控原件' })).toHaveCount(0)
  expect((await page.request.get(source.artifact.download_path)).status()).toBe(403)
  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByLabel('当前候选正文')).toBeVisible()
  await acceptAndCommit(page)
  await expect(dialog).not.toContainText('synthetic-private-solution-marker')
})

test('a real invalid UTF-8 parse shows a blocking error and cannot be confirmed', async ({ page }) => {
  await bootstrap(page)
  const dialog = await openImports(page)
  const before = await page.request.get('/api/v1/courses?limit=100').then(response => response.json())
  await dialog.getByLabel('解析格式').selectOption('text')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'invalid-utf8.txt', mimeType: 'text/plain', buffer: Buffer.from([0xc3, 0x28]) })
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  await expect(dialog.getByText('导入失败', { exact: true })).toBeVisible()
  await expect(dialog.getByText(/阻塞错误.*ENCODING_CHOICE_REQUIRED/)).toBeVisible()
  await expect(dialog.getByRole('checkbox', { name: /接受警告/ })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '取消本次导入' })).toHaveCount(0)
  await expect(dialog.getByLabel('原件文本编码')).toHaveValue('utf-8')
  await dialog.getByRole('button', { name: '严格解码并预览' }).click()
  await expect(dialog.getByText(/所选编码无法完整解码原件/)).toBeVisible()
  await expect(dialog.getByRole('button', { name: '下载 UTF-8 派生文件' })).toHaveCount(0)
  expect((await page.request.get('/api/v1/courses?limit=100').then(response => response.json())).items).toEqual(before.items)
  await dialog.getByRole('button', { name: '关闭并更换原件' }).click()
  await expect(dialog).toBeHidden()
})

test('local encoding choice preserves the failed original and creates a separately confirmed UTF-8 import', async ({ page }, testInfo) => {
  await bootstrap(page)
  const dialog = await openImports(page)
  const text = '合成编码恢复\n\n这是独立生成的编码测试材料。\n<script>window.encodingExecuted = true</script>\n'
  const original = execFileSync(`${resolve(import.meta.dirname, '../..')}/.venv/bin/python`, ['-c', 'import sys; sys.stdout.buffer.write(sys.argv[1].encode("gb18030"))', text])
  const originalHash = createHash('sha256').update(original).digest('hex')
  let uploadCount = 0
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/api/v1/imports')) uploadCount++ })
  await dialog.getByLabel('解析格式').selectOption('text')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'encoding-original.txt', mimeType: 'text/plain', buffer: original })
  const stagedResponse = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/imports'))
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  const staged = await (await stagedResponse).json()
  expect(staged.input_sha256).toBe(originalHash)
  await expect(dialog.getByText('导入失败', { exact: true })).toBeVisible()
  await expect(dialog.getByRole('checkbox', { name: /接受警告/ })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toHaveCount(0)
  await expect(dialog.getByText('本机原始文件：encoding-original.txt')).toBeVisible()
  await dialog.getByLabel('原件文本编码').selectOption('gb18030')
  await dialog.getByRole('button', { name: '严格解码并预览' }).click()
  await expect(dialog.getByLabel('本机解码文本预览')).toHaveText(text)
  await expect(dialog.getByRole('button', { name: '下载 UTF-8 派生文件' })).toBeDisabled()
  expect(await page.evaluate(() => Reflect.get(window, 'encodingExecuted'))).toBeUndefined()
  expect(uploadCount).toBe(1)
  // A reload must not invent a File from cached IDs or silently fetch private bytes.
  await page.reload()
  await openImports(page)
  await dialog.getByRole('button', { name: `恢复 ${staged.import_id}`, exact: true }).click()
  await expect(dialog.getByText(/浏览器不再持有原文件/)).toBeVisible()
  await expect(dialog.getByRole('button', { name: '严格解码并预览' })).toBeDisabled()
  await dialog.getByLabel('重新选择原始文件').setInputFiles({ name: 'wrong.txt', mimeType: 'text/plain', buffer: Buffer.from('different synthetic file') })
  await dialog.getByLabel('原件文本编码').selectOption('gb18030')
  await dialog.getByRole('button', { name: '严格解码并预览' }).click()
  await expect(dialog.getByText(/所选文件与失败导入的原件 SHA-256 不一致/)).toBeVisible()
  await expect(dialog.getByLabel('本机解码文本预览')).toHaveCount(0)
  await dialog.getByLabel('重新选择原始文件').setInputFiles({ name: 'encoding-original.txt', mimeType: 'text/plain', buffer: original })
  await dialog.getByRole('button', { name: '严格解码并预览' }).click()
  await expect(dialog.getByLabel('本机解码文本预览')).toHaveText(text)
  expect(await dialog.getByLabel('本机解码文本预览').evaluate(element => element.tagName)).toBe('PRE')
  await dialog.getByRole('checkbox', { name: /我已核对本机解码文本/ }).check()
  const downloadPromise = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载 UTF-8 派生文件' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('encoding-original.utf8-derived.txt')
  const stream = await download.createReadStream()
  if (!stream) throw new Error('Derived download stream unavailable')
  const parts: Buffer[] = []
  for await (const part of stream) parts.push(Buffer.from(part))
  const derivative = Buffer.concat(parts)
  expect(derivative).toEqual(Buffer.from(text, 'utf8'))
  expect(createHash('sha256').update(derivative).digest('hex')).not.toBe(originalHash)
  expect(uploadCount).toBe(1)
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('imports-local-encoding-preview-1440.png') })
  await dialog.getByRole('button', { name: '关闭并更换原件' }).click()
  await openImports(page)
  const next = await upload(page, download.suggestedFilename(), derivative.toString('utf8'), 'text')
  expect(next.import_id).not.toBe(staged.import_id)
  expect(next.input_sha256).toBe(createHash('sha256').update(derivative).digest('hex'))
  await acceptAndCommit(page)
  expect(uploadCount).toBe(2)
  const failed = await page.request.get(`/api/v1/imports/${staged.import_id}`).then(response => response.json())
  expect(failed.status).toBe('failed')
  expect(failed.input_sha256).toBe(originalHash)
  expect(failed.preview_refs).toEqual([])
})

test('deferred author preview and original responses cannot restore content after the role is lowered', async ({ page }) => {
  await bootstrap(page)
  const dialog = await openImports(page)
  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByText('操作角色：作者')).toBeVisible()
  let releasePreview: () => void = () => {}
  let previewHeld = false
  let sawPending = false
  const previewGate = new Promise<void>(resolve => { releasePreview = resolve })
  const pattern = /\/api\/v1\/imports\/[^/]+$/
  await page.route(pattern, async route => {
    const response = await route.fetch()
    const value = await response.json()
    if (['staged', 'parsing'].includes(value.status)) sawPending = true
    if (value.status === 'preview_ready' && !previewHeld) {
      previewHeld = true
      await previewGate
    }
    await route.fulfill({ response })
  })
  await dialog.getByLabel('解析格式').selectOption('learnpack')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'deferred-author.learnpack.zip', mimeType: 'application/zip', buffer: originalSyntheticAuthorPackage() })
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  await expect.poll(() => previewHeld).toBe(true)
  expect(sawPending).toBe(true)
  await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('需要作者角色')
  const delayedPreview = page.waitForResponse(response => pattern.test(response.url()) && response.status() === 200)
  releasePreview()
  await (await delayedPreview).finished()
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  await expect(dialog.getByText('操作角色：学习者')).toBeVisible()
  await expect(dialog.getByRole('heading', { name: 'Synthetic author course' })).toHaveCount(0)
  await expect(dialog.getByLabel('当前候选正文')).toHaveCount(0)
  await expect(dialog.getByRole('checkbox', { name: /IMPORT_PRIVATE_ANSWERS/ })).toHaveCount(0)
  await page.unroute(pattern)

  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByRole('button', { name: '下载受控原件' })).toBeVisible()
  let releaseOriginal: () => void = () => {}
  let originalHeld = false
  const originalGate = new Promise<void>(resolve => { releaseOriginal = resolve })
  const originalPattern = /\/api\/v1\/artifacts\/[^/]+\/download$/
  await page.route(originalPattern, async route => {
    const response = await route.fetch()
    expect(response.status()).toBe(200)
    originalHeld = true
    await originalGate
    await route.fulfill({ response })
  })
  let downloads = 0
  page.on('download', () => { downloads++ })
  await dialog.getByRole('button', { name: '下载受控原件' }).click()
  await expect.poll(() => originalHeld).toBe(true)
  await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('需要作者角色')
  const delayedOriginal = page.waitForResponse(response => originalPattern.test(response.url()) && response.status() === 200)
  releaseOriginal()
  await (await delayedOriginal).finished()
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  expect(downloads).toBe(0)
  await expect(dialog.getByLabel('当前候选正文')).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '下载受控原件' })).toHaveCount(0)
})
