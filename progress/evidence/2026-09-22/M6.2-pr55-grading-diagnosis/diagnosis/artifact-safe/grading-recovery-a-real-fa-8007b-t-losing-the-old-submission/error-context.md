# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: grading-recovery.spec.ts >> a real failed regrade survives reload and can recover from the last actual grade without losing the old submission
- Location: ../../tests/e2e/grading-recovery.spec.ts:57:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: 200
Received: 409
```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { writeFileSync } from 'node:fs'
  3   | import { resolve } from 'node:path'
  4   | import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  5   | import type { AssessmentGradingResult, AttemptSnapshot } from '../../packages/contracts/generated/api-types'
  6   | import { originalAssessmentPackage, importAssessmentPackage } from './assessmentTestData'
  7   | import { RestartRuntime } from './restartRuntime'
  8   | 
  9   | const root = resolve(import.meta.dirname, '../..')
  10  | 
  11  | /** Deliberate storage fault in this test's private synthetic DB, never an HTTP capability. */
  12  | function frozenAnswerFault(runtime: RestartRuntime, question: string, action: 'remove' | 'restore') {
  13  |   const script = [
  14  |     'import hashlib,json,os,sqlite3,sys',
  15  |     'from pathlib import Path',
  16  |     'directory=Path(sys.argv[1]); question=sys.argv[2]; action=sys.argv[3]',
  17  |     'saved=directory/"synthetic-private-answer-fault.json"',
  18  |     'd=sqlite3.connect(directory/"workspace.sqlite3"); d.row_factory=sqlite3.Row',
  19  |     'if action=="remove":',
  20  |     ' rows=[dict(r) for r in d.execute("SELECT * FROM solutions WHERE question_id=? ORDER BY solution_revision",(question,))]',
  21  |     ' assert len(rows)==1 and rows[0]["review_status"]=="needs_review"',
  22  |     ' payload=json.dumps(rows[0],ensure_ascii=False).encode()',
  23  |     ' fd=os.open(saved,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)',
  24  |     ' with os.fdopen(fd,"wb") as out: out.write(payload)',
  25  |     ' d.execute("DELETE FROM solutions WHERE question_id=?",(question,)); d.commit()',
  26  |     'else:',
  27  |     ' row=json.loads(saved.read_bytes()); assert row["question_id"]==question',
  28  |     ' d.execute("INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) VALUES(?,?,?,?,?,?)",tuple(row[k] for k in ("question_id","question_revision","solution_revision","private_json","sha256","review_status"))); d.commit()',
  29  |     ' assert dict(d.execute("SELECT * FROM solutions WHERE question_id=?",(question,)).fetchone())==row',
  30  |     'print(json.dumps({"action":action,"saved_original_sha256":hashlib.sha256(saved.read_bytes()).hexdigest()}))',
  31  |   ].join('\n')
  32  |   return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', script, runtime.data, question, action],
  33  |     { cwd: root, encoding: 'utf8' })) as { action: string; saved_original_sha256: string }
  34  | }
  35  | 
  36  | async function result(page: Page, id: string, revision: number) {
  37  |   let value: AssessmentGradingResult | undefined
  38  |   await expect.poll(async () => {
  39  |     const response = await page.request.get(`/api/v1/attempts/${id}/result`)
  40  |     if (response.status() === 202) return 0
> 41  |     expect(response.status()).toBe(200)
      |                               ^ Error: expect(received).toBe(expected) // Object.is equality
  42  |     value = await response.json()
  43  |     return value!.grading_revision
  44  |   }).toBe(revision)
  45  |   return value!
  46  | }
  47  | 
  48  | async function review(page: Page, reason: string) {
  49  |   await page.getByLabel('人工复核理由', { exact: true }).fill(reason)
  50  |   await page.getByRole('checkbox', { name: '复核第 2 题', exact: true }).check()
  51  |   await page.getByLabel('第 2 题人工分数', { exact: true }).fill('1')
  52  |   await page.getByLabel('第 2 题复核依据', { exact: true }).fill('合成软件验收复核依据；不是内容审核或学习效果声明。')
  53  |   await page.getByRole('button', { name: '提交人工复核', exact: true }).click()
  54  |   await page.getByRole('button', { name: '确认提交人工分数与依据', exact: true }).click()
  55  | }
  56  | 
  57  | test('a real failed regrade survives reload and can recover from the last actual grade without losing the old submission', async ({ playwright }, info) => {
  58  |   test.setTimeout(120_000)
  59  |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('gradingrecover')
  60  |   const errors: string[] = [], reviewCommands: string[] = []
  61  |   try {
  62  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  63  |     page.on('pageerror', error => errors.push(error.message))
  64  |     page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/regrade')) reviewCommands.push(request.headers()['idempotency-key']) })
  65  |     await runtime.authenticateOnly(page)
  66  |     const imported = await importAssessmentPackage(page, fixture)
  67  |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  68  |     await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  69  |     await page.getByRole('radio', { name: '独立测试', exact: true }).check()
  70  |     await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  71  |     const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  72  |     await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  73  |     const created = await creating
  74  |     expect(created.status()).toBe(201)
  75  |     const attempt: AttemptSnapshot = await created.json()
  76  |     await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  77  |     await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
  78  |     await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
  79  |     const original = await result(page, attempt.id, 1)
  80  |     expect(original.items.every(item => item.score === null)).toBe(true)
  81  |     const originalResponses = await (await page.request.get(`/api/v1/attempts/${attempt.id}/responses`)).json()
  82  |     await page.getByRole('button', { name: '切换为作者角色以人工复核', exact: true }).click()
  83  |     await page.getByRole('button', { name: '填写人工复核', exact: true }).click()
  84  |     const removed = frozenAnswerFault(runtime, fixture.questions[0].id, 'remove')
  85  |     const submitting = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/attempts/${attempt.id}/regrade`))
  86  |     await review(page, '首次合成复核：故障将由实际评分Worker检测。')
  87  |     const submitted = await submitting
  88  |     expect(submitted.status()).toBe(202)
  89  |     const failedJob = await submitted.json()
  90  |     await expect(page.getByRole('region', { name: '人工复核', exact: true })).toContainText('人工复核命令已被接收')
  91  |     await expect(page.getByText('本机复核草稿存储可用', { exact: true })).toBeVisible()
  92  |     await expect.poll(async () => (await (await page.request.get(`/api/v1/jobs/${failedJob.id}`)).json()).status).toBe('failed')
  93  |     const restored = frozenAnswerFault(runtime, fixture.questions[0].id, 'restore')
  94  |     expect(restored.saved_original_sha256).toBe(removed.saved_original_sha256)
  95  |     await page.reload()
  96  |     await expect(page.getByRole('heading', { name: '评分任务失败', exact: true })).toBeVisible()
  97  |     expect(reviewCommands).toHaveLength(1)
  98  |     const pending = await page.request.get(`/api/v1/attempts/${attempt.id}/result`)
  99  |     expect(pending.status()).toBe(202)
  100 |     const pendingBody = await pending.json()
  101 |     expect(pendingBody.id).toBe(failedJob.id)
  102 |     expect(pendingBody.status).toBe('failed')
  103 |     expect(pendingBody.last_completed_result).toEqual(original)
  104 |     // An acknowledged command is a receipt, not an unsubmitted recovery candidate.
  105 |     // Reload does not replay it; start a new explicit command from the actual old grade.
  106 |     await expect(page.getByRole('button', { name: '填写人工复核', exact: true })).toBeEnabled()
  107 |     await page.getByRole('button', { name: '填写人工复核', exact: true }).click()
  108 |     await expect(page.getByLabel('人工复核理由', { exact: true })).toBeVisible()
  109 |     expect(reviewCommands).toHaveLength(1)
  110 |     const recovering = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/attempts/${attempt.id}/regrade`))
  111 |     await review(page, '原固定答案已原样恢复；依据真实旧评分版本1明确提交新的复核命令。')
  112 |     const accepted = await recovering
  113 |     expect(accepted.status()).toBe(202)
  114 |     expect((await accepted.json()).id).not.toBe(failedJob.id)
  115 |     const final = await result(page, attempt.id, 2)
  116 |     expect(final.status).toBe('needs_review')
  117 |     expect(final.items.map(item => item.score)).toEqual([null, 1, null, null, null])
  118 |     expect(final.manual_reviews).toHaveLength(1)
  119 |     expect(reviewCommands).toHaveLength(2)
  120 |     expect(new Set(reviewCommands).size).toBe(2)
  121 |     expect((await (await page.request.get(`/api/v1/attempts/${attempt.id}/responses`)).json()).responses).toEqual(originalResponses.responses)
  122 |     expect((await (await page.request.get(`/api/v1/jobs/${failedJob.id}`)).json()).status).toBe('failed')
  123 |     expect(errors).toEqual([])
  124 |     writeFileSync(info.outputPath('actual-failed-regrade-recovery.json'), JSON.stringify({
  125 |       scope: 'Owned original-synthetic DB fault, actual UI/HTTP worker failure, original fixed answer restored byte-for-byte, browser reload and explicit UI recovery. No test-only public endpoint.',
  126 |       initial_grading_revision: 1, failed_job_retained: true, frozen_answer_restored: true,
  127 |       original_answer_row_sha256: restored.saved_original_sha256, recovered_grading_revision: final.grading_revision,
  128 |       distinct_explicit_commands: new Set(reviewCommands).size, original_responses_preserved: true,
  129 |       actual_human_math_approval: 'NOT_RUN', runtime_errors: errors,
  130 |     }, null, 2))
  131 |   } finally { await runtime.close() }
  132 | })
  133 | 
```