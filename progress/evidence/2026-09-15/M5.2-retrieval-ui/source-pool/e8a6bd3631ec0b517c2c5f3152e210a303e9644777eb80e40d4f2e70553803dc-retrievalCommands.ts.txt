import { DraftStore, type DraftRecord } from '../../workbench/DraftStore'
import type { ContentRef, JobRef, JobSnapshot, RetrievalIndexRebuildWrite } from '../../../../../packages/contracts/generated/api-types'
import { canonical, normalizedRefs } from './retrievalModel'
import { checkedShape } from './retrievalSchema'
import { validId } from '../assessment/target'
type Base = { version: 1; workspace: string; command_id: string; scope_refs: ContentRef[]; rejected: boolean }
export type RetrievalCommand = Base & (
  { kind: 'rebuild'; body: RetrievalIndexRebuildWrite; ack: JobRef | null }
  | { kind: 'cancel'; job_id: string; body: { expected_revision: number }; ack: JobSnapshot | null })
export const retrievalCommandStore = new DraftStore({ name: 'learning-workbench.retrieval-commands.v1' })
export function decodeCommand(raw: string, workspace: string): RetrievalCommand {
  const value = JSON.parse(raw) as RetrievalCommand
  const keys = ['version', 'workspace', 'command_id', 'scope_refs', 'rejected', 'kind', 'body', 'ack', ...(value?.kind === 'cancel' ? ['job_id'] : [])]
  if (!value || value.workspace !== workspace || value.version !== 1 || !validId(value.command_id) || typeof value.rejected !== 'boolean' || Object.keys(value).length !== keys.length || Object.keys(value).some(key => !keys.includes(key))) throw new Error('本机索引命令身份无效；原记录保留。')
  const refs = normalizedRefs(value.scope_refs)
  if (canonical(refs) !== canonical(value.scope_refs)) throw new Error('本机索引命令的范围不是冻结的完整引用。')
  if (value.kind === 'rebuild') {
    const body = checkedShape<RetrievalIndexRebuildWrite>('RetrievalIndexRebuildWrite', value.body)
    if (body.provider_id !== null || body.consent_id !== null || canonical(body.scope_refs) !== canonical(refs)) throw new Error('本机重建命令的范围或本地能力边界不符。')
    if (value.ack !== null) { const ack = checkedShape<JobRef>('JobRef', value.ack); if (ack.status !== 'queued') throw new Error('原始重建回执不是已受理排队事实。') }
  } else if (value.kind === 'cancel') {
    checkedShape('JobCancelRequest', value.body)
    if (!validId(value.job_id)) throw new Error('本机取消命令缺少原任务身份。')
    if (value.ack !== null) {
      const ack = checkedShape<JobSnapshot>('JobSnapshot', value.ack)
      if (ack.id !== value.job_id || ack.workspace_id !== workspace || ack.kind !== 'retrieval_index' || ack.status !== 'cancelled' || ack.revision !== value.body.expected_revision + 1) throw new Error('取消回执与原命令不符。')
    }
  } else throw new Error('未知本机索引命令类型。')
  return value
}
function checkedRecord(workspace: string, key: string, record: DraftRecord): RetrievalCommand {
  const value = decodeCommand(record.text, workspace)
  if (record.objectId !== key || value.command_id !== key) throw new Error('命令存储键与冻结身份不符。')
  // Two tabs may persist the same immutable command or original ACK. Only full
  // semantic equality is redundant; different bodies, keys or ACKs stay blocked.
  for (const conflict of record.conflicts) {
    if (canonical(decodeCommand(conflict.text, workspace)) !== canonical(value)) throw new Error('本机索引命令存在不一致候选，请保留原记录；未自动覆盖。')
  }
  return value
}
export async function readCommands(workspace: string, store = retrievalCommandStore): Promise<RetrievalCommand[]> {
  const records = await store.load(workspace)
  return Object.entries(records).map(([key, record]) => checkedRecord(workspace, key, record))
}
export async function persistCommand(value: RetrievalCommand, store = retrievalCommandStore): Promise<void> {
  const text = JSON.stringify(decodeCommand(JSON.stringify(value), value.workspace))
  const previous = (await store.load(value.workspace))[value.command_id]
  if (previous) {
    const old = checkedRecord(value.workspace, value.command_id, previous)
    if (canonical({ ...old, ack: null, rejected: false }) !== canonical({ ...value, ack: null, rejected: false })
        || old.ack !== null && canonical(old.ack) !== canonical(value.ack)
        || old.rejected && !value.rejected) throw new Error('原命令已存在不同事实，未覆盖。')
    if (canonical(old) === canonical(value)) return
  }
  // Resolve only the exact duplicate candidates just checked, under the same
  // revision CAS. Newly arriving or unequal candidates are never swept away.
  const result = await store.save(value.workspace, value.command_id, text, previous?.revision ?? 0, previous?.conflicts.map(conflict => conflict.id))
  if (canonical(checkedRecord(value.workspace, value.command_id, result.record)) !== canonical(value)) throw new Error('本机索引命令未安全保存；未开始新的发送。')
}
