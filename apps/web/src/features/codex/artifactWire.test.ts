import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { artifactClient } from './artifactClient'
import { dispatchArtifactCommand, type ArtifactCommand } from './artifactCommands'
import { artifactAck, artifactActor, artifactManifest, artifactWorkspace } from './artifactFixtures'
afterEach(() => vi.unstubAllGlobals())
test('actual selected-artifact POST persists the original actor, key, full manifest and ordered body before transport', async () => {
 const store = new DraftStore({ name: `artifact-wire-${crypto.randomUUID()}`, factory: new IDBFactory() }), basis = artifactManifest()
 const original: ArtifactCommand = { version: 1, workspace_id: artifactWorkspace, actor_session_id: artifactActor, command_id: 'artifact_original_key',
  target_id: basis.manifest.session_id, route: 'POST /api/v1/codex/sessions/{id}/artifacts/import', basis,
  body: { turn_id: basis.manifest.turn_id, artifact_ids: [basis.manifest.entries[0].artifact_id], expected_manifest_sha256: basis.manifest_sha256 }, ack: null, error: null }
 try {
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
   expect(path).toBe('/api/v1/codex/sessions/codex_session_synthetic/artifacts/import')
   expect(init.method).toBe('POST'); expect(new Headers(init.headers).get('Idempotency-Key')).toBe(original.command_id)
   expect(JSON.parse(init.body as string)).toEqual(original.body)
   const durable = (await store.load(artifactWorkspace))[original.command_id]
   expect(durable, 'the original selected command must exist before any actual POST').toBeDefined()
   expect(JSON.parse(durable.text)).toEqual(original)
   return new Response(JSON.stringify(artifactAck), { status: 202 })
  }))
  const result = await dispatchArtifactCommand(original, artifactClient, store)
  expect(result.ack).toEqual(artifactAck)
  expect(JSON.parse((await store.load(artifactWorkspace))[original.command_id].text)).toEqual(result)
 } finally { await store.close() }
})
