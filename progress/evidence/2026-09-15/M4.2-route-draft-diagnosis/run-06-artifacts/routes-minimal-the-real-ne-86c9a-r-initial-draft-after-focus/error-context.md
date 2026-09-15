# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: routes-minimal.spec.ts >> the real new-route goal survives delivery of its own earlier initial draft after focus
- Location: ../m42-route-save-diagnosis/routes-minimal.spec.ts:10:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: "先读再练；提醒不锁定，人工标记不授予能力。"
Received: ""
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
        - group "路线内容" [ref=e106]:
          - generic [ref=e108]:
            - text: 路线名称
            - textbox "路线名称" [ref=e109]: 原创路线与精确任务
          - generic [ref=e110]:
            - text: 学习目标
            - textbox "路线学习目标" [ref=e111]
          - generic [ref=e112]:
            - text: 添加真实学习任务
            - combobox "添加学习任务" [ref=e113]:
              - option "选择精确课程内容、习题或测试" [selected]
          - paragraph [ref=e114]: 尚无可添加的真实材料。可以先导入教材，再创建路线；未编造任务目标。
          - list
        - button "保存路线新修订" [ref=e116] [cursor=pointer]
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
  10 | test('the real new-route goal survives delivery of its own earlier initial draft after focus', async ({page}) => {
  11 |   await page.getByRole('button', { name: '创建路线', exact: true }).first().click()
  12 |   const editor = page.getByRole('dialog', { name: '创建路线', exact: true })
  13 |   await editor.getByRole('button', { name: '填写新路线', exact: true }).click()
  14 |   await editor.getByLabel('路线名称', { exact: true }).fill('原创路线与精确任务')
  15 |   await expect.poll(() => page.evaluate(() => ((window as Window & { __routeStoreGate?: { events: {kind:string}[] } }).__routeStoreGate?.events ?? []).some(value => value.kind === 'actual_initial_save_completed_result_held'))).toBe(true)
  16 |   const goal = editor.getByLabel('路线学习目标', { exact: true })
  17 |   await goal.fill('先读再练；提醒不锁定，人工标记不授予能力。')
> 18 |   expect(await goal.inputValue()).toBe('先读再练；提醒不锁定，人工标记不授予能力。')
     |                                   ^ Error: expect(received).toBe(expected) // Object.is equality
  19 | })
  20 | import { startObserver, finishObserver } from './observer-controlled-min'
  21 | test.beforeEach(async ({ page }, info) => { await startObserver(page, info) })
  22 | test.afterEach(async ({ page }, info) => { await finishObserver(page, info) })
  23 | 
```