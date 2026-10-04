import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, request } from '../../api/client'
import { AuthoringPanel } from './AuthoringPanel'
import type { AuthoringPort } from './authoringClient'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'

const NativeURL = URL
const createURL = vi.fn<(blob: Blob) => string>(() => 'blob:synthetic-local-task')
const revokeURL = vi.fn()
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); createURL.mockClear(); revokeURL.mockClear() })
function setup() {
  vi.stubGlobal('URL', class extends NativeURL { static createObjectURL = createURL; static revokeObjectURL = revokeURL })
  const clicked = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const workspace = `workspace_${crypto.randomUUID()}`
  const session: SessionResponse = { workspace_id: workspace, actor_session_id: 'actor_local_task_original', role: 'author', csrf_token: 'synthetic-only', active_independent_attempt_id: null, active_open_book_attempt_id: null }
  const mutation = vi.fn(async (): Promise<never> => { throw new Error('No server mutation or subject read expected') })
  const port: AuthoringPort = { session: vi.fn(async () => ({ ...session })), list: vi.fn(async () => ({ items: [], next_cursor: null })), prepare: mutation, read: mutation, draft: mutation, preview: mutation, numeric: mutation, decide: mutation, job: mutation, cancel: mutation }
  const state = vi.fn()
  const view = render(<AuthoringPanel workspace={workspace} paused={false} currentBlock={null} port={port} onState={state} />)
  return { port, session, state, clicked, mutation, view, workspace }
}
async function fill() {
  await screen.findByLabelText('例题主题')
  fireEvent.change(screen.getByLabelText('例题主题'), { target: { value: '合成主题 α\n第二行' } })
  fireEvent.change(screen.getByLabelText('已声明先修（每行一条）'), { target: { value: '线性代数\n  保留空格' } })
  fireEvent.change(screen.getByLabelText('学习目标（每行一条，至少一条）'), { target: { value: '写出完整证明\n核对边界' } })
  const button = screen.getByRole('button', { name: '下载当前四项需求说明' })
  await waitFor(() => expect(button.matches(':disabled')).toBe(false))
  return button
}
const readBlob = (blob: Blob) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = reject; reader.readAsText(blob)
})
test('author downloads only the four current inputs without provider or server mutation and keeps dirty protection', async () => {
  const f = setup(), button = await fill()
  await waitFor(() => expect(f.state.mock.lastCall?.[0].dirty).toBe(true))
  fireEvent.click(button)
  await waitFor(() => expect(createURL).toHaveBeenCalledOnce())
  const text = await readBlob(createURL.mock.calls[0][0])
  expect(text).toBe('# 离线创作需求说明\n\n本次下载未调用 Codex。本文件仅包含作者当前输入的四项需求，不含已选材料或其他任务设置；没有创建服务器任务、授权或生成结果。\n\n## 主题\n\n合成主题 α\n第二行\n\n## 已声明先修\n\n线性代数\n  保留空格\n\n## 学习目标\n\n写出完整证明\n核对边界\n\n## 证明策略\n\nfull（完整证明）\n')
  expect(f.clicked).toHaveBeenCalledOnce(); expect(f.mutation).not.toHaveBeenCalled()
  expect(f.port.session).toHaveBeenCalledTimes(2)
  expect(f.state.mock.lastCall?.[0].dirty).toBe(true)
  expect((screen.getByLabelText('例题主题') as HTMLTextAreaElement).value).toBe('合成主题 α\n第二行')
  await waitFor(() => expect(revokeURL).toHaveBeenCalledWith('blob:synthetic-local-task'))
})

test('selected references and provider stay outside the local file and no consent is required', async () => {
  const f = setup(), button = await fill()
  fireEvent.change(screen.getByLabelText('已配置的提供商 ID'), { target: { value: 'provider_do_not_export' } })
  fireEvent.change(screen.getByLabelText('内容块 ID'), { target: { value: 'block_do_not_export' } })
  fireEvent.change(screen.getByLabelText('内容修订'), { target: { value: '7' } })
  fireEvent.change(screen.getByLabelText('内容 SHA256'), { target: { value: 'd'.repeat(64) } })
  fireEvent.click(screen.getByRole('button', { name: '加入这份准确引用' }))
  fireEvent.change(screen.getByLabelText('证明策略'), { target: { value: 'declared_dependencies' } })
  fireEvent.click(button); await waitFor(() => expect(createURL).toHaveBeenCalledOnce())
  const text = await readBlob(createURL.mock.calls[0][0])
  expect(text).toContain('declared_dependencies（明确声明所依赖的结论）')
  for (const omitted of ['provider_do_not_export', 'block_do_not_export', 'd'.repeat(64), f.session.actor_session_id, f.session.csrf_token]) expect(text).not.toContain(omitted)
  expect(f.mutation).not.toHaveBeenCalled(); expect(f.state.mock.lastCall?.[0].dirty).toBe(true)
})
test.each(['learner', 'independent', 'open_book', 'new_actor', 'workspace', 'expired', 'bad_schema'])('fresh %s admission rejects a download without server mutation', async mode => {
  const f = setup(), button = await fill()
  if (mode === 'learner') f.session.role = 'learner'
  if (mode === 'independent') f.session.active_independent_attempt_id = 'attempt_independent'
  if (mode === 'open_book') f.session.active_open_book_attempt_id = 'attempt_open_book'
  if (mode === 'new_actor') f.session.actor_session_id = 'actor_another_session'
  if (mode === 'workspace') f.session.workspace_id = 'workspace_another'
  if (mode === 'expired') f.port.session = vi.fn(async () => { throw new ApiError(401, 'private detail') })
  if (mode === 'bad_schema') f.port.session = vi.fn(async () => ({ ...f.session, active_open_book_attempt_id: undefined }) as unknown as SessionResponse)
  fireEvent.click(button)
  await waitFor(() => expect(screen.queryByText('正在重新核对当前作者与测试策略…')).toBeNull())
  expect(createURL).not.toHaveBeenCalled(); expect(f.clicked).not.toHaveBeenCalled(); expect(f.mutation).not.toHaveBeenCalled()
  expect(screen.queryByText('private detail')).toBeNull()
})
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(accept => { resolve = accept }); return { promise, resolve } }
test.each(['workspace', 'port', 'policy', 'unmount', 'inputs', 'access'])('late permission read after %s change cannot download the original inputs', async mode => {
  const f = setup(), button = await fill(), pending = deferred<SessionResponse>()
  f.port.session = vi.fn(() => pending.promise)
  fireEvent.click(button); await waitFor(() => expect(f.port.session).toHaveBeenCalledOnce())
  if (mode === 'unmount') f.view.unmount()
  else if (mode === 'inputs') fireEvent.change(screen.getByLabelText('例题主题'), { target: { value: 'new text after request' } })
  else if (mode === 'access') {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...f.session, role: 'learner' }), { status: 200 })))
    await act(async () => { await request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-local-task-role' }) })
  } else f.view.rerender(<AuthoringPanel workspace={mode === 'workspace' ? 'workspace_new' : f.workspace} paused={mode === 'policy'} currentBlock={null} port={mode === 'port' ? { ...f.port, session: vi.fn(async () => ({ ...f.session })) } : f.port} onState={f.state} />)
  await act(async () => pending.resolve({ ...f.session }))
  expect(createURL).not.toHaveBeenCalled(); expect(f.clicked).not.toHaveBeenCalled(); expect(f.mutation).not.toHaveBeenCalled()
})
test('double clicking one pending read downloads once and permission failure does not clear valid local inputs', async () => {
  const f = setup(), button = await fill(), pending = deferred<SessionResponse>()
  f.port.session = vi.fn(() => pending.promise)
  fireEvent.click(button); fireEvent.click(button)
  expect(f.port.session).toHaveBeenCalledOnce()
  await act(async () => pending.resolve({ ...f.session }))
  await waitFor(() => expect(f.clicked).toHaveBeenCalledOnce())
  expect(f.state.mock.lastCall?.[0].dirty).toBe(true)
  f.port.session = vi.fn(async () => { throw new ApiError(503, 'private detail') })
  fireEvent.click(button)
  await screen.findByText('当前权限或下载未确认；原输入保留，请重新读取权限后明确重试。')
  expect(createURL).toHaveBeenCalledOnce()
  expect((screen.getByLabelText('例题主题') as HTMLTextAreaElement).value).toBe('合成主题 α\n第二行')
  expect(f.state.mock.lastCall?.[0].dirty).toBe(true)
})

test.each(['unknown', 'authorized'])('the document and its explanation state only non-execution with %s Broker status', async mode => {
  const f = setup(), button = await fill()
  vi.stubGlobal('fetch', vi.fn(async (url: string | URL | Request) => String(url).endsWith('/codex/capabilities')
    ? new Response(JSON.stringify(mode === 'unknown' ? { detail: 'synthetic-unavailable' } : { available: true, authorized: true, adapter_version: 'codex-cli/0.160.0', sandbox_roots: [{ id: 'workspace_default', label: '此工作区的隔离 Broker 目录' }], capabilities: { approvals: false, interrupt: false, artifacts: false } }), { status: mode === 'unknown' ? 503 : 200 })
    : new Response(JSON.stringify(f.session), { status: 200 })))
  fireEvent.click(screen.getByRole('button', { name: '检查 Codex 连接' }))
  await screen.findByText(mode === 'unknown' ? /暂时无法确认 Codex 连接状态/ : '此工作区的 Codex 连接与授权状态已确认。')
  fireEvent.click(button); await waitFor(() => expect(createURL).toHaveBeenCalledOnce())
  const text = await readBlob(createURL.mock.calls[0][0])
  expect(text).not.toContain('未连接 Codex')
  expect(text).toContain('本次下载未调用 Codex。')
  expect(screen.queryByText(/^未连接 Codex：仅下载/)).toBeNull()
  expect(screen.getByText(/^本次下载不调用 Codex：仅下载/)).toBeTruthy()
})
