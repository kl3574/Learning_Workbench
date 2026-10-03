import type { ReviewCommand } from './reviewCommands'

// A failed/aborted IndexedDB write must not erase the already chosen command or
// received ACK. Session secrets are compared only in page memory, never stored.
const held = new Map<string, { command: ReviewCommand; session: string }>()
const listeners = new Set<() => void>()
let revision = 0
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeReviewMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const reviewMemoryVersion = () => revision
export function retainReviewMemory(command: ReviewCommand, session: string) {
  if (!session) throw new Error('Missing original publication session')
  held.set(command.command_id, { command: structuredClone(command), session }); changed()
}
export function pendingReviewMemory(workspace: string) {
  return [...held.values()].some(row => row.command.workspace_id === workspace)
}
export function recoverableReviewMemory(workspace: string, session: string) {
  return [...held.values()].filter(row => row.command.workspace_id === workspace && row.session === session).map(row => structuredClone(row.command))
}
export function releaseReviewMemory(id: string, session: string) {
  if (held.get(id)?.session === session) { held.delete(id); changed() }
}
export function discardReviewMemory(workspace: string) {
  for (const [id, row] of held) if (row.command.workspace_id === workspace) held.delete(id)
  changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (held.size) { event.preventDefault(); event.returnValue = '' }
})
