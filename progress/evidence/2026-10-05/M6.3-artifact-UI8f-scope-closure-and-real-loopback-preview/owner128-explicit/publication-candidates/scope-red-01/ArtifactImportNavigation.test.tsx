import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import type { ImportPreview, ImportDraftSnapshot, JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore } from '../../workbench/DraftStore'
import { CodexArtifactsPanel } from './CodexArtifactsPanel'
import { artifactAck, artifactActor, artifactImport, artifactManifest, artifactWorkspace } from './artifactFixtures'
import { artifactClient } from './artifactClient'
import { makeArtifactCommand, persistArtifactCommand } from './artifactCommands'
import { session } from './bootstrapTestFixtures'
afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals() })
test('explicit checked aggregate child opens actual ordinary Import GET and draft preview without commit, Review or publish POST', async () => {
 const store = new DraftStore({ name: `artifact-nav-${crypto.randomUUID()}`, factory: new IDBFactory() }), forms = new DraftStore({ name: `artifact-navform-${crypto.randomUUID()}`, factory: new IDBFactory() })
 const command = { ...makeArtifactCommand(artifactWorkspace, artifactActor, artifactManifest(), ['artifact_synthetic_md']), ack: artifactAck }
 const snapshot: ImportPreview = { id: 'import_artifact_child', status: 'preview_ready', input_sha256: artifactManifest().manifest.entries[0].sha256, warnings: [], candidate_summary: { course_title: '回导合成候选', lesson_count: 0, block_count: 0, unresolved_refs: [] }, preview_refs: ['draft_artifact_child'] }
 const job: JobSnapshot = { id: 'job_artifact_child', workspace_id: artifactWorkspace, kind: 'import_parse', status: 'awaiting_approval', revision: 3, created_at: '2026-10-04T00:00:00Z', updated_at: '2026-10-04T00:00:00Z', progress: { completed: 1, total: 1, label: 'preview' }, result_refs: [], warnings: [], error: null }
 const draft: ImportDraftSnapshot = { id: 'draft_artifact_child', kind: 'course', revision: 1, base_ref: null, state: 'draft', candidate_sha256: 'a'.repeat(64), warnings: [], payload: { id: 'course_artifact', revision: 1, entity: 'course', title: '真实普通预览组件合成正文 α', audience: '测试', lesson_refs: [] } }
 const calls: string[] = []
 vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
  calls.push(`${init.method} ${path}`); expect(init.method).toBe('GET')
  const body = path === '/api/v1/session' ? { ...session(), workspace_id: artifactWorkspace, actor_session_id: artifactActor }
   : path.startsWith('/api/v1/courses') ? { items: [], next_cursor: null }
    : path === '/api/v1/codex/artifact-imports/job_artifact_import' ? artifactImport()
     : path === '/api/v1/imports/import_artifact_child' ? snapshot
      : path === '/api/v1/jobs/job_artifact_child' ? job
       : path === '/api/v1/drafts/draft_artifact_child' ? draft : null
  if (!body) throw new Error(`Unexpected synthetic route ${path}`)
  return new Response(JSON.stringify(body))
 }))
 try {
  await persistArtifactCommand(command, store)
  render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={artifactClient} store={store} formStore={forms} />)
  expect(calls).toEqual([]); fireEvent.click(screen.getByText('读取产物记录与权限')); await screen.findByText(/产物本机记录已读取/)
  fireEvent.click(screen.getByText('读取回导当前子项 job_artifact_import')); await screen.findByLabelText('回导聚合当前 GET')
  fireEvent.click(screen.getByText('打开普通 Import 预览 import_artifact_child'))
  const read = await screen.findByText('读取指定回导预览 import_artifact_child')
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false))
  expect(calls).not.toContain('GET /api/v1/imports/import_artifact_child')
  fireEvent.click(read); await screen.findByText('真实普通预览组件合成正文 α')
  expect(calls).toContain('GET /api/v1/imports/import_artifact_child'); expect(calls).toContain('GET /api/v1/jobs/job_artifact_child'); expect(calls).toContain('GET /api/v1/drafts/draft_artifact_child')
  expect(calls.every(v => v.startsWith('GET '))).toBe(true)
  expect((screen.getByText('确认导入当前候选') as HTMLButtonElement).disabled).toBe(true)
  expect(JSON.parse((await store.load(artifactWorkspace))[command.command_id].text).ack).toEqual(artifactAck)
 } finally { cleanup(); await store.close(); await forms.close() }
})

test('a clean isolated preview does not lock the new current actor out of their own checked Import child', async () => {
 const store = new DraftStore({ name: `artifact-scope-${crypto.randomUUID()}`, factory: new IDBFactory() }), forms = new DraftStore({ name: `artifact-scopeform-${crypto.randomUUID()}`, factory: new IDBFactory() })
 let currentActor = artifactActor
 const otherActor = 'session_artifact_other', otherAck = { id: 'job_artifact_other', status: 'queued' as const }
 const first = { ...makeArtifactCommand(artifactWorkspace, artifactActor, artifactManifest(), ['artifact_synthetic_md']), ack: artifactAck }
 const second = { ...makeArtifactCommand(artifactWorkspace, otherActor, artifactManifest(), ['artifact_synthetic_md']), ack: otherAck }
 const secondView = { ...artifactImport(), actor_session_id: otherActor, job: { ...otherAck, status: 'completed' as const }, items: [{ ...artifactImport().items[0], import_id: 'import_artifact_other', job: { id: 'job_artifact_other_child', status: 'awaiting_approval' as const } }] }
 const calls: string[] = []
 vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
  calls.push(`${init.method} ${path}`); expect(init.method).toBe('GET')
  const body = path === '/api/v1/session' ? { ...session(), workspace_id: artifactWorkspace, actor_session_id: currentActor }
   : path.startsWith('/api/v1/courses') ? { items: [], next_cursor: null }
    : path === '/api/v1/codex/artifact-imports/job_artifact_import' ? artifactImport()
     : path === '/api/v1/codex/artifact-imports/job_artifact_other' ? secondView : null
  if (!body) throw new Error(`Unexpected synthetic route ${path}`)
  return new Response(JSON.stringify(body))
 }))
 try {
  await persistArtifactCommand(first, store); await persistArtifactCommand(second, store)
  const originals = await store.load(artifactWorkspace)
  render(<CodexArtifactsPanel workspace={artifactWorkspace} writeAdmitted port={artifactClient} store={store} formStore={forms} />)
  fireEvent.click(screen.getByText('读取产物记录与权限')); await screen.findByText(/产物本机记录已读取/)
  fireEvent.click(screen.getByText('读取回导当前子项 job_artifact_import')); await screen.findByLabelText('回导聚合当前 GET')
  fireEvent.click(screen.getByText('打开普通 Import 预览 import_artifact_child'))
  await waitFor(() => expect((screen.getByText('读取指定回导预览 import_artifact_child') as HTMLButtonElement).disabled).toBe(false))
  currentActor = otherActor
  fireEvent.click(screen.getByText('读取产物记录与权限')); await screen.findByText('读取回导当前子项 job_artifact_other')
  fireEvent.click(screen.getByText('读取回导当前子项 job_artifact_other')); await screen.findByText(/Import import_artifact_other/)
  const open = screen.getByText('打开普通 Import 预览 import_artifact_other')
  expect((open as HTMLButtonElement).disabled, 'the old clean hidden preview must not lock the current actor child').toBe(false)
  fireEvent.click(open)
  await waitFor(() => expect((screen.getByText('读取指定回导预览 import_artifact_other') as HTMLButtonElement).disabled).toBe(false))
  expect(await store.load(artifactWorkspace)).toEqual(originals); expect(calls.every(v => v.startsWith('GET '))).toBe(true)
 } finally { cleanup(); await store.close(); await forms.close() }
})
