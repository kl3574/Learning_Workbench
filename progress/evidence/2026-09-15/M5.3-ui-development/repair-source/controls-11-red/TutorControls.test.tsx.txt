import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { TutorControls } from './TutorControls'
const access = vi.hoisted(() => ({ generation: 0, request: vi.fn() }))
vi.mock('../../api/client', () => ({ getSessionGeneration: () => access.generation, request: access.request }))
beforeEach(() => { access.generation = 0; access.request.mockReset() })
afterEach(cleanup)
const props = { workspace: 'workspace_controls_a', commands: [], known: ['run_controls_a'], execute: vi.fn(), busy: false }
it('releases an old pending control read on workspace change and never displays its private fields', async () => {
  let finish!: (value: unknown) => void
  access.request.mockImplementationOnce(() => new Promise(done => { finish = done }))
  const view = render(<TutorControls {...props} />)
  fireEvent.click(screen.getByRole('button', { name: '读取任务控制 run_controls_a' }))
  await waitFor(() => expect(access.request).toHaveBeenCalledTimes(1))
  view.rerender(<TutorControls {...props} workspace="workspace_controls_b" known={['run_controls_b']} />)
  await waitFor(() => expect((screen.getByRole('button', { name: '读取任务控制 run_controls_b' }) as HTMLButtonElement).disabled).toBe(false))
  access.request.mockResolvedValueOnce({ id: 'run_controls_b', workspace_id: 'workspace_controls_b', kind: 'tutor', status: 'running', revision: 4, error: { message: '禁止显示的原问题' } })
  fireEvent.click(screen.getByRole('button', { name: '读取任务控制 run_controls_b' }))
  await screen.findByText('run_controls_b · running · r4')
  await act(async () => finish({ id: 'run_controls_a', workspace_id: 'workspace_controls_a', kind: 'tutor', status: 'running', revision: 8 }))
  expect(screen.queryByText('run_controls_a · running · r8')).toBeNull()
  expect(screen.queryByText('禁止显示的原问题')).toBeNull()
  expect(access.request.mock.calls.map(call => call[0])).toEqual(['GET /api/v1/jobs/{id}', 'GET /api/v1/jobs/{id}'])
})
it('releases a pending read after session generation changes and suppresses the late same-workspace result', async () => {
  let finish!: (value: unknown) => void
  access.request.mockImplementationOnce(() => new Promise(done => { finish = done }))
  const view = render(<TutorControls {...props} />)
  fireEvent.click(screen.getByRole('button', { name: '读取任务控制 run_controls_a' }))
  await waitFor(() => expect(access.request).toHaveBeenCalledTimes(1))
  access.generation++
  view.rerender(<TutorControls {...props} />)
  await waitFor(() => expect((screen.getByRole('button', { name: '读取任务控制 run_controls_a' }) as HTMLButtonElement).disabled).toBe(false))
  await act(async () => finish({ id: 'run_controls_a', workspace_id: props.workspace, kind: 'tutor', status: 'running', revision: 8 }))
  expect(screen.queryByText('run_controls_a · running · r8')).toBeNull()
})
it('does not permit cancelling a Job belonging to another workspace or kind', async () => {
  access.request.mockResolvedValue({ id: 'run_controls_a', workspace_id: 'workspace_other', kind: 'tutor', status: 'running', revision: 8 })
  render(<TutorControls {...props} />)
  fireEvent.click(screen.getByRole('button', { name: '读取任务控制 run_controls_a' }))
  await screen.findByRole('alert')
  expect(screen.queryByRole('button', { name: '明确请求取消此任务' })).toBeNull()
})
