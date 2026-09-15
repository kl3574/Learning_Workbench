import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ProviderConfigAck } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, request } from '../../api/client'
import { commandKey, decodeCommand, newCommand, providerCommandStore } from './providerDrafts'
import { useProviderCommands } from './useProviderCommands'
import { configFixture, proposalFixture, providerFixture, writeFixture } from './testFixtures'
afterEach(cleanup)

test('lost config ACK survives real IDB reload and original replay does not replace a later current revision', async () => {
  const state = providerFixture(), actual = state.port.saveConfig, workspace = `workspace_${crypto.randomUUID()}`
  state.port.saveConfig = vi.fn(async (...args: Parameters<typeof actual>) => { await actual(...args); throw new Error('controlled lost ACK') })
  const first = renderHook(() => useProviderCommands(workspace, false, state.port))
  await waitFor(() => expect(first.result.current.safe).toBe(true))
  act(() => { first.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }) })
  await waitFor(() => expect(first.result.current.safe).toBe(true)); const original = first.result.current.editor!
  await act(() => first.result.current.send()); expect(state.current().revision).toBe(2); expect(first.result.current.editor?.ack).toBeNull()
  first.unmount(); state.external(configFixture(3)); state.port.saveConfig = vi.fn(actual)
  const next = renderHook(() => useProviderCommands(workspace, false, state.port)); await waitFor(() => expect(next.result.current.candidates).toHaveLength(1))
  await act(() => next.result.current.restore(next.result.current.candidates[0])); expect(next.result.current.editor?.command_id).toBe(original.command_id)
  act(() => next.result.current.correct()); expect(next.result.current.editor?.command_id).toBe(original.command_id)
  await act(() => next.result.current.send()); await waitFor(() => expect(next.result.current.safe).toBe(true))
  expect(next.result.current.editor?.ack?.id).toBe('provider_test'); expect(next.result.current.editor?.kind === 'config' && next.result.current.editor.ack?.revision).toBe(2)
  expect(next.result.current.remote?.kind === 'config' && next.result.current.remote.value.revision).toBe(3)
  expect(state.port.saveConfig).toHaveBeenCalledWith('provider_test', original.body, original.command_id)
  expect(decodeCommand((await providerCommandStore.load(workspace))[commandKey(original)].text, workspace).ack).not.toBeNull()
})
test('explicit 412 preserves base and candidate; correction has a new key and requires another send', async () => {
  const state = providerFixture(), workspace = `workspace_${crypto.randomUUID()}`, hook = renderHook(() => useProviderCommands(workspace, false, state.port))
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); act(() => { hook.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }) })
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); const original = hook.result.current.editor!
  state.external(configFixture(2)); await act(() => hook.result.current.send()); expect(hook.result.current.rejected).toBe(true)
  expect(hook.result.current.editor?.body).toEqual(original.body); expect(hook.result.current.remote?.kind === 'config' && hook.result.current.remote.value.revision).toBe(2)
  act(() => hook.result.current.correct()); expect(hook.result.current.editor?.command_id).not.toBe(original.command_id); expect(state.port.saveConfig).toHaveBeenCalledTimes(1)
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); await act(() => hook.result.current.send()); expect(state.current().revision).toBe(3); expect(state.current().model).toBe('my-model-candidate')
})
test('quota failure blocks POST and beforeunload until original command is really durable', async () => {
  const state = providerFixture(), workspace = `workspace_${crypto.randomUUID()}`, hook = renderHook(() => useProviderCommands(workspace, false, state.port))
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); const write = vi.spyOn(providerCommandStore, 'save').mockRejectedValueOnce(new DOMException('controlled quota', 'QuotaExceededError'))
  try {
    act(() => { hook.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }) })
    await waitFor(() => expect(hook.result.current.journal.error).toBeTruthy()); await act(() => hook.result.current.send()); expect(state.port.saveConfig).not.toHaveBeenCalled()
    const leave = new Event('beforeunload', { cancelable: true }); dispatchEvent(leave); expect(leave.defaultPrevented).toBe(true)
    write.mockRestore(); act(() => hook.result.current.retryLocal()); await waitFor(() => expect(hook.result.current.safe).toBe(true))
  } finally { write.mockRestore() }
})
test('a late old workspace ACK cannot overwrite or appear in the new workspace', async () => {
  const state = providerFixture(); let finish!: (value: ProviderConfigAck) => void
  state.port.saveConfig = vi.fn(async () => new Promise<ProviderConfigAck>(done => { finish = done }))
  const first = `workspace_${crypto.randomUUID()}`, second = `workspace_${crypto.randomUUID()}`
  const hook = renderHook(({ workspace }) => useProviderCommands(workspace, false, state.port), { initialProps: { workspace: first } })
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); act(() => { hook.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }) })
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); const original = hook.result.current.editor!; let sending!: Promise<void>
  act(() => { sending = hook.result.current.send() }); await waitFor(() => expect(state.port.saveConfig).toHaveBeenCalledOnce()); hook.rerender({ workspace: second })
  await act(async () => { finish({ id: 'provider_test', revision: 2, configured: true, config_sha256: '2'.repeat(64), secret_present: false }); await sending })
  expect(hook.result.current.editor).toBeNull(); expect(await providerCommandStore.load(second)).toEqual({}); expect(decodeCommand((await providerCommandStore.load(first))[commandKey(original)].text, first).ack).toBeNull()
})
test('independent policy hides grant candidates and stops sending while safe revoke does not read summaries', async () => {
  const state = providerFixture(), workspace = `workspace_${crypto.randomUUID()}`, proposal = proposalFixture()
  const command = newCommand(workspace, { kind: 'grant', proposal, body: { proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 } }); await providerCommandStore.save(workspace, commandKey(command), JSON.stringify(command), 0)
  const hook = renderHook(() => useProviderCommands(workspace, true, state.port)); await waitFor(() => expect(hook.result.current.safe).toBe(true)); expect(hook.result.current.candidates).toEqual([])
  await act(() => hook.result.current.restore({ value: command, text: JSON.stringify(command) })); expect(hook.result.current.editor).toBeNull(); expect(state.port.proposal).not.toHaveBeenCalled(); expect(state.port.grant).not.toHaveBeenCalled()
  act(() => { hook.result.current.begin({ kind: 'revoke', consent_id: 'consent_test', body: { expected_revision: 1 } }) }); await waitFor(() => expect(hook.result.current.safe).toBe(true)); await act(() => hook.result.current.send())
  expect(state.port.revoke).toHaveBeenCalledOnce(); expect(state.port.consents).not.toHaveBeenCalled(); expect(hook.result.current.remote).toBeNull()
})
test('foreign same-object candidates are kept until explicit selection and no implicit POST occurs', async () => {
  const state = providerFixture(), workspace = `workspace_${crypto.randomUUID()}`, a = renderHook(() => useProviderCommands(workspace, false, state.port)), b = renderHook(() => useProviderCommands(workspace, false, state.port))
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true) })
  act(() => { a.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }); b.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: { ...writeFixture(state.current()), model: 'other-page' } }) })
  await waitFor(() => expect(a.result.current.competing.length).toBeGreaterThan(0)); await act(() => a.result.current.send()); expect(state.port.saveConfig).not.toHaveBeenCalled()
  const record = (await providerCommandStore.load(workspace))[commandKey(a.result.current.editor!)]; expect(new Set([record.text, ...record.conflicts.map(value => value.text)]).size).toBe(2)
})
test('malformed extra fields, false ACKs and secret bodies are rejected by generated schemas', () => {
  const workspace = 'workspace_decode', base = configFixture(), original = newCommand(workspace, { kind: 'config', provider_id: base.id, base, body: writeFixture(base) })
  for (const bad of [{ ...original, secret: 'not-allowed' }, { ...original, body: { ...original.body, secret: 'not-allowed' } }, { ...original, body: { ...original.body, expected_revision: true } }, { ...original, ack: { id: base.id, revision: 1, configured: true, secret_present: false, config_sha256: base.config_sha256 } }]) expect(() => decodeCommand(JSON.stringify(bad), workspace)).toThrow()
  expect(() => decodeCommand(JSON.stringify(original), 'other_workspace')).toThrow('身份')
})
test('a non-412 denial cannot silently change the immutable original command', async () => {
  const state = providerFixture(), workspace = `workspace_${crypto.randomUUID()}`, hook = renderHook(() => useProviderCommands(workspace, false, state.port))
  state.port.saveConfig = vi.fn(async () => { throw new ApiError(409, 'controlled denial') })
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); act(() => { hook.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }) }); await waitFor(() => expect(hook.result.current.safe).toBe(true))
  const original = hook.result.current.editor; await act(() => hook.result.current.send()); act(() => hook.result.current.correct()); expect(hook.result.current.editor).toEqual(original); expect(hook.result.current.rejected).toBe(false)
})
test('a real session-access generation change invalidates an in-flight same-workspace ACK', async () => {
  const state = providerFixture(), workspace = `workspace_${crypto.randomUUID()}`; let finish!: (value: ProviderConfigAck) => void
  state.port.saveConfig = vi.fn(async () => new Promise<ProviderConfigAck>(done => { finish = done }))
  const hook = renderHook(() => useProviderCommands(workspace, false, state.port))
  await waitFor(() => expect(hook.result.current.safe).toBe(true)); act(() => { hook.result.current.begin({ kind: 'config', provider_id: state.current().id, base: state.current(), body: writeFixture(state.current()) }) }); await waitFor(() => expect(hook.result.current.safe).toBe(true))
  const original = hook.result.current.editor!; let sending!: Promise<void>; act(() => { sending = hook.result.current.send() }); await waitFor(() => expect(state.port.saveConfig).toHaveBeenCalledOnce())
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })))
  try { await act(async () => { await request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'provider-unit-session-generation' }) }) } finally { vi.unstubAllGlobals() }
  await act(async () => { finish({ id: 'provider_test', revision: 2, config_sha256: '2'.repeat(64), configured: true, secret_present: false }); await sending })
  expect(hook.result.current.editor).toBeNull(); expect(hook.result.current.remote).toBeNull(); expect(decodeCommand((await providerCommandStore.load(workspace))[commandKey(original)].text, workspace).ack).toBeNull()
})
