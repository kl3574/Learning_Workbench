import 'fake-indexeddb/auto'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { persistCommand, readCommands, type RetrievalCommand } from './retrievalCommands'
const stores: DraftStore[] = []
afterEach(async () => { vi.restoreAllMocks(); await Promise.all(stores.splice(0).map(store => store.close())) })
function fixture() {
  const name = `retrieval-race-${crypto.randomUUID()}`
  const a = new DraftStore({ name }), b = new DraftStore({ name }); stores.push(a, b)
  const ref = { entity: 'block' as const, id: 'block_race', revision: 1, sha256: 'a'.repeat(64) }
  const value: RetrievalCommand = { version: 1, workspace: `workspace_${crypto.randomUUID()}`, command_id: `retrieval_${crypto.randomUUID()}`, kind: 'rebuild', scope_refs: [ref], rejected: false, body: { scope_refs: [ref], expected_corpus_sha256: 'b'.repeat(64), provider_id: null, consent_id: null }, ack: null }
  return { a, b, value }
}
function gateActualReads(a: DraftStore, b: DraftStore) {
  let arrived = 0, release!: () => void
  const both = new Promise<void>(done => { release = done })
  for (const store of [a, b]) {
    const load = store.load.bind(store)
    vi.spyOn(store, 'load').mockImplementationOnce(async workspace => {
      const actual = await load(workspace)
      if (++arrived === 2) release()
      await both
      return actual
    })
  }
}
test('two real stores retry the same unknown key/body without making it unrecoverable', async () => {
  const { a, b, value } = fixture(); await persistCommand(value, a)
  gateActualReads(a, b)
  const outcomes = await Promise.allSettled([persistCommand(value, a), persistCommand(value, b)])
  expect(outcomes.map(outcome => outcome.status)).toEqual(['fulfilled', 'fulfilled'])
  expect(await readCommands(value.workspace, b)).toEqual([value])
  expect((await a.load(value.workspace))[value.command_id].revision).toBe(1)
})
test('simultaneous equal original ACKs remain readable after actual IDB CAS conflict', async () => {
  const { a, b, value } = fixture(); await persistCommand(value, a)
  const acknowledged: RetrievalCommand = { ...value, ack: { id: 'job_same', status: 'queued' } }
  gateActualReads(a, b)
  const outcomes = await Promise.allSettled([persistCommand(acknowledged, a), persistCommand(acknowledged, b)])
  expect(outcomes.map(outcome => outcome.status)).toEqual(['fulfilled', 'fulfilled'])
  expect((await a.load(value.workspace))[value.command_id].conflicts).toHaveLength(1)
  expect(await readCommands(value.workspace, b)).toEqual([acknowledged])
})
test('legacy exact duplicate candidates can advance to ACK without erasing different candidates', async () => {
  const { a, b, value } = fixture(); await persistCommand(value, a)
  await a.save(value.workspace, value.command_id, JSON.stringify(value), 1)
  await b.save(value.workspace, value.command_id, JSON.stringify(value), 1)
  expect((await a.load(value.workspace))[value.command_id].conflicts).toHaveLength(1)
  expect(await readCommands(value.workspace, b)).toEqual([value])
  const acknowledged: RetrievalCommand = { ...value, ack: { id: 'job_same', status: 'queued' } }
  await persistCommand(acknowledged, b)
  expect(await readCommands(value.workspace, a)).toEqual([acknowledged])
})
test.each(['key', 'body', 'ack'] as const)('different %s candidate stays intact and blocks automatic recovery', async field => {
  const { a, b, value } = fixture(); await persistCommand(value, a)
  const different = field === 'key' ? { ...value, command_id: 'command_other' }
    : field === 'body' ? { ...value, body: { ...value.body, expected_corpus_sha256: 'c'.repeat(64) } }
    : { ...value, ack: { id: 'job_other', status: 'queued' } }
  await a.save(value.workspace, value.command_id, JSON.stringify(value), 1)
  await b.save(value.workspace, value.command_id, JSON.stringify(different), 1)
  const original = await a.load(value.workspace)
  await expect(readCommands(value.workspace, b)).rejects.toThrow()
  await expect(persistCommand(value, b)).rejects.toThrow()
  expect(await a.load(value.workspace)).toEqual(original)
})
