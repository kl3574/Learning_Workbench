import type { Session, ContentRef } from './model'
const prefix = 'learning-workbench'
let clientId: string
try { const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined; const restoring = navigation?.type === 'reload' || navigation?.type === 'back_forward'; clientId = (restoring ? sessionStorage.getItem(`${prefix}.ui-client`) : null) ?? crypto.randomUUID(); sessionStorage.setItem(`${prefix}.ui-client`, clientId) } catch { clientId = crypto.randomUUID() }
export const lastWorkspaceKey = `${prefix}.last-confirmed-workspace.v1`
export function readLocal(key: string): string | null { try { return localStorage.getItem(key) } catch { return null } }
export function writeLocal(key: string, value: string): boolean { try { localStorage.setItem(key, value); return true } catch { return false } }
export function removeLocal(key: string): boolean { try { localStorage.removeItem(key); return true } catch { return false } }
export const pendingKey = (workspace: string) => `${prefix}.${workspace}.pending-ui.${clientId}.v1`
export type PendingSnapshot = { key: string; session: Session; base: Session | null }
export function decodePending(text: string | null): { session: Session; base: Session | null } | null {
  try { const value = JSON.parse(text ?? 'null'); const session = value?.session ?? value; if (!session || !Number.isInteger(session.revision) || !Array.isArray(session.tabs)) return null; const base = value?.base; return { session, base: base && Number.isInteger(base.revision) && Array.isArray(base.tabs) ? base : null } } catch { return null }
}
export function pendingSnapshots(workspace: string): PendingSnapshot[] {
  const snapshots: PendingSnapshot[] = []
  try { for (let i = 0; i < localStorage.length; i++) { const key = localStorage.key(i)!; if (key.startsWith(`${prefix}.${workspace}.pending-ui.`) && key !== pendingKey(workspace)) { const value = decodePending(localStorage.getItem(key)); if (value) snapshots.push({ key, ...value }) } } } catch { /* caller continues with in-memory state */ }
  return snapshots
}
const directoryKey = (workspace: string, course: string | null, navigation: string) => `${prefix}.${workspace}.${course ?? 'empty'}.${navigation}.directory-scroll.v1`
export function readDirectory(workspace: string | null, course: string | null, navigation: string): number {
  if (!workspace) return 0
  const value = Number(readLocal(directoryKey(workspace, course, navigation)))
  return Number.isFinite(value) && value >= 0 ? value : 0
}
export function saveDirectory(workspace: string | null, course: string | null, navigation: string, offset: number): boolean {
  return !workspace || writeLocal(directoryKey(workspace, course, navigation), String(offset))
}

export type ReaderViewState = { expandedDetails: string[]; focusKey: string | null; positionKnown?: boolean }
const readerViewKey = (workspace: string, tabId: string) => `${prefix}.${workspace}.${tabId}.reader-view.v1`
export function readReaderView(workspace: string | null, tabId: string): ReaderViewState {
  if (!workspace) return { expandedDetails: [], focusKey: null }
  try { const value = JSON.parse(readLocal(readerViewKey(workspace, tabId)) ?? 'null'); return { expandedDetails: Array.isArray(value?.expandedDetails) ? value.expandedDetails.filter((key: unknown): key is string => typeof key === 'string') : [], focusKey: typeof value?.focusKey === 'string' ? value.focusKey : null, ...(value?.positionKnown === true ? { positionKnown: true } : {}) } } catch { return { expandedDetails: [], focusKey: null } }
}
export function saveReaderView(workspace: string | null, tabId: string, state: ReaderViewState): boolean {
  return !!workspace && writeLocal(readerViewKey(workspace, tabId), JSON.stringify(state))
}

const lastReadKey = (workspace: string, course: string, entry: string) => `${prefix}.${workspace}.${course}.${entry}.last-reading.v1`
export function saveLastReading(workspace: string | null, course: string, entry: string, ref: ContentRef): boolean {
  return !!workspace && writeLocal(lastReadKey(workspace, course, entry), JSON.stringify(ref))
}
export function readLastReading(workspace: string | null, course: string, entry: string): ContentRef | null {
  if (!workspace) return null
  try { return JSON.parse(readLocal(lastReadKey(workspace, course, entry)) ?? 'null') } catch { return null }
}
