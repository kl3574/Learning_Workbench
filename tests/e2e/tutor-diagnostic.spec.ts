import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { readFile } from 'node:fs/promises'
import { observeTutorCompletion } from './tutorDiagnostic'

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
