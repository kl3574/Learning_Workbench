import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { approvalAck, approvalControl, approvalSession, approvalView, approvalWorkspace } from './approvalFixtures'
import type { ApprovalPort } from './approvalClient'
import { CodexApprovalsPanel } from './CodexApprovalsPanel'
import { readApprovalCommand } from './approvalCommands'
const stores: DraftStore[] = []
const local = () => { const s = new DraftStore({ name: `approval-panel-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(s); return s }
const port = (): ApprovalPort => ({ session: vi.fn(async () => approvalSession()), control: vi.fn(async () => approvalControl()), read: vi.fn(async () => approvalView()), decide: vi.fn(async () => approvalAck()) })
afterEach(async () => { cleanup(); await Promise.all(stores.splice(0).map(s => s.close())); vi.restoreAllMocks() })
const refresh = async () => { fireEvent.click(screen.getByText('读取审批记录与权限')); await screen.findByText(/审批本机记录已读取/) }
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
