# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: retrieval.spec.ts >> real explicit cold scope, original rebuild Job, complete hits/no match/resource omission and unchanged historical scope
- Location: tests/e2e/retrieval.spec.ts:47:1

# Error details

```
Error: Command failed: <private-home>/Desktop/learning/Learning_Workbench/.venv/bin/python -B -c import sys,json,hashlib
from pathlib import Path
from packages.contracts import domain_models as dm
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.application.content import ContentService
from services.api.app.infrastructure.content_repository import reference
input=json.load(sys.stdin)
db=Database(Settings(data_dir=Path(input['data'])))
ws=db.initialize()
def block(id,text,rev=1):
 body=text.encode('utf-8')
 value=dm.ContentBlock(id=id,revision=rev,kind='text',title='合成未审 '+id,body_path='content/'+id+'.md',body_sha256=hashlib.sha256(body).hexdigest())
 return value,body
normal,normalbody=block('retrieval_native_original','原始 SVD 概率教材；保持完整数学条件。\n')
large,largebody=block('retrieval_native_large','budget '*350000)
empty,emptybody=block('retrieval_native_empty','... ，；。\n')
lesson=dm.Lesson(id='retrieval_native_lesson',revision=1,title='检索合成小节',objectives=[],block_refs=[reference(normal)])
extra=dm.Lesson(id='retrieval_native_extra',revision=1,title='资源与空词合成小节',objectives=[],block_refs=[reference(large),reference(empty)])
course=dm.Course(id='retrieval_native_course',revision=1,title='检索未审合成教材',audience='原生工程测试，非专家审核',lesson_refs=[reference(lesson),reference(extra)])
if input['advance']:
 newer,body=block(normal.id,'新的修订；旧范围不得偷偷换成此正文。\n',2)
 ContentService(db).publish(ws,[newer],{newer.body_path:body})
else:
 ContentService(db).publish(ws,[normal,large,empty,lesson,extra,course],{normal.body_path:normalbody,large.body_path:largebody,empty.body_path:emptybody})
print(json.dumps({'course':reference(course).model_dump(mode='json'),'lesson':reference(lesson).model_dump(mode='json'),'block':reference(normal).model_dump(mode='json')}))
Traceback (most recent call last):
  File "<string>", line 25, in <module>
  File "<private-home>/Desktop/learning/Learning_Workbench/services/api/app/application/content.py", line 360, in publish
    return self.publish_in_transaction(repository.connection, workspace_id, objects, bodies)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<private-home>/Desktop/learning/Learning_Workbench/services/api/app/application/content.py", line 388, in publish_in_transaction
    staged = self._stage(repository, values, bodies, budgets)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<private-home>/Desktop/learning/Learning_Workbench/services/api/app/application/content.py", line 225, in _stage
    self._body_bytes(value, body, budgets)
  File "<private-home>/Desktop/learning/Learning_Workbench/services/api/app/application/content.py", line 200, in _body_bytes
    raise invalid()
services.api.app.application.errors.ApiError: (422, 'SCHEMA_INVALID', '内容结构、引用或查询参数无效。')

```

# Test source

```ts
  1  | import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { execFileSync } from 'node:child_process'
  3  | import { writeFileSync } from 'node:fs'
  4  | import { resolve } from 'node:path'
  5  | import { RestartRuntime } from './restartRuntime'
  6  | import type { ContentRef, RetrievalQueryView } from '../../packages/contracts/generated/api-types'
  7  | const root = resolve(import.meta.dirname, '../..')
  8  | 
  9  | /** Controlled synthetic publication/next-revision injection, not an author workflow or expert review. */
  10 | function material(runtime: RestartRuntime, advance = false): { course: ContentRef; lesson: ContentRef; block: ContentRef } {
  11 |   const script = `import sys,json,hashlib
  12 | from pathlib import Path
  13 | from packages.contracts import domain_models as dm
  14 | from services.api.app.infrastructure.config import Settings
  15 | from services.api.app.infrastructure.database import Database
  16 | from services.api.app.application.content import ContentService
  17 | from services.api.app.infrastructure.content_repository import reference
  18 | input=json.load(sys.stdin)
  19 | db=Database(Settings(data_dir=Path(input['data'])))
  20 | ws=db.initialize()
  21 | def block(id,text,rev=1):
  22 |  body=text.encode('utf-8')
  23 |  value=dm.ContentBlock(id=id,revision=rev,kind='text',title='合成未审 '+id,body_path='content/'+id+'.md',body_sha256=hashlib.sha256(body).hexdigest())
  24 |  return value,body
  25 | normal,normalbody=block('retrieval_native_original','原始 SVD 概率教材；保持完整数学条件。\\n')
  26 | large,largebody=block('retrieval_native_large','budget '*350000)
  27 | empty,emptybody=block('retrieval_native_empty','... ，；。\\n')
  28 | lesson=dm.Lesson(id='retrieval_native_lesson',revision=1,title='检索合成小节',objectives=[],block_refs=[reference(normal)])
  29 | extra=dm.Lesson(id='retrieval_native_extra',revision=1,title='资源与空词合成小节',objectives=[],block_refs=[reference(large),reference(empty)])
  30 | course=dm.Course(id='retrieval_native_course',revision=1,title='检索未审合成教材',audience='原生工程测试，非专家审核',lesson_refs=[reference(lesson),reference(extra)])
  31 | if input['advance']:
  32 |  newer,body=block(normal.id,'新的修订；旧范围不得偷偷换成此正文。\\n',2)
  33 |  ContentService(db).publish(ws,[newer],{newer.body_path:body})
  34 | else:
  35 |  ContentService(db).publish(ws,[normal,large,empty,lesson,extra,course],{normal.body_path:normalbody,large.body_path:largebody,empty.body_path:emptybody})
  36 | print(json.dumps({'course':reference(course).model_dump(mode='json'),'lesson':reference(lesson).model_dump(mode='json'),'block':reference(normal).model_dump(mode='json')}))`
> 37 |   return JSON.parse(execFileSync(resolve(root, '.venv/bin/python'), ['-B', '-c', script], {
     |                     ^ Error: Command failed: <private-home>/Desktop/learning/Learning_Workbench/.venv/bin/python -B -c import sys,json,hashlib
  38 |     cwd: root, input: JSON.stringify({ data: runtime.data, advance }), encoding: 'utf8', maxBuffer: 1024 * 1024,
  39 |   }))
  40 | }
  41 | async function openRetrieval(page: Page) {
  42 |   await page.getByRole('button', { name: /搜索与命令/ }).click()
  43 |   await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: '检索材料', exact: false }).click()
  44 |   return page.getByRole('dialog', { name: '检索材料', exact: true })
  45 | }
  46 | 
  47 | test('real explicit cold scope, original rebuild Job, complete hits/no match/resource omission and unchanged historical scope', async ({ playwright }, info) => {
  48 |   test.setTimeout(120_000)
  49 |   const runtime = await RestartRuntime.start(), refs = material(runtime), errors: string[] = [], responses: RetrievalQueryView[] = []
  50 |   try {
  51 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  52 |     page.on('pageerror', error => errors.push(error.message))
  53 |     await runtime.authenticateOnly(page)
  54 |     await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: refs.course, lesson: refs.lesson, block: refs.block }))}`)
  55 |     await expect(page.getByRole('heading', { name: '合成未审 retrieval_native_original', exact: true })).toBeVisible()
  56 |     const dialog = await openRetrieval(page)
  57 |     await expect(dialog.getByRole('radio', { name: /只查当前内容块/ })).toBeChecked()
  58 |     await expect(dialog.getByRole('region', { name: '所选范围索引状态' })).toContainText('尚无索引')
  59 |     const query = async (text: string) => {
  60 |       await expect(dialog.getByLabel('检索词', { exact: true })).toBeEnabled()
  61 |       await dialog.getByLabel('检索词', { exact: true }).fill(text)
  62 |       const response = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/retrieval/query'))
  63 |       await dialog.getByRole('button', { name: '查询所选材料', exact: true }).click()
  64 |       const value = await response; expect(value.status()).toBe(200); const body: RetrievalQueryView = await value.json(); responses.push(body); return body
  65 |     }
  66 |     const cold = await query('SVD'); expect(cold.index_state).toBe('missing'); expect(cold.result_state).toBe('not_ready'); expect(cold.scope_refs).toEqual([refs.block])
  67 |     const rebuild = async () => {
  68 |       const response = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/index/rebuild'))
  69 |       await dialog.getByRole('button', { name: '明确按已读描述重建索引', exact: true }).click()
  70 |       const accepted = await response; expect(accepted.status()).toBe(202); expect(await accepted.json()).toMatchObject({ status: 'queued' })
  71 |       await expect(dialog.getByRole('region', { name: '所选范围索引状态' })).toContainText('索引已就绪', { timeout: 30_000 })
  72 |       await expect(dialog.getByRole('region', { name: '实际索引任务' })).toContainText('任务当前读回：已完成')
  73 |     }
  74 |     await rebuild()
  75 |     const found = await query('SVD'); expect(found.result_state).toBe('matched'); expect(found.hits).toHaveLength(1); expect(found.hits[0].ref).toEqual(refs.block)
  76 |     await expect(dialog.getByLabel('完整原文：合成未审 retrieval_native_original', { exact: true })).toHaveText(found.hits[0].text)
  77 |     await dialog.getByRole('button', { name: '回读此精确块与来源', exact: true }).click()
  78 |     await expect(dialog.getByRole('region', { name: '独立精确块只读查看' })).toContainText('原始 SVD 概率教材')
  79 |     expect((await query('absentwordxyz')).result_state).toBe('no_match')
  80 |     await dialog.getByRole('radio', { name: /明确查找当前完整教材/ }).check()
  81 |     await expect(dialog.getByRole('region', { name: '所选范围索引状态' })).toContainText('尚无索引')
  82 |     await rebuild()
  83 |     const omitted = await query('budget'); expect(omitted.result_state).toBe('resource_omitted'); expect(omitted.hits).toEqual([]); expect(omitted.omissions.text_byte_budget).toBe(1); expect(omitted.scope_refs).toEqual([refs.course])
  84 |     await expect(dialog.getByRole('heading', { name: '存在匹配，但完整材料超出返回预算', exact: true })).toBeVisible()
  85 |     material(runtime, true)
  86 |     await dialog.getByRole('button', { name: '刷新范围与任务', exact: true }).click()
  87 |     await expect(dialog.getByRole('region', { name: '所选范围索引状态' })).toContainText('原索引需要重新核验')
  88 |     const stale = await query('SVD'); expect(stale.index_state).toBe('stale'); expect(stale.hits).toEqual([])
  89 |     await rebuild()
  90 |     const historical = await query('SVD'); expect(historical.result_state).toBe('matched'); expect(historical.scope_refs).toEqual([refs.course]); expect(historical.hits[0].ref).toEqual(refs.block); expect(historical.hits[0].current_ref.revision).toBe(2); expect(historical.hits[0].text).toBe(found.hits[0].text)
  91 |     await expect(dialog.getByText('HISTORICAL_REVISION', { exact: false })).toBeVisible()
  92 |     await page.screenshot({ path: info.outputPath('retrieval-historical-1440.png') })
  93 |     await page.setViewportSize({ width: 390, height: 844 }); expect(await dialog.evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
  94 |     await page.screenshot({ path: info.outputPath('retrieval-historical-390.png') })
  95 |     expect(errors).toEqual([])
  96 |     writeFileSync(info.outputPath('actual-retrieval-readback.json'), JSON.stringify({ scope: 'Native browser and actual local HTTP/SQLite/worker over explicitly injected unreviewed synthetic public Content; current revision advance via ContentService fixture is not a formal author publication or expert approval workflow. No Provider calls.', references: refs, query_responses: responses, runtime_errors: errors }, null, 2))
  97 |   } finally { await runtime.close() }
  98 | })
  99 | 
```