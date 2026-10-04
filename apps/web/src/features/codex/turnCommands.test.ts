import { IDBFactory } from 'fake-indexeddb'
import { expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { actor, codexSession, workspace } from './bootstrapTestFixtures'
import { decodeTurnCommand, persistTurnCommand, readTurnCommand, turnCancelCommand, turnInterruptCommand, turnPrepareCommand, type TurnCommand } from './turnCommands'
import { turnBody, turnCancelledJob, turnControl, turnPreparation } from './turnTestFixtures'
import { emptyTurnFields, persistTurnForm, readTurnForm, snapshotTurnForm } from './turnForms'
const command = () => turnPrepareCommand(workspace, actor, codexSession(), turnBody())
test.each([
 (v: TurnCommand) => { v.actor_session_id = 'actor_other' },
 (v: TurnCommand) => { v.session_id = 'session_other' },
 (v: TurnCommand) => { v.command_id += '\n' },
 (v: TurnCommand) => { if (v.kind === 'prepare') v.basis.revision = 9 },
 (v: TurnCommand) => { if (v.kind === 'prepare') v.basis.active_turn_id = 'turn_existing' },
 (v: TurnCommand) => { if (v.kind === 'prepare') v.basis.status = 'unknown' },
 (v: TurnCommand) => { if (v.kind === 'prepare') v.body.message += 'changed' },
 (v: TurnCommand) => { if (v.kind === 'prepare' && v.ack) v.ack.session_revision = 4 },
 (v: TurnCommand) => { if (v.kind === 'prepare' && v.ack) v.ack.job.status = 'running' },
 (v: TurnCommand) => { if (v.kind === 'prepare' && v.ack) v.ack.consent_id = 'consent_bootstrap' },
 (v: TurnCommand) => { Object.assign(v, { csrf_token: 'synthetic-only' }) },
])('damaged original actor/body/readonly basis/ACK cannot be accepted as a saved command %#', corrupt => {
 const value = decodeTurnCommand(JSON.stringify({ ...command(), ack: turnPreparation() }), workspace)
 corrupt(value); expect(() => decodeTurnCommand(JSON.stringify(value), workspace)).toThrow()
})
test('cancellation basis belongs to the actual target Job; the cancelling actor may be a different safe reader', () => {
 const value = turnCancelCommand(workspace, 'learner_new', turnControl())
 expect(value.actor_session_id).toBe('learner_new')
 expect(value.body).toEqual({ expected_revision: 1 })
 expect(() => decodeTurnCommand(JSON.stringify({ ...value, body: { expected_revision: 2 } }), workspace)).toThrow()
 expect(() => decodeTurnCommand(JSON.stringify({ ...value, ack: { ...turnCancelledJob(), id: 'job_other' } }), workspace)).toThrow()
})
test.each([
 { id: 'job_other' }, { workspace_id: 'workspace_other' }, { kind: 'authoring' },
 { revision: 0 }, { revision: true }, { progress: { completed: 0, total: null } },
 { warnings: 'omitted' }, { error: {} }, { extra: 'not in Jobs contract' },
])('full cancellation ACK rejects wrong owner/target and malformed closed JobSnapshot %#', change => {
 const original = turnCancelCommand(workspace, 'learner_new', turnControl())
 expect(() => decodeTurnCommand(JSON.stringify({ ...original, ack: { ...turnCancelledJob(), ...change } }), workspace)).toThrow()
})
test('truncated JobRef cannot replace full cancellation ACK; durable ACK survives a pending writer and rejects a changed snapshot', async () => {
 const db = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() })
 try {
  const original = turnCancelCommand(workspace, actor, turnControl())
  const acknowledged = decodeTurnCommand(JSON.stringify({ ...original, ack: turnCancelledJob() }), workspace)
  expect(() => decodeTurnCommand(JSON.stringify({ ...original, ack: { id: 'job_turn_test', status: 'cancelled' } }), workspace)).toThrow()
  await persistTurnCommand(original, db); await persistTurnCommand(acknowledged, db); await persistTurnCommand(original, db)
  expect(readTurnCommand((await db.load(workspace))[original.command_id], workspace)).toEqual(acknowledged)
  const changed = decodeTurnCommand(JSON.stringify({ ...acknowledged, ack: { ...turnCancelledJob(), updated_at: '2026-10-04T00:00:02Z' } }), workspace)
  await expect(persistTurnCommand(changed, db)).rejects.toThrow()
  expect(readTurnCommand((await db.load(workspace))[original.command_id], workspace)).toEqual(acknowledged)
 } finally { await db.close() }
})
test('fresh store read preserves original command; concurrent ACK and pending writers retain the checked ACK', async () => {
 const factory = new IDBFactory(), name = `turn-command-${crypto.randomUUID()}`, first = new DraftStore({ name, factory }), second = new DraftStore({ name, factory })
 const original = command(), ack = decodeTurnCommand(JSON.stringify({ ...original, ack: turnPreparation() }), workspace)
 await persistTurnCommand(original, first)
 await Promise.all([persistTurnCommand(ack, first), persistTurnCommand(original, second)])
 const record = (await second.load(workspace))[original.command_id]
 expect(readTurnCommand(record, workspace)).toEqual(ack)
 expect(record.text).not.toMatch(/csrf|cookie|synthetic-only-not-persisted/)
 await expect(persistTurnCommand({ ...original, actor_session_id: 'actor_other' }, second)).rejects.toThrow()
 const controller = new AbortController(); controller.abort()
 await expect(persistTurnCommand(original, first, { allowed: () => false, signal: controller.signal })).rejects.toThrow()
 expect(readTurnCommand((await first.load(workspace))[original.command_id], workspace)).toEqual(ack)
 await first.close(); await second.close()
})
test('incompatible concurrent original commands fail closed while both stored candidates remain available', async () => {
 const db = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() }), original = command()
 await persistTurnCommand(original, db)
 await db.save(workspace, original.command_id, JSON.stringify({ ...original, actor_session_id: 'actor_other' }), 0)
 const raw = (await db.load(workspace))[original.command_id]
 expect(raw.conflicts).toHaveLength(1)
 expect(() => readTurnCommand(raw, workspace)).toThrow()
 await expect(persistTurnCommand(original, db)).rejects.toThrow()
 expect((await db.load(workspace))[original.command_id]).toEqual(raw)
 await db.close()
})
test('out-of-order form saves and reload preserve latest and older unsent snapshots without overwriting either', async () => {
 const factory = new IDBFactory(), name = crypto.randomUUID(), first = new DraftStore({ name, factory }), second = new DraftStore({ name, factory })
 const one = snapshotTurnForm(workspace, actor, { ...emptyTurnFields(), message: '原 α\n ' }, null)
 const two = snapshotTurnForm(workspace, actor, { ...one.fields, message: '原 α\n 😀 final ' }, one)
 await persistTurnForm(two, first); await persistTurnForm(one, first)
 const recovered = Object.values(await second.load(workspace)).map(v => readTurnForm(v, workspace))
 expect(recovered).toHaveLength(2); expect(recovered).toContainEqual(one); expect(recovered).toContainEqual(two)
 await expect(persistTurnForm({ ...two, fields: { ...two.fields, message: 'replacement' } }, first)).rejects.toThrow()
 await first.close(); await second.close()
})

const interrupt = () => turnInterruptCommand(workspace, 'safe_new_actor', { ...codexSession(), revision: 4, active_turn_id: turnControl().id }, turnControl())
test.each([
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.body.expected_session_revision++ },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.body.turn_id = 'other_turn' },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.basis.session.id = 'other_session' },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.basis.session.active_turn_id = 'other_turn' },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.basis.turn.session_id = 'other_session' },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.basis.turn.approval_ids = ['missing_approval'] },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { Object.assign(v.basis, { extra: 'unknown' }) },
 (v: Extract<TurnCommand, { kind: 'interrupt' }>) => { v.ack = { id: v.session_id, turn_id: 'wrong', status: 'already_terminal' } },
])('interrupt frozen current-session/turn basis, body and ACK cannot drift %#', corrupt => {
 const original = interrupt()
 if (original.kind !== 'interrupt') throw new Error('Expected interrupt')
 corrupt(original)
 expect(() => decodeTurnCommand(JSON.stringify(original), workspace)).toThrow()
})
test('interrupt history preserves its complete original actor/body/key/basis and ACK under concurrent pending writer', async () => {
 const store = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() }), original = interrupt()
 try {
  const acknowledged = decodeTurnCommand(JSON.stringify({ ...original, ack: { id: original.session_id, turn_id: 'turn_test', status: 'already_terminal' } }), workspace)
  await persistTurnCommand(original, store)
  await Promise.all([persistTurnCommand(acknowledged, store), persistTurnCommand(original, store)])
  const actual = readTurnCommand((await store.load(workspace))[original.command_id], workspace)
  expect(actual).toEqual(acknowledged)
  expect(JSON.stringify(actual)).not.toMatch(/csrf|cookie/)
  await expect(persistTurnCommand({ ...original, actor_session_id: 'different_actor' }, store)).rejects.toThrow()
  expect(readTurnCommand((await store.load(workspace))[original.command_id], workspace)).toEqual(acknowledged)
 } finally { await store.close() }
})
