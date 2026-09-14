import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { RouteRecord } from './routeClient'
import { RouteEditor } from './RouteEditor'
const access = vi.hoisted(() => ({ value: 0, listeners: new Set<() => void>(), write: vi.fn() }))
vi.mock('../../api/client', async original => ({ ...await original<typeof import('../../api/client')>(), getSessionGeneration: () => access.value, subscribeSessionAccess: (listener: () => void) => { access.listeners.add(listener); return () => access.listeners.delete(listener) }, request: access.write }))
vi.mock('./routeChoices', () => ({ readRouteChoices: async () => [] }))
afterEach(cleanup)
const initial: RouteRecord = { route: { id: 'route_policy_restore', revision: 1, title: '原创路线', goal: '原目标', steps: [{ id: 'step_read', title: '阅读', target: { entity: 'lesson', id: 'lesson_original', revision: 1, sha256: 'c'.repeat(64) }, completion_rule: 'read' }] }, ref: { entity: 'route', id: 'route_policy_restore', revision: 1, sha256: 'a'.repeat(64) }, bindings: [] }
test('a route command in flight through an access change can recover its actual receipt after policy resumes', async () => {
  let release!: (ref: ContentRef) => void
  const receipt: ContentRef = { ...initial.ref, revision: 2, sha256: 'd'.repeat(64) }
  access.write.mockImplementationOnce(() => new Promise<ContentRef>(resolve => { release = resolve })).mockResolvedValue(receipt)
  const props = { workspace: 'workspace_route_policy_restore', initial, paused: false, onState: vi.fn(), saved: vi.fn() }
  const view = render(<RouteEditor {...props} />)
  await waitFor(() => expect((screen.getByRole('button', { name: '编辑此路线修订' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '编辑此路线修订' })); fireEvent.change(screen.getByLabelText('路线学习目标'), { target: { value: '真实未同步路线目标' } })
  await waitFor(() => expect((screen.getByRole('button', { name: '保存路线新修订' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '保存路线新修订' })); await waitFor(() => expect(access.write).toHaveBeenCalledTimes(1))
  act(() => { access.value++; access.listeners.forEach(listener => listener()) }); view.rerender(<RouteEditor {...props} paused />)
  await act(async () => release(receipt)); view.rerender(<RouteEditor {...props} />)
  // A late receipt may be offered for explicit replay or adopted after a
  // current permission check, but must not leave every recovery action blocked.
  await waitFor(() => {
    const retry = screen.queryByRole('button', { name: '保存路线新修订' }), opened = screen.queryByRole('button', { name: '打开已保存路线' })
    expect((retry instanceof HTMLButtonElement && !retry.disabled) || (opened instanceof HTMLButtonElement && !opened.disabled)).toBe(true)
  })
})

test('policy resume allows another route edit without a late old receipt replacing its durable command', async () => {
  access.write.mockReset()
  let release!: (ref: ContentRef) => void
  access.write.mockImplementation(() => new Promise<ContentRef>(resolve => { release = resolve }))
  const props = { workspace: 'workspace_route_newer_command', initial, paused: false, onState: vi.fn(), saved: vi.fn() }
  const view = render(<RouteEditor {...props} />)
  await waitFor(() => expect((screen.getByRole('button', { name: '编辑此路线修订' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '编辑此路线修订' })); fireEvent.change(screen.getByLabelText('路线学习目标'), { target: { value: 'Old submitted route command A' } })
  await waitFor(() => expect((screen.getByRole('button', { name: '保存路线新修订' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '保存路线新修订' })); await waitFor(() => expect(access.write).toHaveBeenCalledTimes(1))
  act(() => { access.value++; access.listeners.forEach(listener => listener()) }); view.rerender(<RouteEditor {...props} paused />); view.rerender(<RouteEditor {...props} />)
  await waitFor(() => expect(screen.getByLabelText('路线学习目标').closest('fieldset')?.disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('路线学习目标'), { target: { value: 'New durable route candidate B' } })
  const { routeStore } = await import('./routeDrafts')
  let candidate = ''
  await waitFor(async () => { const disk = await routeStore.load(props.workspace); candidate = Object.values(disk)[0]?.text ?? ''; expect(candidate).toContain('New durable route candidate B') })
  await act(async () => release({ ...initial.ref, revision: 2, sha256: 'd'.repeat(64) }))
  expect((screen.getByLabelText('路线学习目标') as HTMLTextAreaElement).value).toBe('New durable route candidate B')
  const disk = Object.values(await routeStore.load(props.workspace))[0]
  expect([disk.text, ...disk.conflicts.map(item => item.text)]).toContain(candidate)
})
