# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: workbench-initial-recovery.spec.ts >> initial workbench recovery keeps the saved lesson and waits for the real session at 1440px
- Location: tests/e2e/workbench-initial-recovery.spec.ts:6:3

# Error details

```
Error: route.fulfill: Route is already handled!
```

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: '正在恢复工作台', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('heading', { name: '正在恢复工作台', exact: true }) with timeout 5000ms
  - waiting for getByRole('heading', { name: '正在恢复工作台', exact: true })

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
  - text: 未配置模型
  - group:
    - text: 当前上下文
    - paragraph: 尚未选择学习对象
  - heading "围绕当前内容，一起思考" [level=3]
  - paragraph: 模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。
  - paragraph: 现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。
  - button "讲解" [pressed]
  - button "提示"
  - button "推导"
  - button "拓展"
  - text: 问题草稿
  - textbox "问题草稿" [disabled]:
    - /placeholder: 正在确认本机会话或处理草稿选择…
  - text: 联网：未授权
  - button "发送 ↑" [disabled]
  - text: 草稿保留在本机浏览器，尚未发送。
- status: 连接本机服务… 尚未选择对象 正常学习 · 本机
```

# Test source

```ts
  1  | import { test, expect, type Route } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { createHash } from 'node:crypto'
  3  | import { bootstrap } from './helpers'
  4  | 
  5  | for (const width of [1440, 390]) {
  6  |   test(`initial workbench recovery keeps the saved lesson and waits for the real session at ${width}px`, async ({ page }, info) => {
  7  |     await bootstrap(page)
  8  |     await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  9  |     await page.getByRole('button', { name: '浏览合成示例课程' }).click()
  10 |     await page.getByRole('button', { name: '打开示例小节' }).click()
  11 |     await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  12 |     await expect(page.locator('.reader-content h1')).toContainText('1.3')
  13 |     await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  14 |     await page.setViewportSize({ width, height: 900 })
  15 | 
  16 |     let release!: () => void, received!: () => void
  17 |     const delivery = new Promise<void>(resolve => { release = resolve })
  18 |     const upstreamReady = new Promise<void>(resolve => { received = resolve })
  19 |     let intercepted = false, writesWhileReading = 0, held = true, originalBodySha = '', deliveredBodySha = ''
  20 |     let savedCourse: unknown, savedLesson: unknown
  21 |     page.on('request', request => { if (held && request.method() === 'PUT' && new URL(request.url()).pathname === '/api/v1/workbench/session') writesWhileReading++ })
  22 |     const handler = async (route: Route) => {
  23 |       if (route.request().method() !== 'GET' || intercepted) { await route.continue(); return }
  24 |       intercepted = true
  25 |       const response = await route.fetch(), body = await response.body()
  26 |       expect(response.status()).toBe(200)
  27 |       const saved = JSON.parse(body.toString())
  28 |       savedCourse = saved.course_ref
  29 |       savedLesson = saved.tabs.find((tab: { id: string }) => tab.id === saved.active_tab_id)?.context.active_ref
  30 |       originalBodySha = createHash('sha256').update(body).digest('hex')
  31 |       received()
  32 |       await delivery
  33 |       deliveredBodySha = createHash('sha256').update(body).digest('hex')
  34 |       await route.fulfill({ response, body })
  35 |     }
  36 |     await page.route('**/api/v1/workbench/session', handler)
  37 |     try {
  38 |       await page.reload()
  39 |       await upstreamReady
> 40 |       await expect(page.getByRole('heading', { name: '正在恢复工作台', exact: true })).toBeVisible()
     |                                                                                 ^ Error: expect(locator).toBeVisible() failed
  41 |       await expect(page.getByText('正在读取工作台状态，完成后可继续操作。', { exact: true })).toBeVisible()
  42 |       await expect(page.getByRole('navigation', { name: '学习主导航' })).toHaveCount(0)
  43 |       expect(writesWhileReading).toBe(0)
  44 |       expect(savedCourse).toMatchObject({ entity: 'course', id: 'synthetic_course_layout' })
  45 |       expect(savedLesson).toMatchObject({ entity: 'lesson', id: 'synthetic_lesson_1_3' })
  46 |       await info.attach(`initial-workbench-loading-${width}`, { body: await page.screenshot(), contentType: 'image/png' })
  47 |       held = false; release()
  48 |       await expect(page.locator('.reader-content h1')).toContainText('1.3')
  49 |       await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  50 |       expect(deliveredBodySha).toBe(originalBodySha)
  51 |       if (width < 820) await page.getByRole('button', { name: '切换导航栏' }).click()
  52 |       await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
  53 |       if (width < 820) await page.getByRole('button', { name: '切换导航栏' }).click()
  54 |       await page.getByRole('button', { name: '继续浏览示例' }).click()
  55 |       await expect(page.locator('.reader-content h1')).toContainText('1.3')
  56 |       await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  57 |       const current = await page.evaluate(async () => {
  58 |         const response = await fetch('/api/v1/workbench/session')
  59 |         if (!response.ok) throw new Error('Expected a readable saved workbench session')
  60 |         return response.json()
  61 |       })
  62 |       expect(current.course_ref).toEqual(savedCourse)
  63 |       expect(current.tabs.find((tab: { id: string }) => tab.id === current.active_tab_id)?.context.active_ref).toEqual(savedLesson)
  64 |     } finally { held = false; release(); await page.unroute('**/api/v1/workbench/session', handler) }
  65 |   })
  66 | }
  67 | 
```