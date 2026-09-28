import type { BlockProvenanceResponse, ContentRef, PageRevision, SessionResponse } from '../../../../../../packages/contracts/generated/api-types'
import { request, requestWithMetadata } from '../../../api/client'
import { checkedShape } from '../../retrieval/retrievalSchema'
import { canonical, digest } from '../../retrieval/retrievalModel'
import { verifyMetadata, type LoadedBlock } from '../contentClient'
import { sameRef } from '../target'

function checked<T>(name: string, value: unknown): T {
  try { return checkedShape<T>(name, value) }
  catch { throw new Error('修订比较响应不符合当前契约，未采用其内容。') }
}
export type ComparePort = {
  session(): Promise<SessionResponse>
  history(id: string, cursor: string | null): Promise<PageRevision>
  block(ref: ContentRef): Promise<LoadedBlock>
}
export const compareClient: ComparePort = {
  session: async () => checked('SessionResponse', await request('GET /api/v1/session', undefined)),
  history: async (id, cursor) => {
    const page = checked<PageRevision>('PageRevision', await request('GET /api/v1/objects/{id}/revisions', undefined, undefined, { path: { id }, query: { limit: 20, ...(cursor ? { cursor } : {}) } }))
    if (page.items.length > 20 || page.items.some((item, index) => item.ref.entity !== 'block' || item.ref.id !== id
      || index > 0 && item.ref.revision >= page.items[index - 1].ref.revision)
      || page.next_cursor !== null && (!page.next_cursor || page.next_cursor.length > 1024 || !page.items.length)) throw new Error('历史分页与此内容块不符，未采用其修订。')
    return page
  },
  block: async selected => {
    const ref = checked<ContentRef>('ContentRef', selected)
    if (ref.entity !== 'block') throw new Error('只比较同一内容块的精确修订。')
    const result = await requestWithMetadata('GET /api/v1/blocks/{id}', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision, include_provenance: true } })
    const projection = checked<BlockProvenanceResponse>('BlockProvenanceResponse', result.data)
    verifyMetadata(ref, projection.block, result.etag)
    // This narrow closed ContentBlock tree has only fixed ASCII keys and safe integer
    // revisions. No generic Python/JS float or arbitrary Unicode-key equivalence is claimed.
    // Missing model-default fields also fail the full persisted metadata hash.
    if (!sameRef(ref, projection.block_ref) || digest(canonical(projection.block)) !== ref.sha256) throw new Error('完整块元数据与所选修订哈希不符，未显示比较内容。')
    const body = await requestWithMetadata('GET /api/v1/blocks/{id}/body', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision } })
    if (typeof body.data !== 'string' || body.etag !== `"${projection.block.body_sha256}"`
      || digest(body.data) !== projection.block.body_sha256) throw new Error('正文 UTF-8 与所选块的哈希不符，未显示比较内容。')
    return { ...projection, body: body.data }
  },
}
