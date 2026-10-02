import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentBlock, ContentRef, DraftCreated, EditDraftSnapshot } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, type ReaderPackage } from './readerTestData'
import { publishExtra } from './contentImpactsData'

function dependencyPackage(): ReaderPackage {
  const root = resolve(import.meta.dirname, '../..')
  const script = `import base64,hashlib,json,io,zipfile
from packages.contracts import domain_models as d
from packages.contracts.canonical import canonical_bytes,metadata_sha256
def ref(x): return d.ContentRef(entity=x.entity,id=x.id,revision=x.revision,sha256=metadata_sha256(x))
def block(name,body,dependencies=[]): return d.ContentBlock(id='native_dependency_'+name,revision=1,kind='text',title='原创合成依赖 '+name,body_path='content/dependency-'+name+'.md',body_sha256=hashlib.sha256(body.encode()).hexdigest(),depends_on=dependencies)
bodies={name:'原创合成 '+name+' 正文。只验软件保存与精确引用，不作学术或教学批准。\\n' for name in ['first','second','base']}
first=block('first',bodies['first']); second=block('second',bodies['second']); base=block('base',bodies['base'],[ref(second),ref(first)])
blocks=[base,first,second]
lesson=d.Lesson(id='native_dependency_lesson',revision=1,title='合成依赖编辑小节',objectives=['保留原精确引用'],block_refs=[ref(base)])
course=d.Course(id='native_dependency_course',revision=1,title='合成依赖编辑教材',audience='软件验收',lesson_refs=[ref(lesson)])
p={'course.json':canonical_bytes(course),'concepts.json':b'[]','symbols.json':b'[]','sources/citations.json':b'[]','lessons/dependencies.json':canonical_bytes(lesson)}
for value in blocks:
 p['blocks/'+value.id+'.json']=canonical_bytes(value);p[value.body_path]=bodies[value.id.removeprefix('native_dependency_')].encode()
m=d.Manifest(package_id='native_dependency_package',profile='learner',created_at='2026-10-02T00:00:00Z',files=[d.FileEntry(path=k,sha256=hashlib.sha256(v).hexdigest(),size=len(v),media_type='text/markdown' if k.endswith('.md') else 'application/json',visibility='learner') for k,v in sorted(p.items())])
p['manifest.json']=canonical_bytes(m);f=io.BytesIO()
with zipfile.ZipFile(f,'w') as z:
 for k,v in sorted(p.items()): z.writestr(zipfile.ZipInfo(k,date_time=(2026,10,2,0,0,0)),v)
print(json.dumps({'archive':base64.b64encode(f.getvalue()).decode(),'course':ref(course).model_dump(),'lessons':[ref(lesson).model_dump()],'blocks':[ref(value).model_dump() for value in blocks],'bodies':{'native_dependency_'+name:body for name,body in bodies.items()}}))`
  const value = JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', script], { cwd: root, encoding: 'utf8' }))
  return { ...value, bytes: Buffer.from(value.archive, 'base64') }
}

test('native text edit preserves ordered original dependency refs after source current advances', async ({ playwright }, info) => {
  test.setTimeout(150_000)
  const runtime = await RestartRuntime.start(), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
    const fixture = dependencyPackage(), imported = await importReaderPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(imported.dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const base = fixture.blocks[0], ordered = [fixture.blocks[2], fixture.blocks[1]]
    await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lessons[0], block: base, view: 'lesson' }))}`)
    const editor = page.getByRole('region', { name: '文本块编辑与恢复', exact: true })
    await editor.getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
    const originals = editor.getByLabel('原精确依赖只读记录', { exact: true })
    await expect(originals).toBeVisible(); expect(JSON.parse((await originals.textContent())!)).toEqual(ordered)
    expect(await originals.evaluate(el => el.tagName)).toBe('PRE')
    const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/drafts'))
    await editor.getByRole('button', { name: '从此准确修订明确创建编辑稿', exact: true }).click()
    const createdResponse = await creating; expect(createdResponse.status()).toBe(201)
    const created: DraftCreated = await createdResponse.json(), id = created.draft_id
    await editor.getByLabel('读取已有编辑稿 ID', { exact: true }).fill(id)
    await editor.getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
    const title = '已明确编辑但保留依赖的合成标题', body = '合成新正文 🧠 e\u0301\n仅修改本文，保留历史来源引用及顺序。\n'
    await editor.getByLabel('本机标题', { exact: true }).fill(title)
    await editor.getByLabel('本机正文', { exact: true }).fill(body)
    const patching = page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
    await editor.getByRole('button', { name: '明确提交本机标题与正文', exact: true }).click()
    const patched = await patching; expect(patched.status()).toBe(200)
    expect(patched.request().postDataJSON().patches.map((value: { field: string }) => value.field).sort()).toEqual(['body_markdown', 'title'])
    await editor.getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
    const snapshotResponse = await page.request.get(`/api/v1/draft-edits/${id}`); expect(snapshotResponse.status()).toBe(200)
    const snapshot: EditDraftSnapshot = await snapshotResponse.json()
    expect(snapshot.payload.body_markdown).toBe(body); expect(snapshot.base_ref).toEqual(base)
    const workspace = await page.request.get('/api/v1/session').then(r => r.json()).then(value => value.workspace_id as string)
    for (const ref of ordered) publishExtra(runtime, workspace, ref, [2])
    const currentSources: ContentRef[] = []
    for (const ref of ordered) {
      const response = await page.request.get(`/api/v1/objects/${ref.id}/current`); expect(response.status()).toBe(200)
      const current: ContentRef = await response.json(); expect(current.id).toBe(ref.id); expect(current.revision).toBe(2); expect(current.sha256).not.toBe(ref.sha256)
      currentSources.push(current)
    }
    await editor.getByRole('button', { name: '核验已保存精确编辑稿并进入审核', exact: true }).click()
    const review = editor.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await review.getByLabel('本次审核备注', { exact: true }).fill('合成软件验收：新审核基于明确保存的正文和原精确依赖；不认证学术质量。')
    await review.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
    const reviewing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${id}/review`))
    await review.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
    const reviewed = await reviewing; expect(reviewed.status()).toBe(202); const reviewAck = await reviewed.json()
    await review.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
    const decision = review.getByRole('region', { name: '明确人工审核决定', exact: true })
    await decision.getByLabel('数学审核决定').selectOption('NOT_APPLICABLE')
    await decision.getByLabel('来源审核决定').selectOption('APPROVED')
    await decision.getByLabel('审核理由').fill('原创合成纯文本，人工意图仅供软件协议验收，不作数学、来源或教学质量结论。')
    await decision.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
    const deciding = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/reviews/${reviewAck.id}/decision`))
    await decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click(); expect((await deciding).status()).toBe(200)
    await review.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
    const publication = review.getByRole('region', { name: '编辑稿发布与恢复', exact: true })
    await publication.getByRole('button', { name: '选择此审核并重新读取编辑发布基准', exact: true }).click()
    const basis = publication.getByRole('region', { name: '本次编辑发布基准', exact: true })
    await basis.getByText('核对完整保留的原精确依赖及顺序', { exact: true }).click()
    expect(JSON.parse((await basis.getByLabel('发布保留的原精确依赖', { exact: true }).textContent())!)).toEqual(ordered)
    for (const checkbox of await basis.getByRole('group', { name: '逐条确认此块警告', exact: true }).getByRole('checkbox').all()) await checkbox.check()
    await basis.getByLabel('我已核对准确编辑稿、原块与所选人工审核，明确发布为原块下一修订。', { exact: true }).check()
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 }); await basis.scrollIntoViewIfNeeded()
      expect(await editor.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
      await page.screenshot({ path: info.outputPath(`text-dependencies-${width}.png`) })
    }
    const publishing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${id}/publish`))
    await basis.getByRole('button', { name: '明确发布这一编辑稿', exact: true }).click()
    const response = await publishing; expect(response.status()).toBe(201); const published: ContentRef = await response.json()
    await expect(publication.getByText('原发布 ACK 已保存', { exact: true })).toBeVisible()
    expect(published.id).toBe(base.id); expect(published.revision).toBe(2)
    const metadataResponse = await page.request.get(`/api/v1/blocks/${base.id}?revision=2`); expect(metadataResponse.status()).toBe(200)
    expect(metadataResponse.headers().etag).toBe(`"${published.sha256}"`)
    const metadata: ContentBlock = await metadataResponse.json()
    expect(metadata.depends_on).toEqual(ordered); expect(metadata.title).toBe(title); expect(metadata.concepts).toEqual([])
    const bodyResponse = await page.request.get(`/api/v1/blocks/${base.id}/body?revision=2`); expect(bodyResponse.status()).toBe(200); expect(await bodyResponse.text()).toBe(body)
    expect(await page.request.get(`/api/v1/blocks/${base.id}/body?revision=1`).then(r => r.text())).toBe(fixture.bodies[base.id])
    const actual = await page.request.get(`/api/v1/draft-edits/${id}`).then(r => r.json()); expect(actual.state).toBe('published'); expect(actual.candidate).toEqual(snapshot.candidate)
    expect(await page.request.get(`/api/v1/lessons/${fixture.lessons[0].id}?revision=1`).then(r => r.json()).then(value => value.block_refs)).toEqual([base])
    writeFileSync(info.outputPath('text-dependencies-actual.json'), JSON.stringify({ scope: 'Actual native Import/Reader/Edit/Review/synthetic human decision/publication and independent readback. Fixture-only source current advancement uses Content owner; no external model or academic acceptance.', base, original_ordered_dependencies: ordered, later_source_currents: currentSources, candidate: snapshot.candidate, publish_request: response.request().postDataJSON(), original_ack: published, current_draft: actual, actual_block: metadata, actual_body: await bodyResponse.text(), page_errors: errors }, null, 2))
    expect(errors).toEqual([])
  } finally { await runtime.close() }
})
