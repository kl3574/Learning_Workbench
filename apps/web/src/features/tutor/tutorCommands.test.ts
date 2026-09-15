import { IDBFactory } from 'fake-indexeddb'
import { describe, expect, it } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { decodeTutorCommand, makeTutorCommand, persistTutorCommand, readTutorCommand } from './tutorCommands'
import { tutorBinding, tutorScope, tutorThread } from './tutorFixtures'
const create = () => makeTutorCommand('workspace_tutor_test', 'root_test', { kind: 'thread', body: { scope: tutorScope, binding: tutorBinding, title: tutorThread().title } })
const store = () => new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() })
describe('actual IndexedDB immutable Tutor commands', () => {
  it('persists before send and recovers unchanged key/body across store reads', async () => {
    const disk = store(), original = create()
    await persistTutorCommand(original, disk)
    const record = (await disk.load(original.workspace_id))[original.command_id]
    expect(readTutorCommand(record, original.workspace_id)).toEqual(original)
    expect(() => decodeTutorCommand(record.text, 'workspace_other')).toThrow()
  })
  it('concurrent identical pending retries and an actual ACK converge without erasing acknowledgement', async () => {
    const disk = store(), original = create()
    await persistTutorCommand(original, disk)
    const ack = { ...original, ack: tutorThread() } as typeof original
    await Promise.all([persistTutorCommand(original, disk), persistTutorCommand(ack, disk)])
    expect(await persistTutorCommand(original, disk)).toEqual(ack)
    expect(readTutorCommand((await disk.load(original.workspace_id))[original.command_id], original.workspace_id)).toEqual(ack)
  })
  it('never merges different key/body/ACK candidates', async () => {
    const disk = store(), original = create()
    await persistTutorCommand(original, disk)
    const different = { ...original, body: { ...original.body, title: '不同正文' } }
    await disk.save(original.workspace_id, original.command_id, JSON.stringify(different), 0)
    const record = (await disk.load(original.workspace_id))[original.command_id]
    expect(record.conflicts).toHaveLength(1)
    expect(() => readTutorCommand(record, original.workspace_id)).toThrow()
    expect(() => decodeTutorCommand(JSON.stringify({ ...original, ack: { ...tutorThread(), title: '伪造回执' } }), original.workspace_id)).toThrow()
  })
  it('keeps a definite rejection separate from unknown result and immutable command', async () => {
    const disk = store(), original = create(), rejected = { ...original, rejection: { status: 412, code: 'REVISION_MISMATCH' } }
    await persistTutorCommand(original, disk); await persistTutorCommand(rejected, disk)
    expect((await persistTutorCommand(original, disk)).rejection?.status).toBe(412)
    expect(() => decodeTutorCommand(JSON.stringify({ ...rejected, ack: tutorThread() }), original.workspace_id)).toThrow()
  })
})
