import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore } from '../../workbench/DraftStore'
import { actor, codexSession, workspace } from './bootstrapTestFixtures'
import { CodexTurnPanel } from './CodexTurnPanel'
import { turnClient } from './turnClient'
import { readTurnCommand } from './turnCommands'
import { heldTurnCommands, heldTurnForms, releaseTurnCommand, releaseTurnForm } from './turnMemory'
import { turnControl, turnPort } from './turnTestFixtures'

// POST /jobs/{id}/cancel returns the closed JobSnapshot owner contract, not JobRef.
const cancelled = (): JobSnapshot => ({ id: 'job_turn_test', workspace_id: workspace, kind: 'codex_turn',
 status: 'cancelled', revision: 2, created_at: '2026-10-04T00:00:00Z', updated_at: '2026-10-04T00:00:01Z',
 progress: { completed: 0, total: null, label: 'cancelled' }, result_refs: [], warnings: [], error: null })
const stores: DraftStore[] = []
const local = () => { const value = new DraftStore({ name: `turn-wire-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(value); return value }
afterEach(async () => {
 cleanup(); heldTurnCommands(workspace).forEach(releaseTurnCommand); heldTurnForms(workspace).forEach(releaseTurnForm)
 await Promise.all(stores.splice(0).map(value => value.close())); vi.unstubAllGlobals()
})

test('real cancellation wire is retained completely through client, explicit replay, and durable reload', async () => {
 const store = local(), formStore = local(), port = { ...turnPort(), cancel: turnClient.cancel }
 const posts: Array<{ path: string; key: string; body: unknown }> = []
 const fetch = vi.fn(async (path: string, init: RequestInit) => {
  const key = new Headers(init.headers).get('Idempotency-Key')!, body = JSON.parse(init.body as string)
  const original = readTurnCommand((await store.load(workspace))[key], workspace)
  expect(original.kind).toBe('cancel'); expect(original.actor_session_id).toBe(actor)
  expect(original.basis).toEqual(turnControl()); expect(original.body).toEqual(body); expect(original.ack).toBeNull()
  posts.push({ path, key, body })
  if (posts.length === 1) throw new Error('synthetic lost cancellation ACK')
  return new Response(JSON.stringify(cancelled()), { status: 200 })
 })
 vi.stubGlobal('fetch', fetch)
 let view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 const refresh = async () => { fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/) }
 await refresh()
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: codexSession().id } })
 fireEvent.click(screen.getByText('读取安全回合分页')); await screen.findByLabelText('安全回合分页')
 fireEvent.click(screen.getByText('读取回合控制 turn_test')); await screen.findByLabelText('当前回合控制 turn_test')
 fireEvent.click(screen.getByText('明确取消回合 Job job_turn_test')); await screen.findByText(/操作结果或本机保存尚未确认/)
 expect(posts).toHaveLength(1)
 const original = posts[0], savedOriginal = readTurnCommand((await store.load(workspace))[original.key], workspace)
 view.unmount(); view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await refresh(); expect(posts).toHaveLength(1)
 fireEvent.click(screen.getByText(`显式回放回合原 key ${original.key}`))
 await waitFor(async () => expect(readTurnCommand((await store.load(workspace))[original.key], workspace).ack).toEqual(cancelled()))
 await screen.findByText(/取消原 ACK 已保存/)
 expect(posts).toEqual([original, original]); expect(original.path).toBe('/api/v1/jobs/job_turn_test/cancel')
 expect(original.body).toEqual({ expected_revision: 1 })
 expect(readTurnCommand((await store.load(workspace))[original.key], workspace)).toEqual({ ...savedOriginal, ack: cancelled() })
 view.unmount(); render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await refresh(); expect(posts).toHaveLength(2)
 expect(screen.getByText('取消回合 Job · 原 ACK 已记录，不是当前状态')).toBeTruthy()
 expect(readTurnCommand((await store.load(workspace))[original.key], workspace).ack).toEqual(cancelled())
 expect(port.prepare).not.toHaveBeenCalled(); expect(port.current).not.toHaveBeenCalled()
})
