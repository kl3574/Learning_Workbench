import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ConsentPage, ConsentView } from '../../../../../packages/contracts/generated/api-types'
import { useProviderReads } from './useProviderReads'
import { consentFixture, pageFixture, providerFixture } from './testFixtures'
afterEach(cleanup)
test('history pagination carries the actual cursor and does not invent a frozen global snapshot', async () => {
  const fixture = providerFixture(), first = consentFixture(), second: ConsentView = { ...consentFixture(), id: 'consent_older' }
  fixture.port.consents = vi.fn().mockResolvedValueOnce({ items: [first], next_cursor: 'signed_cursor' }).mockResolvedValueOnce(pageFixture([second]))
  const hook = renderHook(() => useProviderReads('workspace_pages', false, '', fixture.port))
  await waitFor(() => expect(hook.result.current.history?.next_cursor).toBe('signed_cursor')); await act(() => hook.result.current.more())
  expect(hook.result.current.history?.items.map(value => value.id)).toEqual(['consent_test', 'consent_older']); expect(fixture.port.consents).toHaveBeenNthCalledWith(2, { cursor: 'signed_cursor', limit: 20 })
  expect(hook.result.current.controlRefs).toEqual([{ id: 'consent_test', revision: 1 }, { id: 'consent_older', revision: 1 }])
})
test('a repeated or tampered next page preserves earlier rows and surfaces failure', async () => {
  const fixture = providerFixture(), first = consentFixture()
  fixture.port.consents = vi.fn().mockResolvedValueOnce({ items: [first], next_cursor: 'signed_cursor' }).mockResolvedValueOnce(pageFixture([first]))
  const hook = renderHook(() => useProviderReads('workspace_bad_page', false, '', fixture.port)); await waitFor(() => expect(hook.result.current.history?.items).toHaveLength(1)); await act(() => hook.result.current.more())
  expect(hook.result.current.history?.items).toEqual([first]); expect(hook.result.current.historyError).toContain('下一页尚未完整读回')
})
test('a late previous-workspace history cannot populate a new page or its safe revoke refs', async () => {
  const fixture = providerFixture(); let release!: (value: ConsentPage) => void
  fixture.port.consents = vi.fn().mockImplementationOnce(async () => new Promise<ConsentPage>(done => { release = done })).mockResolvedValue(pageFixture())
  const hook = renderHook(({ workspace }) => useProviderReads(workspace, false, '', fixture.port), { initialProps: { workspace: 'workspace_old_read' } })
  await waitFor(() => expect(fixture.port.consents).toHaveBeenCalledOnce()); hook.rerender({ workspace: 'workspace_new_read' }); await waitFor(() => expect(hook.result.current.history?.items).toEqual([]))
  await act(async () => { release(pageFixture([consentFixture()])) }); expect(hook.result.current.history?.items).toEqual([]); expect(hook.result.current.controlRefs).toEqual([])
})
