import type { ContentBlock, ContentRef, DraftPublishWrite, EditDraftSnapshot, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { editClient } from '../draftEditor/editClient'
import { publicationClient } from '../draftPublication/publicationClient'
import { compareClient } from '../reader/versionCompare/compareClient'

export type EditPublicationPort = {
  session(): Promise<SessionResponse>
  draft(id: string, revision?: number): Promise<EditDraftSnapshot>
  base(ref: ContentRef): Promise<{ metadata: ContentBlock; body_markdown: string }>
  review(id: string): Promise<StoredReviewReceipt>
  publish(id: string, body: DraftPublishWrite, key: string): Promise<ContentRef>
  current(id: string): Promise<ContentRef>
}
export const editPublicationClient: EditPublicationPort = {
  session: editClient.session, draft: editClient.read,
  base: async ref => { const block = await compareClient.block(ref); return { metadata: block.block, body_markdown: block.body } },
  review: publicationClient.review, publish: publicationClient.publish, current: publicationClient.current,
}
