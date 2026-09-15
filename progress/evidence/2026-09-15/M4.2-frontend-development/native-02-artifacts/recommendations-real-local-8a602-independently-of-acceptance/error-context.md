# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: recommendations.spec.ts >> real local suggestions cover another imported textbook and open its complete original refs independently of acceptance
- Location: tests/e2e/recommendations.spec.ts:90:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: 200
Received: 409
```

# Test source

```ts
  1  | import { execFileSync } from 'node:child_process'
  2  | import { resolve } from 'node:path'
  3  | import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  4  | import type { ContentRef } from '../../packages/contracts/generated/types'
  5  | import type { ImportCommitResponse } from '../../packages/contracts/generated/api-types'
  6  | 
  7  | export type PracticePackage = {
  8  |   bytes: Buffer; profile: 'author' | 'learner'; course: ContentRef; lesson: ContentRef
  9  |   block: ContentRef; practice: ContentRef; questions: ContentRef[]
  10 | }
  11 | 
  12 | /** The archive is built from the original Python fixture, never a private library. */
  13 | export function originalPracticePackage(prefix: string, profile: PracticePackage['profile'] = 'author'): PracticePackage {
  14 |   const root = resolve(import.meta.dirname, '../..')
  15 |   const result = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'import base64,json,sys; from tests.practice_fixtures import practice_fixture; from services.api.app.infrastructure.content_repository import reference; f=practice_fixture(sys.argv[1],profile=sys.argv[2]); print(json.dumps(dict(archive=base64.b64encode(f.archive).decode(),course=reference(f.course).model_dump(),lesson=reference(f.lesson).model_dump(),block=reference(f.block).model_dump(),practice=reference(f.practice).model_dump(),questions=[reference(q).model_dump() for q in f.questions])))', prefix, profile], { cwd: root, encoding: 'utf8' })
  16 |   const value: { archive: string; course: ContentRef; lesson: ContentRef; block: ContentRef; practice: ContentRef; questions: ContentRef[] } = JSON.parse(result)
  17 |   return { bytes: Buffer.from(value.archive, 'base64'), profile, course: value.course, lesson: value.lesson, block: value.block, practice: value.practice, questions: value.questions }
  18 | }
  19 | 
  20 | /** Actual upload, worker preview, explicit confirmation and learner-role readback. */
  21 | export async function importPracticePackage(page: Page, value: PracticePackage) {
  22 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  23 |   await page.keyboard.press('Control+Shift+P')
  24 |   await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ }).click()
  25 |   const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  26 |   await expect(dialog.getByText(/操作角色：(作者|学习者)$/)).toBeVisible()
  27 |   const desiredRole = value.profile === 'author' ? '作者' : '学习者'
  28 |   const switchRole = dialog.getByRole('button', { name: `切换为${desiredRole}角色`, exact: true })
  29 |   if (await switchRole.count()) await switchRole.click()
  30 |   await expect(dialog.getByText(`操作角色：${desiredRole}`, { exact: true })).toBeVisible()
  31 |   await dialog.getByLabel('解析格式').selectOption('learnpack')
  32 |   await dialog.getByLabel('选择导入文件').setInputFiles({ name: `original-practice-${value.profile}.learnpack.zip`, mimeType: 'application/zip', buffer: value.bytes })
  33 |   const staged = page.waitForResponse(response => response.url().endsWith('/api/v1/imports') && response.request().method() === 'POST')
  34 |   await dialog.getByRole('button', { name: '上传并生成预览', exact: true }).click()
  35 |   expect((await staged).status()).toBe(202)
  36 |   await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  37 |   for (const checkbox of await dialog.getByRole('checkbox', { name: /接受警告/ }).all()) await checkbox.check()
  38 |   await dialog.getByRole('checkbox', { name: /我已核对本次候选/ }).check()
  39 |   const committing = page.waitForResponse(response => /\/api\/v1\/imports\/[^/]+\/commit$/.test(response.url()) && response.request().method() === 'POST')
  40 |   await dialog.getByRole('button', { name: '确认导入当前候选', exact: true }).click()
  41 |   const response = await committing
> 42 |   expect(response.status()).toBe(200)
     |                             ^ Error: expect(received).toBe(expected) // Object.is equality
  43 |   const receipt: ImportCommitResponse = await response.json()
  44 |   expect(receipt.course_refs).toContainEqual(value.course)
  45 |   await expect(dialog.getByRole('heading', { name: '导入已提交', exact: true })).toBeVisible()
  46 |   if (value.profile === 'author') {
  47 |     await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  48 |     await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
  49 |   }
  50 |   return { dialog, receipt }
  51 | }
  52 | 
```