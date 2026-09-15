import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ProviderSecretAck } from '../../../../../packages/contracts/generated/api-types'
import { ApiError } from '../../api/client'
import { DraftStore } from '../../workbench/DraftStore'
import { useProviderSecret } from './useProviderSecret'
import { configFixture, providerFixture } from './testFixtures'
afterEach(cleanup)

test('secret loss retries exact temporary bytes/key and never touches persistence', async () => {
  const state = providerFixture(), base = state.current(), changed = vi.fn()
  const disk = vi.spyOn(DraftStore.prototype, 'save'), local = vi.spyOn(Storage.prototype, 'setItem')
  const ack = { id: base.id, revision: 2, config_sha256: '2'.repeat(64), secret_present: true }
  state.port.saveSecret = vi.fn().mockRejectedValueOnce(new Error('controlled ACK loss')).mockResolvedValueOnce(ack)
  const hook = renderHook(() => useProviderSecret('workspace_secret', base, state.port, changed))
  act(() => hook.result.current.edit('synthetic-secret-🧠é \n'))
  await act(() => hook.result.current.run('write')); expect(hook.result.current.ack).toBeNull(); expect(hook.result.current.text).toBe('synthetic-secret-🧠é \n')
  const original = hook.result.current.command
  act(() => hook.result.current.edit('replacement-blocked')); expect(hook.result.current.command).toEqual(original)
  const leaving = new Event('beforeunload', { cancelable: true }); dispatchEvent(leaving); expect(leaving.defaultPrevented).toBe(true)
  state.external({ ...configFixture(3), secret_present: true }); await act(() => hook.result.current.run('write'))
  expect(vi.mocked(state.port.saveSecret).mock.calls[0]).toEqual(vi.mocked(state.port.saveSecret).mock.calls[1])
  expect(hook.result.current.ack?.revision).toBe(2); expect(hook.result.current.remote?.revision).toBe(3); expect(hook.result.current.text).toBe(''); expect(hook.result.current.command).toBeNull()
  expect(disk).not.toHaveBeenCalled(); expect(local).not.toHaveBeenCalled(); disk.mockRestore(); local.mockRestore()
})
test('secret refresh cannot reconstruct a previous unknown write from secret_present', async () => {
  const state = providerFixture(), changed = vi.fn(); state.port.saveSecret = vi.fn(async () => { throw new Error('unknown') })
  const first = renderHook(() => useProviderSecret('workspace_secret_reload', state.current(), state.port, changed))
  act(() => first.result.current.edit('synthetic-ephemeral')); await act(() => first.result.current.run('write')); first.unmount()
  state.external({ ...configFixture(2), secret_present: true })
  const next = renderHook(() => useProviderSecret('workspace_secret_reload', state.current(), state.port, changed))
  expect(next.result.current.text).toBe(''); expect(next.result.current.command).toBeNull(); expect(next.result.current.ack).toBeNull(); expect(state.port.saveSecret).toHaveBeenCalledOnce()
})
test('412 secret correction retains temporary input and changes key only after explicit comparison', async () => {
  const state = providerFixture(), base = state.current(), hook = renderHook(() => useProviderSecret('workspace_secret_cas', base, state.port, vi.fn()))
  act(() => hook.result.current.edit('synthetic-original')); state.external(configFixture(2)); await act(() => hook.result.current.run('write'))
  const original = hook.result.current.command; expect(hook.result.current.rejected).toBe(true); expect(hook.result.current.remote?.revision).toBe(2)
  act(() => hook.result.current.correct()); expect(hook.result.current.command?.key).not.toBe(original?.key); expect(hook.result.current.command?.kind === 'write' && hook.result.current.command.body.secret).toBe('synthetic-original'); expect(state.port.saveSecret).toHaveBeenCalledOnce()
  await act(() => hook.result.current.run('write')); expect(hook.result.current.ack?.revision).toBe(3)
})
test('workspace change clears temporary secrets and ignores the old ACK and refresh callback', async () => {
  const state = providerFixture(), changed = vi.fn(); let finish!: (value: ProviderSecretAck) => void
  state.port.saveSecret = vi.fn(async () => new Promise<ProviderSecretAck>(done => { finish = done }))
  const hook = renderHook(({ workspace }) => useProviderSecret(workspace, state.current(), state.port, changed), { initialProps: { workspace: 'workspace_old_secret' } })
  act(() => hook.result.current.edit('synthetic-old-secret')); let sending!: Promise<void>; act(() => { sending = hook.result.current.run('write') }); await waitFor(() => expect(state.port.saveSecret).toHaveBeenCalledOnce())
  hook.rerender({ workspace: 'workspace_new_secret' }); expect(hook.result.current.text).toBe('')
  await act(async () => { finish({ id: 'provider_test', revision: 2, config_sha256: '2'.repeat(64), secret_present: true }); await sending })
  expect(hook.result.current.ack).toBeNull(); expect(hook.result.current.command).toBeNull(); expect(changed).not.toHaveBeenCalled()
})
test('delete uses the exact captured strong hash; an unknown result cannot turn into a different command', async () => {
  const state = providerFixture(), base = { ...state.current(), secret_present: true }, hook = renderHook(() => useProviderSecret('workspace_delete_secret', base, state.port, vi.fn()))
  state.port.deleteSecret = vi.fn(async () => { throw new ApiError(503, 'controlled') })
  await act(() => hook.result.current.run('delete')); const original = hook.result.current.command
  act(() => hook.result.current.edit('blocked')); await act(() => hook.result.current.run('write')); expect(state.port.saveSecret).not.toHaveBeenCalled()
  await act(() => hook.result.current.run('delete')); expect(vi.mocked(state.port.deleteSecret).mock.calls).toEqual([[base.id, base.config_sha256, original?.key], [base.id, base.config_sha256, original?.key]])
})

test('a new secret command uses its actual readback while the parent still supplies the older config', async () => {
  const state = providerFixture(), base = state.current()
  const hook = renderHook(() => useProviderSecret('workspace_secret_parent_late', base, state.port, vi.fn()))
  act(() => hook.result.current.edit('synthetic-newer-readback'))
  await act(() => hook.result.current.run('write'))
  const readback = state.current(); expect(readback.revision).toBe(2)
  expect(hook.result.current.remote).toEqual(readback); expect(base.revision).toBe(1)
  await act(() => hook.result.current.run('delete'))
  expect(vi.mocked(state.port.deleteSecret).mock.calls[0]?.[1]).toBe(readback.config_sha256)
  expect(hook.result.current.ack?.revision).toBe(3); expect(hook.result.current.rejected).toBe(false)
})

test('a newer parent config takes precedence over an older actual secret readback', async () => {
  const state = providerFixture(), base = state.current()
  const hook = renderHook(({ current }) => useProviderSecret('workspace_secret_parent_newer', current, state.port, vi.fn()), { initialProps: { current: base } })
  act(() => hook.result.current.edit('synthetic-parent-newer'))
  await act(() => hook.result.current.run('write')); expect(hook.result.current.remote?.revision).toBe(2)
  const newer = { ...configFixture(3), secret_present: true }; state.external(newer); hook.rerender({ current: newer })
  await act(() => hook.result.current.run('delete'))
  expect(vi.mocked(state.port.deleteSecret).mock.calls[0]?.[1]).toBe(newer.config_sha256)
  expect(hook.result.current.ack?.revision).toBe(4)
})

test('an ACK alone cannot replace a failed current readback with an invented config basis', async () => {
  const state = providerFixture(), base = state.current()
  state.port.config = vi.fn(async () => { throw new Error('controlled current read unavailable') })
  const hook = renderHook(() => useProviderSecret('workspace_secret_ack_only', base, state.port, vi.fn()))
  act(() => hook.result.current.edit('synthetic-ack-not-current'))
  await act(() => hook.result.current.run('write')); expect(hook.result.current.ack?.revision).toBe(2); expect(hook.result.current.remote).toBeNull()
  await act(() => hook.result.current.run('delete'))
  expect(vi.mocked(state.port.deleteSecret).mock.calls[0]?.[1]).toBe(base.config_sha256)
  expect(hook.result.current.rejected).toBe(true)
})

test('a different provider response cannot become a new secret command basis', async () => {
  const state = providerFixture(), base = state.current()
  state.port.config = vi.fn(async () => ({ ...configFixture(9), id: 'provider_wrong_response', secret_present: true }))
  const hook = renderHook(() => useProviderSecret('workspace_secret_response_id', base, state.port, vi.fn()))
  act(() => hook.result.current.edit('synthetic-provider-identity'))
  await act(() => hook.result.current.run('write'))
  expect(hook.result.current.ack?.revision).toBe(2); expect(hook.result.current.remote).toBeNull()
  expect(hook.result.current.error).toContain('当前配置尚未读回')
  await act(() => hook.result.current.run('delete'))
  expect(vi.mocked(state.port.deleteSecret).mock.calls[0]?.slice(0, 2)).toEqual([base.id, base.config_sha256])
})

for (const changeWorkspace of [true, false]) test(`a delayed read cannot cross the port owner; workspace changed ${changeWorkspace}`, async () => {
  const first = providerFixture(), second = providerFixture(), base = first.current()
  let finish!: (value: ReturnType<typeof configFixture>) => void
  first.port.config = vi.fn(() => new Promise<ReturnType<typeof configFixture>>(resolve => { finish = resolve }))
  const hook = renderHook(({ workspace, port }) => useProviderSecret(workspace, base, port, vi.fn()), { initialProps: { workspace: 'workspace_secret_owner_first', port: first.port } })
  act(() => hook.result.current.edit('synthetic-first-owner'))
  let sending!: Promise<void>; act(() => { sending = hook.result.current.run('write') })
  await waitFor(() => expect(first.port.config).toHaveBeenCalledOnce())
  hook.rerender({ workspace: changeWorkspace ? 'workspace_secret_owner_second' : 'workspace_secret_owner_first', port: second.port })
  await act(async () => { finish({ ...configFixture(9), secret_present: true }); await sending })
  expect(hook.result.current.remote).toBeNull(); expect(hook.result.current.ack).toBeNull()
  await act(() => hook.result.current.run('delete'))
  expect(vi.mocked(second.port.deleteSecret).mock.calls[0]?.slice(0, 2)).toEqual([base.id, base.config_sha256])
})

test('a failed refresh retains the last real read separately from a later ACK', async () => {
  const state = providerFixture(), base = state.current()
  const hook = renderHook(() => useProviderSecret('workspace_secret_read_failure', base, state.port, vi.fn()))
  act(() => hook.result.current.edit('synthetic-last-actual-read'))
  await act(() => hook.result.current.run('write')); const readback = hook.result.current.remote
  expect(readback?.revision).toBe(2)
  state.port.config = vi.fn(async () => { throw new Error('controlled post-delete read failure') })
  await act(() => hook.result.current.run('delete'))
  expect(hook.result.current.ack?.revision).toBe(3); expect(hook.result.current.remote).toEqual(readback)
  expect(hook.result.current.error).toContain('当前配置尚未读回')
})

test('a later parent revision cannot rebase an unknown original secret command', async () => {
  const state = providerFixture(), base = state.current()
  const response = { id: base.id, revision: 2, config_sha256: '2'.repeat(64), secret_present: true }
  state.port.saveSecret = vi.fn().mockRejectedValueOnce(new Error('controlled ACK loss')).mockResolvedValueOnce(response)
  const hook = renderHook(({ current }) => useProviderSecret('workspace_secret_retry_parent', current, state.port, vi.fn()), { initialProps: { current: base } })
  act(() => hook.result.current.edit('synthetic-original-parent-base'))
  await act(() => hook.result.current.run('write')); const original = hook.result.current.command
  const later = { ...configFixture(3), secret_present: true }; state.external(later); hook.rerender({ current: later })
  expect(hook.result.current.command).toEqual(original)
  await act(() => hook.result.current.run('write'))
  expect(vi.mocked(state.port.saveSecret).mock.calls[1]).toEqual(vi.mocked(state.port.saveSecret).mock.calls[0])
  expect(hook.result.current.ack?.revision).toBe(2); expect(hook.result.current.remote?.revision).toBe(3)
})
