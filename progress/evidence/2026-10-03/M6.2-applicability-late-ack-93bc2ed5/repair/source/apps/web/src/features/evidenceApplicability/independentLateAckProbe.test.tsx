// Independent synthetic controlled-transport probe. No server or model calls.
import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { request } from '../../api/client'
import { commandStore, readCommand, type Command } from './commands'
import { discard, pending, recoverable } from './memory'
import { ack, evidenceId, eventId, original, session } from './fixtures'
import { ApplicabilityPanel } from './ApplicabilityPanel'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
const spaces: string[] = []
afterEach(async () => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); for (const workspace of spaces.splice(0)) discard(workspace); await commandStore.close() })
const json = (value: unknown) => new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } })
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r }); return { promise, resolve } }

async function sent() {
  const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace)
  const actor = session(workspace), late = deferred<Response>()
  let current: SessionResponse = { ...actor }
  const posts: { key: string; body: Command['body'] }[] = []
  const fetcher = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(String(input), 'http://synthetic.invalid')
    if (url.pathname === '/api/v1/session' && init?.method === 'GET') return json(current)
    if (url.pathname === '/api/v1/session/role' && init?.method === 'POST') return json(current)
    if (url.pathname === '/api/v1/attempts/attempt_probe/abandon' && init?.method === 'POST') return json({})
    if (url.pathname === `/api/v1/learning/evidence/${evidenceId}/applicability` && init?.method === 'GET') return json({ ...original, event_decision_head: url.searchParams.has('event_id') ? 0 : null })
    if (url.pathname === `/api/v1/learning/evidence/${evidenceId}/applicability-decisions` && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as Command['body'], key = new Headers(init.headers).get('Idempotency-Key')!
      posts.push({ key, body })
      return posts.length === 1 ? late.promise : json({ ...ack(body), actor_session_id: actor.actor_session_id })
    }
    throw new Error(`Unexpected synthetic transport route: ${init?.method} ${url.pathname}`)
  })
  vi.stubGlobal('fetch', fetcher)
  render(<ApplicabilityPanel workspace={workspace} paused={false} evidenceId={evidenceId} />)
  await waitFor(() => expect(screen.getByRole('button', { name: '读取所选原证据当前适用性' })).toBeDefined())
  fireEvent.click(screen.getByRole('button', { name: '读取所选原证据当前适用性' }))
  fireEvent.click(await screen.findByRole('button', { name: `读取事件决定基准 ${eventId}` }))
  fireEvent.click(await screen.findByRole('button', { name: '采用本次已读依据准备决定' }))
  fireEvent.change(await screen.findByLabelText('明确适用性决定'), { target: { value: 'usable' } })
  fireEvent.change(screen.getByLabelText('适用性理由'), { target: { value: 'Synthetic original received ACK must survive an access transition' } })
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: '明确保存适用性决定' }))
  await waitFor(() => expect(posts).toHaveLength(1))
  const command = readCommand((await commandStore.load(workspace))[posts[0].key], workspace)
  const receipt = { ...ack(command.body), actor_session_id: actor.actor_session_id }
  const deliver = async (usable = true) => { await act(async () => { late.resolve(json(usable ? receipt : {})); await late.promise; await new Promise(resolve => setTimeout(resolve, 0)) }) }
  const transition = async (kind: 'role' | 'policy', blocked: boolean) => {
    current = { ...actor, ...(kind === 'role' ? { role: blocked ? 'learner' as const : 'author' as const } : { active_independent_attempt_id: blocked ? 'attempt_probe' : null }) }
    await act(async () => {
      if (kind === 'role') await request('POST /api/v1/session/role', { role: blocked ? 'learner' : 'author' }, { 'Idempotency-Key': `probe_${blocked}` })
      else await request('POST /api/v1/attempts/{id}/abandon', { expected_revision: 1 }, { 'Idempotency-Key': `probe_${blocked}` }, { path: { id: 'attempt_probe' } })
    })
    await waitFor(() => expect(screen.queryByRole('button', { name: '读取所选原证据当前适用性' }) !== null).toBe(!blocked))
  }
  return { workspace, actor, posts, command, receipt, deliver, transition }
}

test('control: same access generation saves a received ACK with exactly one decision POST', async () => {
  const f = await sent(); await f.deliver()
  await waitFor(async () => expect(readCommand((await commandStore.load(f.workspace))[f.command.command_id], f.workspace).ack).toEqual(f.receipt))
  expect(pending(f.workspace)).toBe(false); expect(f.posts).toHaveLength(1)
})

test.each(['role', 'policy'] as const)('late ACK after %s generation change remains original-session save-only recoverable', async kind => {
  const f = await sent(); await f.transition(kind, true); await f.deliver()
  expect(screen.queryByRole('region', { name: '本机适用性原命令' })).toBeNull()
  expect(screen.queryAllByText(original.current_basis_sha256, { exact: true })).toHaveLength(0)
  expect(readCommand((await commandStore.load(f.workspace))[f.command.command_id], f.workspace)).toEqual(f.command)
  const retained = recoverable(f.workspace, f.actor.csrf_token)
  expect(recoverable(f.workspace, 'synthetic-other-session')).toEqual([])
  const heldBeforeReturn = pending(f.workspace)
  const learnerSave = screen.queryByRole('button', { name: '只保存原会话的适用性内存记录' }) as HTMLButtonElement | null
  if (learnerSave) expect(learnerSave.disabled).toBe(true)
  await f.transition(kind, false)
  const replay = screen.getByRole('button', { name: `显式回放原适用性命令 ${f.command.command_id}` }) as HTMLButtonElement
  const save = screen.queryByRole('button', { name: '只保存原会话的适用性内存记录' }) as HTMLButtonElement | null
  console.info('LATE_ACK_OBSERVATION', JSON.stringify({ kind, received_ack: true, retained_original_ack: retained.length === 1 && retained[0].ack?.receipt_sha256 === f.receipt.receipt_sha256, pending_after_ack: heldBeforeReturn, other_session_retained: recoverable(f.workspace, 'synthetic-other-session').length, original_role_save_available: !!save && !save.disabled, old_generation_replay_disabled: replay.disabled, decision_posts_before_save: f.posts.length }))
  expect.soft(retained).toEqual([{ ...f.command, ack: f.receipt, rejection: null }])
  expect.soft(save !== null && !save.disabled).toBe(true)
  expect(replay.disabled).toBe(true)
  if (save && !save.disabled) { fireEvent.click(save); await waitFor(() => expect(pending(f.workspace)).toBe(false)) }
  expect.soft(readCommand((await commandStore.load(f.workspace))[f.command.command_id], f.workspace).ack).toEqual(f.receipt)
  expect(f.posts).toHaveLength(1)
})

test('control: a lost response without access change remains explicitly recoverable using the exact original key and body', async () => {
  const f = await sent()
  // A schema-invalid response models an unusable ACK while the server retains it.
  // This is distinct from the valid late ACK in the two transition probes.
  await f.deliver(false)
  expect(readCommand((await commandStore.load(f.workspace))[f.command.command_id], f.workspace).ack).toBeNull()
  const replay = screen.getByRole('button', { name: `显式回放原适用性命令 ${f.command.command_id}` }) as HTMLButtonElement
  await waitFor(() => expect(replay.disabled).toBe(false)); fireEvent.click(replay)
  await waitFor(() => expect(f.posts).toHaveLength(2)); expect(f.posts[1]).toEqual(f.posts[0])
  await waitFor(async () => expect(readCommand((await commandStore.load(f.workspace))[f.command.command_id], f.workspace).ack).toEqual(f.receipt))
})
