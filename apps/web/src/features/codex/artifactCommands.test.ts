import { IDBFactory } from 'fake-indexeddb'
import { expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { checkedArtifact } from './artifactClient'
import { decodeArtifactCommand, dispatchArtifactCommand, makeArtifactCommand, persistArtifactCommand, readArtifactImport } from './artifactCommands'
import { artifactAck, artifactActor, artifactImport, artifactManifest, artifactWorkspace } from './artifactFixtures'
const command = () => makeArtifactCommand(artifactWorkspace, artifactActor, artifactManifest(), ['artifact_synthetic_md'])
test('golden Python-hashed Unicode manifest is closed and detects byte, total, membership and path damage', () => {
 expect(checkedArtifact('CodexArtifactManifestView', artifactManifest())).toEqual(artifactManifest())
 for (const mutate of [(v: ReturnType<typeof artifactManifest>) => { v.manifest.entries[0].logical_path = 'else.md' }, (v: ReturnType<typeof artifactManifest>) => { v.manifest.total_bytes++ }, (v: ReturnType<typeof artifactManifest>) => { v.manifest.entries.push(v.manifest.entries[0]) }, (v: ReturnType<typeof artifactManifest>) => { v.manifest.entries[0].logical_path = '../private' }, (v: ReturnType<typeof artifactManifest>) => { Object.assign(v.manifest, { extra: true }) }]) {
  const value = artifactManifest(); mutate(value); expect(() => checkedArtifact('CodexArtifactManifestView', value)).toThrow()
 }
})
test('command rejects body, basis, closed ACK and actor shape changes', () => {
 for (const mutate of [(c: ReturnType<typeof command>) => { c.body.turn_id = 'turn_other' }, (c: ReturnType<typeof command>) => { c.body.artifact_ids.push(c.body.artifact_ids[0]) }, (c: ReturnType<typeof command>) => { c.body.artifact_ids = ['artifact_synthetic_note'] }, (c: ReturnType<typeof command>) => { c.target_id = 'session_other' }, (c: ReturnType<typeof command>) => { c.ack = { ...artifactAck, status: 'completed' } }, (c: ReturnType<typeof command>) => { Object.assign(c, { token: 'not-allowed' }) }]) {
  const value = command(); mutate(value); expect(() => decodeArtifactCommand(JSON.stringify(value), artifactWorkspace)).toThrow()
 }
})
test('stored original full body and ACK cannot be replaced, ACK replay performs zero POST', async () => {
 const store = new DraftStore({ name: `artifact-command-${crypto.randomUUID()}`, factory: new IDBFactory() }), original = command(), port = { import: vi.fn(async () => artifactAck) }
 try {
  const ack = await dispatchArtifactCommand(original, port, store)
  expect(await dispatchArtifactCommand(original, port, store)).toEqual(ack); expect(port.import).toHaveBeenCalledTimes(1)
  await expect(persistArtifactCommand({ ...ack, actor_session_id: 'actor_other' }, store)).rejects.toThrow()
  await expect(persistArtifactCommand({ ...ack, ack: { ...artifactAck, id: 'job_other' } }, store)).rejects.toThrow()
 } finally { await store.close() }
})
test('a checked late ACK is delivered to retention before a delivery denial and never claimed durable', async () => {
 const store = new DraftStore({ name: `artifact-command-${crypto.randomUUID()}`, factory: new IDBFactory() }), original = command(), onAck = vi.fn()
 try {
  await expect(dispatchArtifactCommand(original, { import: async () => artifactAck }, store, { onAck, beforeDelivery: async () => { throw new Error('actor changed') } })).rejects.toThrow('actor changed')
  expect(onAck).toHaveBeenCalledWith({ ...original, ack: artifactAck }); expect(JSON.parse((await store.load(artifactWorkspace))[original.command_id].text).ack).toBeNull()
 } finally { await store.close() }
})
test('aggregate current GET preserves original queued ACK and checks ordered source, actor, job and child identities', () => {
 const c = { ...command(), ack: artifactAck }
 expect(readArtifactImport(artifactImport(), c).job.status).toBe('completed'); expect(c.ack.status).toBe('queued')
 for (const mutate of [(v: ReturnType<typeof artifactImport>) => { v.actor_session_id = 'actor_other' }, (v: ReturnType<typeof artifactImport>) => { v.job.id = 'job_other' }, (v: ReturnType<typeof artifactImport>) => { v.items[0].source_sha256 = 'a'.repeat(64) }, (v: ReturnType<typeof artifactImport>) => { v.items.push(v.items[0]) }, (v: ReturnType<typeof artifactImport>) => { v.items[0].job.id = v.job.id }, (v: ReturnType<typeof artifactImport>) => { v.manifest_sha256 = 'a'.repeat(64) }]) {
  const v = artifactImport(); mutate(v); expect(() => readArtifactImport(v, c)).toThrow()
 }
})
