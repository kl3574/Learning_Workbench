import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import type { CodexCurrentSessionView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { DraftStore } from '../../workbench/DraftStore'
import { CodexBootstrapPanel } from './CodexBootstrapPanel'
import { bootstrapClient, checkedBootstrap } from './bootstrapClient'
import { prepareCommand, persistBootstrapCommand } from './bootstrapCommands'
import { heldBootstrapCommands, releaseBootstrapCommand } from './bootstrapMemory'
import { actor, bootstrapPort, codexSession, preparation, workspace } from './bootstrapTestFixtures'

afterEach(() => {
 cleanup(); vi.unstubAllGlobals()
 for (const value of heldBootstrapCommands(workspace)) releaseBootstrapCommand(value)
})
const current = (): CodexCurrentSessionView => ({ ...codexSession(), revision: 3,
 active_turn_id: 'turn_current', capabilities: { approvals: false, interrupt: false, artifacts: false } })

test('current GET accepts checked control history without widening original bootstrap decoders', async () => {
 const value = current(), fetch = vi.fn(async () => new Response(JSON.stringify(value), { status: 200 }))
 vi.stubGlobal('fetch', fetch)
 expect(await bootstrapClient.read(value.id)).toEqual(value)
 const [path, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
 expect(path).toBe('/api/v1/codex/sessions/codex_session_test')
 expect(init.method).toBe('GET'); expect(init.body).toBeUndefined()
 expect(new Headers(init.headers).get('Idempotency-Key')).toBeNull()
 expect(() => checkedBootstrap('CodexSessionView', value)).toThrow()
 const { active_turn_id: omitted, ...ack } = value; void omitted
 expect(() => checkedBootstrap('CodexSessionCreateAck', ack)).toThrow()
 expect(checkedBootstrap('CodexSessionView', codexSession())).toEqual(codexSession())
})

test.each([
 { revision: 1 }, { revision: 2 }, { status: 'unknown' },
 { capabilities: { approvals: 1, interrupt: false, artifacts: false } },
 { active_turn_id: undefined }, { revision: true }, { upstream_thread: 'forbidden' },
])('current read rejects damaged or inconsistent projection %j', patch => {
 expect(() => checkedBootstrap('CodexCurrentSessionView', { ...current(), ...patch })).toThrow()
})

test('current model accepts actual operation booleans and terminal slot release without manufacturing ACK fields', () => {
 const value = { ...current(), revision: 5, active_turn_id: null,
  capabilities: { approvals: true, interrupt: true, artifacts: true } }
 expect(checkedBootstrap('CodexCurrentSessionView', value)).toEqual(value)
 expect(checkedBootstrap('CodexCurrentSessionView', codexSession('initializing'))).toEqual(codexSession('initializing'))
 expect(checkedBootstrap('CodexCurrentSessionView', codexSession('unknown'))).toEqual(codexSession('unknown'))
})

test('current session panel renders the read slot and operation flags while original command bytes stay intact', async () => {
 const port = bootstrapPort(), db = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() })
 const command = prepareCommand(workspace, actor)
 if (command.kind !== 'prepare') throw new Error('Expected the synthetic preparation command')
 await persistBootstrapCommand({ ...command, ack: preparation() }, db)
 const before = Object.values(await db.load(workspace))[0].text
 port.preparation = vi.fn(async () => preparation('consumed'))
 port.read = vi.fn(async () => ({ ...current(), capabilities: { approvals: true, interrupt: false, artifacts: true } }))
 render(<CodexBootstrapPanel workspace={workspace} writeAdmitted port={port} store={db} />)
 fireEvent.click(screen.getByRole('button', { name: '读取本地会话记录' }))
 await screen.findByRole('button', { name: '读取准备当前状态 preparation_test' })
 fireEvent.click(screen.getByRole('button', { name: '读取准备当前状态 preparation_test' }))
 await waitFor(() => expect(screen.getByText('真实本地记录：ready · r3')).toBeTruthy())
 expect(screen.getByText('active_turn_id：turn_current；审批、interrupt、artifacts：true、false、true。')).toBeTruthy()
 expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled(); expect(port.prepare).not.toHaveBeenCalled()
 expect(Object.values(await db.load(workspace))[0].text).toBe(before)
})
