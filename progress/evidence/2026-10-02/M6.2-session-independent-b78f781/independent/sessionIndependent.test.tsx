import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError } from '../../api/client'
import { reviewSession } from '../draftReview/reviewFixtures'
import { editBase, editFixture } from './editFixtures'
import { editCommands, editBuffers, persistCommand, type EditCommand } from './editJournal'
import type { EditPort } from './editClient'
import { useDraftEditor } from './useDraftEditor'

afterEach(async () => { cleanup(); vi.restoreAllMocks(); await Promise.all([editCommands.close(), editBuffers.close()]) })
async function fixture(kind: 'create' | 'patch' = 'patch') {
  const workspace = `workspace_${crypto.randomUUID()}`, baseline = editFixture(), session = reviewSession(workspace)
  const original: EditCommand = { version: 2, workspace_id: workspace, actor_session_id: session.actor_session_id, key: `editcmd_${crypto.randomUUID()}`, page: 'page_independent_previous', access: 0,
    route: kind === 'create' ? 'POST /api/v1/drafts' : 'PATCH /api/v1/drafts/draft_edit_synthetic', base_ref: editBase,
    operation: kind === 'create' ? { kind, body: { kind: 'block', base_ref: editBase, title: '独立原创建' } }
      : { kind, baseline, local: { title: '独立原标题', body_markdown: '独立原正文 🧠\n' }, body: { expected_revision: 1, patches: [{ field: 'title', value: '独立原标题' }, { field: 'body_markdown', value: '独立原正文 🧠\n' }] } }, ack: null, rejection: null }
  await persistCommand(original)
  const before = await editCommands.load(workspace)
  const port: EditPort = { session: vi.fn(async () => session), verifyBase: vi.fn(async () => {}), read: vi.fn(async () => baseline), create: vi.fn(), patch: vi.fn() }
  const hook = renderHook(({ paused }) => useDraftEditor(workspace, editBase, paused, port), { initialProps: { paused: false } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  return { workspace, baseline, session, original, before, port, hook }
}
test.each(['workspace', 'revoked', 'missing_actor'] as const)('fresh replay Session failure %s hides material and preserves exact unknown journal', async fault => {
  const f = await fixture()
  if (fault === 'workspace') vi.mocked(f.port.session).mockResolvedValueOnce({ ...f.session, workspace_id: 'workspace_other' })
  if (fault === 'revoked') vi.mocked(f.port.session).mockRejectedValueOnce(new ApiError(401, 'Session revoked', 'SESSION_REQUIRED'))
  if (fault === 'missing_actor') { const invalid: Partial<typeof f.session> = { ...f.session }; delete invalid.actor_session_id; vi.mocked(f.port.session).mockResolvedValueOnce(invalid as typeof f.session) }
  await act(() => f.hook.result.current.execute(f.original))
  expect(f.hook.result.current.ready).toBe(false); expect(f.hook.result.current.commands).toEqual([])
  expect(f.port.read).not.toHaveBeenCalled(); expect(f.port.patch).not.toHaveBeenCalled(); expect(f.port.create).not.toHaveBeenCalled()
  expect(await editCommands.load(f.workspace)).toEqual(f.before)
})
test.each(['create', 'patch'] as const)('late permission response after Policy pause cannot execute %s', async kind => {
  const f = await fixture(kind)
  let resolve!: (value: typeof f.session) => void
  vi.mocked(f.port.session).mockReturnValueOnce(new Promise(done => { resolve = done }))
  let pending!: Promise<void>; act(() => { pending = f.hook.result.current.execute(f.original) })
  f.hook.rerender({ paused: true })
  await act(async () => { resolve(f.session); await pending })
  expect(f.hook.result.current.ready).toBe(false); expect(f.port.verifyBase).not.toHaveBeenCalled(); expect(f.port.read).not.toHaveBeenCalled()
  expect(f.port.patch).not.toHaveBeenCalled(); expect(f.port.create).not.toHaveBeenCalled(); expect(await editCommands.load(f.workspace)).toEqual(f.before)
})
test.each(['create', 'patch'] as const)('damaged exact original %s material is not converted to a mutation rejection or new command', async kind => {
  const f = await fixture(kind)
  if (kind === 'create') vi.mocked(f.port.verifyBase).mockRejectedValueOnce(new ApiError(409, 'Original hash mismatch', 'CONTENT_INTEGRITY_ERROR'))
  else vi.mocked(f.port.read).mockResolvedValueOnce({ ...f.baseline, candidate: { ...f.baseline.candidate, candidate_sha256: 'a'.repeat(64) } })
  await act(() => f.hook.result.current.execute(f.original))
  expect(f.port.patch).not.toHaveBeenCalled(); expect(f.port.create).not.toHaveBeenCalled(); expect(await editCommands.load(f.workspace)).toEqual(f.before)
})
