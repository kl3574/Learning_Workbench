import { act, cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { IDBFactory } from 'fake-indexeddb'
import { DraftStore } from '../../workbench/DraftStore'
import { useTutor } from './useTutor'
import { TutorWorkflow } from './TutorWorkflow'
import type { TutorPort } from './tutorClient'
import type { TutorRunView } from '../../../../../packages/contracts/generated/api-types'
import { tutorBinding, tutorRun, tutorScope, tutorThread } from './tutorFixtures'
import type { TutorObservationRecord } from './tutorObservation'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })
it.each([false, true])('binds accepted read to actual DOM, and rejects late delivery after scope change (%s)', async revoked => {
  vi.stubGlobal('__tutorObservationEnabled', true)
  const records: TutorObservationRecord[] = []
  vi.stubGlobal('__tutorDiagnosticMechanism', (batch: TutorObservationRecord[]) => { records.push(...batch); throw new Error('UNTRUSTED_OBSERVER') })
  let resolve!: (value: TutorRunView) => void
  const port: TutorPort = { threads: async () => ({ items: [tutorThread()], next_cursor: null }), create: async () => tutorThread(),
    messages: async () => ({ thread: tutorThread(), items: [], next_cursor: null }), start: async () => tutorRun(),
    read: vi.fn().mockResolvedValueOnce(tutorRun()).mockImplementationOnce(() => new Promise(done => { resolve = done })),
    cancel: vi.fn(), events: async function* () { yield { type: 'completed', run_id: tutorRun().run.id, seq: 2, occurred_at: '2026-09-22T00:00:00Z' } } }
  const store = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() })
  const bind = async () => ({ scope: tutorScope, binding: tutorBinding }), location = { context: tutorScope }
  let state!: ReturnType<typeof useTutor>
  function Screen({ paused }: { paused: boolean }) { state = useTutor('workspace_tutor_test', location, paused, port, bind, store); return <TutorWorkflow workspace="workspace_tutor_test" state={state} settings={() => undefined} /> }
  const view = render(<Screen paused={false} />)
  await waitFor(() => expect(state.ready && state.bound).toBeTruthy())
  await act(async () => state.select(tutorThread()))
  await act(async () => state.start('PRIVATE_ORIGINAL_QUESTION', 'explain'))
  await waitFor(() => expect(port.read).toHaveBeenCalledTimes(2))
  if (revoked) view.rerender(<Screen paused />)
  const complete = tutorRun(); complete.run.status = 'completed'; complete.run.last_seq = 2; complete.job_revision = 3
  await act(async () => resolve(complete))
  await waitFor(() => expect(records.some(value => value.stage === (revoked ? 'scope_discarded' : 'snapshot_accepted') && value.after === 2)).toBe(true))
  if (revoked) {
    expect(state.run).toBeNull()
    expect(view.queryByRole('heading', { name: '真实任务状态：completed' })).toBeNull()
    expect(records.filter(value => value.stage === 'snapshot_accepted' && value.status === 'completed')).toEqual([])
  } else {
    const region = view.getByRole('region', { name: '当前问答任务' })
    const token = region.getAttribute('data-tutor-observation')
    const accepted = records.find(value => `${value.epoch}:${value.ordinal}` === token)!
    expect(accepted).toMatchObject({ stage: 'snapshot_accepted', run: complete.run.id, seq: 2, revision: 3, status: 'completed' })
    const trigger = records.find(value => value.stage === 'reload_trigger')!
    expect(accepted.cause).toBe(trigger.span)
    expect(region.textContent).toContain('真实任务状态：completed')
  }
  expect(JSON.stringify(records)).not.toContain('PRIVATE_ORIGINAL_QUESTION')
})
