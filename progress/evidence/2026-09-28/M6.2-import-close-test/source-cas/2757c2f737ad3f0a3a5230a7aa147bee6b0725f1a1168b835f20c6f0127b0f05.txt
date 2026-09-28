import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
const state = vi.hoisted(() => ({ workspace: 'workspace_review_shell', importConfirmed: false, publication: false, commit: vi.fn() }))
vi.mock('../../workbench/useWorkbench', async () => {
  const { emptySession } = await import('../../workbench/model')
  return { useWorkbench: () => ({ session: emptySession(), set: vi.fn(), status: 'saved', uiReady: true, error: '', drafts: {}, updateDraft: vi.fn(), reconnect: vi.fn(), draftConflicts: {}, draftSaving: {}, draftErrors: {}, chooseDraft: vi.fn(), draftResolving: {}, workspaceId: state.workspace, recoverable: [], restorePending: false, comparison: null, retainLocal: vi.fn(), draftBases: {}, draftStored: {} }) }
})
vi.mock('../assessment/useWorkspacePolicy', () => ({ useWorkspacePolicy: () => ({ known: true, independentId: null, openBookId: null, error: '', refresh: () => {} }) }))
vi.mock('../routes/useRoutes', () => ({ useRoutes: () => ({ records: [], loading: false, error: '', refresh: () => {} }) }))
vi.mock('../learning/useConceptStates', () => ({ useConceptStates: () => ({ value: null, error: '' }) }))
vi.mock('../../workbench/Tutor', () => ({ Tutor: () => null }))
vi.mock('../imports/useImportWorkflow', async () => {
  const { reviewCandidate, reviewSession } = await import('./reviewFixtures')
  const { publicationDraft } = await import('../draftPublication/publicationFixtures')
  return { useImportWorkflow: () => ({ snapshot: null, active: null, auth: reviewSession(state.workspace), accessReady: true,
    accepted: [], mapping: [], courses: [], recovery: [], courseCursor: null, busy: false, confirmed: state.importConfirmed,
    draft: state.publication ? publicationDraft : { id: reviewCandidate.draft_id, revision: 1, kind: 'block', candidate_sha256: reviewCandidate.candidate_sha256, state: 'draft' }, commit: state.commit }) }
})
HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
import { Shell } from '../../workbench/Shell'
import { publicationDraft, publicationReceipt } from '../draftPublication/publicationFixtures'
import { publicationCommandStore } from '../draftPublication/publicationCommands'
import { machineReceipt, reviewSession, safeReviewJob } from './reviewFixtures'
import { rememberReviewJob, reviewCommandStore, reviewControlStore, reviewJobStore } from './reviewCommands'
afterEach(async () => { state.publication = false; cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await Promise.all([reviewCommandStore.close(), reviewControlStore.close(), reviewJobStore.close(), publicationCommandStore.close()]) })

test('actual Import and Shell preserve review reason until explicit close without submitting import or review', async () => {
  state.workspace = `workspace_${crypto.randomUUID()}`
  const calls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    calls.push(`${init.method} ${path}`)
    const value = path === '/api/v1/session' ? reviewSession(state.workspace)
      : path === `/api/v1/jobs/${machineReceipt.id}` ? safeReviewJob(state.workspace)
        : path === `/api/v1/reviews/${machineReceipt.id}` ? machineReceipt : undefined
    if (!value || init.method !== 'GET') throw new Error('Unexpected write or endpoint in Shell review fixture')
    return new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } })
  }))
  await rememberReviewJob(state.workspace, machineReceipt.id)
  render(<Shell />)
  fireEvent.click(screen.getByRole('button', { name: '导入' }))
  const dialog = screen.getByRole('dialog', { name: '导入' })
  fireEvent.click(within(dialog).getByRole('button', { name: '打开候选审核与恢复' }))
  const readJob = await screen.findByRole('button', { name: `读取审核任务 ${machineReceipt.id}` })
  await waitFor(() => expect((readJob as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(readJob)
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  const reason = await screen.findByLabelText('审核理由')
  await waitFor(() => expect((reason as HTMLTextAreaElement).disabled).toBe(false))
  fireEvent.change(reason, { target: { value: 'Synthetic unsubmitted reason' } })
  fireEvent.click(within(dialog).getByRole('button', { name: '关闭导入' }))
  const confirm = await screen.findByRole('dialog', { name: '保留审核原命令' })
  expect((reason as HTMLTextAreaElement).value).toBe('Synthetic unsubmitted reason')
  fireEvent.click(within(confirm).getByRole('button', { name: '返回导入与审核' }))
  expect((screen.getByLabelText('审核理由') as HTMLTextAreaElement).value).toBe('Synthetic unsubmitted reason')
  fireEvent.click(within(dialog).getByRole('button', { name: '关闭导入' }))
  const discard = screen.getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭' }) as HTMLButtonElement
  await waitFor(() => expect(discard.disabled).toBe(false)); fireEvent.click(discard)
  await waitFor(() => expect(screen.queryByRole('dialog', { name: '导入' })).toBeNull())
  expect(state.commit).not.toHaveBeenCalled(); expect(state.importConfirmed).toBe(false)
  expect(calls.every(value => value.startsWith('GET '))).toBe(true)
})

test('Import close stays blocked during the current publication ledger read and requires a new explicit enabled click', async () => {
  state.workspace = `workspace_${crypto.randomUUID()}`
  let holdPublication = false, release!: () => void, heldLoads = 0
  const barrier = new Promise<void>(done => { release = done }), calls: string[] = []
  const originalLoad = publicationCommandStore.load.bind(publicationCommandStore)
  vi.spyOn(publicationCommandStore, 'load').mockImplementation(async (...args) => {
    if (holdPublication) { heldLoads++; await barrier }
    return originalLoad(...args)
  })
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    calls.push(`${init.method} ${path}`)
    const value = path === '/api/v1/session' ? reviewSession(state.workspace)
      : path === `/api/v1/jobs/${machineReceipt.id}` ? safeReviewJob(state.workspace)
        : path === `/api/v1/reviews/${machineReceipt.id}` ? machineReceipt : undefined
    if (!value || init.method !== 'GET') throw new Error('Unexpected write or endpoint in close guard fixture')
    return new Response(JSON.stringify(value))
  }))
  try {
    await rememberReviewJob(state.workspace, machineReceipt.id)
    render(<Shell />); fireEvent.click(screen.getByRole('button', { name: '导入' }))
    const dialog = screen.getByRole('dialog', { name: '导入' })
    fireEvent.click(within(dialog).getByRole('button', { name: '打开候选审核与恢复' }))
    const job = await screen.findByRole('button', { name: `读取审核任务 ${machineReceipt.id}` })
    await waitFor(() => expect((job as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(job)
    const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
    await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
    const reason = await screen.findByLabelText('审核理由') as HTMLTextAreaElement
    await waitFor(() => expect(reason.disabled).toBe(false))
    fireEvent.change(reason, { target: { value: 'Synthetic unsubmitted reason' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '关闭导入' }))
    const initialConfirmation = await screen.findByRole('dialog', { name: '保留审核原命令' })
    fireEvent.click(within(initialConfirmation).getByRole('button', { name: '返回导入与审核' }))
    const refresh = screen.getByRole('button', { name: '重新核验发布权限与本机记录' }) as HTMLButtonElement
    await waitFor(() => expect(refresh.disabled).toBe(false))
    holdPublication = true; fireEvent.click(refresh)
    await waitFor(() => expect(heldLoads).toBe(1))
    expect(reason.disabled).toBe(true)
    fireEvent.click(within(dialog).getByRole('button', { name: '关闭导入' }))
    const confirmation = await screen.findByRole('dialog', { name: '保留审核原命令' })
    const discard = within(confirmation).getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭' }) as HTMLButtonElement
    expect(discard.disabled).toBe(true)
    fireEvent.click(discard)
    expect(screen.getByRole('dialog', { name: '导入' })).toBe(dialog)
    expect(reason.value).toBe('Synthetic unsubmitted reason')
    await act(async () => { release() })
    await waitFor(() => expect(discard.disabled).toBe(false))
    expect(reason.disabled).toBe(false)
    expect(reason.value).toBe('Synthetic unsubmitted reason')
    expect(screen.getByRole('dialog', { name: '导入' })).toBe(dialog)
    fireEvent.click(discard)
    await waitFor(() => expect(screen.queryByRole('dialog', { name: '导入' })).toBeNull())
    expect(state.commit).not.toHaveBeenCalled()
    expect(calls.every(value => value.startsWith('GET '))).toBe(true)
  } finally { release() }
})


test('actual Import and Shell merge publication confirmations into the existing close guard without issuing a write', async () => {
  state.workspace = `workspace_${crypto.randomUUID()}`; state.publication = true
  const writes: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    if (init.method !== 'GET') { writes.push(path); throw new Error('No implicit publish') }
    const value = path === '/api/v1/session' ? reviewSession(state.workspace)
      : path === `/api/v1/jobs/${publicationReceipt.id}` ? safeReviewJob(state.workspace)
        : path === `/api/v1/reviews/${publicationReceipt.id}` ? publicationReceipt
          : path === `/api/v1/drafts/${publicationDraft.id}` ? publicationDraft : undefined
    if (!value) throw new Error('Unexpected endpoint')
    return new Response(JSON.stringify(value))
  }))
  await rememberReviewJob(state.workspace, publicationReceipt.id)
  render(<Shell />); fireEvent.click(screen.getByRole('button', { name: '导入' }))
  const dialog = screen.getByRole('dialog', { name: '导入' })
  fireEvent.click(within(dialog).getByRole('button', { name: '打开候选审核与恢复' }))
  const job = await screen.findByRole('button', { name: `读取审核任务 ${publicationReceipt.id}` })
  await waitFor(() => expect((job as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(job)
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  await waitFor(() => expect((screen.getByRole('button', { name: '选择此审核并重新读取发布基准' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '选择此审核并重新读取发布基准' }))
  const warning = await screen.findByRole('checkbox', { name: /Synthetic first source warning/ })
  fireEvent.click(warning)
  fireEvent.click(within(dialog).getByRole('button', { name: '关闭导入' }))
  const confirm = await screen.findByRole('dialog', { name: '保留审核原命令' })
  expect(confirm.textContent).toContain('发布确认')
  fireEvent.click(within(confirm).getByRole('button', { name: '返回导入与审核' }))
  expect((screen.getByRole('checkbox', { name: /Synthetic first source warning/ }) as HTMLInputElement).checked).toBe(true)
  expect(writes).toEqual([])
})
