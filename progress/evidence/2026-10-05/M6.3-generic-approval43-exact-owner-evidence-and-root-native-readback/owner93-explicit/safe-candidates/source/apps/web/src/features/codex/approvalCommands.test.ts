import { IDBFactory } from 'fake-indexeddb'
import { expect, test, vi } from 'vitest'
import type { ApprovalDecision } from '../../../../../packages/contracts/generated/api-types'
import type { CodexFileOperation, GenericApprovalView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { DraftStore } from '../../workbench/DraftStore'
import { checkedApproval } from './approvalClient'
import { decodeApprovalCommand, dispatchApprovalCommand, makeApprovalCommand, persistApprovalCommand, readApprovalCommand, type ApprovalCommand } from './approvalCommands'
import { approvalAck, approvalActor, approvalControl, approvalView, approvalWorkspace } from './approvalFixtures'

const learner = 'learner_approval_synthetic'
const command = () => {
 const view = approvalView()
 return makeApprovalCommand(approvalWorkspace, approvalActor, { kind: 'approve', view }, view.id)
}
const decline = (validity: GenericApprovalView['validity'] = 'unavailable') => {
 const control = approvalControl()
 control.approval_controls[0].validity = validity
 return makeApprovalCommand(approvalWorkspace, learner, { kind: 'decline', control }, control.approval_controls[0].id)
}
const decode = (value: ApprovalCommand) => decodeApprovalCommand(JSON.stringify(value), approvalWorkspace)
const store = () => new DraftStore({ name: `approval-command-${crypto.randomUUID()}`, factory: new IDBFactory() })
const fileView = (): GenericApprovalView & { operation: CodexFileOperation } => ({
 ...approvalView(),
 operation: { kind: 'file_change', operation_profile_sha256: '4'.repeat(64), files: [
  { path: 'turn_outputs/old.md', action: 'delete', before_sha256: '6'.repeat(64), before_size: 0, after_sha256: null, after_size: null, diff: '' },
  { path: 'turn_outputs/新 α.md', action: 'add', before_sha256: null, before_size: null, after_sha256: '7'.repeat(64), after_size: 0, diff: '' },
  { path: 'turn_outputs/update.md', action: 'update', before_sha256: '8'.repeat(64), before_size: 1, after_sha256: '9'.repeat(64), after_size: 2, diff: '-α\n+β\n' },
 ] },
})

test('learner decline retains the complete safe control and the actual deciding actor in the full ACK', async () => {
 const db = store(), original = decline(), ack = approvalAck('decline', learner)
 const port = { decide: vi.fn(async (id: string, body: ApprovalDecision, key: string) => {
  const durable = readApprovalCommand((await db.load(approvalWorkspace))[key], approvalWorkspace)
  expect(durable).toEqual(original)
  expect(id).toBe(original.target_id)
  expect(body).toEqual({ expected_revision: 1, operation_sha256: approvalView().operation_sha256, decision: 'decline' })
  return ack
 }) }
 try {
  expect(original.basis).toEqual({ kind: 'decline', control: { ...approvalControl(), approval_controls: [{ ...approvalControl().approval_controls[0], validity: 'unavailable' }] } })
  expect(original.actor_session_id).not.toBe(approvalControl().actor_session_id)
  const saved = await dispatchApprovalCommand(original, port, db)
  expect(saved.ack).toEqual(ack)
  expect(readApprovalCommand((await db.load(approvalWorkspace))[original.command_id], approvalWorkspace)).toEqual(saved)
  expect(port.decide).toHaveBeenCalledTimes(1)
 } finally { await db.close() }
})

test('approval CAS comes from the selected approval, never the dynamic Job revision', () => {
 for (const original of [command(), decline()]) {
  expect(original.body.expected_revision).toBe(1)
  expect(approvalControl().job_revision).toBe(8)
  expect(() => decode({ ...original, body: { ...original.body, expected_revision: 8 } })).toThrow()
 }
 const control = approvalControl()
 control.approval_controls = []
 expect(() => makeApprovalCommand(approvalWorkspace, learner, { kind: 'decline', control }, control.approval_ids[0])).toThrow()
})

test('every immutable ACK binding and the closed ACK shape are checked against the original learner command', () => {
 const original = decline()
 const changes: Array<[string, Record<string, unknown>]> = [
  ['approval id', { id: 'approval_other' }], ['revision', { revision: 3 }],
  ['actual deciding actor', { actor_session_id: approvalActor }], ['operation hash', { operation_sha256: 'a'.repeat(64) }],
  ['decision', { decision: 'approve_once' }], ['applied', { applied: false }],
  ['session', { session_id: 'session_other' }], ['turn', { turn_id: 'turn_other' }],
  ['run', { run_id: 'job_other' }], ['job', { job: { id: 'job_other', status: 'running' } }],
  ['coherent but foreign run and job', { run_id: 'job_other', job: { id: 'job_other', status: 'running' } }],
  ['invalid Job status', { job: { id: approvalAck().job.id, status: 'unknown' } }],
  ['additional field', { execution: 'completed' }],
 ]
 for (const [field, change] of changes) {
  expect(() => decodeApprovalCommand(JSON.stringify({ ...original, ack: { ...approvalAck('decline', learner), ...change } }), approvalWorkspace), field).toThrow()
 }
 for (const field of Object.keys(approvalAck())) {
  const incomplete: Record<string, unknown> = { ...approvalAck('decline', learner) }
  delete incomplete[field]
  expect(() => decodeApprovalCommand(JSON.stringify({ ...original, ack: incomplete }), approvalWorkspace), `missing ${field}`).toThrow()
 }
})

test('saved basis membership, original operation actor, hash and owner identities cannot be substituted', () => {
 const mutations: Array<[string, (value: ApprovalCommand) => void]> = [
  ['approval membership', c => { if (c.basis.kind === 'decline') { c.basis.control.approval_controls[0].id = 'approval_other'; c.basis.control.approval_ids[0] = 'approval_other' } }],
  ['approval revision', c => { if (c.basis.kind === 'decline') c.basis.control.approval_controls[0].revision++ }],
  ['operation hash', c => { if (c.basis.kind === 'decline') c.basis.control.approval_controls[0].operation_sha256 = 'a'.repeat(64) }],
  ['session owner', c => { if (c.basis.kind === 'decline') c.basis.control.session_id = 'session_other' }],
  ['turn owner', c => { if (c.basis.kind === 'decline') c.basis.control.id = 'turn_other' }],
  ['job owner', c => { if (c.basis.kind === 'decline') c.basis.control.job.id = 'job_other' }],
  ['target', c => { c.target_id = 'approval_other' }],
  ['workspace', c => { c.workspace_id = 'workspace_other' }],
  ['route', c => { Object.assign(c, { route: 'POST /api/v1/jobs/{id}/cancel' }) }],
 ]
 for (const [field, mutate] of mutations) {
  const value = { ...decline(), ack: approvalAck('decline', learner) }
  mutate(value)
  expect(() => decode(value), field).toThrow()
 }
 const preparedByAnotherActor = command()
 if (preparedByAnotherActor.basis.kind === 'approve') preparedByAnotherActor.basis.view.actor_session_id = learner
 expect(() => decode(preparedByAnotherActor)).toThrow()
})

test('lost ACK survives a store reopen and explicit expired decline replay sends the exact original body and key', async () => {
 const factory = new IDBFactory(), name = `approval-reopen-${crypto.randomUUID()}`
 const first = new DraftStore({ name, factory }), reopened = new DraftStore({ name, factory }), original = decline('expired')
 const attempts: Array<{ id: string; body: ApprovalDecision; key: string }> = []
 const ack = approvalAck('decline', learner)
 const port = { decide: vi.fn(async (id: string, body: ApprovalDecision, key: string) => {
  attempts.push({ id, body: structuredClone(body), key })
  if (attempts.length === 1) throw new Error('decision committed but response lost')
  return ack
 }) }
 try {
  await expect(dispatchApprovalCommand(original, port, first)).rejects.toThrow('response lost')
  await first.close()
  const recovered = readApprovalCommand((await reopened.load(approvalWorkspace))[original.command_id], approvalWorkspace)
  expect(recovered).toEqual(original)
  expect(attempts).toHaveLength(1)
  const saved = await dispatchApprovalCommand(recovered, port, reopened)
  expect(attempts).toEqual([1, 2].map(() => ({ id: original.target_id, body: original.body, key: original.command_id })))
  expect(saved.ack).toEqual(ack)
  expect(await dispatchApprovalCommand(original, port, reopened)).toEqual(saved)
  expect(attempts).toHaveLength(2)
 } finally { await first.close(); await reopened.close() }
})

test('decline journal decoding accepts unavailable, changed, expired and closed original safe controls', () => {
 for (const validity of ['current', 'unavailable', 'changed', 'expired', 'closed'] as const) {
  const value = decline(validity)
  expect(decode({ ...value, ack: approvalAck('decline', learner) }).body.decision, validity).toBe('decline')
 }
})

test('pending closed and approved-but-never-started closed views retain their actual revision and error facts', () => {
 const pending: GenericApprovalView = { ...approvalView(), revision: 2, validity: 'closed', error_code: 'CODEX_CANCELLED' }
 const approved: GenericApprovalView = { ...approvalView(), revision: 3, decision: 'approve_once', validity: 'closed', decided_at: '2026-10-05T00:00:01Z', error_code: 'CODEX_CANCELLED' }
 expect(checkedApproval('GenericApprovalView', pending)).toEqual(pending)
 expect(checkedApproval('GenericApprovalView', approved)).toEqual(approved)
 expect(approved.execution).toBe('not_started')
 expect(approved.started_at).toBeNull()
})

test('current completed facts and a pending writer cannot replace the historical full decision ACK', async () => {
 const db = store(), original = command(), port = { decide: vi.fn(async () => approvalAck()) }
 try {
  const saved = await dispatchApprovalCommand(original, port, db)
  const current: GenericApprovalView = { ...approvalView(), revision: 4, decision: 'approve_once', validity: 'closed', execution: 'completed',
   job: { ...approvalView().job, status: 'completed' }, job_revision: 13,
   decided_at: '2026-10-05T00:00:01Z', started_at: '2026-10-05T00:00:02Z', finished_at: '2026-10-05T00:00:03Z', result_sha256: 'a'.repeat(64) }
  expect(checkedApproval('GenericApprovalView', current).job.status).toBe('completed')
  expect(saved.ack?.job.status).toBe('running')
  await persistApprovalCommand(original, db)
  expect(readApprovalCommand((await db.load(approvalWorkspace))[original.command_id], approvalWorkspace)).toEqual(saved)
  await expect(persistApprovalCommand({ ...saved, basis: { kind: 'approve', view: current } }, db)).rejects.toThrow()
  expect(await dispatchApprovalCommand(original, port, db)).toEqual(saved)
  expect(port.decide).toHaveBeenCalledTimes(1)
  const publicAck = { ...approvalAck(), job: { ...approvalAck().job, status: 'completed' as const } }
  expect(decode({ ...original, ack: publicAck }).ack).toEqual(publicAck)
  await expect(persistApprovalCommand({ ...saved, ack: publicAck }, db)).rejects.toThrow()
  expect(readApprovalCommand((await db.load(approvalWorkspace))[original.command_id], approvalWorkspace)).toEqual(saved)
 } finally { await db.close() }
})

test('command and file paths are canonical while ordered Unicode file changes, zero sizes and empty diffs survive', () => {
 const files = fileView(), checked = checkedApproval('GenericApprovalView', files)
 expect(checked.operation).toEqual(files.operation)
 const unsafe = ['/absolute', '../escape', 'dir/../escape', './file', 'dir//file', 'dir/', 'C:file', 'dir\\file', 'dir/\u0000file', 'dir/\u007ffile']
 for (const value of unsafe) {
  const view = approvalView()
  if (view.operation.kind !== 'command') throw new Error('command fixture required')
  view.operation.cwd = value
  expect(() => checkedApproval('GenericApprovalView', view), `cwd ${JSON.stringify(value)}`).toThrow()
  const read = approvalView()
  if (read.operation.kind !== 'command') throw new Error('command fixture required')
  read.operation.read_files = [{ path: value, size: 0, sha256: 'a'.repeat(64) }]
  expect(() => checkedApproval('GenericApprovalView', read), `read ${JSON.stringify(value)}`).toThrow()
  const file = fileView(); file.operation.files[0].path = value
  expect(() => checkedApproval('GenericApprovalView', file), `file ${JSON.stringify(value)}`).toThrow()
 }
 const reads = approvalView()
 if (reads.operation.kind !== 'command') throw new Error('command fixture required')
 reads.operation.read_files = Array.from({ length: 2 }, () => ({ path: 'inputs/α.md', size: 0, sha256: 'a'.repeat(64) }))
 expect(() => checkedApproval('GenericApprovalView', reads)).toThrow()
 const duplicate = fileView(); duplicate.operation.files[1].path = duplicate.operation.files[0].path
 expect(() => checkedApproval('GenericApprovalView', duplicate)).toThrow()
})

test('file add, update and delete require paired hashes and sizes on exactly the existing sides', () => {
 for (const [index, fields] of [[0, ['before_sha256', 'before_size']], [1, ['after_sha256', 'after_size']], [2, ['before_sha256', 'before_size', 'after_sha256', 'after_size']]] as const) {
  for (const field of fields) {
   const view = fileView(); Object.assign(view.operation.files[index], { [field]: null })
   expect(() => checkedApproval('GenericApprovalView', view), `${index} missing ${field}`).toThrow()
  }
 }
 for (const [index, fields] of [[0, ['after_sha256', 'after_size']], [1, ['before_sha256', 'before_size']]] as const) {
  for (const field of fields) {
   const view = fileView(); Object.assign(view.operation.files[index], { [field]: field.endsWith('sha256') ? 'a'.repeat(64) : 0 })
   expect(() => checkedApproval('GenericApprovalView', view), `${index} invented ${field}`).toThrow()
  }
 }
})

test('same key cannot replace an independently valid original body, and stored conflicts remain inspectable', async () => {
 const db = store(), original = decline(), changed = decline()
 changed.command_id = original.command_id
 changed.body.operation_sha256 = 'a'.repeat(64)
 if (changed.basis.kind === 'decline') changed.basis.control.approval_controls[0].operation_sha256 = changed.body.operation_sha256
 expect(decode(changed)).toEqual(changed)
 try {
  await persistApprovalCommand(original, db)
  await expect(persistApprovalCommand(changed, db)).rejects.toThrow()
  expect(readApprovalCommand((await db.load(approvalWorkspace))[original.command_id], approvalWorkspace)).toEqual(original)
  await db.save(approvalWorkspace, original.command_id, JSON.stringify(changed), 0)
  const conflict = (await db.load(approvalWorkspace))[original.command_id]
  expect(conflict.conflicts).toHaveLength(1)
  expect(() => readApprovalCommand(conflict, approvalWorkspace)).toThrow()
  await expect(persistApprovalCommand(original, db)).rejects.toThrow()
  expect((await db.load(approvalWorkspace))[original.command_id]).toEqual(conflict)
 } finally { await db.close() }
})

test('two individually valid full ACKs for the same key are rejected without erasing either candidate', async () => {
 const db = store(), original = command(), acknowledged = { ...original, ack: approvalAck() }
 const changed = decode({ ...acknowledged, ack: { ...approvalAck(), job: { ...approvalAck().job, status: 'completed' } } })
 try {
  await persistApprovalCommand(acknowledged, db)
  await db.save(approvalWorkspace, original.command_id, JSON.stringify(changed), 0)
  const conflict = (await db.load(approvalWorkspace))[original.command_id]
  expect(conflict.conflicts).toHaveLength(1)
  expect(() => readApprovalCommand(conflict, approvalWorkspace)).toThrow('Conflicting approval ACK')
  await expect(persistApprovalCommand(acknowledged, db)).rejects.toThrow()
  expect((await db.load(approvalWorkspace))[original.command_id]).toEqual(conflict)
 } finally { await db.close() }
})
