import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { CodexCapabilities, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, request } from '../../api/client'
import { CodexCapabilitiesPanel } from './CodexCapabilitiesPanel'
import type { CodexCapabilityPort } from './codexClient'
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const workspace = 'workspace_codex_ui'
const session = (): SessionResponse => ({ workspace_id: workspace, actor_session_id: 'session_synthetic_codex_ui', role: 'author', csrf_token: 'synthetic-only', active_independent_attempt_id: null, active_open_book_attempt_id: null })
const capabilities = (): CodexCapabilities => ({ available: true, authorized: false, adapter_version: 'codex-cli/0.160.0', sandbox_roots: [{ id: 'workspace_default', label: '此工作区的隔离 Broker 目录' }], capabilities: { approvals: false, interrupt: false, artifacts: false } })
const port = (): CodexCapabilityPort => ({ session: vi.fn(async () => session()), capabilities: vi.fn(async () => capabilities()) })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
const check = () => fireEvent.click(screen.getByRole('button', { name: '检查 Codex 连接' }))

test('explicit check reads session then capabilities, displays only this Broker and false product flags', async () => {
  const p = port(), order: string[] = []
  p.session = vi.fn(async () => { order.push('session'); return session() })
  p.capabilities = vi.fn(async () => { order.push('capabilities'); return capabilities() })
  render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />)
  expect(p.session).not.toHaveBeenCalled(); expect(p.capabilities).not.toHaveBeenCalled()
  expect(screen.getByText(/受控 Codex 任务导出与产物回导尚未实现；当前可下载四项本地需求说明，仍未连接 Codex/)).toBeTruthy()
  check(); await screen.findByText('未连接 Codex：此工作区的隔离 Broker 尚未授权。')
  expect(order).toEqual(['session', 'capabilities']); expect(screen.getAllByText('不可用')).toHaveLength(3)
  expect(screen.getByText('codex-cli/0.160.0')).toBeTruthy()
  expect(screen.getByText(/不表示其他 Codex 会话的登录状态/)).toBeTruthy()
  expect(screen.getAllByRole('button')).toHaveLength(1)
})
test('unavailable adapter is distinct from an unknown failed probe', async () => {
  const p = port(); p.capabilities = vi.fn(async () => ({ available: false, authorized: false, adapter_version: null, sandbox_roots: [], capabilities: { approvals: false, interrupt: false, artifacts: false } }))
  render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />); check()
  await screen.findByText('未连接 Codex：未发现可用的本机适配器。')
  p.capabilities = vi.fn(async () => { throw new ApiError(503, 'synthetic-private-server-error', 'CODEX_PROBE_TIMEOUT') })
  check(); await screen.findByText(/暂时无法确认 Codex 连接状态/)
  expect(screen.queryByText(/未发现可用/)).toBeNull(); expect(screen.queryByText(/synthetic-private/)).toBeNull()
})
test.each(['learner', 'independent', 'open_book', 'wrong_workspace'])('fresh %s session never admits the capability probe', async mode => {
  const p = port(); p.session = vi.fn(async () => ({ ...session(), ...(mode === 'learner' ? { role: 'learner' as const } : mode === 'independent' ? { active_independent_attempt_id: 'attempt_synthetic' } : mode === 'open_book' ? { active_open_book_attempt_id: 'attempt_synthetic' } : { workspace_id: 'workspace_other' }) }))
  render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />); check()
  await screen.findByText(/当前会话或测试策略不允许检查/); expect(p.capabilities).not.toHaveBeenCalled()
})
test('unknown parent policy disables the button and causes no session or capability read', () => {
  const p = port(); render(<CodexCapabilitiesPanel workspace={workspace} admitted={false} port={p} />)
  const button = screen.getByRole('button', { name: '检查 Codex 连接' }) as HTMLButtonElement
  expect(button.disabled).toBe(true); fireEvent.click(button)
  expect(p.session).not.toHaveBeenCalled(); expect(p.capabilities).not.toHaveBeenCalled()
})
test.each(['permission', 'workspace', 'port'])('late capability response is discarded on %s change', async mode => {
  const pending = deferred<CodexCapabilities>(), p = port(); p.capabilities = vi.fn(() => pending.promise)
  const view = render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />); check()
  await waitFor(() => expect(p.capabilities).toHaveBeenCalledOnce())
  view.rerender(<CodexCapabilitiesPanel workspace={mode === 'workspace' ? 'workspace_other' : workspace} admitted={mode !== 'permission'} port={mode === 'port' ? port() : p} />)
  await act(async () => pending.resolve({ ...capabilities(), authorized: true }))
  expect(screen.queryByText('此工作区的 Codex 连接与授权状态已确认。')).toBeNull()
  expect(screen.queryByText('codex-cli/0.160.0')).toBeNull()
})
test('access-change notification hides previous observations immediately and ignores in-flight response', async () => {
  const p = port(), pending = deferred<CodexCapabilities>()
  render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />); check()
  await screen.findByText('codex-cli/0.160.0')
  p.capabilities = vi.fn(() => pending.promise); check(); await waitFor(() => expect(p.capabilities).toHaveBeenCalledOnce())
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...session(), role: 'learner' }), { status: 200 })))
  await act(async () => { await request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-role-transition' }) })
  await act(async () => pending.resolve({ ...capabilities(), authorized: true }))
  expect(screen.queryByText('codex-cli/0.160.0')).toBeNull(); expect(screen.getByText('尚未检查 Codex 连接。')).toBeTruthy()
})
test('double click admits one probe and unmount does not persist or issue another request', async () => {
  const pending = deferred<CodexCapabilities>(), p = port(); p.capabilities = vi.fn(() => pending.promise)
  const view = render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />)
  const button = screen.getByRole('button', { name: '检查 Codex 连接' }); fireEvent.click(button); fireEvent.click(button)
  await waitFor(() => expect(p.capabilities).toHaveBeenCalledOnce()); expect(p.session).toHaveBeenCalledOnce()
  view.unmount(); await act(async () => pending.resolve(capabilities()))
  expect(p.capabilities).toHaveBeenCalledOnce()
})
test('malformed port response never displays private extra fields or a successful connection', async () => {
  const p = port(); p.capabilities = vi.fn(async () => ({ ...capabilities(), authorized: true, account: { email: 'synthetic-private-email' } }))
  render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />); check()
  await screen.findByText(/暂时无法确认 Codex 连接状态/)
  expect(screen.queryByText(/synthetic-private/)).toBeNull(); expect(screen.queryByText('此工作区的 Codex 连接与授权状态已确认。')).toBeNull()
})

test.each(['unknown', 'authorized'])('local download explanation never contradicts the %s Broker observation', async mode => {
  const p = port()
  p.capabilities = mode === 'unknown'
    ? vi.fn(async () => { throw new ApiError(503, 'synthetic-unavailable') })
    : vi.fn(async () => ({ ...capabilities(), authorized: true }))
  render(<CodexCapabilitiesPanel workspace={workspace} admitted port={p} />); check()
  await screen.findByText(mode === 'unknown' ? /暂时无法确认 Codex 连接状态/ : '此工作区的 Codex 连接与授权状态已确认。')
  expect(screen.queryByText(/仍未连接 Codex/)).toBeNull()
  expect(screen.getByText(/当前可下载四项本地需求说明；该本地需求说明不调用 Codex/)).toBeTruthy()
})
