import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftEditor } from './DraftEditor'
import type { EditPort } from './editClient'
import { editFixture } from './editFixtures'
import { editBuffers, editCommands } from './editJournal'
import { codeMirrorTestGeometry, replaceSource } from './sourceEditorTestSupport'
import { reviewSession } from '../draftReview/reviewFixtures'
import type { LoadedBlock } from '../reader/contentClient'
import { canonical, digest } from '../retrieval/retrievalModel'

codeMirrorTestGeometry()
afterEach(async () => { cleanup(); vi.restoreAllMocks(); await Promise.all([editBuffers.close(), editCommands.close()]) })

test('original concept IDs remain read-only in their original order while only title and body are submitted', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, concepts = ['original_concept_second', 'original_concept_first']
  const body = 'Original synthetic concept-bound text.\n'
  const metadata: LoadedBlock['block'] = { schema_version: '3.0.0', entity: 'block', id: 'block_edit_synthetic', revision: 1, kind: 'text', title: 'Original concept-bound text', body_path: 'content/edit-synthetic.md', body_sha256: digest(body), concepts, citations: [], depends_on: [] }
  const ref = { entity: 'block' as const, id: metadata.id, revision: 1, sha256: digest(canonical(metadata)) }
  const block: LoadedBlock = { block_ref: ref, block: metadata, body, citations: [], unresolved_citation_ids: [], warnings: [], original_source: null }
  const snapshot = editFixture(1, metadata.title, body)
  snapshot.base_ref = ref; snapshot.payload.base_ref = ref; snapshot.candidate.candidate_sha256 = digest(canonical(snapshot.payload))
  const port: EditPort = { session: async () => reviewSession(workspace), verifyBase: vi.fn(async () => {}), read: vi.fn(async () => snapshot),
    create: vi.fn(async () => ({ draft_id: snapshot.candidate.draft_id, revision: 1, base_ref: ref, state: 'draft' as const })),
    patch: vi.fn(async () => ({ draft_id: snapshot.candidate.draft_id, revision: 2, validation_warnings: [] })) }
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  const shown = await screen.findByLabelText('原概念 ID 只读记录')
  expect(JSON.parse(shown.textContent!)).toEqual(concepts)
  expect(shown.tagName).toBe('PRE')
  expect(screen.queryByRole('textbox', { name: /概念/ })).toBeNull()
  expect(port.create).not.toHaveBeenCalled(); expect(port.patch).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '从此准确修订明确创建编辑稿' }))
  const read = await screen.findByRole('button', { name: `另行读取草稿头 ${snapshot.candidate.draft_id}` })
  expect(port.create).toHaveBeenCalledWith({ kind: 'block', base_ref: ref, title: metadata.title }, expect.any(String))
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  await screen.findByRole('region', { name: '当前本机编辑' })
  await waitFor(() => expect(screen.getByLabelText('本机标题').closest('fieldset')!.disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('本机标题'), { target: { value: 'Explicit edited title' } })
  act(() => replaceSource(screen.getByLabelText('本机正文'), 'Explicit edited body.\n'))
  const submit = screen.getByRole('button', { name: '明确提交本机标题与正文' }) as HTMLButtonElement
  await waitFor(() => expect(submit.disabled).toBe(false)); fireEvent.click(submit)
  await waitFor(() => expect(port.patch).toHaveBeenCalledExactlyOnceWith(snapshot.candidate.draft_id,
    { expected_revision: 1, patches: [{ field: 'title', value: 'Explicit edited title' }, { field: 'body_markdown', value: 'Explicit edited body.\n' }] }, expect.any(String)))
  expect(JSON.parse(screen.getByLabelText('原概念 ID 只读记录').textContent!)).toEqual(concepts)
})

test.each(['learner', 'independent', 'open_book'] as const)('original concept IDs stay hidden when %s denies the current authoring view', async mode => {
  const workspace = `workspace_${crypto.randomUUID()}`, body = 'Synthetic protected original.\n'
  const metadata: LoadedBlock['block'] = { schema_version: '3.0.0', entity: 'block', id: 'block_edit_synthetic', revision: 1, kind: 'text', title: 'Protected original', body_path: 'content/edit-synthetic.md', body_sha256: digest(body), concepts: ['hidden_original_concept'], citations: [], depends_on: [] }
  const ref = { entity: 'block' as const, id: metadata.id, revision: 1, sha256: digest(canonical(metadata)) }
  const block: LoadedBlock = { block_ref: ref, block: metadata, body, citations: [], unresolved_citation_ids: [], warnings: [], original_source: null }
  const session = reviewSession(workspace)
  if (mode === 'learner') session.role = 'learner'
  if (mode === 'independent') session.active_independent_attempt_id = 'attempt_concept_independent'
  if (mode === 'open_book') session.active_open_book_attempt_id = 'attempt_concept_open_book'
  const port: EditPort = { session: vi.fn(async () => session), verifyBase: vi.fn(), read: vi.fn(), create: vi.fn(), patch: vi.fn() }
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await waitFor(() => expect(port.session).toHaveBeenCalledOnce())
  expect(screen.queryByLabelText('原概念 ID 只读记录')).toBeNull()
  expect(screen.queryByText(/hidden_original_concept/)).toBeNull()
  expect(screen.queryByRole('button', { name: '从此准确修订明确创建编辑稿' })).toBeNull()
  expect(port.create).not.toHaveBeenCalled(); expect(port.patch).not.toHaveBeenCalled()
})
