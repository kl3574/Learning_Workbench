import { describe, expect, it } from 'vitest'
import type { TutorRunView } from '../../../../../packages/contracts/generated/api-types'
import { acceptRun, observeEvent, threadMatches } from './tutorState'
const ref = { entity: 'lesson' as const, id: 'lesson_unit', revision: 1, sha256: 'a'.repeat(64) }
const scope = { view_kind: 'lesson' as const, active_ref: ref, attached_refs: [], attempt_id: null, selection: null }
const binding = { practice: null, assessment: null }
const run = (): TutorRunView => ({ run: { id: 'run_unit', thread_id: 'thread_unit', status: 'running', context_snapshot_id: null, last_seq: 1, answer_markdown: '', citations: [], search_status: 'not_requested' }, job_revision: 1, thread_revision: 2, context: null, latest_proposal_id: null, consent_id: null, result: { refusal_markdown: '', usage: { input_tokens: null, output_tokens: null }, provider: null, error_code: null } })
const event = { run_id: 'run_unit', seq: 2, occurred_at: '2026-09-15T00:00:00Z' }
describe('Tutor observation ownership and committed result boundary', () => {
  it('preserves whitespace and never converts a terminal event into a committed result', () => {
    const partial = observeEvent(run(), { ...event, type: 'answer_delta', text: ' \n' })
    expect(partial.run.answer_markdown).toBe(' \n')
    const ended = observeEvent(partial, { ...event, seq: 3, type: 'completed' })
    expect(ended.run.status).toBe('running'); expect(ended.result.provider).toBeNull()
    expect(observeEvent(ended, { ...event, seq: 2, type: 'answer_delta', text: 'duplicate' })).toBe(ended)
  })
  it('rejects another run, event gaps and regressing actual usage', () => {
    expect(() => observeEvent(run(), { ...event, run_id: 'run_other', type: 'completed' })).toThrow()
    expect(() => observeEvent(run(), { ...event, seq: 3, type: 'completed' })).toThrow()
    const value = observeEvent(run(), { ...event, type: 'usage', input_tokens: 3, output_tokens: null })
    expect(() => observeEvent(value, { ...event, seq: 3, type: 'usage', input_tokens: null, output_tokens: 1 })).toThrow()
  })
  it('rejects snapshot text replacement, wrong thread and older sequence', () => {
    const value = run(); value.run.answer_markdown = 'actual'; value.run.last_seq = 3
    expect(() => acceptRun(value, { ...run(), run: { ...run().run, last_seq: 4, answer_markdown: 'different' } }, 'thread_unit')).toThrow()
    expect(() => acceptRun(value, run(), 'thread_unit')).toThrow()
    expect(() => acceptRun(null, run(), 'thread_other')).toThrow()
  })
  it('matches full thread root, while permitting a new explicit selection and binding revision', () => {
    const thread = { id: 'thread_unit', revision: 1, created_at: event.occurred_at, title: '合成线程', scope, binding }
    expect(threadMatches(thread, scope, binding)).toBe(true)
    expect(threadMatches(thread, { ...scope, active_ref: { ...ref, revision: 2 } }, binding)).toBe(false)
    expect(threadMatches(thread, { ...scope, active_ref: { ...ref, sha256: 'b'.repeat(64) } }, binding)).toBe(false)
  })
})
