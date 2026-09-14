import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ReviewWarnings } from './ReviewWarnings'

afterEach(cleanup)

it('requires explicit warning-code acceptance and exposes no acceptance for blocking errors', () => {
  const change = vi.fn()
  render(<ReviewWarnings accepted={[]} change={change} disabled={false} warnings={[
    { code: 'TEXT_UNSTRUCTURED', message: '纯文本未结构化', locator: null, severity: 'warning' },
    { code: 'HASH_INVALID', message: '清单哈希失败', locator: 'content/a.md', severity: 'error' },
  ]} />)
  expect(screen.getAllByRole('checkbox')).toHaveLength(1)
  fireEvent.click(screen.getByRole('checkbox'))
  expect(change).toHaveBeenCalledWith(['TEXT_UNSTRUCTURED'])
  expect(screen.getByText(/不能通过接受警告绕过/)).toBeTruthy()
})

it('does not fabricate a content review when no parser warning exists', () => {
  render(<ReviewWarnings accepted={[]} change={() => {}} disabled={false} warnings={[]} />)
  expect(screen.getByText(/仍未经过数学或来源审校/)).toBeTruthy()
})
