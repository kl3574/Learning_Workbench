# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: grading-recovery.spec.ts >> a real failed regrade survives reload and can recover from the last actual grade without losing the old submission
- Location: ../../tests/e2e/grading-recovery.spec.ts:57:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('dialog', { name: '导入', exact: true }).getByText(/操作角色：(作者|学习者)$/)
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('dialog', { name: '导入', exact: true }).getByText(/操作角色：(作者|学习者)$/) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByText(/操作角色：(作者|学习者)$/)

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
- status: 当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。
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
> 26 |   await expect(dialog.getByText(/操作角色：(作者|学习者)$/)).toBeVisible()
     |                                                    ^ Error: expect(locator).toBeVisible() failed
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
  42 |   expect(response.status()).toBe(200)
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