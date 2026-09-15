import { request } from '../../api/client'
import type { ContentRef, JobRef, JobSnapshot, RetrievalIndexOverview, RetrievalIndexRebuildWrite, RetrievalIndexScopeStatus, RetrievalQueryView, RetrievalQueryWrite } from '../../../../../packages/contracts/generated/api-types'
import { checkedQuery, checkedStatus } from './retrievalModel'
import { checkedShape } from './retrievalSchema'
import { readBlock, type LoadedBlock } from '../reader/contentClient'
export type RetrievalPort = {
  status: (workspace: string, refs: ContentRef[]) => Promise<RetrievalIndexScopeStatus>
  query: (workspace: string, body: RetrievalQueryWrite) => Promise<RetrievalQueryView>
  rebuild: (body: RetrievalIndexRebuildWrite, key: string) => Promise<JobRef>
  job: (workspace: string, id: string) => Promise<JobSnapshot>
  cancel: (workspace: string, id: string, revision: number, key: string) => Promise<JobSnapshot>
  block: (ref: ContentRef) => Promise<LoadedBlock>
  overview: (cursor?: string) => Promise<RetrievalIndexOverview>
}
function job(value: unknown, workspace: string, id: string) {
  const result = checkedShape<JobSnapshot>('JobSnapshot', value)
  if (result.id !== id || result.workspace_id !== workspace || result.kind !== 'retrieval_index') throw new Error('返回任务与当前工作区、索引任务身份不符。')
  return result
}
export const retrievalClient: RetrievalPort = {
  status: async (workspace, refs) => checkedStatus(await request('GET /api/v1/index/status', undefined, undefined, { query: { scope_refs: JSON.stringify(refs) } }), workspace, refs),
  query: async (workspace, body) => checkedQuery(await request('POST /api/v1/retrieval/query', body), workspace, body.scope_refs),
  rebuild: async (body, key) => checkedShape<JobRef>('JobRef', await request('POST /api/v1/index/rebuild', body, { 'Idempotency-Key': key })),
  job: async (workspace, id) => job(await request('GET /api/v1/jobs/{id}', undefined, undefined, { path: { id } }), workspace, id),
  cancel: async (workspace, id, revision, key) => job(await request('POST /api/v1/jobs/{id}/cancel', { expected_revision: revision }, { 'Idempotency-Key': key }, { path: { id } }), workspace, id),
  block: readBlock,
  overview: async cursor => checkedShape<RetrievalIndexOverview>('RetrievalIndexOverview', await request('GET /api/v1/index/status', undefined, undefined, { query: { ...(cursor ? { cursor } : {}), limit: 20 } })),
}
