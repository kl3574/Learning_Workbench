# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: routes-controlled.spec.ts >> real route creation, reminder, manual false, reordered revision and exact target navigation preserve history
- Location: ../m42-route-save-diagnosis/routes-controlled.spec.ts:10:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('dialog', { name: '创建路线', exact: true }).getByRole('button', { name: '打开已保存路线', exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - link "跳到学习内容" [ref=e4] [cursor=pointer]:
    - /url: "#reader-main"
  - banner [ref=e5]:
    - link "知径 学习工作台" [ref=e6] [cursor=pointer]:
      - /url: "#"
      - generic [aria-hidden] [ref=e7]: 径
      - strong [ref=e8]: 知径
      - generic [ref=e9]: 学习工作台
    - button "搜索与命令 Ctrl ⇧ P" [ref=e10] [cursor=pointer]:
      - generic [aria-hidden] [ref=e11]: ⌕
      - text: 搜索与命令
      - generic [ref=e12]: Ctrl ⇧ P
    - generic [ref=e13]:
      - button "切换导航栏" [expanded] [ref=e14] [cursor=pointer]: 目录
      - button "切换 Agent 栏" [expanded] [ref=e15] [cursor=pointer]: Agent
      - button "专注" [ref=e16] [cursor=pointer]
      - button "导入" [ref=e17] [cursor=pointer]
  - generic [ref=e18]:
    - complementary "课程导航" [ref=e19]:
      - generic [ref=e20]:
        - generic [ref=e21]:
          - generic [ref=e22]: 学习路线
          - heading "目标与任务顺序" [level=2] [ref=e23]
          - paragraph [ref=e24]: 阅读、自报、参与和独立证据分别记录。
          - button "学习目标与基础" [ref=e25] [cursor=pointer]
        - navigation "学习主导航" [ref=e26]:
          - button "学习路线" [ref=e27] [cursor=pointer]:
            - generic [aria-hidden] [ref=e28]: ↗
          - button "教材 含例题" [ref=e30] [cursor=pointer]:
            - generic [aria-hidden] [ref=e31]: ▤
            - generic [ref=e32]: 教材
            - generic [ref=e33]: 含例题
          - button "习题 含解答" [ref=e34] [cursor=pointer]:
            - generic [aria-hidden] [ref=e35]: ✎
            - generic [ref=e36]: 习题
            - generic [ref=e37]: 含解答
          - button "测试题" [ref=e38] [cursor=pointer]:
            - generic [aria-hidden] [ref=e39]: ☑
        - region "学习路线目录" [ref=e41]:
          - generic [ref=e42]:
            - heading "路线与历史修订" [level=2] [ref=e43]
            - button "刷新路线" [ref=e44] [cursor=pointer]
          - generic [ref=e45]:
            - paragraph [ref=e46]: 尚无正式学习路线。
            - list
            - generic [ref=e47]:
              - button "创建路线" [ref=e48] [cursor=pointer]
              - button "学习建议" [ref=e49] [cursor=pointer]
              - button "查看概念与技能证据" [ref=e50] [cursor=pointer]
        - generic [ref=e51]:
          - button "笔记" [ref=e52] [cursor=pointer]
          - button "创作" [ref=e53] [cursor=pointer]
          - button "设置" [ref=e54] [cursor=pointer]
    - separator "导航栏宽度" [ref=e55]
    - main [ref=e56]:
      - tablist "打开的学习对象" [ref=e57]:
        - tab "学习路线" [selected] [ref=e58] [cursor=pointer]
      - generic [ref=e59]:
        - heading "从学习目标开始" [level=1] [ref=e60]
        - paragraph [ref=e61]: 路线把真实教材、练习和测试排成任务顺序。先修提醒帮助选择顺序，完成标记不代表掌握。
        - paragraph [ref=e62]: 尚无正式学习路线。
        - generic [ref=e63]:
          - button "创建路线" [ref=e64] [cursor=pointer]
          - button "学习建议" [ref=e65] [cursor=pointer]
          - button "学习目标与基础" [ref=e66] [cursor=pointer]
          - button "查看概念与技能证据" [ref=e67] [cursor=pointer]
        - list
    - separator "Agent 栏宽度" [ref=e68]
    - complementary "Agent 助教" [ref=e69]:
      - generic [ref=e70]:
        - generic [ref=e71]:
          - heading "Agent" [level=2] [ref=e72]
          - generic [ref=e73]: 未配置模型
        - group [ref=e74]:
          - generic "当前上下文" [ref=e75] [cursor=pointer]
          - paragraph [ref=e76]: 尚未选择学习对象
        - generic [ref=e77]:
          - generic [aria-hidden] [ref=e78]: ✦
          - heading "围绕当前内容，一起思考" [level=3] [ref=e79]
          - paragraph [ref=e80]: 模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。
          - paragraph [ref=e81]: 现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。
        - generic [ref=e82]:
          - generic "教学意图" [ref=e83]:
            - button "讲解" [pressed] [ref=e84] [cursor=pointer]
            - button "提示" [ref=e85] [cursor=pointer]
            - button "推导" [ref=e86] [cursor=pointer]
            - button "拓展" [ref=e87] [cursor=pointer]
          - generic [ref=e88]: 问题草稿
          - textbox "问题草稿" [ref=e89]:
            - /placeholder: 写下问题，草稿按当前对象保留…
          - generic [ref=e90]:
            - generic [ref=e91]: 联网：未授权
            - button "发送 ↑" [disabled] [ref=e92]
          - generic [ref=e93]: 草稿保留在本机浏览器，尚未发送。
  - status [ref=e94]:
    - generic [ref=e95]: ✓ UI 会话已保存
    - generic [ref=e96]: 尚未选择对象
    - generic [ref=e97]: 正常学习 · 本机
  - dialog "创建路线" [ref=e98]:
    - generic [ref=e99]:
      - banner [ref=e100]:
        - heading "创建路线" [level=2] [ref=e101]
        - button "关闭创建路线" [ref=e102] [cursor=pointer]: ×
      - region "路线编辑" [ref=e103]:
        - paragraph [ref=e104]: 任务绑定真实内容的精确修订。保存生成新路线修订；旧路线与旧人工完成记录保留，先修只作提醒。
        - status [ref=e105]: 本机路线草稿存储可用
        - alert [ref=e106]: 请填写路线名称、目标，并添加至少一个有标题的任务。
        - group "路线内容" [ref=e107]:
          - generic [ref=e109]:
            - text: 路线名称
            - textbox "路线名称" [ref=e110]: 原创路线与精确任务
          - generic [ref=e111]:
            - text: 学习目标
            - textbox "路线学习目标" [ref=e112]
          - generic [ref=e113]:
            - text: 添加真实学习任务
            - combobox "添加学习任务" [ref=e114]:
              - option "选择精确课程内容、习题或测试" [selected]
              - option "教材 · 原创练习验收教材 routeuinative r1 / 数量关系与基本运算：参考练习 r1"
              - option "内容块 · 数量关系与基本运算：参考练习 / 数量、步骤与单位 r1"
              - option "习题 · 五类参考练习：作答与帮助记录 r1"
              - option "测试 · 数量关系参考测验：未审核内容的作答记录 r1"
          - list [ref=e115]:
            - listitem [ref=e116]:
              - generic [ref=e117]:
                - text: 任务 1 标题
                - textbox "任务 1 标题" [ref=e118]: 先读精确小节
              - paragraph [ref=e119]: lesson · lesson_routeuinative · r1
              - generic [ref=e120]:
                - text: 完成规则
                - combobox "任务 1 完成规则" [ref=e121]:
                  - option "仅人工标记"
                  - option "明确标记阅读完成" [selected]
              - group [ref=e122]:
                - generic "先修提醒（不锁定学习入口）" [ref=e123] [cursor=pointer]
              - generic [ref=e124]:
                - button "上移任务 1" [disabled] [ref=e125]: 上移
                - button "下移任务 1" [ref=e126] [cursor=pointer]: 下移
                - button "删除任务 1" [ref=e127] [cursor=pointer]: 删除任务
            - listitem [ref=e128]:
              - generic [ref=e129]:
                - text: 任务 2 标题
                - textbox "任务 2 标题" [ref=e130]: 练习提醒可跳过
              - paragraph [ref=e131]: practice_set · practice_routeuinative · r1
              - generic [ref=e132]:
                - text: 完成规则
                - combobox "任务 2 完成规则" [ref=e133]:
                  - option "仅人工标记"
                  - option "提交本次习题练习" [selected]
              - group [ref=e134]:
                - generic "先修提醒（不锁定学习入口）" [ref=e135] [cursor=pointer]
                - generic [ref=e136]:
                  - checkbox "先读精确小节" [checked] [ref=e137]
                  - text: 先读精确小节
              - generic [ref=e138]:
                - button "上移任务 2" [ref=e139] [cursor=pointer]: 上移
                - button "下移任务 2" [disabled] [ref=e140]: 下移
                - button "删除任务 2" [ref=e141] [cursor=pointer]: 删除任务
        - generic [ref=e142]:
          - button "保存路线新修订" [active] [ref=e143] [cursor=pointer]
          - button "重试原路线保存命令" [ref=e144] [cursor=pointer]
```

# Test source

```ts
  1  | import { expect, test as base } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { writeFileSync } from 'node:fs'
  3  | import { RestartRuntime } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/tests/e2e/restartRuntime.ts'
  4  | import { originalAssessmentPackage, importAssessmentPackage } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/tests/e2e/assessmentTestData.ts'
  5  | import type { PageRoute } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/packages/contracts/generated/api-types.ts'
  6  | const test = base.extend<{ runtime: RestartRuntime }>({
  7  |   runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  8  |   page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
  9  | })
  10 | test('real route creation, reminder, manual false, reordered revision and exact target navigation preserve history', async ({ page }, info) => {
  11 |   const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  12 |   const fixture = originalAssessmentPackage('routeuinative', 'learner'), imported = await importAssessmentPackage(page, fixture); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click(); await page.getByRole('navigation', { name: '学习主导航', exact: true }).getByRole('button', { name: '学习路线', exact: true }).click()
  13 |   await page.getByRole('button', { name: '创建路线', exact: true }).first().click(); const editor = page.getByRole('dialog', { name: '创建路线', exact: true }); await editor.getByRole('button', { name: '填写新路线', exact: true }).click(); await editor.getByLabel('路线名称', { exact: true }).fill('原创路线与精确任务'); await editor.getByLabel('路线学习目标', { exact: true }).fill('先读再练；提醒不锁定，人工标记不授予能力。')
  14 |   const refValue = (ref: typeof fixture.lesson) => `${ref.entity}:${ref.id}:${ref.revision}:${ref.sha256}`
  15 |   await expect(editor.getByLabel('添加学习任务').locator(`option[value="${refValue(fixture.lesson)}"]`)).toHaveCount(1); await editor.getByLabel('添加学习任务').selectOption(refValue(fixture.lesson)); await editor.getByLabel('添加学习任务').selectOption(refValue(fixture.practice)); await editor.getByLabel('任务 1 标题').fill('先读精确小节'); await editor.getByLabel('任务 2 标题').fill('练习提醒可跳过')
> 16 |   const second = editor.locator('.route-editor-steps>li').nth(1); await second.locator('summary').click(); await second.getByRole('checkbox', { name: '先读精确小节', exact: true }).check(); await editor.getByRole('button', { name: '保存路线新修订', exact: true }).click(); await editor.getByRole('button', { name: '打开已保存路线', exact: true }).click(); await expect(page.getByRole('heading', { name: '原创路线与精确任务', exact: true })).toBeVisible()
     |                                                                                                                                                                                                                                                                                                                                        ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  17 |   const first: PageRoute = await page.request.get('/api/v1/routes?limit=100').then(response => response.json()); expect(first.items).toHaveLength(1); expect(first.items[0].steps.map(step => step.target)).toEqual([fixture.lesson, fixture.practice]); const r1 = first.item_refs[0]
  18 |   await expect(page.getByText('先修提醒：先读精确小节尚未完成；仍可打开本任务。', { exact: true })).toBeVisible(); await page.getByRole('button', { name: '打开任务：练习提醒可跳过', exact: true }).click(); await expect.poll(() => new URL(page.url()).searchParams.has('practice')).toBe(true); const practice = JSON.parse(new URL(page.url()).searchParams.get('practice')!); expect(practice.practice_ref).toEqual(fixture.practice); expect(practice.lesson_ref).toEqual(fixture.lesson); expect(practice.course_ref).toEqual(fixture.course)
  19 |   await page.getByRole('tab', { name: /原创路线与精确任务/ }).click(); await page.getByRole('button', { name: '手动标为未完成：先读精确小节', exact: true }).click(); await page.getByRole('button', { name: '确认保存人工标记', exact: true }).click(); await expect(page.getByText(/人工未完成优先保留/)).toBeVisible()
  20 |   await page.getByRole('button', { name: '编辑路线并保存新修订', exact: true }).click(); const edit = page.getByRole('dialog', { name: '编辑路线', exact: true }); await edit.getByRole('button', { name: '编辑此路线修订', exact: true }).click(); await edit.getByRole('button', { name: '上移任务 2', exact: true }).click(); await edit.getByRole('button', { name: '保存路线新修订', exact: true }).click(); await edit.getByRole('button', { name: '打开已保存路线', exact: true }).click()
  21 |   const final: PageRoute = await page.request.get('/api/v1/routes?limit=100').then(response => response.json()); expect(final.items).toHaveLength(2); expect(final.items.find(item => item.revision === 1)).toEqual(first.items[0]); const r2 = final.items.find(item => item.revision === 2)!; expect(r2.steps.map(step => step.id)).toEqual([...first.items[0].steps.map(step => step.id)].reverse()); const progress = await page.request.get('/api/v1/learning/progress').then(response => response.json()); const old = progress.route_steps.find((item: { route_ref: { id: string; revision: number }; step_id: string }) => item.route_ref.id === r1.id && item.route_ref.revision === 1 && item.step_id === first.items[0].steps[0].id); expect(old.manual_override).toBe(false); expect(progress.route_steps.filter((item: { route_ref: { revision: number }; manual_override: boolean | null }) => item.route_ref.revision === 2).every((item: { manual_override: boolean | null }) => item.manual_override === null)).toBe(true)
  22 |   await page.screenshot({ path: info.outputPath('route-reordered-1440.png') }); await page.setViewportSize({ width: 390, height: 844 }); await page.getByRole('heading', { name: '原创路线与精确任务', exact: true }).scrollIntoViewIfNeeded(); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); await page.screenshot({ path: info.outputPath('route-reordered-390.png') }); expect(errors).toEqual([])
  23 |   writeFileSync(info.outputPath('actual-route-ui.json'), JSON.stringify({ scope: 'original synthetic actual UI route POST/PUT and manual completion', versions: final.item_refs, original_content_unchanged: true, step_ids_preserved_by_reorder: true, old_manual_false_preserved: true, new_revision_does_not_inherit_manual: true, exact_navigation: practice, runtime_errors: errors }, null, 2))
  24 | })
  25 | 
  26 | import { startObserver, finishObserver } from './observer-controlled'
  27 | test.beforeEach(async ({ page }, info) => { await startObserver(page, info) })
  28 | test.afterEach(async ({ page }, info) => { await finishObserver(page, info) })
  29 | 
```