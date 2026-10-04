import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { ApiError } from '../../api/client'
import { deferred } from './bootstrapTestFixtures'
import { heldApprovalCommands, heldApprovalForms, releaseApprovalCommand, releaseApprovalForm } from './approvalMemory'
import { persistApprovalForm, snapshotApprovalForm } from './approvalForms'
import { approvalAck, approvalControl, approvalSession, approvalView, approvalWorkspace } from './approvalFixtures'
import type { ApprovalPort } from './approvalClient'
import { CodexApprovalsPanel } from './CodexApprovalsPanel'
import { readApprovalCommand } from './approvalCommands'
const stores: DraftStore[] = []
const local = () => { const s = new DraftStore({ name: `approval-panel-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(s); return s }
const port = (): ApprovalPort => ({ session: vi.fn(async () => approvalSession()), control: vi.fn(async () => approvalControl()), read: vi.fn(async () => approvalView()), decide: vi.fn(async () => approvalAck()) })
afterEach(async () => { cleanup(); heldApprovalCommands(approvalWorkspace).forEach(releaseApprovalCommand); heldApprovalForms(approvalWorkspace).forEach(releaseApprovalForm); await Promise.all(stores.splice(0).map(s => s.close())); vi.restoreAllMocks() })
const refresh = async () => { fireEvent.click(screen.getByText('读取审批记录与权限')); await screen.findByText(/审批本机记录已读取/); await waitFor(() => expect((screen.getByText('读取审批记录与权限') as HTMLButtonElement).disabled).toBe(false)) }
async function readControl() {
 await refresh(); fireEvent.change(screen.getByLabelText('审批来源 turn ID'), { target: { value: 'turn_approval_synthetic' } })
 fireEvent.click(screen.getByText('独立读取审批安全控制')); await screen.findByLabelText('审批安全控制 GET')
}
test('learner can decline from the complete safe control without subject GET; durable ACK binds the actual deciding actor', async () => {
 const p = port(), store = local(), forms = local(), actor = 'learner_deciding_actor'
 vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), actor_session_id: actor, role: 'learner', active_independent_attempt_id: 'attempt_independent' })
 vi.mocked(p.decide).mockImplementation(async (id, body, key) => {
  const c = readApprovalCommand((await store.load(approvalWorkspace))[key], approvalWorkspace)
  expect(c.actor_session_id).toBe(actor); expect(c.basis).toEqual({ kind: 'decline', control: approvalControl() })
  expect(id).toBe('approval_synthetic'); expect(body).toEqual({ expected_revision: 1, operation_sha256: '5'.repeat(64), decision: 'decline' })
  return approvalAck('decline', actor)
 })
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted={false} port={p} store={store} formStore={forms} />)
 await readControl(); fireEvent.click(screen.getByText('明确拒绝这一次操作 approval_synthetic'))
 await screen.findByText(/审批原 ACK 已保存/)
 expect(p.read).not.toHaveBeenCalled(); expect(p.decide).toHaveBeenCalledTimes(1)
 const saved = Object.values(await store.load(approvalWorkspace)).map(r => readApprovalCommand(r, approvalWorkspace))
 expect(saved[0].ack).toEqual(approvalAck('decline', actor))
})

async function readDetail() { await readControl(); fireEvent.click(screen.getByText('独立读取完整操作 approval_synthetic')); await screen.findByLabelText('审批当前详情 GET') }
const approve = () => fireEvent.click(screen.getByText('明确仅批准这一次完整操作 approval_synthetic'))
test('original author explicitly sees the complete operation; approval ACK does not become execution, independent GET keeps original ACK', async () => {
 const p = port(), store = local(), forms = local()
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 expect(p.session).not.toHaveBeenCalled(); await readDetail()
 expect(screen.getByLabelText('完整实际命令').textContent).toBe(approvalView().operation.kind === 'command' ? (approvalView().operation as { command_text: string }).command_text : '')
 expect(p.decide).not.toHaveBeenCalled(); approve(); await screen.findByText(/审批原 ACK 已保存/)
 expect(p.read).toHaveBeenCalledTimes(1); expect(within(screen.getByLabelText('审批当前详情 GET')).getByText(/执行 not_started/)).toBeTruthy()
 const before = Object.values(await store.load(approvalWorkspace))[0].text
 vi.mocked(p.read).mockResolvedValue({ ...approvalView(), revision: 4, decision: 'approve_once', validity: 'closed', execution: 'completed', decided_at: '2026-10-05T00:00:01Z', started_at: '2026-10-05T00:00:02Z', finished_at: '2026-10-05T00:00:03Z', result_sha256: '6'.repeat(64), job: { id: 'job_approval_synthetic', status: 'completed' }, job_revision: 20 })
 fireEvent.click(screen.getByText('独立刷新操作执行事实 approval_synthetic')); await screen.findByText(/执行 completed/)
 expect(Object.values(await store.load(approvalWorkspace))[0].text).toBe(before); expect(p.decide).toHaveBeenCalledTimes(1)
})
test('lost approval ACK survives remount, refresh sends zero POST, explicit original key/body replays even after current closes', async () => {
 const p = port(), store = local(), forms = local(); vi.mocked(p.decide).mockRejectedValueOnce(new Error('lost ACK'))
 const view = render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await readDetail(); approve(); await screen.findByText(/审批结果或本机保存未知/)
 const call = vi.mocked(p.decide).mock.calls[0], original = readApprovalCommand((await store.load(approvalWorkspace))[call[2]], approvalWorkspace)
 view.unmount(); render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await refresh(); expect(p.decide).toHaveBeenCalledTimes(1)
 // No new operation GET is necessary for recovery of this exact original command.
 vi.mocked(p.read).mockRejectedValue(new Error('current may already be closed'))
 fireEvent.click(screen.getByText(`显式回放审批原 key ${call[2]}`)); await screen.findByText(/审批原 ACK 已保存/)
 expect(vi.mocked(p.decide).mock.calls[1]).toEqual(call)
 expect(readApprovalCommand((await store.load(approvalWorkspace))[call[2]], approvalWorkspace)).toEqual({ ...original, ack: approvalAck() })
})
test.each([412, 409])('%i preserves original approval body/key/basis and independent read neither rewrites nor retries', async status => {
 const p = port(), store = local(), forms = local(); vi.mocked(p.decide).mockRejectedValueOnce(new ApiError(status, 'private diagnostics', 'REVISION_MISMATCH'))
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await readDetail(); approve(); await screen.findByText(status === 412 ? /审批版本已变化/ : /审批绑定或阶段冲突/)
 const call = vi.mocked(p.decide).mock.calls[0], before = (await store.load(approvalWorkspace))[call[2]].text
 fireEvent.click(screen.getByText('独立刷新操作执行事实 approval_synthetic')); await waitFor(() => expect(p.read).toHaveBeenCalledTimes(2))
 expect((await store.load(approvalWorkspace))[call[2]].text).toBe(before); expect(p.decide).toHaveBeenCalledTimes(1)
 expect((screen.getByText('明确仅批准这一次完整操作 approval_synthetic') as HTMLButtonElement).disabled).toBe(true); expect(screen.queryByText(/private diagnostics/)).toBeNull()
})
test.each(['learner', 'independent', 'open_book'] as const)('%s decline stays available without operation detail access', async mode => {
 const p = port(), store = local(), forms = local()
 vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), role: mode === 'learner' ? 'learner' : 'author', active_independent_attempt_id: mode === 'independent' ? 'attempt_independent' : null, active_open_book_attempt_id: mode === 'open_book' ? 'attempt_open_book' : null })
 vi.mocked(p.decide).mockResolvedValue(approvalAck('decline'))
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted={false} port={p} store={store} formStore={forms} />)
 await readControl(); expect((screen.getByText('独立读取完整操作 approval_synthetic') as HTMLButtonElement).disabled).toBe(true)
 fireEvent.click(screen.getByText('明确拒绝这一次操作 approval_synthetic')); await screen.findByText(/审批原 ACK 已保存/)
 expect(p.read).not.toHaveBeenCalled(); expect(p.decide).toHaveBeenCalledTimes(1)
})
test.each(['actor', 'learner', 'independent', 'open_book'] as const)('fresh %s change rejects new approval before write transport and hides operation', async mode => {
 const p = port(), store = local(), forms = local()
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await readDetail()
 vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), actor_session_id: mode === 'actor' ? 'other_actor' : approvalSession().actor_session_id, role: mode === 'learner' ? 'learner' : 'author', active_independent_attempt_id: mode === 'independent' ? 'attempt_independent' : null, active_open_book_attempt_id: mode === 'open_book' ? 'attempt_open_book' : null })
 approve(); await screen.findByText(/审批当前权限或原 actor 已变化/)
 expect(p.decide).not.toHaveBeenCalled(); expect(screen.queryByLabelText('完整当前操作')).toBeNull()
})
test('unsupported operation remains readable but cannot approve, while safe decline works', async () => {
 const p = port(), store = local(), forms = local()
 vi.mocked(p.read).mockResolvedValue({ ...approvalView(), operation: { kind: 'unsupported', category: 'network', reason: 'CODEX_OPERATION_UNSUPPORTED' } })
 vi.mocked(p.decide).mockResolvedValue(approvalAck('decline'))
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await readDetail()
 expect((screen.getByText('明确仅批准这一次完整操作 approval_synthetic') as HTMLButtonElement).disabled).toBe(true)
 fireEvent.click(screen.getByText('明确拒绝这一次操作 approval_synthetic')); await screen.findByText(/审批原 ACK 已保存/)
 expect(vi.mocked(p.decide).mock.calls[0][1].decision).toBe('decline')
})
test('complete file changes preserve order, Unicode and full diff as inert text', async () => {
 const p = port(), store = local(), forms = local(), diff = '-旧 α\n+<img src=x onerror=alert(1)>\n'
 vi.mocked(p.read).mockResolvedValue({ ...approvalView(), operation: { kind: 'file_change', operation_profile_sha256: '7'.repeat(64), files: [
  { path: '旧.md', action: 'delete', before_sha256: '1'.repeat(64), before_size: 4, after_sha256: null, after_size: null, diff },
  { path: '新.md', action: 'add', before_sha256: null, before_size: null, after_sha256: '2'.repeat(64), after_size: 0, diff: '' }] } })
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await readDetail()
 expect(screen.getByLabelText('完整 diff 旧.md').textContent).toBe(diff); expect(screen.getByLabelText('完整 diff 新.md').textContent).toBe('')
 expect(document.querySelector('img')).toBeNull(); expect(p.decide).not.toHaveBeenCalled()
})
test('late checked ACK after unmount remains original actor memory, local save performs no second POST', async () => {
 const p = port(), store = local(), forms = local(), response = deferred<ReturnType<typeof approvalAck>>()
 vi.mocked(p.decide).mockReturnValue(response.promise)
 const view = render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await readDetail(); approve()
 await waitFor(() => expect(p.decide).toHaveBeenCalledTimes(1)); view.unmount()
 await act(async () => response.resolve(approvalAck())); await waitFor(() => expect(heldApprovalCommands(approvalWorkspace).some(c => c.ack?.id === 'approval_synthetic')).toBe(true))
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await refresh()
 fireEvent.click(screen.getByText('仅保存审批本机事实')); await screen.findByText(/仅保存审批原 actor 的本机事实/)
 expect(p.decide).toHaveBeenCalledTimes(1); expect(Object.values(await store.load(approvalWorkspace)).map(r => readApprovalCommand(r, approvalWorkspace))[0].ack).toEqual(approvalAck())
})
test('actual actor loss before ACK delivery isolates full original ACK and denies new actor replay or disclosure', async () => {
 const p = port(), store = local(), forms = local(), response = deferred<ReturnType<typeof approvalAck>>()
 vi.mocked(p.decide).mockReturnValue(response.promise)
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await readDetail(); approve()
 await waitFor(() => expect(p.decide).toHaveBeenCalledTimes(1)); vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), actor_session_id: 'other_actor' })
 await act(async () => response.resolve(approvalAck())); await screen.findByText(/审批当前权限或原 actor 已变化/)
 expect(heldApprovalCommands(approvalWorkspace)[0].ack).toEqual(approvalAck()); await refresh()
 expect(screen.queryByLabelText('完整当前操作')).toBeNull(); expect(screen.queryByText(/显式回放审批原 key/)).toBeNull()
 fireEvent.click(screen.getByText('仅保存审批本机事实')); await screen.findByText(/仅保存审批原 actor 的本机事实/)
 expect(Object.values(await store.load(approvalWorkspace)).map(r => readApprovalCommand(r, approvalWorkspace))[0].ack).toEqual(approvalAck()); expect(p.decide).toHaveBeenCalledTimes(1)
})
test.each(['port', 'workspace'] as const)('late complete operation after %s replacement cannot appear', async mode => {
 const p = port(), next = port(), store = local(), forms = local(), response = deferred<ReturnType<typeof approvalView>>()
 const view = render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await readControl()
 vi.mocked(p.read).mockReturnValue(response.promise); fireEvent.click(screen.getByText('独立读取完整操作 approval_synthetic')); await waitFor(() => expect(p.read).toHaveBeenCalledTimes(1))
 view.rerender(<CodexApprovalsPanel workspace={mode === 'workspace' ? 'workspace_other' : approvalWorkspace} writeAdmitted port={mode === 'port' ? next : p} store={store} formStore={forms} />)
 await act(async () => response.resolve(approvalView())); expect(screen.queryByLabelText('完整当前操作')).toBeNull(); expect(p.decide).not.toHaveBeenCalled()
})
test('original form restore rereads actor before showing safe identifiers or saving a new branch', async () => {
 const p = port(), store = local(), forms = local(), original = snapshotApprovalForm(approvalWorkspace, approvalSession().actor_session_id, { turn_id: 'turn_saved_original' }, null)
 await persistApprovalForm(original, forms)
 render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />); await refresh()
 vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), actor_session_id: 'other_actor' })
 fireEvent.click(screen.getByText(`恢复审批表单 ${original.draft_id} · 1`)); await screen.findByText(/审批当前权限或原 actor 已变化/)
 expect((screen.getByLabelText('审批来源 turn ID') as HTMLInputElement).value).toBe(''); expect(Object.keys(await forms.load(approvalWorkspace))).toEqual([original.snapshot_id]); expect(p.decide).not.toHaveBeenCalled()
})

test.each(['learner', 'independent', 'open_book'] as const)('prior rejected approve preserves its original facts while %s can explicitly decline a fresh pending safe control', async mode => {
 const p = port(), store = local(), forms = local()
 vi.mocked(p.decide).mockRejectedValueOnce(new ApiError(503, 'runtime became unavailable', 'CODEX_RUNTIME_UNAVAILABLE')).mockResolvedValue(approvalAck('decline'))
 const view = render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await readDetail(); approve(); await screen.findByText(/BLOCKED：当前操作或固定运行证明不可用/)
 const first = vi.mocked(p.decide).mock.calls[0], original = (await store.load(approvalWorkspace))[first[2]].text
 vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), role: mode === 'learner' ? 'learner' : 'author', active_independent_attempt_id: mode === 'independent' ? 'attempt_independent' : null, active_open_book_attempt_id: mode === 'open_book' ? 'attempt_open_book' : null })
 view.rerender(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted={false} port={p} store={store} formStore={forms} />)
 await readControl(); const reads = vi.mocked(p.read).mock.calls.length
 const decline = screen.getByText('明确拒绝这一次操作 approval_synthetic') as HTMLButtonElement
 expect(decline.disabled, 'a prior academic approve command must not block explicit safe decline of a still-pending operation').toBe(false)
 fireEvent.click(decline); await screen.findByText(/审批原 ACK 已保存/)
 expect(p.decide).toHaveBeenCalledTimes(2); const second = vi.mocked(p.decide).mock.calls[1]
 expect(second[2]).not.toBe(first[2]); expect(second[1]).toEqual({ expected_revision: 1, operation_sha256: '5'.repeat(64), decision: 'decline' })
 expect((await store.load(approvalWorkspace))[first[2]].text).toBe(original); expect(p.read).toHaveBeenCalledTimes(reads)
 const reduced = readApprovalCommand((await store.load(approvalWorkspace))[second[2]], approvalWorkspace)
 expect(reduced.basis).toEqual({ kind: 'decline', control: approvalControl() }); expect(reduced.ack).toEqual(approvalAck('decline'))
})

test('unknown approve also permits explicit safe decline while its exact pending journal stays unchanged', async () => {
 const p = port(), store = local(), forms = local(); vi.mocked(p.decide).mockRejectedValueOnce(new Error('response unavailable')).mockResolvedValue(approvalAck('decline'))
 const view = render(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted port={p} store={store} formStore={forms} />)
 await readDetail(); approve(); await screen.findByText(/审批结果或本机保存未知/)
 const first = vi.mocked(p.decide).mock.calls[0], original = (await store.load(approvalWorkspace))[first[2]].text
 vi.mocked(p.session).mockResolvedValue({ ...approvalSession(), role: 'learner' }); view.rerender(<CodexApprovalsPanel workspace={approvalWorkspace} writeAdmitted={false} port={p} store={store} formStore={forms} />)
 await readControl(); fireEvent.click(screen.getByText('明确拒绝这一次操作 approval_synthetic')); await screen.findByText(/审批原 ACK 已保存/)
 expect(p.decide).toHaveBeenCalledTimes(2); expect(vi.mocked(p.decide).mock.calls[1][2]).not.toBe(first[2]); expect((await store.load(approvalWorkspace))[first[2]].text).toBe(original)
 fireEvent.click(screen.getByText('独立读取审批安全控制')); await screen.findByLabelText('审批安全控制 GET')
 expect((screen.getByText('明确拒绝这一次操作 approval_synthetic') as HTMLButtonElement).disabled).toBe(true); expect(p.decide).toHaveBeenCalledTimes(2)
})
