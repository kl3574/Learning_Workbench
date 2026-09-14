import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef } from '../../packages/contracts/generated/types'

export type ReaderPackage = { bytes: Buffer; course: ContentRef; lessons: ContentRef[]; blocks: ContentRef[]; bodies: Record<string, string> }
export function originalReaderPackage(prefix: string, revision = 1, history = false): ReaderPackage {
  if (history && revision !== 2) throw new Error('The history archive has revision 2 as its root course')
  const root = resolve(import.meta.dirname, '../..')
  const result = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'import base64,json,sys; from tests.reader_fixtures import reader_fixture,reader_history_package,ref; f=reader_fixture(sys.argv[1],int(sys.argv[2])); archive=reader_history_package(sys.argv[1]) if sys.argv[3]=="history" else f.archive; print(json.dumps(dict(archive=base64.b64encode(archive).decode(),course=ref(f.course).model_dump(),lessons=[ref(v).model_dump() for v in f.lessons],blocks=[ref(v).model_dump() for v in f.blocks],bodies=f.bodies)))', prefix, String(revision), history ? 'history' : 'single'], { cwd: root, encoding: 'utf8' })
  const value = JSON.parse(result)
  return { bytes: Buffer.from(value.archive, 'base64'), course: value.course, lessons: value.lessons, blocks: value.blocks, bodies: value.bodies }
}

export async function importReaderPackage(page: Page, value: ReaderPackage) {
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.keyboard.press('Control+Shift+P')
  await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ }).click()
  const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await dialog.getByLabel('解析格式').selectOption('learnpack')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'original-reader.learnpack.zip', mimeType: 'application/zip', buffer: value.bytes })
  const upload = page.waitForResponse(response => response.url().endsWith('/api/v1/imports') && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  const staged = await upload
  expect(staged.status()).toBe(202)
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  for (const checkbox of await dialog.getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  const commit = page.waitForResponse(response => /\/api\/v1\/imports\/[^/]+\/commit$/.test(response.url()) && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '确认导入当前候选' }).click()
  const response = await commit
  expect(response.status()).toBe(200)
  const actual = await response.json()
  expect(actual.course_refs).toContainEqual(value.course)
  await expect(dialog.getByRole('heading', { name: '导入已提交', exact: true })).toBeVisible()
  return { dialog, receipt: actual }
}
