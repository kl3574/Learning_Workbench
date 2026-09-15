import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { TutorEvidence } from './TutorEvidence'
import { tutorRun } from './tutorFixtures'
import type { TutorInputMaterial } from '../../../../../packages/contracts/generated/api-types'
const access = vi.hoisted(() => ({ generation: 0, read: vi.fn() }))
vi.mock('../../api/client', () => ({ getSessionGeneration: () => access.generation }))
vi.mock('../reader/contentClient', () => ({ readBlock: access.read }))
const material: TutorInputMaterial = { reference: { ref: { entity: 'block', id: 'block_original', revision: 1, sha256: 'b'.repeat(64) }, title: '原创未审教材', locator: '本机原文', excerpt_sha256: 'c'.repeat(64), character_count: 3 }, body_sha256: 'c'.repeat(64), material_review: 'unreviewed' }
function value() { const result = tutorRun(); result.context = { snapshot: { id: 'context_original', created_at: '2026-09-15T00:00:00Z', request_sha256: 'd'.repeat(64), resolved_refs: [material.reference.ref], policy: 'learning', character_count: 3, snapshot_sha256: 'e'.repeat(64) }, included: [material], history_message_ids: [], omissions: [], warnings: [] }; return result }
beforeEach(() => { access.generation = 0; access.read.mockReset() })
afterEach(cleanup)
it('keeps model links and refusal as raw text, input unreviewed and unknown usage unknown', () => {
  const run = value(); run.run.answer_markdown = '模型声称 [已证明](https://example.invalid/source)'; run.result.refusal_markdown = ' \n不能确认。'
  render(<TutorEvidence value={run} messages={[]} />)
  expect(screen.getByLabelText('本次模型回答原文').textContent).toBe(run.run.answer_markdown)
  expect(screen.queryAllByRole('link')).toEqual([])
  expect(screen.getByText('原创未审教材 · 材料未审')).toBeTruthy()
  expect(screen.getByText('这些记录仅证明输入了什么，不证明答案或推导受到这些材料支持。')).toBeTruthy()
  expect(screen.getByText(/输入 token：未知；输出 token：未知/)).toBeTruthy()
  expect(access.read).not.toHaveBeenCalled()
})
it('reads only an explicitly requested exact block and rejects body not matching frozen input', async () => {
  access.read.mockResolvedValue({ block: { body_sha256: 'f'.repeat(64) }, body: '假原文' })
  render(<TutorEvidence value={value()} messages={[]} />)
  fireEvent.click(screen.getByRole('button', { name: '核对本次输入的完整块原文', hidden: true }))
  await screen.findByRole('alert', { hidden: true })
  expect(access.read).toHaveBeenCalledWith(material.reference.ref)
  expect(screen.queryByText('假原文')).toBeNull()
})
it('discards an exact original read when the session becomes unavailable before delivery', async () => {
  let finish!: (value: unknown) => void
  access.read.mockImplementation(() => new Promise(done => { finish = done }))
  render(<TutorEvidence value={value()} messages={[]} />)
  fireEvent.click(screen.getByRole('button', { name: '核对本次输入的完整块原文', hidden: true }))
  await act(async () => { access.generation++; finish({ block: { body_sha256: material.body_sha256 }, body: '真原文' }) })
  expect(screen.queryByText('真原文')).toBeNull()
})
