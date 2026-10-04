import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { ApiError } from '../../api/client'
import { deferred, session } from './bootstrapTestFixtures'
import { artifactAck, artifactActor, artifactData, artifactImport, artifactManifest, artifactWorkspace } from './artifactFixtures'
import type { ArtifactPort } from './artifactClient'
import { CodexArtifactsPanel } from './CodexArtifactsPanel'
import { heldArtifactCommands, heldArtifactForms, releaseArtifactCommand, releaseArtifactForm } from './artifactMemory'
import { persistArtifactForm, snapshotArtifactForm } from './artifactForms'
import { readArtifactCommand } from './artifactCommands'
const stores: DraftStore[] = []
const local = () => { const s = new DraftStore({ name: `artifact-panel-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(s); return s }
const auth = () => ({ ...session(), workspace_id: artifactWorkspace, actor_session_id: artifactActor })
const port = (): ArtifactPort => ({ session: vi.fn(async () => auth()), manifest: vi.fn(async () => artifactManifest()), import: vi.fn(async () => artifactAck), imports: vi.fn(async () => artifactImport()), download: vi.fn(async () => new Blob([artifactData])) })
afterEach(async () => { cleanup(); heldArtifactCommands(artifactWorkspace).forEach(releaseArtifactCommand); heldArtifactForms(artifactWorkspace).forEach(releaseArtifactForm); await Promise.all(stores.splice(0).map(s => s.close())); vi.unstubAllGlobals(); vi.restoreAllMocks() })
const refresh = async () => { fireEvent.click(screen.getByText('读取产物记录与权限')); await screen.findByText(/产物本机记录已读取/); await waitFor(() => expect((screen.getByText('读取产物记录与权限') as HTMLButtonElement).disabled).toBe(false)) }
async function choose() {
 await refresh()
 fireEvent.change(screen.getByLabelText('产物来源 session ID'), { target: { value: 'codex_session_synthetic' } })
 fireEvent.change(screen.getByLabelText('产物来源 turn ID'), { target: { value: 'turn_artifact_synthetic' } })
 fireEvent.click(screen.getByText('独立读取当前产物清单')); await screen.findByLabelText('当前产物清单 GET')
 fireEvent.click(screen.getByText('使用此清单建立新选择'))
 fireEvent.click(screen.getByLabelText('选择产物 成果/说明.md'))
 await waitFor(() => expect((screen.getByText('明确新建所选产物的回导预览') as HTMLButtonElement).disabled).toBe(false))
}
test('shows failed source and all three NOT_RUN, persists explicit selection before POST, separates current from original ACK', async () => {
 const p = port(), store = local(), forms = local()
 vi.mocked(p.import).mockImplementation(async (target, body, key) => {
  const c = readArtifactCommand((await store.load(artifactWorkspace))[key], artifactWorkspace)
  expect(c.actor_session_id).toBe(artifactActor); expect(c.target_id).toBe(target); expect(c.body).toEqual(body); expect(c.basis).toEqual(artifactManifest()); expect(c.ack).toBeNull()
  return artifactAck
 })
 render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 expect(p.session).not.toHaveBeenCalled(); await choose()
 expect(within(screen.getByLabelText('当前产物清单 GET')).getByText('failed')).toBeTruthy()
 expect(screen.getByText('数学审校 NOT_RUN；来源核验 NOT_RUN；独立教学审校 NOT_RUN。')).toBeTruthy()
 expect((screen.getByLabelText('选择产物 notes.txt') as HTMLInputElement).disabled).toBe(true)
 expect(p.import).not.toHaveBeenCalled()
 fireEvent.click(screen.getByText('明确新建所选产物的回导预览')); await screen.findByText(/回导原 202 ACK 已保存；/)
 expect(p.imports).not.toHaveBeenCalled()
 fireEvent.click(screen.getByText(`读取回导当前子项 ${artifactAck.id}`)); await screen.findByLabelText('回导聚合当前 GET')
 expect(within(screen.getByLabelText('回导聚合当前 GET')).getByText(/completed；原 actor/)).toBeTruthy()
 const saved = Object.values(await store.load(artifactWorkspace)).map(r => readArtifactCommand(r, artifactWorkspace)); expect(saved[0].ack).toEqual(artifactAck)
 expect(p.import).toHaveBeenCalledTimes(1)
})
test('lost ACK survives remount and refresh with zero automatic POST, explicit replay uses original actor/key/full body/manifest', async () => {
 const p = port(), store = local(), forms = local(); vi.mocked(p.import).mockRejectedValueOnce(new Error('lost ACK'))
 const view = render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await choose(); fireEvent.click(screen.getByText('明确新建所选产物的回导预览')); await screen.findByText(/产物结果或本机保存未知/)
 const originalCall = vi.mocked(p.import).mock.calls[0], original = readArtifactCommand((await store.load(artifactWorkspace))[originalCall[2]], artifactWorkspace)
 view.unmount(); render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 expect(p.import).toHaveBeenCalledTimes(1); await refresh(); expect(p.import).toHaveBeenCalledTimes(1)
 fireEvent.click(screen.getByText(`显式回放回导原 key ${originalCall[2]}`)); await screen.findByText(/回导原 202 ACK 已保存；/)
 expect(vi.mocked(p.import).mock.calls[1]).toEqual(originalCall)
 expect(readArtifactCommand((await store.load(artifactWorkspace))[originalCall[2]], artifactWorkspace)).toEqual({ ...original, ack: artifactAck })
})
test.each([412, 409])('%i retains original selection/key/basis, independent current read never resends', async status => {
 const p = port(), store = local(), forms = local(); vi.mocked(p.import).mockRejectedValueOnce(new ApiError(status, 'private detail', 'CODEX_SOURCE_CHANGED'))
 render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await choose(); fireEvent.click(screen.getByText('明确新建所选产物的回导预览')); await screen.findByText(status === 412 ? /产物版本已变化/ : /产物绑定冲突/)
 const call = vi.mocked(p.import).mock.calls[0], before = (await store.load(artifactWorkspace))[call[2]].text
 fireEvent.click(screen.getByText('独立读取当前产物清单')); await screen.findByText(/当前清单已读取/)
 expect((await store.load(artifactWorkspace))[call[2]].text).toBe(before); expect(p.import).toHaveBeenCalledTimes(1); expect(screen.queryByText(/private detail/)).toBeNull()
})
test.each(['actor', 'learner', 'independent', 'open_book'] as const)('restore rereads fresh %s before revealing original selection or creating a branch', async mode => {
 const p = port(), store = local(), forms = local(), original = snapshotArtifactForm(artifactWorkspace, artifactActor, { session_id: 'codex_session_synthetic', turn_id: 'turn_artifact_synthetic', selection: { basis: artifactManifest(), artifact_ids: ['artifact_synthetic_md'] } }, null)
 await persistArtifactForm(original, forms)
 render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await refresh()
 const restore = screen.getByText(`恢复产物表单 ${original.draft_id} · 1`)
 vi.mocked(p.session).mockResolvedValue({ ...auth(), actor_session_id: mode === 'actor' ? 'actor_other' : artifactActor, role: mode === 'learner' ? 'learner' : 'author', active_independent_attempt_id: mode === 'independent' ? 'attempt_active' : null, active_open_book_attempt_id: mode === 'open_book' ? 'attempt_active' : null })
 fireEvent.click(restore); await screen.findByText(/产物操作的当前权限或原 actor 已变化/)
 expect(screen.queryByLabelText('原清单选择')).toBeNull(); expect(Object.keys(await forms.load(artifactWorkspace))).toEqual([original.snapshot_id]); expect(p.import).not.toHaveBeenCalled()
})
test('unmount retains late checked ACK under original actor and saving local facts performs no second POST', async () => {
 const p = port(), store = local(), forms = local(), response = deferred<typeof artifactAck>()
 vi.mocked(p.import).mockReturnValue(response.promise)
 const view = render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await choose(); fireEvent.click(screen.getByText('明确新建所选产物的回导预览')); await waitFor(() => expect(p.import).toHaveBeenCalledTimes(1))
 view.unmount(); await act(async () => response.resolve(artifactAck)); await waitFor(() => expect(heldArtifactCommands(artifactWorkspace).some(c => c.ack?.id === artifactAck.id)).toBe(true))
 render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await refresh()
 fireEvent.click(screen.getByText('仅保存产物本机事实')); await screen.findByText(/仅保存产物原 actor 的本机事实/)
 expect(p.import).toHaveBeenCalledTimes(1); expect(Object.values(await store.load(artifactWorkspace)).map(r => readArtifactCommand(r, artifactWorkspace))[0].ack).toEqual(artifactAck)
})
test('manifest arriving after port replacement is not shown and never causes import', async () => {
 const p = port(), next = port(), store = local(), forms = local(), response = deferred<ReturnType<typeof artifactManifest>>()
 const view = render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await refresh(); fireEvent.change(screen.getByLabelText('产物来源 session ID'), { target: { value: 'codex_session_synthetic' } }); fireEvent.change(screen.getByLabelText('产物来源 turn ID'), { target: { value: 'turn_artifact_synthetic' } })
 vi.mocked(p.manifest).mockReturnValue(response.promise); fireEvent.click(screen.getByText('独立读取当前产物清单')); await waitFor(() => expect(p.manifest).toHaveBeenCalledTimes(1))
 view.rerender(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={next} store={store} formStore={forms} />)
 await act(async () => response.resolve(artifactManifest())); expect(screen.queryByLabelText('当前产物清单 GET')).toBeNull(); expect(p.import).not.toHaveBeenCalled(); expect(next.import).not.toHaveBeenCalled()
})
test('fresh Policy denial after actual download bytes prevents any browser download delivery', async () => {
 const p = port(), store = local(), forms = local(), click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
 vi.mocked(p.download).mockImplementation(async () => { vi.mocked(p.session).mockResolvedValue({ ...auth(), role: 'learner' }); return new Blob([artifactData]) })
 render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await choose()
 fireEvent.click(screen.getByText('受控下载 成果/说明.md')); await screen.findByText(/产物操作的当前权限或原 actor 已变化/)
 expect(p.download).toHaveBeenCalledTimes(1); expect(click).not.toHaveBeenCalled()
})
