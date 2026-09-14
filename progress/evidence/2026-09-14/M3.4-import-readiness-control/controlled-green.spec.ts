import { writeFileSync } from 'node:fs'
const observations: object[] = []
import { expect, test as base } from '/tmp/m33-import-recovery-review-3cf2c34/apps/web/node_modules/@playwright/test/index.mjs'
import type { AttemptSnapshot } from '/tmp/m33-import-recovery-review-3cf2c34/packages/contracts/generated/api-types'
import { originalAssessmentPackage, importAssessmentPackage } from '/tmp/m33-import-recovery-review-3cf2c34/tests/e2e/assessmentTestData'
import { RestartRuntime } from '/tmp/m33-import-recovery-review-3cf2c34/tests/e2e/restartRuntime'

const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
})

test('an open author import retains its task across independent start and submit but rechecks pending-answer protection before restoring content', async ({ page }) => {
  const assessment = originalAssessmentPackage('importpolicyassessment')
  const imported = await importAssessmentPackage(page, assessment)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.getByRole('button', { name: '导入', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  const material = originalAssessmentPackage('importpolicyprivate')
  await dialog.getByLabel('解析格式').selectOption('learnpack')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'original-private-synthetic.learnpack.zip', mimeType: 'application/zip', buffer: material.bytes })
  const staging = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/imports'))
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  const staged = await staging; expect(staged.status()).toBe(202)
  const receipt: { import_id: string } = await staged.json()
  await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('当前候选正文', { exact: true })).toBeVisible()
  await expect(dialog.getByRole('button', { name: '下载受控原件', exact: true })).toBeVisible()

  const testPage = await page.context().newPage()
  await testPage.goto(`${new URL(page.url()).origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: assessment.assessment, course_ref: assessment.course }))}`)
  await expect(testPage.getByRole('heading', { name: '范围与内容状态', exact: true })).toBeVisible()
  await testPage.getByRole('radio', { name: '独立测试', exact: true }).check()
  await testPage.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const creating = testPage.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${assessment.assessment.id}/attempts`))
  await testPage.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const created = await creating; expect(created.status()).toBe(201)
  const attempt: AttemptSnapshot = await created.json()
  await expect(testPage.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  await expect(dialog.getByText('当前导入记录、已选择的本机文件与未提交设置仍保留。权限恢复后会重新读取服务端内容。', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('当前候选正文', { exact: true })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '下载受控原件', exact: true })).toHaveCount(0)
  await expect(dialog.getByLabel('选择预览候选')).toHaveCount(0)

  await testPage.getByRole('button', { name: '提交本次测试', exact: true }).click()
  const submitting = testPage.waitForResponse(response => response.url().endsWith(`/attempts/${attempt.id}/submit`))
  await testPage.getByRole('dialog', { name: '确认提交测试', exact: true }).getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
  expect((await submitting).status()).toBe(202)
  await expect(dialog.getByRole('alert')).toContainText('仍受策略保护')
  // Its original task is still active in this dialog, but its old private
  // projection cannot reappear after the ordinary material lock has ended.
  await expect(dialog.locator('.import-details')).toContainText(receipt.import_id)
  await expect(dialog.getByLabel('选择导入文件')).toHaveCount(0)
  await expect(dialog.getByLabel('当前候选正文', { exact: true })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '下载受控原件', exact: true })).toHaveCount(0)
  expect((await page.request.get(`/api/v1/imports/${receipt.import_id}`)).status()).toBe(409)
  expect((await testPage.request.get(`/api/v1/attempts/${attempt.id}`)).status()).toBe(200)
  await testPage.close()
})

test.afterEach(() => { writeFileSync('/tmp/m33-import-recovery-probe/controlled-green-ledger.json', JSON.stringify(observations,null,2)+'\n') })

test('a reselected failed original survives a role-policy pause in memory while decoded text must be checked again', async ({ page }) => {
  const bytes = Buffer.from([0xc4, 0xe3, 0xba, 0xc3])
  await page.getByRole('button', { name: '导入', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await dialog.getByLabel('解析格式').selectOption('text')
  await dialog.getByLabel('选择导入文件').setInputFiles({ name: 'original-gb18030.txt', mimeType: 'text/plain', buffer: bytes })
  const staging = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/imports'))
  await dialog.getByRole('button', { name: '上传并生成预览' }).click()
  const staged = await staging; expect(staged.status()).toBe(202)
  const receipt: { import_id: string } = await staged.json()
  await expect(dialog.getByRole('heading', { name: '选择原件编码并在本机预览', exact: true })).toBeVisible()
  // Probe transport gate: preserve actual response bytes, delay only the first two cold session reads.
  let gated = 0
  const started = Date.now()
  await page.exposeFunction('recordImportClick', (value: object) => observations.push({ event: 'click', elapsedMs: Date.now()-started, ...value }))
  await page.addInitScript(() => {
    document.addEventListener('click', event => {
      const button = (event.target as Element | null)?.closest('button')
      if (button?.textContent?.trim() !== '导入') return
      setTimeout(() => {
        const report = (window as unknown as { recordImportClick: (value: object) => void }).recordImportClick
        report({ dialogCount: document.querySelectorAll('dialog[open]').length, policyUnknown: [...document.querySelectorAll('h1')].some(node => node.textContent === '正在核验测试访问策略'), recoveryIds: Object.keys(localStorage).filter(key=>key.startsWith('learning-workbench.import-id.v1:')).length })
      }, 0)
    })
  })
  await page.route('**/api/v1/session', async route => {
    if (route.request().method() !== 'GET' || gated >= 2) return route.continue()
    const ordinal = ++gated
    const response = await route.fetch()
    observations.push({event:'held_actual_session',ordinal,status:response.status(),elapsedMs:Date.now()-started})
    await new Promise(resolve=>setTimeout(resolve,1000))
    await route.fulfill({response})
    observations.push({event:'released_actual_session',ordinal,elapsedMs:Date.now()-started})
  })
  await page.reload()
  await expect(page.getByRole('heading', { name: '当前教材目录', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '导入', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '导入', exact: true })
  await dialog.getByRole('button', { name: `恢复 ${receipt.import_id}`, exact: true }).click()
  await expect(dialog.getByRole('button', { name: '严格解码并预览', exact: true })).toBeDisabled()
  await dialog.getByLabel('重新选择原始文件').setInputFiles({ name: 'reselected-original.txt', mimeType: 'text/plain', buffer: bytes })
  await dialog.getByLabel('原件文本编码').selectOption('gb18030')
  await dialog.getByRole('button', { name: '严格解码并预览', exact: true }).click()
  await expect(dialog.getByLabel('本机解码文本预览')).toHaveText('你好')
  await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  await expect(dialog.getByText('本机原始文件：reselected-original.txt', { exact: true })).toBeVisible()
  await expect(dialog.getByLabel('本机解码文本预览')).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '严格解码并预览', exact: true })).toBeEnabled()
  await dialog.getByLabel('原件文本编码').selectOption('gb18030')
  await dialog.getByRole('button', { name: '严格解码并预览', exact: true }).click()
  await expect(dialog.getByLabel('本机解码文本预览')).toHaveText('你好')
})
