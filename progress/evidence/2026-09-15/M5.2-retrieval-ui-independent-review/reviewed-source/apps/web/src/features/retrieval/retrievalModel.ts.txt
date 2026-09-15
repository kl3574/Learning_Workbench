import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { ContentRef, RetrievalHitView, RetrievalIndexScopeStatus, RetrievalQueryView, RetrievalScopePath } from '../../../../../packages/contracts/generated/api-types'
import { checkedShape } from './retrievalSchema'
import { exactRef } from '../assessment/target'
import { sameRef, type ReaderTarget } from '../reader/target'
export const digest = (text: string) => bytesToHex(sha256(new TextEncoder().encode(text)))
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
  if (value && typeof value === 'object') { const row = value as Record<string, unknown>; return `{${Object.keys(row).sort().map(key => `${JSON.stringify(key)}:${canonical(row[key])}`).join(',')}}` }
  return JSON.stringify(value)
}
const compareRef = (a: ContentRef, b: ContentRef) => a.entity < b.entity ? -1 : a.entity > b.entity ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : a.revision - b.revision || (a.sha256 < b.sha256 ? -1 : a.sha256 > b.sha256 ? 1 : 0)
const fail = (): never => { throw new Error('检索响应的范围、索引或原文关系不一致；未采用其他对象或损坏正文。') }
export function normalizedRefs(refs: ContentRef[]): ContentRef[] {
  if (!Array.isArray(refs) || refs.length < 1 || refs.length > 16) fail()
  const identities = new Map<string, string>()
  for (const ref of refs) {
    if (!['block', 'lesson', 'course'].includes(ref.entity) || !exactRef(ref, ref.entity)) fail()
    const key = `${ref.entity}:${ref.id}:${ref.revision}`
    if (identities.has(key) && identities.get(key) !== ref.sha256) fail()
    identities.set(key, ref.sha256)
  }
  return [...new Map(refs.map(ref => [canonical(ref), ref])).values()].sort(compareRef)
}
export const scopeHash = (workspace: string, refs: ContentRef[]) => digest(canonical({ version: 'retrieval-scope-v1', workspace_id: workspace, scope_refs: normalizedRefs(refs) }))
function checkScope(value: { scope_sha256: string; scope_refs: ContentRef[] }, workspace: string, refs: ContentRef[]) {
  if (value.scope_sha256 !== scopeHash(workspace, refs) || canonical(value.scope_refs) !== canonical(normalizedRefs(refs))) fail()
}
export function checkedStatus(raw: unknown, workspace: string, refs: ContentRef[]): RetrievalIndexScopeStatus {
  const value = checkedShape<RetrievalIndexScopeStatus>('RetrievalIndexScopeStatus', raw)
  checkScope(value, workspace, refs)
  const absent = value.index_version === null
  if (absent !== (value.indexed_corpus_sha256 === null) || absent !== (value.last_built_at === null)) fail()
  if (value.latest_job && (value.latest_job.job.status === 'failed') !== (value.latest_job.error !== null)) fail()
  if (value.state === 'ready' && (absent || value.indexed_corpus_sha256 !== value.corpus_sha256)
      || value.state === 'stale' && (absent || value.indexed_corpus_sha256 === value.corpus_sha256)
      || value.state === 'missing' && !absent
      || value.state === 'building' && (!value.latest_job || value.latest_job.target_corpus_sha256 !== value.corpus_sha256 || !['queued', 'running', 'awaiting_approval'].includes(value.latest_job.job.status))) fail()
  return value
}
export function checkedHit(hit: RetrievalHitView, roots: ContentRef[]): void {
  if (hit.ref.entity !== 'block' || hit.current_ref.entity !== 'block' || hit.ref.id !== hit.current_ref.id
      || hit.body_sha256 !== digest(hit.text) || hit.text.includes('\r')) fail()
  const count = Array.from(hit.text).length
  if (hit.location.start_cp !== 0 || hit.location.end_cp !== count
      || hit.locator !== `block:${hit.ref.id}@r${hit.ref.revision};body:${hit.body_sha256};cp:0-${count}`) fail()
  const codes = new Set(hit.warnings.map(w => w.code))
  if (!codes.has('MATERIAL_UNREVIEWED') || codes.has('HISTORICAL_REVISION') !== !sameRef(hit.ref, hit.current_ref)
      || codes.has('CONTENT_ARCHIVED') !== (hit.lifecycle === 'archived')) fail()
  const paths = new Set<string>()
  for (const path of hit.parent_paths) {
    if (!roots.some(root => sameRef(root, path.root_ref)) || !sameRef(path.block_ref, hit.ref)
        || (path.course_ref === null) !== (path.course_title === null) || (path.lesson_ref === null) !== (path.lesson_title === null)) fail()
    if (path.root_ref.entity === 'block' && (!sameRef(path.root_ref, hit.ref) || path.course_ref || path.lesson_ref)
        || path.root_ref.entity === 'lesson' && (!sameRef(path.root_ref, path.lesson_ref) || path.course_ref)
        || path.root_ref.entity === 'course' && (!sameRef(path.root_ref, path.course_ref) || !path.lesson_ref)) fail()
    const key = canonical([path.root_ref, path.course_ref, path.lesson_ref, path.block_ref])
    if (paths.has(key)) fail(); paths.add(key)
  }
  if (hit.provenance.state === 'frozen' && (!hit.provenance.original || hit.provenance.unresolved_citation_ids.length)
      || hit.provenance.state === 'unresolved' && (hit.provenance.original || hit.provenance.citations.length || !hit.provenance.warnings.some(w => w.code === 'PROVENANCE_UNRESOLVED'))) fail()
}
export function checkedQuery(raw: unknown, workspace: string, refs: ContentRef[]): RetrievalQueryView {
  const value = checkedShape<RetrievalQueryView>('RetrievalQueryView', raw)
  checkScope(value, workspace, refs)
  const omissions = Object.values(value.omissions).reduce((sum, number) => sum + number, 0)
  if ((value.index_version === null) !== (value.indexed_corpus_sha256 === null)) fail()
  if (value.index_state !== 'ready') {
    if (value.result_state !== 'not_ready' || value.matched_count !== null || value.hits.length || omissions || !value.warnings.some(w => w.code === `INDEX_${value.index_state.toUpperCase()}`)) fail()
  } else {
    if (value.index_version === null || value.indexed_corpus_sha256 !== value.corpus_sha256 || value.matched_count === null || omissions !== value.matched_count - value.hits.length) fail()
    if (value.result_state === 'matched' ? !value.hits.length : value.result_state === 'resource_omitted'
      ? !value.matched_count || !!value.hits.length || !value.warnings.some(w => w.code === 'RETRIEVAL_RESOURCE_OMITTED')
      : !['indexed_empty', 'no_match'].includes(value.result_state) || !!value.matched_count || !!value.hits.length || !!omissions) fail()
  }
  let bytes = 0
  value.hits.forEach((hit, index) => {
    checkedHit(hit, refs); bytes += new TextEncoder().encode(hit.text).length
    const previous = value.hits[index - 1]
    if (previous && (previous.score < hit.score || previous.score === hit.score && compareRef(previous.ref, hit.ref) >= 0)) fail()
  })
  if (bytes > 2 * 1024 * 1024 || new Set(value.hits.map(hit => canonical(hit.ref))).size !== value.hits.length) fail()
  return value
}
export function readerPath(path: RetrievalScopePath): ReaderTarget | null {
  return path.root_ref.entity === 'course' && path.course_ref && path.lesson_ref
    ? { course: path.course_ref, lesson: path.lesson_ref, block: path.block_ref } : null
}
