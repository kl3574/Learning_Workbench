# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: block-version-compare.spec.ts >> actual historical block r1/r2 comparison is read-only and remains contained at desktop and narrow widths
- Location: ../../tests/e2e/block-version-compare.spec.ts:5:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('#block-block_nativecompare_definition-r2').getByRole('region', { name: '块修订比较', exact: true }).getByLabel('左侧修订', { exact: true })

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
          - button "原创阅读验收教材 nativecompare" [ref=f3e23] [cursor=pointer]:
            - text: 原创阅读验收教材 nativecompare
            - generic [aria-hidden] [ref=f3e24]: ⌄
          - paragraph [ref=f3e25]: 2 章 / 2 节 · 尚未审校
          - generic [ref=f3e26]: 已阅读 0 / 2 · 未诊断
          - button "查看教材修订" [ref=f3e27] [cursor=pointer]
          - button "继续阅读 →" [ref=f3e28] [cursor=pointer]
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
              - /placeholder: 搜索章节、小节、内容块标题
          - navigation "上下文目录" [ref=f3e52]:
            - list [ref=f3e53]:
              - listitem [ref=f3e54]:
                - generic [ref=f3e55]:
                  - button "折叠第一章：模型、推导与算例" [expanded] [ref=f3e56] [cursor=pointer]: ⌄
                  - link "第一章：模型、推导与算例" [ref=f3e57] [cursor=pointer]:
                    - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_nativecompare%22%2C%22revision%22%3A2%2C%22sha256%22%3A%220ba206d93646845878df5b41b5c690042b9b60700309c86ade933083064fdde8%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_nativecompare_reasoning%22%2C%22revision%22%3A2%2C%22sha256%22%3A%22b398192823c12f8cad71b692278b8b0a2af64d6cfc799d93b72e7c2aa7f39f45%22%7D%7D
                - list [ref=f3e58]:
                  - listitem [ref=f3e59]:
                    - generic [ref=f3e60]:
                      - button "展开内容块：从定义到证明与例题的完整推导" [expanded] [ref=f3e61] [cursor=pointer]: ›
                      - generic "未读" [ref=f3e62]: ○
                      - link "从定义到证明与例题的完整推导" [ref=f3e63] [cursor=pointer]:
                        - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_nativecompare%22%2C%22revision%22%3A2%2C%22sha256%22%3A%220ba206d93646845878df5b41b5c690042b9b60700309c86ade933083064fdde8%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_nativecompare_reasoning%22%2C%22revision%22%3A2%2C%22sha256%22%3A%22b398192823c12f8cad71b692278b8b0a2af64d6cfc799d93b72e7c2aa7f39f45%22%7D%7D
                    - list [ref=f3e64]:
                      - listitem [ref=f3e65]:
                        - link "定义：残差与损失" [ref=f3e66] [cursor=pointer]:
                          - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_nativecompare%22%2C%22revision%22%3A2%2C%22sha256%22%3A%220ba206d93646845878df5b41b5c690042b9b60700309c86ade933083064fdde8%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_nativecompare_reasoning%22%2C%22revision%22%3A2%2C%22sha256%22%3A%22b398192823c12f8cad71b692278b8b0a2af64d6cfc799d93b72e7c2aa7f39f45%22%7D%2C%22block%22%3A%7B%22entity%22%3A%22block%22%2C%22id%22%3A%22block_nativecompare_definition%22%2C%22revision%22%3A2%2C%22sha256%22%3A%228d393495978a249b68d0f4ccc944666e4b4bf31664df9a429c07b253ca4d4a8d%22%7D%2C%22view%22%3A%22lesson%22%7D#block-block_nativecompare_definition-r2
                      - listitem [ref=f3e67]:
                        - link "证明：唯一最小点" [ref=f3e68] [cursor=pointer]:
                          - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_nativecompare%22%2C%22revision%22%3A2%2C%22sha256%22%3A%220ba206d93646845878df5b41b5c690042b9b60700309c86ade933083064fdde8%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_nativecompare_reasoning%22%2C%22revision%22%3A2%2C%22sha256%22%3A%22b398192823c12f8cad71b692278b8b0a2af64d6cfc799d93b72e7c2aa7f39f45%22%7D%2C%22block%22%3A%7B%22entity%22%3A%22block%22%2C%22id%22%3A%22block_nativecompare_proof%22%2C%22revision%22%3A2%2C%22sha256%22%3A%22399acd0f20d2a71db316431fabaad5c7af8e3b5664d504d4dd6d835dd5d51a35%22%7D%2C%22view%22%3A%22lesson%22%7D#block-block_nativecompare_proof-r2
                      - listitem [ref=f3e69]:
                        - link "例题 · 例题：逐项计算与边界" [ref=f3e70] [cursor=pointer]:
                          - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_nativecompare%22%2C%22revision%22%3A2%2C%22sha256%22%3A%220ba206d93646845878df5b41b5c690042b9b60700309c86ade933083064fdde8%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_nativecompare_reasoning%22%2C%22revision%22%3A2%2C%22sha256%22%3A%22b398192823c12f8cad71b692278b8b0a2af64d6cfc799d93b72e7c2aa7f39f45%22%7D%2C%22block%22%3A%7B%22entity%22%3A%22block%22%2C%22id%22%3A%22block_nativecompare_example%22%2C%22revision%22%3A2%2C%22sha256%22%3A%2266caa6088e65fd5ad2b52c804b09194c57ad078e8cd8b311509a66ffd57d0728%22%7D%2C%22view%22%3A%22worked_example%22%7D#block-block_nativecompare_example-r2
              - listitem [ref=f3e71]:
                - generic [ref=f3e72]:
                  - button "展开第二章：小结与回读" [ref=f3e73] [cursor=pointer]: ›
                  - link "第二章：小结与回读" [ref=f3e74] [cursor=pointer]:
                    - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_nativecompare%22%2C%22revision%22%3A2%2C%22sha256%22%3A%220ba206d93646845878df5b41b5c690042b9b60700309c86ade933083064fdde8%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_nativecompare_review%22%2C%22revision%22%3A2%2C%22sha256%22%3A%229353d076f6c080380c2baa429601dc9a005e056b886e2196cd3371e69fdec71a%22%7D%7D
        - generic [ref=f3e75]:
          - button "笔记" [ref=f3e76] [cursor=pointer]
          - button "创作" [ref=f3e77] [cursor=pointer]
          - button "设置" [ref=f3e78] [cursor=pointer]
    - separator "导航栏宽度" [ref=f3e79]
    - main [ref=f3e80]:
      - tablist "打开的学习对象" [ref=f3e81]:
        - tab "教材" [ref=f3e82] [cursor=pointer]
        - generic [ref=f3e83]:
          - tab "已固定定义：残差与损失 · r2" [selected] [ref=f3e84] [cursor=pointer]: ⌖ 定义：残差与损失 · r2
          - button "固定标签 定义：残差与损失 · r2" [ref=f3e85] [cursor=pointer]: ⌖
          - button "关闭标签 定义：残差与损失 · r2" [ref=f3e86] [cursor=pointer]: ×
      - article [ref=f3e88]:
        - generic [ref=f3e89]: 原创阅读验收教材 nativecompare › 第一章：模型、推导与算例 › 从定义到证明与例题的完整推导
        - heading "从定义到证明与例题的完整推导" [level=1] [ref=f3e90]
        - generic [ref=f3e91]: 教材修订 2 · 小节修订 2 · 尚未审校 · 未诊断
        - generic [ref=f3e92]:
          - button "明确标记本节已读" [ref=f3e93] [cursor=pointer]
          - button "为此对象添加书签" [ref=f3e94] [cursor=pointer]
          - button "为当前选文记笔记" [disabled] [ref=f3e95]
          - button "查看笔记" [ref=f3e96] [cursor=pointer]
          - button "本节习题" [ref=f3e97] [cursor=pointer]
        - generic [ref=f3e98]:
          - heading "定义：残差与损失" [level=2] [ref=f3e99]
          - generic [ref=f3e100]:
            - heading "残差与损失的定义" [level=1] [ref=f3e101]
            - paragraph [ref=f3e102]:
              - text: 设参数
              - 'generic "公式：\\theta\\in\\mathbb{R}" [ref=f3e103]'
              - text: ，给定观测向量
              - generic "公式：h=(1,2)" [ref=f3e119]
              - text: 与
              - generic "公式：y=(2,4)" [ref=f3e142]
              - text: 。 残差为
              - generic "公式：r_i=y_i-h_i\\theta" [ref=f3e165]
              - text: ，平方损失为
              - 'generic "公式：L(\\theta)=\\sum_{i=1}^2r_i^2" [ref=f3e198]'
              - text: 。
            - paragraph [ref=f3e236]:
              - text: 第二修订选文 🧠 中文 café é：
              - strong [ref=f3e237]: 强调内容
              - text: 与
              - code [ref=f3e238]: 被动代码
              - text: 。
            - paragraph [ref=f3e239]: 重复句子用于选择定位。
            - paragraph [ref=f3e240]: 中间段落保持原始换行和标点。
            - paragraph [ref=f3e241]: 重复句子用于选择定位。
          - group [ref=f3e242]:
            - generic "原始 Markdown 与精确选文" [ref=f3e243] [cursor=pointer]
          - group [ref=f3e244]:
            - generic "来源与提取诊断" [ref=f3e245] [cursor=pointer]
          - region "块修订比较" [ref=f3e246]:
            - button "收起修订比较" [expanded] [active] [ref=f3e247] [cursor=pointer]
            - generic [ref=f3e248]:
              - heading "比较同一块的两个精确修订" [level=3] [ref=f3e249]
              - paragraph [ref=f3e250]: 明确选择两侧修订。仅比较原文与字段；文字差异不证明数学或语义等价，不批准、发布或恢复内容。
              - paragraph [ref=f3e251]: 收起保留本页选择，正文重新读取；切到其他块或刷新页面需重新选择。
              - generic [ref=f3e252]:
                - generic [ref=f3e253]:
                  - text: 左侧修订
                  - combobox "左侧修订" [ref=f3e254]:
                    - option "请选择准确修订" [selected]
                    - option "修订 2 · 8d393495978a"
                    - option "修订 1 · 16d7b8300eb3"
                - generic [ref=f3e255]:
                  - text: 右侧修订
                  - combobox "右侧修订" [ref=f3e256]:
                    - option "请选择准确修订" [selected]
                    - option "修订 2 · 8d393495978a"
                    - option "修订 1 · 16d7b8300eb3"
              - generic [ref=f3e257]:
                - button "重新读取历史列表" [ref=f3e258] [cursor=pointer]
                - button "读取所选两个修订" [disabled] [ref=f3e259]
        - generic [ref=f3e260]:
          - heading "证明：唯一最小点" [level=2] [ref=f3e261]
          - generic [ref=f3e262]:
            - heading "唯一性的完整证明" [level=1] [ref=f3e263]
            - paragraph [ref=f3e264]: 对任意实参数，逐项展开并配方：
            - paragraph [ref=f3e265]:
              - generic "公式：L(\\theta)=(2-\\theta)^2+(4-2\\theta)^2=20-20\\theta+5\\theta^2=5(\\theta-2)^2." [ref=f3e266]
            - paragraph [ref=f3e379]:
              - text: 实数平方非负，且平方为零当且仅当其底数为零。因此损失最小值为零，只在
              - generic "公式：\\theta=2" [ref=f3e380]
              - text: 达到。 这里证明的是此给定平方目标的唯一最小点，不是任意噪声模型中的统计最优性。
          - group [ref=f3e395]:
            - generic "原始 Markdown 与精确选文" [ref=f3e396] [cursor=pointer]
          - group [ref=f3e397]:
            - generic "来源与提取诊断" [ref=f3e398] [cursor=pointer]
          - region "块修订比较" [ref=f3e399]:
            - button "比较此块的两个修订" [ref=f3e400] [cursor=pointer]
        - generic [ref=f3e401]:
          - heading "例题 · 例题：逐项计算与边界" [level=2] [ref=f3e402]
          - generic [ref=f3e403]:
            - heading "已知观测的逐项计算" [level=1] [ref=f3e404]
            - paragraph [ref=f3e405]:
              - text: 条件为
              - generic "公式：h=(1,2)" [ref=f3e406]
              - text: 、
              - generic "公式：y=(2,4)" [ref=f3e429]
              - text: ，未知参数为实数。
            - table [ref=f3e452]:
              - rowgroup [ref=f3e453]:
                - row [ref=f3e454]:
                  - columnheader "量" [ref=f3e455]
                  - columnheader "展开" [ref=f3e456]
                  - columnheader "结果" [ref=f3e457]
              - rowgroup [ref=f3e458]:
                - row [ref=f3e459]:
                  - cell "公式：A" [ref=f3e460]
                  - cell "公式：1^2+2^2" [ref=f3e469]
                  - cell "公式：5" [ref=f3e491]
                - row [ref=f3e500]:
                  - cell "公式：B" [ref=f3e501]
                  - cell "公式：1\\cdot2+2\\cdot4" [ref=f3e510]
                  - cell "公式：10" [ref=f3e540]
                - row [ref=f3e550]:
                  - cell "公式：\\hat\\theta" [ref=f3e551]
                  - cell "公式：B/A" [ref=f3e564]
                  - cell "公式：2" [ref=f3e577]
            - paragraph [ref=f3e586]:
              - text: 代回得预测
              - generic "公式：(2,4)" [ref=f3e587]
              - text: 、残差
              - generic "公式：(0,0)" [ref=f3e603]
              - text: 、损失零，与前述配方证明一致。 若两个
              - generic "公式：h_i" [ref=f3e619]
              - text: 都为零，损失不再依赖参数，不能宣称唯一估计。
            - paragraph [ref=f3e630]: 下面仅展示长度较大的向量，以验证公式局部滚动：
            - paragraph [ref=f3e631]:
              - generic "公式：v=(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40)." [ref=f3e632]
            - code [ref=f3e841]: "# 合成示例代码仅作文本，不在 Reader 执行。 print(\"READER_CODE_MUST_STAY_PASSIVE\")"
          - group [ref=f3e842]:
            - generic "原始 Markdown 与精确选文" [ref=f3e843] [cursor=pointer]
          - group [ref=f3e844]:
            - generic "来源与提取诊断" [ref=f3e845] [cursor=pointer]
          - region "块修订比较" [ref=f3e846]:
            - button "比较此块的两个修订" [ref=f3e847] [cursor=pointer]
        - generic [ref=f3e848]:
          - button "← 上一节" [disabled] [ref=f3e849]
          - button "下一节 →" [ref=f3e850] [cursor=pointer]
    - separator "Agent 栏宽度" [ref=f3e851]
    - complementary "Agent 助教" [ref=f3e852]:
      - generic [ref=f3e853]:
        - generic [ref=f3e854]:
          - heading "Agent" [level=2] [ref=f3e855]
          - generic [ref=f3e856]: 本地任务 · 明确授权
        - group [ref=f3e857]:
          - generic "当前上下文" [ref=f3e858] [cursor=pointer]
          - paragraph [ref=f3e859]: 定义：残差与损失
          - generic [ref=f3e860]: 修订 2 · 已解析的准确引用
          - group [ref=f3e861]:
            - generic "查看引用范围" [ref=f3e862] [cursor=pointer]
        - group [ref=f3e863]:
          - generic "明确选择本次附加范围（默认无）" [ref=f3e864]
        - region "真实问答线程与任务" [ref=f3e865]:
          - paragraph [ref=f3e866]: 发送先建立本地任务并准备上下文，不自动外发；随后核对并明确批准本次授权。
          - button "重新读取线程与当前绑定" [ref=f3e867] [cursor=pointer]
          - generic [ref=f3e868]:
            - text: 新线程标题
            - textbox "新线程标题" [ref=f3e869]: 围绕当前内容的问答
          - button "明确创建本地线程" [ref=f3e870] [cursor=pointer]
          - generic "当前对象的真实线程" [ref=f3e871]:
            - paragraph [ref=f3e872]: 当前已读取页没有此精确对象的线程；可创建或继续读取服务器列表。
          - region "问答原文与证据边界" [ref=f3e873]
        - generic [ref=f3e874]:
          - generic "教学意图" [ref=f3e875]:
            - button "讲解" [pressed] [ref=f3e876] [cursor=pointer]
            - button "提示" [ref=f3e877] [cursor=pointer]
            - button "推导" [ref=f3e878] [cursor=pointer]
            - button "拓展" [ref=f3e879] [cursor=pointer]
          - generic [ref=f3e880]: 问题草稿
          - textbox "问题草稿" [ref=f3e881]:
            - /placeholder: 写下问题，草稿按当前对象保留…
          - generic [ref=f3e882]:
            - generic [ref=f3e883]: 联网：未授权
            - button "创建本次问答任务 ↑" [disabled] [ref=f3e884]
          - generic [ref=f3e885]: 本机草稿保留；发送与结果以本次任务记录为准。
  - status [ref=f3e886]:
    - generic [ref=f3e887]: ✓ UI 会话已保存
    - generic [ref=f3e888]: 内容修订 2
    - generic [ref=f3e889]: 正常学习 · 本机
```

# Test source

```ts
  1  | import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { bootstrap } from './helpers'
  3  | import { importReaderPackage, originalReaderPackage } from './readerTestData'
  4  | 
  5  | test('actual historical block r1/r2 comparison is read-only and remains contained at desktop and narrow widths', async ({ page }, info) => {
  6  |   const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  7  |   await bootstrap(page)
  8  |   const current = originalReaderPackage('nativecompare', 2, true), old = originalReaderPackage('nativecompare', 1)
  9  |   const imported = await importReaderPackage(page, current)
  10 |   await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  11 |   await page.goto(`/?reader=${encodeURIComponent(JSON.stringify({ course: current.course, lesson: current.lessons[0], block: current.blocks[0], view: 'lesson' }))}`)
  12 |   const block = page.locator(`#block-${current.blocks[0].id}-r2`)
  13 |   await expect(block.locator('.reader-markdown')).toContainText('第二修订选文')
  14 |   const requests: { method: string; path: string }[] = []
  15 |   page.on('request', request => { const path = new URL(request.url()).pathname; if (path.startsWith('/api/v1/')) requests.push({ method: request.method(), path }) })
  16 |   const before = await page.request.get('/api/v1/learning/progress').then(response => response.json())
  17 |   const panel = block.getByRole('region', { name: '块修订比较', exact: true })
  18 |   await panel.getByRole('button', { name: '比较此块的两个修订', exact: true }).click()
  19 |   await expect(panel.getByRole('option', { name: /修订 1/ }).first()).toBeAttached()
  20 |   await expect(panel.getByRole('button', { name: '读取所选两个修订', exact: true })).toBeDisabled()
> 21 |   await panel.getByLabel('左侧修订', { exact: true }).selectOption(old.blocks[0].sha256)
     |                                                   ^ Error: locator.selectOption: Test timeout of 30000ms exceeded.
  22 |   await panel.getByLabel('右侧修订', { exact: true }).selectOption(current.blocks[0].sha256)
  23 |   await panel.getByRole('button', { name: '读取所选两个修订', exact: true }).click()
  24 |   const left = panel.getByLabel('左侧完整原文', { exact: true }), right = panel.getByLabel('右侧完整原文', { exact: true })
  25 |   await expect(left).toHaveText(old.bodies[old.blocks[0].id], { useInnerText: false })
  26 |   await expect(right).toHaveText(current.bodies[current.blocks[0].id], { useInnerText: false })
  27 |   expect(await left.textContent()).toBe(old.bodies[old.blocks[0].id])
  28 |   expect(await right.textContent()).toBe(current.bodies[current.blocks[0].id])
  29 |   await expect(panel.getByLabel('逐行文字差异')).toContainText('选文甲')
  30 |   await expect(panel.getByLabel('逐行文字差异')).toContainText('第二修订选文')
  31 |   await expect(panel).toContainText(old.blocks[0].sha256)
  32 |   await expect(panel).toContainText(current.blocks[0].sha256)
  33 |   const geometry = async () => panel.evaluate(node => ({ width: node.clientWidth, scroll: node.scrollWidth, readerWidth: node.closest('.reader-scroll')!.clientWidth, readerScroll: node.closest('.reader-scroll')!.scrollWidth }))
  34 |   const desktop = await geometry(); expect(desktop.scroll).toBeLessThanOrEqual(desktop.width + 1); expect(desktop.readerScroll).toBeLessThanOrEqual(desktop.readerWidth + 1)
  35 |   await panel.screenshot({ path: info.outputPath('block-compare-1440.png') })
  36 |   await page.setViewportSize({ width: 390, height: 844 })
  37 |   const narrow = await geometry(); expect(narrow.scroll).toBeLessThanOrEqual(narrow.width + 1); expect(narrow.readerScroll).toBeLessThanOrEqual(narrow.readerWidth + 1)
  38 |   await panel.getByRole('button', { name: '收起修订比较', exact: true }).scrollIntoViewIfNeeded()
  39 |   await page.screenshot({ path: info.outputPath('block-compare-controls-390.png') })
  40 |   await left.scrollIntoViewIfNeeded()
  41 |   expect(await left.evaluate(node => getComputedStyle(node).overflowX)).toBe('auto')
  42 |   expect(await left.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(true)
  43 |   await page.screenshot({ path: info.outputPath('block-compare-original-390.png') })
  44 |   await panel.getByRole('button', { name: '收起修订比较', exact: true }).click()
  45 |   await panel.getByRole('button', { name: '比较此块的两个修订', exact: true }).click()
  46 |   await expect(panel.getByLabel('左侧修订', { exact: true })).toHaveValue(old.blocks[0].sha256)
  47 |   await expect(panel.getByLabel('右侧修订', { exact: true })).toHaveValue(current.blocks[0].sha256)
  48 |   expect(await page.request.get('/api/v1/learning/progress').then(response => response.json())).toEqual(before)
  49 |   const contentReads = requests.filter(request => request.path.includes(`/blocks/${old.blocks[0].id}`) || request.path === `/api/v1/objects/${old.blocks[0].id}/revisions`)
  50 |   expect(contentReads.length).toBeGreaterThanOrEqual(5)
  51 |   expect(contentReads.every(request => request.method === 'GET')).toBe(true)
  52 |   expect(requests.filter(request => request.method !== 'GET' && !request.path.startsWith('/api/v1/workbench/'))).toEqual([])
  53 |   await info.attach('comparison-http-readback', { body: JSON.stringify({ old: old.blocks[0], current: current.blocks[0], desktop, narrow, contentReads, learningUnchanged: true }), contentType: 'application/json' })
  54 |   expect(errors).toEqual([])
  55 | })
  56 | 
```