# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: content-impacts.spec.ts >> native edit publication discovers actual impacts and preserves human decisions through CAS, lost reply, IDB failure, access changes, stable pages and restart
- Location: ../../tests/e2e/content-impacts.spec.ts:28:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('region', { name: '内容变更影响复核', exact: true }).getByRole('region', { name: '本次读取的内容影响详情', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('region', { name: '内容变更影响复核', exact: true }).getByRole('region', { name: '本次读取的内容影响详情', exact: true }) with timeout 5000ms
  - waiting for getByRole('region', { name: '内容变更影响复核', exact: true }).getByRole('region', { name: '本次读取的内容影响详情', exact: true })

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
        - row "项目 原基准（版本 6） 本地待同步 服务端（版本 9）":
          - columnheader "项目"
          - columnheader "原基准（版本 6）"
          - columnheader "本地待同步"
          - columnheader "服务端（版本 9）"
      - rowgroup:
        - row "课程 保留的课程引用（待解析） 保留的课程引用（待解析） 保留的课程引用（待解析）":
          - rowheader "课程"
          - cell "保留的课程引用（待解析）"
          - cell "保留的课程引用（待解析）"
          - cell "保留的课程引用（待解析）"
        - row "当前入口 教材 教材 教材":
          - rowheader "当前入口"
          - cell "教材"
          - cell "教材"
          - cell "教材"
        - row "导航栏 展开，300 像素 展开，300 像素 展开，300 像素":
          - rowheader "导航栏"
          - cell "展开，300 像素"
          - cell "展开，300 像素"
          - cell "展开，300 像素"
        - row "Agent 栏 展开，368 像素 展开，368 像素 展开，368 像素":
          - rowheader "Agent 栏"
          - cell "展开，368 像素"
          - cell "展开，368 像素"
          - cell "展开，368 像素"
        - row "打开的内容 待解析对象 · 修订 1（当前） 待解析对象 · 修订 1（当前） 待解析对象 · 修订 1（当前）":
          - rowheader "打开的内容"
          - cell "待解析对象 · 修订 1（当前）"
          - cell "待解析对象 · 修订 1（当前）"
          - cell "待解析对象 · 修订 1（当前）"
        - row "目录位置 距顶部 0 像素，展开 2 项 距顶部 0 像素，展开 2 项 距顶部 0 像素，展开 2 项":
          - rowheader "目录位置"
          - cell "距顶部 0 像素，展开 2 项"
          - cell "距顶部 0 像素，展开 2 项"
          - cell "距顶部 0 像素，展开 2 项"
        - row "阅读位置 距顶部 129 像素 距顶部 558 像素 距顶部 129 像素":
          - rowheader "阅读位置"
          - cell "距顶部 129 像素"
          - cell "距顶部 558 像素"
          - cell "距顶部 129 像素"
    - button "采用本地会话并重新保存"
    - button "采用服务端会话，放弃本地 UI 修改"
- status:
  - text: 发现其他窗口的待同步 UI 快照；原始快照保留。
  - button "恢复待同步快照 1"
- complementary "课程导航":
  - text: 当前课程
  - button "原创影响验收教材"
  - paragraph: 1 章 / 1 节 · 尚未审校
  - text: 已阅读 0 / 1 · 未诊断
  - button "查看教材修订"
  - button "继续阅读 →"
  - navigation "学习主导航":
    - button "学习路线"
    - button "教材 含例题"
    - button "习题 含解答"
    - button "测试题"
  - region "当前教材目录":
    - heading "当前教材目录" [level=2]
    - button "完整标题"
    - text: 搜索当前目录
    - textbox "搜索当前目录":
      - /placeholder: 搜索章节、小节、内容块标题
    - navigation "上下文目录":
      - list:
        - listitem:
          - button "折叠原创影响验收教材" [expanded]: ⌄
          - link "原创影响验收教材":
            - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%221300c85e5db00898f85d3c4c14cfd6aebe07199d246e87d7890f882394334453%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22fb795729c84dc9cde4daec8adcd122e7e011766ac3147511a8b2a4a596f98cd4%22%7D%7D
          - list:
            - listitem:
              - button "展开内容块：原创影响验收小节" [expanded]: ›
              - text: ○
              - link "原创影响验收小节":
                - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%221300c85e5db00898f85d3c4c14cfd6aebe07199d246e87d7890f882394334453%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22fb795729c84dc9cde4daec8adcd122e7e011766ac3147511a8b2a4a596f98cd4%22%7D%7D
              - list:
                - listitem:
                  - link "原创合成编辑标题":
                    - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%221300c85e5db00898f85d3c4c14cfd6aebe07199d246e87d7890f882394334453%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22fb795729c84dc9cde4daec8adcd122e7e011766ac3147511a8b2a4a596f98cd4%22%7D%2C%22block%22%3A%7B%22entity%22%3A%22block%22%2C%22id%22%3A%22block_native_impact%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22ab01a0afdc4f33e23ecf70586cab0b12749546bfb3bc9e7a191c7d250f708017%22%7D%2C%22view%22%3A%22lesson%22%7D#block-block_native_impact-r1
  - button "笔记"
  - button "创作"
  - button "设置"
- separator "导航栏宽度"
- main:
  - tablist "打开的学习对象":
    - tab "教材"
    - tab "已固定原创合成编辑标题 · r1" [selected]: ⌖ 原创合成编辑标题 · r1
    - button "固定标签 原创合成编辑标题 · r1": ⌖
    - button "关闭标签 原创合成编辑标题 · r1": ×
  - article:
    - text: 原创影响验收教材 › 课程 › 原创影响验收小节
    - heading "原创影响验收小节" [level=1]
    - text: 教材修订 1 · 小节修订 1 · 尚未审校 · 未诊断
    - paragraph: 正在阅读旧修订。旧正文、选文与笔记引用保留；未自动改为当前版本。
    - button "明确标记本节已读"
    - button "为此对象添加书签"
    - button "为当前选文记笔记" [disabled]
    - button "查看笔记"
    - button "本节习题"
    - heading "原创合成编辑标题" [level=2]
    - paragraph: 原创合成编辑正文。仅验证软件保存、冲突与恢复，不作教学批准。
    - group: 原始 Markdown 与精确选文
    - group: 来源与提取诊断
    - region "块修订比较":
      - button "比较此块的两个修订"
      - button "打开此块的恢复原记录"
    - region "文本块编辑与恢复":
      - button "编辑此精确文本块"
    - button "← 上一节" [disabled]
    - button "下一节 →" [disabled]
- separator "Agent 栏宽度"
- complementary "Agent 助教":
  - heading "Agent" [level=2]
  - text: 本地任务 · 明确授权
  - group:
    - text: 当前上下文
    - paragraph: 原创合成编辑标题
    - text: 修订 1 · 已解析的准确引用
    - group: 查看引用范围
  - group: 明确选择本次附加范围（默认无）
  - region "真实问答线程与任务":
    - paragraph: 发送先建立本地任务并准备上下文，不自动外发；随后核对并明确批准本次授权。
    - button "重新读取线程与当前绑定"
    - text: 新线程标题
    - textbox "新线程标题": 围绕当前内容的问答
    - button "明确创建本地线程"
    - paragraph: 当前已读取页没有此精确对象的线程；可创建或继续读取服务器列表。
    - region "问答原文与证据边界"
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
- status: 会话版本冲突 内容修订 1 正常学习 · 本机
```

# Test source

```ts
  1   | import { writeFileSync } from 'node:fs'
  2   | import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3   | import type { ContentImpactPage as ImpactPage, ContentImpactView as View, ImpactObjectDecisionWrite as Write, ImpactObjectDecisionReceipt as Receipt } from '../../packages/contracts/generated/api-types'
  4   | import { RestartRuntime } from './restartRuntime'
  5   | import { publishEditedBlock, publishExtra } from './contentImpactsData'
  6   | import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
  7   | const panel = (page: Page) => page.getByRole('region', { name: '内容变更影响复核', exact: true })
  8   | async function open(page: Page) { await page.getByRole('button', { name: '创作', exact: true }).click(); await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click(); await expect(panel(page).getByRole('button', { name: '从第一页读取内容变更', exact: true })).toBeVisible() }
  9   | async function list(page: Page, filter = '', limit = '20'): Promise<ImpactPage> {
  10  |   await panel(page).getByLabel('按原变更对象标识筛选（留空查看全部）', { exact: true }).fill(filter); await panel(page).getByLabel('每页事件数', { exact: true }).fill(limit)
  11  |   const response = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === '/api/v1/content/impacts')
  12  |   await panel(page).getByRole('button', { name: '从第一页读取内容变更', exact: true }).click(); const r = await response; expect(r.status()).toBe(200); return r.json()
  13  | }
  14  | async function freeze(page: Page, event: string, target: string) {
  15  |   await panel(page).getByRole('button', { name: `读取对象当前依据 ${target}`, exact: true }).click()
  16  |   await panel(page).getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click()
  17  |   await expect(panel(page).getByRole('group', { name: '本次人工内容决定', exact: true })).toContainText(event)
  18  | }
  19  | async function form(page: Page, decision: Write['decision'], reason: string) {
  20  |   await panel(page).getByLabel('本次人工决定', { exact: true }).selectOption(decision); await panel(page).getByRole('textbox', { name: '决定理由', exact: true }).fill(reason)
  21  |   await panel(page).getByLabel('我已比对原变更、当前对象和冻结依据，明确追加这次人工判断。', { exact: true }).check()
  22  | }
  23  | async function submit(page: Page) { await panel(page).getByRole('button', { name: '明确保存内容决定', exact: true }).click() }
  24  | async function view(page: Page, event: string, target: string): Promise<View> { const r = await page.request.get(`/api/v1/content/impacts/${event}?target_id=${target}`); expect(r.status()).toBe(200); return r.json() }
  25  | async function journal(page: Page) {
  26  |   return page.evaluate(async () => { const db = await new Promise<IDBDatabase>((yes, no) => { const r = indexedDB.open('learning-workbench.content-impact-commands.v1', 1); r.onsuccess = () => yes(r.result); r.onerror = () => no(r.error) }); try { return await new Promise<string[]>((yes, no) => { const t = db.transaction('drafts', 'readonly'), r = t.objectStore('drafts').getAll(); r.onsuccess = () => yes(r.result.map((x: { text: string }) => x.text)); r.onerror = () => no(r.error) }) } finally { db.close() } })
  27  | }
  28  | test('native edit publication discovers actual impacts and preserves human decisions through CAS, lost reply, IDB failure, access changes, stable pages and restart', async ({ playwright }, info) => {
  29  |   test.setTimeout(210_000)
  30  |   const runtime = await RestartRuntime.start(), errors: string[] = []
  31  |   try {
  32  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', e => errors.push(e.message)); await runtime.authenticateOnly(page)
  33  |     const publication = await publishEditedBlock(page, runtime), target = publication.fixture.lessons[0].id, block = publication.fixture.blocks[0].id
  34  |     const session = await page.request.get('/api/v1/session').then(r => r.json())
  35  |     const parentRead = await page.request.get(`/api/v1/lessons/${target}?revision=1`); expect(parentRead.status()).toBe(200); const parentBefore = await parentRead.json(); expect(parentBefore.block_refs).toEqual([publication.fixture.blocks[0]])
  36  |     await open(page)
  37  |     const discovered = await list(page, block); expect(discovered.items).toHaveLength(1)
  38  |     const event = discovered.items[0].event_id // Obtained solely from actual UI request, never SQL/outbox injection.
  39  |     await panel(page).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await freeze(page, event, target); await form(page, 'no_revision_needed', 'Explicit synthetic first Content judgment; no other owner completion.')
  40  |     const competing = await context.browser()!.newContext({ storageState: await context.storageState() }), other = await competing.newPage(); await other.goto(runtime.origin); await open(other); expect((await list(other, block)).items[0].event_id).toBe(event)
  41  |     await panel(other).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await freeze(other, event, target); await form(other, 'new_revision_required', 'Synthetic competing old-head judgment')
  42  |     const commands: { key: string; body: Write }[] = []; let original!: Receipt, accepted!: () => void; const acceptance = new Promise<void>(r => { accepted = r }), endpoint = `**/api/v1/content/impacts/${event}/decisions`
  43  |     await page.route(endpoint, async route => { commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() }); if (commands.length === 1) { const r = await route.fetch(); expect(r.status()).toBe(200); original = await r.json(); accepted(); await route.abort('failed') } else await route.continue() })
  44  |     await other.route(endpoint, async route => { await acceptance; await route.continue() })
  45  |     await Promise.all([submit(page), submit(other)])
  46  |     await expect(panel(page).getByText(/决定结果未知，原提交内容已保留/)).toBeVisible(); await expect(panel(other).getByText(/对象修订或决定版本已变化（412）/)).toBeVisible()
  47  |     expect(original.classification).toBe('exact_ref'); expect((await view(page, event, target)).target_decision_head).toBe(1)
  48  |     await page.evaluate(() => { const original = IDBDatabase.prototype.transaction; Object.assign(window, { restoreImpactIdb: () => { IDBDatabase.prototype.transaction = original } }); IDBDatabase.prototype.transaction = function (...args: Parameters<IDBDatabase['transaction']>) { const tx = original.apply(this, args); if (this.name === 'learning-workbench.content-impact-commands.v1' && args[1] === 'readwrite') queueMicrotask(() => tx.abort()); return tx } })
  49  |     await panel(page).getByText(/决定结果未知，原提交内容已保留/).click()
  50  |     const replay = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/content/impacts/${event}/decisions`))
  51  |     await panel(page).getByRole('button', { name: `按原提交内容重试 ${commands[0].key}`, exact: true }).click(); expect((await replay).status()).toBe(200)
  52  |     await expect(panel(page).getByText(/原决定或已收到的回执尚未安全保存到本机/)).toBeVisible(); expect(commands[1]).toEqual(commands[0]); expect(JSON.parse((await journal(page))[0]).ack).toBeNull()
  53  |     await page.getByRole('button', { name: '关闭创作', exact: true }).click(); const guard = page.getByRole('dialog', { name: '保留创作原命令', exact: true })
  54  |     await expect(guard.getByRole('button', { name: '保留原命令，明确丢弃临时表单并关闭', exact: true })).toBeDisabled()
  55  |     await guard.getByRole('button', { name: '保留内容决定隔离内存，丢弃临时表单并前往角色控制', exact: true }).click()
  56  |     await page.getByRole('button', { name: '切换为学习者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click()
  57  |     await page.getByRole('button', { name: '创作', exact: true }).click(); await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click()
  58  |     await expect(panel(page).getByText(/原决定或已收到的回执尚未安全保存到本机/)).toBeVisible(); await expect(panel(page).getByRole('region', { name: '本机保留的内容决定', exact: true })).toHaveCount(0)
  59  |     await expect(panel(page).getByRole('button', { name: '只保存原会话的内容决定内存', exact: true })).toBeDisabled()
  60  |     await page.evaluate(() => (window as unknown as { restoreImpactIdb(): void }).restoreImpactIdb())
  61  |     await page.getByRole('button', { name: '关闭创作', exact: true }).click(); await guard.getByRole('button', { name: '保留内容决定隔离内存，丢弃临时表单并前往角色控制', exact: true }).click()
  62  |     await page.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click(); await open(page)
  63  |     await panel(page).getByRole('button', { name: '只保存原会话的内容决定内存', exact: true }).click(); await expect(panel(page).getByText(new RegExp(`原决定回执已保存.*${commands[0].key}`))).toBeVisible(); expect(commands).toHaveLength(2)
  64  |     expect(JSON.parse((await journal(page))[0]).ack).toEqual(original); await panel(page).getByText(new RegExp(`原决定回执已保存.*${commands[0].key}`)).click()
  65  |     await expect(panel(page).getByRole('button', { name: `按原提交内容重试 ${commands[0].key}`, exact: true })).toBeDisabled(); await competing.close()
  66  |     const extra = [publishExtra(runtime, session.workspace_id, publication.fixture.lessons[0], [2])]
  67  |     await panel(page).getByRole('button', { name: `另行读取原决定对象 ${commands[0].key}`, exact: true }).click(); await panel(page).getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click()
  68  |     await form(page, 'new_revision_required', 'Explicit new-head correction after target revision changed; ID-only remains conservative.'); await submit(page)
  69  |     await expect.poll(async () => (await view(page, event, target)).target_decision_head).toBe(2)
  70  |     const corrected = await view(page, event, target); expect(corrected.decisions[1].classification).toBe('id_only_candidate'); expect(corrected.action_required_target_ids).toContain(target)
  71  |     expect(corrected.decisions[0]).toEqual(original)
  72  |     extra.push(publishExtra(runtime, session.workspace_id, publication.published, [3, 4]))
  73  |     const firstPage = await list(page, block, '1'), ids = [firstPage.items[0].event_id]; expect(firstPage.next_cursor).not.toBeNull()
  74  |     extra.push(publishExtra(runtime, session.workspace_id, publication.published, [5]))
  75  |     for (let n = 0; n < 2; n++) { const next = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === '/api/v1/content/impacts'); await panel(page).getByRole('button', { name: '沿原筛选读取下一页事件', exact: true }).click(); const response = await next; expect(response.status()).toBe(200); const value: ImpactPage = await response.json(); ids.push(value.items[0].event_id); if (n === 1) expect(value.next_cursor).toBeNull() }
  76  |     expect(new Set(ids).size).toBe(3); expect((await list(page, block)).items).toHaveLength(4); expect((await list(page, target)).items).toHaveLength(1)
  77  |     const all = await list(page); expect(all.items).toHaveLength(5)
  78  |     await panel(page).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click()
  79  |     for (const width of [1440, 390]) { await page.setViewportSize({ width, height: 900 }); await panel(page).scrollIntoViewIfNeeded(); expect(await panel(page).evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true); await page.screenshot({ path: info.outputPath(`content-impacts-${width}.png`) }) }
  80  |     const durable = await journal(page), database = runtime.databaseIdentity(); await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
  81  |     const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; await restored.goto(runtime.origin); await open(restored)
  82  |     expect((await list(restored, block)).items.map(x => x.event_id)).toContain(event); expect(await journal(restored)).toEqual(durable); expect(runtime.databaseIdentity()).toEqual(database)
  83  |     await panel(restored).getByText(new RegExp(`原决定回执已保存.*${commands[0].key}`)).click(); await expect(panel(restored).getByRole('button', { name: `按原提交内容重试 ${commands[0].key}`, exact: true })).toBeDisabled()
  84  |     expect(await restored.request.get(`/api/v1/lessons/${target}?revision=1`).then(r => r.json())).toEqual(parentBefore)
  85  |     await panel(restored).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await expect(panel(restored).getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toBeVisible()
  86  |     const policyPage = await next.newPage(); await policyPage.goto(runtime.origin); const assessment = originalAssessmentPackage('impactpolicy'); const imported = await importAssessmentPackage(policyPage, assessment); await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
> 87  |     await panel(restored).getByRole('button', { name: '重新核验内容复核权限', exact: true }).click(); await list(restored, block); await panel(restored).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await expect(panel(restored).getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toBeVisible()
      |                                                                                                                                                                                                                                                                                                               ^ Error: expect(locator).toBeVisible() failed
  88  |     expect((await restored.request.get('/api/v1/session').then(r => r.json())).role).toBe('author')
  89  |     const href = `${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: assessment.assessment, course_ref: assessment.course }))}`; await policyPage.goto(href)
  90  |     await policyPage.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await policyPage.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  91  |     await expect(policyPage.getByText('独立测试进行中', { exact: true }).first()).toBeVisible(); await expect(panel(restored).getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toHaveCount(0); await expect(panel(restored).getByRole('region', { name: '本机保留的内容决定', exact: true })).toHaveCount(0)
  92  |     expect((await restored.request.get('/api/v1/content/impacts')).status()).toBe(409)
  93  |     writeFileSync(info.outputPath('actual-content-impacts.json'), JSON.stringify({ scope: 'Actual native UI Edit/Review/manual publication then public impact discovery, decisions, lost response, real IDB abort and actor isolation. Extra owner publications only test pagination; event IDs always from HTTP. Synthetic intent; no academic/numeric approval.', publication, discovered, original, corrected, commands, page_membership: ids, all, extra, durable, parentBefore, page_errors: errors }, null, 2))
  94  |     expect(errors).toEqual([])
  95  |   } finally { await runtime.close() }
  96  | })
  97  | 
  98  | test('native unsubmitted Content judgment survives role cycles with original basis and explicit close discard', async ({ playwright }, info) => {
  99  |   test.setTimeout(150_000)
  100 |   const runtime = await RestartRuntime.start(), decisionWrites: string[] = []
  101 |   try {
  102 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && /^\/api\/v1\/content\/impacts\/[^/]+\/decisions$/.test(path)) decisionWrites.push(path) }); await runtime.authenticateOnly(page)
  103 |     const publication = await publishEditedBlock(page, runtime), target = publication.fixture.lessons[0].id
  104 |     const currentSession = await page.request.get('/api/v1/session').then(r => r.json())
  105 |     await open(page); const event = (await list(page, publication.published.id)).items[0].event_id
  106 |     await panel(page).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await freeze(page, event, target)
  107 |     const reason = '尚未提交的原始人工理由 α\n保留换行、Unicode 与旧依据。'
  108 |     await form(page, 'new_revision_required', reason)
  109 |     const controls = await context.newPage(); await controls.goto(runtime.origin); await expect(controls.getByText('✓ UI 会话已保存')).toBeVisible(); await controls.keyboard.press('Control+Shift+P'); await controls.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ }).click()
  110 |     for (let i = 0; i < 2; i++) {
  111 |       await controls.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  112 |       await expect(panel(page).getByRole('textbox', { name: '决定理由', exact: true })).toHaveCount(0)
  113 |       await expect(panel(page).getByText(/本页仍保留未提交的内容决定表单与原依据/)).toBeVisible()
  114 |       await expect(panel(page).getByRole('button', { name: '重新核验权限与当前依据，恢复原会话表单', exact: true })).toBeDisabled()
  115 |       if (i === 1) publishExtra(runtime, currentSession.workspace_id, publication.fixture.lessons[0], [2])
  116 |       await controls.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  117 |       const restoring = panel(page).getByRole('button', { name: '重新核验权限与当前依据，恢复原会话表单', exact: true }); await expect(restoring).toBeEnabled(); await restoring.click()
  118 |       await expect(panel(page).getByRole('textbox', { name: '决定理由', exact: true })).toHaveValue(reason)
  119 |       await expect(panel(page).getByLabel('我已比对原变更、当前对象和冻结依据，明确追加这次人工判断。', { exact: true })).not.toBeChecked()
  120 |       expect(await journal(page)).toEqual([])
  121 |     }
  122 |     await expect(panel(page).getByText(/新读取与已采用依据不同/)).toBeVisible()
  123 |     await panel(page).getByLabel('我已比对原变更、当前对象和冻结依据，明确追加这次人工判断。', { exact: true }).check()
  124 |     await expect(panel(page).getByRole('button', { name: '明确保存内容决定', exact: true })).toBeDisabled()
  125 |     await panel(page).getByRole('button', { name: '丢弃未提交表单与冻结依据', exact: true }).click()
  126 |     await panel(page).getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click(); await form(page, 'no_revision_needed', reason)
  127 |     await page.getByRole('button', { name: '关闭创作', exact: true }).click()
  128 |     const guard = page.getByRole('dialog', { name: '保留创作原命令', exact: true }); await guard.getByRole('button', { name: '返回创作', exact: true }).click(); await expect(panel(page).getByRole('textbox', { name: '决定理由', exact: true })).toHaveValue(reason)
  129 |     await page.getByRole('button', { name: '关闭创作', exact: true }).click(); await guard.getByRole('button', { name: '保留原命令，明确丢弃临时表单并关闭', exact: true }).click()
  130 |     await open(page); await expect(panel(page).getByText(/本页仍保留未提交的内容决定表单与原依据/)).toHaveCount(0)
  131 |     expect(await journal(page)).toEqual([]); expect((await view(page, event, target)).decisions).toEqual([]); expect(decisionWrites).toEqual([])
  132 |     writeFileSync(info.outputPath('unsubmitted-form-readback.json'), JSON.stringify({ scope: 'Synthetic unsubmitted judgment; two real role cycles, fresh same-session restore, changed target keeps original basis, confirmed explicit close discard. No Content decision HTTP write.', reason, event, decisionWrites, original_target: publication.fixture.lessons[0], durable_commands: await journal(page), decisions: (await view(page, event, target)).decisions }, null, 2))
  133 |   } finally { await runtime.close() }
  134 | })
  135 | 
```