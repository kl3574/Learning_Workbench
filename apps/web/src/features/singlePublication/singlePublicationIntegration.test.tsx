import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuthoringPort } from '../authoring/authoringClient'
import { AuthoringPanel } from '../authoring/AuthoringPanel'
import { useAuthoring } from '../authoring/useAuthoring'
import { providerFixture } from '../providers/testFixtures'
import { singlePublicationFixture } from './singlePublicationFixtures'
import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
afterEach(cleanup)
function fixture() {
  const f = singlePublicationFixture(); f.draft.state = 'published'; f.draft.published_ref = f.ack
  const numeric = { ...f.numeric, revision: 1, expired: false, decision: 'pending' as const, job: null, job_revision: null, result: null }
  const job: JobSnapshot = { id: f.generation.summary.id, workspace_id: f.workspace, kind: 'authoring', status: 'completed', revision: 3, created_at: f.generation.summary.created_at, updated_at: f.generation.summary.updated_at, progress: { completed: 1, total: 1, label: '合成已完成' }, result_refs: [], warnings: [], error: null }
  const port: AuthoringPort = { session: f.port.session, list: vi.fn(async () => ({ items: [job], next_cursor: null })), read: f.port.generation, draft: f.port.draft, numeric: vi.fn(async () => numeric), preview: vi.fn(), prepare: vi.fn(), job: vi.fn(async () => job), cancel: vi.fn(),
    decide: vi.fn<AuthoringPort['decide']>(async (_id, body) => ({ id: numeric.id, revision: 2, operation_sha256: body.operation_sha256, decision: body.decision, applied: true, job: null })) }
  return { ...f, port, numeric }
}
test('Authoring actual published projection blocks new preview and approval while showing original ref and preserving decline', async () => {
  const f = fixture(); render(<AuthoringPanel workspace={f.workspace} paused={false} currentBlock={null} port={f.port} provider={providerFixture().port} onState={vi.fn()} />)
  // This scenario starts after academic command recovery has completed. The
  // pre-existing control/subject initialization race is tracked separately.
  await waitFor(() => expect(screen.getByLabelText('例题主题').matches(':disabled')).toBe(false))
  const read = await screen.findByRole('button', { name: `读取创作详情 ${f.generation.summary.id}` }); await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  fireEvent.click(await screen.findByRole('button', { name: '读取这份准确例题候选' }))
  await screen.findByText(/状态 published/); expect(screen.getByText(/原发布引用：/)).toBeTruthy()
  expect((screen.getByRole('button', { name: '明确准备独立数值检查预览' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: `读取数值检查 ${f.numeric.id}` })); await screen.findByRole('button', { name: '明确拒绝本次数值执行' })
  expect((screen.getByRole('button', { name: '明确批准本次数值执行' }) as HTMLButtonElement).disabled).toBe(true)
  await waitFor(() => expect((screen.getByRole('button', { name: '明确拒绝本次数值执行' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '明确拒绝本次数值执行' })); await waitFor(() => expect(f.port.decide).toHaveBeenCalledTimes(1))
  expect(vi.mocked(f.port.decide).mock.calls[0][1].decision).toBe('decline'); expect(f.port.preview).not.toHaveBeenCalled()
})
test('Authoring command admission also rejects new preview/approve against known published single without blocking decline', async () => {
  const f = fixture(), hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.read(f.generation.summary.id)); await act(() => hook.result.current.readDraft()); await act(() => hook.result.current.readNumeric(f.numeric.id))
  await act(() => hook.result.current.create({ kind: 'numeric_preview', draft_id: f.draft.candidate.draft_id, body: { candidate: f.draft.candidate } }))
  await act(() => hook.result.current.create({ kind: 'numeric_decision', check_id: f.numeric.id, body: { decision: 'approve_once', expected_revision: 1, operation_sha256: f.numeric.operation_sha256 } }))
  expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled()
  await act(() => hook.result.current.create({ kind: 'numeric_decision', check_id: f.numeric.id, body: { decision: 'decline', expected_revision: 1, operation_sha256: f.numeric.operation_sha256 } }))
  expect(f.port.decide).toHaveBeenCalledTimes(1)
})
