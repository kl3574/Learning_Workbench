import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { approvalClient } from './approvalClient'
import { dispatchApprovalCommand, type ApprovalCommand } from './approvalCommands'
import { approvalAck, approvalActor, approvalView, approvalWorkspace } from './approvalFixtures'
afterEach(() => vi.unstubAllGlobals())
test('actual generated decision POST persists original actor, key, complete operation basis and approval revision before transport', async () => {
 const store = new DraftStore({ name: `approval-wire-${crypto.randomUUID()}`, factory: new IDBFactory() }), view = approvalView()
 const command: ApprovalCommand = { version: 1, workspace_id: approvalWorkspace, actor_session_id: approvalActor, command_id: 'approval_original_key', target_id: view.id,
  route: 'POST /api/v1/approvals/{id}/decision', basis: { kind: 'approve', view }, body: { expected_revision: 1, operation_sha256: view.operation_sha256, decision: 'approve_once' }, ack: null, error: null }
 try {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
   expect(url).toBe('/api/v1/approvals/approval_synthetic/decision'); expect(init.method).toBe('POST')
   expect(new Headers(init.headers).get('Idempotency-Key')).toBe('approval_original_key'); expect(JSON.parse(init.body as string)).toEqual(command.body)
   const original = (await store.load(approvalWorkspace))[command.command_id]
   expect(original, 'the complete original approval command must be durable before the first POST').toBeDefined()
   expect(JSON.parse(original.text)).toEqual(command)
   return new Response(JSON.stringify(approvalAck()))
  }))
  const result = await dispatchApprovalCommand(command, approvalClient, store)
  expect(result.ack).toEqual(approvalAck())
  expect(JSON.parse((await store.load(approvalWorkspace))[command.command_id].text)).toEqual(result)
 } finally { await store.close() }
})
