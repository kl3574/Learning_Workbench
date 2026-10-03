import { sameValue } from '../providers/providerSchema'
import type { Command } from './commands'
const held = new Map<string, { command: Command; session: string }>(), listeners = new Set<() => void>()
// The current JS page remembers who created each original command even after
// its journal save succeeds. A permission refresh with a different session must
// not inherit this page's old command merely because its access counter matches.
const originalSessions = new Map<string, string>()
export function bindOriginal(command: Command, session: string) {
  if (!session || originalSessions.has(command.command_id) && originalSessions.get(command.command_id) !== session) throw new Error('原命令会话绑定冲突。')
  originalSessions.set(command.command_id, session)
}
export const ownsOriginal = (command: Command, session: string) => !!session && originalSessions.get(command.command_id) === session
let revision = 0
const changed = () => { ++revision; listeners.forEach(fn => fn()) }
export const subscribe = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn) } }
export const version = () => revision
export const pending = (workspace: string) => [...held.values()].some(row => row.command.workspace_id === workspace)
export const recoverable = (workspace: string, session: string) => [...held.values()].filter(row => row.command.workspace_id === workspace && row.session === session).map(row => structuredClone(row.command))
export function retain(command: Command, session: string) {
  if (!session) throw new Error('缺少原会话身份。')
  const old = held.get(command.command_id)
  if (old && (old.session !== session || !sameValue({ ...old.command, ack: null, rejection: null }, { ...command, ack: null, rejection: null }) || old.command.ack && command.ack && !sameValue(old.command.ack, command.ack))) throw new Error('隔离内存原命令冲突。')
  held.set(command.command_id, { command: structuredClone(old?.command.ack || old?.command.rejection && !command.ack ? old.command : command), session }); changed()
}
export const release = (id: string, session: string) => { if (held.get(id)?.session === session) { held.delete(id); changed() } }
export function discard(workspace: string) { for (const [id, row] of held) if (row.command.workspace_id === workspace) held.delete(id); changed() }
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => { if (held.size) { event.preventDefault(); event.returnValue = '' } })
