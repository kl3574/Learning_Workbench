import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef } from '../../packages/contracts/generated/types'
import type { ImportCommitResponse } from '../../packages/contracts/generated/api-types'

export type PracticePackage = {
  bytes: Buffer; profile: 'author' | 'learner'; course: ContentRef; lesson: ContentRef
  block: ContentRef; practice: ContentRef; questions: ContentRef[]
}

/** The archive is built from the original Python fixture, never a private library. */
export function originalPracticePackage(prefix: string, profile: PracticePackage['profile'] = 'author'): PracticePackage {
  const root = resolve(import.meta.dirname, '../..')
  const result = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'import base64,json,sys; from tests.practice_fixtures import practice_fixture; from services.api.app.infrastructure.content_repository import reference; f=practice_fixture(sys.argv[1],profile=sys.argv[2]); print(json.dumps(dict(archive=base64.b64encode(f.archive).decode(),course=reference(f.course).model_dump(),lesson=reference(f.lesson).model_dump(),block=reference(f.block).model_dump(),practice=reference(f.practice).model_dump(),questions=[reference(q).model_dump() for q in f.questions])))', prefix, profile], { cwd: root, encoding: 'utf8' })
  const value: { archive: string; course: ContentRef; lesson: ContentRef; block: ContentRef; practice: ContentRef; questions: ContentRef[] } = JSON.parse(result)
  return { bytes: Buffer.from(value.archive, 'base64'), profile, course: value.course, lesson: value.lesson, block: value.block, practice: value.practice, questions: value.questions }
}

/** Actual upload, worker preview, explicit confirmation and learner-role readback. */
export async function importPracticePackage(page: Page, value: PracticePackage) {
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await page.keyboard.press('Control+Shift+P')
  await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ }).click()
  const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await expect(dialog.getByText(/操作角色：(作者|学习者)$/)).toBeVisible()
  const desiredRole = value.profile === 'author' ? '作者' : '学习者'
  const switchRole = dialog.getByRole('button', { name: `切换为${desiredRole}角色`, exact: true })
  if (await switchRole.count()) await switchRole.click()
  await expect(dialog.getByText(`操作角色：${desiredRole}`, { exact: true })).toBeVisible()
  await dialog.getByLabel('解析格式').selectOption('learnpack')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: `original-practice-${value.profile}.learnpack.zip`, mimeType: 'application/zip', buffer: value.bytes })
  const staged = page.waitForResponse(response => response.url().endsWith('/api/v1/imports') && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '上传并生成预览', exact: true }).click()
  expect((await staged).status()).toBe(202)
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  for (const checkbox of await dialog.getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  const committing = page.waitForResponse(response => /\/api\/v1\/imports\/[^/]+\/commit$/.test(response.url()) && response.request().method() === 'POST')
  await dialog.getByRole('button', { name: '确认导入当前候选', exact: true }).click()
  const response = await committing
  expect(response.status()).toBe(200)
  const receipt: ImportCommitResponse = await response.json()
  expect(receipt.course_refs).toContainEqual(value.course)
  await expect(dialog.getByRole('heading', { name: '导入已提交', exact: true })).toBeVisible()
  if (value.profile === 'author') {
    await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
  }
  return { dialog, receipt }
}
