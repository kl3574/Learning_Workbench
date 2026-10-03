import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { AuthoringPanel } from './AuthoringPanel'
import type { AuthoringPort } from './authoringClient'
import { bootstrapPort, deferred, preparation, session, workspace } from '../codex/bootstrapTestFixtures'
import { heldBootstrapCommands, releaseBootstrapCommand } from '../codex/bootstrapMemory'
afterEach(() => { cleanup(); for (const value of heldBootstrapCommands(workspace)) releaseBootstrapCommand(value) })
test('parent keeps the original close guard and a closed static label for a late bootstrap ACK', async () => {
 const unexpected = vi.fn(async (): Promise<never> => { throw new Error('No academic write expected') })
 const port: AuthoringPort = { session: vi.fn(async () => session()), list: vi.fn(async () => ({ items: [], next_cursor: null })), prepare: unexpected, read: unexpected, draft: unexpected, preview: unexpected, numeric: unexpected, decide: unexpected, job: unexpected, cancel: unexpected }
 const bootstrap = bootstrapPort(), pending = deferred<ReturnType<typeof preparation>>(), state = vi.fn()
 bootstrap.prepare = vi.fn(() => pending.promise)
 const db = new DraftStore({ name: 'authoring-bootstrap-parent', factory: new IDBFactory() })
 const view = render(<AuthoringPanel workspace={workspace} paused={false} currentBlock={null} port={port} bootstrap={bootstrap} bootstrapStore={db} onState={state} />)
 await waitFor(() => expect(state.mock.calls.at(-1)?.[0].safe).toBe(true))
 fireEvent.click(screen.getByRole('button', { name: '读取本地会话记录' }))
 await waitFor(() => expect((screen.getByRole('button', { name: '准备本地控制会话' }) as HTMLButtonElement).disabled).toBe(false))
 fireEvent.click(screen.getByRole('button', { name: '准备本地控制会话' }))
 await waitFor(() => expect(bootstrap.prepare).toHaveBeenCalledOnce())
 await waitFor(() => expect(state.mock.calls.at(-1)?.[0].safe).toBe(false))
 view.rerender(<AuthoringPanel workspace={workspace} paused currentBlock={null} port={port} bootstrap={bootstrap} bootstrapStore={db} onState={state} />)
 await act(async () => pending.resolve(preparation()))
 await waitFor(() => expect(state.mock.calls.at(-1)?.[0]).toMatchObject({ dirty: true, safe: false, isolated: true, isolationLabel: '保留本地会话隔离内存，丢弃临时表单并前往角色控制' }))
 expect(unexpected).not.toHaveBeenCalled(); expect(bootstrap.prepare).toHaveBeenCalledOnce()
 expect(JSON.parse(Object.values(await db.load(workspace))[0].text).ack).toBeNull()
})
