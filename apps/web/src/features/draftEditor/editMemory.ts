import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { sameValue } from '../providers/providerSchema'
import type { EditBuffer } from './editJournal'

// Recovery of an interrupted local save only. This page-memory vault is never
// serialized; the session secret is compared in memory and is never returned.
const held = new Map<string, { buffer: EditBuffer; session: string }>()
const listeners = new Set<() => void>()
let revision = 0
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeEditMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const editMemoryVersion = () => revision
export function retainEditMemory(buffer: EditBuffer, session: string) {
  if (!session) throw new Error('Missing memory session binding')
  held.set(buffer.id, { buffer: structuredClone(buffer), session }); changed()
}
export function pendingEditMemory(workspace: string, base: ContentRef): boolean {
  return [...held.values()].some(row => row.buffer.workspace === workspace && sameValue(row.buffer.base_ref, base))
}
export function recoverableEditMemory(workspace: string, base: ContentRef, session: string): EditBuffer | undefined {
  const row = [...held.values()].find(row => row.session === session && row.buffer.workspace === workspace && sameValue(row.buffer.base_ref, base))
  return row && structuredClone(row.buffer)
}
export function releaseEditMemory(id: string, session: string) {
  if (held.get(id)?.session === session) { held.delete(id); changed() }
}
export function discardEditMemory(workspace: string, base: ContentRef) {
  for (const [id, row] of held) if (row.buffer.workspace === workspace && sameValue(row.buffer.base_ref, base)) held.delete(id)
  changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (held.size) { event.preventDefault(); event.returnValue = '' }
})
