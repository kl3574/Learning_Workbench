# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: observe-original.spec.ts >> route directory stays honestly empty and continue reading restores the exact last lesson
- Location: ../m42-continue-reading-diagnosis/observe-original.spec.ts:7:1

# Error details

```
Test timeout of 30000ms exceeded while running "afterEach" hook.
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
  - generic [ref=f3e18]:
    - complementary "课程导航" [ref=f3e19]:
      - generic [ref=f3e20]:
        - generic [ref=f3e21]:
          - generic [ref=f3e22]: 当前课程
          - button "理解模型、条件与计算：合成阅读工作台示例课程" [ref=f3e23] [cursor=pointer]:
            - text: 理解模型、条件与计算：合成阅读工作台示例课程
            - generic [aria-hidden] [ref=f3e24]: ⌄
          - paragraph [ref=f3e25]: 合成示例 · 8 章 / 48 节
          - generic [ref=f3e26]: 正式阅读记录 0 / 48 · 未诊断
          - button "继续浏览示例" [active] [ref=f3e27] [cursor=pointer]:
            - text: 继续浏览示例
            - generic [aria-hidden] [ref=f3e28]: →
        - navigation "学习主导航" [ref=f3e29]:
          - button "学习路线" [ref=f3e30] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e31]: ↗
          - button "教材 含例题" [ref=f3e33] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e34]: ▤
            - generic [ref=f3e35]: 教材
            - generic [ref=f3e36]: 含例题
          - button "习题 含解答" [ref=f3e37] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e38]: ✎
            - generic [ref=f3e39]: 习题
            - generic [ref=f3e40]: 含解答
          - button "测试题" [ref=f3e41] [cursor=pointer]:
            - generic [aria-hidden] [ref=f3e42]: ☑
        - region "当前教材目录" [ref=f3e44]:
          - generic [ref=f3e45]:
            - heading "当前教材目录" [level=2] [ref=f3e46]
            - button "完整标题" [ref=f3e47] [cursor=pointer]
          - generic [ref=f3e48]:
            - generic [ref=f3e49]: 搜索当前目录
            - textbox "搜索当前目录" [ref=f3e50]:
              - /placeholder: 搜索章节、小节
          - navigation "上下文目录" [ref=f3e52]:
            - list [ref=f3e53]:
              - listitem [ref=f3e54]:
                - generic [ref=f3e55]:
                  - button "折叠第 1 章 观察、变量与一个小模型" [expanded] [ref=f3e56] [cursor=pointer]: ⌄
                  - link "第 1 章 观察、变量与一个小模型" [ref=f3e57] [cursor=pointer]:
                    - /url: "#synthetic_chapter_1"
                - list [ref=f3e58]:
                  - listitem [ref=f3e59]:
                    - link "已读（合成展示） 1.1 本章目标与思路" [ref=f3e60] [cursor=pointer]:
                      - /url: "#synthetic_lesson_1_1"
                      - generic "已读（合成展示）" [ref=f3e61]: ✓
                      - generic [ref=f3e62]: 1.1 本章目标与思路
                  - listitem [ref=f3e63]:
                    - link "未读 1.2 变量、定义域与记号" [ref=f3e64] [cursor=pointer]:
                      - /url: "#synthetic_lesson_1_2"
                      - generic "未读" [ref=f3e65]: ○
                      - generic [ref=f3e66]: 1.2 变量、定义域与记号
                  - listitem [ref=f3e67]:
                    - link "未读 1.3 从一个简单例子开始理解推导中的条件与边界" [ref=f3e68] [cursor=pointer]:
                      - /url: "#synthetic_lesson_1_3"
                      - generic "未读" [ref=f3e69]: ○
                      - generic [ref=f3e70]: 1.3 从一个简单例子开始理解推导中的条件与边界
                  - listitem [ref=f3e71]:
                    - link "未读 1.4 逐步展开计算" [ref=f3e72] [cursor=pointer]:
                      - /url: "#synthetic_lesson_1_4"
                      - generic "未读" [ref=f3e73]: ○
                      - generic [ref=f3e74]: 1.4 逐步展开计算
                  - listitem [ref=f3e75]:
                    - link "过期引用（合成展示） 1.5 一个需要仔细核对适用条件的长中文标题示例：当观测数量变化时如何理解结论" [ref=f3e76] [cursor=pointer]:
                      - /url: "#synthetic_lesson_1_5"
                      - generic "过期引用（合成展示）" [ref=f3e77]: ↻
                      - generic [ref=f3e78]: 1.5 一个需要仔细核对适用条件的长中文标题示例：当观测数量变化时如何理解结论
                  - listitem [ref=f3e79]:
                    - link "未读 1.6 边界、小结与下一步" [ref=f3e80] [cursor=pointer]:
                      - /url: "#synthetic_lesson_1_6"
                      - generic "未读" [ref=f3e81]: ○
                      - generic [ref=f3e82]: 1.6 边界、小结与下一步
              - listitem [ref=f3e83]:
                - generic [ref=f3e84]:
                  - button "展开第 2 章 从误差到平方和" [ref=f3e85] [cursor=pointer]: ›
                  - link "第 2 章 从误差到平方和" [ref=f3e86] [cursor=pointer]:
                    - /url: "#synthetic_chapter_2"
              - listitem [ref=f3e87]:
                - generic [ref=f3e88]:
                  - button "展开第 3 章 条件与唯一性的边界" [ref=f3e89] [cursor=pointer]: ›
                  - link "第 3 章 条件与唯一性的边界" [ref=f3e90] [cursor=pointer]:
                    - /url: "#synthetic_chapter_3"
              - listitem [ref=f3e91]:
                - generic [ref=f3e92]:
                  - button "展开第 4 章 向量与几何直觉" [ref=f3e93] [cursor=pointer]: ›
                  - link "第 4 章 向量与几何直觉" [ref=f3e94] [cursor=pointer]:
                    - /url: "#synthetic_chapter_4"
              - listitem [ref=f3e95]:
                - generic [ref=f3e96]:
                  - button "展开第 5 章 矩阵表达与维度检查" [ref=f3e97] [cursor=pointer]: ›
                  - link "第 5 章 矩阵表达与维度检查" [ref=f3e98] [cursor=pointer]:
                    - /url: "#synthetic_chapter_5"
              - listitem [ref=f3e99]:
                - generic [ref=f3e100]:
                  - button "展开第 6 章 计算过程与结果复核" [ref=f3e101] [cursor=pointer]: ›
                  - link "第 6 章 计算过程与结果复核" [ref=f3e102] [cursor=pointer]:
                    - /url: "#synthetic_chapter_6"
              - listitem [ref=f3e103]:
                - generic [ref=f3e104]:
                  - button "展开第 7 章 假设变化后的修订比较" [ref=f3e105] [cursor=pointer]: ›
                  - link "第 7 章 假设变化后的修订比较" [ref=f3e106] [cursor=pointer]:
                    - /url: "#synthetic_chapter_7"
              - listitem [ref=f3e107]:
                - generic [ref=f3e108]:
                  - button "展开第 8 章 回顾与后续学习方向" [ref=f3e109] [cursor=pointer]: ›
                  - link "第 8 章 回顾与后续学习方向" [ref=f3e110] [cursor=pointer]:
                    - /url: "#synthetic_chapter_8"
        - generic [ref=f3e111]:
          - button "笔记" [ref=f3e112] [cursor=pointer]
          - button "创作" [ref=f3e113] [cursor=pointer]
          - button "设置" [ref=f3e114] [cursor=pointer]
    - separator "导航栏宽度" [ref=f3e115]
    - main [ref=f3e116]:
      - tablist "打开的学习对象" [ref=f3e117]:
        - tab "教材" [ref=f3e118] [cursor=pointer]
        - generic [ref=f3e119]:
          - tab "1.3 从一个简单例子开始理解推导中的条件与边界" [selected] [ref=f3e120] [cursor=pointer]
          - button "固定标签 1.3 从一个简单例子开始理解推导中的条件与边界" [ref=f3e121] [cursor=pointer]: ⋄
          - button "关闭标签 1.3 从一个简单例子开始理解推导中的条件与边界" [ref=f3e122] [cursor=pointer]: ×
      - article [ref=f3e124]:
        - generic [ref=f3e125]:
          - text: 合成示例课程
          - generic [ref=f3e126]: ›
          - text: 第 1 章
          - generic [ref=f3e127]: ›
          - text: "1.3"
        - generic [ref=f3e128]: 合成示例 · 仅用于界面验收，不是正式教材或学习证据
        - heading "1.3 从一个简单例子开始理解推导中的条件与边界" [level=1] [ref=f3e129]
        - generic [ref=f3e130]:
          - text: 修订 1
          - generic [ref=f3e131]: ·
          - text: 未诊断
          - generic [ref=f3e132]: ·
          - text: 未读
        - paragraph [ref=f3e133]:
          - text: 这是一段
          - strong [ref=f3e134]: 合成排版材料
          - text: ，用于检查阅读工作台。它不是已审核教材，也不代表任何人的真实学习记录。
        - heading "目标与逻辑链" [level=2] [ref=f3e135]
        - paragraph [ref=f3e136]:
          - text: 明确变量 → 写出条件 → 展开计算 → 检查边界。这里令
          - 'generic "公式：x\\in\\mathbb{R}" [ref=f3e137]'
          - text: ，通过一个小例子检查数学显示与阅读节奏。
        - heading "定义与条件" [level=2] [ref=f3e153]
        - paragraph [ref=f3e154]:
          - text: 对给定实数
          - generic "公式：a" [ref=f3e155]
          - text: ，考虑函数
          - generic "公式：f(x)=(x-a)^2" [ref=f3e163]
          - text: 。因为平方非负，当且仅当
          - generic "公式：x=a" [ref=f3e198]
          - text: 时取零。
        - generic "公式：f(x)=(x-a)^2=x^2-2ax+a^2\\geq 0" [ref=f3e214]:
          - group [ref=f3e269]:
            - generic "LaTeX 源文" [ref=f3e270]
        - heading "例题 · 逐步检查" [level=3] [ref=f3e271]
        - paragraph [ref=f3e272]:
          - text: 取
          - generic "公式：a=2" [ref=f3e273]
          - text: 。代入
          - generic "公式：x=3" [ref=f3e288]
          - text: 得
          - generic "公式：(3-2)^2=1" [ref=f3e303]
          - text: ；代入
          - generic "公式：x=2" [ref=f3e332]
          - text: 得零。这一段是教材内的完整算例展示，并未建立练习或测试。
        - heading "长公式排版检查" [level=2] [ref=f3e347]
        - paragraph [ref=f3e348]: 下式故意较长；超出阅读宽度的部分应在公式内部滚动。
        - 'generic "公式：\\underbrace{(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2+(x-a)^2}_{\\text{eight identical terms}}=8x^2-16ax+8a^2\\geq 0" [ref=f3e350]':
          - group [ref=f3e540]:
            - generic "LaTeX 源文" [ref=f3e541]
        - heading "边界与小结" [level=2] [ref=f3e542]
        - paragraph [ref=f3e543]: 本例只讨论实数平方；换用其他定义域时应重新检查条件。页面支持选文预览，并保留原始 LaTeX。
        - table [ref=f3e544]:
          - rowgroup [ref=f3e545]:
            - row [ref=f3e546]:
              - columnheader "检查对象" [ref=f3e547]
              - columnheader "状态说明" [ref=f3e548]
          - rowgroup [ref=f3e549]:
            - row [ref=f3e550]:
              - cell "数学显示" [ref=f3e551]
              - cell "本地 MathJax SVG" [ref=f3e552]
            - row [ref=f3e553]:
              - cell "样例身份" [ref=f3e554]
              - cell "合成 UI 数据" [ref=f3e555]
            - row [ref=f3e556]:
              - cell "学习证据" [ref=f3e557]
              - cell "未创建" [ref=f3e558]
        - paragraph [ref=f3e559]: \n第 1 章，第 3 节。
        - generic [ref=f3e560]:
          - button "← 上一节" [ref=f3e561] [cursor=pointer]
          - button "下一节 →" [ref=f3e562] [cursor=pointer]
    - separator "Agent 栏宽度" [ref=f3e563]
    - complementary "Agent 助教" [ref=f3e564]:
      - generic [ref=f3e565]:
        - generic [ref=f3e566]:
          - heading "Agent" [level=2] [ref=f3e567]
          - generic [ref=f3e568]: 未配置模型
        - group [ref=f3e569]:
          - generic "当前上下文" [ref=f3e570] [cursor=pointer]
          - paragraph [ref=f3e571]: 1.3 从一个简单例子开始理解推导中的条件与边界
          - generic [ref=f3e572]: 修订 1 · 合成示例引用
          - group [ref=f3e573]:
            - generic "查看引用范围" [ref=f3e574] [cursor=pointer]
        - generic [ref=f3e575]:
          - generic [aria-hidden] [ref=f3e576]: ✦
          - heading "围绕当前内容，一起思考" [level=3] [ref=f3e577]
          - paragraph [ref=f3e578]: 模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。
          - paragraph [ref=f3e579]: 现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。
        - generic [ref=f3e580]:
          - generic "教学意图" [ref=f3e581]:
            - button "讲解" [pressed] [ref=f3e582] [cursor=pointer]
            - button "提示" [ref=f3e583] [cursor=pointer]
            - button "推导" [ref=f3e584] [cursor=pointer]
            - button "拓展" [ref=f3e585] [cursor=pointer]
          - generic [ref=f3e586]: 问题草稿
          - textbox "问题草稿" [ref=f3e587]:
            - /placeholder: 写下问题，草稿按当前对象保留…
          - generic [ref=f3e588]:
            - generic [ref=f3e589]: 联网：未授权
            - button "发送 ↑" [disabled] [ref=f3e590]
          - generic [ref=f3e591]: 草稿保留在本机浏览器，尚未发送。
  - status [ref=f3e592]:
    - generic [ref=f3e593]: ✓ UI 会话已保存
    - generic [ref=f3e594]: 内容修订 1
    - generic [ref=f3e595]: 合成示例 · 无学习证据 · 本机
```

# Test source

```ts
  1  | import { test, expect } from '<acceptance-cache>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { bootstrap } from '<acceptance-cache>/m42-4cf13f7/tests/e2e/helpers.ts'
  3  | import { install, finish } from './observe.mjs'
  4  | test.beforeEach(async ({ page }, info) => { await install(page, info) })
> 5  | test.afterEach(async ({ page }, info) => { await finish(page, info) })
     |      ^ Test timeout of 30000ms exceeded while running "afterEach" hook.
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
  25 |   await page.getByRole('button', { name: '继续浏览示例' }).click()
  26 |   await expect(page.locator('.reader-content h1')).toContainText('1.3')
  27 | })
  28 | 
```