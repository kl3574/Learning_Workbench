import { afterEach, describe, expect, it, vi } from 'vitest'
import { IDBFactory } from 'fake-indexeddb'
import { DraftStorageError, DraftStore } from './DraftStore'

const opened: DraftStore[] = []
function stores() {
  const factory = new IDBFactory()
  const name = 'draft-test-' + crypto.randomUUID()
  const first = new DraftStore({ factory, name }); const second = new DraftStore({ factory, name })
  opened.push(first, second)
  return { first, second, factory, name }
}
afterEach(async () => { await Promise.all(opened.splice(0).map(store => store.close())); vi.restoreAllMocks() })
describe('transactional browser drafts', () => {
  it('concurrent different-object writes never replace each other and survive a new reader', async () => {
    const { first, second, factory, name } = stores()
    await Promise.all([first.save('workspace_a', 'object_a', 'A', 0), second.save('workspace_a', 'object_b', 'B', 0)])
    const reload = new DraftStore({ factory, name }); opened.push(reload)
    const records = await reload.load('workspace_a')
    expect(records.object_a.text).toBe('A'); expect(records.object_b.text).toBe('B')
    expect(records.object_a.revision).toBe(1); expect(records.object_b.revision).toBe(1)
  })
  it('same-object concurrent CAS commits one winner and durably retains the rejected candidate', async () => {
    const { first, second } = stores()
    const results = await Promise.all([first.save('workspace', 'object', 'A', 0), second.save('workspace', 'object', 'B', 0)])
    expect(results.map(result => result.kind).sort()).toEqual(['conflict', 'saved'])
    const record = (await first.load('workspace')).object
    expect(record.revision).toBe(1)
    expect(new Set([record.text, ...record.conflicts.map(conflict => conflict.text)])).toEqual(new Set(['A', 'B']))
    expect(record.conflicts[0]).toMatchObject({ expectedRevision: 0, actualRevision: 1 })
  })
  it('retains conflicting candidates through later edits until explicit conflict resolution', async () => {
    const { first, second } = stores()
    await first.save('workspace', 'object', 'first', 0)
    const conflict = await second.save('workspace', 'object', 'candidate', 0)
    expect(conflict.kind).toBe('conflict')
    await first.save('workspace', 'object', 'next', 1)
    let record = (await second.load('workspace')).object
    expect(record.text).toBe('next'); expect(record.conflicts[0].text).toBe('candidate')
    await second.save('workspace', 'object', 'candidate', 2, [record.conflicts[0].id])
    record = (await first.load('workspace')).object
    expect(record.text).toBe('candidate'); expect(record.revision).toBe(3); expect(record.conflicts).toEqual([])
  })
  it('does not duplicate an identical retried conflict or remove unseen conflict candidates', async () => {
    const { first, second } = stores()
    await first.save('workspace', 'object', 'winner', 0)
    const one = await second.save('workspace', 'object', 'one', 0)
    await second.save('workspace', 'object', 'one', 0)
    await second.save('workspace', 'object', 'two', 0)
    expect((await first.load('workspace')).object.conflicts).toHaveLength(2)
    if (one.kind !== 'conflict') throw new Error('Expected a conflict')
    await first.save('workspace', 'object', 'one', 1, [one.conflict.id])
    expect((await second.load('workspace')).object.conflicts.map(conflict => conflict.text)).toEqual(['two'])
  })
  it('separates workspaces and allows an explicitly saved empty draft', async () => {
    const { first } = stores()
    await first.save('a', 'same_object', 'A', 0); await first.save('b', 'same_object', 'B', 0)
    expect((await first.load('a')).same_object.text).toBe('A')
    expect((await first.load('b')).same_object.text).toBe('B')
    await first.save('a', 'same_object', '', 1)
    expect((await first.load('a')).same_object.text).toBe('')
    expect(await first.load('absent')).toEqual({})
  })
  it('does not claim saved when opening storage fails and permits retry', async () => {
    const { first, factory } = stores()
    vi.spyOn(factory, 'open').mockImplementationOnce(() => { throw new DOMException('synthetic failure', 'SecurityError') })
    await expect(first.save('workspace', 'object', 'keep in memory', 0)).rejects.toMatchObject({ code: 'OPEN_FAILED' })
    expect((await first.save('workspace', 'object', 'retry unchanged text', 0)).kind).toBe('saved')
  })
  it('does not commit or claim success on quota/transaction failure', async () => {
    const { first, factory, name } = stores()
    await first.save('workspace', 'object', 'saved', 0)
    const database = await new Promise<IDBDatabase>((resolve, reject) => { const request = factory.open(name); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    const prototype: IDBObjectStore = Object.getPrototypeOf(database.transaction('drafts').objectStore('drafts'))
    const original = prototype.put
    vi.spyOn(prototype, 'put').mockImplementation(function (this: IDBObjectStore, ...args: Parameters<IDBObjectStore['put']>) {
      const request = original.apply(this, args)
      this.transaction.abort()
      return request
    })
    await expect(first.save('workspace', 'object', 'not durable', 1)).rejects.toBeInstanceOf(DraftStorageError)
    expect((await first.load('workspace')).object.text).toBe('saved')
    database.close()
  })
  it('reports quota exhaustion without uncaught events or replacing the committed text', async () => {
    const { first, factory, name } = stores()
    await first.save('workspace', 'object', 'saved', 0)
    const database = await new Promise<IDBDatabase>((resolve, reject) => { const request = factory.open(name); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    const prototype: IDBObjectStore = Object.getPrototypeOf(database.transaction('drafts').objectStore('drafts'))
    vi.spyOn(prototype, 'put').mockImplementationOnce(() => { throw new DOMException('synthetic quota failure', 'QuotaExceededError') })
    await expect(first.save('workspace', 'object', 'keep in memory', 1)).rejects.toMatchObject({ code: 'QUOTA_EXCEEDED' })
    expect((await first.load('workspace')).object.text).toBe('saved')
    expect((await first.save('workspace', 'object', 'retry after freeing storage', 1)).kind).toBe('saved')
    database.close()
  })
  it('notifies other tabs only for the subscribed workspace and never broadcasts draft text', async () => {
    const { first, second } = stores()
    const broadcasts = vi.spyOn(BroadcastChannel.prototype, 'postMessage')
    const received: string[] = []
    const unsubscribe = second.subscribe('workspace', () => received.push('changed'))
    await first.save('other', 'object', 'private other text', 0)
    await new Promise(resolve => setTimeout(resolve, 20)); expect(received).toEqual([])
    await first.save('workspace', 'object', 'private text', 0)
    await vi.waitFor(() => expect(received).toEqual(['changed']))
    expect(JSON.stringify(broadcasts.mock.calls)).not.toContain('private text')
    expect(JSON.stringify(broadcasts.mock.calls)).not.toContain('private other text')
    unsubscribe()
    await first.save('workspace', 'object', 'edited', 1)
    await new Promise(resolve => setTimeout(resolve, 20)); expect(received).toEqual(['changed'])
  })
})
