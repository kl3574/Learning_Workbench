import { describe, expect, it } from 'vitest'
import { checkedQuery, checkedStatus, digest, readerPath, scopeHash } from './retrievalModel'
import type { RetrievalHitView, RetrievalIndexScopeStatus, RetrievalQueryView } from '../../../../../packages/contracts/generated/api-types'
const ref = { entity: 'block' as const, id: 'block_retrieval', revision: 1, sha256: 'a'.repeat(64) }
const workspace = 'workspace_retrieval'
const status = (): RetrievalIndexScopeStatus => ({ kind: 'scope', scope_refs: [ref], scope_sha256: scopeHash(workspace, [ref]), corpus_sha256: 'b'.repeat(64), state: 'missing', indexed_corpus_sha256: null, index_version: null, last_built_at: null, latest_job: null })
const query = (): RetrievalQueryView => ({ scope_refs: [ref], scope_sha256: scopeHash(workspace, [ref]), corpus_sha256: 'b'.repeat(64), index_state: 'missing', indexed_corpus_sha256: null, index_version: null, result_state: 'not_ready', matched_count: null, hits: [], omissions: { result_limit: 0, text_byte_budget: 0, json_byte_budget: 0 }, warnings: [{ code: 'INDEX_MISSING', message: '尚无索引', locator: null, severity: 'warning' }] })
describe('retrieval exact public model', () => {
  it('binds the explicit full scope and keeps no_match separate from not_ready', () => {
    expect(checkedStatus(status(), workspace, [ref]).state).toBe('missing')
    expect(checkedQuery(query(), workspace, [ref]).result_state).toBe('not_ready')
    expect(() => checkedQuery({ ...query(), result_state: 'no_match', matched_count: 0 }, workspace, [ref])).toThrow()
  })
  it('rejects another workspace, revision, extra wire field and false ready', () => {
    expect(() => checkedStatus(status(), 'workspace_other', [ref])).toThrow()
    expect(() => checkedStatus(status(), workspace, [{ ...ref, revision: 2 }])).toThrow()
    expect(() => checkedStatus({ ...status(), fake: true }, workspace, [ref])).toThrow()
    expect(() => checkedStatus({ ...status(), state: 'ready' }, workspace, [ref])).toThrow()
    expect(() => checkedStatus({ ...status(), state: 'building' }, workspace, [ref])).toThrow()
  })
  it('preserves full original UTF-8, Unicode codepoint locations, historical refs and absent parents', () => {
    const text = '条件😀\n'
    const hit: RetrievalHitView = { ref, current_ref: { ...ref, revision: 2, sha256: 'c'.repeat(64) }, title: '历史未审块', text, score: 1, body_sha256: digest(text), locator: `block:${ref.id}@r1;body:${digest(text)};cp:0-4`, location: { version: 'whole-block-v1', unit: 'unicode_codepoint', start_cp: 0, end_cp: 4 }, lifecycle: 'archived', material_review: 'unreviewed', provenance: { state: 'unresolved', original: null, citations: [], unresolved_citation_ids: [], warnings: [{ code: 'PROVENANCE_UNRESOLVED', message: '无冻结来源', locator: null, severity: 'warning' }] }, parent_paths: [{ root_ref: ref, block_ref: ref, course_ref: null, course_title: null, lesson_ref: null, lesson_title: null }], warnings: ['MATERIAL_UNREVIEWED', 'HISTORICAL_REVISION', 'CONTENT_ARCHIVED'].map(code => ({ code, message: code, locator: null, severity: 'warning' })) }
    const value: RetrievalQueryView = { ...query(), index_state: 'ready', index_version: 'index_model', indexed_corpus_sha256: 'b'.repeat(64), result_state: 'matched', matched_count: 1, hits: [hit], warnings: [] }
    expect(checkedQuery(value, workspace, [ref]).hits[0].text).toBe(text)
    expect(readerPath(hit.parent_paths[0])).toBeNull()
    for (const changed of [{ ...hit, text: text.trim() }, { ...hit, body_sha256: ref.sha256 }, { ...hit, location: { ...hit.location, end_cp: text.length } }, { ...hit, current_ref: { ...ref, id: 'another' } }, { ...hit, warnings: [] }]) expect(() => checkedQuery({ ...value, hits: [changed] }, workspace, [ref])).toThrow()
  })
  it('keeps empty lexical index, no match and all-resource-omitted results distinct', () => {
    const ready = { ...query(), index_state: 'ready' as const, index_version: 'index_model', indexed_corpus_sha256: 'b'.repeat(64), matched_count: 0, warnings: [] }
    for (const result_state of ['no_match', 'indexed_empty'] as const) expect(checkedQuery({ ...ready, result_state }, workspace, [ref]).result_state).toBe(result_state)
    const omitted = { ...ready, result_state: 'resource_omitted', matched_count: 1, omissions: { result_limit: 0, text_byte_budget: 0, json_byte_budget: 1 }, warnings: [{ code: 'RETRIEVAL_RESOURCE_OMITTED', message: '整块遗漏', locator: null, severity: 'warning' }] }
    expect(checkedQuery(omitted, workspace, [ref]).result_state).toBe('resource_omitted')
    expect(() => checkedQuery({ ...omitted, matched_count: 2 }, workspace, [ref])).toThrow()
  })
})
