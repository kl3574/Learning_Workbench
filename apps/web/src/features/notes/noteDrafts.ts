import type { ContentRef, Note } from '../../../../../packages/contracts/generated/types'
import schema from '../../../../../packages/contracts/generated/schemas/Note.schema.json'
import { bytesToHex } from '@noble/hashes/utils.js'
import { sha256 } from '@noble/hashes/sha2.js'
import { DraftStore } from '../../workbench/DraftStore'
export const noteDraftStore = new DraftStore({ name: 'learning-workbench.note-drafts.v1' })
export type NoteEnvelope = { version: 1; base_ref: ContentRef | null; base_note: Note | null; candidate: Note; creation_key: string }
export const noteKey = (note: Note) => `note:${note.id}`
type Shape = { $ref?: string; type?: string; properties?: Record<string, Shape>; required?: string[]; additionalProperties?: boolean; const?: unknown; enum?: unknown[]; minimum?: number; minLength?: number; maxLength?: number; pattern?: string; default?: unknown }
function normalize(shape: Shape, value: unknown, draft = false, field = ''): unknown {
  if (shape.$ref) return normalize((schema.$defs as Record<string, Shape>)[shape.$ref.split('/').at(-1)!], value, draft, field)
  if (value === undefined && 'default' in shape) return structuredClone(shape.default)
  if (shape.const !== undefined && value !== shape.const || shape.enum && !shape.enum.includes(value)) throw new Error('字段值不符合生成契约。')
  if (shape.type === 'object') {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('草稿对象结构无效。')
    const record = value as Record<string, unknown>, properties = shape.properties ?? {}
    if (Object.keys(record).some(key => !(key in properties)) || shape.required?.some(key => !(key in record))) throw new Error('草稿包含未知字段或缺少必要字段。')
    return Object.fromEntries(Object.entries(properties).filter(([key, item]) => key in record || 'default' in item).map(([key, item]) => [key, normalize(item, record[key], draft, key)]))
  }
  if (shape.type === 'string') {
    if (typeof value !== 'string' || new TextDecoder().decode(new TextEncoder().encode(value)) !== value || shape.pattern && !new RegExp(shape.pattern).test(value)) throw new Error('草稿文本或标识无效。')
    const length = Array.from(value).length
    if (shape.maxLength !== undefined && length > shape.maxLength || shape.minLength !== undefined && length < shape.minLength && !(draft && field === 'markdown')) throw new Error('草稿文本长度不符合契约。')
    return value
  }
  if (shape.type === 'integer' && (!Number.isSafeInteger(value) || shape.minimum !== undefined && Number(value) < shape.minimum)) throw new Error('草稿修订或位置无效。')
  return value
}
function canonical(value: unknown): string {
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) return '{' + Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, child]) => `${JSON.stringify(key)}:${canonical(child)}`).join(',') + '}'
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']'
  return JSON.stringify(value)
}
function checkedNote(value: unknown, workspace: string, draft: boolean): Note {
  const note = normalize(schema as Shape, value, draft) as Note
  if (note.workspace_id !== workspace || note.anchor.ref.entity !== 'block' || note.anchor.end_codepoint < note.anchor.start_codepoint || note.anchor.end_codepoint - note.anchor.start_codepoint !== Array.from(note.anchor.exact_quote).length) throw new Error('笔记所属工作区、块引用或码点范围不匹配。')
  return note
}
export function decodeNoteEnvelope(text: string, workspace: string): NoteEnvelope {
  const value = JSON.parse(text) as NoteEnvelope
  if (!value || value.version !== 1 || ['version', 'base_ref', 'base_note', 'candidate', 'creation_key'].some(key => !(key in value)) || Object.keys(value).some(key => !['version', 'base_ref', 'base_note', 'candidate', 'creation_key'].includes(key)) || typeof value.creation_key !== 'string' || !value.creation_key || value.creation_key.length > 200 || (value.base_ref === null) !== (value.base_note === null)) throw new Error('本机笔记草稿结构不匹配，原记录保留。')
  const candidate = checkedNote(value.candidate, workspace, true)
  const base = value.base_note ? checkedNote(value.base_note, workspace, false) : null
  const ref = value.base_ref ? normalize(schema.$defs.ContentRef, value.base_ref) as ContentRef : null
  if (base && (!ref || ref.entity !== 'note' || base.id !== candidate.id || ref.id !== base.id || ref.revision !== base.revision || ref.sha256 !== bytesToHex(sha256(new TextEncoder().encode(canonical(base)))))) throw new Error('本机笔记基准引用与原始元数据哈希不符；原记录保留。')
  return { version: 1, candidate, base_note: base, base_ref: ref, creation_key: value.creation_key }
}
export const noteDirty = (value: NoteEnvelope) => !value.base_note || value.candidate.markdown !== value.base_note.markdown || JSON.stringify(value.candidate.anchor) !== JSON.stringify(value.base_note.anchor)
