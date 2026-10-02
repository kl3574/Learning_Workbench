import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef, DraftCreated } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, type ReaderPackage } from './readerTestData'
export function originalImpactPackage(): ReaderPackage {
  const root = resolve(import.meta.dirname, '../..')
  const script = `import base64,hashlib,json,io,zipfile
from packages.contracts import domain_models as d
from packages.contracts.canonical import canonical_bytes,metadata_sha256
body='原创合成编辑正文。仅验证软件保存、冲突与恢复，不作教学批准。\\n'
b=d.ContentBlock(id='block_native_impact',revision=1,kind='text',title='原创合成编辑标题',body_path='content/native-impact.md',body_sha256=hashlib.sha256(body.encode()).hexdigest())
def ref(x): return d.ContentRef(entity=x.entity,id=x.id,revision=x.revision,sha256=metadata_sha256(x))
l=d.Lesson(id='lesson_native_impact',revision=1,title='原创影响验收小节',objectives=['保留原文'],block_refs=[ref(b)])
c=d.Course(id='course_native_impact',revision=1,title='原创影响验收教材',audience='合成验收',lesson_refs=[ref(l)])
p={'course.json':canonical_bytes(c),'concepts.json':b'[]','symbols.json':b'[]','sources/citations.json':b'[]','blocks/native-impact.json':canonical_bytes(b),'lessons/native-impact.json':canonical_bytes(l),b.body_path:body.encode()}
m=d.Manifest(package_id='package_native_impact',profile='learner',created_at='2026-09-28T00:00:00Z',files=[d.FileEntry(path=k,sha256=hashlib.sha256(v).hexdigest(),size=len(v),media_type='text/markdown' if k.endswith('.md') else 'application/json',visibility='learner') for k,v in sorted(p.items())])
p['manifest.json']=canonical_bytes(m)
f=io.BytesIO()
with zipfile.ZipFile(f,'w') as z:
 for k,v in sorted(p.items()): z.writestr(zipfile.ZipInfo(k,date_time=(2026,9,28,0,0,0)),v)
print(json.dumps({'archive':base64.b64encode(f.getvalue()).decode(),'course':ref(c).model_dump(),'lessons':[ref(l).model_dump()],'blocks':[ref(b).model_dump()],'bodies':{b.id:body}}))`
  const value = JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', script], { cwd: root, encoding: 'utf8' }))
  return { ...value, bytes: Buffer.from(value.archive, 'base64') }
}

export async function publishEditedBlock(page: Page, runtime: RestartRuntime, beforeEdit?: (fixture: ReaderPackage) => Promise<void>) {
  const fixture = originalImpactPackage(), imported = await importReaderPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  const href = `${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lessons[0], block: fixture.blocks[0], view: 'lesson' }))}`
  await page.goto(href)
  if (beforeEdit) await beforeEdit(fixture)
  const editor = page.getByRole('region', { name: '文本块编辑与恢复', exact: true })
  await editor.getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
  const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/drafts'))
  await editor.getByRole('button', { name: '从此准确修订明确创建编辑稿', exact: true }).click()
  const created: DraftCreated = await (await creating).json()
  await editor.getByLabel('读取已有编辑稿 ID', { exact: true }).fill(created.draft_id)
  await editor.getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
  await editor.getByLabel('本机标题', { exact: true }).fill('发布后原创内容影响标题')
  await editor.getByLabel('本机正文', { exact: true }).fill('原创合成内容影响发布正文，仅验证软件保存与复核流程。\n')
  const patch = page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${created.draft_id}`))
  await editor.getByRole('button', { name: '明确提交本机标题与正文', exact: true }).click(); expect((await patch).status()).toBe(200)
  await editor.getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
  await editor.getByRole('button', { name: '核验已保存精确编辑稿并进入审核', exact: true }).click()
  const review = editor.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
  await review.getByRole('textbox', { name: '本次审核备注', exact: true }).fill('原创合成纯文本软件验收；不作真实学术或教学批准。')
  await review.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
  const reviewing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${created.draft_id}/review`))
  await review.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click(); const reviewAck = await (await reviewing).json()
  await review.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  const decision = review.getByRole('region', { name: '明确人工审核决定', exact: true })
  await decision.getByLabel('数学审核决定').selectOption('NOT_APPLICABLE'); await decision.getByLabel('来源审核决定').selectOption('APPROVED')
  await decision.getByLabel('审核理由').fill('明确合成判断：原创纯文本无数学断言，仅作软件流程验收。')
  await decision.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
  const deciding = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/reviews/${reviewAck.id}/decision`))
  await decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click(); expect((await deciding).status()).toBe(200)
  await review.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  const publication = review.getByRole('region', { name: '编辑稿发布与恢复', exact: true })
  await publication.getByRole('button', { name: '选择此审核并重新读取编辑发布基准', exact: true }).click()
  const basis = publication.getByRole('region', { name: '本次编辑发布基准', exact: true })
  await expect(basis).toBeVisible()
  await expect(basis.getByRole('group', { name: '逐条确认此块警告' })).toBeVisible()
  for (const box of await basis.getByRole('group', { name: '逐条确认此块警告' }).getByRole('checkbox').all()) await box.check()
  await basis.getByLabel('我已核对准确编辑稿、原块与所选人工审核，明确发布为原块下一修订。', { exact: true }).check()
  const publishing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${created.draft_id}/publish`))
  await basis.getByRole('button', { name: '明确发布这一编辑稿', exact: true }).click()
  const response = await publishing; expect(response.status()).toBe(201); const published: ContentRef = await response.json()
  await expect(publication.getByText('原发布 ACK 已保存', { exact: true })).toBeVisible()
  expect(published.id).toBe(fixture.blocks[0].id); expect(published.revision).toBe(2)
  return { fixture, published, href, draft_id: created.draft_id, review_id: reviewAck.id }
}
export function publishExtra(runtime: RestartRuntime, workspace: string, ref: ContentRef, revisions: number[]) {
  const root = resolve(import.meta.dirname, '../..')
  const program = `import sys,json
from pathlib import Path
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.application.content import ContentService
from packages.contracts.domain_models import ContentRef
s=ContentService(Database(Settings(data_dir=Path(sys.argv[1]))));r=ContentRef.model_validate_json(sys.argv[3]);v=s.read(sys.argv[2],r.entity,r.id,r.revision)
for n in json.loads(sys.argv[4]): s.publish(sys.argv[2],[v.model_copy(update={'revision':n,'title':'Synthetic extra owner publication '+str(n)})],{})
print(json.dumps({'scope':'Controlled ContentService publication solely for pagination/current-state changes; no event IDs read or inserted','revisions':json.loads(sys.argv[4])}))`
  return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B','-c',program,runtime.data,workspace,JSON.stringify(ref),JSON.stringify(revisions)], { cwd: root, encoding: 'utf8' }))
}
