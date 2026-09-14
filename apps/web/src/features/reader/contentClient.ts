import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { request, requestWithMetadata } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import { sameRef } from './target'
export function verifyMetadata(ref: ContentRef, value: { id: string; revision: number; entity?: string }, etag: string | null) {
  if (value.id !== ref.id || value.revision !== ref.revision || value.entity !== ref.entity || etag !== `"${ref.sha256}"`) throw new Error('对象修订或元数据哈希不符；保留原引用，未加载其他版本。')
}
export async function readCourse(ref: ContentRef) {
  const result = await requestWithMetadata('GET /api/v1/courses/{id}', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision } })
  verifyMetadata(ref, result.data, result.etag); return result.data
}
export async function readLesson(ref: ContentRef) {
  const result = await requestWithMetadata('GET /api/v1/lessons/{id}', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision } })
  verifyMetadata(ref, result.data, result.etag); return result.data
}
export async function readBlock(ref: ContentRef) {
  const result = await requestWithMetadata('GET /api/v1/blocks/{id}', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision, include_provenance: true } })
  if (!('block' in result.data)) throw new Error('服务端未返回请求的来源投影。')
  const projection = result.data
  verifyMetadata(ref, projection.block, result.etag)
  if (!sameRef(ref, projection.block_ref)) throw new Error('来源投影未绑定请求中的准确内容块。')
  const body = await requestWithMetadata('GET /api/v1/blocks/{id}/body', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision } })
  if (body.etag !== `"${projection.block.body_sha256}"` || bytesToHex(sha256(new TextEncoder().encode(body.data))) !== projection.block.body_sha256) throw new Error('正文哈希校验失败；未显示损坏正文。')
  return { ...projection, body: body.data }
}
export type LoadedBlock = Awaited<ReturnType<typeof readBlock>>
export const readProgress = (courseId: string) => request('GET /api/v1/learning/progress', undefined, undefined, { query: { course_id: courseId } })
