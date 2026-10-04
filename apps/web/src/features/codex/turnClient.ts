import type { JobRef, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexCurrentSessionView, CodexTurnControlView, CodexTurnPage, CodexTurnPreparationView, CodexTurnPrepareWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import schemas from '../../../../../packages/contracts/generated/codex-turn-schemas.json'
import { request } from '../../api/client'
import { checkedProvider, sameValue, validIdentity } from '../providers/providerSchema'
import { bootstrapClient } from './bootstrapClient'

type TurnWire = {
 CodexTurnPrepareWrite: CodexTurnPrepareWrite
 CodexTurnPreparationView: CodexTurnPreparationView
 CodexTurnControlView: CodexTurnControlView
 CodexTurnPage: CodexTurnPage
}
const invalid = (): never => { throw new Error('回合记录不符合当前契约，原命令保留。') }
function distinct(values: unknown[]) { if (new Set(values.map(v => JSON.stringify(v))).size !== values.length) invalid() }
function utc(value: string) {
 const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z$/.exec(value)
 if (!match || value.startsWith('0000')) return invalid()
 const ms = Date.parse(match[1] + 'Z')
 if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0, 19) !== match[1]) return invalid()
 return BigInt(ms) * 1000n + BigInt((match[2] ?? '').slice(0, 6).padEnd(6, '0'))
}
const refs = (value: CodexTurnPrepareWrite['context_refs']) => distinct(value.map(r => [r.entity, r.id, r.revision]))
function preparation(value: CodexTurnPreparationView) {
 const r = value.request, s = value.summary
 utc(value.created_at); refs(r.context_refs)
 if (value.session_revision <= r.expected_session_revision || !sameValue(s.tools, r.tools)
  || value.consent_id !== null && value.proposal_id === null || s.history_turn_ids.includes(value.turn_id)
  || s.character_count < Array.from(r.message).length) invalid()
 distinct(s.history_turn_ids); distinct(s.warnings.map(w => [w.code, w.message, w.locator, w.severity]))
 distinct(s.materials.map(m => [m.ref.entity, m.ref.id, m.ref.revision]))
 let after = 0
 for (const material of s.materials) {
  if (material.ref.entity !== 'block') invalid()
  const index = r.context_refs.findIndex((ref, index) => index >= after && sameValue(ref, material.ref))
  if (index < 0) invalid(); after = index + 1
 }
}
function control(value: CodexTurnControlView) {
 distinct(value.approval_ids)
 if (!sameValue(value.approval_ids, value.approval_controls.map(a => a.id))) invalid()
 for (const a of value.approval_controls) if (a.decision !== 'pending' && a.revision < 2) invalid()
 if (value.consent_control && value.consent_control.revision !== (value.consent_control.status === 'revoked' ? 2 : 1)) invalid()
 const terminal = value.execution === 'terminal', created = utc(value.created_at)
 if (terminal !== (value.outcome !== null) || terminal !== (value.finished_at !== null)
  || value.execution === 'active' && value.started_at === null
  || value.execution === 'not_started' && value.started_at !== null) invalid()
 const started = value.started_at === null ? null : utc(value.started_at)
 const finished = value.finished_at === null ? null : utc(value.finished_at)
 if (started !== null && started < created || finished !== null && finished < created
  || started !== null && finished !== null && finished < started) invalid()
 if (terminal) {
  const expected = value.outcome === 'completed' || value.outcome === 'cancelled' ? value.outcome : 'failed'
  if (value.job.status !== expected) invalid()
 } else if (['completed', 'failed', 'cancelled'].includes(value.job.status)) invalid()
 if (value.outcome === 'completed' && (started === null || value.error_code !== null)
  || value.manifest_id !== null && !terminal) invalid()
}
/** Closed wire plus local relationships only; server-owned history/proof grants no client authority. */
export function checkedTurn<N extends keyof TurnWire>(name: N, raw: unknown): TurnWire[N] {
 try {
  const value = checkedProvider<TurnWire[N]>(name, raw, schemas.schemas)
  if (name === 'CodexTurnPrepareWrite') refs((value as CodexTurnPrepareWrite).context_refs)
  if (name === 'CodexTurnPreparationView') preparation(value as CodexTurnPreparationView)
  if (name === 'CodexTurnControlView') control(value as CodexTurnControlView)
  if (name === 'CodexTurnPage') {
   const page = value as CodexTurnPage
   distinct(page.items.map(v => v.id)); if (new Set(page.items.map(v => v.session_id)).size > 1) invalid()
   page.items.forEach(control)
  }
  return value
 } catch { return invalid() }
}
function identity(id: string) { if (!validIdentity(id)) invalid(); return id }
export type TurnPageQuery = { cursor?: string; limit?: number }
export type TurnPort = {
 session(): Promise<SessionResponse>
 current(id: string): Promise<CodexCurrentSessionView>
 prepare(id: string, body: CodexTurnPrepareWrite, key: string): Promise<CodexTurnPreparationView>
 preparation(id: string): Promise<CodexTurnPreparationView>
 control(id: string): Promise<CodexTurnControlView>
 turns(id: string, query?: TurnPageQuery): Promise<CodexTurnPage>
 cancel(jobId: string, expectedRevision: number, key: string): Promise<JobRef>
}
export const turnClient: TurnPort = {
 session: bootstrapClient.session,
 current: async id => {
  const value = await bootstrapClient.read(identity(id))
  if (value.id !== id) invalid(); return value
 },
 prepare: async (id, body, key) => {
  const checked = checkedTurn('CodexTurnPrepareWrite', body)
  const value = checkedTurn('CodexTurnPreparationView', await request('POST /api/v1/codex/sessions/{id}/turn-preparations', checked, { 'Idempotency-Key': key }, { path: { id: identity(id) } }))
  if (value.session_id !== id || !sameValue(value.request, checked)) invalid()
  return value
 },
 preparation: async id => {
  const value = checkedTurn('CodexTurnPreparationView', await request('GET /api/v1/codex/turn-preparations/{id}', undefined, undefined, { path: { id: identity(id) } }))
  if (value.id !== id) invalid(); return value
 },
 control: async id => {
  const value = checkedTurn('CodexTurnControlView', await request('GET /api/v1/codex/turns/{id}', undefined, undefined, { path: { id: identity(id) } }))
  if (value.id !== id) invalid(); return value
 },
 turns: async (id, query = {}) => {
  if (Object.keys(query).some(k => !['cursor', 'limit'].includes(k))
   || query.limit !== undefined && (!Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 100)
   || query.cursor !== undefined && (typeof query.cursor !== 'string' || !query.cursor.trim())) invalid()
  const value = checkedTurn('CodexTurnPage', await request('GET /api/v1/codex/sessions/{id}/turns', undefined, undefined, { path: { id: identity(id) }, query }))
  if (value.items.some(v => v.session_id !== id)) invalid(); return value
 },
 cancel: async (jobId, expectedRevision, key) => {
  const body = checkedProvider<{ expected_revision: number }>('JobCancelRequest', { expected_revision: expectedRevision })
  const value = checkedProvider<JobRef>('JobRef', await request('POST /api/v1/jobs/{id}/cancel', body, { 'Idempotency-Key': key }, { path: { id: identity(jobId) } }))
  if (value.id !== jobId) invalid(); return value
 },
}
