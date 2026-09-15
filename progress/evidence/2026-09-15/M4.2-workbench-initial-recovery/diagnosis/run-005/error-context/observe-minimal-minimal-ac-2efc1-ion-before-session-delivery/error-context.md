# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: observe-minimal.spec.ts >> minimal actual saved lesson survives reload navigation before session delivery
- Location: ../m42-continue-reading-diagnosis/observe-minimal.spec.ts:8:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('button', { name: '继续浏览示例' })
Expected: visible
Timeout: 1000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('button', { name: '继续浏览示例' }) with timeout 1000ms
  - waiting for getByRole('button', { name: '继续浏览示例' })

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
- status:
  - text: 服务端会话已变化。基准、本地待同步与服务端会话如下；请选择保留的版本。
  - button "读取服务端会话，保留草稿"
- region "会话三方比较":
  - group:
    - text: 比较会话版本并明确选择
    - paragraph: 原基准是编辑开始时已确认的会话。本地一栏包含尚未确认的修改；采用任一版本都保留问题草稿。
    - table:
      - rowgroup:
        - row "项目 原基准（未知） 本地待同步 服务端（版本 3）":
          - columnheader "项目"
          - columnheader "原基准（未知）"
          - columnheader "本地待同步"
          - columnheader "服务端（版本 3）"
      - rowgroup:
        - row "课程 未保存该基准，无法比较 未选择课程 合成示例课程":
          - rowheader "课程"
          - cell "未保存该基准，无法比较"
          - cell "未选择课程"
          - cell "合成示例课程"
        - row "当前入口 未保存该基准，无法比较 习题 教材":
          - rowheader "当前入口"
          - cell "未保存该基准，无法比较"
          - cell "习题"
          - cell "教材"
        - row "导航栏 未保存该基准，无法比较 展开，300 像素 展开，300 像素":
          - rowheader "导航栏"
          - cell "未保存该基准，无法比较"
          - cell "展开，300 像素"
          - cell "展开，300 像素"
        - row "Agent 栏 未保存该基准，无法比较 展开，368 像素 展开，368 像素":
          - rowheader "Agent 栏"
          - cell "未保存该基准，无法比较"
          - cell "展开，368 像素"
          - cell "展开，368 像素"
        - row "打开的内容 未保存该基准，无法比较 没有打开的内容 1.3 从一个简单例子开始理解推导中的条件与边界 · 修订 1（当前）":
          - rowheader "打开的内容"
          - cell "未保存该基准，无法比较"
          - cell "没有打开的内容"
          - cell "1.3 从一个简单例子开始理解推导中的条件与边界 · 修订 1（当前）"
        - row "目录位置 未保存该基准，无法比较 距顶部 0 像素，展开 0 项 距顶部 0 像素，展开 1 项":
          - rowheader "目录位置"
          - cell "未保存该基准，无法比较"
          - cell "距顶部 0 像素，展开 0 项"
          - cell "距顶部 0 像素，展开 1 项"
        - row "阅读位置 未保存该基准，无法比较 没有当前内容 距顶部 0 像素":
          - rowheader "阅读位置"
          - cell "未保存该基准，无法比较"
          - cell "没有当前内容"
          - cell "距顶部 0 像素"
    - button "采用本地会话并重新保存"
    - button "采用服务端会话，放弃本地 UI 修改"
- complementary "课程导航":
  - text: 当前课程
  - button "尚未选择课程"
  - paragraph: 从自己的学习目标开始
  - text: 暂无已读取的阅读记录 · 未诊断
  - navigation "学习主导航":
    - button "学习路线"
    - button "教材 含例题"
    - button "习题 含解答"
    - button "测试题"
  - region "当前教材目录":
    - heading "上下文目录" [level=2]
    - paragraph: 尚未选择教材。导入材料或选择已导入课程开始阅读。
    - button "导入资料"
    - button "加载合成示例课程"
    - paragraph: 尚无已审核习题
  - button "笔记"
  - button "创作"
  - button "设置"
- separator "导航栏宽度"
- main:
  - tablist "打开的学习对象":
    - tab "习题" [selected]
  - text: 习题
  - heading "选择习题，开始一次练习" [level=1]
  - paragraph: 从左侧当前课程的习题目录选择参考题集。明确开始后才创建作答会话，参考解答保持隐藏。
  - button "选择课程"
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
  - textbox "问题草稿":
    - /placeholder: 写下问题，草稿按当前对象保留…
  - text: 联网：未授权
  - button "发送 ↑" [disabled]
  - text: 草稿保留在本机浏览器，尚未发送。
- status: 会话版本冲突 尚未选择对象 正常学习 · 本机
```

# Test source

```ts
  1  | import { test, expect } from '<acceptance-cache>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { bootstrap } from '<acceptance-cache>/m42-4cf13f7/tests/e2e/helpers.ts'
  3  | import { install, finish } from './observe.mjs'
  4  | test.beforeEach(async ({ page }, info) => { await install(page, info) })
  5  | test.afterEach(async ({ page }, info) => { await finish(page, info) })
  6  | // Diagnostic minimization after original-case controlled RED. This is a separate
  7  | // derived test, not a change to the original body or its timeout.
  8  | test('minimal actual saved lesson survives reload navigation before session delivery', async ({ page }) => {
  9  |   await bootstrap(page)
  10 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  11 |   await page.getByRole('button', { name: '浏览合成示例课程' }).click()
  12 |   await page.getByRole('button', { name: '打开示例小节' }).click()
  13 |   await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  14 |   await expect(page.locator('.reader-content h1')).toContainText('1.3')
  15 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  16 |   await page.reload()
  17 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
> 18 |   await expect(page.getByRole('button', { name: '继续浏览示例' })).toBeVisible({ timeout: 1000 })
     |                                                              ^ Error: expect(locator).toBeVisible() failed
  19 |   await page.getByRole('button', { name: '继续浏览示例' }).click()
  20 |   await expect(page.locator('.reader-content h1')).toContainText('1.3')
  21 | })
  22 | 
```