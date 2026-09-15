# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: workbench-initial-recovery.spec.ts >> initial workbench recovery keeps the saved lesson and waits for the real session at 390px
- Location: tests/e2e/workbench-initial-recovery.spec.ts:6:3

# Error details

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
  - link "知径":
    - /url: "#"
    - strong: 知径
  - button "搜索与命令"
  - button "切换导航栏": 目录
  - button "切换 Agent 栏": Agent
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
- status: 连接本机服务… 正常学习 · 本机
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
  16 |     let release!: () => void, received!: () => void, finished!: () => void
  17 |     const delivery = new Promise<void>(resolve => { release = resolve })
  18 |     const upstreamReady = new Promise<void>(resolve => { received = resolve })
  19 |     const responseHandled = new Promise<void>(resolve => { finished = resolve })
  20 |     let intercepted = false, writesWhileReading = 0, held = true, originalBodySha = '', deliveredBodySha = ''
  21 |     let savedCourse: unknown, savedLesson: unknown
  22 |     page.on('request', request => { if (held && request.method() === 'PUT' && new URL(request.url()).pathname === '/api/v1/workbench/session') writesWhileReading++ })
  23 |     const handler = async (route: Route) => {
  24 |       if (route.request().method() !== 'GET' || intercepted) { await route.continue(); return }
  25 |       intercepted = true
  26 |       try {
  27 |         const response = await route.fetch(), body = await response.body()
  28 |         expect(response.status()).toBe(200)
  29 |         const saved = JSON.parse(body.toString())
  30 |         savedCourse = saved.course_ref
  31 |         savedLesson = saved.tabs.find((tab: { id: string }) => tab.id === saved.active_tab_id)?.context.active_ref
  32 |         originalBodySha = createHash('sha256').update(body).digest('hex')
  33 |         received()
  34 |         await delivery
  35 |         deliveredBodySha = createHash('sha256').update(body).digest('hex')
  36 |         await route.fulfill({ response, body })
  37 |       } finally { finished() }
  38 |     }
  39 |     await page.route('**/api/v1/workbench/session', handler)
  40 |     try {
  41 |       await page.reload()
  42 |       await upstreamReady
> 43 |       await expect(page.getByRole('heading', { name: '正在恢复工作台', exact: true })).toBeVisible()
     |                                                                                 ^ Error: expect(locator).toBeVisible() failed
  44 |       await expect(page.getByText('正在读取工作台状态，完成后可继续操作。', { exact: true })).toBeVisible()
  45 |       await expect(page.getByRole('navigation', { name: '学习主导航' })).toHaveCount(0)
  46 |       expect(writesWhileReading).toBe(0)
  47 |       expect(savedCourse).toMatchObject({ entity: 'course', id: 'synthetic_course_layout' })
  48 |       expect(savedLesson).toMatchObject({ entity: 'lesson', id: 'synthetic_lesson_1_3' })
  49 |       await info.attach(`initial-workbench-loading-${width}`, { body: await page.screenshot(), contentType: 'image/png' })
  50 |       held = false; release()
  51 |       await expect(page.locator('.reader-content h1')).toContainText('1.3')
  52 |       await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  53 |       expect(deliveredBodySha).toBe(originalBodySha)
  54 |       if (width < 820) await page.getByRole('button', { name: '切换导航栏' }).click()
  55 |       await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
  56 |       if (width < 820) await page.getByRole('button', { name: '切换导航栏' }).click()
  57 |       await page.getByRole('button', { name: '继续浏览示例' }).click()
  58 |       await expect(page.locator('.reader-content h1')).toContainText('1.3')
  59 |       await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  60 |       const current = await page.evaluate(async () => {
  61 |         const response = await fetch('/api/v1/workbench/session')
  62 |         if (!response.ok) throw new Error('Expected a readable saved workbench session')
  63 |         return response.json()
  64 |       })
  65 |       expect(current.course_ref).toEqual(savedCourse)
  66 |       expect(current.tabs.find((tab: { id: string }) => tab.id === current.active_tab_id)?.context.active_ref).toEqual(savedLesson)
  67 |     } finally { held = false; release(); if (intercepted) await responseHandled; await page.unroute('**/api/v1/workbench/session', handler) }
  68 |   })
  69 | }
  70 | 
```