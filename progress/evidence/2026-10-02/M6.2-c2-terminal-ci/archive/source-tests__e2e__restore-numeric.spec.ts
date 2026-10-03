import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRestoreDraftSnapshot } from '../../packages/contracts/generated/api-types'
import type { RestoreNumericCheckView } from '../../packages/contracts/generated/restore-numeric-types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, originalReaderPackage } from './readerTestData'

test('actual Restore numeric UI freezes manually anchored material, requires separate execution approval and preserves actual sandbox outcome', async ({ playwright }, info) => {
  test.setTimeout(180_000)
  const runtime = await RestartRuntime.start(), writes: { path: string; key: string; body: unknown }[] = [], errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page)
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => { if (request.method() === 'POST' && /restore-(?:drafts\/[^/]+\/numeric-checks|numeric-checks\/[^/]+\/decision)$/.test(new URL(request.url()).pathname)) writes.push({ path: new URL(request.url()).pathname, key: request.headers()['idempotency-key'], body: request.postDataJSON() }) })
    const current = originalReaderPackage('nativenumeric', 2, true), old = originalReaderPackage('nativenumeric', 1), source = old.blocks[2], id = source.id, body = old.bodies[id]
    const imported = await importReaderPackage(page, current)
    await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(imported.dialog.getByText('操作角色：作者', { exact: true })).toBeVisible(); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: current.course, lesson: current.lessons[0], block: current.blocks[2], view: 'lesson' }))}`)
    const parentResponse = await page.request.get(`/api/v1/lessons/${current.lessons[0].id}?revision=2`); expect(parentResponse.status()).toBe(200); const parentBefore = await parentResponse.json()
    const block = page.locator(`#block-${id}-r2`), compare = block.getByRole('region', { name: '块修订比较', exact: true }), restore = block.getByRole('region', { name: '历史内容块恢复与审核', exact: true })
    await compare.getByRole('button', { name: '比较此块的两个修订', exact: true }).click()
    await compare.getByRole('combobox', { name: '左侧修订', exact: true }).selectOption(source.sha256)
    await compare.getByRole('combobox', { name: '右侧修订', exact: true }).selectOption(current.blocks[2].sha256)
    await compare.getByRole('button', { name: '读取所选两个修订', exact: true }).click()
    await compare.getByRole('button', { name: '选择左侧历史版本准备恢复', exact: true }).click()
    await restore.getByRole('button', { name: '重新读取当前基准并核验所选历史原件', exact: true }).click()
    await restore.getByRole('textbox', { name: '本次恢复理由', exact: true }).fill('原创合成算例恢复，仅验收数值协议；不代表数学或教学批准。')
    await restore.getByLabel('我已核对历史来源、当前基准与全部字段，明确创建独立待审恢复稿。', { exact: true }).check()
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/content/restore-drafts'))
    await restore.getByRole('button', { name: '明确创建本次历史恢复稿', exact: true }).click()
    const created = await creating; expect(created.status()).toBe(201); const ack = await created.json(), draftId = ack.candidate.draft_id
    await restore.getByRole('button', { name: `另行读取恢复稿 ${draftId}`, exact: true }).click()
    await restore.getByRole('button', { name: '打开恢复例题数值复算与安全任务', exact: true }).click()
    const numeric = restore.getByRole('region', { name: '恢复例题独立数值复算', exact: true })
    await numeric.getByRole('button', { name: '重新读取这份恢复例题的数值材料', exact: true }).click()
    const editor = numeric.getByRole('region', { name: '手工提供恢复例题数值材料', exact: true })
    expect(await editor.getByRole('textbox', { name: '本恢复候选的完整原正文', exact: true }).inputValue()).toBe(body)
    const symbol = editor.getByRole('group', { name: '符号 1', exact: true })
    for (const [name, value] of [['变量名', 'A'], ['LaTeX 记号', 'A'], ['取值域', '有限实数'], ['量纲说明', '无量纲']]) await symbol.getByRole('textbox', { name, exact: true }).fill(value)
    const assertion = editor.getByRole('group', { name: '断言 1', exact: true })
    for (const [name, value] of [['断言标识', 'assert_original_sum'], ['有限算术表达式', '1**2+2**2'], ['明确期望值', '5'], ['绝对容差', '0'], ['相对容差', '0'], ['单位标签', '1']]) await assertion.getByRole('textbox', { name, exact: true }).fill(value)
    const formula = '1^2+2^2', formulaStart = body.indexOf(formula), expectedStart = body.indexOf('| $5$ |') + 3
    expect(formulaStart).toBeGreaterThan(0); expect(body[expectedStart]).toBe('5')
    for (const [name, position, quote] of [['断言 1 的公式出处', formulaStart, formula], ['断言 1 的期望值出处', expectedStart, '5']] as const) {
      const fields = assertion.getByRole('group', { name, exact: true }), start = [...body.slice(0, position)].length
      await fields.getByRole('textbox', { name: '起点', exact: true }).fill(String(start)); await fields.getByRole('textbox', { name: '终点', exact: true }).fill(String(start + [...quote].length)); await fields.getByRole('textbox', { name: '原文片段', exact: true }).fill(quote)
    }
    await editor.getByRole('textbox', { name: '数值材料提供理由', exact: true }).fill('逐字对应原 A 行的有限算术；仅合成协议验收，不声称完整学术审核。')
    await editor.getByLabel('我已逐项提供并核对这份计划和原文定位，明确请求冻结预览；本次不批准执行。', { exact: true }).check()
    let dropped = false
    await page.route(`**/api/v1/content/restore-drafts/${draftId}/numeric-checks`, async route => {
      if (!dropped) { const response = await route.fetch(); expect(response.status()).toBe(201); dropped = true; await route.abort('failed') } else await route.continue()
    })
    await numeric.getByRole('button', { name: '明确提交手填材料并冻结数值预览', exact: true }).click()
    await expect(numeric.getByText('数值材料预览 · 数值结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
    expect(writes).toHaveLength(1)
    const first = writes[0]
    const previewing = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/restore-drafts/${draftId}/numeric-checks`))
    await numeric.getByRole('button', { name: `显式回放原数值命令 ${first.key}`, exact: true }).click()
    const previewResponse = await previewing; expect(previewResponse.status()).toBe(201); const preview: RestoreNumericCheckView = await previewResponse.json()
    await expect(numeric.getByText('数值材料预览 · 原数值 ACK 已保存', { exact: true })).toBeVisible(); expect(writes[1]).toEqual(first)
    expect(preview.job).toBeNull(); expect(preview.result).toBeNull(); expect(preview.decision).toBe('pending')
    const bound: ContentRestoreDraftSnapshot = await page.request.get(`/api/v1/content/restore-drafts/${draftId}`).then(response => response.json())
    expect(bound.numeric_check_ids).toEqual([preview.id]); expect(bound.numeric_material?.material.plan.assertions[0].expression).toBe('1**2+2**2')
    expect(bound.body_markdown).toBe(body); expect(bound.proposed_block.kind).toBe('worked_example')
    await numeric.getByRole('button', { name: `另行读取原预览对应的当前检查 ${preview.id}`, exact: true }).click()
    await expect(numeric.getByRole('region', { name: '实际冻结的恢复数值材料', exact: true })).toContainText(bound.numeric_material!.numeric_material_sha256)
    const execution = numeric.getByRole('region', { name: '独立数值执行批准', exact: true })
    await expect(execution.getByRole('button', { name: '明确批准本次数值执行', exact: true })).toBeDisabled()
    expect(writes.filter(value => value.path.endsWith('/decision'))).toHaveLength(0)
    for (const width of [1440, 390]) { await page.setViewportSize({ width, height: 900 }); await execution.scrollIntoViewIfNeeded(); expect(await numeric.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true); await page.screenshot({ path: info.outputPath(`restore-numeric-approval-${width}.png`) }) }
    await page.setViewportSize({ width: 1440, height: 900 })
    await execution.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
    const approving = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/restore-numeric-checks/${preview.id}/decision`))
    await execution.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click(); const approval = await approving; expect(approval.status()).toBe(202); const decision = await approval.json()
    await expect(numeric.getByText('独立数值决定 · 原数值 ACK 已保存', { exact: true })).toBeVisible()
    let actual!: RestoreNumericCheckView
    await expect.poll(async () => { const response = await page.request.get(`/api/v1/content/restore-numeric-checks/${preview.id}`); expect(response.status()).toBe(200); actual = await response.json(); return actual.result !== null }, { timeout: 30_000 }).toBe(true)
    expect(actual.job?.id).toBe(decision.job.id); expect(['PASS', 'BLOCKED']).toContain(actual.result!.verdict)
    if (actual.result!.verdict === 'BLOCKED') { expect(actual.result!.outcome).toBe('environment_unavailable'); expect(actual.result!.exit_code).not.toBe(0) }
    else { expect(actual.result!.outcome).toBe('passed'); expect(actual.result!.exit_code).toBe(0); expect(actual.result!.assertions.every(value => value.passed)).toBe(true) }
    await numeric.getByRole('button', { name: `另行读取恢复数值检查 ${preview.id}`, exact: true }).click()
    await expect(numeric.getByRole('region', { name: '实际数值结果', exact: true })).toContainText(actual.result!.verdict)
    expect(writes.filter(value => value.path.endsWith('/decision'))).toHaveLength(1)
    expect(await page.request.get(`/api/v1/objects/${id}/current`).then(response => response.json())).toEqual(current.blocks[2])
    // A new Review must observe the completed actual execution; synthetic human
    // intent cannot turn the host's BLOCKED numeric evidence into publishability.
    await restore.getByRole('button', { name: `另行读取恢复稿 ${draftId}`, exact: true }).click()
    await restore.getByRole('button', { name: '打开恢复审核与发布恢复', exact: true }).click()
    const review = restore.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await review.getByRole('textbox', { name: '本次审核备注', exact: true }).fill('真实执行之后的新审核；本合成决定不覆盖数值失败或替代学术验收。')
    await review.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
    const reviewing = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/drafts/${draftId}/review`))
    await review.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
    const reviewResponse = await reviewing; expect(reviewResponse.status()).toBe(202); const reviewJob = await reviewResponse.json()
    const readReview = review.getByRole('button', { name: '另行读取当前审核回执', exact: true })
    await expect(readReview).toBeEnabled(); await readReview.click()
    const human = review.getByRole('region', { name: '明确人工审核决定', exact: true })
    await human.getByLabel('数学审核决定').selectOption('APPROVED'); await human.getByLabel('来源审核决定').selectOption('APPROVED')
    await human.getByLabel('审核理由').fill('仅原创合成协议验收：明确记录新决定，以验证数值准入仍独立；不声称真实数学、来源或教学批准。')
    await human.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
    const deciding = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/reviews/${reviewJob.id}/decision`))
    await human.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click()
    expect((await deciding).status()).toBe(200); await expect(readReview).toBeEnabled(); await readReview.click()
    const publication = review.getByRole('region', { name: '恢复稿发布与恢复', exact: true })
    await publication.getByRole('button', { name: '选择此审核并重新读取恢复发布基准', exact: true }).click()
    const basis = publication.getByRole('region', { name: '本次恢复发布基准', exact: true })
    await expect(basis).toContainText(bound.candidate.candidate_sha256)
    for (const checkbox of await basis.getByRole('group', { name: '逐条确认此块警告' }).getByRole('checkbox').all()) await checkbox.check()
    await basis.getByLabel('我已核对准确恢复稿、历史原块、当前基准与所选人工审核，明确发布为当前基准下一修订。', { exact: true }).check()
    const publishing = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/drafts/${draftId}/publish`))
    await basis.getByRole('button', { name: '明确发布这一恢复稿', exact: true }).click()
    const publishResponse = await publishing, publishOutcome = { status: publishResponse.status(), body: await publishResponse.json() }
    writeFileSync(info.outputPath('actual-publication-response.json'), JSON.stringify({ actual, reviewJob, publishOutcome }, null, 2))
    if (actual.result!.verdict === 'BLOCKED') {
      expect(publishOutcome.status).toBe(409); expect(publishOutcome.body.error.code).toBe('PUBLISH_NUMERIC_REQUIRED')
      await expect(publication.getByText('服务端拒绝，原发布基准保留', { exact: true })).toBeVisible()
      expect(await page.request.get(`/api/v1/objects/${id}/current`).then(response => response.json())).toEqual(current.blocks[2])
      const unchanged = await page.request.get(`/api/v1/content/restore-drafts/${draftId}`).then(response => response.json())
      expect(unchanged.state).toBe('draft'); expect(unchanged.published_ref).toBeNull()
    } else {
      expect(publishOutcome.status).toBe(201); expect(publishOutcome.body.revision).toBe(3); expect(publishOutcome.body.id).toBe(id)
      expect(await page.request.get(`/api/v1/blocks/${id}/body?revision=3`).then(response => response.text())).toBe(body)
      expect(await page.request.get(`/api/v1/blocks/${id}?revision=3`).then(response => response.json())).toEqual(bound.proposed_block)
    }
    const parentAfter = await page.request.get(`/api/v1/lessons/${current.lessons[0].id}?revision=2`); expect(parentAfter.status()).toBe(200); expect(await parentAfter.json()).toEqual(parentBefore)
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('restore-numeric-actual.json'), JSON.stringify({ scope: 'Real browser/HTTP/SQLite/IDB/sealed runtime and fresh Review. Human decisions are synthetic software fixtures. Physical BLOCKED must reject publication; physical PASS can publish exact original body. No academic/source/pedagogy approval.', preview, bound, decision, actual, reviewJob, publishOutcome, writes, errors, originalParent: parentBefore, newModelCalls: 0 }, null, 2))
  } finally { await runtime.close() }
})
