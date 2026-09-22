/** Local, unsent UI drafts. IndexedDB is not authoritative learning evidence. */
export interface DraftConflict {
  id: string
  expectedRevision: number
  actualRevision: number
  text: string
  createdAt: string
}
export interface DraftRecord {
  objectId: string
  revision: number
  text: string
  updatedAt: string
  conflicts: DraftConflict[]
}
interface StoredDraft extends DraftRecord { workspaceId: string }
export type DraftSaveResult = { kind: 'saved'; record: DraftRecord } | { kind: 'conflict'; record: DraftRecord; conflict: DraftConflict }
export type DraftWriteGuard = { allowed: () => boolean; signal: AbortSignal }
export type DraftStorageCode = 'UNAVAILABLE' | 'OPEN_FAILED' | 'BLOCKED' | 'READ_FAILED' | 'WRITE_FAILED' | 'QUOTA_EXCEEDED' | 'INVALID_INPUT' | 'ACCESS_CHANGED'
export class DraftStorageError extends Error {
  readonly code: DraftStorageCode
  constructor(code: DraftStorageCode) {
    const messages: Record<DraftStorageCode, string> = {
      UNAVAILABLE: '浏览器草稿存储不可用，请保留当前文字并重试。',
      OPEN_FAILED: '无法打开浏览器草稿存储，当前文字尚未保存。',
      BLOCKED: '其他窗口阻止草稿存储升级，请关闭旧窗口后重试。',
      READ_FAILED: '无法读取已存草稿，暂不覆盖本机已有记录。',
      WRITE_FAILED: '草稿写入失败，当前文字尚未保存，请重试。',
      QUOTA_EXCEEDED: '浏览器存储空间不足，当前文字尚未保存，请保留文字后重试。',
      INVALID_INPUT: '草稿对象或基准修订无效，当前文字尚未保存。',
      ACCESS_CHANGED: '当前权限或工作区已变化，未写入这次草稿。',
    }
    super(messages[code]); this.name = 'DraftStorageError'; this.code = code
  }
}
export function assertDraftWriteAllowed(guard?: DraftWriteGuard): void {
  if (guard && (guard.signal.aborted || !guard.allowed())) throw new DraftStorageError('ACCESS_CHANGED')
}
function storageError(code: DraftStorageCode, cause?: unknown) {
  return new DraftStorageError(cause instanceof DOMException && cause.name === 'QuotaExceededError' ? 'QUOTA_EXCEEDED' : code)
}
function publicRecord(value: StoredDraft): DraftRecord {
  return { objectId: value.objectId, revision: value.revision, text: value.text, updatedAt: value.updatedAt, conflicts: structuredClone(value.conflicts) }
}
function validRecord(value: StoredDraft | undefined): value is StoredDraft {
  return !!value && typeof value.workspaceId === 'string' && typeof value.objectId === 'string'
    && Number.isSafeInteger(value.revision) && value.revision >= 1 && typeof value.text === 'string'
    && typeof value.updatedAt === 'string' && Array.isArray(value.conflicts)
    && value.conflicts.every(conflict => conflict !== null && typeof conflict === 'object' && typeof conflict.id === 'string' && typeof conflict.text === 'string'
      && typeof conflict.createdAt === 'string' && Number.isSafeInteger(conflict.expectedRevision) && Number.isSafeInteger(conflict.actualRevision))
}
export class DraftStore {
  private databasePromise: Promise<IDBDatabase> | null = null
  private readonly listeners = new Map<string, Set<() => void>>()
  private channel: BroadcastChannel | null = null
  private readonly instanceId = crypto.randomUUID()
  private readonly name: string
  private readonly factory: IDBFactory | undefined
  constructor(options: { name?: string; factory?: IDBFactory } = {}) {
    this.name = options.name ?? 'learning-workbench.unsent-drafts.v1'
    this.factory = options.factory ?? globalThis.indexedDB
  }
  private open(): Promise<IDBDatabase> {
    if (!this.factory) return Promise.reject(new DraftStorageError('UNAVAILABLE'))
    if (this.databasePromise) return this.databasePromise
    const factory = this.factory
    this.databasePromise = new Promise<IDBDatabase>((resolve, reject) => {
      let request: IDBOpenDBRequest
      let failed = false
      try { request = factory.open(this.name, 1) } catch (error) { reject(storageError('OPEN_FAILED', error)); return }
      request.onupgradeneeded = () => {
        const store = request.result.createObjectStore('drafts', { keyPath: ['workspaceId', 'objectId'] })
        store.createIndex('workspaceId', 'workspaceId')
      }
      request.onerror = () => { failed = true; reject(storageError('OPEN_FAILED', request.error)) }
      request.onblocked = () => { failed = true; reject(new DraftStorageError('BLOCKED')) }
      request.onsuccess = () => {
        if (failed) { request.result.close(); return }
        const database = request.result
        database.onversionchange = () => { database.close(); this.databasePromise = null }
        resolve(database)
      }
    }).catch(error => { this.databasePromise = null; throw error })
    return this.databasePromise
  }
  async load(workspaceId: string): Promise<Record<string, DraftRecord>> {
    if (!workspaceId) throw new DraftStorageError('INVALID_INPUT')
    const database = await this.open()
    return new Promise((resolve, reject) => {
      let transaction: IDBTransaction
      try { transaction = database.transaction('drafts', 'readonly') } catch (error) { reject(storageError('READ_FAILED', error)); return }
      const request = transaction.objectStore('drafts').index('workspaceId').getAll(workspaceId)
      let records: Record<string, DraftRecord> = {}
      let invalid = false
      request.onsuccess = () => {
        const values: StoredDraft[] = request.result
        if (values.some(value => !validRecord(value))) { invalid = true; transaction.abort(); return }
        records = Object.fromEntries(values.map(value => [value.objectId, publicRecord(value)]))
      }
      transaction.oncomplete = () => resolve(records)
      transaction.onabort = () => reject(storageError('READ_FAILED', invalid ? undefined : transaction.error))
      transaction.onerror = () => { /* onabort is the only failure settlement */ }
    })
  }
  async save(workspaceId: string, objectId: string, text: string, expectedRevision: number, resolvedConflictIds: readonly string[] = [], guard?: DraftWriteGuard): Promise<DraftSaveResult> {
    if (!workspaceId || !objectId || typeof text !== 'string' || !Number.isSafeInteger(expectedRevision) || expectedRevision < 0 || expectedRevision === Number.MAX_SAFE_INTEGER) throw new DraftStorageError('INVALID_INPUT')
    assertDraftWriteAllowed(guard)
    const database = await this.open()
    assertDraftWriteAllowed(guard)
    const result = await new Promise<DraftSaveResult>((resolve, reject) => {
      let transaction: IDBTransaction
      try { transaction = database.transaction('drafts', 'readwrite') } catch (error) { reject(storageError('WRITE_FAILED', error)); return }
      const store = transaction.objectStore('drafts')
      const request = store.get([workspaceId, objectId])
      let outcome: DraftSaveResult | null = null
      let invalid = false
      let writeError: DraftStorageError | null = null
      let committing = false
      const abortWrite = (error: DraftStorageError) => {
        if (committing) return
        try { transaction.abort(); writeError = error }
        catch { /* Already finishing: only the actual terminal event settles the write. */ }
      }
      const revoked = () => abortWrite(new DraftStorageError('ACCESS_CHANGED'))
      const cleanup = () => guard?.signal.removeEventListener('abort', revoked)
      guard?.signal.addEventListener('abort', revoked, { once: true })
      const put = (value: StoredDraft) => {
        assertDraftWriteAllowed(guard)
        const written = store.put(value)
        if (guard) written.onsuccess = () => {
          try {
            assertDraftWriteAllowed(guard)
            // The final access check and explicit commit share one synchronous
            // callback. Revocation after this admission cannot undo a committing
            // transaction. Only oncomplete below establishes persistence.
            transaction.commit()
            committing = true
            cleanup()
          } catch (error) { abortWrite(error instanceof DraftStorageError ? error : storageError('WRITE_FAILED', error)) }
        }
      }
      request.onsuccess = () => {
        try {
        assertDraftWriteAllowed(guard)
        const current: StoredDraft | undefined = request.result
        if (current !== undefined && !validRecord(current)) { invalid = true; transaction.abort(); return }
        const revision = current?.revision ?? 0
        const now = new Date().toISOString()
        if (revision !== expectedRevision) {
          // A conflicting candidate is itself persisted in this same transaction.
          // It must remain available after a browser reload or another tab's save.
          if (!current) { invalid = true; transaction.abort(); return }
          const duplicate = current.conflicts.find(conflict => conflict.expectedRevision === expectedRevision && conflict.text === text)
          const conflict: DraftConflict = duplicate ?? { id: crypto.randomUUID(), expectedRevision, actualRevision: revision, text, createdAt: now }
          const next: StoredDraft = { ...current, conflicts: duplicate ? current.conflicts : [...current.conflicts, conflict] }
          put(next)
          outcome = { kind: 'conflict', record: publicRecord(next), conflict: structuredClone(conflict) }
        } else {
          const next: StoredDraft = { workspaceId, objectId, revision: revision + 1, text, updatedAt: now,
            conflicts: (current?.conflicts ?? []).filter(conflict => !resolvedConflictIds.includes(conflict.id)) }
          put(next)
          outcome = { kind: 'saved', record: publicRecord(next) }
        }
        } catch (error) { abortWrite(error instanceof DraftStorageError ? error : storageError('WRITE_FAILED', error)) }
      }
      transaction.oncomplete = () => { cleanup(); outcome ? resolve(outcome) : reject(new DraftStorageError('WRITE_FAILED')) }
      transaction.onabort = () => { cleanup(); reject(writeError ?? storageError(invalid ? 'READ_FAILED' : 'WRITE_FAILED', transaction.error)) }
      transaction.onerror = () => { /* do not report success before transaction commit */ }
      if (guard?.signal.aborted) revoked()
    })
    this.notify(workspaceId)
    return result
  }
  private emit(workspaceId: string) { for (const listener of this.listeners.get(workspaceId) ?? []) queueMicrotask(listener) }
  private notify(workspaceId: string) {
    this.emit(workspaceId)
    // Notification is best effort; a failure cannot undo an already committed draft.
    // Messages contain workspace identity only, never draft text or conflicts.
    try {
      const sender = new BroadcastChannel(this.name)
      sender.postMessage({ workspaceId, source: this.instanceId }); sender.close()
    } catch { /* browsers without BroadcastChannel can still reload saved drafts */ }
  }
  subscribe(workspaceId: string, listener: () => void): () => void {
    let listeners = this.listeners.get(workspaceId)
    if (!listeners) { listeners = new Set(); this.listeners.set(workspaceId, listeners) }
    listeners.add(listener)
    if (!this.channel) {
      try {
        this.channel = new BroadcastChannel(this.name)
        this.channel.onmessage = event => {
          if (event.data?.source !== this.instanceId && typeof event.data?.workspaceId === 'string') this.emit(event.data.workspaceId)
        }
      } catch { /* persistence remains usable; callers can refresh on focus/reconnect */ }
    }
    return () => {
      this.listeners.get(workspaceId)?.delete(listener)
      if (!this.listeners.get(workspaceId)?.size) this.listeners.delete(workspaceId)
      if (!this.listeners.size) { this.channel?.close(); this.channel = null }
    }
  }
  async close(): Promise<void> {
    this.channel?.close(); this.channel = null; this.listeners.clear()
    const pending = this.databasePromise; this.databasePromise = null
    if (pending) (await pending).close()
  }
}
const defaultStore = new DraftStore()
export const load = (workspaceId: string) => defaultStore.load(workspaceId)
export const save = (workspaceId: string, objectId: string, text: string, expectedRevision: number, resolvedConflictIds?: readonly string[]) => defaultStore.save(workspaceId, objectId, text, expectedRevision, resolvedConflictIds)
export const subscribe = (workspaceId: string, listener: () => void) => defaultStore.subscribe(workspaceId, listener)
