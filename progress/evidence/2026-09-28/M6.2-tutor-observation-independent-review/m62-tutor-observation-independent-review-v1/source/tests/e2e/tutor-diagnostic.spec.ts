import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { readFile } from 'node:fs/promises'
import { observeTutorCompletion, safeAPIMechanism } from './tutorDiagnostic'

test('diagnostic retains the original five-second failure and a completed peer read without collecting private text', async ({ page }, info) => {
  await page.setContent('<section aria-label="真实问答线程与任务"><section aria-label="当前问答任务"><h3>真实任务状态：queued</h3><p role="status">正在观察任务；断开观察不会取消任务</p></section><pre aria-label="本次模型回答原文">SYNTHETIC_PRIVATE_BODY_NOT_FOR_DIAGNOSTIC</pre><input value="SYNTHETIC_PRIVATE_KEY_NOT_FOR_DIAGNOSTIC"></section>')
  const observer = await observeTutorCompletion(page, {
    readRun: () => new Promise(() => undefined),
    readRuntime: async () => ({ test_only: true, received_request_count: 0, validated_request_count: 0, invalid_request_count: 0, secret: 'SYNTHETIC_PRIVATE_KEY_NOT_FOR_DIAGNOSTIC' }),
  })
  observer.bindRun('run_synthetic_diagnostic')
  let original: unknown, caught: unknown
  try {
    try {
      await observer.around(info, async () => {
        try { await expect(page.getByRole('heading', { name: '真实任务状态：completed', exact: true })).toBeVisible() }
        catch (error) { original = error; throw error }
      })
    } catch (error) { caught = error }
    expect(original).toBeInstanceOf(Error); expect(caught).toBe(original)
    expect(String(caught)).toContain('5000ms')
    const raw = await readFile(info.outputPath('tutor-completion-diagnostic.json'), 'utf8'), value = JSON.parse(raw)
    expect(raw).not.toContain('SYNTHETIC_PRIVATE_')
    expect(value.assertion.verdict).toBe('failed')
    expect(value.frozen_observation.last_dom_delivered.state.run_status).toBe('queued')
    expect(value.post_assertion.phase).toBe('post-failure')
    expect(value.post_assertion.wait_limit_ms).toBe(500)
    expect(value.post_assertion.run).toEqual({ state: 'timeout' })
    expect(value.post_assertion.runtime).toEqual({ state: 'complete', value: { test_only: true, received_request_count: 0, validated_request_count: 0, invalid_request_count: 0 } })
  } finally { observer.dispose() }
})

test('diagnostic closes metadata, freezes delivered ordinals and leaves missing observations unknown', async ({ page }, info) => {
  const snapshot = { epoch: 'a'.repeat(32), selected_run: 'run_metadata', snapshot_source_ns: 5, omitted: 1, invalid: 0, snapshot_contended: false,
    records: [{ epoch: 'a'.repeat(32), ordinal: 1, source_ns: 4, stage: 'tutor_terminal_committed', run: 'run_metadata', status: 'completed' }] }
  expect(safeAPIMechanism(snapshot, 'run_metadata').records).toEqual(snapshot.records)
  expect(() => safeAPIMechanism(snapshot, 'run_other')).toThrow('INVALID_API_MECHANISM')
  await page.setContent('<section aria-label="真实问答线程与任务"><section aria-label="当前问答任务" data-tutor-observation="page:1"><h3>真实任务状态：completed</h3><p>run_metadata · Jobs r3 · 事件水位 2</p></section></section>')
  const observer = await observeTutorCompletion(page, {
    readRun: async () => ({ run: { id: 'run_metadata', status: 'completed', last_seq: 2, answer_markdown: 'PRIVATE_BODY' }, job_revision: 3 }),
    readRuntime: async () => ({ test_only: true, received_request_count: 1, validated_request_count: 1, invalid_request_count: 0,
      mechanism: { epoch: 'a'.repeat(32), selected_run: 'run_metadata', snapshot_source_ns: 5, omitted: 1, invalid: 0, snapshot_contended: false,
        records: [{ epoch: 'a'.repeat(32), ordinal: 1, source_ns: 4, stage: 'tutor_terminal_committed', run: 'run_metadata', status: 'completed', text: 'PRIVATE_BODY' }] } }),
  })
  observer.bindRun('run_metadata')
  try {
    await page.evaluate(async () => {
      const sink = (window as unknown as { __tutorDiagnosticMechanism: (value: unknown) => Promise<void> }).__tutorDiagnosticMechanism
      const value = { epoch: 'page', ordinal: 1, source_ms: 1, stage: 'snapshot_accepted', run: 'run_metadata', operation: 3, after: 2, span: 'page:1', seq: 2, revision: 3, status: 'completed' }
      await sink([{ ...value, text: 'PRIVATE_BODY' }])
      await sink([value])
    })
    await observer.around(info, async () => { await expect(page.getByRole('heading', { name: '真实任务状态：completed', exact: true })).toBeVisible() })
    // A delivery after around() cannot rewrite the frozen file.
    await page.evaluate(async () => { await (window as unknown as { __tutorDiagnosticMechanism: (value: unknown) => Promise<void> }).__tutorDiagnosticMechanism([{ text: 'PRIVATE_LATE' }]) })
    const raw = await readFile(info.outputPath('tutor-completion-diagnostic.json'), 'utf8'), value = JSON.parse(raw)
    expect(raw).not.toContain('PRIVATE_')
    expect(value.mechanism.invalid_deliveries).toBe(1)
    expect(value.mechanism.frozen_browser_records).toHaveLength(1)
    expect(value.mechanism.frozen_dom_projections).toHaveLength(1)
    expect(value.mechanism.frozen_dom_projections[0].matched_source).toBe(true)
    expect(value.mechanism.frozen_browser_records[0].delivered_ms).toBeLessThanOrEqual(value.assertion.frozen_at_ms)
    expect(value.mechanism.post_assertion_api).toEqual({ state: 'failed' })
    expect(value.mechanism.post_assertion_browser).toEqual({ state: 'failed' })
    expect(value.post_assertion.run.state).toBe('complete')
  } finally { observer.dispose() }
})
