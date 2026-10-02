# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: import-policy-probe.spec.ts >> original grading recovery import command while real Policy response is held
- Location: tests/e2e/import-policy-probe.spec.ts:6:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。', { exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。', { exact: true }) with timeout 5000ms
  - waiting for getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。', { exact: true })

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
- dialog "导入":
  - banner:
    - heading "导入" [level=2]
    - button "关闭导入": ×
  - status:
    - paragraph: 正在核验导入访问权限。测试限制期间，材料预览与原件下载暂不可用。
    - paragraph: 当前导入记录、已选择的本机文件与未提交设置仍保留。权限恢复后会重新读取服务端内容。
  - button "打开候选审核与恢复"
```

# Test source

```ts
  1  | import { writeFileSync } from 'node:fs'
  2  | import { expect, test, type Route } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3  | import { RestartRuntime } from './restartRuntime'
  4  | import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
  5  | 
  6  | test('original grading recovery import command while real Policy response is held', async ({ playwright }, info) => {
  7  |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('gradingrecover')
  8  |   const facts: Record<string, unknown> = { baseline: 'c2f47a2778bb6a78c73237f8bb89fb271dfedcd6', fixture: 'originalAssessmentPackage(gradingrecover)', original_helper_unchanged: true, original_role_assertion_timeout_ms: 5000 }
  9  |   let release!: () => void, released = false, requests = 0, held = 0
  10 |   const gate = new Promise<void>(yes => { release = yes }), deliveries: Promise<void>[] = []
  11 |   const releaseGate = () => { released = true; release() }
  12 |   try {
  13 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  14 |     const handler = (route: Route) => {
  15 |       const delivery = (async () => {
  16 |         if (route.request().method() !== 'GET' || ++requests === 1 || released) { await route.continue(); return }
  17 |         const response = await route.fetch(); expect(response.status()).toBe(200)
  18 |         const body = await response.json(); facts.actual_server_policy = { independent: body.active_independent_attempt_id, open_book: body.active_open_book_attempt_id, role: body.role }
  19 |         held++; await gate; await route.fulfill({ response })
  20 |       })(); deliveries.push(delivery); return delivery
  21 |     }
  22 |     await page.route('**/api/v1/session', handler)
  23 |     await runtime.authenticateOnly(page)
  24 |     await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toBeVisible()
  25 |     await expect.poll(() => held).toBeGreaterThan(0)
  26 |     facts.ui_saved_while_policy_unknown = true
  27 |     facts.topbar_disabled = await page.locator('.import-trigger').isDisabled()
  28 |     let rejected: unknown
  29 |     const importing = importAssessmentPackage(page, fixture).catch(error => { rejected = error; return null })
> 30 |     await expect(page.getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。', { exact: true })).toBeVisible()
     |                                                                                    ^ Error: expect(locator).toBeVisible() failed
  31 |     facts.original_palette_click_rejected = true
  32 |     releaseGate()
  33 |     await expect(page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })).toHaveCount(0)
  34 |     await expect(page.locator('.import-trigger')).toBeEnabled()
  35 |     facts.policy_recovered_before_role_assertion_end = true
  36 |     await importing
  37 |     facts.dialog_count_after_original_assertion = await page.getByRole('dialog', { name: '导入', exact: true }).count()
  38 |     facts.original_assertion_failed = !!rejected
  39 |     await page.screenshot({ path: info.outputPath('held-policy-original-import.png') })
  40 |     if (rejected) throw rejected
  41 |   } finally {
  42 |     releaseGate(); await Promise.allSettled(deliveries); facts.held_responses = held
  43 |     writeFileSync(info.outputPath('held-policy-original-import.json'), JSON.stringify(facts, null, 2) + '\n')
  44 |     await runtime.close()
  45 |   }
  46 | })
  47 | 
```