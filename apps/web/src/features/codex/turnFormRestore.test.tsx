import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { actor, codexSession, deferred, session, workspace } from './bootstrapTestFixtures'
import { CodexTurnPanel } from './CodexTurnPanel'
import { emptyTurnFields, persistTurnForm, readTurnForm, snapshotTurnForm } from './turnForms'
import { heldTurnForms, releaseTurnForm } from './turnMemory'
import { turnPort } from './turnTestFixtures'

const stores: DraftStore[] = []
const local = () => { const store = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() }); stores.push(store); return store }
afterEach(async () => { cleanup(); heldTurnForms(workspace).forEach(releaseTurnForm); await Promise.all(stores.splice(0).map(v => v.close())) })
const message = '  saved original α\n中文😀  '
const ref = { entity: 'block' as const, id: 'saved_original_block', revision: 2, sha256: 'a'.repeat(64) }
async function savedForm() {
 const port = turnPort(), store = local(), formStore = local()
 const original = snapshotTurnForm(workspace, actor, { ...emptyTurnFields(), session_id: codexSession().id, message, context_refs: [ref], provider_id: 'codex_local' }, null)
 await persistTurnForm(original, formStore)
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 fireEvent.click(screen.getByText('读取回合记录与权限'))
 await screen.findByText(/已读取本机记录/)
 expect((screen.getByLabelText('回合原文') as HTMLTextAreaElement).value).toBe('')
 return { port, store, formStore, original, view, before: await formStore.load(workspace) }
}
test.each(['actor', 'learner', 'independent', 'open_book', 'workspace'] as const)('restoring an unopened saved form rejects an unannounced server %s change before disclosing or branching it', async change => {
 const { port, formStore, original, before } = await savedForm()
 // Only the authoritative session response changes. No page generation event,
 // rerender, role-write notification, or second explicit refresh assists this check.
 vi.mocked(port.session).mockResolvedValue({ ...session(),
  actor_session_id: change === 'actor' ? 'actor_other' : actor,
  workspace_id: change === 'workspace' ? 'workspace_other' : workspace,
  role: change === 'learner' ? 'learner' : 'author',
  active_independent_attempt_id: change === 'independent' ? 'attempt_independent' : null,
  active_open_book_attempt_id: change === 'open_book' ? 'attempt_open' : null,
 })
 fireEvent.click(screen.getByText(/恢复原表单/))
 await waitFor(() => expect((screen.getByText('读取回合记录与权限') as HTMLButtonElement).disabled).toBe(false))
 const fields = screen.queryByLabelText('回合原文') as HTMLTextAreaElement | null
 expect.soft(fields?.value ?? '').toBe('')
 expect.soft(screen.queryByLabelText('本次精确材料引用')?.textContent ?? '[]').toBe('[]')
 expect.soft(heldTurnForms(workspace).filter(v => v.snapshot_id !== original.snapshot_id)).toEqual([])
 expect.soft(await formStore.load(workspace)).toEqual(before)
 expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
})

test('restore verifies access around local read and commit, preserves the original, and never creates a remote command', async () => {
 const { port, store, formStore, original, before } = await savedForm(), load = formStore.load.bind(formStore), order: string[] = []
 vi.mocked(port.session).mockImplementation(async () => { order.push('permission'); return session() })
 vi.spyOn(formStore, 'load').mockImplementation(async (...args) => { order.push('local_read'); return load(...args) })
 const save = formStore.save.bind(formStore)
 vi.spyOn(formStore, 'save').mockImplementation(async (...args) => { order.push('branch_commit'); return save(...args) })
 fireEvent.click(screen.getByText(/恢复原表单/))
 await screen.findByText(/原表单已核验并恢复/)
 expect(order).toEqual(['permission', 'local_read', 'permission', 'local_read', 'branch_commit', 'permission'])
 const after = await formStore.load(workspace), restored = Object.values(after).map(v => readTurnForm(v, workspace)).find(v => v.snapshot_id !== original.snapshot_id)!
 expect(after[original.snapshot_id]).toEqual(before[original.snapshot_id]); expect(Object.keys(after)).toHaveLength(2)
 expect(restored.actor_session_id).toBe(actor); expect(restored.fields).toEqual(original.fields); expect(restored.draft_id).not.toBe(original.draft_id)
 expect((screen.getByLabelText('回合原文') as HTMLTextAreaElement).value).toBe(message)
 expect(JSON.parse(screen.getByLabelText('本次精确材料引用').textContent!)).toEqual([ref])
 expect(await store.load(workspace)).toEqual({}); expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
})

test('permission change during the local read blocks restore before any new branch is created', async () => {
 const { port, formStore, before } = await savedForm(), load = formStore.load.bind(formStore)
 vi.spyOn(formStore, 'load').mockImplementationOnce(async (...args) => {
  const result = await load(...args); vi.mocked(port.session).mockResolvedValue({ ...session(), active_independent_attempt_id: 'attempt_new' }); return result
 })
 fireEvent.click(screen.getByText(/恢复原表单/)); await screen.findByText(/当前权限或原 actor 已变化/)
 expect(screen.queryByLabelText('回合原文')).toBeNull(); expect(await formStore.load(workspace)).toEqual(before)
 expect(heldTurnForms(workspace)).toEqual([]); expect(port.prepare).not.toHaveBeenCalled()
})

test('permission loss during branch persistence retains original facts but prevents protected delivery', async () => {
 const { port, formStore, original, before } = await savedForm(), save = formStore.save.bind(formStore)
 vi.spyOn(formStore, 'save').mockImplementationOnce(async (...args) => {
  const result = await save(...args); vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner' }); return result
 })
 fireEvent.click(screen.getByText(/恢复原表单/)); await screen.findByText(/当前权限或原 actor 已变化/)
 expect(screen.queryByLabelText('回合原文')).toBeNull(); expect(screen.queryByText(/原表单已核验并恢复/)).toBeNull()
 const after = await formStore.load(workspace)
 expect(after[original.snapshot_id]).toEqual(before[original.snapshot_id])
 expect(Object.values(after).map(v => readTurnForm(v, workspace).actor_session_id)).toEqual([actor, actor])
 expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
})

test.each(['changed', 'conflicting', 'missing'] as const)('a cached form list cannot restore a %s local baseline', async mode => {
 const { port, formStore, original } = await savedForm()
 if (mode === 'missing') vi.spyOn(formStore, 'load').mockResolvedValueOnce({})
 else await formStore.save(workspace, original.snapshot_id, JSON.stringify({ ...original, fields: { ...original.fields, message: 'changed after list read' } }), mode === 'conflicting' ? 0 : 1)
 const before = mode === 'missing' ? null : await formStore.load(workspace)
 fireEvent.click(screen.getByText(/恢复原表单/)); await screen.findByText(/操作结果或本机保存尚未确认/)
 expect((screen.getByLabelText('回合原文') as HTMLTextAreaElement).value).toBe('')
 expect(heldTurnForms(workspace)).toEqual([])
 if (before) expect(await formStore.load(workspace)).toEqual(before)
 expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
})

test.each(['admission', 'workspace', 'port', 'store', 'unmount'] as const)('restore in flight under a changed %s scope cannot branch or deliver the old form', async change => {
 const { port, store, formStore, view, before } = await savedForm(), pending = deferred<typeof before>()
 vi.spyOn(formStore, 'load').mockReturnValueOnce(pending.promise)
 fireEvent.click(screen.getByText(/恢复原表单/))
 await waitFor(() => expect(formStore.load).toHaveBeenCalledOnce())
 if (change === 'unmount') view.unmount()
 else view.rerender(<CodexTurnPanel workspace={change === 'workspace' ? 'workspace_other' : workspace} writeAdmitted={change !== 'admission'} port={change === 'port' ? turnPort() : port} store={store} formStore={change === 'store' ? local() : formStore} />)
 await act(async () => pending.resolve(before))
 expect(screen.queryByLabelText('回合原文')).toBeNull(); expect(heldTurnForms(workspace)).toEqual([])
 expect(await formStore.load(workspace)).toEqual(before); expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
})
