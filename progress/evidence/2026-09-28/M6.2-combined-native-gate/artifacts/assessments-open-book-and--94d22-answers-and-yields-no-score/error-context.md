# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: assessments.spec.ts >> open-book and assisted freeze actual policies; explicit abandon retains saved answers and yields no score
- Location: ../../tests/e2e/assessments.spec.ts:90:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByRole('button', { name: '切换为作者角色', exact: true })
    - locator resolved to <button>切换为作者角色</button>
  - attempting click action
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed

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
      - button "导入" [ref=f2e17] [cursor=pointer]
  - generic [ref=f2e18]:
    - complementary "课程导航" [ref=f2e19]:
      - generic [ref=f2e20]:
        - generic [ref=f2e21]:
          - generic [ref=f2e22]: 测试工作区
          - heading "测试与作答记录" [level=2] [ref=f2e23]
          - paragraph [ref=f2e24]: 所选课程修订 1 的准确关联测试
          - button "选择课程" [ref=f2e25] [cursor=pointer]
        - navigation "学习主导航" [ref=f2e26]:
          - button "学习路线" [ref=f2e27] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e28]: ↗
          - button "教材" [ref=f2e30] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e31]: ▤
          - button "习题" [ref=f2e33] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e34]: ✎
          - button "测试题" [ref=f2e36] [cursor=pointer]:
            - generic [aria-hidden] [ref=f2e37]: ☑
        - generic [ref=f2e39]:
          - heading "测试上下文目录" [level=2] [ref=f2e41]
          - generic [ref=f2e42]:
            - navigation "测试题号目录" [ref=f2e43]:
              - button "第 1 题" [ref=f2e44] [cursor=pointer]
              - button "第 2 题" [ref=f2e45] [cursor=pointer]
              - button "第 3 题" [ref=f2e46] [cursor=pointer]
              - button "第 4 题" [ref=f2e47] [cursor=pointer]
              - button "第 5 题" [ref=f2e48] [cursor=pointer]
            - button "查看全部测试（含未关联课程）" [ref=f2e49] [cursor=pointer]
            - button "刷新测试目录与记录" [ref=f2e50] [cursor=pointer]
            - group [ref=f2e51]:
              - generic "数量关系参考测验：未审核内容的作答记录 · r1" [ref=f2e52]
              - paragraph [ref=f2e53]: 5 题 · 参考需审查
              - button "查看测试范围：数量关系参考测验：未审核内容的作答记录" [ref=f2e54] [cursor=pointer]
              - list [ref=f2e55]:
                - listitem [ref=f2e56]:
                  - button "开卷测试 · 已放弃 · 9/28/2026, 8:53:38 AM" [ref=f2e57] [cursor=pointer]
        - generic [ref=f2e58]:
          - button "笔记" [ref=f2e59] [cursor=pointer]
          - button "创作" [ref=f2e60] [cursor=pointer]
          - button "设置" [ref=f2e61] [cursor=pointer]
    - separator "导航栏宽度" [ref=f2e62]
    - main [ref=f2e63]:
      - tablist "打开的学习对象" [ref=f2e64]:
        - tab "测试题" [ref=f2e65] [cursor=pointer]
        - generic [ref=f2e66]:
          - tab "已固定lesson_nativeassessmentopen · r1" [ref=f2e67] [cursor=pointer]: ⌖ lesson_nativeassessmentopen · r1
          - button "固定标签 lesson_nativeassessmentopen · r1" [ref=f2e68] [cursor=pointer]: ⌖
          - button "关闭标签 lesson_nativeassessmentopen · r1" [ref=f2e69] [cursor=pointer]: ×
        - generic [ref=f2e70]:
          - tab "已固定测试范围 · r1" [ref=f2e71] [cursor=pointer]: ⌖ 测试范围 · r1
          - button "固定标签 测试范围 · r1" [ref=f2e72] [cursor=pointer]: ⌖
          - button "关闭标签 测试范围 · r1" [ref=f2e73] [cursor=pointer]: ×
        - generic [ref=f2e74]:
          - tab "已固定测试作答 · r1" [selected] [ref=f2e75] [cursor=pointer]: ⌖ 测试作答 · r1
          - button "固定标签 测试作答 · r1" [ref=f2e76] [cursor=pointer]: ⌖
          - button "关闭标签 测试作答 · r1" [ref=f2e77] [cursor=pointer]: ×
      - article [ref=f2e79]:
        - generic [ref=f2e80]: 测试 · 冻结作答实例
        - heading "本次测试作答" [level=1] [ref=f2e81]
        - generic [ref=f2e82]:
          - strong [ref=f2e83]: 开卷测试 · 已放弃
          - status [ref=f2e84]: 服务端作答已保存
          - generic [ref=f2e85]: 本机草稿存储可用
        - paragraph [ref=f2e86]: 会话修订 3。已放弃，不计为独立测试零分。
        - paragraph [ref=f2e87]: 冻结策略：获准材料可读；Agent 仅固定操作帮助；联网未获许可；标准答案按服务端冻结策略放行，实际已释放内容显示在评分结果中。
        - generic [ref=f2e88]:
          - button "打开本次测试复盘" [disabled] [ref=f2e89]
          - button "重新读取测试状态" [ref=f2e90] [cursor=pointer]
          - button "立即保存测试作答" [disabled] [ref=f2e91]
        - navigation "本次测试题目" [ref=f2e92]:
          - button "第 1 题" [ref=f2e93] [cursor=pointer]
          - button "第 2 题 · 已填写" [ref=f2e94] [cursor=pointer]
          - button "第 3 题" [ref=f2e95] [cursor=pointer]
          - button "第 4 题" [ref=f2e96] [cursor=pointer]
          - button "第 5 题" [ref=f2e97] [cursor=pointer]
        - generic [ref=f2e98]:
          - heading "第 2 题 · 文本填空" [level=2] [ref=f2e99]
          - paragraph [ref=f2e100]: 修订 1 · 概念回忆 · 按冻结内容状态核对；最终数值与推导依据分别判断
          - group [ref=f2e101]:
            - generic "题目引用与概念" [ref=f2e102]
          - paragraph [ref=f2e104]:
            - text: 等式
            - generic "公式：a+b=b+a" [ref=f2e105]
            - text: 表达加法的哪一种性质？
          - paragraph [ref=f2e134]: 作答格式：填写性质的中文名称。
          - group "第 2 题作答" [ref=f2e135]:
            - generic [ref=f2e137]:
              - text: 答案
              - textbox "第 2 题答案" [disabled] [ref=f2e138]: 放弃前已保存的原创答案
            - generic [ref=f2e139]:
              - text: 推导步骤（可选）
              - textbox "第 2 题推导步骤" [disabled] [ref=f2e140]
            - text: 答案最多 4,000 个字符；步骤最多 20,000 个字符。表达式按原文保存，尚不做评分判定。
        - generic [ref=f2e141]:
          - heading "测试结束状态" [level=2] [ref=f2e142]
          - paragraph [ref=f2e143]: 已放弃 · 无分数。测试作答不可修改；本机候选单独保留。
        - group [ref=f2e144]:
          - generic "本次测试的冻结引用与范围" [ref=f2e145]
    - separator "Agent 栏宽度" [ref=f2e146]
    - complementary "Agent 助教" [ref=f2e147]:
      - generic [ref=f2e148]:
        - heading "Agent · 固定操作帮助" [level=2] [ref=f2e149]
        - paragraph [ref=f2e150]: 本次测试仅允许操作帮助，未调用模型或联网。
        - list [ref=f2e151]:
          - listitem [ref=f2e152]: 用题号目录或 Tab 键移动，作答会自动保存并明确显示状态。
          - listitem [ref=f2e153]: 离线或版本冲突时保留本机候选；重新读取后先比较，再明确恢复。
          - listitem [ref=f2e154]: 提交前确认作答已保存；关闭标签或浏览器不会提交。
          - listitem [ref=f2e155]: 可明确放弃当前测试；放弃不计为独立零分。
        - paragraph [ref=f2e156]: 模型：未调用 · 联网：未调用 · 标准答案：未请求
      - region "问答任务停止控制" [ref=f2e157]:
        - heading "已有问答任务的停止控制" [level=3] [ref=f2e158]
        - paragraph [ref=f2e159]: 此处只读取任务 ID、状态与版本。取消请求不等于远端已停止。
        - generic [ref=f2e160]:
          - text: 已有 Tutor 任务 ID
          - textbox "已有 Tutor 任务 ID" [ref=f2e161]
        - button "读取此任务控制" [disabled] [ref=f2e162]
  - status [ref=f2e163]:
    - generic [ref=f2e164]: ✓ UI 会话已保存
    - generic [ref=f2e165]: 内容修订 1
    - generic [ref=f2e166]: 开卷测试 · 已放弃 · 本机
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
> 29 |   if (await switchRole.count()) await switchRole.click()
     |                                                  ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
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