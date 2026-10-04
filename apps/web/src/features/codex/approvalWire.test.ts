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

test('generated approval GET preserves the complete body and rejects wrong target, extra keys and incomplete operation', async () => {
 const value = approvalView(), calls: Array<[string, string | undefined]> = []
 vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => { calls.push([url, init.method]); return new Response(JSON.stringify(value)) }))
 expect(await approvalClient.read(value.id)).toEqual(value)
 expect(calls).toEqual([['/api/v1/approvals/approval_synthetic', 'GET']])
 await expect(approvalClient.read('approval_other')).rejects.toThrow()
 vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...value, private_extra: 'not_allowed' }))))
 await expect(approvalClient.read(value.id)).rejects.toThrow()
 vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...value, operation: { kind: 'command', command_text: 'partial description' } }))))
 await expect(approvalClient.read(value.id)).rejects.toThrow()
})
test('actual safe decline transport retains full control and learner ACK, never requests academic approval details', async () => {
 const { approvalControl } = await import('./approvalFixtures'), { makeApprovalCommand } = await import('./approvalCommands')
 const store = new DraftStore({ name: `approval-decline-wire-${crypto.randomUUID()}`, factory: new IDBFactory() }), paths: string[] = [], actor = 'learner_actual_decision'
 const original = makeApprovalCommand(approvalWorkspace, actor, { kind: 'decline', control: approvalControl() }, 'approval_synthetic')
 try {
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
   paths.push(path); expect(init.method).toBe('POST'); expect(JSON.parse(init.body as string).expected_revision).toBe(1)
   expect(JSON.parse((await store.load(approvalWorkspace))[original.command_id].text)).toEqual(original)
   return new Response(JSON.stringify(approvalAck('decline', actor)))
  }))
  const result = await dispatchApprovalCommand(original, approvalClient, store)
  expect(result.ack).toEqual(approvalAck('decline', actor)); expect(paths).toEqual(['/api/v1/approvals/approval_synthetic/decision'])
 } finally { await store.close() }
})
test('actual generated POST propagates owner CAS failure without automatic retry or replacement key', async () => {
 const calls: RequestInit[] = [], body = { expected_revision: 1, operation_sha256: '5'.repeat(64), decision: 'approve_once' as const }
 vi.stubGlobal('fetch', vi.fn(async (_url: string, init: RequestInit) => { calls.push(init); return new Response(JSON.stringify({ error: { code: 'REVISION_MISMATCH', message: 'synthetic CAS failure' } }), { status: 412 }) }))
 await expect(approvalClient.decide('approval_synthetic', body, 'original_cas_key')).rejects.toMatchObject({ status: 412, code: 'REVISION_MISMATCH' })
 expect(calls).toHaveLength(1); expect(new Headers(calls[0].headers).get('Idempotency-Key')).toBe('original_cas_key'); expect(JSON.parse(calls[0].body as string)).toEqual(body)
})
