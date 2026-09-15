# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: observe-original.spec.ts >> route directory stays honestly empty and continue reading restores the exact last lesson
- Location: ../m42-continue-reading-diagnosis/observe-original.spec.ts:7:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '继续浏览示例' })

```

# Page snapshot

```yaml
- generic [ref=f3e3]:
  - link "跳到学习内容" [ref=f3e4] [cursor=pointer]:
    - /url: "#reader-main"
  - banner [ref=f3e5]:
    - link "知径 学习工作台" [ref=f3e6] [cursor=pointer]:
      - /url: "#"
      - generic [aria-hidden] [ref=f3e7]: 径
      - strong [ref=f3e8]: 知径
      - generic [ref=f3e9]: 学习工作台
    - button "搜索与命令 Ctrl ⇧ P" [ref=f3e10] [cursor=pointer]:
      - generic [aria-hidden] [ref=f3e11]: ⌕
      - text: 搜索与命令
      - generic [ref=f3e12]: Ctrl ⇧ P
    - generic [ref=f3e13]:
      - button "切换导航栏" [expanded] [ref=f3e14] [cursor=pointer]: 目录
      - button "切换 Agent 栏" [expanded] [ref=f3e15] [cursor=pointer]: Agent
      - button "专注" [ref=f3e16] [cursor=pointer]
      - button "导入" [ref=f3e17] [cursor=pointer]
  - status [ref=f3e18]:
    - generic [ref=f3e19]: 服务端会话已变化。基准、本地待同步与服务端会话如下；请选择保留的版本。
    - button "读取服务端会话，保留草稿" [ref=f3e20] [cursor=pointer]
  - region "会话三方比较" [ref=f3e21]:
    - group [ref=f3e22]:
      - generic "比较会话版本并明确选择" [ref=f3e23] [cursor=pointer]
      - paragraph [ref=f3e24]: 原基准是编辑开始时已确认的会话。本地一栏包含尚未确认的修改；采用任一版本都保留问题草稿。
      - table [ref=f3e26]:
        - rowgroup [ref=f3e27]:
          - row [ref=f3e28]:
            - columnheader "项目" [ref=f3e29]
            - columnheader "原基准（未知）" [ref=f3e30]
            - columnheader "本地待同步" [ref=f3e31]
            - columnheader "服务端（版本 4）" [ref=f3e32]
        - rowgroup [ref=f3e33]:
          - row [ref=f3e34]:
            - rowheader "课程" [ref=f3e35]
            - cell "未保存该基准，无法比较" [ref=f3e36]
            - cell "未选择课程" [ref=f3e37]
            - cell "合成示例课程" [ref=f3e38]
          - row [ref=f3e39]:
            - rowheader "当前入口" [ref=f3e40]
            - cell "未保存该基准，无法比较" [ref=f3e41]
            - cell "习题" [ref=f3e42]
            - cell "教材" [ref=f3e43]
          - row [ref=f3e44]:
            - rowheader "导航栏" [ref=f3e45]
            - cell "未保存该基准，无法比较" [ref=f3e46]
            - cell "展开，300 像素" [ref=f3e47]
            - cell "展开，300 像素" [ref=f3e48]
          - row [ref=f3e49]:
            - rowheader "Agent 栏" [ref=f3e50]
            - cell "未保存该基准，无法比较" [ref=f3e51]
            - cell "展开，368 像素" [ref=f3e52]
            - cell "展开，368 像素" [ref=f3e53]
          - row [ref=f3e54]:
            - rowheader "打开的内容" [ref=f3e55]
            - cell "未保存该基准，无法比较" [ref=f3e56]
            - cell "没有打开的内容" [ref=f3e57]
            - cell "1.3 从一个简单例子开始理解推导中的条件与边界 · 修订 1（当前）" [ref=f3e58]
          - row [ref=f3e59]:
            - rowheader "目录位置" [ref=f3e60]
            - cell "未保存该基准，无法比较" [ref=f3e61]
            - cell "距顶部 0 像素，展开 0 项" [ref=f3e62]
            - cell "距顶部 0 像素，展开 1 项" [ref=f3e63]
          - row [ref=f3e64]:
            - rowheader "阅读位置" [ref=f3e65]
            - cell "未保存该基准，无法比较" [ref=f3e66]
            - cell "没有当前内容" [ref=f3e67]
            - cell "距顶部 0 像素" [ref=f3e68]
      - generic [ref=f3e69]:
        - button "采用本地会话并重新保存" [ref=f3e70] [cursor=pointer]
        - button "采用服务端会话，放弃本地 UI 修改" [ref=f3e71] [cursor=pointer]
  - generic [ref=f3e72]:
    - complementary "课程导航" [ref=f3e73]:
      - generic [ref=f3e74]:
        - generic [ref=f3e75]:
          - generic [ref=f3e76]: 当前课程
          - button "尚未选择课程" [ref=f3e77] [cursor=pointer]:
            - text: 尚未选择课程
            - generic [aria-hidden] [ref=f3e78]: ⌄
          - paragraph [ref=f3e79]: 从自己的学习目标开始
          - generic [ref=f3e80]: 暂无已读取的阅读记录 · 未诊断
        - navigation "学习主导航" [ref=f3e81]:
          - button "学习路线" [ref=f3e82] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e83]: ↗
          - button "教材 含例题" [ref=f3e85] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e86]: ▤
            - generic [ref=f3e87]: 教材
            - generic [ref=f3e88]: 含例题
          - button "习题 含解答" [ref=f3e89] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e90]: ✎
            - generic [ref=f3e91]: 习题
            - generic [ref=f3e92]: 含解答
          - button "测试题" [ref=f3e93] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e94]: ☑
        - region "当前教材目录" [ref=f3e96]:
          - heading "上下文目录" [level=2] [ref=f3e98]
          - generic:
            - generic [ref=f3e99]:
              - paragraph [ref=f3e100]: 尚未选择教材。导入材料或选择已导入课程开始阅读。
              - button "导入资料" [ref=f3e101] [cursor=pointer]
              - button "加载合成示例课程" [ref=f3e102] [cursor=pointer]
            - paragraph [ref=f3e103]: 尚无已审核习题
        - generic [ref=f3e104]:
          - button "笔记" [ref=f3e105] [cursor=pointer]
          - button "创作" [ref=f3e106] [cursor=pointer]
          - button "设置" [ref=f3e107] [cursor=pointer]
    - separator "导航栏宽度" [ref=f3e108]
    - main [ref=f3e109]:
      - tablist "打开的学习对象" [ref=f3e110]:
        - tab "习题" [selected] [ref=f3e111] [cursor=pointer]
      - generic [ref=f3e113]:
        - generic [ref=f3e114]: 习题
        - heading "选择习题，开始一次练习" [level=1] [ref=f3e115]
        - paragraph [ref=f3e116]: 从左侧当前课程的习题目录选择参考题集。明确开始后才创建作答会话，参考解答保持隐藏。
        - button "选择课程" [ref=f3e117] [cursor=pointer]
    - separator "Agent 栏宽度" [ref=f3e118]
    - complementary "Agent 助教" [ref=f3e119]:
      - generic [ref=f3e120]:
        - generic [ref=f3e121]:
          - heading "Agent" [level=2] [ref=f3e122]
          - generic [ref=f3e123]: 未配置模型
        - group [ref=f3e124]:
          - generic "当前上下文" [ref=f3e125] [cursor=pointer]
          - paragraph [ref=f3e126]: 尚未选择学习对象
        - generic [ref=f3e127]:
          - generic [aria-hidden] [ref=f3e128]: ✦
          - heading "围绕当前内容，一起思考" [level=3] [ref=f3e129]
          - paragraph [ref=f3e130]: 模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。
          - paragraph [ref=f3e131]: 现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。
        - generic [ref=f3e132]:
          - generic "教学意图" [ref=f3e133]:
            - button "讲解" [pressed] [ref=f3e134] [cursor=pointer]
            - button "提示" [ref=f3e135] [cursor=pointer]
            - button "推导" [ref=f3e136] [cursor=pointer]
            - button "拓展" [ref=f3e137] [cursor=pointer]
          - generic [ref=f3e138]: 问题草稿
          - textbox "问题草稿" [ref=f3e139]:
            - /placeholder: 写下问题，草稿按当前对象保留…
          - generic [ref=f3e140]:
            - generic [ref=f3e141]: 联网：未授权
            - button "发送 ↑" [disabled] [ref=f3e142]
          - generic [ref=f3e143]: 草稿保留在本机浏览器，尚未发送。
  - status [ref=f3e144]:
    - generic [ref=f3e145]: 会话版本冲突
    - generic [ref=f3e146]: 尚未选择对象
    - generic [ref=f3e147]: 正常学习 · 本机
```

# Test source

```ts
  1  | import { test, expect } from '<acceptance-cache>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { bootstrap } from '<acceptance-cache>/m42-4cf13f7/tests/e2e/helpers.ts'
  3  | import { install, finish } from './observe.mjs'
  4  | test.beforeEach(async ({ page }, info) => { await install(page, info) })
  5  | test.afterEach(async ({ page }, info) => { await finish(page, info) })
  6  | 
  7  | test('route directory stays honestly empty and continue reading restores the exact last lesson', async ({ page }) => {
  8  |   await bootstrap(page)
  9  |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  10 |   await page.getByRole('button', { name: '浏览合成示例课程' }).click()
  11 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '学习路线', exact: true }).click()
  12 |   await expect(page.getByRole('region', { name: '学习路线目录', exact: true }).getByText('尚无正式学习路线。', { exact: true })).toBeVisible()
  13 |   await expect(page.getByRole('navigation', { name: '上下文目录' })).toHaveCount(0)
  14 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  15 |   await page.getByRole('button', { name: '打开示例小节' }).click()
  16 |   await page.getByRole('navigation', { name: '上下文目录' }).getByRole('link', { name: '1.3' }).click()
  17 |   await expect(page.locator('.reader-content h1')).toContainText('1.3')
  18 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  19 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
  20 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  21 |   await page.getByRole('button', { name: '继续浏览示例' }).click()
  22 |   await expect(page.locator('.reader-content h1')).toContainText('1.3')
  23 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible(); await page.reload()
  24 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '习题' }).click()
> 25 |   await page.getByRole('button', { name: '继续浏览示例' }).click()
     |                                                      ^ Error: locator.click: Test timeout of 30000ms exceeded.
  26 |   await expect(page.locator('.reader-content h1')).toContainText('1.3')
  27 | })
  28 | 
```