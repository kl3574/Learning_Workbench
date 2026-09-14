import { expect, test } from '/tmp/m33-import-recovery-review-3cf2c34/apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from '/tmp/m33-import-recovery-review-3cf2c34/tests/e2e/restartRuntime'
import { writeFileSync } from 'node:fs'

test('controlled cold policy read: recovery IDs survive but early Import click does not open a dialog', async ({ playwright }) => {
 const runtime = await RestartRuntime.start()
 const ledger: object[] = []
 let release = () => {}
 try {
  const context = await runtime.openBrowser(playwright.chromium)
  const page = context.pages()[0]
  await runtime.authenticateOnly(page)
  await expect(page.getByRole('heading',{name:'正在核验测试访问策略',exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'导入',exact:true}).click()
  let dialog = page.getByRole('dialog',{name:'导入',exact:true})
  await dialog.getByLabel('解析格式').selectOption('text')
  await dialog.getByLabel('选择导入文件').setInputFiles({name:'original-gb18030.txt',mimeType:'text/plain',buffer:Buffer.from([0xc4,0xe3,0xba,0xc3])})
  const uploaded = page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/v1/imports'))
  await dialog.getByRole('button',{name:'上传并生成预览'}).click()
  const receipt = await (await uploaded).json()
  await expect(dialog.getByRole('heading',{name:'选择原件编码并在本机预览',exact:true})).toBeVisible()
  const storedBefore = await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('learning-workbench.import-id.v1:')).length)
  let held = 0
  const gate = new Promise<void>(resolve=>{release=resolve})
  await page.route('**/api/v1/session', async route=>{ if(route.request().method()!=='GET')return route.continue(); const response=await route.fetch();held++;await gate;await route.fulfill({response}) })
  await page.reload()
  await expect.poll(()=>held).toBeGreaterThan(0)
  await page.getByRole('button',{name:'导入',exact:true}).click()
  ledger.push({point:'while_real_session_responses_held',heldResponses:held,dialogs:await page.getByRole('dialog',{name:'导入',exact:true}).count(),policyUnknown:await page.getByRole('heading',{name:'正在核验测试访问策略',exact:true}).count(),storedRecoveryIds:await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('learning-workbench.import-id.v1:')).length),denial:await page.getByText('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。',{exact:true}).count()})
  expect(storedBefore).toBe(1)
  await expect(page.getByRole('dialog',{name:'导入',exact:true})).toHaveCount(0)
  release()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await expect(page.getByRole('heading',{name:'正在核验测试访问策略',exact:true})).toHaveCount(0)
  ledger.push({point:'after_actual_policy_read_completed',dialogs:await page.getByRole('dialog',{name:'导入',exact:true}).count(),storedRecoveryIds:await page.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('learning-workbench.import-id.v1:')).length)})
  await expect(page.getByRole('dialog',{name:'导入',exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'导入',exact:true}).click()
  dialog=page.getByRole('dialog',{name:'导入',exact:true})
  await dialog.getByRole('button',{name:`恢复 ${receipt.import_id}`,exact:true}).click()
  await expect(dialog.getByRole('heading',{name:'选择原件编码并在本机预览',exact:true})).toBeVisible()
  ledger.push({point:'explicit_second_click',sameServerImportRecovered:true,dialogs:await dialog.count()})
 } finally {release();await runtime.close();writeFileSync('/tmp/m33-import-recovery-probe/observations.json',JSON.stringify(ledger,null,2)+'\n')}
})
