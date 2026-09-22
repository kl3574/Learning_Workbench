# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tutor.spec.ts >> explicit same-Run consent uses the real loopback protocol and restores raw answer without upgrading evidence
- Location: ../../tests/e2e/tutor.spec.ts:148:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('region', { name: '真实问答线程与任务', exact: true }).getByRole('heading', { name: '真实任务状态：completed', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('region', { name: '真实问答线程与任务', exact: true }).getByRole('heading', { name: '真实任务状态：completed', exact: true }) with timeout 5000ms
  - waiting for getByRole('region', { name: '真实问答线程与任务', exact: true }).getByRole('heading', { name: '真实任务状态：completed', exact: true })

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
  - text: 当前课程
  - button "原创练习验收教材 tutornativeapproved"
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
          - button "折叠第一章：数量关系" [expanded]: ⌄
          - link "第一章：数量关系":
            - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22354b3b7b00be8d533853fad09e75ee90acc4a482cbc86ab7e412b0895bdef71f%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%229bd75cb29cc6e3eb899c6e9fce151abbf30efe7553eefd1431d5e4850dc4e9e1%22%7D%7D
          - list:
            - listitem:
              - button "展开内容块：数量关系与基本运算：参考练习" [expanded]: ›
              - text: ○
              - link "数量关系与基本运算：参考练习":
                - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22354b3b7b00be8d533853fad09e75ee90acc4a482cbc86ab7e412b0895bdef71f%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%229bd75cb29cc6e3eb899c6e9fce151abbf30efe7553eefd1431d5e4850dc4e9e1%22%7D%7D
              - list:
                - listitem:
                  - link "数量、步骤与单位":
                    - /url: /?reader=%7B%22course%22%3A%7B%22entity%22%3A%22course%22%2C%22id%22%3A%22course_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%22354b3b7b00be8d533853fad09e75ee90acc4a482cbc86ab7e412b0895bdef71f%22%7D%2C%22lesson%22%3A%7B%22entity%22%3A%22lesson%22%2C%22id%22%3A%22lesson_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%229bd75cb29cc6e3eb899c6e9fce151abbf30efe7553eefd1431d5e4850dc4e9e1%22%7D%2C%22block%22%3A%7B%22entity%22%3A%22block%22%2C%22id%22%3A%22block_tutornativeapproved%22%2C%22revision%22%3A1%2C%22sha256%22%3A%224a49c62153ae4d867196e4e4e5f1b102266dcb3f66d9d8d48fb4de1ef6288555%22%7D%2C%22view%22%3A%22lesson%22%7D#block-block_tutornativeapproved-r1
  - button "笔记"
  - button "创作"
  - button "设置"
- separator "导航栏宽度"
- main:
  - tablist "打开的学习对象":
    - tab "教材"
    - tab "已固定数量关系与基本运算：参考练习 · r1有问题草稿" [selected]: ⌖ 数量关系与基本运算：参考练习 · r1 •
    - button "固定标签 数量关系与基本运算：参考练习 · r1": ⌖
    - button "关闭标签 数量关系与基本运算：参考练习 · r1": ×
  - article:
    - text: 原创练习验收教材 tutornativeapproved › 第一章：数量关系 › 数量关系与基本运算：参考练习
    - heading "数量关系与基本运算：参考练习" [level=1]
    - text: 教材修订 1 · 小节修订 1 · 尚未审校 · 未诊断
    - button "明确标记本节已读"
    - button "为此对象添加书签"
    - button "为当前选文记笔记" [disabled]
    - button "查看笔记"
    - button "本节习题"
    - heading "数量、步骤与单位" [level=2]
    - heading "数量关系与基本运算" [level=1]
    - paragraph: 本材料是原创软件验收样例，尚未接受独立内容审校。
    - paragraph: 先辨认运算、变量与单位，再写出计算步骤。加法可以交换次序；路程除以时间得到速率；矩形面积由两条边长相乘得到。
    - paragraph: 使用练习提示和参考解答会留下帮助与暴露记录，练习不等于独立测试。
    - group: 原始 Markdown 与精确选文
    - group: 来源与提取诊断
    - button "← 上一节" [disabled]
    - button "下一节 →" [disabled]
- separator "Agent 栏宽度"
- complementary "Agent 助教":
  - heading "Agent" [level=2]
  - text: 本地任务 · 明确授权
  - group:
    - text: 当前上下文
    - paragraph: 数量关系与基本运算：参考练习
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
    - paragraph: 当前真实线程：围绕当前内容的问答 · r2 · thread_bb25397eb74e46adba8aa3f40e9d01d0
    - button "刷新本线程消息"
    - region "当前问答任务":
      - heading "真实任务状态：queued" [level=3]
      - group: 任务详情
      - status: 正在观察任务；断开观察不会取消任务
      - button "读取快照并恢复观察"
      - button "明确取消本次问答任务"
      - paragraph: 关闭页面只断开观察。取消请求不等于提供商已停，也不承诺退款。
    - region "问答原文与证据边界":
      - heading "模型输出／推导尝试，未逐项核验" [level=3]
      - paragraph: 保留模型原文；其中的链接、引用标记与自行声称不代表已核验来源。
      - text: 这是原创合成协议返回的完整助教回答。 它只用于验证持久化与浏览器恢复，不表示数学质量已验收。
      - heading "教材已给出的材料：本次实际输入记录" [level=3]
      - paragraph: 这些记录仅证明输入了什么，不证明答案或推导受到这些材料支持。
      - paragraph: 实际消息总字符 568（不是 token 计数）；真实纳入历史 0 条。
      - group: 数量、步骤与单位 · 材料未审
      - paragraph: 本次仅记录实际输入材料；模型回答或推导尚未逐项核验，未进行外部搜索。
      - heading "外部来源陈述" [level=3]
      - paragraph: 尚未外部搜索，没有受检外部来源；模型自报链接不作为已核引文。
      - heading "暂时无法核验" [level=3]
      - paragraph: 本阶段没有逐项数学或事实核验。任务完成只表示本机接受了完整非拒答输出；不代表答案正确。
      - group: 实际用量与提供商终态
    - region "本次问答授权":
      - heading "本次问答的明确授权" [level=3]
      - paragraph: 先本地冻结输入，再核对服务端预览；只有明确批准后才允许派发。配置存在不代表模型具备完整输入计量证明。
      - button "打开提供商设置"
      - button "刷新配置与授权状态"
      - text: 本次选择的提供商
      - combobox "本次选择的提供商":
        - option "请选择"
        - option "provider_tutor_loopback · test-only-complete-byte-model-v1 · r2" [selected]
      - region "授权提案":
        - heading "提案 proposal_43a27b8d947e4125a0c78d3e069b854f" [level=3]
        - status: 当前诊断：当前有效 · 已有关联授权 consent_96f3b34314cb46ca8de4df6d6a683c38，不能再次批准
        - paragraph: 费用未知，金额没有硬保证；仍执行输入、输出和调用次数限制。
        - region "冻结外发摘要":
          - heading "本次服务端冻结范围" [level=4]
          - term: 目的与原任务
          - definition: tutor · run_e8b0d7d6dc194224983f46eadd79bcc3 · 原修订 3
          - term: 提供商与模型
          - definition: provider_tutor_loopback · r2 · test-only-complete-byte-model-v1
          - term: 目的地
          - definition: http://127.0.0.1:37663/v1 · explicit_loopback
          - term: 适配版本
          - definition: compatible_chat · text-request-v2
          - term: 输入字符
          - definition: 568 个 Unicode 码点；按实际发送出现次数计入
          - term: 输入 token 准入
          - definition: 本地完整精确计数 1322 · test-complete-byte-counter-v2
          - term: 硬预算
          - definition: 输入 ≤ 20000；输出 ≤ 2000；提供商调用 1 次；搜索 0 次；工具 0 次；总超时 180 秒
          - term: 联网范围
          - definition: 不允许网页搜索或工具；仅此冻结提供商请求
          - term: 费用
          - definition: 价格未知，金额没有硬保证；未设置金额上限
          - term: 有效期
          - definition: 2026-09-22T01:58:44.813221Z 至 2026-09-22T02:08:44.685Z
          - group: 核对消息、来源与冻结哈希
        - paragraph:
          - text: 提案哈希：
          - code: 098b46b5c40a4f79d2e8363b5aa714f0c1e648c059a87cb19bcfcb4ba288ddff
      - paragraph: 此 Run 已关联授权 consent_96f3b34314cb46ca8de4df6d6a683c38。继续观察原任务，不重新创建问题或再次授权。
      - region "配置与授权命令":
        - heading "配置与授权命令" [level=3]
        - status: 无秘密候选已安全保留在本机
        - region "当前原命令":
          - heading "批准授权" [level=4]
          - paragraph:
            - text: 原 key：
            - code: provider_8bc69909-9d3d-4bdc-8667-36d0928ae885
          - paragraph:
            - text: 仅批准原提案 proposal_43a27b8d947e4125a0c78d3e069b854f /
            - code: 098b46b5c40a4f79d2e8363b5aa714f0c1e648c059a87cb19bcfcb4ba288ddff
            - text: ；批准不同步调用模型。
          - region "冻结外发摘要":
            - heading "本次服务端冻结范围" [level=4]
            - term: 目的与原任务
            - definition: tutor · run_e8b0d7d6dc194224983f46eadd79bcc3 · 原修订 3
            - term: 提供商与模型
            - definition: provider_tutor_loopback · r2 · test-only-complete-byte-model-v1
            - term: 目的地
            - definition: http://127.0.0.1:37663/v1 · explicit_loopback
            - term: 适配版本
            - definition: compatible_chat · text-request-v2
            - term: 输入字符
            - definition: 568 个 Unicode 码点；按实际发送出现次数计入
            - term: 输入 token 准入
            - definition: 本地完整精确计数 1322 · test-complete-byte-counter-v2
            - term: 硬预算
            - definition: 输入 ≤ 20000；输出 ≤ 2000；提供商调用 1 次；搜索 0 次；工具 0 次；总超时 180 秒
            - term: 联网范围
            - definition: 不允许网页搜索或工具；仅此冻结提供商请求
            - term: 费用
            - definition: 价格未知，金额没有硬保证；未设置金额上限
            - term: 有效期
            - definition: 2026-09-22T01:58:44.813221Z 至 2026-09-22T02:08:44.685Z
            - group: 核对消息、来源与冻结哈希
          - status: 原命令已确认 · 修订 1。此回执保留当时事实，不替代当前状态。
          - paragraph: 当前提案 current · 已关联授权 consent_96f3b34314cb46ca8de4df6d6a683c38。
          - button "重试原配置或授权命令" [disabled]
          - button "另行读取当前状态"
          - button "保留候选，返回设置"
  - button "讲解" [pressed]
  - button "提示"
  - button "推导"
  - button "拓展"
  - text: 问题草稿
  - textbox "问题草稿":
    - /placeholder: 写下问题，草稿按当前对象保留…
    - text: 请解释原创材料，并保留未经验证的边界。
  - text: 联网：未授权
  - button "创建本次问答任务 ↑" [disabled]
  - text: 本机草稿保留；发送与结果以本次任务记录为准。
- status: ✓ UI 会话已保存 内容修订 1 正常学习 · 本机
```

# Test source

```ts
  95  |     let actual: TutorRunView | null = null
  96  |     await page.route('**/api/v1/tutor/runs', async route => {
  97  |       starts.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
  98  |       if (starts.length === 1) {
  99  |         const accepted = await route.fetch(); expect(accepted.status()).toBe(202)
  100 |         actual = await accepted.json()
  101 |         await route.abort('failed') // Drop only the already accepted response; server data remain real.
  102 |       } else await route.continue()
  103 |     })
  104 |     await page.getByLabel('问题草稿', { exact: true }).fill('原始问题不得被重试时的新草稿替换。')
  105 |     await expect(page.getByRole('button', { name: '创建本次问答任务 ↑', exact: true })).toBeEnabled()
  106 |     await page.getByRole('button', { name: '创建本次问答任务 ↑', exact: true }).click()
  107 |     await expect(tutor.getByRole('button', { name: '回放原创建问答任务命令', exact: true })).toBeEnabled()
  108 |     expect(actual).not.toBeNull()
  109 |     await page.reload()
  110 |     await expect(tutor.getByRole('button', { name: '回放原创建问答任务命令', exact: true })).toBeEnabled()
  111 |     await tutor.getByRole('button', { name: '回放原创建问答任务命令', exact: true }).click()
  112 |     await expect(tutor.getByRole('heading', { name: '真实任务状态：awaiting_approval', exact: true })).toBeVisible()
  113 |     expect(starts).toHaveLength(2); expect(starts[1]).toEqual(starts[0])
  114 |     const id = (actual as unknown as TutorRunView).run.id
  115 |     const messages: TutorMessagePage = await page.request.get(`/api/v1/threads/${thread.id}/messages`).then(value => value.json())
  116 |     expect(messages.items).toHaveLength(1); expect(messages.items[0].run_id).toBe(id)
  117 |     const other = await context.newPage()
  118 |     const session: SessionResponse = await other.request.get('/api/v1/session').then(value => value.json())
  119 |     const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token }
  120 |     const attemptResponse = await other.request.post(`/api/v1/assessments/${fixture.assessment.id}/attempts`, { data: { assessment_ref: fixture.assessment, mode: 'open_book' }, headers: { ...headers, 'Idempotency-Key': 'synthetic-tutor-openbook' } })
  121 |     expect(attemptResponse.status()).toBe(201)
  122 |     const attempt: AttemptSnapshot = await attemptResponse.json()
  123 |     await expect(page.getByRole('heading', { name: 'Agent · 固定操作帮助', exact: true })).toBeVisible()
  124 |     await expect(tutor).toHaveCount(0)
  125 |     await expect(page.getByLabel('问题草稿', { exact: true })).toHaveCount(0)
  126 |     await expect(page.locator('.real-reader > h1')).toBeVisible()
  127 |     await expect(page.locator('.import-trigger')).toBeEnabled()
  128 |     const controls = page.getByRole('region', { name: '问答任务停止控制', exact: true })
  129 |     const readingControl = page.waitForResponse(value => value.url().endsWith(`/api/v1/jobs/${id}`) && value.request().method() === 'GET')
  130 |     await controls.getByRole('button', { name: `读取任务控制 ${id}`, exact: true }).click()
  131 |     const controlResponse = await readingControl, controlBody = await controlResponse.json()
  132 |     writeFileSync(info.outputPath('control-read-observation.json'), JSON.stringify({ status: controlResponse.status(), value: { id: controlBody.id, workspace_id: controlBody.workspace_id, kind: controlBody.kind, revision: controlBody.revision, status: controlBody.status }, error_code: controlBody.error?.code ?? null, controls_text: await controls.innerText() }, null, 2))
  133 |     expect(controlResponse.status()).toBe(200)
  134 |     await controls.getByRole('button', { name: '明确请求取消此任务', exact: true }).click()
  135 |     await expect(controls.getByText('已有原取消回执；请重新读取实际控制状态，不把回执当作当前或远端终态。', { exact: true })).toBeVisible()
  136 |     await controls.getByRole('button', { name: `读取任务控制 ${id}`, exact: true }).click()
  137 |     await expect(controls.getByText(new RegExp(`${id} · cancelled · r`))).toBeVisible()
  138 |     expect((await other.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { data: { expected_revision: attempt.revision }, headers: { ...headers, 'Idempotency-Key': 'synthetic-tutor-openbook-end' } })).status()).toBe(200)
  139 |     await expect(tutor.getByRole('button', { name: new RegExp(`^${thread.title} · r`) })).toBeVisible()
  140 |     await tutor.getByRole('button', { name: new RegExp(`^${thread.title} · r`) }).click()
  141 |     await expect(tutor.getByRole('heading', { name: '真实任务状态：cancelled', exact: true })).toBeVisible()
  142 |     const final: TutorRunView = await page.request.get(`/api/v1/runs/${id}`).then(value => value.json())
  143 |     expect(final.run.id).toBe(id); expect(final.result.provider).toBeNull(); expect(final.run.answer_markdown).toBe('')
  144 |     writeFileSync(info.outputPath('actual-tutor-lost-ack-policy.json'), JSON.stringify({ scope: 'Actual server response dropped after accepted POST; original command replay, single persisted user message, real separate-page open_book activation, academic DOM removed, Reader/import usable, Policy-safe cancellation and restored current Run.', starts, original_ack: actual, thread_messages: messages, open_book_id: attempt.id, final }, null, 2))
  145 |   } finally { await runtime.close() }
  146 | })
  147 | 
  148 | test('explicit same-Run consent uses the real loopback protocol and restores raw answer without upgrading evidence', async ({ playwright }, info) => {
  149 |   test.setTimeout(90_000)
  150 |   const runtime = await TutorRuntime.start(), errors: string[] = []
  151 |   let diagnostic: Awaited<ReturnType<typeof observeTutorCompletion>> | undefined
  152 |   try {
  153 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  154 |     diagnostic = await observeTutorCompletion(page, { readRuntime: () => runtime.diagnosticControl() })
  155 |     page.on('pageerror', error => errors.push(error.message))
  156 |     await runtime.authenticateOnly(page)
  157 |     await expect(page.locator('.import-trigger')).toBeEnabled()
  158 |     const fixture = originalAssessmentPackage('tutornativeapproved')
  159 |     const imported = await importAssessmentPackage(page, fixture)
  160 |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  161 |     const initialControl = runtime.control()
  162 |     expect(initialControl.test_only).toBe(true); expect(initialControl.received_request_count).toBe(0)
  163 |     const session: SessionResponse = await page.request.get('/api/v1/session').then(value => value.json())
  164 |     const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token }
  165 |     const config: ProviderConfigWrite = { expected_revision: 0, adapter: initialControl.adapter, base_url: initialControl.base_url, model: initialControl.model, embedding_model: null, endpoint_policy: 'explicit_loopback', pricing: null }
  166 |     expect((await page.request.put('/api/v1/providers/provider_tutor_loopback/config', { data: config, headers: { ...headers, 'Idempotency-Key': 'synthetic-loopback-config' } })).status()).toBe(200)
  167 |     expect((await page.request.post('/api/v1/providers/provider_tutor_loopback/secret', { data: { expected_revision: 1, secret: 'synthetic-loopback-native-constant' }, headers: { ...headers, 'Idempotency-Key': 'synthetic-loopback-secret' } })).status()).toBe(200)
  168 |     await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
  169 |     await expect(page.locator('.real-reader > h1')).toBeVisible()
  170 |     const tutor = page.getByRole('region', { name: '真实问答线程与任务', exact: true })
  171 |     const creating = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/threads'))
  172 |     await tutor.getByRole('button', { name: '明确创建本地线程', exact: true }).click()
  173 |     const thread: TutorThreadView = await (await creating).json()
  174 |     await page.getByLabel('问题草稿', { exact: true }).fill('请解释原创材料，并保留未经验证的边界。')
  175 |     await expect(page.getByRole('button', { name: '创建本次问答任务 ↑', exact: true })).toBeEnabled()
  176 |     const starting = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/tutor/runs'))
  177 |     await page.getByRole('button', { name: '创建本次问答任务 ↑', exact: true }).click()
  178 |     const ack: TutorRunView = await (await starting).json()
  179 |     diagnostic.bindRun(ack.run.id)
  180 |     await expect(tutor.getByRole('heading', { name: '真实任务状态：awaiting_approval', exact: true })).toBeVisible()
  181 |     expect(runtime.control().received_request_count).toBe(0)
  182 |     const preview = tutor.getByRole('region', { name: '准备授权预览', exact: true })
  183 |     await preview.getByLabel('最大输入 token', { exact: true }).fill('20000')
  184 |     await preview.getByLabel('最大输出 token', { exact: true }).fill('2000')
  185 |     await preview.getByLabel('到期时间 UTC', { exact: true }).fill(new Date(Date.now() + 600_000).toISOString())
  186 |     await preview.getByRole('button', { name: '准备服务端预览命令', exact: true }).click()
  187 |     await tutor.getByRole('button', { name: '确认发送授权预览', exact: true }).click()
  188 |     await expect(tutor.getByLabel('我已核对本次冻结范围、目的地、预算与到期时间', { exact: true })).toBeVisible()
  189 |     expect(runtime.control().received_request_count).toBe(0)
  190 |     await tutor.getByLabel('我已核对本次冻结范围、目的地、预算与到期时间', { exact: true }).check()
  191 |     await tutor.getByRole('button', { name: '准备批准本次授权命令', exact: true }).click()
  192 |     diagnostic.mark('grant_click')
  193 |     await tutor.getByRole('button', { name: '确认发送批准授权', exact: true }).click()
  194 |     await diagnostic.around(info, async () => {
> 195 |       await expect(tutor.getByRole('heading', { name: '真实任务状态：completed', exact: true })).toBeVisible()
      |                                                                                           ^ Error: expect(locator).toBeVisible() failed
  196 |     })
  197 |     const complete: TutorRunView = await page.request.get(`/api/v1/runs/${ack.run.id}`).then(value => value.json())
  198 |     expect(complete.run.id).toBe(ack.run.id); expect(complete.run.thread_id).toBe(thread.id)
  199 |     expect(complete.consent_id).toBeTruthy(); expect(complete.latest_proposal_id).toBeTruthy()
  200 |     expect(complete.run.answer_markdown).toBe(initialControl.answer_markdown)
  201 |     expect(complete.run.citations).toEqual([]); expect(complete.result.provider?.outcome).toBe('complete')
  202 |     expect(complete.result.usage.input_tokens).toBeGreaterThan(0); expect(complete.result.usage.output_tokens).toBeGreaterThan(0)
  203 |     await expect.poll(() => runtime.control().validated_request_count).toBe(1)
  204 |     expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0)
  205 |     await expect(tutor.getByLabel('本次模型回答原文', { exact: true })).toHaveText(initialControl.answer_markdown)
  206 |     await expect(tutor.getByText('这些记录仅证明输入了什么，不证明答案或推导受到这些材料支持。', { exact: true })).toBeVisible()
  207 |     await expect(tutor.getByText('尚未外部搜索，没有受检外部来源；模型自报链接不作为已核引文。', { exact: true })).toBeVisible()
  208 |     await page.reload()
  209 |     await tutor.getByRole('button', { name: `${thread.title} · r${complete.thread_revision}`, exact: true }).click()
  210 |     await expect(tutor.getByRole('heading', { name: '真实任务状态：completed', exact: true })).toBeVisible()
  211 |     await expect(tutor.getByLabel('本次模型回答原文', { exact: true })).toHaveText(initialControl.answer_markdown)
  212 |     expect(runtime.control().received_request_count).toBe(1)
  213 |     await tutor.getByLabel('本次模型回答原文', { exact: true }).scrollIntoViewIfNeeded()
  214 |     await page.screenshot({ path: info.outputPath('tutor-loopback-answer-1440.png') })
  215 |     await page.setViewportSize({ width: 390, height: 844 })
  216 |     await page.getByRole('button', { name: '切换 Agent 栏', exact: true }).click()
  217 |     await expect(page.getByRole('dialog', { name: 'Agent 助教', exact: true })).toBeVisible()
  218 |     await tutor.getByRole('button', { name: `${thread.title} · r${complete.thread_revision}`, exact: true }).click()
  219 |     await expect(tutor.getByLabel('本次模型回答原文', { exact: true })).toHaveText(initialControl.answer_markdown)
  220 |     await tutor.getByLabel('本次模型回答原文', { exact: true }).scrollIntoViewIfNeeded()
  221 |     await page.screenshot({ path: info.outputPath('tutor-loopback-answer-390.png') })
  222 |     expect(errors).toEqual([])
  223 |     writeFileSync(info.outputPath('actual-tutor-loopback.json'), JSON.stringify({ scope: 'Test-only complete-byte model, synthetic secret and original material; actual loopback HTTP, provider ledger, Tutor worker/SSE and native UI. No production input proof, vendor call or answer-quality acceptance.', thread, create_ack: ack, final: complete, observation: runtime.control(), runtime_errors: errors }, null, 2))
  224 |   } finally { diagnostic?.dispose(); await runtime.close() }
  225 | })
  226 | 
```