# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: text-edit-concepts.spec.ts >> native text edit preserves original concept pins and ordered dependencies after their current refs advance
- Location: tests/e2e/text-edit-concepts.spec.ts:53:1

# Error details

```
Error: Command failed: <LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-text-concept-native-oct03/.venv/bin/python -B -c import base64,hashlib,json,io,zipfile
from packages.contracts import domain_models as d
from packages.contracts.canonical import canonical_bytes,metadata_sha256
def ref(x): return d.ContentRef(entity=x.entity,id=x.id,revision=x.revision,sha256=metadata_sha256(x))
def block(name,body,dependencies=[],concept_ids=[]): return d.ContentBlock(id='native_concept_edit_'+name,revision=1,kind='text',title='原创合成依赖 '+name,body_path='content/dependency-'+name+'.md',body_sha256=hashlib.sha256(body.encode()).hexdigest(),depends_on=dependencies,concepts=concept_ids)
bodies={name:'原创合成 '+name+' 正文。只验软件保存与精确引用，不作学术或教学批准。\n' for name in ['first','second','base']}
concept_first=d.Concept(id='native_edit_concept_first',revision=1,title='Original first concept')
concept_second=d.Concept(id='native_edit_concept_second',revision=1,title='Original second concept')
first=block('first',bodies['first'],concept_ids=[concept_first.id]); second=block('second',bodies['second']); base=block('base',bodies['base'],[ref(second),ref(first)],[concept_second.id,concept_first.id])
blocks=[base,first,second]
lesson=d.Lesson(id='native_concept_edit_lesson',revision=1,title='合成依赖编辑小节',objectives=['保留原精确引用'],block_refs=[ref(base)])
course=d.Course(id='native_concept_edit_course',revision=1,title='合成依赖编辑教材',audience='软件验收',concept_refs=[ref(concept_first),ref(concept_second)],lesson_refs=[ref(lesson)])
p={'course.json':canonical_bytes(course),'concepts.json':canonical_bytes([concept_first,concept_second]),'symbols.json':b'[]','sources/citations.json':b'[]','lessons/dependencies.json':canonical_bytes(lesson)}
for value in blocks:
 p['blocks/'+value.id+'.json']=canonical_bytes(value);p[value.body_path]=bodies[value.id.removeprefix('native_concept_edit_')].encode()
m=d.Manifest(package_id='native_concept_edit_package',profile='learner',created_at='2026-10-02T00:00:00Z',files=[d.FileEntry(path=k,sha256=hashlib.sha256(v).hexdigest(),size=len(v),media_type='text/markdown' if k.endswith('.md') else 'application/json',visibility='learner') for k,v in sorted(p.items())])
p['manifest.json']=canonical_bytes(m);f=io.BytesIO()
with zipfile.ZipFile(f,'w') as z:
 for k,v in sorted(p.items()): z.writestr(zipfile.ZipInfo(k,date_time=(2026,10,2,0,0,0)),v)
print(json.dumps({'archive':base64.b64encode(f.getvalue()).decode(),'course':ref(course).model_dump(),'concepts':[ref(concept_second).model_dump(),ref(concept_first).model_dump()],'lessons':[ref(lesson).model_dump()],'blocks':[ref(value).model_dump() for value in blocks],'bodies':{'native_concept_edit_'+name:body for name,body in bodies.items()}}))
Traceback (most recent call last):
  File "<string>", line 13, in <module>
  File "<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-text-concept-native-oct03/packages/contracts/canonical.py", line 26, in canonical_bytes
    return json.dumps(
           ^^^^^^^^^^^
  File "<LOCAL_HOME>/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/json/__init__.py", line 238, in dumps
    **kw).encode(obj)
          ^^^^^^^^^^^
  File "<LOCAL_HOME>/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/json/encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<LOCAL_HOME>/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/json/encoder.py", line 258, in iterencode
    return _iterencode(o, 0)
           ^^^^^^^^^^^^^^^^^
  File "<LOCAL_HOME>/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/json/encoder.py", line 180, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
TypeError: Object of type Concept is not JSON serializable

```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { writeFileSync } from 'node:fs'
  3   | import { resolve } from 'node:path'
  4   | import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  5   | import type { ContentBlock, ContentRef, DraftCreated, EditDraftSnapshot } from '../../packages/contracts/generated/api-types'
  6   | import { RestartRuntime } from './restartRuntime'
  7   | import { importReaderPackage, type ReaderPackage } from './readerTestData'
  8   | import { publishExtra } from './contentImpactsData'
  9   | 
  10  | function conceptPackage(): ReaderPackage & { concepts: ContentRef[] } {
  11  |   const root = resolve(import.meta.dirname, '../..')
  12  |   const script = `import base64,hashlib,json,io,zipfile
  13  | from packages.contracts import domain_models as d
  14  | from packages.contracts.canonical import canonical_bytes,metadata_sha256
  15  | def ref(x): return d.ContentRef(entity=x.entity,id=x.id,revision=x.revision,sha256=metadata_sha256(x))
  16  | def block(name,body,dependencies=[],concept_ids=[]): return d.ContentBlock(id='native_concept_edit_'+name,revision=1,kind='text',title='原创合成依赖 '+name,body_path='content/dependency-'+name+'.md',body_sha256=hashlib.sha256(body.encode()).hexdigest(),depends_on=dependencies,concepts=concept_ids)
  17  | bodies={name:'原创合成 '+name+' 正文。只验软件保存与精确引用，不作学术或教学批准。\\n' for name in ['first','second','base']}
  18  | concept_first=d.Concept(id='native_edit_concept_first',revision=1,title='Original first concept')
  19  | concept_second=d.Concept(id='native_edit_concept_second',revision=1,title='Original second concept')
  20  | first=block('first',bodies['first'],concept_ids=[concept_first.id]); second=block('second',bodies['second']); base=block('base',bodies['base'],[ref(second),ref(first)],[concept_second.id,concept_first.id])
  21  | blocks=[base,first,second]
  22  | lesson=d.Lesson(id='native_concept_edit_lesson',revision=1,title='合成依赖编辑小节',objectives=['保留原精确引用'],block_refs=[ref(base)])
  23  | course=d.Course(id='native_concept_edit_course',revision=1,title='合成依赖编辑教材',audience='软件验收',concept_refs=[ref(concept_first),ref(concept_second)],lesson_refs=[ref(lesson)])
  24  | p={'course.json':canonical_bytes(course),'concepts.json':canonical_bytes([concept_first,concept_second]),'symbols.json':b'[]','sources/citations.json':b'[]','lessons/dependencies.json':canonical_bytes(lesson)}
  25  | for value in blocks:
  26  |  p['blocks/'+value.id+'.json']=canonical_bytes(value);p[value.body_path]=bodies[value.id.removeprefix('native_concept_edit_')].encode()
  27  | m=d.Manifest(package_id='native_concept_edit_package',profile='learner',created_at='2026-10-02T00:00:00Z',files=[d.FileEntry(path=k,sha256=hashlib.sha256(v).hexdigest(),size=len(v),media_type='text/markdown' if k.endswith('.md') else 'application/json',visibility='learner') for k,v in sorted(p.items())])
  28  | p['manifest.json']=canonical_bytes(m);f=io.BytesIO()
  29  | with zipfile.ZipFile(f,'w') as z:
  30  |  for k,v in sorted(p.items()): z.writestr(zipfile.ZipInfo(k,date_time=(2026,10,2,0,0,0)),v)
  31  | print(json.dumps({'archive':base64.b64encode(f.getvalue()).decode(),'course':ref(course).model_dump(),'concepts':[ref(concept_second).model_dump(),ref(concept_first).model_dump()],'lessons':[ref(lesson).model_dump()],'blocks':[ref(value).model_dump() for value in blocks],'bodies':{'native_concept_edit_'+name:body for name,body in bodies.items()}}))`
> 32  |   const value = JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', script], { cwd: root, encoding: 'utf8' }))
      |                            ^ Error: Command failed: <LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-text-concept-native-oct03/.venv/bin/python -B -c import base64,hashlib,json,io,zipfile
  33  |   return { ...value, bytes: Buffer.from(value.archive, 'base64') }
  34  | }
  35  | 
  36  | type RetainedWitness = { root_ref: ContentRef; edges: Array<{ owner_ref: ContentRef; target_ref: ContentRef; relation: 'reference' | 'concept' }> }
  37  | function readWitness(runtime: RestartRuntime, workspace: string, ref: ContentRef): RetainedWitness {
  38  |   const root = resolve(import.meta.dirname, '../..')
  39  |   const program = `import json,sys
  40  | from pathlib import Path
  41  | from services.api.app.infrastructure.config import Settings
  42  | from services.api.app.infrastructure.database import Database
  43  | from services.api.app.application.content import ContentService
  44  | from packages.contracts.domain_models import ContentRef
  45  | db=Database(Settings(data_dir=Path(sys.argv[1])));service=ContentService(db)
  46  | with db.connect() as connection:
  47  |  connection.execute('PRAGMA query_only=ON');connection.execute('BEGIN')
  48  |  value=service.verify_retained_dependencies_in_transaction(connection,sys.argv[2],ContentRef.model_validate_json(sys.argv[3]))
  49  |  print(value.model_dump_json())`
  50  |   return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', program, runtime.data, workspace, JSON.stringify(ref)], { cwd: root, encoding: 'utf8' }))
  51  | }
  52  | 
  53  | test('native text edit preserves original concept pins and ordered dependencies after their current refs advance', async ({ playwright }, info) => {
  54  |   test.setTimeout(150_000)
  55  |   const runtime = await RestartRuntime.start(), errors: string[] = []
  56  |   try {
  57  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  58  |     page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
  59  |     const fixture = conceptPackage(), imported = await importReaderPackage(page, fixture)
  60  |     await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  61  |     await expect(imported.dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  62  |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  63  |     const base = fixture.blocks[0], ordered = [fixture.blocks[2], fixture.blocks[1]]
  64  |     await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lessons[0], block: base, view: 'lesson' }))}`)
  65  |     const editor = page.getByRole('region', { name: '文本块编辑与恢复', exact: true })
  66  |     await editor.getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
  67  |     const originals = editor.getByLabel('原精确依赖只读记录', { exact: true })
  68  |     await expect(originals).toBeVisible(); expect(JSON.parse((await originals.textContent())!)).toEqual(ordered)
  69  |     expect(await originals.evaluate(el => el.tagName)).toBe('PRE')
  70  |     const conceptIds = fixture.concepts.map(ref => ref.id)
  71  |     const originalConcepts = editor.getByLabel('原概念 ID 只读记录', { exact: true })
  72  |     await expect(originalConcepts).toBeVisible(); expect(JSON.parse((await originalConcepts.textContent())!)).toEqual(conceptIds)
  73  |     expect(await originalConcepts.evaluate(el => el.tagName)).toBe('PRE')
  74  |     const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/drafts'))
  75  |     await editor.getByRole('button', { name: '从此准确修订明确创建编辑稿', exact: true }).click()
  76  |     const createdResponse = await creating; expect(createdResponse.status()).toBe(201)
  77  |     const created: DraftCreated = await createdResponse.json(), id = created.draft_id
  78  |     await editor.getByLabel('读取已有编辑稿 ID', { exact: true }).fill(id)
  79  |     await editor.getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
  80  |     const title = '已明确编辑但保留依赖的合成标题', body = '合成新正文 🧠 e\u0301\n仅修改本文，保留历史来源引用及顺序。\n'
  81  |     await editor.getByLabel('本机标题', { exact: true }).fill(title)
  82  |     await editor.getByLabel('本机正文', { exact: true }).fill(body)
  83  |     const patching = page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
  84  |     await editor.getByRole('button', { name: '明确提交本机标题与正文', exact: true }).click()
  85  |     const patched = await patching; expect(patched.status()).toBe(200)
  86  |     expect(patched.request().postDataJSON().patches.map((value: { field: string }) => value.field).sort()).toEqual(['body_markdown', 'title'])
  87  |     await editor.getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
  88  |     const snapshotResponse = await page.request.get(`/api/v1/draft-edits/${id}`); expect(snapshotResponse.status()).toBe(200)
  89  |     const snapshot: EditDraftSnapshot = await snapshotResponse.json()
  90  |     expect(snapshot.payload.body_markdown).toBe(body); expect(snapshot.base_ref).toEqual(base)
  91  |     const workspace = await page.request.get('/api/v1/session').then(r => r.json()).then(value => value.workspace_id as string)
  92  |     const originalWitness = readWitness(runtime, workspace, base)
  93  |     for (const ref of [...ordered, ...fixture.concepts]) publishExtra(runtime, workspace, ref, [2])
  94  |     const currentSources: ContentRef[] = []
  95  |     for (const ref of [...ordered, ...fixture.concepts]) {
  96  |       const response = await page.request.get(`/api/v1/objects/${ref.id}/current`); expect(response.status()).toBe(200)
  97  |       const current: ContentRef = await response.json(); expect(current.id).toBe(ref.id); expect(current.revision).toBe(2); expect(current.sha256).not.toBe(ref.sha256)
  98  |       currentSources.push(current)
  99  |     }
  100 |     await editor.getByRole('button', { name: '核验已保存精确编辑稿并进入审核', exact: true }).click()
  101 |     const review = editor.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
  102 |     await review.getByLabel('本次审核备注', { exact: true }).fill('合成软件验收：新审核基于明确保存的正文和原精确依赖；不认证学术质量。')
  103 |     await review.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
  104 |     const reviewing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${id}/review`))
  105 |     await review.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
  106 |     const reviewed = await reviewing; expect(reviewed.status()).toBe(202); const reviewAck = await reviewed.json()
  107 |     await review.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  108 |     const decision = review.getByRole('region', { name: '明确人工审核决定', exact: true })
  109 |     await decision.getByLabel('数学审核决定').selectOption('NOT_APPLICABLE')
  110 |     await decision.getByLabel('来源审核决定').selectOption('APPROVED')
  111 |     await decision.getByLabel('审核理由').fill('原创合成纯文本，人工意图仅供软件协议验收，不作数学、来源或教学质量结论。')
  112 |     await decision.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
  113 |     const deciding = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/reviews/${reviewAck.id}/decision`))
  114 |     await decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click(); expect((await deciding).status()).toBe(200)
  115 |     await review.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  116 |     const publication = review.getByRole('region', { name: '编辑稿发布与恢复', exact: true })
  117 |     await publication.getByRole('button', { name: '选择此审核并重新读取编辑发布基准', exact: true }).click()
  118 |     const basis = publication.getByRole('region', { name: '本次编辑发布基准', exact: true })
  119 |     await basis.getByText('核对完整保留的原精确依赖及顺序', { exact: true }).click()
  120 |     expect(JSON.parse((await basis.getByLabel('发布保留的原精确依赖', { exact: true }).textContent())!)).toEqual(ordered)
  121 |     for (const checkbox of await basis.getByRole('group', { name: '逐条确认此块警告', exact: true }).getByRole('checkbox').all()) await checkbox.check()
  122 |     await basis.getByLabel('我已核对准确编辑稿、原块与所选人工审核，明确发布为原块下一修订。', { exact: true }).check()
  123 |     for (const width of [1440, 390]) {
  124 |       await page.setViewportSize({ width, height: 900 }); await basis.scrollIntoViewIfNeeded()
  125 |       expect(await editor.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
  126 |       await page.screenshot({ path: info.outputPath(`text-concepts-${width}.png`) })
  127 |     }
  128 |     const publishing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${id}/publish`))
  129 |     await basis.getByRole('button', { name: '明确发布这一编辑稿', exact: true }).click()
  130 |     const response = await publishing; expect(response.status()).toBe(201); const published: ContentRef = await response.json()
  131 |     await expect(publication.getByText('原发布 ACK 已保存', { exact: true })).toBeVisible()
  132 |     expect(published.id).toBe(base.id); expect(published.revision).toBe(2)
```