import 'fake-indexeddb/auto'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuthoringDraftView, AuthoringJobView, AuthoringPrepareWrite, JobSnapshot, NumericCheckView } from '../../../../../packages/contracts/generated/api-types'
import { AuthoringPanel } from './AuthoringPanel'
import { providerFixture, proposalFixture } from '../providers/testFixtures'
import type { AuthoringPort } from './authoringClient'
import { digest } from '../retrieval/retrievalModel'
afterEach(cleanup)
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`, numericId = `check_${crypto.randomUUID()}`, generationId = `job_${crypto.randomUUID()}`
  const controls: JobSnapshot[] = [], candidate = { draft_id: `draft_${crypto.randomUUID()}`, draft_revision: 1, entity: 'block' as const, candidate_sha256: 'a'.repeat(64) }
  const validation = { schema: 'NOT_RUN' as const, references: 'NOT_RUN' as const, symbol_declarations: 'NOT_RUN' as const, issues: [], mathematical: 'NOT_RUN' as const, sources: 'NOT_RUN' as const, independent_pedagogy: 'NOT_RUN' as const }
  let view: AuthoringJobView | null = null
  const draft: AuthoringDraftView = { owner: 'authoring', candidate, source_job_id: generationId, state: 'draft', base_ref: null, body_sha256: digest('原样合成例题：x=3，因此 x*2=6。'), payload: { version: 'worked-example-candidate-v1', kind: 'worked_example', title: '合成生成候选', body_markdown: '原样合成例题：x=3，因此 x*2=6。', symbols: [{ name: 'x', tex: 'x', domain: 'real', dimension: 'length' }], declared_source_refs: [], numeric_plan: { version: 'finite-arithmetic-v1', seed: null, variables: [{ name: 'x', value: 3, unit: 'm' }], assertions: [{ id: 'assertion_double', expression: 'x*2', expected: 6, atol: 0, rtol: 0, unit: 'm' }] } }, validation: { ...validation, schema: 'PASS', references: 'PASS', symbol_declarations: 'PASS' }, numeric_check_ids: [], warnings: [] }
  let numeric: NumericCheckView = { id: numericId, revision: 1, candidate, plan: draft.payload.numeric_plan, runtime: { evaluator_version: 'finite-arithmetic-v1', evaluator_sha256: 'b'.repeat(64), runtime_manifest_sha256: 'c'.repeat(64), python_version: 'synthetic-python', sandbox_version: 'synthetic-isolation', wall_seconds: 5, cpu_seconds: 2, memory_bytes: 268435456, output_bytes: 65536, evaluator_process_limit: 1 }, operation_sha256: 'd'.repeat(64), decision: 'pending', created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 600_000).toISOString(), expired: false, job: null, job_revision: null, result: null, warnings: [] }
  const provider = providerFixture().port
  const proposal = proposalFixture(); proposal.id = `proposal_${crypto.randomUUID()}`; proposal.summary.purpose = 'authoring'; proposal.summary.job_id = generationId
  provider.preview = vi.fn(async body => { proposal.summary.budget = { ...body.budget, timeout_seconds: body.budget.timeout_seconds ?? 180 }; proposal.summary.expires_at = body.expires_at; view!.proposal_id = proposal.id; return structuredClone(proposal) })
  provider.proposal = vi.fn(async () => structuredClone(proposal))
  provider.grant = vi.fn(async body => { proposal.consent_id = 'consent_synthetic'; view = { ...view!, consent_id: proposal.consent_id, summary: { ...view!.summary, status: 'completed', job_revision: 3, candidate }, provider_receipt_id: 'receipt_synthetic', provider_outcome: 'completed', raw_answer: JSON.stringify(draft.payload), validation: draft.validation }; controls[0] = { ...controls[0], status: 'completed', revision: 3 }; return { id: proposal.consent_id, revision: 1, status: 'active', ...body, summary: structuredClone(proposal.summary) } })
  const port: AuthoringPort = {
    session: vi.fn<AuthoringPort['session']>(async () => ({ workspace_id: workspace, role: 'author', csrf_token: 'synthetic-test-only', active_independent_attempt_id: null, active_open_book_attempt_id: null })),
    list: vi.fn(async () => ({ items: structuredClone(controls), next_cursor: null })),
    prepare: vi.fn<AuthoringPort['prepare']>(async (body: AuthoringPrepareWrite) => { controls.push({ id: generationId, workspace_id: workspace, kind: 'authoring', status: 'awaiting_approval', revision: 1, created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z', progress: { completed: 0, total: null, label: '等待明确授权' }, result_refs: [], warnings: [], error: null }); view = { summary: { id: generationId, kind: 'authoring', status: 'awaiting_approval', job_revision: 1, title: body.topic, candidate: null, created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z' }, request: body, preparation: { context_snapshot_id: 'context_synthetic', snapshot_sha256: 'a'.repeat(64), job_input_sha256: 'b'.repeat(64), prepared_input_sha256: 'c'.repeat(64), character_count: 200, materials: [], warnings: [] }, proposal_id: null, consent_id: null, provider_receipt_id: null, provider_outcome: null, usage: { input_tokens: null, output_tokens: null }, raw_answer: null, raw_refusal: null, validation, error_code: null }; return { id: generationId, status: 'awaiting_approval' } }),
    read: vi.fn(async () => structuredClone(view!)), draft: vi.fn(async () => structuredClone(draft)),
    preview: vi.fn(async () => { draft.numeric_check_ids.push(numericId); return structuredClone(numeric) }), numeric: vi.fn(async () => structuredClone(numeric)),
    decide: vi.fn<AuthoringPort['decide']>(async (_id, body) => { numeric = { ...numeric, revision: 2, decision: body.decision }; return { id: numericId, revision: 2, operation_sha256: body.operation_sha256, decision: body.decision, applied: true, job: null } }),
    job: vi.fn(async id => structuredClone(controls.find(v => v.id === id)!)), cancel: vi.fn(async () => { throw new Error('Not exercised') }),
  }
  return { workspace, port, provider, generationId, numericId }
}
test('typed component flow prepares once, approves same Job, reads draft and declines a separate numeric preview without execution', async () => {
  const f = fixture(), onState = vi.fn()
  render(<AuthoringPanel workspace={f.workspace} paused={false} currentBlock={null} port={f.port} provider={f.provider} onState={onState} />)
  await screen.findByRole('textbox', { name: '例题主题' })
  fireEvent.change(screen.getByLabelText('例题主题'), { target: { value: '合成教学主题' } }); fireEvent.change(screen.getByLabelText('学习目标（每行一条，至少一条）'), { target: { value: '明确计算步骤' } }); fireEvent.change(screen.getByLabelText('已配置的提供商 ID'), { target: { value: 'provider_test' } })
  await waitFor(() => expect(onState.mock.lastCall?.[0].dirty).toBe(true))
  await waitFor(() => expect((screen.getByRole('button', { name: '明确准备本次例题任务' }) as HTMLButtonElement).matches(':disabled')).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '明确准备本次例题任务' }))
  await screen.findByRole('button', { name: `读取创作详情 ${f.generationId}` })
  expect(f.provider.preview).not.toHaveBeenCalled(); expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.read).not.toHaveBeenCalled()
  expect(f.port.prepare).toHaveBeenCalledWith({ topic: '合成教学主题', prerequisites: [], objectives: ['明确计算步骤'], proof_policy: 'full', output_kind: 'worked_example', provider_id: 'provider_test', source_refs: [] }, expect.any(String))
  fireEvent.click(screen.getByRole('button', { name: `读取创作详情 ${f.generationId}` }))
  await screen.findByLabelText('最大输入 token')
  await waitFor(() => expect((screen.getByRole('button', { name: '准备服务端预览命令' }) as HTMLButtonElement).matches(':disabled')).toBe(false))
  fireEvent.change(screen.getByLabelText('最大输入 token'), { target: { value: '20000' } }); fireEvent.change(screen.getByLabelText('最大输出 token'), { target: { value: '2000' } }); fireEvent.change(screen.getByLabelText('到期时间 UTC'), { target: { value: '2099-01-01T00:00:00Z' } })
  fireEvent.click(screen.getByRole('button', { name: '准备服务端预览命令' }))
  await waitFor(() => expect((screen.getByRole('button', { name: '确认发送授权预览' }) as HTMLButtonElement).matches(':disabled')).toBe(false)); fireEvent.click(screen.getByRole('button', { name: '确认发送授权预览' }))
  await screen.findByLabelText('我已核对本次例题的冻结范围、提供商、预算与到期时间')
  fireEvent.click(screen.getByLabelText('我已核对本次例题的冻结范围、提供商、预算与到期时间')); fireEvent.click(screen.getByRole('button', { name: '准备批准例题模型调用' }))
  await waitFor(() => expect((screen.getByRole('button', { name: '确认发送批准授权' }) as HTMLButtonElement).matches(':disabled')).toBe(false)); fireEvent.click(screen.getByRole('button', { name: '确认发送批准授权' }))
  await screen.findByRole('button', { name: '读取这份准确例题候选' }); expect(f.port.prepare).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: '读取这份准确例题候选' })); await screen.findByText('原样合成例题：x=3，因此 x*2=6。')
  expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '明确准备独立数值检查预览' }))
  await waitFor(() => expect(f.port.preview).toHaveBeenCalledTimes(1)); await waitFor(() => expect((screen.getByRole('button', { name: '刷新候选的检查记录' }) as HTMLButtonElement).matches(':disabled')).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '刷新候选的检查记录' })); fireEvent.click(await screen.findByRole('button', { name: `读取数值检查 ${f.numericId}` }))
  await screen.findByRole('button', { name: '明确拒绝本次数值执行' }); expect(f.port.decide).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '明确拒绝本次数值执行' }))
  await waitFor(() => expect(f.port.decide).toHaveBeenCalledWith(f.numericId, { decision: 'decline', expected_revision: 1, operation_sha256: 'd'.repeat(64) }, expect.any(String)))
  expect(f.port.prepare).toHaveBeenCalledTimes(1); expect(f.provider.grant).toHaveBeenCalledTimes(1)
})
