import type { TutorRunCancel, TutorRunControlView, TutorRunCreate, TutorRunView, TutorThreadCreate, TutorThreadView } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore, type DraftRecord } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue, validIdentity } from '../providers/providerSchema'

type Identity = { version: 1; workspace_id: string; command_id: string; root: string; rejection: { status: number; code: string | null } | null }
export type TutorCommand = Identity & (
  { kind: 'thread'; body: TutorThreadCreate; ack: TutorThreadView | null }
  | { kind: 'run'; body: TutorRunCreate; ack: TutorRunView | null }
  | { kind: 'cancel'; run_id: string; body: TutorRunCancel; ack: TutorRunControlView | null }
)
export type TutorCommandInput = Omit<Extract<TutorCommand, { kind: 'thread' }>, keyof Identity | 'ack'> | Omit<Extract<TutorCommand, { kind: 'run' }>, keyof Identity | 'ack'> | Omit<Extract<TutorCommand, { kind: 'cancel' }>, keyof Identity | 'ack'>
export const tutorCommandStore = new DraftStore({ name: 'learning-workbench.tutor-commands.v1' })
export function checkedTutor<T>(name: string, value: unknown): T {
  try { return checkedProvider<T>(name, value) } catch { throw new Error('问答记录不符合当前生成契约；原记录保留，未采用响应。') }
}
export function decodeTutorCommand(text: string, workspace: string): TutorCommand {
  const value: unknown = JSON.parse(text)
  if (!value || typeof value !== 'object' || !('kind' in value)) throw new Error('问答命令无法读取。')
  const item = value as Record<string, unknown>, kind = item.kind
  if (!exactObject(item, ['version', 'workspace_id', 'command_id', 'root', 'rejection', 'kind', 'body', 'ack', ...(kind === 'cancel' ? ['run_id'] : [])]) || item.version !== 1 || item.workspace_id !== workspace || !validIdentity(item.command_id) || typeof item.root !== 'string' || !item.root) throw new Error('问答原命令身份不一致。')
  if (item.rejection !== null && (!exactObject(item.rejection, ['status', 'code']) || ![400, 409, 412, 422].includes(Number(item.rejection.status)) || item.rejection.code !== null && typeof item.rejection.code !== 'string')) throw new Error('原命令拒绝记录无效。')
  if (item.ack !== null && item.rejection !== null) throw new Error('原命令不能同时有回执和拒绝。')
  if (kind === 'thread') {
    const body = checkedTutor<TutorThreadCreate>('TutorThreadCreate', item.body)
    if (item.ack !== null) { const ack = checkedTutor<TutorThreadView>('TutorThreadView', item.ack); if (!sameValue(ack.scope, body.scope) || !sameValue(ack.binding, body.binding) || ack.title !== body.title || ack.revision !== 1) throw new Error('线程原回执不匹配。') }
  } else if (kind === 'run') {
    const body = checkedTutor<TutorRunCreate>('TutorRunCreate', item.body)
    if (body.request.workspace_id !== workspace || body.request.web_search !== false || body.request.consent_id !== null) throw new Error('问答命令不能代换授权或工作区。')
    if (item.ack !== null) { const ack = checkedTutor<TutorRunView>('TutorRunView', item.ack); if (ack.run.thread_id !== body.request.thread_id || ack.thread_revision !== body.expected_thread_revision + 1) throw new Error('创建回执不匹配原线程。') }
  } else if (kind === 'cancel') {
    checkedTutor<TutorRunCancel>('TutorRunCancel', item.body)
    if (!validIdentity(item.run_id)) throw new Error('取消任务身份无效。')
    if (item.ack !== null && checkedTutor<TutorRunControlView>('TutorRunControlView', item.ack).id !== item.run_id) throw new Error('取消回执属于其他任务。')
  } else throw new Error('未知问答命令。')
  return item as TutorCommand
}
export function makeTutorCommand(workspace: string, root: string, input: TutorCommandInput): TutorCommand {
  return decodeTutorCommand(JSON.stringify({ ...input, version: 1, workspace_id: workspace, command_id: `tutor_${crypto.randomUUID()}`, root, rejection: null, ack: null }), workspace)
}
const immutable = (value: TutorCommand) => ({ ...value, rejection: null, ack: null })
export function readTutorCommand(record: DraftRecord, workspace: string): TutorCommand {
  const values = [record.text, ...record.conflicts.map(value => value.text)].map(text => decodeTutorCommand(text, workspace))
  const first = values[0]
  if (record.objectId !== first.command_id || values.some(value => !sameValue(immutable(value), immutable(first)))) throw new Error('不同原命令在本机发生冲突；全部候选保留，未自动选择。')
  const acknowledged = values.filter(value => value.ack !== null)
  if (acknowledged.some(value => !sameValue(value.ack, acknowledged[0].ack))) throw new Error('原命令存在不同回执；未猜测正确版本。')
  return acknowledged[0] ?? values.find(value => value.rejection) ?? first
}
/** Only identical immutable commands can merge. Concurrent ACK/pending copies
 * never erase a known ACK; different body/key/ACK candidates remain fail closed. */
export async function persistTutorCommand(command: TutorCommand, store = tutorCommandStore): Promise<TutorCommand> {
  let desired = decodeTutorCommand(JSON.stringify(command), command.workspace_id)
  for (let index = 0; index < 4; index++) {
    const previous = (await store.load(command.workspace_id))[command.command_id]
    if (previous) {
      const current = readTutorCommand(previous, command.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('原命令或回执不能更改。')
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!previous.conflicts.length && sameValue(current, desired)) return current
    }
    const result = await store.save(command.workspace_id, command.command_id, JSON.stringify(desired), previous?.revision ?? 0, previous?.conflicts.map(value => value.id) ?? [])
    const resultValue = readTutorCommand(result.record, command.workspace_id)
    if (!result.record.conflicts.length && sameValue(resultValue, desired)) return resultValue
  }
  throw new Error('其他页面仍在保存同一命令；候选已保留，请重新读取后重试。')
}
