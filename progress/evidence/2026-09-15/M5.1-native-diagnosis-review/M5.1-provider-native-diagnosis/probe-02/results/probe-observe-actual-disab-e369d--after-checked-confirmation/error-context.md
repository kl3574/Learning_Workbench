# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: probe.spec.ts >> observe actual disabled assessment start after checked confirmation
- Location: ../../../.cache/learning-workbench-acceptance/m51-provider-native-diagnosis/probe-02/probe.spec.ts:5:1

# Error details

```
Error: expect(locator).toBeEnabled() failed

Locator:  getByRole('button', { name: '明确开始本次测试', exact: true })
Expected: enabled
Received: disabled
Timeout:  2000ms

Call log:
  - Expect "toBeEnabled" getByRole('button', { name: '明确开始本次测试', exact: true }) with timeout 2000ms
  - waiting for getByRole('button', { name: '明确开始本次测试', exact: true })
    21 × locator resolved to <button disabled class="primary-button">明确开始本次测试</button>
       - unexpected value "disabled"

```

```yaml
- button "明确开始本次测试" [disabled]
```

# Test source

```ts
  1  | import { test, expect } from '<REPO>/apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { RestartRuntime } from '<REPO>/tests/e2e/restartRuntime'
  3  | import { originalAssessmentPackage, importAssessmentPackage } from '<REPO>/tests/e2e/assessmentTestData'
  4  | import { writeFileSync } from 'node:fs'
  5  | test('observe actual disabled assessment start after checked confirmation', async ({playwright},info)=>{
  6  |  const runtime=await RestartRuntime.start(), observations: unknown[]=[], pending:Promise<void>[]=[]
  7  |  try {
  8  |  const context=await runtime.openBrowser(playwright.chromium),page=context.pages()[0]; await runtime.authenticateOnly(page)
  9  |  const fixture=originalAssessmentPackage('providerpolicynative','learner'),imported=await importAssessmentPackage(page,fixture);await imported.dialog.getByRole('button',{name:'关闭导入',exact:true}).click()
  10 |  page.on('response',response=>{if(response.request().method()==='GET' && response.url().includes('/api/v1/assessments')) pending.push(response.json().then(body=>{observations.push({url:new URL(response.url()).pathname+new URL(response.url()).search,status:response.status(),body})}).catch(()=>{}))})
  11 |  await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({assessment_ref:fixture.assessment,course_ref:fixture.course}))}`)
  12 |  const check=page.getByRole('checkbox',{name:'我已核对内容状态与模式，确认开始未评分测试',exact:true}),button=page.getByRole('button',{name:'明确开始本次测试',exact:true})
  13 |  await check.check(); await expect(check).toBeChecked()
> 14 |  try { await expect(button).toBeEnabled({timeout:2000}) }
     |                             ^ Error: expect(locator).toBeEnabled() failed
  15 |  finally { await Promise.all(pending);writeFileSync(info.outputPath('actual-observation.json'),JSON.stringify({scope:'Observational private probe; original learner import and actual UI; no interception, source edits, direct attempt creation or response replacement.',checkbox_checked:await check.isChecked(),button_disabled:await button.isDisabled(),page_text:await page.locator('body').innerText(),observations},null,2)) }
  16 |  } finally {await runtime.close()}
  17 | })
  18 | 
```