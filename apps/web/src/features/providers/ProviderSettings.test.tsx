import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ConsentPage } from '../../../../../packages/contracts/generated/api-types'
import { ProviderSettings } from './ProviderSettings'
import { ConsentSummary } from './ConsentSummary'
import { pageFixture, proposalFixture, providerFixture } from './testFixtures'
afterEach(cleanup)
const workspace = () => `workspace_${crypto.randomUUID()}`

test('settings shows actual empty controls/source state without a prompt or job-id entry', async () => {
  const fixture = providerFixture(); fixture.port.capabilities = vi.fn(async () => ({ items: [] })); fixture.port.consents = vi.fn(async () => pageFixture())
  render(<ProviderSettings workspace={workspace()} paused={false} port={fixture.port} onState={vi.fn()} />)
  await waitFor(() => expect(screen.getByText('本工作区尚无提供商配置。')).toBeTruthy())
  expect(screen.getByText('本阶段尚无可发起授权的生成任务。后续由真实生成任务提供准备好的输入；这里不创建任意提示词任务。')).toBeTruthy()
  await waitFor(() => expect(screen.getByText('本工作区尚无授权记录。')).toBeTruthy())
  expect(screen.queryByRole('textbox', { name: /任务|提示词/ })).toBeNull(); expect(fixture.port.preview).not.toHaveBeenCalled(); expect(fixture.port.grant).not.toHaveBeenCalled(); expect(fixture.port.saveSecret).not.toHaveBeenCalled()
})
test('config remains visibly separate from proof readiness and send needs a durable original command', async () => {
  const fixture = providerFixture(), changed = vi.fn()
  render(<ProviderSettings workspace={workspace()} paused={false} port={fixture.port} onState={changed} />)
  await waitFor(() => expect(screen.getByRole('button', { name: 'provider_test' })).toBeTruthy())
  expect(screen.getByText(/INPUT_BOUND_UNAVAILABLE/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'provider_test' }))
  await waitFor(() => expect(screen.getByLabelText('模型名称')).toHaveProperty('value', 'synthetic-model-1'))
  fireEvent.change(screen.getByLabelText('模型名称'), { target: { value: 'my-model-candidate' } })
  await waitFor(() => expect(screen.getByRole('button', { name: '准备配置保存命令' }).matches(':disabled')).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '准备配置保存命令' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '确认发送配置保存' }).matches(':disabled')).toBe(false))
  expect(fixture.port.saveConfig).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '确认发送配置保存' }))
  await waitFor(() => expect(fixture.current().revision).toBe(2))
  await waitFor(() => expect(screen.getByText('原命令已确认 · 修订 2。此回执保留当时事实，不替代当前状态。')).toBeTruthy())
  expect(fixture.port.preview).not.toHaveBeenCalled(); expect(fixture.port.saveSecret).not.toHaveBeenCalled()
})
test('a same-provider refresh must not discard an unacknowledged temporary secret', async () => {
  const fixture = providerFixture(); fixture.port.saveSecret = vi.fn(async () => { throw new Error('controlled unknown') })
  render(<ProviderSettings workspace={workspace()} paused={false} port={fixture.port} onState={vi.fn()} />)
  await waitFor(() => expect(screen.getByRole('button', { name: 'provider_test' })).toBeTruthy()); fireEvent.click(screen.getByRole('button', { name: 'provider_test' }))
  await waitFor(() => expect(screen.getByLabelText('新秘密').matches(':disabled')).toBe(false))
  fireEvent.change(screen.getByLabelText('新秘密'), { target: { value: 'synthetic-retained' } }); fireEvent.click(screen.getByRole('button', { name: '保存秘密' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '重试原秘密写入命令' }).matches(':disabled')).toBe(false))
  // The child retry control settles before its busy effect reaches the parent.
  await waitFor(() => expect(screen.getByRole('button', { name: '重新读取配置与能力' }).matches(':disabled')).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '重新读取配置与能力' }))
  await waitFor(() => expect(fixture.port.config).toHaveBeenCalledTimes(2))
  expect(screen.getByLabelText('新秘密')).toHaveProperty('value', 'synthetic-retained')
  fireEvent.click(screen.getByRole('button', { name: '重试原秘密写入命令' }))
  await waitFor(() => expect(fixture.port.saveSecret).toHaveBeenCalledTimes(2))
  expect(vi.mocked(fixture.port.saveSecret).mock.calls[0]).toEqual(vi.mocked(fixture.port.saveSecret).mock.calls[1])
})
test('policy hides previously read summaries but preserves only safe revoke identities', async () => {
  const fixture = providerFixture(), id = workspace(), view = render(<ProviderSettings workspace={id} paused={false} port={fixture.port} onState={vi.fn()} />)
  await waitFor(() => expect(screen.getByRole('region', { name: '授权 consent_test' })).toBeTruthy())
  view.rerender(<ProviderSettings workspace={id} paused={true} port={fixture.port} onState={vi.fn()} />)
  expect(screen.queryByRole('region', { name: '授权 consent_test' })).toBeNull()
  expect(screen.queryByText('synthetic-model-1', { exact: true })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '准备撤销 consent_test' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '确认发送撤销授权' }).matches(':disabled')).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '确认发送撤销授权' }))
  await waitFor(() => expect(fixture.port.revoke).toHaveBeenCalledOnce())
  expect(fixture.port.consents).toHaveBeenCalledOnce(); expect(fixture.port.preview).not.toHaveBeenCalled(); expect(fixture.port.grant).not.toHaveBeenCalled()
})
test('late history after policy change supplies neither summaries nor new revoke identities', async () => {
  const fixture = providerFixture(); let finish!: (value: ConsentPage) => void
  fixture.port.consents = vi.fn(async () => new Promise<ConsentPage>(done => { finish = done }))
  const id = workspace(), view = render(<ProviderSettings workspace={id} paused={false} port={fixture.port} onState={vi.fn()} />)
  await waitFor(() => expect(fixture.port.consents).toHaveBeenCalledOnce()); view.rerender(<ProviderSettings workspace={id} paused={true} port={fixture.port} onState={vi.fn()} />)
  await act(async () => { finish(pageFixture([fixture.currentConsent()])) })
  expect(screen.queryByRole('region', { name: '授权 consent_test' })).toBeNull(); expect(screen.queryByRole('button', { name: '准备撤销 consent_test' })).toBeNull()
})
test('summary labels an upper bound and unknown price without inventing usage or a quote', () => {
  const summary = proposalFixture().summary
  render(<ConsentSummary value={summary} />)
  const view = within(screen.getByRole('region', { name: '冻结外发摘要' }))
  expect(view.getByText(/已核上界 8（不是实际用量）/)).toBeTruthy(); expect(view.getByText(/价格未知，金额没有硬保证/)).toBeTruthy()
  expect(view.getByText(/提供商调用 1 次；搜索 0 次；工具 0 次/)).toBeTruthy()
  expect(view.getByText(summary.input_token_assurance.request_body_sha256)).toBeTruthy(); expect(view.getByText('该冻结材料没有引用摘录。')).toBeTruthy()
})
test('reusable preview accepts a consumer-owned task but cannot manufacture a task or dispatch on approval', async () => {
  const fixture = providerFixture(), id = workspace()
  render(<ProviderSettings workspace={id} paused={false} port={fixture.port} onState={vi.fn()} task={{ job_id: 'job_test', expected_job_revision: 1 }} />)
  await waitFor(() => expect(screen.getByRole('button', { name: 'provider_test' })).toBeTruthy()); fireEvent.click(screen.getByRole('button', { name: 'provider_test' }))
  await waitFor(() => expect(screen.getByLabelText('最大输入 token').matches(':disabled')).toBe(false))
  fireEvent.change(screen.getByLabelText('最大输入 token'), { target: { value: '10' } }); fireEvent.change(screen.getByLabelText('最大输出 token'), { target: { value: '20' } }); fireEvent.change(screen.getByLabelText('到期时间 UTC'), { target: { value: proposalFixture().summary.expires_at } })
  fireEvent.click(screen.getByRole('button', { name: '准备服务端预览命令' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '确认发送授权预览' }).matches(':disabled')).toBe(false)); fireEvent.click(screen.getByRole('button', { name: '确认发送授权预览' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '核对范围后准备批准命令' }).matches(':disabled')).toBe(false))
  expect(fixture.port.grant).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '核对范围后准备批准命令' })); await waitFor(() => expect(screen.getByRole('button', { name: '确认发送批准授权' }).matches(':disabled')).toBe(false)); fireEvent.click(screen.getByRole('button', { name: '确认发送批准授权' }))
  await waitFor(() => expect(fixture.port.grant).toHaveBeenCalledOnce())
  const call = vi.mocked(fixture.port.grant).mock.calls[0]; expect(call[0]).toEqual({ proposal_id: 'proposal_test', proposal_sha256: 'a'.repeat(64) }); expect(fixture.port.preview).toHaveBeenCalledOnce()
})
