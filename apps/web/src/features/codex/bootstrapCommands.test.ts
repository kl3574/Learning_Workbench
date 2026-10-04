import { IDBFactory } from 'fake-indexeddb'
import { expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { createCommand, decidedCommand, decodeBootstrapCommand, persistBootstrapCommand, prepareCommand, readBootstrapCommand } from './bootstrapCommands'
import { actor, preparation, workspace } from './bootstrapTestFixtures'

test.each(['expired', 'changed', 'unavailable'] as const)('an approved %s basis cannot create a new session command', validity => {
 expect(() => createCommand(workspace, actor, { ...preparation('approved'), validity })).toThrow()
})
test('approve needs current, decline tolerates unavailable, neither decides an expired preparation', () => {
 expect(() => decidedCommand(workspace, actor, { ...preparation(), validity: 'unavailable' }, 'approve_once')).toThrow()
 expect(decidedCommand(workspace, actor, { ...preparation(), validity: 'unavailable' }, 'decline').kind).toBe('decision')
 expect(() => decidedCommand(workspace, actor, { ...preparation(), validity: 'expired' }, 'decline')).toThrow()
})
test('read-only other actor and different adapter ACK cannot become this actor command', () => {
 expect(() => decidedCommand(workspace, 'session_other', preparation(), 'approve_once')).toThrow()
 const value = createCommand(workspace, actor, preparation('approved'))
 expect(() => decodeBootstrapCommand(JSON.stringify({ ...value, ack: { id: 'codex_session_test', revision: 2, status: 'ready', adapter_version: 'another-profile', capabilities: { approvals: false, interrupt: false, artifacts: false } } }), workspace)).toThrow()
})
test('original body/key/basis and ACK survive a fresh store, with no session secrets or rebasing', async () => {
 const factory = new IDBFactory(), name = `command-${crypto.randomUUID()}`, first = new DraftStore({ name, factory })
 const value = prepareCommand(workspace, actor)
 await persistBootstrapCommand(value, first)
 const second = new DraftStore({ name, factory }), recovered = readBootstrapCommand((await second.load(workspace))[value.command_id], workspace)
 expect(recovered).toEqual(value)
 const acknowledged = decodeBootstrapCommand(JSON.stringify({ ...value, ack: preparation() }), workspace)
 await persistBootstrapCommand(acknowledged, second)
 expect(await persistBootstrapCommand(value, first)).toEqual(acknowledged)
 const record = (await first.load(workspace))[value.command_id]
 expect(record.text).not.toMatch(/csrf|cookie|synthetic-only-not-persisted/)
 expect(readBootstrapCommand(record, workspace)).toEqual(acknowledged)
 await expect(persistBootstrapCommand({ ...value, actor_session_id: 'session_other' }, first)).rejects.toThrow()
})
test('aborted storage guard preserves the original pending command and received ACK remains caller-owned', async () => {
 const db = new DraftStore({ name: 'aborted-command', factory: new IDBFactory() }), value = prepareCommand(workspace, actor)
 await persistBootstrapCommand(value, db)
 const controller = new AbortController(); controller.abort()
 await expect(persistBootstrapCommand({ ...value, ack: preparation() } as typeof value, db, { allowed: () => false, signal: controller.signal })).rejects.toThrow()
 expect(readBootstrapCommand((await db.load(workspace))[value.command_id], workspace)).toEqual(value)
})
