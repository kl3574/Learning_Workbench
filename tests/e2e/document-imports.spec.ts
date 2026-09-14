import { expect, test, type Download, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { bootstrap } from './helpers'
import type { DraftSnapshot, ImportKind } from '../../apps/web/src/features/imports/contracts'

const root = resolve(import.meta.dirname, '../..')
const hash = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')
type Fixture = 'pdf_text_fixture' | 'pdf_scan_fixture' | 'pdf_mixed_fixture' | 'pdf_encrypted_fixture' | 'pdf_malformed_fixture' | 'docx_fixture' | 'docx_malformed_fixture'
function original(name: Fixture) {
  return execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'import sys; from tests import document_fixtures as f; sys.stdout.buffer.write(getattr(f, sys.argv[1])())', name], { cwd: root })
}
const dialogFor = (page: Page) => page.getByRole('dialog', { name: '导入', exact: true })
async function openImports(page: Page) {
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.keyboard.press('Control+Shift+P')
  await page.getByRole('dialog', { name: '命令面板' }).getByRole('button', { name: /^导入/ }).click()
  await expect(dialogFor(page).getByText('操作角色：学习者')).toBeVisible()
}
async function stage(page: Page, bytes: Buffer, name: string, kind: ImportKind) {
  const dialog = dialogFor(page)
  await dialog.getByLabel('解析格式').selectOption(kind)
  await dialog.getByLabel('选择导入文件').setInputFiles({ name, mimeType: name.endsWith('.pdf') ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: bytes })
  const request = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/imports'))
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  const response = await request
  expect(response.status()).toBe(202)
  const result = await response.json()
  expect(result.input_sha256).toBe(hash(bytes))
  return result
}
async function candidate(page: Page, containing: string) {
  const dialog = dialogFor(page)
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  const selector = dialog.getByLabel('选择预览候选')
  const ids = await selector.locator('option').evaluateAll(options => options.map(option => (option as HTMLOptionElement).value))
  for (const id of ids) {
    const response = await page.request.get(`/api/v1/drafts/${id}`)
    expect(response.status()).toBe(200)
    const value: DraftSnapshot = await response.json()
    if (!('metadata' in value.payload) || !value.payload.body_markdown.includes(containing)) continue
    await selector.selectOption(id)
    await expect(dialog.getByText('读取候选正文…', { exact: true })).toHaveCount(0)
    await expect(dialog.getByLabel('当前候选正文')).toContainText(containing)
    return value as DraftSnapshot & { payload: Extract<DraftSnapshot['payload'], { metadata: unknown }> }
  }
  throw new Error(`No actual candidate contained the expected original marker: ${containing}`)
}
async function downloadBytes(download: Download) {
  const stream = await download.createReadStream()
  if (!stream) throw new Error('Native download stream unavailable')
  const chunks: Buffer[] = []
  for await (const chunk of stream) chunks.push(Buffer.from(chunk))
  return Buffer.concat(chunks)
}
async function acceptWarnings(page: Page) {
  for (const checkbox of await dialogFor(page).getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  await dialogFor(page).getByRole('checkbox', { name: /我已核对本次候选/ }).check()
}
async function confirm(page: Page) {
  const response = page.waitForResponse(value => value.request().method() === 'POST' && /\/imports\/[^/]+\/commit$/.test(value.url()))
  await dialogFor(page).getByRole('button', { name: '确认导入当前候选' }).click()
  const result = await response
  expect(result.status()).toBe(200)
  await expect(dialogFor(page).getByRole('heading', { name: '导入已提交', exact: true })).toBeVisible()
  return result.json()
}

test('real two-page PDF keeps exact page citations, guarded original bytes and explicit fidelity approval', async ({ page }, testInfo) => {
  await bootstrap(page); await openImports(page)
  const bytes = original('pdf_text_fixture')
  const dialog = dialogFor(page)
  const before = await page.request.get('/api/v1/courses').then(response => response.json())
  const staged = await stage(page, bytes, 'synthetic-pages.pdf', 'auto')
  const first = await candidate(page, 'PDF page one alpha')
  await expect(dialog.getByLabel('当前候选正文')).toContainText('PDF page one alpha.')
  expect(first.payload.citations?.some(citation => citation.locator.endsWith(';pdf:page:1') && citation.source_sha256 === hash(bytes))).toBe(true)
  await expect(dialog.getByLabel('当前候选的原件来源')).toContainText('PDF 第 1 页')
  const second = await candidate(page, 'PDF page two beta')
  await expect(dialog.getByLabel('当前候选正文')).toContainText('PDF page two beta.')
  expect(second.payload.citations?.some(citation => citation.locator.endsWith(';pdf:page:2') && citation.source_sha256 === hash(bytes))).toBe(true)
  await expect(dialog.getByLabel('当前候选的原件来源')).toContainText('PDF 第 2 页')
  const preview = await page.request.get(`/api/v1/imports/${staged.import_id}`).then(response => response.json())
  expect(preview.warnings.some((warning: { code: string; locator: string }) => warning.code === 'PDF_IMAGE_NOT_TEX' && warning.locator.endsWith(';pdf:page:2'))).toBe(true)
  await expect(dialog.getByRole('checkbox', { name: /PDF_TEXT_LAYOUT_UNVERIFIED/ }).first()).toBeVisible()
  expect(second.payload.body_markdown).not.toContain('\\frac')
  await expect(dialog.getByLabel('当前候选正文').locator('.formula')).toHaveCount(0)
  expect((await page.request.get('/api/v1/courses').then(response => response.json())).items).toEqual(before.items)
  await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toBeDisabled()
  const download = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载受控原件' }).click()
  expect(await downloadBytes(await download)).toEqual(bytes)
  await page.reload(); await openImports(page)
  await dialogFor(page).getByRole('button', { name: `恢复 ${staged.import_id}`, exact: true }).click()
  await candidate(page, 'PDF page two beta')
  await expect(dialogFor(page).getByLabel('当前候选正文')).toContainText('PDF page two beta.')
  await expect(dialogFor(page).getByLabel('当前候选的原件来源')).toContainText('PDF 第 2 页')
  await dialogFor(page).getByLabel('选择预览候选').focus()
  await page.screenshot({ path: testInfo.outputPath('document-pdf-preview-1440.png') })
  await acceptWarnings(page)
  const committed = await confirm(page)
  expect(committed.course_refs).toHaveLength(1)
  const body = await page.request.get(`/api/v1/blocks/${second.payload.metadata.id}/body?revision=${second.payload.metadata.revision}`)
  expect(body.status()).toBe(200)
  expect(await body.text()).toBe(second.payload.body_markdown)
})

test('real DOCX safe text stays readable for learner while original bytes require an explicit author role', async ({ page }, testInfo) => {
  await bootstrap(page); await openImports(page)
  const externalRequests: string[] = []
  page.on('request', request => { if (new URL(request.url()).hostname === 'example.invalid') externalRequests.push(request.url()) })
  const bytes = original('docx_fixture')
  const staged = await stage(page, bytes, 'synthetic-document.docx', 'docx')
  const paragraph = await candidate(page, 'DOCX paragraph alpha')
  const dialog = dialogFor(page)
  await expect(dialog.getByLabel('当前候选的原件来源')).toContainText('DOCX 正文第 2 个段落节点')
  expect(paragraph.payload.citations?.every(citation => citation.source_sha256 === hash(bytes))).toBe(true)
  await expect(dialog.getByText(/原件暂不可读取/)).toBeVisible()
  await expect(dialog.getByText(/原件暂不可读取/)).toContainText('作者')
  await expect(dialog.getByRole('button', { name: '重试读取候选', exact: true })).toHaveCount(0)
  expect((await page.request.get(`/api/v1/sources/${paragraph.payload.source_id}`)).status()).toBe(403)
  const table = await candidate(page, 'Cell A')
  expect(table.payload.citations?.some(citation => citation.locator.includes('/w:tbl[1]/w:tr[1]/w:tc[1]'))).toBe(true)
  const preview = await page.request.get(`/api/v1/imports/${staged.import_id}`).then(response => response.json())
  for (const code of ['DOCX_OMML_NOT_TEX', 'DOCX_FLOATING_IMAGE', 'DOCX_EXTERNAL_RESOURCE_NOT_FETCHED', 'DOCX_TABLE_LAYOUT_UNVERIFIED', 'DOCX_ORIGINAL_RESTRICTED']) {
    expect(preview.warnings.some((warning: { code: string }) => warning.code === code)).toBe(true)
  }
  await expect(dialog.locator('.formula,img,iframe')).toHaveCount(0)
  expect(externalRequests).toEqual([])
  await acceptWarnings(page)
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toBeEnabled()
  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByText('操作角色：作者')).toBeVisible()
  await candidate(page, 'DOCX paragraph alpha')
  const download = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载受控原件' }).click()
  expect(await downloadBytes(await download)).toEqual(bytes)
  await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  await candidate(page, 'DOCX paragraph alpha')
  await expect(dialog.getByRole('button', { name: '下载受控原件' })).toHaveCount(0)
  await page.setViewportSize({ width: 390, height: 844 })
  await dialog.getByLabel('选择预览候选').focus()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  const flowWidth = await dialog.locator('.import-workflow').evaluate(element => ({ scroll: element.scrollWidth, client: element.clientWidth }))
  expect(flowWidth.scroll).toBeLessThanOrEqual(flowWidth.client)
  await page.screenshot({ path: testInfo.outputPath('document-docx-preview-390.png') })
  await acceptWarnings(page)
  await confirm(page)
})

test('a real scanned PDF fails without invented text or OCR and its local original is checked explicitly after reload', async ({ page }) => {
  await bootstrap(page); await openImports(page)
  const bytes = original('pdf_scan_fixture')
  const before = await page.request.get('/api/v1/courses').then(response => response.json())
  const staged = await stage(page, bytes, 'synthetic-scan.pdf', 'pdf')
  const dialog = dialogFor(page)
  await expect(dialog.getByText('导入失败', { exact: true })).toBeVisible()
  await expect(dialog.getByText('PDF_NO_EXTRACTABLE_TEXT', { exact: true }).first()).toBeVisible()
  await expect(dialog.getByText(/OCR/).first()).toBeVisible()
  await expect(dialog.getByLabel('当前候选正文')).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toHaveCount(0)
  const failed = await page.request.get(`/api/v1/imports/${staged.import_id}`).then(response => response.json())
  expect(failed.preview_refs).toEqual([])
  expect(failed.input_sha256).toBe(hash(bytes))
  expect(failed.warnings.some((warning: { code: string; locator?: string }) => warning.code === 'PDF_PAGE_NO_TEXT' && warning.locator?.endsWith(';pdf:page:1'))).toBe(true)
  await expect(dialog.getByRole('listitem').filter({ hasText: '阻塞错误' }).getByRole('checkbox')).toHaveCount(0)
  await dialog.getByRole('button', { name: '核对本机原件 SHA-256' }).click()
  await expect(dialog.getByText(/本机文件与失败导入的原件哈希一致/)).toBeVisible()
  const download = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '保存本机原件副本以查看' }).click()
  expect(await downloadBytes(await download)).toEqual(bytes)
  await page.reload(); await openImports(page)
  await dialog.getByRole('button', { name: `恢复 ${staged.import_id}`, exact: true }).click()
  await expect(dialog.getByText(/浏览器不再持有原始文件/)).toBeVisible()
  await expect(dialog.getByRole('button', { name: '核对本机原件 SHA-256' })).toBeDisabled()
  await dialog.getByLabel('选择用于核对的原始文件').setInputFiles({ name: 'wrong.pdf', mimeType: 'application/pdf', buffer: Buffer.from('different bytes') })
  await dialog.getByRole('button', { name: '核对本机原件 SHA-256' }).click()
  await expect(dialog.getByText(/所选文件与失败导入的原件 SHA-256 不一致/)).toBeVisible()
  await expect(dialog.getByRole('button', { name: '保存本机原件副本以查看' })).toHaveCount(0)
  expect((await page.request.get('/api/v1/courses').then(response => response.json())).items).toEqual(before.items)
  expect((await page.request.get(`/api/v1/imports/${staged.import_id}`).then(response => response.json())).status).toBe('failed')
})

for (const [fixture, filename, kind] of [['pdf_encrypted_fixture', 'encrypted.pdf', 'pdf'], ['docx_malformed_fixture', 'malformed.docx', 'docx']] as const) {
  test(`real ${filename} extraction failure remains blocked and preserves its original hash`, async ({ page }) => {
    await bootstrap(page); await openImports(page)
    const bytes = original(fixture)
    const before = await page.request.get('/api/v1/courses').then(response => response.json())
    const staged = await stage(page, bytes, filename, kind)
    const dialog = dialogFor(page)
    await expect(dialog.getByText('导入失败', { exact: true })).toBeVisible()
    await expect(dialog.getByText(/阻塞错误/).first()).toBeVisible()
    await expect(dialog.getByRole('button', { name: '确认导入当前候选' })).toHaveCount(0)
    await expect(dialog.getByRole('listitem').filter({ hasText: '阻塞错误' }).getByRole('checkbox')).toHaveCount(0)
    for (const checkbox of await dialog.getByRole('checkbox', { name: /接受警告/ }).all()) await expect(checkbox).toBeDisabled()
    const failed = await page.request.get(`/api/v1/imports/${staged.import_id}`).then(response => response.json())
    expect(failed.preview_refs).toEqual([])
    expect(failed.input_sha256).toBe(hash(bytes))
    expect((await page.request.get('/api/v1/courses').then(response => response.json())).items).toEqual(before.items)
  })
}
