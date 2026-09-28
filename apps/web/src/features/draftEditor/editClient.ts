import type { DraftCreated, DraftCreateWrite, DraftPatched, DraftPatchWrite, EditDraftSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checkedEdit, editSnapshot } from './editSchema'
export type EditPort = {
  session(): Promise<SessionResponse>
  read(id: string, revision?: number): Promise<EditDraftSnapshot>
  create(body: DraftCreateWrite, key: string): Promise<DraftCreated>
  patch(id: string, body: DraftPatchWrite, key: string): Promise<DraftPatched>
}
export const editClient: EditPort = {
  session: async () => checkedEdit('SessionResponse', await request('GET /api/v1/session', undefined)),
  read: async (id, revision) => editSnapshot(await request('GET /api/v1/draft-edits/{id}', undefined, undefined,
    { path: { id }, ...(revision === undefined ? {} : { query: { revision } }) }), undefined, id, revision),
  create: async (body, key) => checkedEdit('DraftCreated', await request('POST /api/v1/drafts', checkedEdit('DraftCreateWrite', body), { 'Idempotency-Key': key })),
  patch: async (id, body, key) => checkedEdit('DraftPatched', await request('PATCH /api/v1/drafts/{id}', checkedEdit('DraftPatchWrite', body), { 'Idempotency-Key': key }, { path: { id } })),
}
