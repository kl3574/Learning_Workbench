import { writeFile } from 'node:fs/promises'
import { expect, test, type Route } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { bootstrap } from './helpers'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
import type { AttemptSnapshot } from '../../packages/contracts/generated/api-types'

test('import admission waits for real Policy after UI saved and never replays a rejected click', async ({ page }, info) => {
  await bootstrap(page)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let requests = 0, held = 0, released = false
  const deliveries: Promise<void>[] = []
  const facts: Record<string, boolean | number> = {}
  const handler = (route: Route) => {
    const delivery = (async () => {
      if (route.request().method() !== 'GET' || ++requests === 1 || released) { await route.continue(); return }
      const response = await route.fetch()
      expect(response.status()).toBe(200)
      held++
      await gate
      await route.fulfill({ response })
    })()
    deliveries.push(delivery)
    return delivery
  }
  await page.route('**/api/v1/session', handler)
  try {
    await page.reload()
    await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
    const checking = page.getByText('正在核验服务端测试策略；尚未向模型提供任何内容。', { exact: true })
    await expect(checking).toBeVisible()
    await expect.poll(() => held).toBeGreaterThan(0)
    const trigger = page.locator('.import-trigger')
    const dialog = page.getByRole('dialog', { name: '导入', exact: true })
    facts.uiSavedWhilePolicyUnknown = true
    facts.entryEnabledWhilePolicyUnknown = await trigger.isEnabled()
    // Observe the original fault before asserting the admission contract. A fixed
    // disabled entry is not force-clicked; a real enabled entry uses a real click.
    if (facts.entryEnabledWhilePolicyUnknown) {
      await trigger.click()
      await expect(page.getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。', { exact: true })).toBeVisible()
      facts.realClickRejectedByGuard = true
    }
    await expect(dialog).toHaveCount(0)
    released = true; release()
    await expect(checking).toHaveCount(0)
    await expect(trigger).toBeEnabled()
    await expect(dialog).toHaveCount(0)
    facts.noAutomaticReplayAfterPolicyRecovery = true
    await trigger.click()
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(/操作角色：(作者|学习者)$/)).toBeVisible()
    facts.explicitClickAfterPolicyRecoveryOpens = true
    expect(facts.entryEnabledWhilePolicyUnknown).toBe(false)
  } finally {
    released = true; release()
    await Promise.all(deliveries)
    await page.unroute('**/api/v1/session', handler)
    facts.actualPolicyResponsesHeld = held
    await writeFile(info.outputPath('actual-import-admission.json'), JSON.stringify(facts, null, 2) + '\n')
  }
})

test('real independent Policy preserves an open import selection and restores only explicit admission', async ({ playwright }, info) => {
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page)
    await expect(page.locator('.import-trigger')).toBeEnabled()
    // This original synthetic package remains unreviewed; importing it does not
    // establish expert approval, and this test neither submits nor grades answers.
    const fixture = originalAssessmentPackage('nativeimportadmission')
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const second = await page.context().newPage()
    const facts: Record<string, boolean | number | string> = {}
    try {
      await second.goto(`/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
      await expect(second.locator('.real-reader > h1')).toBeVisible()
      await second.getByRole('navigation', { name: '学习主导航', exact: true }).getByRole('button', { name: '测试题', exact: true }).click()
      const entry = second.locator('.assessment-directory details').first()
      await entry.locator('summary').click()
      await entry.getByRole('button', { name: /^查看测试范围：/ }).click()
      await expect(second.getByRole('heading', { name: '范围与内容状态', exact: true })).toBeVisible()
      await second.getByRole('radio', { name: '独立测试', exact: true }).check()
      await second.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()

      await page.locator('.import-trigger').click()
      const dialog = page.getByRole('dialog', { name: '导入', exact: true })
      await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
      await dialog.getByLabel('解析格式').selectOption('text')
      await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'synthetic-retained-choice.txt', mimeType: 'text/plain', buffer: Buffer.from('原创合成导入选择，尚未上传。') })
      await expect(dialog.getByText(/^已选择：synthetic-retained-choice.txt/)).toBeVisible()
      const creating = second.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
      await second.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
      const created = await creating
      expect(created.status()).toBe(201)
      const attempt: AttemptSnapshot = await created.json()
      expect(attempt.policy.mode).toBe('independent')
      expect(attempt.grading_status).toBe('not_graded')
      await expect(second.getByText('服务端作答已保存', { exact: true })).toBeVisible()
      await page.evaluate(() => window.dispatchEvent(new Event('focus')))
      await expect(page.getByRole('heading', { name: '独立测试进行中', exact: true })).toBeVisible()
      await expect(page.locator('.import-trigger')).toBeDisabled()
      await expect(dialog).toBeVisible()
      await expect(dialog.getByText('当前导入记录、已选择的本机文件与未提交设置仍保留。权限恢复后会重新读取服务端内容。', { exact: true })).toBeVisible()
      await expect(dialog.getByLabel('选择导入文件')).toHaveCount(0)
      await expect(dialog.getByText(/^已选择：synthetic-retained-choice.txt/)).toHaveCount(0)
      facts.independentEntryDisabled = true
      facts.existingDialogRetainedWithMaterialsHidden = true

      await second.getByRole('button', { name: '放弃本次测试', exact: true }).click()
      const abandoning = second.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/attempts/${attempt.id}/abandon`))
      await second.getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click()
      expect((await abandoning).status()).toBe(200)
      await page.evaluate(() => window.dispatchEvent(new Event('focus')))
      await expect(page.locator('.import-trigger')).toBeEnabled()
      await expect(dialog.getByText(/^已选择：synthetic-retained-choice.txt/)).toBeVisible()
      await expect(dialog.getByLabel('解析格式')).toHaveValue('text')
      await expect(dialog.getByRole('button', { name: '上传并生成预览', exact: true })).toBeEnabled()
      facts.selectedFileAndFormatRecovered = true
      const ended = await page.request.get(`/api/v1/attempts/${attempt.id}`)
      expect(ended.status()).toBe(200)
      const snapshot: AttemptSnapshot = await ended.json()
      expect(snapshot.status).toBe('abandoned')
      expect(snapshot.grading_status).toBe('not_graded')
      facts.actualAttemptStatus = snapshot.status
      await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
      await expect(dialog).toHaveCount(0)
      await page.locator('.import-trigger').click()
      await expect(dialog).toBeVisible()
      facts.explicitAdmissionAfterAbandon = true
    } finally {
      await second.close()
      await writeFile(info.outputPath('actual-independent-import-policy.json'), JSON.stringify(facts, null, 2) + '\n')
    }
  } finally { await runtime.close() }
})
